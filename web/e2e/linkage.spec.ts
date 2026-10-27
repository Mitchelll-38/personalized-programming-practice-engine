import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const choiceId = "c".repeat(32);
type Attempt = { student_id: string; problem_id: string; correct: boolean; choice_id?: string; request_id: string };
type Interaction = { student_id: string; problem_id: string; correct: boolean; sequence_index: number; attempt_number: number };
async function workspace(page: Page, request: APIRequestContext) {
  const bundle = await (await request.get("/api/students/demo/workspace")).json();
  const history: Interaction[] = [];
  const attempts: Attempt[] = [];
  page.on("request", (call) => {
    if (new URL(call.url()).pathname === "/api/attempts" && call.method() === "POST") attempts.push(call.postDataJSON());
  });
  await page.route("**/api/students/demo/workspace", (route) => route.fulfill({ json: {
    ...bundle, history, ranking: { ...bundle.ranking, snapshot_id: (history.length ? "b" : "a").repeat(32),
      history_sequence_index: history.length - 1 },
  } }));
  await page.route("**/api/recommendation-choices", (route) => route.fulfill({ status: 201, json: {
    ...route.request().postDataJSON(), choice_id: choiceId, created_at: "2026-10-17T21:00:00Z",
  } }));
  await page.route("**/api/attempts", (route) => {
    const body = route.request().postDataJSON();
    const row = { student_id: "demo", problem_id: body.problem_id, correct: body.correct,
      sequence_index: history.length, attempt_number: history.filter((item) => item.problem_id === body.problem_id).length + 1 };
    history.push(row);
    return route.fulfill({ status: 201, json: row });
  });
  await page.goto("/");
  await page.getByLabel("Exercise library").selectOption("java-count");
  return { attempts, history, choice: page.getByRole("region", { name: "Recommendation choice" }) };
}

async function choose(page: Page) {
  await page.getByRole("region", { name: "Recommendation choice" }).getByRole("button", { name: "Choose this recommendation", exact: true }).click();
  await expect(page.getByText("The next simulated outcome will link to your recorded choice. Choosing alone does not grade code.")).toBeVisible();
}

test("acknowledged same-context choice links once and refresh clears the next attempt", async ({ page, request }) => {
  const { attempts } = await workspace(page, request);
  await choose(page);
  expect(attempts).toHaveLength(0);
  await page.getByRole("button", { name: "Simulate correct", exact: true }).click();
  await expect(page.getByText("Simulated correct outcome recorded as interaction 0.")).toBeVisible();
  expect(attempts[0]).toMatchObject({ student_id: "demo", problem_id: "java-count", correct: true, choice_id: choiceId });
  expect(attempts[0].request_id).toMatch(/^[a-f0-9]{32}$/);
  await expect(page.getByText(/The next simulated outcome will link/)).toHaveCount(0);
  await page.getByRole("button", { name: "Simulate correct", exact: true }).click();
  await expect(page.getByText("Simulated correct outcome recorded as interaction 1.")).toBeVisible();
  expect(attempts[1]).toMatchObject({ student_id: "demo", problem_id: "java-count", correct: true });
  expect(attempts[1].request_id).toMatch(/^[a-f0-9]{32}$/);
  expect(attempts[1].request_id).not.toBe(attempts[0].request_id);
});

test("pending choice never blocks or retroactively links an unlinked simulation", async ({ page, request }) => {
  const { attempts } = await workspace(page, request);
  let pending: import("@playwright/test").Route | undefined;
  await page.route("**/api/recommendation-choices", (route) => { pending = route; });
  await page.getByRole("region", { name: "Recommendation choice" }).getByRole("button", { name: "Choose this recommendation", exact: true }).click();
  await expect.poll(() => !!pending).toBe(true);
  await page.getByRole("button", { name: "Simulate incorrect", exact: true }).click();
  await expect(page.getByText("Simulated incorrect outcome recorded as interaction 0.")).toBeVisible();
  await pending!.fulfill({ status: 201, json: { ...pending!.request().postDataJSON(), choice_id: choiceId, created_at: "2026-10-17T21:00:00Z" } }).catch(() => {});
  expect(attempts).toHaveLength(1);
  expect(attempts[0]).toMatchObject({ student_id: "demo", problem_id: "java-count", correct: false });
  expect(attempts[0].request_id).toMatch(/^[a-f0-9]{32}$/);
  await expect(page.getByText(/The next simulated outcome will link/)).toHaveCount(0);
});

