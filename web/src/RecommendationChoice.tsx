import { useEffect, useRef, useState } from "react";
import { recordRecommendationChoice } from "./api";

export default function RecommendationChoice({ snapshotId, problemId, busy }: { snapshotId: string; problemId: string; busy: boolean }) {
  const [state, setState] = useState<"idle" | "pending" | "recorded" | "error">("idle");
  const [error, setError] = useState("");
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);

  async function choose() {
    if (busy || pending.current || state === "recorded") return;
    const controller = new AbortController();
    pending.current = controller;
    setState("pending");
    setError("");
    try {
      await recordRecommendationChoice(snapshotId, problemId, controller.signal);
      if (!controller.signal.aborted) setState("recorded");
    } catch (error) {
      if (!controller.signal.aborted) {
        setError(error instanceof Error ? error.message : "Could not record this choice. Please retry.");
        setState("error");
      }
    } finally {
      if (pending.current === controller) pending.current = null;
    }
  }

  return <section aria-label="Recommendation choice" className="simulation">
    <h3>Choose this recommendation</h3>
    <p>Record an explicit choice from this ranking. Simulated correctness is recorded separately.</p>
    <button onClick={() => void choose()} disabled={busy || state === "pending" || state === "recorded" || !/^[a-f0-9]{32}$/.test(snapshotId)}>
      {state === "recorded" ? "Choice recorded" : state === "error" ? "Retry choice" : "Choose this recommendation"}
    </button>
    <div aria-live="polite">
      {state === "pending" && <p role="status">Recording your choice…</p>}
      {state === "recorded" && <p role="status">Choice recorded for this recommendation snapshot. Simulated outcomes remain separate.</p>}
      {state === "error" && <div role="alert"><p>{error}</p><p>A failed request may already have recorded this choice. Retrying can create another choice event.</p></div>}
    </div>
  </section>;
}
