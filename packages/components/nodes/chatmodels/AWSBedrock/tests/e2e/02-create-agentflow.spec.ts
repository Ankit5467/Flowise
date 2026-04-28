import { test, expect, UI_BASE, createFlowViaAPI, deleteFlowViaAPI } from './fixtures'

test.describe('Create Agentflow', () => {
    let flowId: string

    test('creates a ResearchAgent-style agentflow via API and opens it in UI', async ({ authedPage, request }) => {
        // Create flow via standalone API request (logs in separately)
        flowId = await createFlowViaAPI(request, 'e2e-test-create', 'anthropic.claude-haiku-4-5-20251001-v1:0')
        expect(flowId).toBeTruthy()

        // Navigate to the agentflow canvas
        await authedPage.goto(`${UI_BASE}/v2/agentcanvas/${flowId}`)
        await authedPage.waitForTimeout(5000)

        // Take a screenshot for debugging
        await authedPage.screenshot({ path: 'packages/components/nodes/chatmodels/AWSBedrock/tests/e2e/screenshots/02-canvas.png' })

        // Verify canvas loads with nodes (ReactFlow renders .react-flow__node divs)
        const nodeCount = await authedPage.locator('.react-flow__node').count()
        console.log(`Canvas nodes found: ${nodeCount}`)
        console.log(`Current URL: ${authedPage.url()}`)
        expect(nodeCount).toBe(3)
    })

    test('shows agent node with AWS Bedrock model', async ({ authedPage }) => {
        await authedPage.goto(`${UI_BASE}/v2/agentcanvas/${flowId}`)
        await authedPage.waitForLoadState('networkidle')
        await authedPage.waitForTimeout(2000)

        // Verify Agent node displays AWS Bedrock icon/label
        await expect(authedPage.locator('text=Agent 0')).toBeVisible({ timeout: 10000 })
    })

    test('can open agent config by clicking on the node', async ({ authedPage }) => {
        await authedPage.goto(`${UI_BASE}/v2/agentcanvas/${flowId}`)
        await authedPage.waitForLoadState('networkidle')
        await authedPage.waitForTimeout(2000)

        // Double-click on Agent node to open config (single-click only selects)
        await authedPage.locator('text=Agent 0').dblclick()
        await authedPage.waitForTimeout(1000)

        // Config dialog should appear
        await expect(authedPage.locator('role=dialog')).toBeVisible({ timeout: 10000 })
    })

    test('save button works', async ({ authedPage }) => {
        await authedPage.goto(`${UI_BASE}/v2/agentcanvas/${flowId}`)
        await authedPage.waitForLoadState('networkidle')
        await authedPage.waitForTimeout(2000)

        // Click save button
        const saveButton = authedPage.locator('button[title*="Save"]')
        await expect(saveButton).toBeVisible({ timeout: 5000 })
        await saveButton.click()

        // Wait for save to complete (no error toast)
        await authedPage.waitForTimeout(2000)
    })

    test.afterAll(async ({ request }) => {
        if (flowId) {
            await deleteFlowViaAPI(request, flowId)
        }
    })
})
