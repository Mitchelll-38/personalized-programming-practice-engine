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
  recommendations: Recommendation[];
};
export type Model = {
  model_id: string;
  dataset_version: string;
  is_demo: boolean;
  calibrated: boolean;
};
export type Snapshot = {
  model: Model;
  exercises: Exercise[];
  history: Interaction[];
  profile: Profile;
  ranking: Ranking;
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, options);
  if (!response.ok)
    throw new Error(
      `API request failed (${response.status}). Check that the local API is running, then retry.`,
    );
  return response.json() as Promise<T>;
}

export async function getSnapshot(): Promise<Snapshot> {
  const [model, exercises, history, profile, ranking] = await Promise.all([
    request<Model>("/models/current"),
    request<Exercise[]>("/exercises"),
    request<Interaction[]>("/students/demo/history"),
    request<Profile>("/students/demo/profile"),
    request<Ranking>("/students/demo/recommendations"),
  ]);
  return { model, exercises, history, profile, ranking };
}

export function recordOutcome(problem_id: string, correct: boolean) {
  return request<Interaction>("/attempts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ student_id: "demo", problem_id, correct }),
  });
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
