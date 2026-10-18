import { useEffect, useState } from "react";
import { getResearchModel, predictResearch, type Exercise, type ResearchInput, type ResearchPrediction, type Snapshot } from "./api";

function inputFor(snapshot: Snapshot, candidate: Exercise): ResearchInput {
  const catalog = new Map(snapshot.exercises.map((exercise) => [exercise.problem_id, exercise]));
  const history = snapshot.history.filter((row) => row.attempt_number === 1)
    .sort((a, b) => a.sequence_index - b.sequence_index).map((row) => {
      const exercise = catalog.get(row.problem_id);
      if (!exercise) throw new Error("History exercise metadata is missing. Refresh the workspace before inspection.");
      return { student_id: "demo", problem_id: row.problem_id, sequence_index: row.sequence_index,
        correct: row.correct, attempt_number: row.attempt_number,
        problem_text: exercise.problem_text, concept_ids: exercise.concept_ids };
    });
  return { student_id: "demo", target_sequence_index: Math.max(-1, ...snapshot.history.map((row) => row.sequence_index)) + 1,
    history, candidate: { problem_id: candidate.problem_id, problem_text: candidate.problem_text, concept_ids: candidate.concept_ids } };
}

type State = { status: "idle" | "loading" | "unconfigured" | "error"; message?: string } |
  { status: "ready"; result: ResearchPrediction };

export default function ResearchInspector({ snapshot, candidate, busy }: { snapshot: Snapshot; candidate: Exercise; busy: boolean }) {
  const [enabled, setEnabled] = useState(false);
  const [retry, setRetry] = useState(0);
  const [state, setState] = useState<State>({ status: "idle" });
  const attempted = snapshot.history.some((row) => row.problem_id === candidate.problem_id);

  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "idle" });
    if (!enabled || attempted || busy) return () => controller.abort();
    setState({ status: "loading" });
    void (async () => {
      try {
        const model = await getResearchModel(controller.signal);
        if (controller.signal.aborted) return;
        if (!model) { setState({ status: "unconfigured" }); return; }
        const result = await predictResearch(inputFor(snapshot, candidate), controller.signal);
        if (controller.signal.aborted) return;
        if (!result) { setState({ status: "unconfigured" }); return; }
        const score = result.predictions[0];
        if (!result.model.is_synthetic || result.model.source_kind !== "synthetic" || result.model.calibrated || result.model.research_results ||
            result.predictions.length !== 1 || score.problem_id !== candidate.problem_id ||
            !Number.isFinite(score.predicted_correctness) || score.predicted_correctness < 0 || score.predicted_correctness > 1)
          throw new Error("Unexpected research response. Retry inspection.");
        setState({ status: "ready", result });
      } catch (error) {
        if (!controller.signal.aborted) setState({ status: "error", message: error instanceof Error ? error.message : "Inspection failed. Please retry." });
      }
    })();
    return () => controller.abort();
  }, [enabled, attempted, busy, retry, snapshot, candidate]);

  return <section className="simulation" aria-label="Fitted baseline inspection">
    <h3>Fitted baseline inspection</h3>
    <p>Optional synthetic model inspection. Replay estimates and rankings use the demo heuristic.</p>
    <button aria-pressed={enabled} disabled={busy} onClick={() => setEnabled(!enabled)}>
      {enabled ? "Hide fitted baseline" : "Inspect fitted baseline"}
    </button>
    {enabled && <div aria-live="polite">
      {attempted ? <p>A first-attempt model requires a new exercise. This exercise already appears in history; demo retries remain available.</p> :
        busy ? <p>Waiting for the refreshed history.</p> :
        state.status === "loading" ? <p role="status">Inspecting fitted baseline…</p> :
        state.status === "unconfigured" ? <p>No fitted baseline configured. The demo remains available.</p> :
        state.status === "error" ? <div role="alert"><p>{state.message}</p><button onClick={() => setRetry(retry + 1)}>Retry inspection</button></div> :
        state.status === "ready" ? <div className="reason-box">
          <h3>Synthetic fitted estimate · Uncalibrated</h3>
          <p>Predicted correctness: <strong>{Math.round(state.result.predictions[0].predicted_correctness * 100)}%</strong></p>
          <p>Model: <code>{state.result.model.model_kind} / {state.result.model.model_version}</code></p>
          <p>Dataset: <code>{state.result.model.dataset_version}</code></p>
          <p>Software-test output; no measured research result or learning gain.</p>
        </div> : null}
    </div>}
  </section>;
}
