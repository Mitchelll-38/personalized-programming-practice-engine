export type Exercise = {
  problem_id: string;
  title: string;
  problem_text: string;
  concept_ids: string[];
  prerequisites: string[];
};
export type Interaction = {
  student_id: string;
  problem_id: string;
  sequence_index: number;
  correct: boolean;
  attempt_number: number;
};
export type Profile = {
  student_id: string;
  is_demo: boolean;
  total_interactions: number;
  first_attempts: number;
  retries: number;
  concepts: {
    concept_id: string;
    estimated_performance: number;
    supporting_attempts: number;
    supporting_problem_ids: string[];
    evidence_status: "no-history" | "limited-history" | "observed-first-attempt";
  }[];
};
export type Recommendation = {
  problem_id: string;
  title: string;
  concept_ids: string[];
  predicted_correctness: number;
  score: number;
  reasons: string[];
};
export type Ranking = {
  student_id: string;
  is_demo: boolean;
  policy_version: string;
  snapshot_id: string;
  history_sequence_index: number;
  policy_config?: PracticePolicy | null;
  policy_sha256?: string | null;
  recommendations: Recommendation[];
};
export type PracticePolicy = {
  policy_version: "transparent-ranking-v2";
  challenge_lower: number;
  challenge_upper: number;
  need_weight: number;
  prerequisite_penalty: number;
  repeat_penalty: number;
  prerequisite_threshold: number;
};
export type Model = {
  model_id: string;
  dataset_version: string;
  is_demo: boolean;
  calibrated: boolean;
};
type WorkspaceCore = {
  model: Model;
  exercises: Exercise[];
  history: Interaction[];
  profile: Profile;
};
export type Snapshot = WorkspaceCore & (
  { ranking: Ranking; ranking_error?: never } |
  { ranking: null; ranking_error: "practice_policy_unavailable" }
);

export class ApiHttpError extends Error {
  constructor(readonly status: number, message: string) {
    super(message);
    this.name = "ApiHttpError";
  }
}

async function request<T>(path: string, options?: RequestInit, errors?: Partial<Record<number, string>>): Promise<T> {
  const response = await fetch(`/api${path}`, options);
  if (!response.ok)
    throw new ApiHttpError(response.status,
      errors?.[response.status] ?? `API request failed (${response.status}). Check that the local API is running, then retry.`,
    );
  return response.json() as Promise<T>;
}

const object = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === "object" && !Array.isArray(value);
const text = (value: unknown): value is string => typeof value === "string";
const strings = (value: unknown): value is string[] => Array.isArray(value) && value.every(text);
const count = (value: unknown): value is number => Number.isSafeInteger(value) && (value as number) >= 0;
const probability = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1;

function validWorkspace(value: unknown): value is Snapshot {
  if (!object(value) || !object(value.model) || !Array.isArray(value.exercises) ||
      !Array.isArray(value.history) || !object(value.profile)) return false;
  const { model, exercises, history, profile, ranking } = value;
  if (!text(model.model_id) || !text(model.dataset_version) || model.is_demo !== true ||
      typeof model.calibrated !== "boolean" ||
      !exercises.every((item) => object(item) && text(item.problem_id) && text(item.title) &&
        text(item.problem_text) && strings(item.concept_ids) && strings(item.prerequisites)) ||
      !history.every((item) => object(item) && item.student_id === "demo" && text(item.problem_id) &&
        count(item.sequence_index) && count(item.attempt_number) && item.attempt_number > 0 &&
        typeof item.correct === "boolean") ||
      profile.student_id !== "demo" || profile.is_demo !== true ||
      !count(profile.total_interactions) || !count(profile.first_attempts) || !count(profile.retries) ||
      !Array.isArray(profile.concepts) ||
      !profile.concepts.every((item) => object(item) && text(item.concept_id) &&
        probability(item.estimated_performance) && count(item.supporting_attempts) &&
        strings(item.supporting_problem_ids) &&
        ["no-history", "limited-history", "observed-first-attempt"].includes(item.evidence_status as string)))
    return false;
  if (ranking === null) return value.ranking_error === "practice_policy_unavailable";
  return value.ranking_error === undefined && object(ranking) &&
    text(ranking.policy_version) && typeof ranking.snapshot_id === "string" &&
    /^[a-f0-9]{32}$/.test(ranking.snapshot_id) &&
    Number.isSafeInteger(ranking.history_sequence_index) && (ranking.history_sequence_index as number) >= -1 &&
    Array.isArray(ranking.recommendations) &&
    ranking.recommendations.every((item) => object(item) && text(item.problem_id) &&
      text(item.title) && strings(item.concept_ids) && probability(item.predicted_correctness) &&
      typeof item.score === "number" && Number.isFinite(item.score) && strings(item.reasons));
}

export async function getSnapshot(): Promise<Snapshot> {
  const view = await request<unknown>("/students/demo/workspace");
  if (!validWorkspace(view))
    throw new Error("Unexpected workspace response. Refresh the workspace before replaying.");
  return view;
}

