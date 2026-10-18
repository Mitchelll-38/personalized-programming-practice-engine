# Label-free baseline inference boundary

Owner: coordinator. Purpose: prepare reviewed research artifacts for serving
without accepting target responses. Dependencies: canonical causal histories and
portable rate/logistic/BKT artifacts. Acceptance: reject candidate responses and
invalid histories, preserve batch order, retain artifact integrity checks and
return finite probabilities. API rollout follows separately.

`PredictionInput` accepts student ID, target sequence position, prior canonical
interactions and candidate ID/statement/concepts. It has **no target-label or
target-code field**, including inside the candidate. Candidates require nonempty
metadata and unique concept tags. Histories must contain the same student's
strictly earlier, distinct first attempts and exclude the candidate response.
Retries and attempts at the same candidate are not scored as future distinct
first attempts. Historical code remains allowed in canonical inputs; these
baselines do not use it.

`predict_inputs(artifact, queries)` accepts only the reviewed JSON artifact types,
revalidates inputs even after unchecked `model_copy` changes and calls artifact
prediction, which rechecks model-payload integrity. Output preserves input order
and contains only problem ID and finite p(correct). An empty batch is supported.
Unknown exercises retain each underlying baseline's documented fallback behavior.

Existing model interfaces consume evaluation `PredictionExample` objects. The
adapter internally supplies a fixed false label sentinel that the inference
implementations ignore; callers cannot supply it. This is an interface adaptation,
not an observed outcome. Never evaluate or fit on these internal sentinel objects.

This PR loads no files, trains no model and changes no API endpoint, active model,
calibration flag or learner profile. Artifact provenance remains declared, not
authenticated evidence of data permission or empirical quality. Neural checkpoint
serving is a separate adapter; importing this module does not require Torch.

The adapter also accepts reviewed `CalibratedBaselineArtifact` envelopes. It
retains the same label-free causal inputs and delegates to the wrapper's live
integrity checks and scalar prediction. The wrapper's public `baseline()` returns
a detached, validated base artifact for metadata/source inspection; changing that
copy cannot alter the wrapper. Calibration provenance remains declared rather
than authenticated evidence. See [research-api.md](research-api.md) for metadata.

## Optional DKT inference adapter

Owner: coordinator. Purpose: query a loaded strict CPU DKT checkpoint through the
same label-free causal request/ordered probability contract as portable baselines.
Dependency: checkpoint #26 and input boundary #30. Acceptance: require a reviewed
checkpoint and typed revalidated requests; retain known/unknown and cold-start
semantics and live integrity checks; emit finite ordered scores; importing the
existing generic serving/API modules remains free of Torch. Implementation lives
in a separate optional module. No checkpoint file loading, API activation, neural
calibration or measured research results are added by this adapter.


Import `predict_dkt_inputs` from `practice_engine.models.dkt_serving` only in an
optional neural environment. It accepts an already-loaded `DKTCheckpoint` and a
list of `PredictionInput` objects, returning ordered `PredictionScore` objects.
Unknown candidate IDs retain the checkpoint's declared train-count fallback;
empty histories retain its zero recurrent state. Every call revalidates request
copies, nested metadata and live checkpoint weights, including empty batches.
The legacy checkpoint interface receives the same fixed internal false-label
sentinel used by baseline serving; it never accepts a client outcome. This
optional import requires Torch, while generic API/serving imports do not.
