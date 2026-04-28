/**
 * Playwright E2E test configuration for Flowise Bedrock integration.
 *
 * Requires Flowise running on localhost:8080 (UI) / localhost:3000 (API).
 * Tests make real AWS Bedrock API calls (costs money, needs AWS creds).
 *
 * workers: 1 is required — Flowise uses SQLite which locks under
 * concurrent access. Multiple workers cause SQLITE_BUSY errors.
 *
 * @see e2e/fixtures.ts for auth and helper functions
 */
import { defineConfig } from '@playwright/test'

export default defineConfig({
    testDir: './e2e',
    outputDir: './test-results',
    testIgnore: ['**/auth.setup.ts'],
    timeout: 180_000, // 3 min — some Bedrock models are slow
    expect: { timeout: 60_000 },
    fullyParallel: false,
    workers: 1, // SQLite locks under concurrent access
    retries: 1,
    reporter: [['html', { open: 'never', outputFolder: './playwright-report' }], ['list']],
    use: {
        browserName: 'chromium',
        screenshot: 'on',
        trace: 'on-first-retry',
        video: 'retain-on-failure'
    }
})
