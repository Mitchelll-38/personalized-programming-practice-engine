import { expect, test, type Page } from "@playwright/test";

const secondary = ".rank, .recommendation-copy > span, .probability > span, .save-status, .concept p, th, td.mono, .table-note, footer";

async function lowContrast(page: Page, selector: string) {
  return page.locator(selector).evaluateAll((elements) => {
    function luminance(color: string) {
      const rgb = color.match(/[\d.]+/g)!.slice(0, 3).map(Number).map((value) => value / 255);
      return rgb.reduce((sum, value, index) => sum + (value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4) * [.2126, .7152, .0722][index], 0);
    }
    return elements.flatMap((element) => {
      const color = getComputedStyle(element).color;
      let surface: Element | null = element;
      let background = "rgba(0, 0, 0, 0)";
      while (surface && background === "rgba(0, 0, 0, 0)") {
        background = getComputedStyle(surface).backgroundColor;
        surface = surface.parentElement;
      }
      const [foreground, back] = [luminance(color), luminance(background)];
      const ratio = (Math.max(foreground, back) + .05) / (Math.min(foreground, back) + .05);
      return ratio >= 4.5 ? [] : [{ text: element.textContent?.trim(), color, background, ratio }];
    });
  });
}

test("meaningful secondary text meets normal-text contrast on actual replay surfaces", async ({ page }, testInfo) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Recommended practice" })).toBeVisible();
  await expect(page.locator(".concept p").first()).toBeVisible();
  expect(await lowContrast(page, secondary)).toEqual([]);
  const cards = page.locator("button.recommendation");
  await cards.nth(1).hover();
  expect(await lowContrast(page, ".recommendation .rank, .recommendation-copy > span, .probability > span")).toEqual([]);
  await cards.nth(1).click();
  await expect(cards.nth(1)).toHaveAttribute("aria-pressed", "true");
  expect(await lowContrast(page, ".recommendation .rank, .recommendation-copy > span, .probability > span")).toEqual([]);
  await page.screenshot({ path: testInfo.outputPath("contrast-desktop.png"), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await lowContrast(page, secondary)).toEqual([]);
  await page.screenshot({ path: testInfo.outputPath("contrast-mobile.png"), fullPage: true });
});
