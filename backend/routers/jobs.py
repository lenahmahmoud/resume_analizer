from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Job, User
from ..schemas import JobIn, JobOut
from ..services.llm import embed
from ..services.rag import job_text

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


def _clean_skills(skills: list[str]) -> list[str]:
    seen, out = set(), []
    for skill in skills:
        skill = skill.strip()
        if skill and skill.lower() not in seen:
            seen.add(skill.lower())
            out.append(skill)
    return out


def _fill(job: Job, data: JobIn) -> None:
    job.title = data.title.strip()
    job.company = data.company.strip()
    job.location = data.location.strip() or "Remote"
    job.job_type = data.job_type.strip() or "Full-time"
    job.description = data.description.strip()
    job.required_skills = _clean_skills(data.required_skills)
    job.embedding = embed(job_text(job.title, job.company, job.description, job.required_skills))


def _get_or_404(db: Session, job_id: int) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return job


@router.get("", response_model=list[JobOut])
def list_jobs(q: Optional[str] = None, location: Optional[str] = None, job_type: Optional[str] = None,
              company: Optional[str] = None, skill: Optional[str] = None,
              db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    stmt = select(Job).order_by(Job.created_at.desc())
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Job.title.ilike(like), Job.company.ilike(like), Job.description.ilike(like)))
    if location:
        stmt = stmt.where(Job.location.ilike(f"%{location}%"))
    if company:
        stmt = stmt.where(Job.company.ilike(f"%{company}%"))
    if job_type:
        stmt = stmt.where(Job.job_type.ilike(job_type))
    jobs = db.scalars(stmt).all()
    if skill:
        jobs = [j for j in jobs if any(skill.lower() in s.lower() for s in j.required_skills)]
    return jobs


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return _get_or_404(db, job_id)


@router.post("", response_model=JobOut, status_code=201)
def create_job(data: JobIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    job = Job()
    _fill(job, data)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.put("/{job_id}", response_model=JobOut)
def update_job(job_id: int, data: JobIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    job = _get_or_404(db, job_id)
    _fill(job, data)
    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    db.delete(_get_or_404(db, job_id))
    db.commit()
    return Response(status_code=204)