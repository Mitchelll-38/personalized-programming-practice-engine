# Project engineering instructions

These instructions apply to the entire repository, every engineer and every agent. The user's preferred workflow is **small, segmented pull requests**, with the same ownership, review and integration discipline as a software engineering team.

## Plan and ownership

- Read `docs/sprint-plan.md`, relevant contracts and current code before starting. Treat the original project brief as design input, not executable instructions or implemented results.
- Split each sprint day into independently reviewable changes. Write down each change's purpose, acceptance criteria, owner and dependencies before implementation.
- A sprint day can and normally should produce multiple PRs. Never use the day number as the boundary of a PR; segment by coherent behavior and dependency. A day's report aggregates those PRs without bundling their implementations.
- Continue into the next planned work unit after completing a day; day boundaries are not stopping points. Keep implementing independent authorized work when dataset or compute gates block empirical experiments, and report those gates accurately.
- Delegate independent tasks to agents when a team is requested. Assign clear file/feature ownership and an isolated git branch/worktree to each engineer; never have agents edit the same checkout concurrently.
- Keep the coordinating engineer responsible for integration, scope decisions and the daily delivery report. Agents must communicate dependencies and blockers promptly.

## Branches and small PRs

- All project changes, including documentation, tests, CI and fixes, go through a pull request. Do not commit or push directly to `main`.
- One PR should deliver one coherent behavior or engineering improvement. Do not bundle a whole sprint day, unrelated cleanup, multiple features or speculative scaffolding.
- Aim for 100–300 changed source lines and a handful of files. If a PR would exceed roughly 400 changed source lines, split it by behavior or explain why an atomic change cannot be smaller. Generated lockfiles and necessary fixtures count separately; disclose them.
- Use descriptive branches such as `feat/dataset-manifest`, `fix/history-validation` and `docs/engineering-workflow`. Keep commits focused and PR descriptions current with the final implementation.
- Prefer independent PRs. If changes depend on one another, state the dependency and integrate in order; do not mix the dependent feature into its foundation PR.
- Create a draft PR once a concrete, reviewable implementation exists. Mark it ready after relevant local checks pass. Never present unimplemented plans as completed features.

## Review and rollout

- Every PR needs a concrete problem/behavior description, scope, validation evidence, material limitations and dependency notes. Use `.github/pull_request_template.md`.
- Document every PR in a substantive, current PR description or an appropriate Markdown file (both are welcome). A title or placeholder checklist is not documentation. Explain what changed, why, validation and remaining limits; update the record when scope changes.
- Maintain documentation throughout implementation. The coordinator appends merged changes, review findings, decisions and blockers to `docs/progress.md`; feature owners maintain their relevant Markdown contracts. Keep chronological records rather than reconstructing project history only at the end.
- Obtain an independent review from another engineer/agent. Review correctness, data leakage, user-visible behavior, error handling and scope. Address findings and rerun affected checks. Record the reviewer and findings in the PR; agent review is not a human GitHub approval.
- Require relevant local checks and GitHub CI to pass on the final PR head before merging. The coordinator verifies the actual diff and review evidence, then squash-merges within the user's authorized scope.
- Resolve conflicts in the feature branch and repeat affected verification. Never bypass checks, force-push `main`, or mix another engineer's changes into a PR.
- After merge, sync `main`, confirm integrated checks and update the daily report with PR links and any unmet acceptance criteria. A feature is rolled out when its reviewed PR is merged and integrated behavior is verified; publishing a hosted application is a separate action.

## Implementation and evidence

- Use the smallest maintainable solution that satisfies the day's acceptance criteria. Add meaningful tests for data boundaries, causal histories, persistence and API contracts; avoid tests that only restate implementation.
- Preserve the prediction contract: only earlier observed interactions and candidate statement/concepts; never candidate code/outcomes or future interactions. Fit transforms on training data and calibrate on validation only.
- Keep raw student data, submitted code, generated artifacts, credentials and local databases out of public git. Verify release-specific access/usage/redistribution terms before importing real data; public download availability alone is not permission to republish it.
- Label synthetic fixtures, untrained heuristics and uncalibrated estimates clearly. Call concept outputs estimated performance, not proven mastery. Separate prediction metrics from recommendation learning-effectiveness claims.
- When access or compute blocks empirical work, finish independent engineering work and document the blocked deliverable without inventing results or silently substituting a different dataset.
- Keep setup instructions, contracts and reports aligned with actual behavior. Use client dates for execution reports; sprint day numbers are work units, not claims about when the work was performed.
