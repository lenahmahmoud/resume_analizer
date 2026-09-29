import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import MAX_UPLOAD_MB, UPLOAD_DIR
from ..database import get_db
from ..deps import get_current_user, get_owned_resume
from ..models import Resume, ResumeAnalysis, User
from ..services.agents import ResumeAnalyzerAgent
from ..services.llm import embed
from ..services.parser import extract_text

router = APIRouter(prefix="/api/resumes", tags=["Resumes"])
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def resume_out(r: Resume) -> dict:
    return {"id": r.id, "filename": r.filename, "uploaded_at": r.uploaded_at, "analyzed": r.analysis is not None}


def analysis_out(a: ResumeAnalysis) -> dict:
    return {
        "contact": a.contact, "technical_skills": a.technical_skills, "soft_skills": a.soft_skills,
        "education": a.education, "experience": a.experience,
        "years_of_experience": a.years_of_experience, "summary": a.summary,
    }


@router.post("", status_code=201)
def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    original_name = Path(file.filename or "").name
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Only PDF and DOCX files are allowed")
    content = file.file.read()
    if not content:
        raise HTTPException(400, "The uploaded file is empty")
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(400, f"File is too large (maximum {MAX_UPLOAD_MB} MB)")
    if ext == ".pdf" and not content.startswith(b"%PDF"):
        raise HTTPException(400, "This file is not a valid PDF")
    if ext == ".docx" and not content.startswith(b"PK"):
        raise HTTPException(400, "This file is not a valid DOCX")

    UPLOAD_DIR.mkdir(exist_ok=True)
    path = UPLOAD_DIR / f"{uuid.uuid4().hex}{ext}"
    path.write_bytes(content)
    try:
        text = extract_text(path)
    except ValueError as error:
        path.unlink(missing_ok=True)
        raise HTTPException(400, str(error))
    except Exception:
        path.unlink(missing_ok=True)
        raise HTTPException(400, "This file is corrupted or cannot be read. Please upload a valid file.")

    resume = Resume(user_id=user.id, filename=original_name[:255], file_path=str(path), raw_text=text)
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume_out(resume)


@router.get("")
def list_resumes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(Resume).where(Resume.user_id == user.id).order_by(Resume.uploaded_at.desc())).all()
    return [resume_out(r) for r in rows]


@router.get("/{resume_id}")
def get_resume(resume_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resume = get_owned_resume(db, resume_id, user)
    return {**resume_out(resume), "analysis": analysis_out(resume.analysis) if resume.analysis else None}


@router.delete("/{resume_id}", status_code=204)
def delete_resume(resume_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resume = get_owned_resume(db, resume_id, user)
    Path(resume.file_path).unlink(missing_ok=True)
    db.delete(resume)
    db.commit()
    return Response(status_code=204)


@router.post("/{resume_id}/analyze")
def analyze_resume(resume_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resume = get_owned_resume(db, resume_id, user)
    data = ResumeAnalyzerAgent().run(resume.raw_text)

    titles = [e.get("title", "") for e in data["experience"] if isinstance(e, dict)]
    embed_input = (f"{data['summary']} Technical skills: {', '.join(data['technical_skills'])}. "
                   f"Soft skills: {', '.join(data['soft_skills'])}. Roles: {', '.join(titles)}")

    analysis = resume.analysis or ResumeAnalysis(resume=resume)
    for key, value in data.items():
        setattr(analysis, key, value)
    analysis.embedding = embed(embed_input)
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis_out(analysis)