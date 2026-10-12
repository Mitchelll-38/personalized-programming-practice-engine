import { expect, test } from "@playwright/test";

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
