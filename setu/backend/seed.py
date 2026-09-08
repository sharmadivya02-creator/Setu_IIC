import random

from sqlalchemy import delete

from app.auth import hash_password
from app.db import SessionLocal
from app.market import refresh_market_postings
from app.models import (
    Application,
    Batch,
    College,
    Company,
    Posting,
    PostingSkill,
    Skill,
    SkillSimilarity,
    Student,
    StudentSkill,
    User,
)
from app.similarity import build_pairs, load_vectors

random.seed(42)

DEMO_PASSWORD = "setu1234"

SKILLS = {
    "Languages": ["Python", "Java", "JavaScript", "TypeScript", "C++", "C", "Go", "Rust", "Kotlin", "Swift", "SQL", "Bash"],
    "Backend": ["FastAPI", "Django", "Flask", "Node.js", "Express", "Spring Boot", "REST APIs", "GraphQL", "gRPC", "WebSockets", "Authentication/JWT"],
    "Frontend": ["React", "Next.js", "Vue", "Angular", "HTML/CSS", "Tailwind CSS", "Redux", "Responsive Design", "Accessibility", "Figma"],
    "Data": ["PostgreSQL", "MySQL", "MongoDB", "Redis", "Pandas", "NumPy", "Data Analysis", "Machine Learning", "Deep Learning", "PyTorch", "TensorFlow", "Scikit-learn", "Apache Spark", "Kafka", "Power BI", "Tableau", "Excel", "Statistics"],
    "Cloud": ["Docker", "Kubernetes", "AWS", "Azure", "GCP", "Terraform", "CI/CD", "Linux", "Nginx", "Monitoring/Grafana", "Serverless"],
    "Mobile": ["Flutter", "React Native", "Android (Kotlin)", "iOS (Swift)"],
    "Practices": ["Git", "Testing (pytest/Jest)", "System Design", "Data Structures & Algorithms", "OOP", "Design Patterns", "Agile/Scrum", "Selenium", "Cybersecurity", "Networking Basics", "Operating Systems"],
    "Soft": ["Communication", "Teamwork", "Problem Solving", "Presentation", "Technical Writing", "Leadership"],
}

FIRST_NAMES = [
    "Aarav", "Ananya", "Vihaan", "Diya", "Arjun", "Ishita", "Kabir", "Meera", "Rohan", "Sneha", "Aditya", "Priya", "Karan", "Nisha", "Rahul",
    "Pooja", "Siddharth", "Riya", "Manish", "Kavya", "Yash", "Tanvi", "Nikhil", "Shreya", "Varun", "Aisha", "Dev", "Sana", "Harsh", "Neha",
    "Om", "Zara", "Parth", "Kritika", "Aman", "Simran", "Rishi", "Anjali", "Tushar", "Bhavya", "Sahil", "Mansi", "Ayush", "Jhanvi", "Vivek",
    "Aditi", "Rajat", "Mahima", "Kunal", "Divya", "Naman", "Ira", "Pranav", "Nandini", "Utkarsh", "Sakshi", "Mohit", "Palak", "Gaurav", "Tara",
]
LAST_NAMES = ["Sharma", "Verma", "Gupta", "Singh", "Patel", "Reddy", "Nair", "Iyer", "Khan", "Mehta", "Joshi", "Das", "Bose", "Rao", "Kulkarni", "Mishra", "Yadav", "Chauhan", "Malhotra", "Saxena"]

