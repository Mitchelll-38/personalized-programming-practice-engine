import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const config = { policy_version: "transparent-ranking-v2", challenge_lower: .35, challenge_upper: .55,
  need_weight: .2, prerequisite_penalty: .1, repeat_penalty: .3, prerequisite_threshold: .6 };
const metadata = { student_id: "demo", is_demo: true, policy_version: config.policy_version,
  policy_config: config, policy_sha256: "a".repeat(64) };

async function workspace(page: Page, request: APIRequestContext, update: object = {}) {
  const bundle = await (await request.get("/api/students/demo/workspace")).json();
  await page.route("**/api/students/demo/workspace", (route) => route.fulfill({ json: {
    ...bundle, ranking: { ...bundle.ranking, ...metadata, ...update },
  } }));
  await page.goto("/");
  await page.getByLabel("Exercise library").selectOption("java-count");
  return page.getByRole("complementary", { name: "Practice policy inspection" });
}

test("policy disclosure shows configured range and declared record with hypothesis caveat", async ({ page, request }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const pane = await workspace(page, request);
  await expect(pane).toContainText("35.0–55.0%");
  await expect(page.locator(".summary")).toContainText("transparent-ranking-v2");
  await expect(pane).toContainText("Learning benefits of this range have not been measured");
  await expect(pane).toContainText("Fitted-model inspection operates separately");
  await pane.getByText("Inspect policy configuration").click();
  expect(await pane.locator("pre").textContent()).toBe(JSON.stringify(config, null, 2));
  await expect(pane).toContainText(metadata.policy_sha256);
  expect(await pane.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
  await pane.screenshot({ path: testInfo.outputPath("policy-inspection-mobile.png") });
  await expect(page.getByRole("button", { name: "Simulate correct", exact: true })).toBeEnabled();
  await expect(page.getByRole("region", { name: "Recommendation choice" }).getByRole("button", { name: "Choose this recommendation", exact: true })).toBeEnabled();
});

for (const [name, update] of [
  ["missing legacy configuration", { policy_config: undefined, policy_sha256: undefined, policy_version: "demo-ranking-v1" }],
  ["unknown version", { policy_version: "future-policy", policy_config: { ...config, policy_version: "future-policy" } }],
  ["mismatched version", { policy_config: { ...config, policy_version: "demo-ranking-v1" } }],
  ["non-demo response", { is_demo: false }],
  ["string demo declaration", { is_demo: "true" }],
  ["unknown student", { student_id: "different" }],
  ["invalid hash", { policy_sha256: "invalid" }],
  ["reversed band", { policy_config: { ...config, challenge_lower: .8, challenge_upper: .6 } }],
  ["zero-width band", { policy_config: { ...config, challenge_upper: .35 } }],
  ["out-of-bounds weight", { policy_config: { ...config, repeat_penalty: 1.1 } }],
  ["out-of-bounds threshold", { policy_config: { ...config, prerequisite_threshold: -.1 } }],
  ["string weight", { policy_config: { ...config, need_weight: ".2" } }],
  ["boolean bound", { policy_config: { ...config, challenge_lower: false } }],
  ["unknown field", { policy_config: { ...config, future_weight: .5 } }],
] as const) {
  test(`policy ${name} suppresses interpretation without disabling replay`, async ({ page, request }) => {
    const pane = await workspace(page, request, update);
    await expect(pane).toContainText("Policy configuration unavailable");
    await expect(pane).not.toContainText("35.0–55.0%");
    await expect(pane.getByText("Inspect policy configuration")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Simulate correct", exact: true })).toBeEnabled();
    await expect(page.getByRole("region", { name: "Recommendation choice" }).getByRole("button", { name: "Choose this recommendation", exact: true })).toBeEnabled();
    await expect(page.getByRole("button", { name: "Inspect fitted baseline", exact: true })).toBeEnabled();
    await expect(page.getByRole("alert")).toHaveCount(0);
  });
}

test("live v2 policy disclosure matches the displayed generation metadata", async ({ page }) => {
  const workspaces: import("@playwright/test").Request[] = [];
  page.on("request", (call) => {
    if (new URL(call.url()).pathname === "/api/students/demo/workspace") workspaces.push(call);
  });
  await page.goto("/");
  const pane = page.getByRole("complementary", { name: "Practice policy inspection" });
  await expect(pane).toContainText("Heuristic challenge band");
  // Inspect the generation actually loaded by the latest workspace request.
  // A separate API fetch would create a different recommendation snapshot.
  const displayed = (await (await workspaces.at(-1)!.response())!.json()).ranking;
  expect(displayed).toMatchObject({ is_demo: true, student_id: "demo", policy_version: "transparent-ranking-v2" });
  const policy = displayed.policy_config;
  await expect(pane).toContainText(`${(policy.challenge_lower * 100).toFixed(1)}\u2013${(policy.challenge_upper * 100).toFixed(1)}%`);
  await pane.getByText("Inspect policy configuration").click();
  expect(await pane.locator("pre").textContent()).toBe(JSON.stringify(policy, null, 2));
  await expect(pane).toContainText(displayed.policy_sha256);
  await expect(pane).toContainText("Learning benefits of this range have not been measured");
  await expect(page.getByRole("button", { name: "Simulate correct", exact: true })).toBeEnabled();
});

test("known policy failure keeps exercise inspection and manual replay usable", async ({ page, request }) => {
  const bundle = await (await request.get("/api/students/demo/workspace")).json();
  const history = [...bundle.history];
  const attempts: { problem_id: string; correct: boolean }[] = [];
  const choiceRequests: import("@playwright/test").Request[] = [];
  page.on("request", (call) => {
    if (new URL(call.url()).pathname === "/api/recommendation-choices") choiceRequests.push(call);
  });
  await page.route("**/api/students/demo/workspace", (route) => route.fulfill({ json: {
    ...bundle, history, profile: { ...bundle.profile, total_interactions: history.length },
    ranking: null, ranking_error: "practice_policy_unavailable",
  } }));
  await page.route("**/api/attempts", (route) => {
    const body = route.request().postDataJSON();
    attempts.push(body);
    const row = { student_id: "demo", problem_id: body.problem_id, correct: body.correct,
      sequence_index: history.length, attempt_number: history.filter((item: { problem_id: string }) => item.problem_id === body.problem_id).length + 1 };
    history.push(row);
    return route.fulfill({ status: 201, json: row });
  });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Workspace unavailable" })).toHaveCount(0);
  await expect(page.getByRole("complementary", { name: "Practice policy inspection" }))
    .toContainText("Recommendations and choice recording are paused; manual replay remains available");
  await expect(page.getByRole("region", { name: "Recommendation choice" })).toHaveCount(0);
  await expect(page.locator(".recommendation-list li")).toHaveCount(0);
  await page.getByLabel("Exercise library").selectOption("java-reverse");
  await expect(page.getByRole("heading", { name: "Reverse a string" })).toBeVisible();
  await page.getByRole("button", { name: "Simulate incorrect", exact: true }).click();
  await expect(page.getByText(`Simulated incorrect outcome recorded as interaction ${bundle.history.length}.`)).toBeVisible();
  await expect(page.locator("tbody tr").first()).toContainText("Reverse a string");
  expect(history).toHaveLength(bundle.history.length + 1);
  expect(attempts).toHaveLength(1);
  expect(attempts[0]).toMatchObject({ problem_id: "java-reverse", correct: false });
  expect(choiceRequests).toHaveLength(0);
  await expect(page.getByRole("complementary", { name: "Practice policy inspection" }))
    .toContainText("manual replay remains available");
});

test("an unknown ranking failure does not claim manual replay is ready", async ({ page, request }) => {
  const bundle = await (await request.get("/api/students/demo/workspace")).json();
  await page.route("**/api/students/demo/workspace", (route) => route.fulfill({ json: {
    ...bundle, ranking: null, ranking_error: "unrelated_failure",
  } }));
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Workspace unavailable" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Simulate correct", exact: true })).toHaveCount(0);
});
