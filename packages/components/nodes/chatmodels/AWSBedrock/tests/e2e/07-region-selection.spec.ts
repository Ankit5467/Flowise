import { test, expect, UI_BASE, createFlowViaAPI, deleteFlowViaAPI, sendMessageViaAPI } from './fixtures'

const PROMPT = 'Reply in one sentence: what is 2+2?'

test.describe('Region Selection', () => {
    test.describe.configure({ timeout: 180_000 })

    test('model works in us-east-1', async ({ authedPage }) => {
        const api = authedPage.request
        const flowId = await createFlowViaAPI(api, 'e2e-region-us', 'amazon.nova-micro-v1:0', 'us-east-1')
        try {
            const response = await sendMessageViaAPI(api, flowId, PROMPT)
            expect(response).not.toContain('ERROR')
            console.log(`us-east-1: ${response.slice(0, 100)}`)
        } finally {
            await deleteFlowViaAPI(api, flowId)
        }
    })

    test('model works in eu-west-1', async ({ authedPage }) => {
        const api = authedPage.request
        const flowId = await createFlowViaAPI(api, 'e2e-region-eu', 'amazon.nova-micro-v1:0', 'eu-west-1')
        try {
            const response = await sendMessageViaAPI(api, flowId, PROMPT)
            expect(response).not.toContain('ERROR')
            console.log(`eu-west-1: ${response.slice(0, 100)}`)
        } finally {
            await deleteFlowViaAPI(api, flowId)
        }
    })

    test('model works in ap-northeast-1 (Tokyo — jp profile)', async ({ authedPage }) => {
        const api = authedPage.request
        const flowId = await createFlowViaAPI(api, 'e2e-region-tokyo', 'anthropic.claude-sonnet-4-6', 'ap-northeast-1')
        try {
            const response = await sendMessageViaAPI(api, flowId, PROMPT)
            expect(response).not.toContain('ERROR')
            console.log(`ap-northeast-1: ${response.slice(0, 100)}`)
        } finally {
            await deleteFlowViaAPI(api, flowId)
        }
    })

    test('model works in ap-southeast-2 (Sydney — au profile)', async ({ authedPage }) => {
        const api = authedPage.request
        const flowId = await createFlowViaAPI(api, 'e2e-region-sydney', 'anthropic.claude-sonnet-4-6', 'ap-southeast-2')
        try {
            const response = await sendMessageViaAPI(api, flowId, PROMPT)
            expect(response).not.toContain('ERROR')
            console.log(`ap-southeast-2: ${response.slice(0, 100)}`)
        } finally {
            await deleteFlowViaAPI(api, flowId)
        }
    })

    test('model works in ca-central-1 (Canada)', async ({ authedPage }) => {
        const api = authedPage.request
        const flowId = await createFlowViaAPI(api, 'e2e-region-canada', 'anthropic.claude-haiku-4-5-20251001-v1:0', 'ca-central-1')
        try {
            const response = await sendMessageViaAPI(api, flowId, PROMPT)
            expect(response).not.toContain('ERROR')
            console.log(`ca-central-1: ${response.slice(0, 100)}`)
        } finally {
            await deleteFlowViaAPI(api, flowId)
        }
    })

    test('model works in sa-east-1 (South America — global fallback)', async ({ authedPage }) => {
        const api = authedPage.request
        const flowId = await createFlowViaAPI(api, 'e2e-region-sa', 'anthropic.claude-sonnet-4-6', 'sa-east-1')
        try {
            const response = await sendMessageViaAPI(api, flowId, PROMPT)
            expect(response).not.toContain('ERROR')
            console.log(`sa-east-1: ${response.slice(0, 100)}`)
        } finally {
            await deleteFlowViaAPI(api, flowId)
        }
    })

    test('region change reflected in UI', async ({ authedPage }) => {
        const api = authedPage.request
        const flowId = await createFlowViaAPI(api, 'e2e-region-ui', 'amazon.nova-micro-v1:0', 'eu-west-1')
        try {
            await authedPage.goto(`${UI_BASE}/v2/agentcanvas/${flowId}`)
            await authedPage.waitForTimeout(5000)

            // Double-click to open agent config
            await authedPage.locator('text=Agent 0').dblclick()
            await authedPage.waitForTimeout(1000)

            // Verify region is shown in the config
            const content = await authedPage.content()
            expect(content).toContain('eu-west-1')
        } finally {
            await deleteFlowViaAPI(api, flowId)
        }
    })
})
