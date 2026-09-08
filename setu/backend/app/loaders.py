import time
from threading import Lock

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from .engine import Held, Requirement
from .models import Posting, PostingSkill, Skill, SkillSimilarity, Student, StudentSkill

REFERENCE_CACHE_TTL_SECONDS = 300
_reference_cache_lock = Lock()
_skill_names_cache: tuple[float, dict[int, str]] | None = None
_skill_adjacency_cache: tuple[float, dict[int, dict[int, float]]] | None = None


def skill_name_map(db: Session) -> dict[int, str]:
    global _skill_names_cache
    now = time.monotonic()
    with _reference_cache_lock:
        if _skill_names_cache is None or now - _skill_names_cache[0] >= REFERENCE_CACHE_TTL_SECONDS:
            _skill_names_cache = (now, {skill_id: name for skill_id, name in db.execute(select(Skill.id, Skill.name))})
        return _skill_names_cache[1]


def skill_adjacency(db: Session) -> dict[int, dict[int, float]]:
    global _skill_adjacency_cache
    now = time.monotonic()
    with _reference_cache_lock:
        if _skill_adjacency_cache is not None and now - _skill_adjacency_cache[0] < REFERENCE_CACHE_TTL_SECONDS:
            return _skill_adjacency_cache[1]

    adjacency: dict[int, dict[int, float]] = {}
    rows = db.execute(
        select(SkillSimilarity.skill_id, SkillSimilarity.related_skill_id, SkillSimilarity.similarity)
    )
    for skill_id, related_skill_id, similarity in rows:
        adjacency.setdefault(skill_id, {})[related_skill_id] = similarity
    with _reference_cache_lock:
        _skill_adjacency_cache = (now, adjacency)
    return adjacency


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
            .options(joinedload(Posting.required_skills).joinedload(PostingSkill.skill), joinedload(Posting.company))
            .order_by(Posting.created_at.desc())
        ).unique()
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
