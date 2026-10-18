"""Transparent demo estimates, not a trained or calibrated knowledge model."""

from api.catalog import BY_ID, CONCEPT_IDS
from api.practice_policy import PracticePolicy


def first_attempts(history: list[dict]) -> list[dict]:
    """Use the first encounter only; successful retries must not inflate evidence."""
    seen = set()
    primary = []
    for item in sorted(history, key=lambda row: row["sequence_index"]):
        if item["problem_id"] not in seen:
            seen.add(item["problem_id"])
            if item["attempt_number"] == 1:
                primary.append(item)
    return primary


def concept_profile(history: list[dict]) -> list[dict]:
    primary = first_attempts(history)
    concepts = []
    for concept in CONCEPT_IDS:
        evidence = [row for row in primary if concept in BY_ID[row["problem_id"]]["concept_ids"]]
        concepts.append({
            "concept_id": concept,
            "estimated_performance": (1 + sum(row["correct"] for row in evidence)) / (2 + len(evidence)),
            "supporting_attempts": len(evidence),
            "supporting_problem_ids": [row["problem_id"] for row in evidence],
            # Evidence-volume labels, not calibrated confidence levels.
            "evidence_status": "no-history" if not evidence else "limited-history" if len(evidence) < 3 else "observed-first-attempt",
        })
    return concepts


def estimate(history: list[dict], candidate_ids: list[str]) -> list[dict]:
    profile = {row["concept_id"]: row["estimated_performance"] for row in concept_profile(history)}
    return [{"problem_id": candidate, "predicted_correctness": round(sum(profile[c] for c in BY_ID[candidate]["concept_ids"]) / len(BY_ID[candidate]["concept_ids"]), 6)} for candidate in candidate_ids]


def recommend(history: list[dict], policy: PracticePolicy | None = None) -> list[dict]:
    """Rank a declared challenge range, observable concept need and novelty."""
    policy = PracticePolicy() if policy is None else policy
    if not isinstance(policy, PracticePolicy):
        raise ValueError("PracticePolicy is required")
    policy = PracticePolicy.model_validate(policy.model_dump())
    attempted = {row["problem_id"] for row in history}
    profile = {row["concept_id"]: row for row in concept_profile(history)}
    recommendations = []
    for prediction in estimate(history, list(BY_ID)):
        exercise = BY_ID[prediction["problem_id"]]
        probability = prediction["predicted_correctness"]
        weak = [c for c in exercise["prerequisites"] if profile[c]["estimated_performance"] < policy.prerequisite_threshold]
        seen = exercise["problem_id"] in attempted
        distance = max(policy.challenge_lower - probability, probability - policy.challenge_upper, 0.)
        need = sum((1 - profile[c]["estimated_performance"]) / (1 + profile[c]["supporting_attempts"])
                   for c in exercise["concept_ids"]) / len(exercise["concept_ids"])
        score = round(1 - distance + policy.need_weight * need
                      - policy.prerequisite_penalty * len(weak) - policy.repeat_penalty * seen, 6)
        position = "below" if probability < policy.challenge_lower else "above" if probability > policy.challenge_upper else "within"
        reasons = [f"Demo estimate is {position} the configured {policy.challenge_lower:.1%}-{policy.challenge_upper:.1%} challenge range.",
                   "Concept need uses estimated performance and distinct first-attempt support.",
                   "Previously attempted in this replay." if seen else "New exercise in this replay."]
        if weak:
            reasons.append("Review prerequisite concepts: " + ", ".join(weak) + ".")
        if any(profile[c]["supporting_attempts"] == 0 for c in exercise["concept_ids"]):
            reasons.append("Some concepts have no first-attempt evidence; estimate uses a neutral prior.")
        recommendations.append({**prediction, "title": exercise["title"], "concept_ids": exercise["concept_ids"], "score": score, "reasons": reasons})
    return sorted(recommendations, key=lambda row: (-row["score"], row["problem_id"]))
