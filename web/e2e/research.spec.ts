import { expect, test, type Page, type Route } from "@playwright/test";
import type { ResearchInput } from "../src/api";

const model = {
  model_kind: "logistic", variant: null, model_version: "logistic-baseline-v1",
  feature_version: "historical-numeric-v1", artifact_version: "portable-baseline-artifact-v1",
  model_sha256: "a".repeat(64), dataset_version: "synthetic-inspector-v1", source_kind: "synthetic",
  is_synthetic: true, calibrated: false, research_results: false,
  provenance: { dataset_version: "synthetic-inspector-v1", source_kind: "synthetic", source_sha256: "b".repeat(64),
    split_version: "student-split-v1", split_sha256: "c".repeat(64), fit_partition: "train" },
};
const json = (route: Route, value: unknown, status = 200) => route.fulfill({ status, json: value });
const prediction = (problem_id: string, probability = .73) => ({ model, predictions: [{ problem_id, predicted_correctness: probability }] });
const calibratedModel = {
  ...model, calibrated: true, artifact_version: "temperature-baseline-artifact-v1",
  base_artifact_version: model.artifact_version, base_artifact_sha256: "d".repeat(64), artifact_sha256: "e".repeat(64),
  calibration: { method: "temperature-scaling-v1", temperature: 2,
    validation_record: { fit_partition: "validation", provenance: model.provenance,
      validation_sha256: "f".repeat(64), probabilities_sha256: "0".repeat(64), n_examples: 12, temperature_grid: [1, 2] } },
};

async function workspace(page: Page) {
  // Intentionally out of order; retry position 8 must advance target timing but
  // never become a primary history response. All fixtures are synthetic.
  const history = [
    { student_id: "demo", problem_id: "java-even", sequence_index: 8, attempt_number: 2, correct: true },
    { student_id: "demo", problem_id: "java-even", sequence_index: 1, attempt_number: 1, correct: false },
    { student_id: "demo", problem_id: "java-sum", sequence_index: 0, attempt_number: 1, correct: true },
  ];
  const bundle = await (await page.request.get("/api/students/demo/workspace")).json();
  await page.route("**/api/students/demo/workspace", (route) => json(route, { ...bundle, history }));
  await page.route("**/api/attempts", async (route) => {
    const body = route.request().postDataJSON();
    const row = { ...body, sequence_index: Math.max(...history.map((item) => item.sequence_index)) + 1,
      attempt_number: history.filter((item) => item.problem_id === body.problem_id).length + 1 };
    history.push(row);
    await json(route, row, 201);
  });
  await page.route("**/api/research/model", (route) => json(route, model));
  await page.goto("/");
  await page.getByLabel("Exercise library").selectOption("java-count");
  return page.getByRole("region", { name: "Fitted baseline inspection" });
}

test("inspection sends causal first attempts and refreshes after replay", async ({ page }, testInfo) => {
  const bodies: { inputs: ResearchInput[] }[] = [];
  await page.route("**/api/research/predict", async (route) => {
    const body = route.request().postDataJSON();
    bodies.push(body);
    await json(route, prediction(body.inputs[0].candidate.problem_id));
  });
  const pane = await workspace(page);
  expect(bodies).toHaveLength(0);
  await pane.getByRole("button", { name: "Inspect fitted baseline", exact: true }).click();
  await expect(pane).toContainText("73%");
  await expect(pane).toContainText("Synthetic fitted estimate · Uncalibrated");
  await expect(pane).toContainText("logistic-baseline-v1");
  await expect(pane).toContainText("synthetic-inspector-v1");
  const query = bodies[0].inputs[0];
  expect(Object.keys(query).sort()).toEqual(["candidate", "history", "student_id", "target_sequence_index"]);
  expect(query.target_sequence_index).toBe(9);
  expect(query.history.map((row: { sequence_index: number }) => row.sequence_index)).toEqual([0, 1]);
  expect(query.history.every((row: { attempt_number: number; problem_text: string; concept_ids: string[] }) =>
    row.attempt_number === 1 && row.problem_text.length > 0 && row.concept_ids.length > 0)).toBe(true);
  expect(Object.keys(query.candidate).sort()).toEqual(["concept_ids", "problem_id", "problem_text"]);
  expect(JSON.stringify(query)).not.toContain("submitted_code");
  await pane.screenshot({ path: testInfo.outputPath("fitted-inspector.png") });
  await page.getByRole("button", { name: "Simulate correct", exact: true }).click();
  await expect(page.getByText("Simulated correct outcome recorded as interaction 9.")).toBeVisible();
  await expect(pane.getByRole("button", { name: "Inspect fitted baseline", exact: true })).toBeVisible();
  await pane.getByRole("button", { name: "Inspect fitted baseline", exact: true }).click();
  await expect(pane).toContainText("requires a new exercise");
  expect(bodies).toHaveLength(1);
  await expect(page.getByRole("button", { name: "Simulate incorrect", exact: true })).toBeEnabled();
  await page.getByLabel("Exercise library").selectOption("java-find");
  await pane.getByRole("button", { name: "Inspect fitted baseline", exact: true }).click();
  await expect(pane).toContainText("73%");
  expect(bodies[1].inputs[0].target_sequence_index).toBe(10);
  expect(bodies[1].inputs[0].history.map((row: { sequence_index: number }) => row.sequence_index)).toEqual([0, 1, 9]);
});

