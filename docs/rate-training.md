# Reproducible baseline smoke runs

October 27 exact bundle read plan — Owner: data engineer. Purpose: prevent a
training loader from using artifact bytes changed after initial manifest
verification. Acceptance: recheck the hash of the exact split, train, validation
and family audit bytes the loader parses; reject a synthetic post-verification
label mutation before fitting, while continuing to hash but never parse test
examples. Dependencies: processing manifest and existing bundle validation.
This is an integrity check, not a claim about source permission or provenance.

The loader now hashes the exact split, train, validation and family audit bytes it
parses against the verified manifest. A changed artifact fails before fitting;
the test partition remains hash-checked by manifest verification and unread as
examples.

October 26 bundle consistency fix plan — Owner: data engineer. Purpose: reject
processed examples whose later observed histories contradict an earlier scored
first attempt. Acceptance: check train/validation scored target identity, position,
statement, concepts and outcome wherever that target appears in a supplied prior
history; reject a rehashed contradictory synthetic bundle under both student and
family protocols, while leaving test examples unread. Dependencies: existing
processing manifest, split and causal-history validation. This check does not
reconstruct the source or establish real-data provenance.

Owner: platform engineer. This change extracts a shared synthetic training-bundle
boundary and extends rate runs to reviewed family splits. Acceptance: verify
partition provenance, reject malformed or leaking histories before fitting,
preserve student runs and never parse test examples. Dependencies: processing
manifests and the family CLI. Logistic/BKT run commands remain separate work.

Create a processing bundle with an explicit synthetic declaration, then run:

```powershell
.\.venv\Scripts\python.exe -m practice_engine.training.rates data/processed/day1 --output artifacts/runs/problem-rate-smoke --variant problem
```

The command verifies the processing hashes and split source/seed, checks disjoint
student or exercise-family groups and causal examples, fits only the train partition and evaluates
validation. It does not parse test examples or select parameters from test data.
Integrity verification hashes test bytes as part of the bundle; that is not test
evaluation. Existing run directories are rejected. Atomic directory replacement
publishes `model.json`, `validation.json` and `run.json` together.

Global and problem variants are separate declared runs. Manifests record smoothing,
seed, versions and source/split provenance. These runs exercise software only:
the current command deliberately requires synthetic input while real access,
terms and catalog/grading gates remain unmet. No fixture metric is a research
result or evidence of improved learning. The saved model does not activate the API.

`load_training_bundle` returns train/validation examples, the verified manifest,
split metadata and artifact provenance. Family runs accept `family-holdout-v1`
bundles from the [family CLI](family-holdout.md), require exact disjoint
family/problem groups and map-hash agreement, and reject any history response
outside training families. Only train and validation examples are parsed;
test bytes are checked for integrity without consuming labels. Student histories
remain student-specific causal prefixes. Train/validation target sequence positions
must be unique per student, including across the two partitions. Hashes do not
certify usage rights.

The loader also checks available train/validation targets against their appearances
in later observed histories. A prior response must retain the scored target's
sequence position, problem identity, statement, concepts and outcome. Family
histories are checked against the same available scored targets after their
training-exercise-only rule; test examples remain unread. This catches internally
contradictory processed bundles, but cannot prove that histories faithfully
represent the original source rows.
