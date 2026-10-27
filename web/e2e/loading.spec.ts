import { expect, test, type APIRequestContext, type Page, type Route } from "@playwright/test";

async function delayedWorkspace(page: Page, request: APIRequestContext) {
  const payload = await (await request.get("/api/students/demo/workspace")).json();
  const pending: Route[] = [];
  await page.route("**/api/students/demo/workspace", (route) => { pending.push(route); });
  await page.goto("/");
  await expect.poll(() => pending.length).toBe(2);
  return async (batch: 0 | 1, fail = false) => {
    await pending[batch].fulfill({ status: fail ? 500 : 200,
      json: { ...payload, model: { ...payload.model, dataset_version: batch ? "synthetic-newer" : "synthetic-older" } },
    });
    // Flush response microtasks and their React commit/effects before asserting
    // absence of stale UI updates; no timing-dependent request-count relaxation.
    await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  };
}

test("late initial success cannot replace a newer snapshot or retrigger inspection", async ({ page, request }) => {
  let predictions = 0;
  const model = { model_kind: "rate", variant: "problem", model_version: "rate-baseline-v1",
    artifact_version: "rate-artifact-v1", feature_version: "training-target-counts-v1", model_sha256: "a".repeat(64),
    dataset_version: "synthetic-inspection", source_kind: "synthetic", is_synthetic: true, calibrated: false, research_results: false,
    provenance: { dataset_version: "synthetic-inspection", source_kind: "synthetic", source_sha256: "b".repeat(64),
      split_version: "student-split-v1", split_sha256: "c".repeat(64), fit_partition: "train" } };
  await page.route("**/api/research/model", (route) => route.fulfill({ json: model }));
  await page.route("**/api/research/predict", async (route) => {
    predictions += 1;
    const query = route.request().postDataJSON().inputs[0];
    await route.fulfill({ json: { model,
      predictions: [{ problem_id: query.candidate.problem_id, predicted_correctness: .73 }] } });
  });
  const finish = await delayedWorkspace(page, request);
  await finish(1);
  await expect(page.locator("footer")).toContainText("synthetic-newer");
  await page.getByLabel("Exercise library").selectOption("java-count");
  const inspector = page.getByRole("region", { name: "Fitted baseline inspection" });
  await inspector.getByRole("button", { name: "Inspect fitted baseline", exact: true }).click();
  await expect(inspector).toContainText("73%");
  expect(predictions).toBe(1);
  await finish(0);
  await expect(page.locator("footer")).toContainText("synthetic-newer");
  await expect(inspector).toContainText("73%");
  expect(predictions).toBe(1);
});

test("late initial failure cannot publish an error after a newer success", async ({ page, request }) => {
  const finish = await delayedWorkspace(page, request);
  await finish(1);
  await expect(page.locator("footer")).toContainText("synthetic-newer");
  await finish(0, true);
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Simulate correct", exact: true })).toBeEnabled();
  await expect(page.locator("footer")).toContainText("synthetic-newer");
});

for (const [name, corrupt] of [
  ["history", (payload: any) => ({ ...payload, history: null })],
  ["model", (payload: any) => ({ ...payload, model: null })],
  ["catalog", (payload: any) => ({ ...payload, exercises: [{ ...payload.exercises[0], concept_ids: null }] })],
  ["profile", (payload: any) => ({ ...payload, profile: { ...payload.profile, concepts: null } })],
  ["ranking", (payload: any) => ({ ...payload, ranking: { ...payload.ranking, recommendations: null } })],
] as const) {
  test(`malformed successful ${name} response shows a recoverable error`, async ({ page, request }) => {
    const payload = await (await request.get("/api/students/demo/workspace")).json();
    const errors: string[] = [];
    let writes = 0;
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("request", (call) => {
      if (call.method() === "POST" && ["/api/attempts", "/api/recommendation-choices"].includes(new URL(call.url()).pathname))
        writes += 1;
    });
    let malformed = true;
    await page.route("**/api/students/demo/workspace", (route) => route.fulfill({
      status: 200, json: malformed ? corrupt(payload) : payload,
    }));
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Workspace unavailable" })).toBeVisible();
    await expect(page.getByRole("alert")).toContainText("Unexpected workspace response");
    await expect(page.getByRole("button", { name: "Simulate correct", exact: true })).toHaveCount(0);
    expect(errors).toEqual([]);
    expect(writes).toBe(0);

    malformed = false;
    await page.getByRole("button", { name: "Retry connection" }).click();
    await expect(page.getByRole("alert")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Simulate correct", exact: true })).toBeEnabled();
    expect(errors).toEqual([]);
    expect(writes).toBe(0);
  });
}

for (const failOlder of [false, true]) {
  test(`stale ${failOlder ? "failure" : "success"} cannot finish loading while newest batch is pending`, async ({ page, request }) => {
    const finish = await delayedWorkspace(page, request);
    await finish(0, failOlder);
    await expect(page.getByText("Connecting to the local research API…")).toBeVisible();
    await expect(page.getByRole("alert")).toHaveCount(0);
    await expect(page.locator("footer")).toHaveCount(0);
    // Latest failures still report a recoverable error and finish loading.
    await finish(1, true);
    await expect(page.getByRole("heading", { name: "Workspace unavailable" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Retry connection" })).toBeEnabled();
    await expect(page.getByRole("alert")).toHaveCount(1);
  });
}
