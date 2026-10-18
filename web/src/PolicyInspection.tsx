import type { Ranking } from "./api";

export default function PolicyInspection({ ranking }: { ranking: Ranking }) {
  const config = ranking.policy_config;
  const fields = ["challenge_lower", "challenge_upper", "need_weight", "prerequisite_penalty", "repeat_penalty", "prerequisite_threshold"] as const;
  const valid = ranking.is_demo === true && ranking.student_id === "demo" &&
    ranking.policy_version === "transparent-ranking-v2" && config?.policy_version === ranking.policy_version &&
    typeof ranking.policy_sha256 === "string" && /^[a-f0-9]{64}$/.test(ranking.policy_sha256) &&
    Object.keys(config).length === fields.length + 1 &&
    fields.every((field) => Number.isFinite(config[field]) && config[field] >= 0 && config[field] <= 1) &&
    config.challenge_lower < config.challenge_upper;

  return <aside className="reason-box policy-inspection" aria-label="Practice policy inspection">
    <h3>Configured heuristic policy</h3>
    {valid ? <>
      <p>Heuristic challenge band: <strong>{(config.challenge_lower * 100).toFixed(1)}–{(config.challenge_upper * 100).toFixed(1)}%</strong> estimated correctness.</p>
      <p>Ranks demo heuristic estimates and observed history. Learning benefits of this range have not been measured.</p>
      <p>Fitted-model inspection operates separately from this ranking policy.</p>
      <details className="policy-record">
        <summary>Inspect policy configuration</summary>
        <pre><code>{JSON.stringify(config, null, 2)}</code></pre>
        <p>Declared policy SHA-256: <code>{ranking.policy_sha256}</code></p>
        <p>This declared hash identifies a configuration; it does not authenticate results.</p>
      </details>
    </> : <p>Policy configuration unavailable. Recommendations and replay remain available.</p>}
  </aside>;
}
