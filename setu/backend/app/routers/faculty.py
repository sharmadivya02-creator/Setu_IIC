from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..auth import hash_password, require_role
from ..db import get_db
from ..engine import cohort_gaps, score_student
from ..loaders import (
    active_postings_with_requirements,
    held_skills_for_students,
    requirements_of,
    skill_adjacency,
    skill_name_map,
    students_in_batch,
)
from ..market import refresh_market_postings
from ..models import Batch, Posting, Student, StudentSkill, User
from ..schemas import (
    AnalyticsOut,
    FacultyStudentCreate,
    FacultyStudentOut,
    FacultyStudentUpdate,
    MarketRefreshOut,
    StudentProfileOut,
)
from .students import profile_out

router = APIRouter(prefix="/faculty", tags=["placement coordinator"], dependencies=[Depends(require_role("faculty"))])


def readiness_of(held, postings_requirements, adjacency=None, top: int = 5) -> float:
    if not postings_requirements:
        return 0.0
    best = sorted((score_student(held, reqs, adjacency).score for reqs in postings_requirements), reverse=True)[:top]
    return round(sum(best) / len(best), 1)


@router.get("/analytics", response_model=AnalyticsOut)
def analytics(batch_id: int | None = None, db: Session = Depends(get_db)):
    batch_name = "All batches"
    if batch_id is not None:
        batch = db.get(Batch, batch_id)
        if batch is None:
            raise HTTPException(404, "Batch not found")
        batch_name = batch.name

    students = students_in_batch(db, batch_id)
    student_ids = [student.id for student in students]
    cohort = held_skills_for_students(db, student_ids)
    postings = active_postings_with_requirements(db)
    postings_requirements = [requirements_of(posting) for posting in postings]
    adjacency = skill_adjacency(db)

    readiness = [readiness_of(cohort[student_id], postings_requirements, adjacency) for student_id in student_ids]
    buckets = {"ready": 0, "close": 0, "developing": 0, "at_risk": 0}
    for value in readiness:
        if value >= 70:
            buckets["ready"] += 1
        elif value >= 50:
            buckets["close"] += 1
        elif value >= 30:
            buckets["developing"] += 1
        else:
            buckets["at_risk"] += 1

    gaps = cohort_gaps(cohort, postings_requirements, skill_name_map(db))
    return AnalyticsOut(
        batch_id=batch_id,
        batch=batch_name,
        student_count=len(students),
        active_postings=len(postings),
        market_postings=sum(1 for posting in postings if posting.source == "market"),
        avg_readiness=round(sum(readiness) / len(readiness), 1) if readiness else 0.0,
        readiness_buckets=buckets,
        gaps=gaps[:12],
        strengths=sorted(gaps, key=lambda item: item["gap"])[:6],
    )


@router.get("/students", response_model=list[FacultyStudentOut])
def list_students(batch_id: int | None = None, db: Session = Depends(get_db)):
    students = students_in_batch(db, batch_id)
    student_ids = [student.id for student in students]
    cohort = held_skills_for_students(db, student_ids)
    postings_requirements = [requirements_of(posting) for posting in active_postings_with_requirements(db)]
    adjacency = skill_adjacency(db)
    rows = []
    for student in students:
        held = cohort[student.id]
        rows.append(
            FacultyStudentOut(
                id=student.id,
                full_name=student.user.full_name,
                email=student.user.email,
                roll_number=student.roll_number,
                batch_id=student.batch_id,
                batch=student.batch.name,
                cgpa=student.cgpa,
                skill_count=len(held),
                verified_count=sum(1 for item in held.values() if item.verified),
                readiness=readiness_of(held, postings_requirements, adjacency),
            )
        )
    rows.sort(key=lambda row: row.readiness, reverse=True)
    return rows


def student_with_skills(db: Session, student_id: int) -> Student:
    student = db.scalar(
        select(Student)
        .where(Student.id == student_id)
        .options(selectinload(Student.skills).selectinload(StudentSkill.skill), selectinload(Student.batch), selectinload(Student.user))
    )
    if student is None:
        raise HTTPException(404, "Student not found")
    return student


@router.get("/students/{student_id}", response_model=StudentProfileOut)
def student_detail(student_id: int, db: Session = Depends(get_db)):
    return profile_out(student_with_skills(db, student_id))


@router.post("/students", response_model=FacultyStudentOut, status_code=201)
def add_student(body: FacultyStudentCreate, db: Session = Depends(get_db)):
    if db.scalar(select(User.id).where(User.email == body.email)):
        raise HTTPException(409, "An account with this email already exists")
    batch = db.get(Batch, body.batch_id)
    if batch is None:
        raise HTTPException(404, "Batch not found")
    user = User(email=body.email, password_hash=hash_password(body.password), role="student", full_name=body.full_name)
    db.add(user)
    db.flush()
    student = Student(user_id=user.id, batch_id=batch.id, roll_number=body.roll_number, cgpa=body.cgpa)
    db.add(student)
    db.commit()
    return FacultyStudentOut(
        id=student.id,
        full_name=user.full_name,
        email=user.email,
        roll_number=student.roll_number,
        batch_id=batch.id,
        batch=batch.name,
        cgpa=student.cgpa,
        skill_count=0,
        verified_count=0,
        readiness=0.0,
    )


@router.put("/students/{student_id}", response_model=StudentProfileOut)
def edit_student(student_id: int, body: FacultyStudentUpdate, db: Session = Depends(get_db)):
    student = student_with_skills(db, student_id)
    if body.full_name is not None:
        student.user.full_name = body.full_name
    if body.roll_number is not None:
        student.roll_number = body.roll_number
    if body.cgpa is not None:
        student.cgpa = body.cgpa
    if body.batch_id is not None:
        if db.get(Batch, body.batch_id) is None:
            raise HTTPException(404, "Batch not found")
        student.batch_id = body.batch_id
    db.commit()
    return profile_out(student_with_skills(db, student_id))


@router.post("/students/{student_id}/skills/{skill_id}/verify", response_model=StudentProfileOut)
def verify_skill(student_id: int, skill_id: int, verified: bool = True, faculty: User = Depends(require_role("faculty")), db: Session = Depends(get_db)):
    link = db.get(StudentSkill, (student_id, skill_id))
    if link is None:
        raise HTTPException(404, "This student has not claimed that skill")
    link.verified = verified
    link.verified_by = faculty.id if verified else None
    db.commit()
    return profile_out(student_with_skills(db, student_id))


@router.post("/market/refresh", response_model=MarketRefreshOut)
def market_refresh(db: Session = Depends(get_db)):
    imported, skipped = refresh_market_postings(db)
    total = db.scalar(select(func.count(Posting.id)).where(Posting.source == "market", Posting.active.is_(True)))
    return MarketRefreshOut(imported=imported, skipped=skipped, total_market_postings=total)