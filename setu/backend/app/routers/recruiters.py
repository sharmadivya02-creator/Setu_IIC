from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..auth import require_role
from ..db import get_db
from ..engine import score_student
from ..loaders import held_skills_for_students, requirements_of, skill_adjacency, skill_name_map, students_in_batch
from ..models import Application, Company, Posting, PostingSkill, Skill, Student, User
from ..schemas import ApplicationOut, CandidateOut, PostingIn, PostingOut, StatusUpdateIn
from .students import posting_out

router = APIRouter(prefix="/recruiters", tags=["recruiter"], dependencies=[Depends(require_role("recruiter"))])

STATUS_ORDER = ["applied", "shortlisted", "interview", "offered", "rejected"]


def my_company(db: Session, user: User) -> Company:
    company = db.scalar(select(Company).where(Company.recruiter_user_id == user.id))
    if company is None:
        raise HTTPException(404, "No company linked to this recruiter account")
    return company


def owned_posting(db: Session, user: User, posting_id: int) -> Posting:
    company = my_company(db, user)
    posting = db.scalar(
        select(Posting)
        .where(Posting.id == posting_id, Posting.company_id == company.id)
        .options(selectinload(Posting.required_skills).selectinload(PostingSkill.skill), selectinload(Posting.company))
    )
    if posting is None:
        raise HTTPException(404, "Posting not found under your company")
    return posting


@router.get("/postings", response_model=list[PostingOut])
def list_postings(user: User = Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    company = my_company(db, user)
    postings = db.scalars(
        select(Posting)
        .where(Posting.company_id == company.id)
        .options(selectinload(Posting.required_skills).selectinload(PostingSkill.skill), selectinload(Posting.company))
        .order_by(Posting.created_at.desc())
    )
    return [posting_out(posting) for posting in postings]


def validate_requirements(db: Session, body: PostingIn) -> None:
    ids = [req.skill_id for req in body.required_skills]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "A skill is listed twice")
    known = set(db.scalars(select(Skill.id).where(Skill.id.in_(ids))))
    unknown = set(ids) - known
    if unknown:
        raise HTTPException(404, f"Unknown skill ids: {sorted(unknown)}")


