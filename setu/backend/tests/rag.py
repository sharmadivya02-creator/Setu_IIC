"""Tests for the policy-document retrieval (RAG) helpers.

chunk_text and retrieve are pure functions -- no database, server or network
needed, same reasoning as test_engine.py. What retrieve() cannot be tested to
do is reach across companies, because it never touches the database at all;
the real multi-tenant guarantee lives in loaders.company_chunk_texts, which
is the only function that ever reads DocumentChunk rows and always filters by
company_id. The last test below documents that guarantee at the boundary
this module *can* verify: two separate chunk lists never bleed into each
other's results, because retrieve() only ever sees the list it is handed.

Run with:
    pip install pytest
    python -m pytest tests/ -v
"""

import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

from app.rag import chunk_text, retrieve  # noqa: E402

COMPANY_A_CHUNKS = [
    "Eligibility criteria: candidates must hold a minimum CGPA of 6.5 out of 10.",
    "Notice period: selected candidates must join within 30 days of the offer letter.",
    "Work authorization: this role is on-site in India and requires existing work authorization.",
]

COMPANY_B_CHUNKS = [
    "Eligibility criteria: candidates must hold a minimum CGPA of 8.0 out of 10, no backlogs allowed.",
    "Remote work policy: fully remote, open to candidates anywhere in the country.",
]


def test_chunk_text_splits_long_text_into_multiple_windows():
    text = " ".join(f"word{i}" for i in range(1000))
    chunks = chunk_text(text, chunk_words=350, overlap=60)
    assert len(chunks) > 1
    # every word in the original text shows up somewhere in the chunks
    covered = " ".join(chunks)
    assert "word0" in covered
    assert "word999" in covered


def test_chunk_text_short_text_is_a_single_chunk():
    assert chunk_text("Just one short policy line.") == ["Just one short policy line."]


def test_chunk_text_empty_input_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_retrieve_on_empty_corpus_returns_nothing():
    """Regression guard: a company with no uploaded documents must not crash,
    it must simply have nothing to retrieve -- same graceful-degradation
    pattern as an empty skill_similarity table or a missing GROQ_API_KEY."""
    assert retrieve([], "eligibility criteria", k=3) == []


def test_retrieve_ranks_the_relevant_chunk_first():
    results = retrieve(COMPANY_A_CHUNKS, "notice period joining timeline", k=3)
    assert len(results) > 0
    top_index, top_text, top_score = results[0]
    assert "notice period" in top_text.lower()
    assert top_score > 0


def test_retrieve_never_mixes_two_different_corpora():
    """The one property that actually matters for privacy: querying company
    A's chunks never surfaces text that only exists in company B's chunks,
    because retrieve() has no way to reach any chunk it was not directly
    handed. This is what keeps policy_check() safe -- it only ever calls
    retrieve() with loaders.company_chunk_texts(db, THIS recruiter's
    company_id)."""
    results_a = retrieve(COMPANY_A_CHUNKS, "eligibility criteria cgpa", k=5)
    texts_a = {text for _, text, _ in results_a}
    assert texts_a.issubset(set(COMPANY_A_CHUNKS))
    assert texts_a.isdisjoint(set(COMPANY_B_CHUNKS))


def test_retrieve_query_with_no_overlap_returns_nothing():
    results = retrieve(COMPANY_A_CHUNKS, "zzz nonexistent qqq term", k=3)
    assert results == []