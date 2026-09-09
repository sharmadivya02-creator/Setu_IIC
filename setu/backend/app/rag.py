

import json
import math
import re
from collections import Counter

CHUNK_WORDS = 350
CHUNK_OVERLAP = 60

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def chunk_text(text: str, chunk_words: int = CHUNK_WORDS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping word-count windows.

    The overlap means a clause that happens to fall right at a chunk
    boundary still reads whole in at least one chunk, instead of being cut
    in half and losing its meaning in both halves.
    """
    words = text.split()
    if not words:
        return []
    chunks = []
    step = max(1, chunk_words - overlap)
    for start in range(0, len(words), step):
        window = " ".join(words[start : start + chunk_words])
        if window.strip():
            chunks.append(window.strip())
        if start + chunk_words >= len(words):
            break
    return chunks


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _tfidf_vectors(tokenized_docs: list[list[str]]) -> list[dict[str, float]]:
    """Plain TF-IDF: term frequency times inverse document frequency, unit-normalized.

    Standard smoothed IDF (as used by scikit-learn's default): log((N+1)/(df+1)) + 1,
    so a term appearing in every document still gets a small positive weight instead
    of collapsing to zero.
    """
    doc_count = len(tokenized_docs)
    document_frequency: Counter = Counter()
    for tokens in tokenized_docs:
        document_frequency.update(set(tokens))

    idf = {term: math.log((doc_count + 1) / (count + 1)) + 1 for term, count in document_frequency.items()}

    vectors = []
    for tokens in tokenized_docs:
        term_frequency = Counter(tokens)
        vector = {term: freq * idf[term] for term, freq in term_frequency.items()}
        length = math.sqrt(sum(weight * weight for weight in vector.values()))
        if length > 0:
            vector = {term: weight / length for term, weight in vector.items()}
        vectors.append(vector)
    return vectors


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if len(b) < len(a):
        a, b = b, a
    return sum(weight * b.get(term, 0.0) for term, weight in a.items())


def retrieve(chunks: list[str], query: str, k: int = 3) -> list[tuple[int, str, float]]:
    """Rank `chunks` by relevance to `query` using TF-IDF cosine similarity.

    Returns up to k (index, chunk_text, score) tuples, highest score first,
    excluding zero-score chunks entirely. Pure function -- it only ever sees
    what it is handed, so multi-tenant safety comes from the caller: the
    only place DocumentChunk rows are read is loaders.company_chunk_texts,
    which always filters by company_id. This function has no way to reach
    the database and mix chunks from two different companies.
    """
    if not chunks or not query.strip():
        return []

    tokenized = [_tokenize(chunk) for chunk in chunks]
    tokenized.append(_tokenize(query))
    vectors = _tfidf_vectors(tokenized)
    query_vector = vectors[-1]
    chunk_vectors = vectors[:-1]

    scored = [(index, chunks[index], _cosine(query_vector, vector)) for index, vector in enumerate(chunk_vectors)]
    scored = [item for item in scored if item[2] > 0]
    scored.sort(key=lambda item: item[2], reverse=True)
    return scored[:k]


POLICY_CATEGORIES = [
    "Eligibility criteria: CGPA cutoff, branch, or backlog rules",
    "Notice period or joining timeline",
    "Work authorization or work-location requirement",
    "Bond, service agreement, or stipend and salary terms",
]


def build_policy_prompt(
    posting_title: str,
    candidate_facts: dict,
    retrieved_by_category: dict[str, list[tuple[int, str, float]]],
) -> tuple[str, str]:
    """Build the system/user prompt pair for a policy-check Groq call.

    Only the text actually retrieved from the recruiter's own uploaded
    documents is ever included -- the model is explicitly told not to
    assume a policy exists when nothing was retrieved for a category.
    """
    context_blocks = []
    for category, matches in retrieved_by_category.items():
        if matches:
            excerpt_lines = "\n".join(f"  - (chunk #{index}) {text}" for index, text, _score in matches)
        else:
            excerpt_lines = "  - no matching policy text was found for this category"
        context_blocks.append(f"CATEGORY: {category}\n{excerpt_lines}")
    context = "\n\n".join(context_blocks)

    system_prompt = (
        "You are a compliance assistant helping a recruiter cross-check ONE candidate against "
        "their own company's uploaded policy documents.\n\n"
        "CRITICAL RULES:\n"
        "1. Base every verdict ONLY on the policy excerpts provided below. Never invent or assume a policy that was not given to you.\n"
        "2. If no excerpt is relevant to a category, the verdict MUST be 'unclear', with evidence_snippet explaining that no matching policy text was found.\n"
        "3. This is informational only. You are not rejecting or approving anyone, and must never phrase a verdict as a final decision.\n"
        "4. verdict must be exactly one of: 'compliant', 'not_compliant', 'unclear'.\n"
        "5. Output MUST be valid JSON with exactly one top-level key 'verdicts': an array of objects shaped "
        '{"rule": string, "verdict": string, "evidence_snippet": string, "source_chunk_id": integer or null}.\n'
        "6. Output only JSON, no markdown fences."
    )

    user_prompt = (
        f"JOB POSTING: {posting_title}\n\n"
        f"CANDIDATE FACTS:\n{json.dumps(candidate_facts)}\n\n"
        f"RETRIEVED POLICY EXCERPTS (grouped by category, best match first):\n{context}\n\n"
        "Produce exactly one verdict object for each category listed above."
    )

    return system_prompt, user_prompt