test("unconfigured and failed research requests leave the demo usable and can retry", async ({ page }) => {
  const pane = await workspace(page);
  await page.route("**/api/research/model", (route) => json(route, { detail: "research_model_not_configured" }, 503));
  await pane.getByRole("button", { name: "Inspect fitted baseline", exact: true }).click();
  await expect(pane).toContainText("No fitted baseline configured");
  await expect(page.getByRole("button", { name: "Simulate correct", exact: true })).toBeEnabled();
  await pane.getByRole("button", { name: "Hide fitted baseline" }).click();
  await page.route("**/api/research/model", (route) => json(route, model));
  await page.route("**/api/research/predict", (route) => json(route, { detail: "unavailable" }, 503));
  await pane.getByRole("button", { name: "Inspect fitted baseline", exact: true }).click();
  await expect(pane.getByRole("alert")).toContainText("Fitted baseline unavailable");
  await page.route("**/api/research/predict", (route) => json(route, prediction("java-count")));
  await pane.getByRole("button", { name: "Retry inspection" }).click();
  await expect(pane).toContainText("73%");
  await expect(page.locator("footer")).toContainText("demo-history-v1");
});

test("selection and hiding cancel pending results and previously attempted candidates never request", async ({ page }) => {
  const pending: Route[] = [];
  await page.route("**/api/research/predict", (route) => { pending.push(route); });
  const pane = await workspace(page);
  await pane.getByRole("button", { name: "Inspect fitted baseline", exact: true }).click();
  await expect.poll(() => pending.length).toBe(1);
  await page.getByLabel("Exercise library").selectOption("java-find");
  await json(pending[0], prediction("java-count", .99)).catch(() => {});
  await expect(pane).not.toContainText("99%");
  await pane.getByRole("button", { name: "Inspect fitted baseline", exact: true }).click();
  await expect.poll(() => pending.length).toBe(2);
  await pane.getByRole("button", { name: "Hide fitted baseline" }).click();
  await json(pending[1], prediction("java-find", .98)).catch(() => {});
  await expect(pane).not.toContainText("98%");
  await page.getByLabel("Exercise library").selectOption("java-even");
  await pane.getByRole("button", { name: "Inspect fitted baseline", exact: true }).click();
  await expect(pane).toContainText("requires a new exercise");
  expect(pending).toHaveLength(2);
});

for (const [name, change] of [
  ["missing calibration flag", { calibrated: undefined }],
  ["missing research-results flag", { research_results: undefined }],
  ["missing synthetic flag", { is_synthetic: undefined }],
  ["string synthetic flag", { is_synthetic: "yes" }],
  ["string calibration flag", { calibrated: "false" }],
  ["string research-results flag", { research_results: "false" }],
] as const) {
  test(`rejects ${name} instead of claiming synthetic uncalibrated output`, async ({ page }) => {
    const pane = await workspace(page);
    await page.route("**/api/research/predict", (route) => json(route, {
      ...prediction("java-count"), model: { ...model, ...change },
    }));
    await pane.getByRole("button", { name: "Inspect fitted baseline", exact: true }).click();
    await expect(pane.getByRole("alert")).toContainText("Unexpected research response");
    await expect(pane).not.toContainText("73%");
    await expect(pane).not.toContainText("Synthetic fitted estimate");
    await expect(page.getByRole("button", { name: "Simulate correct", exact: true })).toBeEnabled();
  });
}