ARCHETYPES = {
    "backend": (["Python", "SQL", "PostgreSQL", "REST APIs", "Git", "FastAPI", "Django", "Docker", "Linux", "Redis", "Authentication/JWT", "Testing (pytest/Jest)", "Data Structures & Algorithms", "OOP"], 0.35),
    "frontend": (["JavaScript", "TypeScript", "React", "HTML/CSS", "Tailwind CSS", "Git", "Next.js", "Redux", "Responsive Design", "Figma", "REST APIs", "Node.js", "Accessibility"], 0.2),
    "data": (["Python", "Pandas", "NumPy", "SQL", "Machine Learning", "Statistics", "Data Analysis", "Scikit-learn", "Excel", "Deep Learning", "PyTorch", "Power BI", "Git"], 0.2),
    "java": (["Java", "Spring Boot", "SQL", "MySQL", "OOP", "Design Patterns", "Data Structures & Algorithms", "Git", "REST APIs", "System Design", "Testing (pytest/Jest)"], 0.15),
    "beginner": (["C", "C++", "Python", "HTML/CSS", "Git", "Excel", "Communication", "Data Structures & Algorithms"], 0.1),
}

COMMON_SOFT = ["Communication", "Teamwork", "Problem Solving", "Presentation"]

COMPANIES = [
    ("Infosys", "https://www.infosys.com"), ("Tata Consultancy Services", "https://www.tcs.com"), ("Zomato", "https://www.zomato.com"),
    ("Razorpay", "https://razorpay.com"), ("Google", "https://careers.google.com"), ("Microsoft", "https://careers.microsoft.com"),
    ("Amazon", "https://www.amazon.jobs"), ("Flipkart", "https://www.flipkartcareers.com"), ("Deloitte", "https://www.deloitte.com"),
    ("Swiggy", "https://careers.swiggy.com"), ("Atlassian", "https://www.atlassian.com/company/careers"), ("Zoho", "https://www.zoho.com/careers"),
]

