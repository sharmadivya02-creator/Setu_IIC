from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Batch, Skill
from ..schemas import BatchOut, SkillOut

router = APIRouter(tags=["reference"])


@router.get("/skills", response_model=list[SkillOut])
def list_skills(db: Session = Depends(get_db)):
    return db.scalars(select(Skill).order_by(Skill.category, Skill.name)).all()


@router.get("/batches", response_model=list[BatchOut])
def list_batches(db: Session = Depends(get_db)):
    return [
        BatchOut(id=batch.id, name=batch.name, college=batch.college.name)
        for batch in db.scalars(select(Batch).order_by(Batch.name))
    ]
