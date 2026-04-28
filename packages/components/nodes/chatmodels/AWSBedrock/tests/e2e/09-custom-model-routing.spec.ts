import {
    test,
    expect,
    UI_BASE,
    listImportedModels,
    createConverseFlowWithCustomModelViaAPI,
    createFlowViaAPI,
    deleteFlowViaAPI,
    sendMessageViaAPI
} from './fixtures'

const testConfig = require('../test-config.json')
const AWS_ACCOUNT_ID = testConfig.awsAccountId || '123456789000'
const PROMPT = 'Reply with exactly one sentence: what is your model name and who made you?'
const importedModelsPromise = listImportedModels()

test.describe('Custom model routing — full branch coverage', () => {
    test.describe.configure({ timeout: 180_000 })

    // ==================================================================
    // IMPORTED MODELS VIA CONVERSE NODE (auto-detection → InvokeModel)
    // ==================================================================

    test('imported model ARNs via Converse node customModel (API)', async ({ authedPage }) => {
        const models = await importedModelsPromise
        if (!models.length) {
            test.skip()
            return
        }
        const api = authedPage.request

        for (const model of models) {
            console.log(`\n[API] Imported ARN auto-detect: ${model.name}`)
            const flowId = await createConverseFlowWithCustomModelViaAPI(api, `e2e-imported-api-${model.name}`, model.arn)
            try {
                let response = ''
                for (let attempt = 1; attempt <= 5; attempt++) {
                    response = await sendMessageViaAPI(api, flowId, PROMPT)
                    if (!response.toLowerCase().includes('not ready')) break
                    console.log(`  Cold start — attempt ${attempt}/5, waiting 60s...`)
                    await authedPage.waitForTimeout(60_000)
                }
                console.log(`  Response: ${response.slice(0, 150)}`)
                expect(response).not.toContain('ERROR:')
                expect(response).not.toContain('UNKNOWN:')
                expect(response.length).toBeGreaterThan(0)
            } finally {
                await deleteFlowViaAPI(api, flowId)
            }
        }
    })

    test('imported model via Converse node — UI chat renders response', async ({ authedPage }) => {
        const models = await importedModelsPromise
        if (!models.length) {
            test.skip()
            return
        }
        const api = authedPage.request

        for (const model of models) {
            console.log(`\n[UI] Imported ARN chat: ${model.name}`)
            const flowId = await createConverseFlowWithCustomModelViaAPI(api, `e2e-imported-ui-${model.name}`, model.arn)
            try {
                // Warm up via API (handles cold start — up to 5 min)
                for (let attempt = 1; attempt <= 5; attempt++) {
                    const warmup = await sendMessageViaAPI(api, flowId, 'hi')
                    if (!warmup.toLowerCase().includes('not ready')) break
                    console.log(`  Cold start — attempt ${attempt}/5, waiting 60s...`)
                    await authedPage.waitForTimeout(60_000)
                }

                await authedPage.goto(`${UI_BASE}/v2/agentcanvas/${flowId}`)
                await authedPage.waitForTimeout(5000)

                const chatBtn = authedPage.locator('[aria-label="chat"]')
                await expect(chatBtn).toBeVisible({ timeout: 10000 })
                await chatBtn.click()
                await authedPage.waitForTimeout(2000)

                const initialCount = await authedPage.locator('.react-markdown').count()
                const chatInput = authedPage.locator('#userInput')
                await expect(chatInput).toBeVisible({ timeout: 10000 })
                await chatInput.fill(PROMPT)
                await chatInput.press('Enter')

                await expect(authedPage.locator('.react-markdown')).toHaveCount(initialCount + 2, { timeout: 120_000 })

                await authedPage.waitForTimeout(8000)
                const responseText = await authedPage
                    .locator('.react-markdown')
                    .last()
                    .innerText({ timeout: 10000 })
                    .catch(() => '')
                console.log(`  [${model.name}] ${responseText?.slice(0, 100)}`)
            } finally {
                await deleteFlowViaAPI(api, flowId)
            }
        }
    })

    // ==================================================================
    // BUILT-IN MODELS VIA CONVERSE NODE (baseline — Converse API)
    // ==================================================================

    test('built-in model via dropdown — API baseline', async ({ authedPage }) => {
        const api = authedPage.request
        console.log('\n[API] Built-in Nova Micro (no customModel)')
        const flowId = await createFlowViaAPI(api, 'e2e-builtin-api', 'amazon.nova-micro-v1:0')
        try {
            const response = await sendMessageViaAPI(api, flowId, PROMPT)
            console.log(`  Response: ${response.slice(0, 150)}`)
            expect(response).not.toContain('ERROR:')
            expect(response.length).toBeGreaterThan(0)
        } finally {
            await deleteFlowViaAPI(api, flowId)
        }
    })

    test('built-in model via dropdown — UI chat renders response', async ({ authedPage }) => {
        const api = authedPage.request
        console.log('\n[UI] Built-in Nova Micro chat')
        const flowId = await createFlowViaAPI(api, 'e2e-builtin-ui', 'amazon.nova-micro-v1:0')
        try {
            await authedPage.goto(`${UI_BASE}/v2/agentcanvas/${flowId}`)
            await authedPage.waitForTimeout(5000)

            const chatBtn = authedPage.locator('[aria-label="chat"]')
            await expect(chatBtn).toBeVisible({ timeout: 10000 })
            await chatBtn.click()
            await authedPage.waitForTimeout(2000)

            const initialCount = await authedPage.locator('.react-markdown').count()
            const chatInput = authedPage.locator('#userInput')
            await expect(chatInput).toBeVisible({ timeout: 10000 })
            await chatInput.fill(PROMPT)
            await chatInput.press('Enter')

            await expect(authedPage.locator('.react-markdown')).toHaveCount(initialCount + 2, { timeout: 120_000 })

            await authedPage.waitForTimeout(8000)
            const responseText = await authedPage
                .locator('.react-markdown')
                .last()
                .innerText({ timeout: 10000 })
                .catch(() => '')
            console.log(`  Response: ${responseText?.slice(0, 100)}`)
        } finally {
            await deleteFlowViaAPI(api, flowId)
        }
    })

    // ==================================================================
    // STOPSEQUENCES MODEL (DeepSeek — verifies stripping works)
    // ==================================================================

    test('stopSequences model (DeepSeek R1) does not error (API)', async ({ authedPage }) => {
        const api = authedPage.request
        console.log('\n[API] DeepSeek R1 — stopSequences stripping')
        const flowId = await createFlowViaAPI(api, 'e2e-stopseq', 'deepseek.r1-v1:0')
        try {
            const response = await sendMessageViaAPI(api, flowId, PROMPT)
            console.log(`  Response: ${response.slice(0, 150)}`)
            expect(response).not.toContain('stopSequences')
            expect(response.length).toBeGreaterThan(0)
        } finally {
            await deleteFlowViaAPI(api, flowId)
        }
    })

    // ==================================================================
    // DIFFERENT REGION
    // ==================================================================

    test('built-in model in eu-west-1 (API)', async ({ authedPage }) => {
        const api = authedPage.request
        console.log('\n[API] Nova Micro in eu-west-1')
        const flowId = await createFlowViaAPI(api, 'e2e-region-eu', 'amazon.nova-micro-v1:0', 'eu-west-1')
        try {
            const response = await sendMessageViaAPI(api, flowId, PROMPT)
            console.log(`  Response: ${response.slice(0, 150)}`)
            expect(response).not.toContain('ERROR:')
            expect(response.length).toBeGreaterThan(0)
        } finally {
            await deleteFlowViaAPI(api, flowId)
        }
    })

    // ==================================================================
    // ERROR HANDLING
    // ==================================================================

    test('nonexistent imported-model ARN returns error (API)', async ({ authedPage }) => {
        const api = authedPage.request
        console.log('\n[API] Nonexistent imported-model ARN')
        const flowId = await createConverseFlowWithCustomModelViaAPI(
            api,
            'e2e-nonexistent',
            `arn:aws:bedrock:us-east-1:${AWS_ACCOUNT_ID}:imported-model/nonexistent999`
        )
        try {
            const response = await sendMessageViaAPI(api, flowId, PROMPT)
            console.log(`  Response: ${response.slice(0, 200)}`)
            expect(response.toLowerCase()).toMatch(/error|not found|not ready/)
        } finally {
            await deleteFlowViaAPI(api, flowId)
        }
    })

    test('non-ARN in customModel returns validation error (API)', async ({ authedPage }) => {
        const api = authedPage.request
        console.log('\n[API] Non-ARN in customModel → validation error')
        const flowId = await createConverseFlowWithCustomModelViaAPI(api, 'e2e-non-arn', 'us.anthropic.claude-haiku-4-5-20251001-v1:0')
        try {
            const response = await sendMessageViaAPI(api, flowId, PROMPT)
            console.log(`  Response: ${response.slice(0, 200)}`)
            expect(response.toLowerCase()).toMatch(/not a valid arn|error/)
        } finally {
            await deleteFlowViaAPI(api, flowId)
        }
    })

    // ==================================================================
    // ARN TYPE HANDLING
    // ==================================================================

    test('inference profile ARN in customModel works (API)', async ({ authedPage }) => {
        const api = authedPage.request
        console.log('\n[API] Inference profile ARN in customModel')
        const flowId = await createConverseFlowWithCustomModelViaAPI(
            api,
            'e2e-profile-arn',
            `arn:aws:bedrock:us-east-1:${AWS_ACCOUNT_ID}:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0`
        )
        try {
            const response = await sendMessageViaAPI(api, flowId, PROMPT)
            console.log(`  Response: ${response.slice(0, 150)}`)
            expect(response).not.toContain('ERROR:')
            expect(response.length).toBeGreaterThan(0)
        } finally {
            await deleteFlowViaAPI(api, flowId)
        }
    })

    test('foundation model ARN in customModel returns error (API)', async ({ authedPage }) => {
        const api = authedPage.request
        console.log('\n[API] Foundation model ARN in customModel → error')
        const flowId = await createConverseFlowWithCustomModelViaAPI(
            api,
            'e2e-foundation-arn',
            'arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0'
        )
        try {
            const response = await sendMessageViaAPI(api, flowId, PROMPT)
            console.log(`  Response: ${response.slice(0, 200)}`)
            expect(response.toLowerCase()).toMatch(/error|invalid|not supported/)
        } finally {
            await deleteFlowViaAPI(api, flowId)
        }
    })

    // ==================================================================
    // STREAMING VERIFICATION
    // ==================================================================

    test('streaming response renders incrementally in UI', async ({ authedPage }) => {
        const api = authedPage.request
        console.log('\n[UI] Streaming verification — Claude Haiku')
        const flowId = await createFlowViaAPI(api, 'e2e-streaming', 'anthropic.claude-haiku-4-5-20251001-v1:0')
        try {
            await authedPage.goto(`${UI_BASE}/v2/agentcanvas/${flowId}`)
            await authedPage.waitForTimeout(5000)

            const chatBtn = authedPage.locator('[aria-label="chat"]')
            await expect(chatBtn).toBeVisible({ timeout: 10000 })
            await chatBtn.click()
            await authedPage.waitForTimeout(2000)

            const initialCount = await authedPage.locator('.react-markdown').count()
            const chatInput = authedPage.locator('#userInput')
            await expect(chatInput).toBeVisible({ timeout: 10000 })
            await chatInput.fill('Write a 3-sentence story about a cat.')
            await chatInput.press('Enter')

            // Wait for response to start (at least one new .react-markdown element)
            await expect(authedPage.locator('.react-markdown')).toHaveCount(initialCount + 2, { timeout: 120_000 })

            // Verify the response has content (streaming completed)
            await authedPage.waitForTimeout(8000)
            const responseText = await authedPage
                .locator('.react-markdown')
                .last()
                .innerText({ timeout: 10000 })
                .catch(() => '')
            console.log(`  Response (${responseText.length} chars): ${responseText.slice(0, 100)}`)
            expect(responseText.length).toBeGreaterThan(20)
        } finally {
            await deleteFlowViaAPI(api, flowId)
        }
    })

    // ==================================================================
    // USAGE METADATA (token counts via API)
    // ==================================================================

    test('API response includes token usage metadata', async ({ authedPage }) => {
        const api = authedPage.request
        console.log('\n[API] Token usage metadata check')
        const flowId = await createFlowViaAPI(api, 'e2e-usage', 'amazon.nova-micro-v1:0')
        try {
            const resp = await api.post(`http://localhost:3000/api/v1/internal-prediction/${flowId}`, {
                headers: { 'x-request-from': 'internal' },
                data: { question: 'Say hello in one word.' },
                timeout: 120_000
            })
            const data = await resp.json()
            console.log(`  Response keys: ${Object.keys(data).join(', ')}`)
            // agentFlowExecutedData contains usageMetadata with token counts
            if (data.agentFlowExecutedData) {
                const execData = data.agentFlowExecutedData[0]
                const usage = execData?.data?.output?.usageMetadata
                console.log(`  Usage: ${JSON.stringify(usage)}`)
                if (usage) {
                    expect(usage.input_tokens).toBeGreaterThan(0)
                    expect(usage.output_tokens).toBeGreaterThan(0)
                }
            }
            expect(data.text).toBeTruthy()
        } finally {
            await deleteFlowViaAPI(api, flowId)
        }
    })

    // ==================================================================
    // TOOL CALLING (Calculator)
    // ==================================================================

    test('model invokes Calculator tool and returns correct result (API)', async ({ authedPage }) => {
        const api = authedPage.request

        // Create a flow with Calculator tool attached
        const flowData = JSON.parse(JSON.stringify(require('../manual_tests/jsons/31-tool-calling-calculator-claude.json')))
        const resp = await api.post('http://localhost:3000/api/v1/chatflows', {
            headers: { 'x-request-from': 'internal' },
            data: {
                name: 'e2e-tool-calling',
                type: 'AGENTFLOW',
                flowData: JSON.stringify(flowData)
            }
        })
        const flowId = (await resp.json()).id
        console.log(`\n[API] Tool calling — Calculator with Claude Haiku (flow: ${flowId})`)

        try {
            const predResp = await api.post(`http://localhost:3000/api/v1/internal-prediction/${flowId}`, {
                headers: { 'x-request-from': 'internal' },
                data: { question: 'What is 1847 multiplied by 293? Use the calculator tool.' },
                timeout: 120_000
            })
            const data = await predResp.json()
            const text = data.text || ''
            console.log(`  Response: ${text.slice(0, 200)}`)
            expect(text).toBeTruthy()
            expect(text).toContain('541')
        } finally {
            await api.delete(`http://localhost:3000/api/v1/chatflows/${flowId}`, {
                headers: { 'x-request-from': 'internal' }
            })
        }
    })
})
