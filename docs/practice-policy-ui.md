# Inspecting the configured heuristic policy

Owner: baseline engineer. Purpose: disclose the configured challenge range and
exact policy record without computing scores in the browser or claiming learning
benefits. Dependency: backend policy PR #61. Acceptance: known v2/demo metadata,
finite bounded values and matching version/hash shape; invalid metadata fallback;
separate ranking, model inspection, choice and simulated-outcome behavior.

The recommendation panel shows the heuristic challenge band as estimated
correctness, while the summary retains its policy version. An optional **Inspect
policy configuration** disclosure shows the exact configuration and declared
SHA-256. Scores still come from the server; no browser control changes weights,
no model is selected and no hash is recomputed/authenticated by the browser.

Only `transparent-ranking-v2` with an exact demo declaration and student ID is
interpreted. Configuration/version must match; all six values must be finite
numbers in `[0,1]` with strictly increasing challenge bounds. The digest must have
the declared SHA-256 shape and configuration fields must match the known schema.
Missing, legacy, unknown or inconsistent metadata shows **Policy configuration
unavailable** rather than inventing default weights/ranges. Browsing, choice,
research inspection and manual replay remain available.

The displayed band is a configured heuristic hypothesis. Its learning benefits
have not been measured. Fitted-model inspection operates separately; neither
configured weights nor a declared hash prove calibration or policy effectiveness.
The [backend contract](practice-policy.md) owns score calculation, configuration
loading and snapshot binding. Browser fixtures test presentation/guard behavior
using original synthetic data and do not validate predictive or teaching quality.
