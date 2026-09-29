from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, get_owned_resume
from ..models import ImprovementReport, Job, User
from ..schemas import ChatIn, ImproveIn
from ..services.agents import CareerAdvisorAgent

router = APIRouter(prefix="/api/advisor", tags=["Career Advisor"])


@router.post("/improve/{resume_id}")
def improve_resume(resume_id: int, data: ImproveIn, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    resume = get_owned_resume(db, resume_id, user)
    if resume.analysis is None:
        raise HTTPException(400, "Analyze this resume first")
    job = None
    if data.target_job_id:
        job = db.get(Job, data.target_job_id)
        if job is None:
            raise HTTPException(404, "Target job not found")

    report = CareerAdvisorAgent().improve(db, resume.raw_text, resume.analysis, data.target_role, job)
    row = resume.report or ImprovementReport(resume=resume)
    row.target_role = str(report.get("target_role") or "")[:150]
    row.report = report
    db.add(row)
    db.commit()
    return report


@router.get("/improve/{resume_id}")
def get_report(resume_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resume = get_owned_resume(db, resume_id, user)
    return resume.report.report if resume.report else None


@router.post("/chat")
def chat(data: ChatIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    analysis = None
    if data.resume_id:
        analysis = get_owned_resume(db, data.resume_id, user).analysis
    return CareerAdvisorAgent().answer(db, data.question, analysis)