from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..auth import require_role
from ..db import get_db
from ..engine import learn_next, score_student
from ..loaders import active_postings_with_requirements, held_skills_for_student, requirements_of
from ..models import Application, Posting, Skill, Student, StudentSkill, User
from ..schemas import (
    ApplicationOut,
    LearnNextOut,
    MatchOut,
    PostingOut,
    RequirementOut,
    StudentProfileOut,
    StudentProfileUpdate,
    StudentSkillIn,
    StudentSkillOut,
)

router = APIRouter(prefix="/students", tags=["student"], dependencies=[Depends(require_role("student"))])


def load_student(db: Session, user: User) -> Student:
    student = db.scalar(
        select(Student)
        .where(Student.user_id == user.id)
        .options(selectinload(Student.skills).selectinload(StudentSkill.skill), selectinload(Student.batch))
    )
    if student is None:
        raise HTTPException(404, "No student profile for this account")
    return student


def posting_out(posting: Posting) -> PostingOut:
    return PostingOut(
        id=posting.id,
        title=posting.title,
        company=posting.company.name,
        kind=posting.kind,
        location=posting.location,
        description=posting.description,
        source=posting.source,
        active=posting.active,
        external_url=posting.external_url,
        created_at=posting.created_at,
        required_skills=[
            RequirementOut(skill_id=ps.skill_id, skill=ps.skill.name, min_level=ps.min_level, importance=ps.importance)
            for ps in posting.required_skills
        ],
    )


def profile_out(student: Student) -> StudentProfileOut:
    return StudentProfileOut(
        id=student.id,
        full_name=student.user.full_name,
        email=student.user.email,
        roll_number=student.roll_number,
        batch_id=student.batch_id,
        batch=student.batch.name,
        cgpa=student.cgpa,
        phone=student.phone,
        github_url=student.github_url,
        resume_url=student.resume_url,
        skills=sorted(
            [
                StudentSkillOut(skill_id=ss.skill_id, name=ss.skill.name, category=ss.skill.category, level=ss.level, verified=ss.verified)
                for ss in student.skills
            ],
            key=lambda item: (-item.level, item.name),
        ),
    )


@router.get("/me", response_model=StudentProfileOut)
def my_profile(user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    return profile_out(load_student(db, user))


@router.put("/me", response_model=StudentProfileOut)
def update_profile(body: StudentProfileUpdate, user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    student = load_student(db, user)
    if body.full_name is not None:
        student.user.full_name = body.full_name
    for field in ("cgpa", "phone", "github_url", "resume_url"):
        value = getattr(body, field)
        if value is not None:
            setattr(student, field, value)
    db.commit()
    db.refresh(student)
    return profile_out(student)


@router.put("/me/skills", response_model=StudentProfileOut)
def replace_skills(body: list[StudentSkillIn], user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    student = load_student(db, user)
    wanted = {item.skill_id: item.level for item in body}
    known_ids = set(db.scalars(select(Skill.id).where(Skill.id.in_(wanted.keys()))))
    unknown = set(wanted) - known_ids
    if unknown:
        raise HTTPException(404, f"Unknown skill ids: {sorted(unknown)}")

    existing = {ss.skill_id: ss for ss in student.skills}
    for skill_id, level in wanted.items():
        if skill_id in existing:
            if existing[skill_id].level != level:
                existing[skill_id].level = level
                existing[skill_id].verified = False
                existing[skill_id].verified_by = None
        else:
            student.skills.append(StudentSkill(skill_id=skill_id, level=level))
    student.skills = [ss for ss in student.skills if ss.skill_id in wanted]
    db.commit()
    return profile_out(load_student(db, user))


@router.get("/me/matches", response_model=list[MatchOut])
def my_matches(user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    student = load_student(db, user)
    held = held_skills_for_student(db, student.id)
    postings = active_postings_with_requirements(db)
    statuses = {
        posting_id: status
        for posting_id, status in db.execute(
            select(Application.posting_id, Application.status).where(Application.student_id == student.id)
        )
    }
    matches = []
    for posting in postings:
        result = score_student(held, requirements_of(posting))
        matches.append(
            MatchOut(
                posting=posting_out(posting),
                score=result.score,
                verified_bonus=result.verified_bonus,
                matched=result.matched,
                below_level=result.below_level,
                missing=result.missing,
                application_status=statuses.get(posting.id),
            )
        )
    matches.sort(key=lambda match: match.score, reverse=True)
    return matches


@router.get("/me/gaps", response_model=list[LearnNextOut])
def my_gaps(user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    student = load_student(db, user)
    held = held_skills_for_student(db, student.id)
    postings = active_postings_with_requirements(db)
    return learn_next(held, [requirements_of(posting) for posting in postings])


@router.post("/me/apply/{posting_id}", response_model=ApplicationOut, status_code=201)
def apply(posting_id: int, user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    student = load_student(db, user)
    posting = db.get(Posting, posting_id)
    if posting is None or not posting.active:
        raise HTTPException(404, "Posting not found or closed")
    if posting.source != "internal":
        raise HTTPException(400, "Market postings are for demand analytics only; apply on the company site")
    duplicate = db.scalar(select(Application.id).where(Application.student_id == student.id, Application.posting_id == posting_id))
    if duplicate:
        raise HTTPException(409, "You already applied to this posting")
    application = Application(student_id=student.id, posting_id=posting_id)
    db.add(application)
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


@router.get("/me/applications", response_model=list[ApplicationOut])
def my_applications(user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    student = load_student(db, user)
    applications = db.scalars(
        select(Application)
        .where(Application.student_id == student.id)
        .options(selectinload(Application.posting).selectinload(Posting.company))
        .order_by(Application.updated_at.desc())
    )
    return [
        ApplicationOut(
            id=app.id,
            posting_id=app.posting_id,
            title=app.posting.title,
            company=app.posting.company.name,
            status=app.status,
            updated_at=app.updated_at,
        )
        for app in applications
    ]
