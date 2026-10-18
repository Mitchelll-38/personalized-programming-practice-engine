# Configurable transparent practice policy

Owner: coordinator. Purpose: replace the hardcoded65% point target with an
inspectable challenge range and bounded concept-need/prerequisite/repetition
weights. Dependencies: existing demo estimates/profile and snapshot #41/#44.
Acceptance: strict finite ordered range/config; deterministic transparent scores;
server-only optional configuration; exact policy/config hash in generated response
and persisted snapshot; historical snapshots remain readable; bad configuration
fails privately without generating a misleading record. No fitted-model selection
or evidence that a challenge range improves learning is claimed.

Plan: define a frozen versioned policy, use distance outside the challenge range
plus observable concept need and existing penalties, load it once per generation,
and retain its exact serialized configuration/hash. Defaults explore60-80%
estimated correctness as a product hypothesis. Environment configuration is a
trusted local experiment input; no client-supplied path or per-request override.
UI already renders backend reasons; optional policy inspection is a separate PR.


`PracticePolicy` defaults to range0.6-0.8, concept-need weight0.2, prerequisite
penalty0.1 per weak prerequisite, repeated-exercise penalty0.3, and prerequisite
threshold0.6. Each value is finite and bounded in[0,1]; challenge bounds must
strictly increase. Scores are ranking values, not probabilities:

```
need = mean((1 - concept_estimate) / (1 + distinct_first_attempt_support))
distance = max(lower - probability, probability - upper, 0)
score = 1 - distance + need_weight * need
        - prerequisite_penalty * weak_prerequisite_count - repeat_penalty * seen
```

Scores round to six decimals and ties use problem ID. Concept estimates remain
synthetic heuristics; retries do not inflate first-attempt support. Any prior
attempt marks an exercise seen. Reasons expose range position, observed support,
novelty and weak prerequisites. This rule does not establish an optimal teaching
policy or calibrated correctness.

Optionally set `PRACTICE_POLICY_CONFIG` to a trusted local JSON file with any of the
versioned policy fields; missing fields use declared defaults. The server reads it
once per generated ranking, rejects unknown/duplicate fields and invalid values,
and returns private503 `practice_policy_unavailable` on missing/bad files. Browsing
history/profile and manual replay remain available. There is no client path or
policy override. Configuration changes are observed on the next generation.

Responses add full normalized `policy_config` and canonical `policy_sha256`; the
snapshot retains that same immutable configuration/hash and matching v2 version.
No original configuration-file path is returned. Historical v1 records lacking
both fields remain readable with null configuration/hash; their original scoring
rule is documented in earlier commits. Known v2 records require both fields even when both are absent from old-style JSON.
A hash without configuration (or mismatched
version/hash) fails snapshot validation. Hashes detect declared content changes,
not authenticated provenance. This affects the heuristic policy only; optional
fitted-model inspection continues independently.
