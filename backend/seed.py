import json
import sys
from pathlib import Path

from .database import Base, SessionLocal, engine
from .models import Job, KnowledgeChunk
from .services.llm import embed_many
from .services.rag import job_text

KB_FILE = Path(__file__).parent / "knowledge_base" / "knowledge_base.json"

SAMPLE_JOBS = [
    ("Junior Python Backend Developer", "TechNile", "Cairo, Egypt", "Full-time",
     "Build and maintain REST APIs for our web platform using Python and FastAPI. Work with SQL databases, write clean tested code and collaborate with the frontend team.",
     ["Python", "FastAPI", "SQL", "Git", "REST APIs", "Docker"]),
    ("Frontend Developer", "PixelWave", "Remote", "Full-time",
     "Create responsive, accessible user interfaces with JavaScript and React. Consume REST APIs, review code with teammates and deliver polished features every sprint.",
     ["HTML", "CSS", "JavaScript", "React", "Git", "Responsive Design"]),
    ("Full-Stack MERN Developer", "CodeCraft", "Giza, Egypt", "Full-time",
     "Develop full-stack features with MongoDB, Express, React and Node.js. Design APIs, build components and deploy applications to the cloud.",
     ["MongoDB", "Express", "React", "Node.js", "JavaScript", "Git"]),
    ("Data Analyst", "DataBridge", "Remote", "Full-time",
     "Analyze business data with SQL and Python, build dashboards in Power BI and present insights to managers to support decisions.",
     ["SQL", "Excel", "Python", "Power BI", "Data Visualization", "Statistics"]),
    ("Machine Learning Engineer", "VisionAI", "Cairo, Egypt", "Full-time",
     "Train, evaluate and deploy machine learning models. Prepare datasets with pandas, experiment with PyTorch and work with engineers to ship models to production.",
     ["Python", "Machine Learning", "PyTorch", "TensorFlow", "Pandas", "NumPy", "SQL"]),
    ("DevOps Engineer", "CloudNest", "Remote", "Full-time",
     "Automate deployments, manage containers and cloud infrastructure, and maintain CI/CD pipelines so teams can release safely and quickly.",
     ["Linux", "Docker", "Kubernetes", "CI/CD", "AWS", "Git", "Bash"]),
    ("UI/UX Designer Intern", "DesignHive", "Alexandria, Egypt", "Internship",
     "Support the design team by creating wireframes and prototypes in Figma, running small user research sessions and handing designs to developers.",
     ["Figma", "Wireframing", "Prototyping", "User Research", "HTML", "CSS"]),
    ("Cybersecurity Analyst", "SecureOps", "Remote", "Full-time",
     "Monitor security alerts, investigate incidents, assess risks and improve our defenses. Automate repetitive tasks with Python scripts.",
     ["Networking", "Linux", "SIEM", "Incident Response", "Python", "Risk Assessment"]),
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if "--reset-kb" in sys.argv:
            db.query(KnowledgeChunk).delete()
            db.commit()

        if db.query(KnowledgeChunk).count() == 0:
            items = json.loads(KB_FILE.read_text(encoding="utf-8"))
            print(f"Embedding {len(items)} knowledge base entries (about 30-60 seconds)...")
            vectors = embed_many([f"{i['title']}. {i['content']}" for i in items])
            for item, vector in zip(items, vectors):
                db.add(KnowledgeChunk(category=item["category"], title=item["title"],
                                      content=item["content"], embedding=vector))
            db.commit()
            print(f"Knowledge base: added {len(items)} entries")
        else:
            print("Knowledge base already filled (use --reset-kb to rebuild it)")

        if db.query(Job).count() == 0:
            print(f"Embedding {len(SAMPLE_JOBS)} sample jobs...")
            vectors = embed_many([job_text(t, c, d, s) for t, c, _, _, d, s in SAMPLE_JOBS])
            for (title, company, location, job_type, description, skills), vector in zip(SAMPLE_JOBS, vectors):
                db.add(Job(title=title, company=company, location=location, job_type=job_type,
                           description=description, required_skills=skills, embedding=vector))
            db.commit()
            print(f"Jobs: added {len(SAMPLE_JOBS)} sample jobs")
        else:
            print("Jobs already exist")
    finally:
        db.close()


if __name__ == "__main__":
    seed()