@router.post("/postings", response_model=PostingOut, status_code=201)
def create_posting(body: PostingIn, user: User = Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    company = my_company(db, user)
    validate_requirements(db, body)
    posting = Posting(
        company_id=company.id,
        title=body.title,
        kind=body.kind,
        location=body.location,
        description=body.description,
        active=body.active,
        source="internal",
    )
    posting.required_skills = [
        PostingSkill(skill_id=req.skill_id, min_level=req.min_level, importance=req.importance) for req in body.required_skills
    ]
    db.add(posting)
    db.commit()
    return posting_out(owned_posting(db, user, posting.id))


@router.put("/postings/{posting_id}", response_model=PostingOut)
def update_posting(posting_id: int, body: PostingIn, user: User = Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    posting = owned_posting(db, user, posting_id)
    validate_requirements(db, body)
    posting.title = body.title
    posting.kind = body.kind
    posting.location = body.location
    posting.description = body.description
    posting.active = body.active
    posting.required_skills = [
        PostingSkill(skill_id=req.skill_id, min_level=req.min_level, importance=req.importance) for req in body.required_skills
    ]
    db.commit()
    return posting_out(owned_posting(db, user, posting_id))


@router.get("/postings/{posting_id}/candidates", response_model=list[CandidateOut])
def ranked_candidates(posting_id: int, limit: int = 50, user: User = Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    posting = owned_posting(db, user, posting_id)
    requirements = requirements_of(posting)
    students = students_in_batch(db, None)
    cohort = held_skills_for_students(db, [student.id for student in students])
    adjacency = skill_adjacency(db)
    skill_names = skill_name_map(db)
    applications = {
        app.student_id: app
        for app in db.scalars(select(Application).where(Application.posting_id == posting_id))
    }

    candidates = []
    for student in students:
        held = cohort[student.id]
        result = score_student(held, requirements, adjacency, skill_names)
        application = applications.get(student.id)
        contact_visible = application is not None and application.status != "applied"
        candidates.append(
            CandidateOut(
                student_id=student.id,
                full_name=student.user.full_name,
                batch=student.batch.name,
                cgpa=student.cgpa,
                roll_number=student.roll_number,
                verified_skill_count=sum(1 for item in held.values() if item.verified),
                skill_count=len(held),
                score=result.score,
                verified_bonus=result.verified_bonus,
                matched=result.matched,
                below_level=result.below_level,
                missing=result.missing,
                related=result.related,
                related_credit=result.related_credit,
                application_id=application.id if application else None,
                application_status=application.status if application else None,
                email=student.user.email if contact_visible else None,
                phone=student.phone if contact_visible else None,
                github_url=student.github_url if contact_visible else None,
                resume_url=student.resume_url if contact_visible else None,
            )
        )
    candidates.sort(key=lambda candidate: (candidate.score, candidate.verified_skill_count, candidate.cgpa), reverse=True)
    return candidates[:limit]


@router.post("/postings/{posting_id}/shortlist/{student_id}", response_model=ApplicationOut, status_code=201)
def shortlist(posting_id: int, student_id: int, user: User = Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    posting = owned_posting(db, user, posting_id)
    if db.get(Student, student_id) is None:
        raise HTTPException(404, "Student not found")
    application = db.scalar(select(Application).where(Application.posting_id == posting_id, Application.student_id == student_id))
    if application is None:
        application = Application(student_id=student_id, posting_id=posting_id)
        db.add(application)
    application.status = "shortlisted"
    db.commit()
    db.refresh(application)
    return ApplicationOut(
        id=application.id,
        posting_id=posting_id,
        title=posting.title,
        company=posting.company.name,
        status=application.status,
        updated_at=application.updated_at,
    )


@router.get("/postings/{posting_id}/applications", response_model=list[CandidateOut])
def applications_for_posting(posting_id: int, user: User = Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    posting = owned_posting(db, user, posting_id)
    requirements = requirements_of(posting)
    applications = list(
        db.scalars(
            select(Application)
            .where(Application.posting_id == posting_id)
            .options(selectinload(Application.student).selectinload(Student.user), selectinload(Application.student).selectinload(Student.batch))
        )
    )
    cohort = held_skills_for_students(db, [app.student_id for app in applications])
    adjacency = skill_adjacency(db)
    skill_names = skill_name_map(db)
    rows = []
    for app in applications:
        student = app.student
        held = cohort[student.id]
        result = score_student(held, requirements, adjacency, skill_names)
        visible = app.status != "applied"
        rows.append(
            CandidateOut(
                student_id=student.id,
                full_name=student.user.full_name,
                batch=student.batch.name,
                cgpa=student.cgpa,
                roll_number=student.roll_number,
                verified_skill_count=sum(1 for item in held.values() if item.verified),
                skill_count=len(held),
                score=result.score,
                verified_bonus=result.verified_bonus,
                matched=result.matched,
                below_level=result.below_level,
                missing=result.missing,
                related=result.related,
                related_credit=result.related_credit,
                application_id=app.id,
                application_status=app.status,
                email=student.user.email if visible else None,
                phone=student.phone if visible else None,
                github_url=student.github_url if visible else None,
                resume_url=student.resume_url if visible else None,
            )
        )
    rows.sort(key=lambda row: (STATUS_ORDER.index(row.application_status), -row.score))
    return rows


@router.put("/applications/{application_id}/status", response_model=ApplicationOut)
def update_status(application_id: int, body: StatusUpdateIn, user: User = Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    company = my_company(db, user)
    application = db.scalar(
        select(Application)
        .join(Posting)
        .where(Application.id == application_id, Posting.company_id == company.id)
        .options(selectinload(Application.posting).selectinload(Posting.company))
    )
    if application is None:
        raise HTTPException(404, "Application not found under your company")
    application.status = body.status
    db.commit()
    db.refresh(application)
    return ApplicationOut(
        id=application.id,
        posting_id=application.posting_id,
        title=application.posting.title,
        company=application.posting.company.name,
        status=application.status,
        updated_at=application.updated_at,
    )