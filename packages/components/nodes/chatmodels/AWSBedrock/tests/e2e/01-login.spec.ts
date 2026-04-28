import { test, expect } from '@playwright/test'
import * as fs from 'fs'
import * as path from 'path'

const testConfig = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'test-config.json'), 'utf8'))
const EMAIL = testConfig.email
const PASSWORD = testConfig.password
const UI_BASE = testConfig.uiBase || 'http://localhost:8080'

test('shows login page on first visit', async ({ page }) => {
    await page.goto(UI_BASE)
    await expect(page.locator('input[name="username"]')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('input[name="password"]')).toBeVisible()
    await expect(page.locator('button[type="submit"]')).toBeVisible()
})

test('logs in with valid credentials', async ({ page }) => {
    await page.goto(UI_BASE)
    await page.fill('input[name="username"]', EMAIL)
    await page.fill('input[name="password"]', PASSWORD)
    await page.click('button[type="submit"]')
    await expect(page.locator('input[name="username"]')).not.toBeVisible({ timeout: 15000 })
})

test('rejects invalid credentials', async ({ page }) => {
    await page.goto(UI_BASE)
    await page.fill('input[name="username"]', 'wrong@email.com')
    await page.fill('input[name="password"]', 'wrongpassword')
    await page.click('button[type="submit"]')
    await page.waitForTimeout(3000)
    await expect(page.locator('input[name="username"]')).toBeVisible()
})