POSTINGS = [
    ("Backend Engineer Intern", "internship", "Bengaluru", [("Python", 3, "must_have"), ("FastAPI", 2, "must_have"), ("PostgreSQL", 3, "must_have"), ("Docker", 2, "nice_to_have"), ("Git", 3, "must_have"), ("REST APIs", 3, "must_have")]),
    ("Software Engineer I", "job", "Hyderabad", [("Java", 4, "must_have"), ("Spring Boot", 3, "must_have"), ("SQL", 3, "must_have"), ("System Design", 2, "nice_to_have"), ("Data Structures & Algorithms", 4, "must_have"), ("Docker", 2, "nice_to_have")]),
    ("Frontend Developer", "job", "Remote", [("React", 4, "must_have"), ("TypeScript", 3, "must_have"), ("HTML/CSS", 4, "must_have"), ("Tailwind CSS", 3, "nice_to_have"), ("Git", 3, "must_have"), ("Testing (pytest/Jest)", 2, "nice_to_have")]),
    ("Data Analyst Intern", "internship", "Pune", [("SQL", 3, "must_have"), ("Pandas", 3, "must_have"), ("Excel", 3, "must_have"), ("Statistics", 3, "must_have"), ("Power BI", 2, "nice_to_have"), ("Communication", 3, "nice_to_have")]),
    ("Machine Learning Engineer", "job", "Bengaluru", [("Python", 4, "must_have"), ("Machine Learning", 4, "must_have"), ("PyTorch", 3, "must_have"), ("Docker", 3, "must_have"), ("AWS", 2, "nice_to_have"), ("Statistics", 3, "must_have")]),
    ("DevOps Engineer", "job", "Chennai", [("Docker", 4, "must_have"), ("Kubernetes", 3, "must_have"), ("Linux", 4, "must_have"), ("CI/CD", 3, "must_have"), ("AWS", 3, "must_have"), ("Terraform", 2, "nice_to_have"), ("Bash", 3, "nice_to_have")]),
    ("Full Stack Developer Intern", "internship", "Remote", [("JavaScript", 3, "must_have"), ("React", 3, "must_have"), ("Node.js", 3, "must_have"), ("MongoDB", 2, "must_have"), ("Git", 3, "must_have"), ("Docker", 2, "nice_to_have")]),
    ("Cloud Support Associate", "job", "Hyderabad", [("Linux", 3, "must_have"), ("AWS", 3, "must_have"), ("Networking Basics", 3, "must_have"), ("Bash", 2, "nice_to_have"), ("Communication", 4, "must_have")]),
    ("Android Developer", "job", "Gurugram", [("Kotlin", 4, "must_have"), ("Android (Kotlin)", 4, "must_have"), ("REST APIs", 3, "must_have"), ("Git", 3, "must_have"), ("Figma", 2, "nice_to_have")]),
    ("Data Engineer", "job", "Bengaluru", [("Python", 4, "must_have"), ("SQL", 4, "must_have"), ("Apache Spark", 3, "must_have"), ("Kafka", 2, "nice_to_have"), ("Docker", 3, "must_have"), ("AWS", 3, "nice_to_have")]),
    ("QA Automation Intern", "internship", "Noida", [("Selenium", 3, "must_have"), ("Python", 3, "must_have"), ("Testing (pytest/Jest)", 3, "must_have"), ("Git", 2, "must_have"), ("Agile/Scrum", 2, "nice_to_have")]),
    ("Backend Developer (Go)", "job", "Remote", [("Go", 4, "must_have"), ("PostgreSQL", 3, "must_have"), ("Docker", 3, "must_have"), ("gRPC", 2, "nice_to_have"), ("Kubernetes", 2, "nice_to_have"), ("System Design", 3, "must_have")]),
    ("Product Analyst", "job", "Mumbai", [("SQL", 4, "must_have"), ("Data Analysis", 4, "must_have"), ("Excel", 4, "must_have"), ("Tableau", 3, "nice_to_have"), ("Presentation", 3, "must_have"), ("Statistics", 3, "must_have")]),
    ("Platform Engineer Intern", "internship", "Bengaluru", [("Docker", 3, "must_have"), ("Linux", 3, "must_have"), ("Python", 3, "must_have"), ("CI/CD", 2, "must_have"), ("Monitoring/Grafana", 2, "nice_to_have"), ("Git", 3, "must_have")]),
    ("React Native Developer", "job", "Remote", [("React Native", 4, "must_have"), ("JavaScript", 4, "must_have"), ("TypeScript", 3, "nice_to_have"), ("REST APIs", 3, "must_have"), ("Git", 3, "must_have")]),
    ("AI Research Intern", "internship", "Bengaluru", [("Python", 4, "must_have"), ("Deep Learning", 4, "must_have"), ("PyTorch", 4, "must_have"), ("Statistics", 3, "must_have"), ("Technical Writing", 2, "nice_to_have")]),
    ("Site Reliability Engineer", "job", "Pune", [("Linux", 4, "must_have"), ("Kubernetes", 4, "must_have"), ("Docker", 4, "must_have"), ("Monitoring/Grafana", 3, "must_have"), ("Go", 2, "nice_to_have"), ("Python", 3, "must_have"), ("Networking Basics", 3, "must_have")]),
    ("Junior Java Developer", "job", "Kolkata", [("Java", 3, "must_have"), ("OOP", 4, "must_have"), ("SQL", 3, "must_have"), ("Spring Boot", 2, "nice_to_have"), ("Git", 2, "must_have"), ("Design Patterns", 2, "nice_to_have")]),
    ("Security Analyst Intern", "internship", "Hyderabad", [("Cybersecurity", 3, "must_have"), ("Networking Basics", 3, "must_have"), ("Linux", 3, "must_have"), ("Python", 2, "nice_to_have"), ("Operating Systems", 3, "must_have")]),
    ("Frontend Intern (Vue)", "internship", "Remote", [("Vue", 3, "must_have"), ("JavaScript", 3, "must_have"), ("HTML/CSS", 3, "must_have"), ("Git", 2, "must_have"), ("Responsive Design", 3, "must_have")]),
    ("Business Intelligence Developer", "job", "Mumbai", [("SQL", 4, "must_have"), ("Power BI", 4, "must_have"), ("Data Analysis", 3, "must_have"), ("Excel", 3, "must_have"), ("Python", 2, "nice_to_have")]),
    ("Software Development Engineer", "job", "Bengaluru", [("Data Structures & Algorithms", 5, "must_have"), ("System Design", 3, "must_have"), ("Java", 4, "must_have"), ("AWS", 2, "nice_to_have"), ("Docker", 2, "nice_to_have"), ("Problem Solving", 4, "must_have")]),
    ("Python Developer", "job", "Remote", [("Python", 4, "must_have"), ("Django", 3, "must_have"), ("PostgreSQL", 3, "must_have"), ("Redis", 2, "nice_to_have"), ("Docker", 3, "must_have"), ("Testing (pytest/Jest)", 3, "must_have")]),
    ("Cloud Engineer Intern", "internship", "Chennai", [("AWS", 3, "must_have"), ("Docker", 3, "must_have"), ("Terraform", 2, "must_have"), ("Linux", 3, "must_have"), ("Python", 2, "nice_to_have"), ("Serverless", 2, "nice_to_have")]),
    ("Data Science Intern", "internship", "Gurugram", [("Python", 3, "must_have"), ("Pandas", 3, "must_have"), ("Scikit-learn", 3, "must_have"), ("Machine Learning", 3, "must_have"), ("SQL", 2, "must_have"), ("Communication", 3, "nice_to_have")]),
]

