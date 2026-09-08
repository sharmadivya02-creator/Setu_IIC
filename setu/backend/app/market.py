import re

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import MARKET_API_URL
from .models import Company, Posting, PostingSkill, Skill

MARKET_COMPANY = "Open Market (Arbeitnow)"

SKILL_PATTERNS = {
    "Python": r"\bpython\b",
    "Java": r"\bjava\b(?!script)",
    "JavaScript": r"\bjavascript\b|\bjs\b",
    "TypeScript": r"\btypescript\b",
    "Go": r"\bgolang\b|\bgo\b(?= developer| engineer| \()",
    "C++": r"\bc\+\+",
    "Rust": r"\brust\b",
    "Kotlin": r"\bkotlin\b",
    "Swift": r"\bswift\b",
    "SQL": r"\bsql\b",
    "PostgreSQL": r"\bpostgres(?:ql)?\b",
    "MySQL": r"\bmysql\b",
    "MongoDB": r"\bmongo(?:db)?\b",
    "Redis": r"\bredis\b",
    "React": r"\breact(?:\.?js)?\b",
    "Angular": r"\bangular\b",
    "Vue": r"\bvue(?:\.?js)?\b",
    "Next.js": r"\bnext\.?js\b",
    "Node.js": r"\bnode(?:\.?js)?\b",
    "Django": r"\bdjango\b",
    "FastAPI": r"\bfastapi\b",
    "Spring Boot": r"\bspring\b",
    "Docker": r"\bdocker\b",
    "Kubernetes": r"\bkubernetes\b|\bk8s\b",
    "AWS": r"\baws\b|\bamazon web services\b",
    "Azure": r"\bazure\b",
    "GCP": r"\bgcp\b|\bgoogle cloud\b",
    "Terraform": r"\bterraform\b",
    "CI/CD": r"\bci/cd\b|\bcontinuous integration\b|\bjenkins\b|\bgithub actions\b",
    "Linux": r"\blinux\b",
    "Git": r"\bgit\b",
    "REST APIs": r"\brest(?:ful)?\b",
    "GraphQL": r"\bgraphql\b",
    "Machine Learning": r"\bmachine learning\b|\bml\b",
    "Deep Learning": r"\bdeep learning\b|\bneural\b",
    "PyTorch": r"\bpytorch\b",
    "TensorFlow": r"\btensorflow\b",
    "Pandas": r"\bpandas\b",
    "Data Analysis": r"\bdata analy",
    "Apache Spark": r"\bspark\b",
    "Kafka": r"\bkafka\b",
    "Tailwind CSS": r"\btailwind\b",
    "HTML/CSS": r"\bhtml\b|\bcss\b",
    "Testing (pytest/Jest)": r"\bpytest\b|\bjest\b|\bunit test",
    "System Design": r"\bsystem design\b|\bdistributed systems\b",
    "Agile/Scrum": r"\bagile\b|\bscrum\b",
    "Communication": r"\bcommunication\b",
    "Flutter": r"\bflutter\b",
    "React Native": r"\breact native\b",
    "Figma": r"\bfigma\b",
    "Power BI": r"\bpower bi\b",
    "Tableau": r"\btableau\b",
    "Excel": r"\bexcel\b",
    "Selenium": r"\bselenium\b",
    "Cybersecurity": r"\bsecurity\b",
}


def market_company(db: Session) -> Company:
    company = db.scalar(select(Company).where(Company.name == MARKET_COMPANY))
    if company is None:
        company = Company(name=MARKET_COMPANY, website="https://www.arbeitnow.com")
        db.add(company)
        db.flush()
    return company


def fetch_market_jobs(limit: int = 40) -> list[dict]:
    response = httpx.get(MARKET_API_URL, timeout=20.0, follow_redirects=True)
    response.raise_for_status()
    return response.json().get("data", [])[:limit]


def extract_skills(text: str, skills_by_name: dict[str, Skill]) -> list[tuple[Skill, int, str]]:
    lowered = text.lower()
    found = []
    for skill_name, pattern in SKILL_PATTERNS.items():
        skill = skills_by_name.get(skill_name)
        if skill is None:
            continue
        hits = len(re.findall(pattern, lowered))
        if hits == 0:
            continue
        importance = "must_have" if hits >= 2 else "nice_to_have"
        min_level = 3 if importance == "must_have" else 2
        found.append((skill, min_level, importance))
    return found


def refresh_market_postings(db: Session) -> tuple[int, int]:
    skills_by_name = {skill.name: skill for skill in db.scalars(select(Skill))}
    company = market_company(db)
    existing_urls = set(db.scalars(select(Posting.external_url).where(Posting.source == "market")))

    imported = skipped = 0
    for job in fetch_market_jobs():
        url = job.get("url")
        text = " ".join([job.get("title", ""), re.sub(r"<[^>]+>", " ", job.get("description", "")), " ".join(job.get("tags", []))])
        requirements = extract_skills(text, skills_by_name)
        if not url or url in existing_urls or len(requirements) < 2:
            skipped += 1
            continue
        posting = Posting(
            company_id=company.id,
            title=f"{job.get('title', 'Role')} at {job.get('company_name', 'Unknown')}"[:160],
            kind="job",
            location=(job.get("location") or "Remote")[:120],
            description=re.sub(r"<[^>]+>", " ", job.get("description", ""))[:1500].strip(),
            source="market",
            active=True,
            external_url=url,
        )
        posting.required_skills = [
            PostingSkill(skill_id=skill.id, min_level=min_level, importance=importance)
            for skill, min_level, importance in requirements[:8]
        ]
        db.add(posting)
        existing_urls.add(url)
        imported += 1
    db.commit()
    return imported, skipped
