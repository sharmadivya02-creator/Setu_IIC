from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Role = Literal["student", "faculty", "recruiter"]
Importance = Literal["must_have", "nice_to_have"]
ApplicationStatus = Literal["applied", "shortlisted", "interview", "offered", "rejected"]


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    full_name: str = Field(min_length=2, max_length=120)
    role: Role
    batch_id: int | None = None
    roll_number: str | None = None
    company_name: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class SkillOut(BaseModel):
    id: int
    name: str
    category: str


class RelatedSkillOut(BaseModel):
    skill_id: int
    skill: str
    category: str
    similarity: float


class BatchOut(BaseModel):
    id: int
    name: str
    college: str


class StudentSkillIn(BaseModel):
    skill_id: int
    level: int = Field(ge=1, le=5)


class StudentSkillOut(BaseModel):
    skill_id: int
    name: str
    category: str
    level: int
    verified: bool


class StudentProfileOut(BaseModel):
    id: int
    full_name: str
    email: str
    roll_number: str
    batch_id: int
    batch: str
    cgpa: float
    phone: str | None
    github_url: str | None
    resume_url: str | None
    skills: list[StudentSkillOut]


class StudentProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    cgpa: float | None = Field(default=None, ge=0, le=10)
    phone: str | None = None
    github_url: str | None = None
    resume_url: str | None = None


class RequirementOut(BaseModel):
    skill_id: int
    skill: str
    min_level: int
    importance: str


class PostingOut(BaseModel):
    id: int
    title: str
    company: str
    kind: str
    location: str
    description: str
    source: str
    active: bool
    external_url: str | None
    created_at: datetime
    required_skills: list[RequirementOut]


class MatchOut(BaseModel):
    posting: PostingOut
    score: float
    verified_bonus: float
    matched: list[dict]
    below_level: list[dict]
    missing: list[dict]
    related: list[dict] = []
    related_credit: float = 0.0
    application_status: str | None


class LearnNextOut(BaseModel):
    skill_id: int
    skill: str
    target_level: int
    demand_pct: float
    avg_score_lift: float


class ApplicationOut(BaseModel):
    id: int
    posting_id: int
    title: str
    company: str
    status: str
    updated_at: datetime


class RequirementIn(BaseModel):
    skill_id: int
    min_level: int = Field(ge=1, le=5)
    importance: Importance = "must_have"


class PostingIn(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    kind: Literal["job", "internship"]
    location: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=10)
    active: bool = True
    required_skills: list[RequirementIn] = Field(min_length=1)


class CandidateOut(BaseModel):
    student_id: int
    full_name: str
    batch: str
    cgpa: float
    roll_number: str
    verified_skill_count: int
    skill_count: int
    score: float
    verified_bonus: float
    matched: list[dict]
    below_level: list[dict]
    missing: list[dict]
    related: list[dict] = []
    related_credit: float = 0.0
    application_id: int | None
    application_status: str | None
    email: str | None
    phone: str | None
    github_url: str | None
    resume_url: str | None


class StatusUpdateIn(BaseModel):
    status: ApplicationStatus


class GapOut(BaseModel):
    skill_id: int
    skill: str
    demand_pct: float
    held_pct: float
    ready_pct: float
    typical_level: int
    gap: float


class AnalyticsOut(BaseModel):
    batch_id: int | None
    batch: str
    student_count: int
    active_postings: int
    market_postings: int
    avg_readiness: float
    readiness_buckets: dict[str, int]
    gaps: list[GapOut]
    strengths: list[GapOut]


class FacultyStudentOut(BaseModel):
    id: int
    full_name: str
    email: str
    roll_number: str
    batch_id: int
    batch: str
    cgpa: float
    skill_count: int
    verified_count: int
    readiness: float


class FacultyStudentCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    roll_number: str = Field(min_length=1, max_length=40)
    batch_id: int
    cgpa: float = Field(default=0, ge=0, le=10)
    password: str = Field(default="setu1234", min_length=6, max_length=72)


class FacultyStudentUpdate(BaseModel):
    full_name: str | None = None
    roll_number: str | None = None
    batch_id: int | None = None
    cgpa: float | None = Field(default=None, ge=0, le=10)


class MarketRefreshOut(BaseModel):
    imported: int
    skipped: int
    total_market_postings: int


class ParsedSkillOut(BaseModel):
    skill_id: int
    name: str
    category: str
    suggested_level: int = Field(ge=1, le=5)
    evidence: str


class ResumeParseResponse(BaseModel):
    summary: str
    skills: list[ParsedSkillOut]
    total_detected: int


class VerificationRequestCreate(BaseModel):
    skill_id: int
    course_name: str | None = None
    evidence_url: str | None = None
    notes: str | None = None


class VerificationRequestOut(BaseModel):
    id: int
    skill_id: int
    skill_name: str
    skill_category: str
    level: int
    course_name: str | None
    evidence_url: str | None
    notes: str | None
    status: str
    reviewed_by: int | None
    review_feedback: str | None
    created_at: datetime
    reviewed_at: datetime | None


class FacultyVerificationReviewIn(BaseModel):
    action: Literal["approve", "reject"]
    feedback: str | None = None


class FacultyVerificationQueueOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    student_roll: str
    batch_name: str
    student_cgpa: float
    student_email: str
    skill_id: int
    skill_name: str
    skill_category: str
    level: int
    course_name: str | None
    evidence_url: str | None
    notes: str | None
    status: str
    reviewed_by: int | None
    reviewer_name: str | None
    review_feedback: str | None
    created_at: datetime
    reviewed_at: datetime | None


class PendingCountOut(BaseModel):
    pending_count: int


class CompanyDocumentOut(BaseModel):
    id: int
    filename: str
    uploaded_at: datetime
    chunk_count: int


class PolicyVerdictOut(BaseModel):
    rule: str
    verdict: str
    evidence_snippet: str
    source_chunk_id: int | None = None


class PolicyCheckResponse(BaseModel):
    candidate_name: str
    posting_title: str
    verdicts: list[PolicyVerdictOut]