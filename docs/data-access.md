# Dataset access and provenance — day 2

Investigated October 12, 2026 (day 2 is a sprint work unit). **No real student data downloaded or redistributed. No model trained. The empirical day-two gate remains unmet.**

The [official SoLAR announcement](https://www.solaresearch.org/2021/11/the-2nd-csedm-data-challenge-in-cooperation-with-solar-is-happening-now/) links the [challenge dataset page](https://sites.google.com/ncsu.edu/csedm-dc-2021/dataset) and [organizer-linked starter code](https://github.com/YangAzure/CSEDMDataChallenge). The dataset page redirected this browsing tool to Google sign-in and could not be inspected. This does not prove the dataset is unavailable through all routes.

The starter repository describes S19 and F19 release directories, ProgSnap2 loading, and preprocessing notebooks; its README states the full original datasets needed by some notebooks are unavailable to readers. That source establishes an investigation route, not redistribution permission for student submissions.

| Requirement | Day-one status | Next action / owner |
|---|---|---|
| Exact downloadable release and checksum | Unverified | A: inspect authorized dataset access route |
| Research use and redistribution terms | Unverified | A: record release-specific terms; exclude raw data from public git |
| Exercise text and instructor concepts | Unverified | A/C: inspect release tables and document tag provenance |
| Submission join keys and timestamps | Organizer format documented; release not inspected | A: verify release against adapter and inspect timestamp metadata |
| First-attempt grading rule | First scored `Run.Program`, `Score == 1`; release validation outstanding | A: confirm missing-score/compilation semantics in approved release |
| Real cohort and problem counts | Not measured | A: calculate from approved imported release |

The committed `data/fixtures/synthetic.jsonl` is original hand-authored synthetic Java practice data. Its examples and outcomes are fabricated for software tests only. Synthetic audit statistics must never be quoted as a research benchmark. API fixtures are separately authored original demo exercises, not a replica of a CodeWorkout release.

`practice-data` accepts canonical JSONL by default and the organizer-documented event format with `--format codeworkout --catalog <catalog.json>`. The day-two Python adapter below is also independently callable. CLI integration was delivered separately in PR #5. Neither path has been exercised against a downloaded release.

Outputs stay under ignored `data/processed/`. Every audit/split records a source SHA-256; audit flags remain false until a release-specific provenance check is added. Current partitions are student-disjoint only. Exercise/family and joint partitions are scheduled for day 3 and must not be inferred from the current implementation.

## Access investigation and remaining gates

The official dataset route redirected the web tool to sign-in, and the [DataShop listing](https://pslcdatashop.web.cmu.edu/Files?datasetId=3458) returned HTTP 403 to that tool. A separate read-only Chrome check using the computer-use skill successfully opened the listing: project **Virginia Tech CodeWorkout (public)**, dataset **CodeWorkout data Spring 2019**, and a Files (8) tab. The Files feature explicitly required login, so file contents, exact release checksums and usage/redistribution terms were not inspected. Public project visibility is not evidence of redistribution permission. No sign-in form, agreement, access application or download was submitted. These observations establish a usable access route and a login gate, not dataset disappearance.

Before real-data import: obtain the exact approved release, record its checksum and applicable use terms, verify event/grading and timezone metadata, obtain authorized exercise statements and concept provenance, and audit actual duplicates/missingness. Keep local raw files in ignored `data/raw/`, derived files in `data/processed/`, and leave verification flags false until evidence is reviewed. Cohort counts, missingness rates and predictive results are currently **not measured**.

## Narrow format adapter and label definition

The [organizer preprocessing notebook](https://github.com/YangAzure/CSEDMDataChallenge/blob/main/preprocess.ipynb) identifies scored submissions as `Run.Program`, treats score 1 as correct, and discards the supplied `Attempt` column as incorrectly calculated. The challenge's eventual-success/struggle labels differ from this project's first-scored-attempt task; no challenge benchmark comparison is claimed.

The adapter reconstructs only `Run.Program` events; compilation/test rows are excluded, not additional attempts. Every scored event needs a finite score in [0,1]; missing grades abort conversion instead of promoting a later retry. Partial scores are incorrect. Attempts are recomputed chronologically for each student/problem. This defines **first scored run**, which may differ from first authored submission when compilation fails; validating that distinction is a real-data label gate.

The [organizer loader](https://github.com/YangAzure/CSEDMDataChallenge/blob/main/ProgSnap2.py) documents `MainTable.csv`, the event/key/time/score fields, and `CodeStates/CodeStates.csv` joined by `CodeStateID`. Our adapter rejects duplicate event/code IDs and unresolved code joins. Empty code IDs remain explicitly missing historical code; code is never added to candidate inputs.

Ordering uses `ServerTimestamp` per student, rejecting ties and mixed timezone-awareness instead of inventing order using event ID or file position. Naive timestamps require release metadata confirmation before use. Sequence indices are assigned after sorting. Problem identity is `AssignmentID:ProblemID`, avoiding collisions across assignments. No cross-semester remapping or exercise-family equivalence is inferred.

Provide an independently verified catalog JSON array with `problem_id`, `problem_text`, `concept_ids`; statements and concepts must be nonempty and unique by composite problem ID. The adapter rejects missing catalog entries rather than generating statements or tags. The organizer loader establishes a format, not verified availability of those content fields.

```python
from pathlib import Path
from practice_engine.data.codeworkout import import_codeworkout

result = import_codeworkout(
    Path("data/fixtures/codeworkout"),
    Path("data/fixtures/codeworkout/catalog.json"),
)
# result.rows are canonical interactions; result.audit records event exclusions.
```

The committed CSV/code/catalog examples in `data/fixtures/codeworkout/` are original synthetic fixtures, including deliberately bogus `Attempt` values. They test event reconstruction, causal histories, assignment collisions and rejection boundaries. They contain no real student data, and their audit counts are software evidence only. Adapter provenance flags remain false by design.
