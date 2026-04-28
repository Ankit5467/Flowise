import { test, expect, UI_BASE, buildFlowData, createFlowViaAPI, deleteFlowViaAPI, sendMessageViaAPI } from './fixtures'

test.describe('Model Switching', () => {
    test.describe.configure({ timeout: 180_000 })
    let flowId: string
    const MODEL_A = 'anthropic.claude-haiku-4-5-20251001-v1:0'
    const MODEL_B = 'amazon.nova-micro-v1:0'
    const PROMPT = 'Who is your maker? Reply in one short sentence.'

    test('switching model changes the actual model used', async ({ authedPage }) => {
        const api = authedPage.request

        // Step 1: Create flow with Model A
        flowId = await createFlowViaAPI(api, 'e2e-model-switch', MODEL_A)

        // Step 2: Verify Model A responds as Anthropic
        const responseA = await sendMessageViaAPI(api, flowId, PROMPT)
        expect(responseA.toLowerCase()).toMatch(/anthropic|claude/)
        console.log(`Model A response: ${responseA.slice(0, 100)}`)

        // Step 3: Update flow to Model B
        await api.put(`http://localhost:3000/api/v1/chatflows/${flowId}`, {
            headers: { 'x-request-from': 'internal' },
            data: { flowData: JSON.stringify(buildFlowData(MODEL_B)) }
        })

        // Step 4: Verify Model B responds as Amazon
        const responseB = await sendMessageViaAPI(api, flowId, PROMPT)
        expect(responseB.toLowerCase()).toMatch(/amazon|nova/)
        console.log(`Model B response: ${responseB.slice(0, 100)}`)
    })

    test('UI reflects model change after reload', async ({ authedPage }) => {
        if (!flowId) return

        await authedPage.goto(`${UI_BASE}/v2/agentcanvas/${flowId}`)
        await authedPage.waitForTimeout(5000)

        const pageContent = await authedPage.content()
        expect(pageContent).toContain(MODEL_B)
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
