import re

from sqlalchemy.orm import Session

from .llm import chat_json, chat_text
from .rag import build_context, cosine, retrieve


def norm(skill: str) -> str:
    """'Node.js' and 'NodeJS' both become 'nodejs' so they compare equal."""
    return re.sub(r"[^a-z0-9+#]", "", str(skill).lower())


def _clean_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    seen, out = set(), []
    for item in value:
        text = str(item).strip()
        if text and text.lower() not in seen:
            seen.add(text.lower())
            out.append(text)
    return out


def _to_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------- Agent 1
class ResumeAnalyzerAgent:
    SYSTEM = """You are a Resume Analyzer Agent. Read the resume text and return ONLY a JSON object with exactly this shape:
{
  "full_name": string or null,
  "email": string or null,
  "phone": string or null,
  "technical_skills": [string],
  "soft_skills": [string],
  "education": [{"degree": string, "institution": string, "year": string}],
  "experience": [{"title": string, "company": string, "duration": string, "highlights": [string]}],
  "years_of_experience": number,
  "summary": string
}
Rules: use ONLY information present in the resume, never invent anything. Use empty lists when nothing is found.
Write skill names in short canonical form (for example "Python", "React", "SQL", "Docker").
"summary" is a professional 3-4 sentence summary of the candidate.
"years_of_experience" is total professional experience in years (0 for students/no experience)."""

    def run(self, resume_text: str) -> dict:
        data = chat_json(self.SYSTEM, resume_text[:12000])
        return {
            "contact": {"name": data.get("full_name"), "email": data.get("email"), "phone": data.get("phone")},
            "technical_skills": _clean_list(data.get("technical_skills")),
            "soft_skills": _clean_list(data.get("soft_skills")),
            "education": data.get("education") if isinstance(data.get("education"), list) else [],
            "experience": data.get("experience") if isinstance(data.get("experience"), list) else [],
            "years_of_experience": _to_float(data.get("years_of_experience")),
            "summary": str(data.get("summary") or ""),
        }


# ---------------------------------------------------------------- Agent 2
class JobMatchingAgent:
    SYSTEM = """You are a Job Matching Agent. You receive a candidate profile, a list of jobs (each with a match score already calculated, matched skills and missing skills) and some career knowledge.
For EACH job write a 2-3 sentence explanation of why it fits the candidate (or not). Mention concrete matched skills and the most important missing skills.
Return ONLY JSON: {"explanations": {"<job_id>": "<text>"}}. Use the job ids exactly as given. Do not change the scores."""

    def recommend(self, db: Session, analysis, jobs, top_n: int = 5) -> list[dict]:
        if not jobs:
            return []
        resume_skills = {norm(s) for s in analysis.technical_skills}
        similarities = [cosine(analysis.embedding, job.embedding) for job in jobs]
        low, high = min(similarities), max(similarities)

        results = []
        for job, similarity in zip(jobs, similarities):
            matched = [s for s in job.required_skills if norm(s) in resume_skills]
            missing = [s for s in job.required_skills if norm(s) not in resume_skills]
            skill_score = len(matched) / len(job.required_skills) if job.required_skills else 0.0
            # similarity is compared relative to the other jobs (best job = 1, worst = 0)
            semantic_score = (similarity - low) / (high - low) if high > low else 0.5
            final = round((0.6 * skill_score + 0.4 * semantic_score) * 100, 1)
            results.append({"job": job, "score": final, "matched": matched, "missing": missing})
        results.sort(key=lambda r: r["score"], reverse=True)
        top = results[:top_n]

        query = f"{analysis.summary} Skills: {', '.join(analysis.technical_skills)}"
        context = build_context(retrieve(db, query, k=3, categories=["career_roadmap", "job_description"]))
        jobs_text = "\n".join(
            f"- job_id={r['job'].id} | {r['job'].title} at {r['job'].company} | score={r['score']} | "
            f"matched={r['matched']} | missing={r['missing']}"
            for r in top
        )
        payload = (
            f"CANDIDATE SUMMARY:\n{analysis.summary}\n"
            f"Skills: {', '.join(analysis.technical_skills)}\n"
            f"Years of experience: {analysis.years_of_experience}\n\n"
            f"JOBS:\n{jobs_text}\n\nKNOWLEDGE:\n{context}"
        )
        explanations = chat_json(self.SYSTEM, payload).get("explanations", {})
        for r in top:
            r["explanation"] = str(explanations.get(str(r["job"].id), ""))
        return top


# ---------------------------------------------------------------- Agent 3
class CareerAdvisorAgent:
    IMPROVE_SYSTEM = """You are a Career Advisor Agent. You receive a resume, a target role and retrieved knowledge (skills, roadmaps, learning resources, resume guidelines).
Prefer facts from the knowledge. Only recommend REAL certifications and REAL learning resources. Be specific and actionable.
Return ONLY JSON:
{
  "target_role": string,
  "missing_skills": [{"skill": string, "why": string}],
  "weaknesses": [string],
  "improvements": [string],
  "certifications": [{"name": string, "why": string}],
  "learning_resources": [{"title": string, "skill": string, "type": string}]
}
Maximum 6 items per list."""

    CHAT_SYSTEM = """You are a friendly Career Advisor Agent. Answer the user's career question clearly in at most 200 words, using the provided knowledge when relevant.
If a candidate profile is provided, personalize the answer. If the question is not about careers, jobs, skills, learning or resumes, politely say you can only help with career topics. Never invent facts."""

    def improve(self, db: Session, resume_text: str, analysis, target_role, target_job) -> dict:
        if target_job is not None:
            target = (f"{target_job.title}. Required skills: {', '.join(target_job.required_skills)}. "
                      f"{target_job.description}")
        elif target_role:
            target = target_role
        else:
            target = "Choose the most suitable role for this candidate based on the resume."
        query = f"{target[:300]} skills roadmap certifications learning resources resume tips"
        context = build_context(retrieve(db, query, k=6))
        payload = (
            f"TARGET ROLE:\n{target}\n\n"
            f"CANDIDATE SKILLS: {', '.join(analysis.technical_skills)}\n\n"
            f"RESUME TEXT:\n{resume_text[:8000]}\n\nKNOWLEDGE:\n{context}"
        )
        return chat_json(self.IMPROVE_SYSTEM, payload, temperature=0.3)

    def answer(self, db: Session, question: str, analysis=None) -> dict:
        scored = retrieve(db, question, k=4)
        profile = ""
        if analysis is not None:
            profile = (f"CANDIDATE PROFILE:\nSkills: {', '.join(analysis.technical_skills)}\n"
                       f"Summary: {analysis.summary}\n\n")
        text = chat_text(self.CHAT_SYSTEM, f"{profile}KNOWLEDGE:\n{build_context(scored)}\n\nQUESTION: {question}")
        return {"answer": text, "sources": [c.title for _, c in scored]}