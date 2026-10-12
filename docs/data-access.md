# Dataset access and provenance — day 1

Investigated October 12, 2026. **No real student data downloaded or redistributed. No model trained.**

The [official SoLAR announcement](https://www.solaresearch.org/2021/11/the-2nd-csedm-data-challenge-in-cooperation-with-solar-is-happening-now/) links the [challenge dataset page](https://sites.google.com/ncsu.edu/csedm-dc-2021/dataset) and [organizer-linked starter code](https://github.com/YangAzure/CSEDMDataChallenge). The dataset page redirected this browsing tool to Google sign-in and could not be inspected. This does not prove the dataset is unavailable through all routes.

The starter repository describes S19 and F19 release directories, ProgSnap2 loading, and preprocessing notebooks; its README states the full original datasets needed by some notebooks are unavailable to readers. That source establishes an investigation route, not redistribution permission for student submissions.

| Requirement | Day-one status | Next action / owner |
|---|---|---|
| Exact downloadable release and checksum | Unverified | A: inspect authorized dataset access route |
| Research use and redistribution terms | Unverified | A: record release-specific terms; exclude raw data from public git |
| Exercise text and instructor concepts | Unverified | A/C: inspect release tables and document tag provenance |
| Submission join keys and timestamps | Unverified | A: reconstruct submission events, reject ambiguous ordering |
| First-attempt grading rule | Canonical Boolean contract only | A: map verified grading fields; document missing/partial grading |
| Real cohort and problem counts | Not measured | A: calculate from approved imported release |

The committed `data/fixtures/synthetic.jsonl` is original hand-authored synthetic Java practice data. Its examples and outcomes are fabricated for software tests only. Synthetic audit statistics must never be quoted as a research benchmark. API fixtures are separately authored original demo exercises, not a replica of a CodeWorkout release.

`practice-data` accepts already-normalized canonical JSONL. It is **not** a CodeWorkout/ProgSnap2 importer. Day 2 must implement an importer against the actual downloaded schema, without counting compilation/test-log rows as separate attempts. Canonical rows require an explicit, unique per-student sequence index, strict Boolean outcome, sequential attempt numbers, and candidate text/concepts. Missing original ordering, labels or texts must be audited before conversion.

Outputs stay under ignored `data/processed/`. Every audit/split records a source SHA-256; audit flags remain false until a release-specific provenance check is added. Current partitions are student-disjoint only. Exercise/family and joint partitions are scheduled for day 3 and must not be inferred from the current implementation.
