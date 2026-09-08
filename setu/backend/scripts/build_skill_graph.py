import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select  

from app.db import SessionLocal 
from app.models import Skill, SkillSimilarity 
from app.similarity import MIN_SIMILARITY, TOP_K, build_pairs, load_vectors  # noqa: E402


def main() -> None:
    vectors = load_vectors()
    if not vectors:
        print("No vectors found at app/data/skill_vectors.json")
        print("Generate them first:")
        print("    pip install sentence-transformers")
        print("    python scripts/generate_skill_vectors.py")
        return

    db = SessionLocal()
    try:
        skills_by_name = {name: skill_id for skill_id, name in db.execute(select(Skill.id, Skill.name))}
        if not skills_by_name:
            print("No skills in the database. Run: python seed.py")
            return

        unknown = sorted(set(vectors) - set(skills_by_name))
        if unknown:
            print(f"Note: {len(unknown)} vector(s) have no matching skill row and are ignored: {unknown[:5]}")

        pairs = build_pairs(vectors)

        db.execute(delete(SkillSimilarity))
        written = 0
        for name, other, score in pairs:
            left = skills_by_name.get(name)
            right = skills_by_name.get(other)
            if left is None or right is None:
                continue
            db.add(SkillSimilarity(skill_id=left, related_skill_id=right, similarity=score))
            written += 1
        db.commit()

        distinct = len({tuple(sorted((a, b))) for a, b, _ in pairs})
        print(f"Skill graph built with threshold {MIN_SIMILARITY} and top-{TOP_K} neighbours.")
        print(f"  {len(vectors)} skills embedded")
        print(f"  {distinct} related pairs found")
        print(f"  {written} rows written (both directions)")

        sample = sorted(pairs, key=lambda row: row[2], reverse=True)[:10]
        if sample:
            print("\nStrongest relationships found:")
            for name, other, score in sample:
                print(f"  {name:<28} <-> {other:<28} {score}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
