from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, get_owned_resume
from ..models import Job, JobMatch, User
from ..services.agents import JobMatchingAgent

router = APIRouter(prefix="/api/matching", tags=["Job Matching"])


def _stored(db: Session, resume_id: int) -> list[dict]:
    rows = db.scalars(select(JobMatch).where(JobMatch.resume_id == resume_id)
                      .order_by(JobMatch.score.desc())).all()
    return [{
        "job_id": m.job_id, "title": m.job.title, "company": m.job.company, "location": m.job.location,
        "job_type": m.job.job_type, "score": m.score, "matched_skills": m.matched_skills,
        "missing_skills": m.missing_skills, "explanation": m.explanation,
    } for m in rows]


@router.post("/{resume_id}")
def recommend_jobs(resume_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resume = get_owned_resume(db, resume_id, user)
    if resume.analysis is None:
        raise HTTPException(400, "Analyze this resume first")
    jobs = db.scalars(select(Job)).all()
    if not jobs:
        raise HTTPException(400, "There are no jobs yet. Add some jobs first.")

    results = JobMatchingAgent().recommend(db, resume.analysis, jobs, top_n=5)
    db.execute(delete(JobMatch).where(JobMatch.resume_id == resume.id))
    for r in results:
        db.add(JobMatch(resume_id=resume.id, job_id=r["job"].id, score=r["score"],
                        matched_skills=r["matched"], missing_skills=r["missing"],
                        explanation=r["explanation"]))
    db.commit()
    return _stored(db, resume.id)


@router.get("/{resume_id}")
def get_matches(resume_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resume = get_owned_resume(db, resume_id, user)
    return _stored(db, resume.id)