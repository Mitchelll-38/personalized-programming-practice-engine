# Chronology CSV projection

Owner: product/platform engineer. Purpose: connect the pure unresolved chronology
collector to the acquired local CSV layout while projecting no outcomes or code.
Acceptance: exactly seven string fields; known metadata/version/restricted scope;
fixed aggregate receipt bound to each parsed file; safe generic errors; original
synthetic boundary tests and private official aggregate replay. Dependency: merged
pure chronology collector #76. Independent reviewer: calibration engineer.

Plan before implementation: separate module/API/CLI, exactly two known CSV reads,
conservative byte/row caps and per-file before/after hashes on the same descriptor.
Keep metadata declarations separate from chronology truth. No structural-module
private helper reuse, interpretation, normalization, history or training activation.

## Interface and privacy

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m practice_engine.data.chronology_csv <private-Data-directory>
```

`audit_release_chronology(Path(...))` returns the same receipt as the CLI. It opens
only `DatasetMetadata.csv` and `MainTable.csv`. Main projection headers must occur
exactly once: SubjectID, AssignmentID, ProblemID, EventType, ServerTimestamp,
ServerTimezone and Order. Additional unique Main columns are ignored; their values
are not projected or analyzed. No Score, code or code-state table is consumed by
the collector. Malformed-width records and duplicate headers fail generically.

Metadata requires exact Property/Value headers, unique nonempty property keys,
Version `6`, scope `Restricted`, and exactly the SubjectID/AssignmentID/ProblemID
scope columns (list order is immaterial). Consistency accepts only TRUE/FALSE,
true/false or True/False as an observed Boolean declaration. Unknown property
values are ignored and never echoed. Unknown versions/scopes or ambiguous metadata
fail; no metadata statement establishes a verified timeline.

The receipt contains only adapter version, two fixed table names with hashes/byte
lengths/record counts, the four known typed declarations and the pure collector's
aggregate report. CSV values remain strings in the exact seven-field projection;
no whitespace trimming, numeric ID coercion, timezone alias or history ordering
is applied. `normalization_applied` and `global_timeline_verified` stay false and
`interpretation_status` stays unresolved, including when declared consistency is
true. No outcomes, code, identities, arbitrary metadata or input paths are emitted.

## Local-input and resource boundaries

Use a quiescent, trusted, locally acquired extracted release. Each file is hashed
before and after parsing on the same descriptor. This rejects changes during its
pass, not concurrent replacement across the two-table operation; there is no
atomic multi-table snapshot. Inputs remain unchanged and no files are created.

Caps are 64 MiB per table, 250,000 Main records and 100 metadata records. Hash reads
and row iteration enforce these limits; CSV decoding also uses Python's standard
field-size bound. These caps support the known S19 release rather than claiming a
general untrusted-ingestion service. The collector keeps projected events in
memory. Fatal I/O/encoding/CSV/metadata/cap/change errors yield a generic CLI error
with no partial receipt, raw value or source path.

Archive verification, structural compatibility, catalog mapping, chronology
interpretation, canonical import and training remain separate reviewed stages.
This utility does not authorize source use, resolve UTC/0 or choose an exclusion
policy. Keep private-release receipts under ignored project-private storage.
