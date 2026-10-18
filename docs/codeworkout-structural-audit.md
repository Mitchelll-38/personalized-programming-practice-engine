# Read-only CodeWorkout structural audit

Owner: product/platform engineer. Purpose: reproduce the acquired release's basic
compatibility diagnostics without reconstructing histories or exposing records.
Acceptance: exact hashes/row counts for the two known tables; aggregate header,
row, identity-key, code-join, event-type and Run score validity checks; private
safe errors; original synthetic regressions and private official aggregate smoke.
Dependencies: existing CodeWorkout table contract and acquired private release.

Plan before implementation: one standard-library module and module CLI, reading
only MainTable.csv and CodeStates/CodeStates.csv. Produce deterministic aggregate
JSON, never raw rows/IDs/code/grade features. Leave archive verification/extraction,
chronology, catalog conversion, canonical import and training gates separate.

## Interface

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m practice_engine.data.codeworkout_audit <private-Data-directory>
```

`audit_structure(Path(...))` returns the same deterministic JSON as the module
CLI. Only `MainTable.csv` and `CodeStates/CodeStates.csv` are opened. Both include
byte length and SHA-256, calculated before and after parsing on the same open file
to reject changes during that table's pass. This is per-table stability, not an
atomic snapshot across tables; audit a quiescent extracted release. No file is
written. Keep private-release receipts in ignored
project storage; public publication of aggregates still requires review.

Each table reports logical CSV records after the header, malformed-width records,
unique-presence booleans for known required headers, and counts of duplicate or
unknown header columns. It never echoes unknown header strings. Empty/missing and
duplicate event/code IDs are counted; Run identity-key emptiness, colon ambiguity
and empty/unresolved code references are diagnosed. Duplicate counts are excess
nonblank occurrences. Empty code references follow the importer: literal empty is
missing; whitespace-only references remain unresolved.

Semantic diagnostics describe well-formed records only; malformed-width records
are counted and skipped. Missing/duplicate dependent headers yield `null` rather
than zero failures. Code joins are also unavailable when the code table has a
malformed record, since its usable ID inventory may be incomplete. A zero count
never overrides separate header/row diagnostics.

Event counts expose only the three known release types (`Run.Program`, `Compile`,
`Compile.Error`) and aggregate `other`/`empty` buckets. Run scores are counted only
as missing, invalid or finite in `[0,1]`; no correctness/partial-score distribution
or grade feature is produced. Score interpretation remains a separate gate.

Unparseable CSV, invalid UTF-8, I/O failures or changing bytes abort without a
partial receipt; CLI errors omit source paths/values and traceback details.
ServerTimestamp is checked only as a required header, never parsed. Timezone and
Order columns are ignored; Subject link grades and early/late tables are never
opened.
This report cannot reconstruct histories or authorize import/provenance/training.

## Verification record

Original synthetic tables exercise unknown-value privacy, poisoned unrelated
files, multiline code/BOM, missing/duplicate headers, unavailable diagnostics,
malformed records, keys/joins, invalid/finite scores, actual file mutation and safe
CLI failures. No downloaded rows or submitted code are committed.

On client date 2026-10-18, private official-release replay reproduced acquisition
hashes and row counts for both known tables, matched prior aggregate event counts,
found 69,627 finite/in-range Run scores and zero key/join diagnostics. The complete
receipt remains private. This is structural evidence, not grading, chronology,
source-use acceptance or an empirical prediction result.

The structural/import/CLI/manifest regression run passed 47 tests in 9.52 seconds.
