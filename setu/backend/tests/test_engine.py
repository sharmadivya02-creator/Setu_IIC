"""Tests for the matching engine.

The engine is a pure function, so these tests need no database, no server and
no network -- plain dictionaries in, numbers out. That is the practical payoff
of keeping engine.py free of imports from the rest of the app.

Run with:
    pip install pytest
    python -m pytest tests/ -v
"""

import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

from app.engine import ADJACENT_CREDIT_CAP, Held, Requirement, cohort_gaps, learn_next, score_student  # noqa: E402

# Skill ids used across the tests
PYTHON, FASTAPI, POSTGRES, DOCKER, MYSQL, REACT, VUE = 1, 2, 3, 4, 5, 6, 7

BACKEND_ROLE = [
    Requirement(PYTHON, "Python", 3, "must_have"),
    Requirement(FASTAPI, "FastAPI", 2, "must_have"),
    Requirement(POSTGRES, "PostgreSQL", 3, "must_have"),
    Requirement(DOCKER, "Docker", 2, "nice_to_have"),
]

NAMES = {PYTHON: "Python", FASTAPI: "FastAPI", POSTGRES: "PostgreSQL", DOCKER: "Docker", MYSQL: "MySQL", REACT: "React", VUE: "Vue"}


def test_empty_requirements_scores_zero():
    assert score_student({}, []).score == 0.0


def test_worked_example_matches_documented_score():
    """The example printed in the project guide must stay true."""
    held = {
        PYTHON: Held(level=4, verified=True),
        FASTAPI: Held(level=2, verified=False),
        DOCKER: Held(level=1, verified=False),
    }
    result = score_student(held, BACKEND_ROLE)

    # Python 3.0 + FastAPI 3.0 + PostgreSQL 0.0 + Docker 0.5 = 6.5 of weight 10
    assert result.score == 65.0
    assert {row["skill"] for row in result.matched} == {"Python", "FastAPI"}
    assert [row["skill"] for row in result.below_level] == ["Docker"]
    assert [row["skill"] for row in result.missing] == ["PostgreSQL"]


def test_meeting_the_bar_is_full_credit_not_more():
    """A level 5 student and a level 3 student both fully satisfy a level 3 need."""
    exactly = score_student({PYTHON: Held(3, False)}, [Requirement(PYTHON, "Python", 3, "must_have")])
    far_above = score_student({PYTHON: Held(5, False)}, [Requirement(PYTHON, "Python", 3, "must_have")])
    assert exactly.score == far_above.score == 100.0


def test_verified_bonus_cannot_exceed_full_credit():
    """Verification adds 10% but is still capped at 1.0 credit."""
    result = score_student({PYTHON: Held(3, True)}, [Requirement(PYTHON, "Python", 3, "must_have")])
    assert result.score == 100.0


def test_verified_bonus_helps_a_below_level_skill():
    """At level 2 of 4 required, raw credit 0.5 becomes 0.55 when verified."""
    plain = score_student({PYTHON: Held(2, False)}, [Requirement(PYTHON, "Python", 4, "must_have")])
    verified = score_student({PYTHON: Held(2, True)}, [Requirement(PYTHON, "Python", 4, "must_have")])
    assert plain.score == 50.0
    assert verified.score == 55.0
    assert verified.verified_bonus == 5.0


def test_must_have_weighs_three_times_nice_to_have():
    reqs = [Requirement(PYTHON, "Python", 3, "must_have"), Requirement(DOCKER, "Docker", 3, "nice_to_have")]
    only_must = score_student({PYTHON: Held(3, False)}, reqs)
    only_nice = score_student({DOCKER: Held(3, False)}, reqs)
    assert only_must.score == 75.0  # 3 of 4 weight
    assert only_nice.score == 25.0  # 1 of 4 weight


# --- transferable skill credit -------------------------------------------------


def test_empty_adjacency_changes_nothing():
    """Regression guard: the feature must be invisible when the graph is empty."""
    held = {PYTHON: Held(4, True), FASTAPI: Held(2, False), DOCKER: Held(1, False)}
    before = score_student(held, BACKEND_ROLE)
    after = score_student(held, BACKEND_ROLE, adjacency={}, skill_names=NAMES)
    assert before.score == after.score == 65.0
    assert after.related == []
    assert after.related_credit == 0.0


def test_related_skill_earns_partial_credit():
    """Knowing MySQL should partly cover a PostgreSQL requirement."""
    held = {
        PYTHON: Held(4, True),
        FASTAPI: Held(2, False),
        DOCKER: Held(1, False),
        MYSQL: Held(4, False),
    }
    adjacency = {POSTGRES: {MYSQL: 0.8}}
    result = score_student(held, BACKEND_ROLE, adjacency, NAMES)

    # 0.4 cap x 0.8 similarity x min(1, 4/3) level factor = 0.32 credit
    # 6.5 (baseline) + 0.32 x weight 3 = 7.46 of weight 10
    assert result.score == 74.6
    assert result.related_credit == 9.6
    assert [row["skill"] for row in result.missing] == []

    row = result.related[0]
    assert row["skill"] == "PostgreSQL"
    assert row["via_skill"] == "MySQL"
    assert row["similarity"] == 0.8
    assert row["credit"] == 0.32