export type AttemptIntent = {
  problem_id: string;
  correct: boolean;
  choice_id?: string;
  request_id: string;
};

export async function recordOutcome(intent: AttemptIntent): Promise<Interaction> {
  const receipt = await request<unknown>("/attempts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ student_id: "demo", ...intent }),
  }, intent.choice_id !== undefined ? {
    404: "Recorded choice or exercise was not found. The rejected link was cleared; choose again to start a new simulation.",
    422: "Recorded choice does not match this exercise. The rejected link was cleared; choose again to start a new simulation.",
    409: "Recorded choice already has a different simulated outcome. The rejected link was cleared; choose again to start a new simulation.",
  } : { 409: "This simulation request already has a different outcome. Choose a new result to start a new simulation." });
  if (!receipt || typeof receipt !== "object" || Array.isArray(receipt))
    throw new Error("Unexpected attempt receipt. The outcome may already be saved; retry the same result to check its receipt.");
  const row = receipt as Record<string, unknown>;
  if (row.student_id !== "demo" || row.problem_id !== intent.problem_id || row.correct !== intent.correct ||
      !Number.isSafeInteger(row.sequence_index) || (row.sequence_index as number) < 0 ||
      !Number.isSafeInteger(row.attempt_number) || (row.attempt_number as number) < 1)
    throw new Error("Unexpected attempt receipt. The outcome may already be saved; retry the same result to check its receipt.");
  return receipt as Interaction;
}

export type RecommendationChoice = {
  choice_id: string;
  created_at: string;
  snapshot_id: string;
  problem_id: string;
};

export async function recordRecommendationChoice(snapshot_id: string, problem_id: string, signal: AbortSignal): Promise<RecommendationChoice> {
  const response = await fetch("/api/recommendation-choices", {
    method: "POST", signal, headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ snapshot_id, problem_id }),
  });
  if (response.status !== 201) throw new Error(`Could not record this choice (${response.status}). Retry or refresh the workspace.`);
  const choice = await response.json() as RecommendationChoice;
  if (!choice || typeof choice.choice_id !== "string" || !/^[a-f0-9]{32}$/.test(choice.choice_id) ||
      choice.snapshot_id !== snapshot_id || choice.problem_id !== problem_id ||
      typeof choice.created_at !== "string" || !/(Z|\+00:00)$/.test(choice.created_at) || !Number.isFinite(Date.parse(choice.created_at)))
    throw new Error("Unexpected choice acknowledgement. The request may already have been recorded.");
  return choice;
}

type ResearchBaseModel = {
  model_kind: "rate" | "logistic" | "bkt";
  variant: "global" | "problem" | null;
  model_version: string;
  feature_version: string;
  artifact_version: string;
  model_sha256: string;
  dataset_version: string;
  source_kind: "synthetic";
  is_synthetic: true;
  research_results: false;
  provenance: {
    dataset_version: string;
    source_kind: "synthetic";
    source_sha256: string;
    split_version: string;
    split_sha256: string;
    fit_partition: "train";
  };
};
export type ResearchModel = ResearchBaseModel & ({ calibrated: false } | {
  calibrated: true;
  artifact_version: "temperature-baseline-artifact-v1";
  base_artifact_version: "rate-artifact-v1" | "portable-baseline-artifact-v1";
  base_artifact_sha256: string;
  artifact_sha256: string;
  calibration: {
    method: "temperature-scaling-v1";
    temperature: number;
    validation_record: {
      fit_partition: "validation";
      provenance: ResearchBaseModel["provenance"];
      validation_sha256: string;
      probabilities_sha256: string;
      n_examples: number;
      temperature_grid: number[];
    };
  };
});
export type ResearchInput = {
  student_id: "demo";
  target_sequence_index: number;
  history: (Interaction & Pick<Exercise, "problem_text" | "concept_ids">)[];
  candidate: Pick<Exercise, "problem_id" | "problem_text" | "concept_ids">;
};
export type ResearchPrediction = {
  model: ResearchModel;
  predictions: { problem_id: string; predicted_correctness: number }[];
};

async function researchRequest<T>(path: string, signal: AbortSignal, body?: ResearchInput): Promise<T | null> {
  const response = await fetch(`/api/research/${path}`, {
    signal,
    ...(body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ inputs: [body] }) } : {}),
  });
  if (response.status === 503) {
    const error = await response.json();
    if (error.detail === "research_model_not_configured") return null;
  }
  if (!response.ok) throw new Error("Fitted baseline unavailable. Check the local research model and retry inspection.");
  return response.json() as Promise<T>;
}

export const getResearchModel = (signal: AbortSignal) => researchRequest<ResearchModel>("model", signal);
export const predictResearch = (query: ResearchInput, signal: AbortSignal) => researchRequest<ResearchPrediction>("predict", signal, query);