test("selection changes discard an acknowledged link", async ({ page, request }) => {
  const { attempts } = await workspace(page, request);
  await choose(page);
  await page.getByLabel("Exercise library").selectOption("java-find");
  await expect(page.getByText(/The next simulated outcome will link/)).toHaveCount(0);
  await page.getByRole("button", { name: "Simulate correct", exact: true }).click();
  await expect(page.getByText("Simulated correct outcome recorded as interaction 0.")).toBeVisible();
  expect(attempts).toHaveLength(1);
  expect(attempts[0]).toMatchObject({ student_id: "demo", problem_id: "java-find", correct: true });
  expect(attempts[0].request_id).toMatch(/^[a-f0-9]{32}$/);
});

test("ambiguous attempt failure retains the same choice for an identical receipt retry", async ({ page, request }) => {
  const { attempts, history } = await workspace(page, request);
  const saved = { student_id: "demo", problem_id: "java-count", correct: true, sequence_index: 0, attempt_number: 1 };
  await page.route("**/api/attempts", (route) => {
    if (!history.length) { history.push(saved); return route.abort("failed"); }
    return route.fulfill({ status: 201, json: saved });
  });
  await choose(page);
  await page.getByRole("button", { name: "Simulate correct", exact: true }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByText(/The next simulated outcome will link/)).toBeVisible();
  await page.getByRole("button", { name: "Simulate correct", exact: true }).click();
  await expect(page.getByText("Simulated correct outcome recorded as interaction 0.")).toBeVisible();
  expect(attempts).toHaveLength(2);
  expect(attempts[1]).toEqual(attempts[0]);
  expect(attempts[0].choice_id).toBe(choiceId);
  await expect(page.locator("tbody tr")).toHaveCount(1);
});

test("transient server failure retains the exact linked request for retry", async ({ page, request }) => {
  const { attempts, history } = await workspace(page, request);
  let failed = false;
  await page.route("**/api/attempts", (route) => {
    if (!failed) {
      failed = true;
      return route.fulfill({ status: 503, json: { detail: "temporary failure" } });
    }
    return route.fallback();
  });
  await choose(page);
  await page.getByRole("button", { name: "Simulate correct", exact: true }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await page.getByRole("button", { name: "Simulate correct", exact: true }).click();
  await expect(page.getByText("Simulated correct outcome recorded as interaction 0.")).toBeVisible();
  expect(attempts).toHaveLength(2);
  expect(attempts[1]).toEqual(attempts[0]);
  expect(attempts[0].choice_id).toBe(choiceId);
  expect(history).toHaveLength(1);
});

for (const [status, message] of [[404, "Recorded choice or exercise was not found"], [422, "Recorded choice does not match"], [409, "Recorded choice already has a different simulated outcome"]] as const) {
  test(`linked outcome ${status} rejects its intent and allows a fresh explicit simulation`, async ({ page, request }) => {
    const { attempts, history } = await workspace(page, request);
    let rejected = false;
    await page.route("**/api/attempts", (route) => {
      if (!rejected) {
        rejected = true;
        return route.fulfill({ status, json: { detail: "synthetic link error" } });
      }
      return route.fallback();
    });
    await choose(page);
    await page.getByRole("button", { name: "Simulate correct", exact: true }).click();
    await expect(page.getByRole("alert")).toContainText(message);
    expect(attempts).toHaveLength(1);
    expect(attempts[0].choice_id).toBe(choiceId);
    await expect(page.getByText(/The next simulated outcome will link/)).toHaveCount(0);
    await page.getByRole("button", { name: "Retry connection" }).click();
    expect(attempts).toHaveLength(1);
    await page.getByRole("button", { name: "Simulate correct", exact: true }).click();
    await expect(page.getByText("Simulated correct outcome recorded as interaction 0.")).toBeVisible();
    expect(attempts).toHaveLength(2);
    expect(attempts[1]).toMatchObject({ student_id: "demo", problem_id: "java-count", correct: true });
    expect(attempts[1].choice_id).toBeUndefined();
    expect(attempts[1].request_id).toMatch(/^[a-f0-9]{32}$/);
    expect(attempts[1].request_id).not.toBe(attempts[0].request_id);
    expect(history).toHaveLength(1);
  });
}
