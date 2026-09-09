import pathlib
import sys

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

from app.auth import create_token, hash_password
from app.db import Base, get_db
from app.main import app
from app.models import Batch, College, Skill, Student, StudentSkill, User, VerificationRequest

# In-memory SQLite for isolated integration testing
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def setup_module():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()

    # Create College and Batch
    college = College(name="Test College")
    db.add(college)
    db.flush()
    batch = Batch(college_id=college.id, name="CSE 2026")
    db.add(batch)
    db.flush()

    # Create Faculty User
    faculty_user = User(
        email="test_faculty@setu.demo",
        password_hash=hash_password("setu1234"),
        role="faculty",
        full_name="Prof. Test Faculty",
    )
    db.add(faculty_user)

    # Create Student User and Student record
    student_user = User(
        email="test_student@setu.demo",
        password_hash=hash_password("setu1234"),
        role="student",
        full_name="Test Student",
    )
    db.add(student_user)
    db.flush()

    student = Student(
        user_id=student_user.id,
        batch_id=batch.id,
        roll_number="CSE001",
        cgpa=8.5,
    )
    db.add(student)
    db.flush()

    # Create Skills
    python_skill = Skill(name="Python", category="Languages")
    fastapi_skill = Skill(name="FastAPI", category="Backend")
    db.add_all([python_skill, fastapi_skill])
    db.flush()

    # Student has Python (verified) and FastAPI (unverified)
    db.add(StudentSkill(student_id=student.id, skill_id=python_skill.id, level=4, verified=True, verified_by=faculty_user.id))
    db.add(StudentSkill(student_id=student.id, skill_id=fastapi_skill.id, level=3, verified=False))
    db.commit()
    db.close()


def test_student_verification_request_flow():
    db = TestingSessionLocal()
    student_user = db.query(User).filter(User.email == "test_student@setu.demo").first()
    faculty_user = db.query(User).filter(User.email == "test_faculty@setu.demo").first()
    fastapi_skill = db.query(Skill).filter(Skill.name == "FastAPI").first()
    python_skill = db.query(Skill).filter(Skill.name == "Python").first()
    student_token = create_token(student_user)
    faculty_token = create_token(faculty_user)
    db.close()

    student_headers = {"Authorization": f"Bearer {student_token}"}
    faculty_headers = {"Authorization": f"Bearer {faculty_token}"}

    # 1. Cannot request verification for an already verified skill
    res = client.post(
        "/api/students/me/verification-requests",
        json={"skill_id": python_skill.id, "course_name": "CS101"},
        headers=student_headers,
    )
    assert res.status_code == 400
    assert "already verified" in res.json()["detail"]

    # 2. Student successfully submits verification request for FastAPI
    res = client.post(
        "/api/students/me/verification-requests",
        json={
            "skill_id": fastapi_skill.id,
            "course_name": "CS-302 Web Architectures",
            "evidence_url": "https://github.com/test/fastapi-app",
            "notes": "Built async endpoints with JWT and SQLite",
        },
        headers=student_headers,
    )
    assert res.status_code == 201
    created_req = res.json()
    assert created_req["skill_name"] == "FastAPI"
    assert created_req["status"] == "pending"
    assert created_req["level"] == 3
    req_id = created_req["id"]

    # 3. Student views their requests list
    res = client.get("/api/students/me/verification-requests", headers=student_headers)
    assert res.status_code == 200
    requests_list = res.json()
    assert len(requests_list) >= 1
    assert requests_list[0]["skill_name"] == "FastAPI"

    # 4. Faculty checks pending count
    res = client.get("/api/faculty/verification-requests/count", headers=faculty_headers)
    assert res.status_code == 200
    assert res.json()["pending_count"] >= 1

    # 5. Faculty views the queue
    res = client.get("/api/faculty/verification-requests?status=pending", headers=faculty_headers)
    assert res.status_code == 200
    queue = res.json()
    assert any(item["id"] == req_id for item in queue)

    # 6. Faculty approves the request
    res = client.post(
        f"/api/faculty/verification-requests/{req_id}/review",
        json={"action": "approve", "feedback": "Lab code verified and rubric satisfied"},
        headers=faculty_headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "approved"

    # 7. Verify that the student skill is now verified
    db = TestingSessionLocal()
    student = db.query(Student).filter(Student.user_id == student_user.id).first()
    fastapi_link = db.get(StudentSkill, (student.id, fastapi_skill.id))
    assert fastapi_link.verified is True
    assert fastapi_link.verified_by == faculty_user.id
    db.close()