def test_related_credit_is_capped_well_below_a_real_match():
    """Even a perfect-similarity related skill is worth at most 40%."""
    reqs = [Requirement(REACT, "React", 3, "must_have")]
    real = score_student({REACT: Held(3, False)}, reqs, {REACT: {VUE: 1.0}}, NAMES)
    transferable = score_student({VUE: Held(5, False)}, reqs, {REACT: {VUE: 1.0}}, NAMES)
    assert real.score == 100.0
    assert transferable.score == ADJACENT_CREDIT_CAP * 100  # 40.0


def test_holding_the_real_skill_ignores_the_related_one():
    """Transferable credit never stacks on top of an actual match."""
    reqs = [Requirement(REACT, "React", 3, "must_have")]
    held = {REACT: Held(3, False), VUE: Held(5, False)}
    result = score_student(held, reqs, {REACT: {VUE: 0.9}}, NAMES)
    assert result.score == 100.0
    assert result.related == []


def test_only_the_best_related_skill_counts():
    """Several weak relations must not add up into a fake match."""
    reqs = [Requirement(POSTGRES, "PostgreSQL", 3, "must_have")]
    held = {MYSQL: Held(3, False), DOCKER: Held(3, False), VUE: Held(3, False)}
    adjacency = {POSTGRES: {MYSQL: 0.6, DOCKER: 0.5, VUE: 0.4}}
    result = score_student(held, reqs, adjacency, NAMES)
    assert len(result.related) == 1
    assert result.related[0]["via_skill"] == "MySQL"
    assert result.score == round(0.4 * 0.6 * 100, 1)  # 24.0


def test_related_credit_scales_with_how_well_you_know_the_other_skill():
    """A level 1 MySQL user transfers less than a level 4 MySQL user."""
    reqs = [Requirement(POSTGRES, "PostgreSQL", 4, "must_have")]
    adjacency = {POSTGRES: {MYSQL: 0.8}}
    weak = score_student({MYSQL: Held(1, False)}, reqs, adjacency, NAMES)
    strong = score_student({MYSQL: Held(4, False)}, reqs, adjacency, NAMES)
    assert weak.score < strong.score
    assert strong.score == 32.0  # 0.4 x 0.8 x 1.0
    assert weak.score == 8.0  # 0.4 x 0.8 x 0.25


def test_unheld_related_skill_gives_nothing():
    """The graph says MySQL is related, but the student does not have it."""
    reqs = [Requirement(POSTGRES, "PostgreSQL", 3, "must_have")]
    result = score_student({PYTHON: Held(5, True)}, reqs, {POSTGRES: {MYSQL: 0.9}}, NAMES)
    assert result.score == 0.0
    assert [row["skill"] for row in result.missing] == ["PostgreSQL"]


# --- the other two engine functions --------------------------------------------


def test_learn_next_ranks_by_score_lift():
    held = {PYTHON: Held(3, False)}
    postings = [BACKEND_ROLE]
    suggestions = learn_next(held, postings)
    # PostgreSQL and FastAPI are must-haves (weight 3), Docker is nice (weight 1)
    assert suggestions[0]["skill"] in {"PostgreSQL", "FastAPI"}
    assert suggestions[-1]["skill"] == "Docker"
    assert all(item["avg_score_lift"] > 0 for item in suggestions)


def test_learn_next_accounts_for_transferable_credit():
    """A skill already partly covered should show a smaller lift."""
    postings = [BACKEND_ROLE]
    without = learn_next({PYTHON: Held(3, False)}, postings)
    with_mysql = learn_next({PYTHON: Held(3, False), MYSQL: Held(4, False)}, postings, adjacency={POSTGRES: {MYSQL: 0.8}})

    lift_without = next(item["avg_score_lift"] for item in without if item["skill"] == "PostgreSQL")
    lift_with = next(item["avg_score_lift"] for item in with_mysql if item["skill"] == "PostgreSQL")
    assert lift_with < lift_without


def test_cohort_gaps_measures_demand_against_readiness():
    cohort = {
        1: {PYTHON: Held(4, False)},
        2: {PYTHON: Held(1, False)},
        3: {},
        4: {},
    }
    gaps = cohort_gaps(cohort, [BACKEND_ROLE], NAMES)
    python_gap = next(row for row in gaps if row["skill"] == "Python")

    assert python_gap["demand_pct"] == 100.0  # required by the only posting
    assert python_gap["held_pct"] == 50.0  # 2 of 4 students list it
    assert python_gap["ready_pct"] == 25.0  # only 1 of 4 is at level 3+
    assert python_gap["gap"] == 75.0
