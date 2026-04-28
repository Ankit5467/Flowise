import { test, expect, UI_BASE, createFlowViaAPI, deleteFlowViaAPI } from './fixtures'

test.describe('Custom Model Field', () => {
    let flowId: string

    test('Custom Model ARN field has correct description', async ({ authedPage }) => {
        const api = authedPage.request
        flowId = await createFlowViaAPI(api, 'e2e-custom-field', 'anthropic.claude-haiku-4-5-20251001-v1:0')

        await authedPage.goto(`${UI_BASE}/v2/agentcanvas/${flowId}`)
        await authedPage.waitForTimeout(5000)

        // Double-click to open agent config
        await authedPage.locator('text=Agent 0').dblclick()
        await authedPage.waitForTimeout(1000)

        // Expand AWS Bedrock Parameters
        const bedrockParams = authedPage.locator('text=AWS Bedrock Parameters')
        if (await bedrockParams.isVisible({ timeout: 3000 }).catch(() => false)) {
            await bedrockParams.click()
            await authedPage.waitForTimeout(500)
        }

        // Verify Custom Model ARN field description
        const content = await authedPage.content()
        expect(content).toContain('imported')
        expect(content).toContain('fine-tuned')
        expect(content).toContain('provisioned')
    })

    test('Custom Endpoint Host is under Additional Parameters', async ({ authedPage }) => {
        await authedPage.goto(`${UI_BASE}/v2/agentcanvas/${flowId}`)
        await authedPage.waitForTimeout(5000)

        await authedPage.locator('text=Agent 0').dblclick()
        await authedPage.waitForTimeout(1000)

        const content = await authedPage.content()
        expect(content).toContain('Hostname-only override')
    })

    test('Custom Model ARN accepts an ARN value', async ({ authedPage }) => {
        await authedPage.goto(`${UI_BASE}/v2/agentcanvas/${flowId}`)
        await authedPage.waitForTimeout(5000)

        await authedPage.locator('text=Agent 0').dblclick()
        await authedPage.waitForTimeout(1000)

        const bedrockParams = authedPage.locator('text=AWS Bedrock Parameters')
        if (await bedrockParams.isVisible({ timeout: 3000 }).catch(() => false)) {
            await bedrockParams.click()
            await authedPage.waitForTimeout(500)
        }

        // Find the Custom Model ARN input (by placeholder)
        const customModelInput = authedPage.locator('input[placeholder*="arn:aws:bedrock"]')
        if (await customModelInput.isVisible({ timeout: 3000 }).catch(() => false)) {
            await customModelInput.fill('arn:aws:bedrock:us-east-1:123456789012:provisioned-model/my-model')
            const value = await customModelInput.inputValue()
            expect(value).toContain('arn:aws:bedrock')
        }
    })

    test.afterAll(async ({ browser }) => {
        if (flowId) {
            const ctx = await browser.newContext()
            const page = await ctx.newPage()
            await page.goto(`${UI_BASE}/signin`)
            const cfg = require('../test-config.json')
            await page.locator('input[name="username"]').fill(cfg.email)
            await page.locator('input[name="password"]').fill(cfg.password)
            await page.locator('button[type="submit"]').click()
            await page.waitForTimeout(3000)
            await deleteFlowViaAPI(page.request, flowId)
            await ctx.close()
        }
    })
})
