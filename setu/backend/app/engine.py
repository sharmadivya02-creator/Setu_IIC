from dataclasses import dataclass, field

WEIGHTS = {"must_have": 3.0, "nice_to_have": 1.0}
VERIFIED_BONUS = 1.1


ADJACENT_CREDIT_CAP = 0.4


@dataclass
class Requirement:
    skill_id: int
    skill_name: str
    min_level: int
    importance: str


@dataclass
class Held:
    level: int
    verified: bool


@dataclass
class MatchResult:
    score: float
    matched: list[dict] = field(default_factory=list)
    below_level: list[dict] = field(default_factory=list)
    missing: list[dict] = field(default_factory=list)
    related: list[dict] = field(default_factory=list)
    verified_bonus: float = 0.0
    related_credit: float = 0.0
    weight_total: float = 0.0


def _best_transferable(
    req: Requirement,
    held_skills: dict[int, Held],
    adjacency: dict[int, dict[int, float]],
) -> dict | None:
    """Find the single best skill the student holds that is related to `req`.

    Only one related skill is ever counted. Stacking several weak relations
    would let a student fake a match out of loosely-connected skills, so the
    best one wins and the rest are ignored.
    """
    neighbours = adjacency.get(req.skill_id)
    if not neighbours:
        return None

    best = None
    for related_id, similarity in neighbours.items():
        held = held_skills.get(related_id)
        if held is None:
            continue
        # Knowing a related skill only helps to the extent you actually know it.
        level_factor = min(1.0, held.level / req.min_level)
        credit = ADJACENT_CREDIT_CAP * similarity * level_factor
        if best is None or credit > best["credit"]:
            best = {
                "via_skill_id": related_id,
                "similarity": round(similarity, 3),
                "via_level": held.level,
                "credit": credit,
            }
    return best


def score_student(
    held_skills: dict[int, Held],
    requirements: list[Requirement],
    adjacency: dict[int, dict[int, float]] | None = None,
    skill_names: dict[int, str] | None = None,
) -> MatchResult:
    """Score one student against one posting's requirements.

    `adjacency` is an optional {skill_id: {related_skill_id: similarity}} map.
    When it is empty or omitted, scoring behaves exactly as it did before
    transferable-skill credit existed.

    `skill_names` is only used to label which held skill produced transferable
    credit, so the explanation can name it.
    """
    if not requirements:
        return MatchResult(score=0.0)

    adjacency = adjacency or {}
    names = dict(skill_names or {})
    for req in requirements:
        names.setdefault(req.skill_id, req.skill_name)

    weight_total = 0.0
    credit_total = 0.0
    bonus_total = 0.0
    related_total = 0.0
    matched, below_level, missing, related = [], [], [], []

    for req in requirements:
        weight = WEIGHTS[req.importance]
        weight_total += weight
        held = held_skills.get(req.skill_id)

        if held is None:
            transferable = _best_transferable(req, held_skills, adjacency)
            if transferable is not None:
                credit = transferable["credit"]
                credit_total += credit * weight
                related_total += credit * weight
                related.append({
                    "skill_id": req.skill_id,
                    "skill": req.skill_name,
                    "needed": req.min_level,
                    "importance": req.importance,
                    "via_skill_id": transferable["via_skill_id"],
                    "via_skill": names.get(transferable["via_skill_id"], f"skill {transferable['via_skill_id']}"),
                    "via_level": transferable["via_level"],
                    "similarity": transferable["similarity"],
                    "credit": round(credit, 3),
                })
                continue
            missing.append({
                "skill_id": req.skill_id,
                "skill": req.skill_name,
                "needed": req.min_level,
                "importance": req.importance,
            })
            continue

        raw_credit = min(1.0, held.level / req.min_level)
        credit = raw_credit
        if held.verified:
            credit = min(1.0, raw_credit * VERIFIED_BONUS)
            bonus_total += (credit - raw_credit) * weight
        credit_total += credit * weight

        entry = {
            "skill_id": req.skill_id,
            "skill": req.skill_name,
            "level": held.level,
            "needed": req.min_level,
            "importance": req.importance,
            "verified": held.verified,
            "credit": round(credit, 3),
        }
        if held.level >= req.min_level:
            matched.append(entry)
        else:
            below_level.append(entry)

    score = round(100.0 * credit_total / weight_total, 1)
    missing.sort(key=lambda item: (item["importance"] != "must_have", item["skill"]))
    related.sort(key=lambda item: item["credit"], reverse=True)
    return MatchResult(
        score=score,
        matched=matched,
        below_level=below_level,
        missing=missing,
        related=related,
        verified_bonus=round(100.0 * bonus_total / weight_total, 1),
        related_credit=round(100.0 * related_total / weight_total, 1),
        weight_total=weight_total,
    )


