import time
from threading import Lock

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from ..ai import extract_skills_with_groq, extract_text_from_pdf
from ..auth import invalidate_cached_user, require_role
from ..db import get_db
from ..engine import learn_next, score_student
from ..loaders import Held, active_postings_with_requirements, requirements_of, skill_adjacency, skill_name_map
from ..models import Application, Posting, Skill, Student, StudentSkill, User
from ..schemas import (
    ApplicationOut,
    LearnNextOut,
    MatchOut,
    ParsedSkillOut,
    PostingOut,
    RequirementOut,
    ResumeParseResponse,
    StudentProfileOut,
    StudentProfileUpdate,
    StudentSkillIn,
    StudentSkillOut,
)

router = APIRouter(prefix="/students", tags=["student"], dependencies=[Depends(require_role("student"))])
SCORE_CACHE_TTL_SECONDS = 60
_matches_cache: dict[int, tuple[float, tuple[MatchOut, ...]]] = {}
_gaps_cache: dict[int, tuple[float, tuple[LearnNextOut, ...]]] = {}
_applications_cache: dict[int, tuple[float, tuple[ApplicationOut, ...]]] = {}
_score_cache_lock = Lock()


def invalidate_score_cache(user_id: int) -> None:
    with _score_cache_lock:
        _matches_cache.pop(user_id, None)
        _gaps_cache.pop(user_id, None)
        _applications_cache.pop(user_id, None)


def cached_score(cache: dict, user_id: int):
    with _score_cache_lock:
        entry = cache.get(user_id)
        if entry is not None and time.monotonic() - entry[0] < SCORE_CACHE_TTL_SECONDS:
            return list(entry[1])
    return None


def load_student(db: Session, user: User) -> Student:
    student = db.execute(
        select(Student)
        .where(Student.user_id == user.id)
        .options(
            joinedload(Student.user),
            joinedload(Student.batch),
            joinedload(Student.skills).joinedload(StudentSkill.skill),
        )
    ).unique().scalar_one_or_none()
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


def held_skills(student: Student) -> dict[int, Held]:
    """Build the scoring input from skills already eager-loaded with the profile."""
    return {skill.skill_id: Held(level=skill.level, verified=skill.verified) for skill in student.skills}


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
    invalidate_cached_user(user.id)
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
    invalidate_score_cache(user.id)
    return profile_out(load_student(db, user))


@router.post("/me/parse-resume", response_model=ResumeParseResponse)
async def parse_resume(
    file: UploadFile = File(...),
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    if user is None:
        raise HTTPException(401, "Authentication required.")
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported. Please upload a valid .pdf file.")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File size exceeds 10 MB limit.")

    resume_text = extract_text_from_pdf(content)

    skills = list(db.scalars(select(Skill).order_by(Skill.category, Skill.name)))
    taxonomy_data = [{"id": s.id, "name": s.name, "category": s.category} for s in skills]
    skills_by_id = {s.id: s for s in skills}
    skills_by_name = {s.name.lower(): s for s in skills}

    ai_result = await extract_skills_with_groq(resume_text, taxonomy_data)

    parsed_skills: list[ParsedSkillOut] = []
    seen_ids = set()

    for item in ai_result.get("skills", []):
        try:
            skill_id = int(item.get("skill_id", 0))
            raw_level = int(item.get("suggested_level", 1))
            clamped_level = max(1, min(5, raw_level))
            evidence = str(item.get("evidence", "")).strip()

            skill = None
            if skill_id in skills_by_id:
                skill = skills_by_id[skill_id]
            else:
                candidate_name = str(item.get("name") or item.get("skill_name") or "").strip().lower()
                if candidate_name in skills_by_name:
                    skill = skills_by_name[candidate_name]

            if skill and skill.id not in seen_ids:
                seen_ids.add(skill.id)
                parsed_skills.append(
                    ParsedSkillOut(
                        skill_id=skill.id,
                        name=skill.name,
                        category=skill.category,
                        suggested_level=clamped_level,
                        evidence=evidence or f"Identified in resume projects ({skill.name})",
                    )
                )
        except Exception:
            continue

    summary = str(ai_result.get("summary", "")).strip() or "Resume profile analyzed successfully."

    return ResumeParseResponse(
        summary=summary,
        skills=parsed_skills,
        total_detected=len(parsed_skills),
    )


@router.get("/me/matches", response_model=list[MatchOut])

def my_matches(user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    cached = cached_score(_matches_cache, user.id)
    if cached is not None:
        return cached
    student = load_student(db, user)
    held = held_skills(student)
    postings = active_postings_with_requirements(db)
    adjacency = skill_adjacency(db)
    skill_names = skill_name_map(db)
    statuses = {
        posting_id: status
        for posting_id, status in db.execute(
            select(Application.posting_id, Application.status).where(Application.student_id == student.id)
        )
    }
    matches = []
    for posting in postings:
        result = score_student(held, requirements_of(posting), adjacency, skill_names)
        matches.append(
            MatchOut(
                posting=posting_out(posting),
                score=result.score,
                verified_bonus=result.verified_bonus,
                matched=result.matched,
                below_level=result.below_level,
                missing=result.missing,
                related=result.related,
                related_credit=result.related_credit,
                application_status=statuses.get(posting.id),
            )
        )
    matches.sort(key=lambda match: match.score, reverse=True)
    with _score_cache_lock:
        _matches_cache[user.id] = (time.monotonic(), tuple(matches))
    return matches


@router.get("/me/gaps", response_model=list[LearnNextOut])
def my_gaps(user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    cached = cached_score(_gaps_cache, user.id)
    if cached is not None:
        return cached
    student = load_student(db, user)
    held = held_skills(student)
    postings = active_postings_with_requirements(db)
    gaps = learn_next(held, [requirements_of(posting) for posting in postings], adjacency=skill_adjacency(db))
    with _score_cache_lock:
        _gaps_cache[user.id] = (time.monotonic(), tuple(gaps))
    return gaps


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
    invalidate_score_cache(user.id)
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
    cached = cached_score(_applications_cache, user.id)
    if cached is not None:
        return cached
    student = load_student(db, user)
    applications = db.scalars(
        select(Application)
        .where(Application.student_id == student.id)
        .options(selectinload(Application.posting).selectinload(Posting.company))
        .order_by(Application.updated_at.desc())
    )
    result = [
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
    with _score_cache_lock:
        _applications_cache[user.id] = (time.monotonic(), tuple(result))
    return result
import time
from threading import Lock
