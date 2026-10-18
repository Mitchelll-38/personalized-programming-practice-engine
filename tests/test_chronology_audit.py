"""Original synthetic projections; no released student rows."""

from dataclasses import FrozenInstanceError, replace
import itertools
import json

import pytest

from practice_engine.data.chronology_audit import ChronologyEvent, audit_chronology


def event(order="1", second="01", **changes):
    return replace(ChronologyEvent("synthetic-learner", "synthetic-assignment", "synthetic-problem",
                                  "Run.Program", f"2026-10-18T12:00:{second}", "UTC", order),
                   **changes)


def counts(events, subset="run_program"):
    return audit_chronology(events).aggregates[subset]["counts"]


def test_raw_decreases_are_not_timezone_policy():
    rows = [event("1", "03"), event("2", "02"), event("3", "01", timezone="0")]
    result = audit_chronology(rows).aggregates
    c = result["run_program"]["counts"]
    assert c["raw_wall_time_decreases"] == 2
    assert c["same_literal_decreases"] == c["same_literal_pairs"] == 1
    assert c["incomparable_literal_pairs"] == 1
    assert c["decreasing_subjects"] == c["decreasing_scopes"] == 1
    assert c["mixed_timezone_subjects"] == 1
    assert result["interpretation_status"] == "unresolved"
    assert result["normalization_applied"] is False
    assert result["global_timeline_verified"] is False


def test_ties_cross_scope_and_literal_are_observations_only():
    rows = [event(), event("2"), event("1", problem_id="other", timezone="0")]
    c = counts(rows)
    assert c["wall_time_tie_groups"] == 1
    assert c["wall_time_tied_rows"] == c["max_wall_time_tie_size"] == 3
    assert c["wall_time_tie_excess"] == 2
    assert c["cross_problem_wall_time_tie_groups"] == 1
    assert c["cross_literal_wall_time_tie_groups"] == 1
    assert c["scoped_wall_time_tie_groups"] == 1
    assert c["scoped_ties_with_missing_or_duplicate_order"] == 0
    assert c["adjacent_raw_wall_time_pairs"] == 1  # never cross-problem


def test_duplicate_orders_have_no_input_order_tiebreak():
    rows = [event("0", "05"), event("1", "04"), event("1", "03"), event("2", "02")]
    expected = audit_chronology(rows).aggregates
    assert expected["run_program"]["counts"]["duplicate_scoped_order_excess"] == 1
    assert expected["run_program"]["counts"]["adjacent_raw_wall_time_pairs"] == 0
    for permutation in itertools.permutations(rows):
        assert audit_chronology(iter(permutation)).aggregates == expected


def test_raw_wall_time_summary_is_permutation_invariant_and_scope_exact():
    rows = [event("1", "03"), event("2", "02"),
            event("3", "01", timezone="0"), event("4", "00", assignment_id="different")]
    expected = audit_chronology(rows).aggregates
    assert expected["run_program"]["counts"]["adjacent_raw_wall_time_pairs"] == 2
    for permutation in itertools.permutations(rows):
        assert audit_chronology(permutation).aggregates == expected


def test_missing_literals_do_not_claim_comparability():
    c = counts([event("1", "02", timezone=""), event("2", "01", timezone="")])
    assert c["raw_wall_time_decreases"] == c["incomparable_literal_pairs"] == 1
    assert c["same_literal_pairs"] == c["same_literal_decreases"] == 0


def test_no_ties_means_zero_max_and_adjacency_excludes_invalid_orders():
    c = counts([event("1", "03"), event("invalid", "02"), event("2", "01")])
    assert c["max_wall_time_tie_size"] == 0
    assert c["invalid_orders"] == 1
    assert c["adjacent_raw_wall_time_pairs"] == c["raw_wall_time_decreases"] == 1


@pytest.mark.parametrize("order", ["", "01", "-1", "+1", "1.0", "1e2", " 1", "١", "9" * 19])
def test_order_strictness_and_missing_order_tie(order):
    c = counts([event(order), event("2")])
    assert c["invalid_orders"] == 1
    assert c["scoped_ties_with_missing_or_duplicate_order"] == 1


@pytest.mark.parametrize("stamp", ["", "NaN", "2026-10-18", "2026-10-18T12:00:60",
    "2026-02-30T12:00:00", "2026-10-18T12:00:00.1234567", "2026-10-18T12:00:00+00:99",
    "2026-10-18T12:00:00+24:00", "2026-10-18T12:00:00+0000"])
def test_timestamp_strictness(stamp):
    assert counts([event(timestamp=stamp)])["invalid_timestamps"] == 1


def test_aware_timestamps_counted_without_utc_conversion_or_naive_comparison():
    c = counts([event(), event("2", timestamp="2026-10-18T12:00:01Z"),
                event("3", timestamp="2026-10-18T08:00:01-04:00")])
    assert c["aware_timestamps"] == 2
    assert c["naive_timestamps"] == c["mixed_awareness_subjects"] == 1
    assert c["wall_time_tie_groups"] == c["adjacent_raw_wall_time_pairs"] == 0


def test_unknown_literals_are_aggregated_without_echoing_values():
    rows = [event(timezone="private-zone"), event("2", timezone=""),
            event("3", timezone="0"), event("4", event_type="private-event")]
    result = audit_chronology(rows).aggregates
    assert result["all_events"]["timezone_literals"] == {"UTC": 1, "zero": 1, "missing": 1, "other": 1}
    assert result["all_events"]["counts"]["events"] == 4
    assert result["run_program"]["counts"]["events"] == 3
    serialized = json.dumps(result)
    for secret in ("private-zone", "private-event", "synthetic-learner", "synthetic-assignment", "synthetic-problem", "2026-10"):
        assert secret not in serialized


def test_detached_receipt_and_empty_input():
    audit = audit_chronology([])
    assert counts([])["events"] == 0
    modified = audit.aggregates
    modified["all_events"]["counts"]["events"] = 100
    assert audit.aggregates["all_events"]["counts"]["events"] == 0
    with pytest.raises(FrozenInstanceError):
        event().order = "2"


@pytest.mark.parametrize("bad", [None, {}, {"Score": "1", "Code": "poison"},
    event(order=1), event(subject_id=" "), event(event_type="")])
def test_no_implicit_projection_or_nonstring_fields(bad):
    with pytest.raises(ValueError):
        audit_chronology([bad])