BATCHES = ["CSE 2026", "IT 2026", "ECE 2026", "CSE 2027"]


def wipe(db):
    for table in (Application, PostingSkill, Posting, StudentSkill, Student, Company, Batch, College, Skill, User):
        db.execute(delete(table))
    db.commit()


def make_students(db, batches, skills_by_name):
    students = []
    archetype_names = list(ARCHETYPES)
    archetype_weights = [ARCHETYPES[name][1] for name in archetype_names]
    used_names = set()
    for index in range(60):
        while True:
            full_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            if full_name not in used_names:
                used_names.add(full_name)
                break
        archetype = random.choices(archetype_names, archetype_weights)[0]
        core_skills, _ = ARCHETYPES[archetype]
        batch = batches[index % len(batches)]
        email = f"{full_name.lower().replace(' ', '.')}{index}@student.setu.demo"
        user = User(email=email, password_hash=hash_password(DEMO_PASSWORD), role="student", full_name=full_name)
        db.add(user)
        db.flush()
        student = Student(
            user_id=user.id,
            batch_id=batch.id,
            roll_number=f"{batch.name.split()[0]}{batch.name.split()[1][2:]}{index + 1:03d}",
            cgpa=round(random.uniform(6.0, 9.6), 2),
            github_url=f"https://github.com/{full_name.split()[0].lower()}{index}",
        )
        db.add(student)
        db.flush()

        chosen = random.sample(core_skills, k=min(len(core_skills), random.randint(5, 9)))
        chosen += random.sample(COMMON_SOFT, k=random.randint(1, 3))
        strength = {"beginner": (1, 3), "backend": (2, 5), "frontend": (2, 5), "data": (2, 5), "java": (2, 5)}[archetype]
        for skill_name in set(chosen):
            level = random.randint(*strength)
            db.add(StudentSkill(student_id=student.id, skill_id=skills_by_name[skill_name].id, level=level, verified=random.random() < 0.3))
        students.append(student)
    return students


