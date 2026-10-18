import { expect, test, type APIRequestContext, type Page, type Route } from "@playwright/test";

const acknowledgement = (body: { snapshot_id: string; problem_id: string }) => ({
  ...body, choice_id: "c".repeat(32), created_at: "2026-10-17T21:00:00Z",
});
const created = (route: Route) => route.fulfill({ status: 201, json: acknowledgement(route.request().postDataJSON()) });

async function workspace(page: Page, request: APIRequestContext) {
  const ranking = await (await request.get("/api/students/demo/recommendations")).json();
  let snapshot = "a".repeat(32);
  const history: { student_id: string; problem_id: string; sequence_index: number; correct: boolean; attempt_number: number }[] = [];
  await page.route("**/api/students/demo/recommendations", (route) => route.fulfill({ json: {
    ...ranking, snapshot_id: snapshot, history_sequence_index: history.length - 1,
  } }));
  await page.route("**/api/students/demo/history", (route) => route.fulfill({ json: history }));
  await page.route("**/api/attempts", async (route) => {
    const row = { ...route.request().postDataJSON(), sequence_index: history.length, attempt_number: 1 };
    history.push(row);
    snapshot = "b".repeat(32);
    await route.fulfill({ status: 201, json: row });
  });
  await page.goto("/");
  await page.getByLabel("Exercise library").selectOption("java-count");
  return page.getByRole("region", { name: "Recommendation choice" });
}

test("only explicit choice posts exact ranking context and refresh clears acknowledgement", async ({ page, request }) => {
  const calls: { snapshot_id: string; problem_id: string }[] = [];
  await page.route("**/api/recommendation-choices", async (route) => {
    calls.push(route.request().postDataJSON());
    await created(route);
  });
  const pane = await workspace(page, request);
  await page.getByLabel("Exercise library").selectOption("java-find");
  await page.getByRole("button").filter({ hasText: "Count positive entries" }).click();
  expect(calls).toHaveLength(0);
  await pane.getByRole("button", { name: "Choose this recommendation", exact: true }).click();
  await expect(pane).toContainText("Choice recorded for this recommendation snapshot");
  expect(calls).toEqual([{ snapshot_id: "a".repeat(32), problem_id: "java-count" }]);
  await expect(pane.getByRole("button", { name: "Choice recorded", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "Simulate correct", exact: true }).click();
  await expect(page.getByText("Simulated correct outcome recorded as interaction 0.")).toBeVisible();
  await expect(pane.getByRole("button", { name: "Choose this recommendation", exact: true })).toBeEnabled();
  await expect(pane).not.toContainText("Choice recorded for this recommendation snapshot");
  expect(calls).toHaveLength(1);
});

test("double activation posts once and old context cannot acknowledge a new candidate", async ({ page, request }) => {
  const pending: Route[] = [];
  await page.route("**/api/recommendation-choices", (route) => { pending.push(route); });
  const pane = await workspace(page, request);
  await pane.getByRole("button", { name: "Choose this recommendation", exact: true }).evaluate((button: HTMLButtonElement) => { button.click(); button.click(); });
  await expect.poll(() => pending.length).toBe(1);
  await expect(page.getByRole("button", { name: "Simulate incorrect", exact: true })).toBeEnabled();
  await page.getByLabel("Exercise library").selectOption("java-find");
  await created(pending[0]).catch(() => {});
  await expect(pane.getByRole("button", { name: "Choose this recommendation", exact: true })).toBeEnabled();
  await expect(pane).not.toContainText("Choice recorded for this recommendation snapshot");
  expect(pending).toHaveLength(1);
});

for (const failure of [404, 422, 500, "network", "mismatched acknowledgement"] as const) {
  test(`choice ${failure} stays independent of replay and requires explicit retry`, async ({ page, request }) => {
    let calls = 0;
    await page.route("**/api/recommendation-choices", async (route) => {
      calls += 1;
      if (failure === "network") await route.abort("failed");
      else if (failure === "mismatched acknowledgement") await route.fulfill({ status: 201,
        json: { ...acknowledgement(route.request().postDataJSON()), problem_id: "other" } });
      else await route.fulfill({ status: failure, json: { detail: "synthetic error" } });
    });
    const pane = await workspace(page, request);
    await pane.getByRole("button", { name: "Choose this recommendation", exact: true }).click();
    await expect(pane.getByRole("alert")).toContainText("Retrying can create another choice event");
    expect(calls).toBe(1);
    await expect(page.getByRole("button", { name: "Simulate correct", exact: true })).toBeEnabled();
    await expect(pane).not.toContainText("Choice recorded for this recommendation snapshot");
    await page.route("**/api/recommendation-choices", async (route) => { calls += 1; await created(route); });
    await pane.getByRole("button", { name: "Retry choice", exact: true }).click();
    await expect(pane).toContainText("Choice recorded for this recommendation snapshot");
    expect(calls).toBe(2);
  });
}
