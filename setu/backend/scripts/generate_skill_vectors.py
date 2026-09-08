
import ast
import json
import pathlib

BACKEND = pathlib.Path(__file__).resolve().parent.parent
MODEL_NAME = "all-MiniLM-L6-v2"
OUTPUT = BACKEND / "app" / "data" / "skill_vectors.json"


TEMPLATE = "{name}, a {category} skill used in software engineering and technology jobs"


def load_skill_taxonomy() -> dict[str, list[str]]:
   
    source = (BACKEND / "seed.py").read_text()
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "SKILLS" for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise SystemExit("Could not find a SKILLS dict in seed.py")


def build_sentences() -> dict[str, str]:
    sentences = {}
    for category, names in load_skill_taxonomy().items():
        for name in names:
            sentences[name] = TEMPLATE.format(name=name, category=category.lower())
    return sentences


def main() -> None:
    from sentence_transformers import SentenceTransformer

    sentences = build_sentences()
    names = list(sentences.keys())

    print(f"Loading model {MODEL_NAME} ...")
    model = SentenceTransformer(MODEL_NAME)

    print(f"Embedding {len(names)} skills ...")
    vectors = model.encode(
        [sentences[name] for name in names],
        normalize_embeddings=True,  # unit length, so cosine similarity == dot product
        show_progress_bar=False,
    )

    payload = {
        "model": MODEL_NAME,
        "dimensions": int(vectors.shape[1]),
        "normalized": True,
        "vectors": {name: [round(float(value), 6) for value in vector] for name, vector in zip(names, vectors)},
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload))
    print(f"Wrote {len(names)} vectors of {payload['dimensions']} dimensions to {OUTPUT}")


if __name__ == "__main__":
    main()
