import { test as setup } from '@playwright/test'
import * as fs from 'fs'
import * as path from 'path'

const testConfig = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'test-config.json'), 'utf8'))
const EMAIL = testConfig.email
const PASSWORD = testConfig.password
const UI_BASE = testConfig.uiBase || 'http://localhost:8080'
const AUTH_FILE = 'packages/components/nodes/chatmodels/AWSBedrock/tests/e2e/.auth/user.json'

setup('authenticate', async ({ page }) => {
    await page.goto(UI_BASE)
    await page.waitForTimeout(3000)

    // Fill login form
    await page.fill('input[name="username"]', EMAIL)
    await page.fill('input[name="password"]', PASSWORD)
    await page.click('button[type="submit"]')

    // Wait for login to complete
    await page.waitForTimeout(5000)

    // Save signed-in state
    await page.context().storageState({ path: AUTH_FILE })
})