def run():
    db = SessionLocal()
    wipe(db)

    skills_by_name = {}
    for category, names in SKILLS.items():
        for name in names:
            skill = Skill(name=name, category=category)
            db.add(skill)
            skills_by_name[name] = skill
    db.flush()

    college = College(name="NIT Allahabad")
    db.add(college)
    db.flush()
    batches = [Batch(college_id=college.id, name=name) for name in BATCHES]
    db.add_all(batches)
    db.flush()

    faculty_user = User(email="faculty@setu.demo", password_hash=hash_password(DEMO_PASSWORD), role="faculty", full_name="Dr. Kavita Rao")
    db.add(faculty_user)

    companies = []
    for name, website in COMPANIES:
        company = Company(name=name, website=website)
        db.add(company)
        companies.append(company)
    db.flush()

    recruiter_user = User(email="recruiter@setu.demo", password_hash=hash_password(DEMO_PASSWORD), role="recruiter", full_name="Arjun Menon")
    db.add(recruiter_user)
    db.flush()
    companies[3].recruiter_user_id = recruiter_user.id

    postings = []
    for index, (title, kind, location, requirements) in enumerate(POSTINGS):
        company = companies[3] if index < 4 else companies[index % len(companies)]
        posting = Posting(
            company_id=company.id,
            title=title,
            kind=kind,
            location=location,
            description=f"Sample posting for demo purposes. {company.name} is hiring a {title} in {location}. Requirements are listed as skill tags with minimum levels.",
            source="internal",
            active=True,
        )
        posting.required_skills = [
            PostingSkill(skill_id=skills_by_name[skill_name].id, min_level=level, importance=importance)
            for skill_name, level, importance in requirements
        ]
        db.add(posting)
        postings.append(posting)
    db.flush()

    students = make_students(db, batches, skills_by_name)

    demo_user = User(email="student@setu.demo", password_hash=hash_password(DEMO_PASSWORD), role="student", full_name="Shivam Kumar")
    db.add(demo_user)
    db.flush()
    demo_student = Student(user_id=demo_user.id, batch_id=batches[0].id, roll_number="CSE26000", cgpa=8.4, github_url="https://github.com/shivam", phone="+91 98765 43210")
    db.add(demo_student)
    db.flush()
    for skill_name, level, verified in [("Python", 4, True), ("SQL", 3, True), ("PostgreSQL", 3, False), ("REST APIs", 3, False), ("Git", 4, True), ("FastAPI", 2, False), ("React", 2, False), ("Data Structures & Algorithms", 3, True), ("Communication", 4, False), ("Pandas", 2, False)]:
        db.add(StudentSkill(student_id=demo_student.id, skill_id=skills_by_name[skill_name].id, level=level, verified=verified, verified_by=faculty_user.id if verified else None))

    statuses = ["applied", "applied", "applied", "shortlisted", "interview", "rejected", "offered"]
    for posting in postings[:10]:
        for student in random.sample(students, k=random.randint(3, 8)):
            db.add(Application(student_id=student.id, posting_id=posting.id, status=random.choice(statuses)))
    db.add(Application(student_id=demo_student.id, posting_id=postings[0].id, status="shortlisted"))
    db.add(Application(student_id=demo_student.id, posting_id=postings[22].id, status="applied"))
    db.commit()

    try:
        imported, skipped = refresh_market_postings(db)
        print(f"market postings imported: {imported} (skipped {skipped})")
    except Exception as error:
        print(f"market import skipped, no network or API down: {error}")

    # Build the skill similarity graph if embedding vectors are present.
    # Absent vectors are not an error: scoring simply runs without
    # transferable-skill credit, exactly as it did before that feature existed.
    vectors = load_vectors()
    if vectors:
        pairs = build_pairs(vectors)
        db.execute(delete(SkillSimilarity))
        for name, other, score in pairs:
            left, right = skills_by_name.get(name), skills_by_name.get(other)
            if left is not None and right is not None:
                db.add(SkillSimilarity(skill_id=left.id, related_skill_id=right.id, similarity=score))
        db.commit()
        print(f"skill graph: {len({tuple(sorted((a, b))) for a, b, _ in pairs})} related pairs")
    else:
        print("skill graph: no vectors found, transferable-skill credit is off")
        print("  to enable: pip install sentence-transformers")
        print("             python scripts/generate_skill_vectors.py")

    print(f"skills: {len(skills_by_name)}")
    print(f"students: {len(students) + 1}, postings: {len(postings)}")
    print("logins: student@setu.demo / faculty@setu.demo / recruiter@setu.demo, password setu1234")
    db.close()


if __name__ == "__main__":
    run()
