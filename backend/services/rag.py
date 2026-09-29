import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import KnowledgeChunk
from .llm import embed


def cosine(a, b) -> float:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if a.size == 0 or b.size == 0 or a.size != b.size:
        return 0.0
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def job_text(title: str, company: str, description: str, skills: list[str]) -> str:
    return f"{title} at {company}. Skills: {', '.join(skills)}. {description}"


def retrieve(db: Session, query: str, k: int = 4, categories: list[str] | None = None):
    """Return the k most relevant knowledge base entries as (score, chunk) pairs."""
    query_vector = embed(query)
    stmt = select(KnowledgeChunk)
    if categories:
        stmt = stmt.where(KnowledgeChunk.category.in_(categories))
    chunks = db.scalars(stmt).all()
    scored = sorted(
        ((cosine(query_vector, c.embedding), c) for c in chunks),
        key=lambda pair: pair[0],
        reverse=True,
    )
    return scored[:k]


def build_context(scored) -> str:
    if not scored:
        return "(no knowledge base entries found)"
    return "\n\n".join(f"[{c.category}] {c.title}\n{c.content}" for _, c in scored)