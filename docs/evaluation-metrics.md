# Offline probability evaluation

`practice_engine.evaluation.evaluate(examples, probabilities)` accepts nonempty
prediction examples and aligned finite probabilities in [0, 1] meaning
`p(correct)`. Boolean probabilities are rejected. It returns `aggregate`, sorted
`per_student`, `equal_student_macro`, and `metric_definitions` dictionaries.

Aggregate and student reports contain counts, correctness prevalence, binary log
loss (natural log; fixed clipping at 1e-15 and 1-1e-15), Brier score on raw
probabilities, correct-positive ROC AUC, and incorrect-positive average precision.
ROC ties receive half credit. Incorrect AP ranks by decreasing `p(incorrect)` and
groups equal scores before adding recall increments times precision; it is step
average precision, not trapezoidal precision-recall area. Both ranking metrics
are null for one-class samples with `requires_both_classes` reasons.

Macro log loss and Brier average each student's metric equally, avoiding extra
weight for students with longer histories. They do not average ranking metrics
or claim confidence intervals. This module neither fits models/calibrators nor
selects thresholds. Callers own partition provenance, validation-only model
selection and locked-test access. Synthetic tests verify arithmetic and data
boundaries; these are not measured model results or learning-effectiveness claims.
