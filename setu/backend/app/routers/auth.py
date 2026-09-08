from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import cache_user, create_token, current_user, hash_password, verify_password
from ..db import get_db
from ..models import Batch, Company, Student, User
from ..schemas import LoginIn, RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def user_out(user: User) -> UserOut:
    return UserOut(id=user.id, email=user.email, full_name=user.full_name, role=user.role)


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User.id).where(User.email == body.email)):
        raise HTTPException(409, "An account with this email already exists")

    if body.role == "student":
        if body.batch_id is None or not body.roll_number:
            raise HTTPException(422, "Students must pick a batch and give a roll number")
        if db.get(Batch, body.batch_id) is None:
            raise HTTPException(404, "Batch not found")
    if body.role == "recruiter" and not body.company_name:
        raise HTTPException(422, "Recruiters must give a company name")

    user = User(email=body.email, password_hash=hash_password(body.password), role=body.role, full_name=body.full_name)
    db.add(user)
    db.flush()

    if body.role == "student":
        db.add(Student(user_id=user.id, batch_id=body.batch_id, roll_number=body.roll_number))
    elif body.role == "recruiter":
        db.add(Company(name=body.company_name, recruiter_user_id=user.id))
    db.commit()
    cache_user(user)
    return TokenOut(access_token=create_token(user), user=user_out(user))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Wrong email or password")
    cache_user(user)
    return TokenOut(access_token=create_token(user), user=user_out(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user_out(user)
