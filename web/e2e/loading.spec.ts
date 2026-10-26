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
