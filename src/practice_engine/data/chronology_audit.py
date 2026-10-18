"""Label-free wall-time diagnostics; never a canonical chronology policy."""

from collections import Counter, defaultdict
from dataclasses import dataclass, fields
from datetime import datetime
import json
import re
from typing import Iterable


@dataclass(frozen=True)
class ChronologyEvent:
    subject_id: str
    assignment_id: str
    problem_id: str
    event_type: str
    timestamp: str
    timezone: str
    order: str


@dataclass(frozen=True)
class ChronologyAudit:
    _json: str

    @property
    def aggregates(self) -> dict:
        return json.loads(self._json)


_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}"
                   r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})?")
_ORDER = re.compile(r"(?:0|[1-9][0-9]{0,17})")


def _timestamp(value: str) -> datetime | None:
    if not _TIME.fullmatch(value):
        return None
    try:
        # datetime accepts overflowing offset minutes; require ISO minute bounds.
        if value[-6:-5] in ("+", "-") and int(value[-2:]) > 59:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _collect(events: list[ChronologyEvent]) -> dict:
    counts = dict.fromkeys((
        "events", "subjects", "invalid_timestamps", "naive_timestamps", "aware_timestamps",
        "invalid_orders", "duplicate_scoped_order_excess", "mixed_timezone_subjects",
        "mixed_awareness_subjects", "wall_time_tie_groups", "wall_time_tied_rows",
        "wall_time_tie_excess", "max_wall_time_tie_size", "subjects_with_wall_time_ties",
        "cross_problem_wall_time_tie_groups", "cross_literal_wall_time_tie_groups",
        "scoped_wall_time_tie_groups", "scoped_ties_with_missing_or_duplicate_order",
        "adjacent_raw_wall_time_pairs", "raw_wall_time_decreases", "same_literal_pairs",
        "same_literal_decreases", "incomparable_literal_pairs", "decreasing_scopes",
        "decreasing_subjects",
    ), 0)
    zones = dict.fromkeys(("UTC", "zero", "missing", "other"), 0)
    subject_zones, awareness = defaultdict(set), defaultdict(set)
    times, scoped_times, ordered = defaultdict(list), defaultdict(list), defaultdict(list)
    subjects = set()
    for event in events:
        subject = event.subject_id
        scope = (subject, event.assignment_id, event.problem_id)
        subjects.add(subject)
        zone = event.timezone
        zones[{"UTC": "UTC", "0": "zero", "": "missing"}.get(zone, "other")] += 1
        subject_zones[subject].add(zone)
        order = int(event.order) if _ORDER.fullmatch(event.order) else None
        counts["invalid_orders"] += order is None
        stamp = _timestamp(event.timestamp)
        kind = "invalid" if stamp is None else "naive" if stamp.tzinfo is None else "aware"
        counts[f"{kind}_timestamps"] += 1
        if stamp is not None:
            awareness[subject].add(kind)
        if order is not None:
            ordered[scope].append((order, stamp if kind == "naive" else None, zone))
        if kind == "naive":
            times[(subject, stamp)].append((scope, zone))
            scoped_times[(*scope, stamp)].append(order)
    tied_subjects, decreasing_subjects, decreasing_scopes = set(), set(), set()
    for (subject, _), values in times.items():
        n = len(values)
        counts["max_wall_time_tie_size"] = max(counts["max_wall_time_tie_size"], n)
        if n > 1:
            tied_subjects.add(subject)
            counts["wall_time_tie_groups"] += 1
            counts["wall_time_tied_rows"] += n
            counts["wall_time_tie_excess"] += n - 1
            counts["cross_problem_wall_time_tie_groups"] += len({v[0] for v in values}) > 1
            counts["cross_literal_wall_time_tie_groups"] += len({v[1] for v in values}) > 1
    for values in scoped_times.values():
        if len(values) > 1:
            counts["scoped_wall_time_tie_groups"] += 1
            counts["scoped_ties_with_missing_or_duplicate_order"] += (
                None in values or len(values) != len(set(values)))
    for scope, values in ordered.items():
        frequency = Counter(v[0] for v in values)
        counts["duplicate_scoped_order_excess"] += sum(n - 1 for n in frequency.values())
        values.sort(key=lambda v: v[0])
        for left, right in zip(values, values[1:]):
            if frequency[left[0]] > 1 or frequency[right[0]] > 1:
                continue
            if left[1] is None or right[1] is None:
                continue
            counts["adjacent_raw_wall_time_pairs"] += 1
            comparable = bool(left[2]) and left[2] == right[2]
            counts["same_literal_pairs" if comparable else "incomparable_literal_pairs"] += 1
            if right[1] < left[1]:
                counts["raw_wall_time_decreases"] += 1
                counts["same_literal_decreases"] += comparable
                decreasing_scopes.add(scope)
                decreasing_subjects.add(scope[0])
    counts.update(events=len(events), subjects=len(subjects),
                  mixed_timezone_subjects=sum(len(v) > 1 for v in subject_zones.values()),
                  mixed_awareness_subjects=sum(len(v) > 1 for v in awareness.values()),
                  subjects_with_wall_time_ties=len(tied_subjects),
                  decreasing_scopes=len(decreasing_scopes),
                  decreasing_subjects=len(decreasing_subjects))
    return {"counts": counts, "timezone_literals": zones}


def audit_chronology(events: Iterable[ChronologyEvent]) -> ChronologyAudit:
    """Project no outcomes; never resolve zones, Order ties or cross-problem order."""
    projected = []
    for event in events:
        if type(event) is not ChronologyEvent or any(
                type(getattr(event, field.name)) is not str for field in fields(ChronologyEvent)):
            raise ValueError("Chronology requires exact string-only projected events")
        if any(not value.strip() for value in (
                event.subject_id, event.assignment_id, event.problem_id, event.event_type)):
            raise ValueError("Chronology requires nonempty identity and event type")
        projected.append(event)
    report = {
        "audit_version": "chronology-aggregate-v1", "interpretation_status": "unresolved",
        "normalization_applied": False, "global_timeline_verified": False,
        "order_scope": "SubjectID;AssignmentID;ProblemID",
        "all_events": _collect(projected),
        "run_program": _collect([v for v in projected if v.event_type == "Run.Program"]),
    }
    return ChronologyAudit(json.dumps(report, sort_keys=True, allow_nan=False))
