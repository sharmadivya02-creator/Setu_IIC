import time
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Batch, Skill, SkillSimilarity
from ..schemas import BatchOut, RelatedSkillOut, SkillOut

router = APIRouter(tags=["reference"])

SKILLS_CACHE_TTL_SECONDS = 300
_skills_cache: tuple[float, tuple[SkillOut, ...]] | None = None
_skills_cache_lock = Lock()


@router.get("/skills", response_model=list[SkillOut])
def list_skills(db: Session = Depends(get_db)):
    global _skills_cache

    now = time.monotonic()
    with _skills_cache_lock:
        if _skills_cache is None or now - _skills_cache[0] >= SKILLS_CACHE_TTL_SECONDS:
            _skills_cache = (
                now,
                tuple(
                    SkillOut(id=skill.id, name=skill.name, category=skill.category)
                    for skill in db.scalars(select(Skill).order_by(Skill.category, Skill.name))
                ),
            )
        return list(_skills_cache[1])


@router.get("/skills/{skill_id}/related", response_model=list[RelatedSkillOut])
def related_skills(skill_id: int, db: Session = Depends(get_db)):
    """Show which skills the embedding model considers close to this one.

    Returns an empty list when the skill graph has not been built.
    """
    if db.get(Skill, skill_id) is None:
        raise HTTPException(404, "Skill not found")
    rows = db.execute(
        select(Skill.id, Skill.name, Skill.category, SkillSimilarity.similarity)
        .join(SkillSimilarity, SkillSimilarity.related_skill_id == Skill.id)
        .where(SkillSimilarity.skill_id == skill_id)
        .order_by(SkillSimilarity.similarity.desc())
    )
    return [
        RelatedSkillOut(skill_id=row[0], skill=row[1], category=row[2], similarity=round(row[3], 3))
        for row in rows
    ]


@router.get("/batches", response_model=list[BatchOut])
def list_batches(db: Session = Depends(get_db)):
    return [
        BatchOut(id=batch.id, name=batch.name, college=batch.college.name)
        for batch in db.scalars(select(Batch).order_by(Batch.name))
    ]
