import { expect, test, type APIRequestContext, type Page, type Route } from "@playwright/test";

const paths = ["/models/current", "/exercises", "/students/demo/history", "/students/demo/profile", "/students/demo/recommendations"];

async function delayedWorkspace(page: Page, request: APIRequestContext) {
  const payloads = new Map(await Promise.all(paths.map(async (path) =>
    [path, await (await request.get(`/api${path}`)).json()] as const)));
  const batches = [new Map<string, Route>(), new Map<string, Route>()];
  const counts = new Map<string, number>();
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname.replace(/^\/api/, "");
    if (!payloads.has(path)) { await route.fallback(); return; }
    const batch = counts.get(path) ?? 0;
    counts.set(path, batch + 1);
    batches[batch].set(path, route);
  });
  await page.goto("/");
  await expect.poll(() => batches.map((batch) => batch.size)).toEqual([5, 5]);
  return async (batch: 0 | 1, fail = false) => {
    await Promise.all([...batches[batch]].map(([path, route]) => route.fulfill({
      status: fail && path === "/models/current" ? 500 : 200,
      json: path === "/models/current" ? { ...payloads.get(path), dataset_version: batch ? "synthetic-newer" : "synthetic-older" } : payloads.get(path),
    })));
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
