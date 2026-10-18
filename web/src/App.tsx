import { useCallback, useEffect, useState } from "react";
import { getSnapshot, recordOutcome, type Snapshot } from "./api";
import ResearchInspector from "./ResearchInspector";

const label = (id: string) => id.replace(/[_-]/g, " ");
const percent = (value: number) => `${Math.round(value * 100)}%`;

export default function App() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [refreshPending, setRefreshPending] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const next = await getSnapshot();
      setSnapshot(next);
      setSelectedId((current) =>
        next.exercises.some((item) => item.problem_id === current)
          ? current
          : (next.ranking.recommendations[0]?.problem_id ??
            next.exercises[0]?.problem_id ??
            ""),
      );
      setRefreshPending(false);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not reach the local API. Start the server and retry.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function simulate(correct: boolean) {
    if (!selectedId || saving) return;
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const stored = await recordOutcome(selectedId, correct);
      setNotice(
        `Simulated ${correct ? "correct" : "incorrect"} outcome recorded as interaction ${stored.sequence_index}.`,
      );
      setRefreshPending(true);
      await load();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not record this outcome. Please retry.",
      );
    } finally {
      setSaving(false);
    }
  }

  const selected = snapshot?.exercises.find(
    (item) => item.problem_id === selectedId,
  );
  const selectedRanking = snapshot?.ranking.recommendations.find(
    (item) => item.problem_id === selectedId,
  );
  const correctCount =
    snapshot?.history.filter((item) => item.correct).length ?? 0;

  return (
    <div className="workspace">
      <header className="topbar">
        <a className="brand" href="#main">
          <span className="brand-mark" aria-hidden="true">
            p.
          </span>{" "}
          Practice Engine
        </a>
        <span className="workspace-label">
          Research workspace <span className="divider">/</span> Demo
        </span>
      </header>
      <main id="main">
        <div className="page-heading">
          <div>
            <p className="eyebrow">PERSONALIZED PROGRAMMING PRACTICE</p>
            <h1>A clearer next step.</h1>
            <p className="lede">
              Explore how a learner’s history shapes their next Java exercise.
            </p>
          </div>
          <div className="learner">
            <span className="avatar" aria-hidden="true">
              D
            </span>
            <div>
              <strong>Demo learner</strong>
              <span>Synthetic interaction history</span>
            </div>
          </div>
        </div>
        <aside className="demo-banner">
          <span className="status-dot" aria-hidden="true" />
          <div>
            <strong>Synthetic research demo</strong>
            <p>
              Untrained heuristic estimates, uncalibrated predictions, and
              simulated outcomes. Exercises are for inspection; Java code
              execution is not available.
            </p>
          </div>
        </aside>
        <div aria-live="polite" className="feedback">
          {notice && <p className="notice">{notice}</p>}
          {error && (
            <div role="alert" className="error">
              <p>{error}</p>
              <button onClick={() => void load()} disabled={loading || saving}>
                Retry connection
              </button>
              {refreshPending && (
                <p>
                  The outcome was saved. Refresh the workspace before recording
                  another outcome.
                </p>
              )}
            </div>
          )}
        </div>
        {loading && !snapshot ? (
          <div className="empty loading" role="status">
            Connecting to the local research API…
          </div>
        ) : !snapshot ? (
          <div className="empty">
            <h2>Workspace unavailable</h2>
            <p>
              Start the FastAPI server on port 8000 to load the demo learner.
            </p>
            <code>uvicorn api.main:app --reload</code>
          </div>
        ) : (
          <>
            <section className="summary" aria-label="Learner summary">
              <div>
                <span className="eyebrow">RECORDED INTERACTIONS</span>
                <strong>
                  {snapshot.profile.total_interactions.toString().padStart(2, "0")}
                </strong>
                <p>{correctCount} simulated correct outcomes across all interactions</p>
                <p>{snapshot.profile.first_attempts} distinct first attempts · {snapshot.profile.retries} retries excluded from estimates</p>
              </div>
              <div>
                <span className="eyebrow">CONCEPTS IN PROFILE</span>
                <strong>
                  {snapshot.profile.concepts.length.toString().padStart(2, "0")}
                </strong>
                <p>History-based demo estimates</p>
              </div>
              <div>
                <span className="eyebrow">RECOMMENDATION POLICY</span>
                <strong className="policy">
                  {snapshot.ranking.policy_version}
                </strong>
                <p>Ranked by a transparent heuristic</p>
              </div>
            </section>
            <div className="main-grid">
              <section className="panel recommendations">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">01 / NEXT EXERCISES</p>
                    <h2>Recommended practice</h2>
                  </div>
                  <span className="small-tag">Demo ranking</span>
                </div>
                <p className="section-note">
                  Select an exercise to inspect its prompt and ranking reasons.
                </p>
                {snapshot.ranking.recommendations.length ? (
                  <ol className="recommendation-list">
                    {snapshot.ranking.recommendations.map((item, index) => (
                      <li key={item.problem_id}>
                        <button
                          className={`recommendation ${selectedId === item.problem_id ? "selected" : ""}`}
                          aria-pressed={selectedId === item.problem_id}
                          onClick={() => setSelectedId(item.problem_id)}
                        >
                          <span className="rank">
                            {String(index + 1).padStart(2, "0")}
                          </span>
                          <span className="recommendation-copy">
                            <strong>{item.title}</strong>
                            <span>
                              {item.concept_ids.map(label).join(" · ")}
                            </span>
                          </span>
                          <span className="probability">
                            <strong>
                              {percent(item.predicted_correctness)}
                            </strong>
                            <span>demo estimate</span>
                          </span>
                        </button>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="empty compact">
                    No recommendations yet. Choose an exercise from the library
                    below.
                  </p>
                )}
                <div className="library">
                  <label htmlFor="exercise-picker">Exercise library</label>
                  <select
                    id="exercise-picker"
                    value={selectedId}
                    onChange={(event) => setSelectedId(event.target.value)}
                    disabled={!snapshot.exercises.length}
                  >
                    {!snapshot.exercises.length && (
                      <option value="">No exercises available</option>
                    )}
                    {snapshot.exercises.map((item) => (
                      <option key={item.problem_id} value={item.problem_id}>
                        {item.title}
                      </option>
                    ))}
                  </select>
                </div>
              </section>
              <section className="panel exercise">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">02 / EXERCISE INSPECTOR</p>
                    <h2>{selected?.title ?? "Select an exercise"}</h2>
                  </div>
                  <span className="small-tag neutral">Java</span>
                </div>
                {selected ? (
                  <>
                    <div className="tags">
                      {selected.concept_ids.map((concept) => (
                        <span key={concept}>{label(concept)}</span>
                      ))}
                    </div>
                    <p className="problem-text">{selected.problem_text}</p>
                    <p className="prerequisites">
                      <strong>Prerequisites</strong>{" "}
                      {selected.prerequisites.length
                        ? selected.prerequisites.map(label).join(", ")
                        : "None"}
                    </p>
                    {selectedRanking && (
                      <div className="reason-box">
                        <h3>Why this exercise?</h3>
                        <ul>
                          {selectedRanking.reasons.map((reason, index) => (
                            <li key={index}>{reason}</li>
                          ))}
                        </ul>
                        <p>
                          Predicted correctness:{" "}
                          <strong>
                            {percent(selectedRanking.predicted_correctness)}
                          </strong>{" "}
                          · Ranking score: {selectedRanking.score.toFixed(3)}
                        </p>
                      </div>
                    )}
                    <ResearchInspector key={`${selectedId}:${JSON.stringify(snapshot.history)}`} snapshot={snapshot} candidate={selected} busy={saving || loading || refreshPending} />
                    <div className="simulation">
                      <h3>Replay a simulated outcome</h3>
                      <p>
                        Record a synthetic result to recalculate the concept
                        profile and recommendations. This does not grade code.
                      </p>
                      <div className="actions">
                        <button
                          className="primary"
                          onClick={() => void simulate(true)}
                          disabled={saving || loading || refreshPending}
                        >
                          Simulate correct
                        </button>
                        <button
                          onClick={() => void simulate(false)}
                          disabled={saving || loading || refreshPending}
                        >
                          Simulate incorrect
                        </button>
                      </div>
                      <span className="save-status" role="status">
                        {saving
                          ? "Saving outcome and refreshing estimates…"
                          : loading
                            ? "Refreshing workspace…"
                            : "Outcomes persist in the local demo database."}
                      </span>
                    </div>
                  </>
                ) : (
                  <p className="empty compact">
                    Select an available exercise to inspect its prompt.
                  </p>
                )}
              </section>
              <section className="panel concepts">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">03 / LEARNER PROFILE</p>
                    <h2>Concept estimates</h2>
                  </div>
                </div>
                <p className="section-note">
                  Estimated performance from synthetic history. These values are
                  not calibrated mastery scores. Labels describe evidence volume,
                  not confidence; limited history means one or two first attempts.
                </p>
                <div className="concept-list">
                  {snapshot.profile.concepts.length ? (
                    snapshot.profile.concepts.map((concept) => (
                      <div className="concept" key={concept.concept_id}>
                        <div>
                          <strong>{label(concept.concept_id)}</strong>
                          <span>{percent(concept.estimated_performance)}</span>
                        </div>
                        <meter
                          min="0"
                          max="1"
                          value={concept.estimated_performance}
                          aria-label={`${label(concept.concept_id)} estimated performance`}
                        />
                        <p>
                          {concept.evidence_status === "no-history"
                            ? "No history · 50% neutral prior; no personal evidence."
                            : `${concept.evidence_status === "limited-history" ? "Limited history" : "Observed first attempts"} · ${concept.supporting_attempts} distinct supporting exercises`}
                        </p>
                        {concept.supporting_problem_ids.length > 0 && (
                          <details className="concept-evidence">
                            <summary>Inspect supporting first attempts</summary>
                            <ul>
                              {concept.supporting_problem_ids.map((id) => (
                                <li key={id}>
                                  {snapshot.exercises.find((item) => item.problem_id === id)?.title ?? id}
                                  {" · "}{snapshot.history.find((item) => item.problem_id === id && item.attempt_number === 1)?.correct ? "Simulated correct" : "Simulated incorrect"}
                                </li>
                              ))}
                            </ul>
                          </details>
                        )}
                      </div>
                    ))
                  ) : (
                    <p className="empty compact">
                      No concept estimates available.
                    </p>
                  )}
                </div>
              </section>
              <section className="panel history">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">04 / INTERACTION LOG</p>
                    <h2>Recent history</h2>
                  </div>
                  <span className="small-tag neutral">Synthetic</span>
                </div>
                {snapshot.history.length ? (
                  <div className="table-scroll">
                    <table>
                      <caption className="sr-only">
                        Latest synthetic learner interactions
                      </caption>
                      <thead>
                        <tr>
                          <th scope="col">Sequence</th>
                          <th scope="col">Exercise</th>
                          <th scope="col">Attempt</th>
                          <th scope="col">Outcome</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[...snapshot.history]
                          .sort((a, b) => b.sequence_index - a.sequence_index)
                          .slice(0, 8)
                          .map((item) => (
                            <tr key={item.sequence_index}>
                              <td className="mono">
                                {String(item.sequence_index).padStart(2, "0")}
                              </td>
                              <td>
                                {snapshot.exercises.find(
                                  (exercise) =>
                                    exercise.problem_id === item.problem_id,
                                )?.title ?? item.problem_id}
                              </td>
                              <td>{item.attempt_number}</td>
                              <td>
                                <span
                                  className={`outcome ${item.correct ? "correct" : "incorrect"}`}
                                >
                                  {item.correct ? "Correct" : "Incorrect"}
                                </span>
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="empty compact">
                    No interactions recorded. Replay an outcome to start the
                    history.
                  </p>
                )}
                <p className="table-note">
                  Showing the latest {Math.min(snapshot.history.length, 8)} of{" "}
                  {snapshot.history.length} interactions.
                </p>
              </section>
            </div>
            <footer>
              <span>
                Model: <code>{snapshot.model.model_id}</code> · Dataset:{" "}
                <code>{snapshot.model.dataset_version}</code>
              </span>
              <span>Local research prototype · Untrained / uncalibrated</span>
            </footer>
          </>
        )}
      </main>
    </div>
  );
}
