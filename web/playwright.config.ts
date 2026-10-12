import { defineConfig } from "@playwright/test";

// Refuse existing servers: every run must own an isolated synthetic database.
const python = process.env.PRACTICE_TEST_PYTHON ?? "python";

export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  retries: 0,
  use: { baseURL: "http://127.0.0.1:5174", trace: "retain-on-failure" },
  webServer: [
    {
      command: `"${python}" web/e2e/serve_api.py`,
      cwd: "..",
      url: "http://127.0.0.1:8001/health",
      reuseExistingServer: false,
    },
    {
      command: "npm run dev -- --port 5174 --strictPort",
      url: "http://127.0.0.1:5174",
      env: { PRACTICE_API_URL: "http://127.0.0.1:8001" },
      reuseExistingServer: false,
    },
  ],
});
