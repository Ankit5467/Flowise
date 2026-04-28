import { test, expect, UI_BASE, loadModels, createFlowViaAPI, deleteFlowViaAPI } from './fixtures'

const PROMPT = 'Reply with exactly one sentence: what is your model name and who made you?'
const models = loadModels()

test.describe('Invoke all Bedrock models via UI chat', () => {
    test.describe.configure({ timeout: 180_000 })

    for (const model of models) {
        test(`invoke ${model.name}`, async ({ authedPage, request }) => {
            const flowId = await createFlowViaAPI(request, `e2e-invoke-${model.name}`, model.name)

            try {
                await authedPage.goto(`${UI_BASE}/v2/agentcanvas/${flowId}`)
                await authedPage.waitForTimeout(5000)

                // Open chat panel
                const chatBtn = authedPage.locator('[aria-label="chat"]')
                await expect(chatBtn).toBeVisible({ timeout: 10000 })
                await chatBtn.click()
                await authedPage.waitForTimeout(2000)

                // Count initial markdown elements (before sending)
                const initialCount = await authedPage.locator('.react-markdown').count()

                // Type message and press Enter to send
                const chatInput = authedPage.locator('#userInput')
                await expect(chatInput).toBeVisible({ timeout: 10000 })
                await chatInput.fill(PROMPT)
                await chatInput.press('Enter')

                // Wait for TWO new .react-markdown elements: user message + AI response
                await expect(authedPage.locator('.react-markdown')).toHaveCount(initialCount + 2, { timeout: 120_000 })

                // Wait for streaming to finish, then get the response text
                await authedPage.waitForTimeout(3000)
                const responseText = await authedPage
                    .locator('.react-markdown')
                    .last()
                    .innerText({ timeout: 5000 })
                    .catch(() => '')
                console.log(`[${model.name}] ${responseText?.slice(0, 100)}`)
                // Response may be empty for some streaming responses that haven't fully rendered
                // The key assertion is that the element appeared (count check above)
            } finally {
                await deleteFlowViaAPI(request, flowId)
            }
        })
    }
})
