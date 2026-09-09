import time
from datetime import datetime
from threading import Lock

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
from ..models import Batch, Posting, Student, StudentSkill, User, VerificationRequest
from ..schemas import (
    AnalyticsOut,
    FacultyStudentCreate,
    FacultyStudentOut,
    FacultyStudentUpdate,
    FacultyVerificationQueueOut,
    FacultyVerificationReviewIn,
    MarketRefreshOut,
    PendingCountOut,
    StudentProfileOut,
)
from .students import invalidate_score_cache, profile_out

router = APIRouter(prefix="/faculty", tags=["placement coordinator"], dependencies=[Depends(require_role("faculty"))])
FACULTY_CACHE_TTL_SECONDS = 60
_analytics_cache: dict[int | None, tuple[float, AnalyticsOut]] = {}
_students_cache: dict[int | None, tuple[float, tuple[FacultyStudentOut, ...]]] = {}
_faculty_cache_lock = Lock()


def clear_faculty_cache() -> None:
    with _faculty_cache_lock:
        _analytics_cache.clear()
        _students_cache.clear()


def cached_faculty(cache: dict, key: int | None):
    with _faculty_cache_lock:
        entry = cache.get(key)
        if entry is not None and time.monotonic() - entry[0] < FACULTY_CACHE_TTL_SECONDS:
            return entry[1]
    return None


def readiness_of(held, postings_requirements, adjacency=None, top: int = 5) -> float:
    if not postings_requirements:
        return 0.0
    best = sorted((score_student(held, reqs, adjacency).score for reqs in postings_requirements), reverse=True)[:top]
    return round(sum(best) / len(best), 1)


@router.get("/analytics", response_model=AnalyticsOut)
def analytics(batch_id: int | None = None, db: Session = Depends(get_db)):
    cached = cached_faculty(_analytics_cache, batch_id)
    if cached is not None:
        return cached
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
    result = AnalyticsOut(
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
    with _faculty_cache_lock:
        _analytics_cache[batch_id] = (time.monotonic(), result)
    return result


@router.get("/students", response_model=list[FacultyStudentOut])
def list_students(batch_id: int | None = None, db: Session = Depends(get_db)):
    cached = cached_faculty(_students_cache, batch_id)
    if cached is not None:
        return list(cached)
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
    with _faculty_cache_lock:
        _students_cache[batch_id] = (time.monotonic(), tuple(rows))
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
    clear_faculty_cache()
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
    clear_faculty_cache()
    return profile_out(student_with_skills(db, student_id))


@router.post("/students/{student_id}/skills/{skill_id}/verify", response_model=StudentProfileOut)
def verify_skill(student_id: int, skill_id: int, verified: bool = True, faculty: User = Depends(require_role("faculty")), db: Session = Depends(get_db)):
    link = db.get(StudentSkill, (student_id, skill_id))
    if link is None:
        raise HTTPException(404, "This student has not claimed that skill")
    link.verified = verified
    link.verified_by = faculty.id if verified else None
    db.commit()
    clear_faculty_cache()
    return profile_out(student_with_skills(db, student_id))


@router.post("/market/refresh", response_model=MarketRefreshOut)
def market_refresh(db: Session = Depends(get_db)):
    imported, skipped = refresh_market_postings(db)
    clear_faculty_cache()
    total = db.scalar(select(func.count(Posting.id)).where(Posting.source == "market", Posting.active.is_(True)))
    return MarketRefreshOut(imported=imported, skipped=skipped, total_market_postings=total)


def serialize_queue_item(req: VerificationRequest) -> FacultyVerificationQueueOut:
    return FacultyVerificationQueueOut(
        id=req.id,
        student_id=req.student_id,
        student_name=req.student.user.full_name,
        student_roll=req.student.roll_number,
        batch_name=req.student.batch.name,
        student_cgpa=req.student.cgpa,
        student_email=req.student.user.email,
        skill_id=req.skill_id,
        skill_name=req.skill.name,
        skill_category=req.skill.category,
        level=req.level,
        course_name=req.course_name,
        evidence_url=req.evidence_url,
        notes=req.notes,
        status=req.status,
        reviewed_by=req.reviewed_by,
        reviewer_name=req.reviewer.full_name if req.reviewer else None,
        review_feedback=req.review_feedback,
        created_at=req.created_at,
        reviewed_at=req.reviewed_at,
    )


@router.get("/verification-requests/count", response_model=PendingCountOut)
def pending_verifications_count(db: Session = Depends(get_db)):
    count = db.scalar(
        select(func.count(VerificationRequest.id)).where(VerificationRequest.status == "pending")
    ) or 0
    return PendingCountOut(pending_count=count)


@router.get("/verification-requests", response_model=list[FacultyVerificationQueueOut])
def list_verification_requests(status: str | None = None, db: Session = Depends(get_db)):
    stmt = (
        select(VerificationRequest)
        .options(
            selectinload(VerificationRequest.student).selectinload(Student.user),
            selectinload(VerificationRequest.student).selectinload(Student.batch),
            selectinload(VerificationRequest.skill),
            selectinload(VerificationRequest.reviewer),
        )
        .order_by(VerificationRequest.created_at.desc())
    )
    if status and status != "all":
        stmt = stmt.where(VerificationRequest.status == status)

    requests = db.scalars(stmt).all()
    return [serialize_queue_item(req) for req in requests]


@router.post("/verification-requests/{request_id}/review", response_model=FacultyVerificationQueueOut)
def review_verification_request(
    request_id: int,
    body: FacultyVerificationReviewIn,
    faculty: User = Depends(require_role("faculty")),
    db: Session = Depends(get_db),
):
    req = db.execute(
        select(VerificationRequest)
        .where(VerificationRequest.id == request_id)
        .options(
            selectinload(VerificationRequest.student).selectinload(Student.user),
            selectinload(VerificationRequest.student).selectinload(Student.batch),
            selectinload(VerificationRequest.skill),
            selectinload(VerificationRequest.reviewer),
        )
    ).scalar_one_or_none()

    if req is None:
        raise HTTPException(404, "Verification request not found")

    if body.action == "approve":
        req.status = "approved"
        req.reviewed_by = faculty.id
        req.reviewed_at = datetime.now()
        req.review_feedback = body.feedback

        skill_link = db.get(StudentSkill, (req.student_id, req.skill_id))
        if skill_link is not None:
            skill_link.verified = True
            skill_link.verified_by = faculty.id
            if req.level:
                skill_link.level = req.level

        invalidate_score_cache(req.student.user_id)
    elif body.action == "reject":
        req.status = "rejected"
        req.reviewed_by = faculty.id
        req.reviewed_at = datetime.now()
        req.review_feedback = body.feedback
    else:
        raise HTTPException(400, "Invalid action. Must be 'approve' or 'reject'.")

    db.commit()
    clear_faculty_cache()
    db.refresh(req)
    return serialize_queue_item(req)