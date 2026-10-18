# Catalog coverage and chronology audit

Owner: coordinator/data lead, independently audited by data/model engineers.
Purpose: distinguish available problem metadata from unresolved causal ordering.
Acceptance: exact sources/hashes, explicit identifier/concept policy, private raw
storage and an honest boundary before real import/training. Dependencies: acquired
S19 archive and independently inspected organizer sources. Plan: compare catalog
coverage without target outcomes, audit ordering label-blind and preserve source
uncertainty rather than weakening import checks.

## Organizer-linked catalog — October 18, 2026

The archived [organizer challenge document](https://docs.google.com/document/d/1t1-w6_PhPe2B8mX58GslCBNZFAat6Mhrf_EtmXvFYmY/edit)
links this exact [prompt/concept spreadsheet](https://docs.google.com/spreadsheets/d/1-APxPAVP3PylM0fskzDNgpalj1DTuMqDLkgBC5QxJdg/edit#gid=0)
in its problem-prompts section. The document identifies its contents as archived.
The original CSV is stored privately beside the release, with an acquisition
receipt: **15,797 bytes**, SHA-256
`ad34fdb7325476d8eb1a861cc5b46e410472c097668c42d5f4310bf99e18855f`.

Independent audits agree on 50 unique problem rows, nonempty requirements and 18
binary concept columns, each row having at least one positive tag. The annotations
are one researcher's estimates; they are not instructor ground truth. No exact
catalog-specific redistribution license was found. Public accessibility and the
CodeWorkout site's general Creative Commons description do not identify a license
variant for this sheet. Acquired prompts/catalog stay private; no public catalog or
model publication permission is inferred.

Literal assignment-ID strings differ between the release and sheet. A narrowly
audited integer versus trailing-zero-decimal spelling crosswalk yields complete
50/50 coverage without collisions; ProblemID is matched exactly. The reviewed [catalog mapper](organizer-catalog.md) preserves release composite
IDs, prompt text and original positive concept-header IDs. It rejects unknown spellings, lossy numeric coercion,
collisions, invalid cells and missing/extra coverage. This is explicit cross-source
mapping, not a change to exact string equality in the generic importer.

## Chronology remains unresolved

The [ProgSnap v6 specification](https://cssplice.org/progsnap2/ProgSnap2-v6-31Jul2019.pdf)
requires timestamps to be interpreted with their timezone, and confines `Order`
comparisons to the declared ordering scope. This release declares the scope
`SubjectID;AssignmentID;ProblemID`. Within-scope `Order` cannot order different
problems. A few timestamp reversals also contradict scoped Order.

All parsed timestamps lack offsets, and most subjects have both `0` and `UTC`
timezone labels. The organizer's timezone description references Eastern time and
UTC without clearly establishing equivalence of those two labels. Plain timestamp
parsing in the organizer notebooks does not settle the convention of these exact
released bytes. Current exporter code is not proof of a historical export policy.

Independent label-blind sensitivity audits show that the competing interpretations
change event order substantially. Therefore the pipeline must not equate `0` with
UTC, use global `Order`, or select the interpretation yielding fewer anomalies as
if it were verified source truth. A private clarification draft is prepared;
contacting the organizer requires separate user authorization. No message or data
attachment has been sent as part of this audit.

Catalog mapping and archive inspection are implemented independently. Canonical real
histories, verified-release provenance and real train/validation runs remain gated
on an authoritative timezone interpretation and a reviewed ordering/exclusion
policy. No row-level data, per-subject audit values, submitted code or challenge
labels are published here, and no real predictive result is claimed.
