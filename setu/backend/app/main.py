from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .config import CORS_ORIGINS
from .db import Base, engine
from .routers import auth, faculty, recruiters, skills, students

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Setu API",
    version="1.0.0",
    description="Skill-mapping and placement platform. Students, placement coordinators and recruiters share one matching engine.",
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (auth.router, skills.router, students.router, faculty.router, recruiters.router):
    app.include_router(router, prefix="/api")


@app.get("/api/health", tags=["reference"])
def health():
    return {"status": "ok"}