def cohort_gaps(
    cohort_skills: dict[int, dict[int, Held]],
    postings_requirements: list[list[Requirement]],
    skill_names: dict[int, str],
) -> list[dict]:
    student_count = len(cohort_skills)
    posting_count = len(postings_requirements)
    if student_count == 0 or posting_count == 0:
        return []

    demand_count: dict[int, int] = {}
    level_sum: dict[int, int] = {}
    for requirements in postings_requirements:
        for req in requirements:
            demand_count[req.skill_id] = demand_count.get(req.skill_id, 0) + 1
            level_sum[req.skill_id] = level_sum.get(req.skill_id, 0) + req.min_level

    gaps = []
    for skill_id, demanded_in in demand_count.items():
        typical_level = round(level_sum[skill_id] / demanded_in)
        holders = 0
        ready = 0
        for held_skills in cohort_skills.values():
            held = held_skills.get(skill_id)
            if held is None:
                continue
            holders += 1
            if held.level >= typical_level:
                ready += 1
        demand_pct = round(100.0 * demanded_in / posting_count, 1)
        held_pct = round(100.0 * holders / student_count, 1)
        ready_pct = round(100.0 * ready / student_count, 1)
        gaps.append({
            "skill_id": skill_id,
            "skill": skill_names.get(skill_id, str(skill_id)),
            "demand_pct": demand_pct,
            "held_pct": held_pct,
            "ready_pct": ready_pct,
            "typical_level": typical_level,
            "gap": round(demand_pct - ready_pct, 1),
        })

    gaps.sort(key=lambda item: item["gap"], reverse=True)
    return gaps


def learn_next(
    held_skills: dict[int, Held],
    postings_requirements: list[list[Requirement]],
    limit: int = 6,
    adjacency: dict[int, dict[int, float]] | None = None,
) -> list[dict]:
    """Rank the skills that would raise this student's average score the most.

    Adjacency matters here: a skill the student already gets transferable
    credit for produces a smaller lift than one they get nothing for, so
    learning suggestions automatically account for what is already partly
    covered.
    """
    if not postings_requirements:
        return []

    baseline = sum(score_student(held_skills, reqs, adjacency).score for reqs in postings_requirements)
    candidates: dict[int, Requirement] = {}
    for requirements in postings_requirements:
        for req in requirements:
            current = held_skills.get(req.skill_id)
            if current is not None and current.level >= req.min_level:
                continue
            previous = candidates.get(req.skill_id)
            if previous is None or req.min_level > previous.min_level:
                candidates[req.skill_id] = req

    suggestions = []
    for skill_id, req in candidates.items():
        trial = dict(held_skills)
        trial[skill_id] = Held(level=req.min_level, verified=False)
        lifted = sum(score_student(trial, reqs, adjacency).score for reqs in postings_requirements)
        demanded_in = sum(1 for reqs in postings_requirements if any(r.skill_id == skill_id for r in reqs))
        suggestions.append({
            "skill_id": skill_id,
            "skill": req.skill_name,
            "target_level": req.min_level,
            "demand_pct": round(100.0 * demanded_in / len(postings_requirements), 1),
            "avg_score_lift": round((lifted - baseline) / len(postings_requirements), 1),
        })

    suggestions.sort(key=lambda item: item["avg_score_lift"], reverse=True)
    return suggestions[:limit]
