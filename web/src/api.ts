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
  concepts: {
    concept_id: string;
    estimated_performance: number;
    supporting_attempts: number;
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
