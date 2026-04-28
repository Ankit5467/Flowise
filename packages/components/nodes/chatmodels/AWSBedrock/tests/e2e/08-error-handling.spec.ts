import { test, expect, UI_BASE, createFlowViaAPI, deleteFlowViaAPI, sendMessageViaAPI } from './fixtures'

test.describe('Error Handling', () => {
    test.describe.configure({ timeout: 180_000 })

    test('stopSequences models (DeepSeek) work without error', async ({ authedPage }) => {
        const api = authedPage.request
        const flowId = await createFlowViaAPI(api, 'e2e-error-deepseek', 'deepseek.r1-v1:0')
        try {
            const response = await sendMessageViaAPI(api, flowId, 'Say hello in one word.')
            expect(response).not.toContain('stopSequences')
            expect(response).not.toContain('ERROR')
            console.log(`DeepSeek R1: ${response.slice(0, 100)}`)
        } finally {
            await deleteFlowViaAPI(api, flowId)
        }
    })

    test('OpenAI GPT OSS models work without stopSequences error', async ({ authedPage }) => {
        const api = authedPage.request
        const flowId = await createFlowViaAPI(api, 'e2e-error-openai', 'openai.gpt-oss-20b-1:0')
        try {
            const response = await sendMessageViaAPI(api, flowId, 'Say hello in one word.')
            expect(response).not.toContain('stopSequences')
            expect(response).not.toContain('ERROR')
            console.log(`OpenAI GPT OSS: ${response.slice(0, 100)}`)
        } finally {
            await deleteFlowViaAPI(api, flowId)
        }
    })

    test('chat UI shows response for valid model', async ({ authedPage }) => {
        const api = authedPage.request
        const flowId = await createFlowViaAPI(api, 'e2e-error-display', 'anthropic.claude-haiku-4-5-20251001-v1:0')
        try {
            await authedPage.goto(`${UI_BASE}/v2/agentcanvas/${flowId}`)
            await authedPage.waitForTimeout(5000)

            // Open chat
            const chatBtn = authedPage.locator('[aria-label="chat"]')
            await expect(chatBtn).toBeVisible({ timeout: 10000 })
            await chatBtn.click()
            await authedPage.waitForTimeout(2000)

            // Count initial messages
            const initialCount = await authedPage.locator('.react-markdown').count()

            // Send message
            const chatInput = authedPage.locator('#userInput')
            await expect(chatInput).toBeVisible({ timeout: 10000 })
            await chatInput.fill('Say hello')
            await chatInput.press('Enter')

            // Wait for response (user message + AI response = +2)
            await expect(authedPage.locator('.react-markdown')).toHaveCount(initialCount + 2, { timeout: 120_000 })

            // Verify response rendered
            await authedPage.waitForTimeout(3000)
            const responseText = await authedPage
                .locator('.react-markdown')
                .last()
                .innerText({ timeout: 5000 })
                .catch(() => '')
            console.log(`Chat UI response: ${responseText.slice(0, 100)}`)
            expect(responseText.length).toBeGreaterThan(0)
        } finally {
            await deleteFlowViaAPI(api, flowId)
        }
    })
})
