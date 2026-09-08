from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .engine import Held, Requirement
from .models import Posting, PostingSkill, Skill, Student, StudentSkill


def skill_name_map(db: Session) -> dict[int, str]:
    return {skill_id: name for skill_id, name in db.execute(select(Skill.id, Skill.name))}


def held_skills_for_students(db: Session, student_ids: list[int]) -> dict[int, dict[int, Held]]:
    held: dict[int, dict[int, Held]] = {student_id: {} for student_id in student_ids}
    if not student_ids:
        return held
    rows = db.execute(
        select(StudentSkill.student_id, StudentSkill.skill_id, StudentSkill.level, StudentSkill.verified)
        .where(StudentSkill.student_id.in_(student_ids))
    )
    for student_id, skill_id, level, verified in rows:
        held[student_id][skill_id] = Held(level=level, verified=verified)
    return held


def held_skills_for_student(db: Session, student_id: int) -> dict[int, Held]:
    return held_skills_for_students(db, [student_id])[student_id]


def active_postings_with_requirements(db: Session) -> list[Posting]:
    return list(
        db.scalars(
            select(Posting)
            .where(Posting.active.is_(True))
            .options(selectinload(Posting.required_skills).selectinload(PostingSkill.skill), selectinload(Posting.company))
            .order_by(Posting.created_at.desc())
        )
    )


def requirements_of(posting: Posting) -> list[Requirement]:
    return [
        Requirement(skill_id=ps.skill_id, skill_name=ps.skill.name, min_level=ps.min_level, importance=ps.importance)
        for ps in posting.required_skills
    ]


def students_in_batch(db: Session, batch_id: int | None) -> list[Student]:
    query = select(Student).options(selectinload(Student.user), selectinload(Student.batch))
    if batch_id is not None:
        query = query.where(Student.batch_id == batch_id)
    return list(db.scalars(query.order_by(Student.roll_number)))
