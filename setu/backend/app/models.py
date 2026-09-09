from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    student: Mapped["Student | None"] = relationship(back_populates="user", uselist=False)
    company: Mapped["Company | None"] = relationship(back_populates="recruiter", uselist=False)


class College(Base):
    __tablename__ = "colleges"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))

    batches: Mapped[list["Batch"]] = relationship(back_populates="college")


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))

    college: Mapped[College] = relationship(back_populates="batches")
    students: Mapped[list["Student"]] = relationship(back_populates="batch")


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), index=True)
    roll_number: Mapped[str] = mapped_column(String(40))
    cgpa: Mapped[float] = mapped_column(Float, default=0.0)
    phone: Mapped[str | None] = mapped_column(String(20))
    github_url: Mapped[str | None] = mapped_column(String(255))
    resume_url: Mapped[str | None] = mapped_column(String(255))

    user: Mapped[User] = relationship(back_populates="student")
    batch: Mapped[Batch] = relationship(back_populates="students")
    skills: Mapped[list["StudentSkill"]] = relationship(back_populates="student", cascade="all, delete-orphan")
    applications: Mapped[list["Application"]] = relationship(back_populates="student")
    verification_requests: Mapped[list["VerificationRequest"]] = relationship(back_populates="student", cascade="all, delete-orphan")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    category: Mapped[str] = mapped_column(String(40), index=True)


class StudentSkill(Base):
    __tablename__ = "student_skills"

    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True)
    level: Mapped[int] = mapped_column(Integer)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    student: Mapped[Student] = relationship(back_populates="skills")
    skill: Mapped[Skill] = relationship()


Index("ix_student_skills_skill_id", StudentSkill.skill_id)


class SkillSimilarity(Base):
    """Precomputed semantic closeness between two skills.

    Rows are written by scripts/build_skill_graph.py from embedding vectors.
    Both directions are stored (A->B and B->A) so a lookup filters one column.
    An empty table simply disables transferable-skill credit.
    """

    __tablename__ = "skill_similarity"

    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)
    related_skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)
    similarity: Mapped[float] = mapped_column(Float)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    website: Mapped[str | None] = mapped_column(String(255))
    recruiter_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), unique=True)

    recruiter: Mapped[User | None] = relationship(back_populates="company")
    postings: Mapped[list["Posting"]] = relationship(back_populates="company")


class CompanyDocument(Base):
    """A policy PDF (T&C, eligibility rules, etc.) a recruiter uploaded for their company."""

    __tablename__ = "company_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """One chunk of text from an uploaded company policy document.

    No embedding is stored here on purpose: a recruiter's document set is
    tiny (a handful of files, a few dozen chunks), so a TF-IDF vector is
    cheap to build fresh at query time straight from this text column (see
    app/rag.py). That avoids ever serving a stale vector after a document
    is added or removed, and needs no extra migration if the retrieval
    method ever changes.

    company_id is denormalized here (it is also reachable via document.
    company_id) so every retrieval query can filter on one indexed column
    with no join -- that single filter is what keeps one company's policy
    text from ever being retrieved for another company's candidates.
    """

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("company_documents.id", ondelete="CASCADE"), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)

    document: Mapped[CompanyDocument] = relationship(back_populates="chunks")


class Posting(Base):
    __tablename__ = "postings"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(20))
    location: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20), default="internal")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    external_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    company: Mapped[Company] = relationship(back_populates="postings")
    required_skills: Mapped[list["PostingSkill"]] = relationship(back_populates="posting", cascade="all, delete-orphan")
    applications: Mapped[list["Application"]] = relationship(back_populates="posting")


Index("ix_postings_source_active", Posting.source, Posting.active)


class PostingSkill(Base):
    __tablename__ = "posting_skills"

    posting_id: Mapped[int] = mapped_column(ForeignKey("postings.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True)
    min_level: Mapped[int] = mapped_column(Integer)
    importance: Mapped[str] = mapped_column(String(20))

    posting: Mapped[Posting] = relationship(back_populates="required_skills")
    skill: Mapped[Skill] = relationship()


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("student_id", "posting_id", name="uq_application_student_posting"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    posting_id: Mapped[int] = mapped_column(ForeignKey("postings.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="applied")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    student: Mapped[Student] = relationship(back_populates="applications")
 ai
    posting: Mapped[Posting] = relationship(back_populates="applications")


class VerificationRequest(Base):
    __tablename__ = "verification_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), index=True)
    level: Mapped[int] = mapped_column(Integer)
    course_name: Mapped[str | None] = mapped_column(String(120))
    evidence_url: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    review_feedback: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)

    student: Mapped[Student] = relationship(back_populates="verification_requests")
    skill: Mapped[Skill] = relationship()
    reviewer: Mapped[User | None] = relationship(foreign_keys=[reviewed_by])

    posting: Mapped[Posting] = relationship(back_populates="applications")
 main
