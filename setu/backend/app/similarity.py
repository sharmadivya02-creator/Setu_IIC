import json
import math
import pathlib

VECTOR_FILE = pathlib.Path(__file__).resolve().parent / "data" / "skill_vectors.json"


MIN_SIMILARITY = 0.35


TOP_K = 8


def load_vectors() -> dict[str, list[float]]:

    if not VECTOR_FILE.exists():
        return {}
    payload = json.loads(VECTOR_FILE.read_text())
    return payload.get("vectors", {})


def mean_centre(vectors: dict[str, list[float]]) -> dict[str, list[float]]:
    """Subtract the average vector, then rescale each result to unit length."""
    if not vectors:
        return {}

    names = list(vectors)
    dimensions = len(vectors[names[0]])
    count = len(names)

    centre = [0.0] * dimensions
    for vector in vectors.values():
        for index, value in enumerate(vector):
            centre[index] += value
    centre = [value / count for value in centre]

    centred = {}
    for name, vector in vectors.items():
        shifted = [value - centre[index] for index, value in enumerate(vector)]
        length = math.sqrt(sum(value * value for value in shifted))
        if length == 0:
            continue
        centred[name] = [value / length for value in shifted]
    return centred


def cosine(a: list[float], b: list[float]) -> float:
   
    return sum(x * y for x, y in zip(a, b))


def build_pairs(
    vectors: dict[str, list[float]],
    min_similarity: float = MIN_SIMILARITY,
    top_k: int = TOP_K,
) -> list[tuple[str, str, float]]:
   
    centred = mean_centre(vectors)
    names = sorted(centred)

    neighbours: dict[str, list[tuple[str, float]]] = {name: [] for name in names}
    for i, left in enumerate(names):
        for right in names[i + 1:]:
            score = cosine(centred[left], centred[right])
            if score < min_similarity:
                continue
            neighbours[left].append((right, score))
            neighbours[right].append((left, score))

    rows = []
    for name, related in neighbours.items():
        related.sort(key=lambda item: item[1], reverse=True)
        for other, score in related[:top_k]:
            rows.append((name, other, round(score, 4)))
    return rows