for (const [name, change] of [
  ["unverified source", { source_kind: "unverified" }],
  ["validation fit", { fit_partition: "validation" }],
  ["different dataset", { dataset_version: "other" }],
  ["invalid source digest", { source_sha256: "bad" }],
  ["missing split digest", { split_sha256: undefined }],
  ["blank split version", { split_version: "" }],
] as const) {
  test(`uncalibrated response rejects ${name} and recovers on retry`, async ({ page }) => {
    const pane = await workspace(page);
    let malformed = true;
    await page.route("**/api/research/predict", (route) => json(route, {
      ...prediction("java-count"), model: malformed ? {
        ...model, provenance: { ...model.provenance, ...change },
      } : model,
    }));
    await pane.getByRole("button", { name: "Inspect fitted baseline", exact: true }).click();
    await expect(pane.getByRole("alert")).toContainText("Unexpected research response");
    await expect(pane).not.toContainText("73%");
    await expect(pane).not.toContainText("Synthetic fitted estimate");
    await expect(page.getByRole("button", { name: "Simulate correct", exact: true })).toBeEnabled();

    malformed = false;
    await pane.getByRole("button", { name: "Retry inspection" }).click();
    await expect(pane.getByRole("heading", { name: "Synthetic fitted estimate · Uncalibrated" })).toBeVisible();
    await expect(pane).toContainText("73%");
  });
}

test("calibrated inspection labels scaling and fitting limits without changing replay", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const pane = await workspace(page);
  await page.route("**/api/research/predict", (route) => json(route, {
    model: calibratedModel, predictions: [{ problem_id: "java-count", predicted_correctness: .62 }],
  }));
  await pane.getByRole("button", { name: "Inspect fitted baseline", exact: true }).click();
  await expect(pane.getByRole("heading", { name: "Temperature-scaled synthetic estimate" })).toBeVisible();
  await expect(pane).toContainText("62%");
  await expect(pane).toContainText("Temperature: 2 · Fitted on 12 validation examples");
  await expect(pane).toContainText("reliability has not been independently established");
  await expect(pane).not.toContainText("Uncalibrated");
  await pane.getByText("Inspect declared calibration record").click();
  await expect(pane).toContainText("temperature-scaling-v1");
  await expect(pane).toContainText(calibratedModel.artifact_sha256);
  await expect(pane).toContainText("Declared hashes do not authenticate provenance");
  expect(await pane.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
  await pane.screenshot({ path: testInfo.outputPath("calibrated-inspector-mobile.png") });
  await expect(page.locator("footer")).toContainText("demo-history-v1");
  await expect(page.getByRole("button", { name: "Simulate correct", exact: true })).toBeEnabled();
});

for (const [name, change] of [
  ["unknown envelope", { artifact_version: "future-envelope" }],
  ["unknown method", { calibration: { ...calibratedModel.calibration, method: "future-method" } }],
  ["invalid temperature", { calibration: { ...calibratedModel.calibration, temperature: 0 } }],
  ["missing receipt", { calibration: { method: "temperature-scaling-v1", temperature: 2 } }],
  ["wrong fitting partition", { calibration: { ...calibratedModel.calibration,
    validation_record: { ...calibratedModel.calibration.validation_record, fit_partition: "test" } } }],
  ["mismatched provenance", { calibration: { ...calibratedModel.calibration,
    validation_record: { ...calibratedModel.calibration.validation_record, provenance: { ...model.provenance, dataset_version: "different" } } } }],
  ["invalid fitting hash", { calibration: { ...calibratedModel.calibration,
    validation_record: { ...calibratedModel.calibration.validation_record, validation_sha256: "bad" } } }],
  ["string calibration declaration", { calibrated: "true" }],
  ["contradictory uncalibrated envelope", { calibrated: false }],
] as const) {
  test(`calibrated response rejects ${name}`, async ({ page }) => {
    const pane = await workspace(page);
    await page.route("**/api/research/predict", (route) => json(route, {
      model: { ...calibratedModel, ...change }, predictions: [{ problem_id: "java-count", predicted_correctness: .62 }],
    }));
    await pane.getByRole("button", { name: "Inspect fitted baseline", exact: true }).click();
    await expect(pane.getByRole("alert")).toContainText("Unexpected research response");
    await expect(pane).not.toContainText("62%");
    await expect(page.getByRole("button", { name: "Simulate correct", exact: true })).toBeEnabled();
  });
}
