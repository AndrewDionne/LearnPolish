import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  retries: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  // Hosted Ubuntu images include Google Chrome. CI can use it directly to
  // avoid network/apt stalls during Playwright's separate browser install.
  // Local development still uses the Playwright-managed Chromium by default.
  projects: [
    { name: 'desktop-chromium', use: { ...devices['Desktop Chrome'], ...(process.env.PTP_CI_SYSTEM_CHROME === '1' ? {channel:'chrome' as const} : {}) } },
    { name: 'mobile-chromium', use: { ...devices['Pixel 7'], ...(process.env.PTP_CI_SYSTEM_CHROME === '1' ? {channel:'chrome' as const} : {}) } },
  ],
  webServer: {
    command: 'npm run build && npm run preview',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: !process.env.CI,
    timeout: 90_000,
  },
});
