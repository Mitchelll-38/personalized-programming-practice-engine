# Organizer catalog mapping

Owner: model platform engineer. Dependencies: reviewed official S19 acquisition
and organizer-linked public catalog evidence; this is separate from chronology
and real-source training authorization. Purpose: map the exact known organizer
CSV to supplied release composite IDs while retaining original prompt/concept
meaning. Acceptance: exact header order, lossless Requirement text, verbatim
positive concept IDs, narrow one-to-one assignment crosswalk, exact ProblemID,
complete coverage/collision rejection, detached identity receipt and typed output.

Plan recorded before implementation: read/hash exact CSV bytes; validate the
known 21-column format and explicit unique release-ID inventory; construct a narrow
ASCII-integer/zero-only-decimal assignment crosswalk without changing release IDs.
Map only positive 1 cells to original concept headers. Return immutable typed
candidates and detached aggregate identity/audit metadata. Test malformed headers,
IDs, cells, missing/extra/ambiguous coverage, text preservation and identity hashes
with original synthetic fixtures. After focused checks, privately smoke the actual
catalog and inventory. No canonical interaction import, training, authentication,
source flags or catalog-license claim is added.

`map_organizer_catalog(csv_path, release_problem_ids)` requires a nonempty unique
list/tuple of exact release `AssignmentID:ProblemID` strings. CSV headers must be
`AssignmentID`, `ProblemID`, `Requirement`, then these 18 columns in order:
`If/Else`, `NestedIf`, `While`, `For`, `NestedFor`, `Math+-*/`, `Math%`,
`LogicAndNotOr`, `LogicCompareNum`, `LogicBoolean`, `StringFormat`, `StringConcat`,
`StringIndex`, `StringLen`, `StringEqual`, `CharEqual`, `ArrayIndex`, `DefFunction`.
Cells must be exactly 1 or empty; zero, whitespace and numeric/text variants fail.
Each prompt must contain non-whitespace text and each problem a positive concept.
Prompt cell content (including whitespace/newlines) is preserved, with UTF-8 BOM
accepted for headers. No slugging or inferred concepts are used.

Assignment spellings on either side may be canonical ASCII integers (zero or
nonzero digits without leading zeros), optionally followed by a decimal point
and one or more zeros. Crosswalk matches the integer spelling without floating
arithmetic. Each side must use exactly one raw spelling per matched assignment;
collisions, signs, exponents, fractions and leading zeros fail. Problem IDs require
canonical ASCII integer strings and match exactly. Every supplied release problem
must map once and no catalog extras are accepted. Output always retains the raw
release composite ID; lexical sorting is serialization order, never chronology.
Existing v1 importer identity/ordering behavior is unchanged.

The frozen result holds typed `Candidate` tuples and a receipt exposed as a fresh
deep-detached JSON dictionary on every access. The receipt binds exact CSV bytes,
sorted inventory, assignment crosswalk, explicit column policy and canonical
candidate values using hashes, plus aggregate counts and annotation caveat. It
contains no prompt text. Integrity is not authenticated source or use permission;
the caller must separately bind a reviewed acquisition receipt. The organizer
[catalog](https://docs.google.com/spreadsheets/d/1-APxPAVP3PylM0fskzDNgpalj1DTuMqDLkgBC5QxJdg/edit)
is linked by the archived organizer document's prompt/concept section. Its tags
are one researcher's estimates, not instructor ground truth or proven mastery.
No explicit catalog-specific redistribution license was established; all acquired
or mapped actual content stays under ignored project-private storage.

The function writes no files, imports no interactions and fits nothing. Its receipt
does not verify chronology, scoring, source rights or authorization to train; in
particular, historical timezone/Order ambiguity remains unresolved. Synthetic
fixtures validate software only. Separate reviewed source/bundle/training gates
remain closed.
