import { expect, test, type Request } from "@playwright/test";

test("live explicit choice binds the displayed generation without changing outcomes", async ({ page, request }) => {
  const before = await Promise.all(["history", "profile"].map(async (name) =>
    (await request.get(`/api/students/demo/${name}`)).json()));
  const workspaces: Request[] = [];
  const choices: Request[] = [];
  let attempts = 0;
  page.on("request", (call) => {
    const path = new URL(call.url()).pathname;
    if (path === "/api/students/demo/workspace") workspaces.push(call);
    if (path === "/api/recommendation-choices" && call.method() === "POST") choices.push(call);
    if (path === "/api/attempts" && call.method() === "POST") attempts += 1;
  });
  await page.goto("/");
  await page.getByLabel("Exercise library").selectOption("java-count");
  const pane = page.getByRole("region", { name: "Recommendation choice" });
  const button = pane.getByRole("button", { name: "Choose this recommendation", exact: true });
  await expect(button).toBeEnabled();
  expect(choices).toHaveLength(0);
  // The latest workspace request owns the displayed snapshot, including when
  // StrictMode has started multiple initial requests. Do not fetch a new ranking.
  const displayed = (await (await workspaces.at(-1)!.response())!.json()).ranking;
  expect(displayed.recommendations.some((row: { problem_id: string }) => row.problem_id === "java-count")).toBe(true);
  const responsePromise = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/api/recommendation-choices" && response.request().method() === "POST");
  await button.click();
  const response = await responsePromise;
  expect(response.status()).toBe(201);
  expect(response.request().postDataJSON()).toEqual({ snapshot_id: displayed.snapshot_id, problem_id: "java-count" });
  const saved = await response.json();
  expect(saved).toMatchObject({ snapshot_id: displayed.snapshot_id, problem_id: "java-count" });
  expect(saved.choice_id).toMatch(/^[a-f0-9]{32}$/);
  expect(saved.created_at).toMatch(/(Z|\+00:00)$/);
  await expect(pane).toContainText("Choice recorded for this recommendation snapshot");
  expect(choices).toHaveLength(1);
  expect(attempts).toBe(0);
  const after = await Promise.all(["history", "profile"].map(async (name) =>
    (await request.get(`/api/students/demo/${name}`)).json()));
  expect(after).toEqual(before);
});

test("live replay persists first evidence and excludes successful retries", async ({ page, request }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(page.getByText("Synthetic research demo", { exact: true })).toBeVisible();
  await expect(page.getByText("3 distinct first attempts · 1 retries excluded from estimates")).toBeVisible();
  const strings = page.locator(".concept").filter({ has: page.getByText("strings", { exact: true }) });
  await expect(strings).toContainText("No history · 50% neutral prior; no personal evidence.");

  await page.getByLabel("Exercise library").selectOption("java-reverse");
  await expect(page.getByRole("heading", { name: "Reverse a string" })).toBeVisible();
  await page.getByRole("button", { name: "Simulate incorrect", exact: true }).click();
  await expect(page.getByText("Simulated incorrect outcome recorded as interaction 4.")).toBeVisible();
  await expect(page.getByText("4 distinct first attempts · 1 retries excluded from estimates")).toBeVisible();
  await expect(strings).toContainText("Limited history · 1 distinct supporting exercises");
  await expect(strings.locator("meter")).toHaveAttribute("value", String(1 / 3));
  await strings.getByText("Inspect supporting first attempts").click();
  await expect(strings).toContainText("Reverse a string · Simulated incorrect");

  const profileBeforeRetry = await (await request.get("/api/students/demo/profile")).json();
  await page.getByRole("button", { name: "Simulate correct", exact: true }).click();
  await expect(page.getByText("Simulated correct outcome recorded as interaction 5.")).toBeVisible();
  await expect(page.getByText("4 distinct first attempts · 2 retries excluded from estimates")).toBeVisible();
  const profileAfterRetry = await (await request.get("/api/students/demo/profile")).json();
  expect(profileAfterRetry.concepts).toEqual(profileBeforeRetry.concepts);
  expect(profileAfterRetry.total_interactions).toBe(6);
  expect(profileAfterRetry.first_attempts).toBe(4);
  expect(profileAfterRetry.retries).toBe(2);

  await page.reload();
  await expect(page.getByText("4 distinct first attempts · 2 retries excluded from estimates")).toBeVisible();
  const stored = await (await request.get("/api/students/demo/history")).json();
  expect(stored.at(-1)).toMatchObject({ problem_id: "java-reverse", sequence_index: 5, attempt_number: 2, correct: true });
  expect(errors).toEqual([]);
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("live acknowledged choice links one outcome and identical retry returns its receipt", async ({ page, request }) => {
  const before = await (await request.get("/api/students/demo/history")).json();
  const beforeProfile = await (await request.get("/api/students/demo/profile")).json();
  await page.goto("/");
  await page.getByLabel("Exercise library").selectOption("java-count");
  const pane = page.getByRole("region", { name: "Recommendation choice" });
  const choicePromise = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/api/recommendation-choices" && response.request().method() === "POST");
  await pane.getByRole("button", { name: "Choose this recommendation", exact: true }).click();
  const choiceResponse = await choicePromise;
  expect(choiceResponse.status()).toBe(201);
  const choice = await choiceResponse.json();
  await expect(page.getByText(/The next simulated outcome will link/)).toBeVisible();
  const attemptPromise = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/api/attempts" && response.request().method() === "POST");
  await page.getByRole("button", { name: "Simulate correct", exact: true }).click();
  const attemptResponse = await attemptPromise;
  expect(attemptResponse.status()).toBe(201);
  const payload = attemptResponse.request().postDataJSON();
  expect(payload).toEqual({ student_id: "demo", problem_id: "java-count", correct: true, choice_id: choice.choice_id });
  const saved = await attemptResponse.json();
  expect(saved.sequence_index).toBe(before.at(-1).sequence_index + 1);
  await expect(page.getByRole("button", { name: "Simulate correct", exact: true })).toBeEnabled();
  await expect(page.getByText(/The next simulated outcome will link/)).toHaveCount(0);
  await expect(pane.getByRole("button", { name: "Choose this recommendation", exact: true })).toBeEnabled();
  const after = await (await request.get("/api/students/demo/history")).json();
  expect(after).toEqual([...before, saved]);
  const afterProfile = await (await request.get("/api/students/demo/profile")).json();
  expect(afterProfile.total_interactions).toBe(beforeProfile.total_interactions + 1);
  const retry = await request.post("/api/attempts", { data: payload });
  expect(retry.status()).toBe(201);
  expect(await retry.json()).toEqual(saved);
  expect(await (await request.get("/api/students/demo/history")).json()).toEqual(after);
  expect(await (await request.get("/api/students/demo/profile")).json()).toEqual(afterProfile);
});
