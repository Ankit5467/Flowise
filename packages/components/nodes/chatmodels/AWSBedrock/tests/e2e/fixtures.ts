/**
 * Playwright E2E test fixtures and helpers for Flowise Bedrock integration.
 *
 * Provides:
 * - `authedPage` fixture: logs into Flowise UI before each test
 * - `buildFlowData()`: creates a Start → Agent → DirectReply agentflow JSON
 *   matching the ResearchAgent pattern (context/ResearchAgent Agents.json)
 * - `createFlowViaAPI()` / `deleteFlowViaAPI()` / `sendMessageViaAPI()`:
 *   API helpers that authenticate and manage test flows
 *
 * Key design choice: API calls use `authedPage.request` (not standalone
 * `request`) because Flowise auth relies on HttpOnly cookies that are
 * only accessible within the browser's cookie jar.
 *
 * Requires: Flowise running on localhost:8080 (UI) / localhost:3000 (API)
 */
import { test as base, expect, type Page, type APIRequestContext } from '@playwright/test'
import * as fs from 'fs'
import * as path from 'path'

const testConfig = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'test-config.json'), 'utf8'))
const EMAIL = testConfig.email
const PASSWORD = testConfig.password
const API_BASE = testConfig.apiBase || 'http://localhost:3000'
const INTERNAL_HEADERS = { 'x-request-from': 'internal' }

export const UI_BASE = testConfig.uiBase || 'http://localhost:8080'

/**
 * Authenticated test fixture.
 * Logs in via the UI at the start of each test that needs it.
 * Uses a quick login flow — fill form + submit + wait.
 */
export const test = base.extend<{ authedPage: Page }>({
    authedPage: async ({ page }, use) => {
        // Login via UI
        await page.goto(`${UI_BASE}/signin`, { waitUntil: 'domcontentloaded' })
        await page.waitForTimeout(3000)
        await page.locator('input[name="username"]').fill(EMAIL)
        await page.locator('input[name="password"]').fill(PASSWORD)
        await page.locator('button[type="submit"]').click()
        await page.waitForTimeout(8000) // generous wait for login + redirect
        await use(page)
    }
})

export { expect }

/** Load models from models.json */
export function loadModels(): any[] {
    const modelsPath = path.join(__dirname, '..', '..', '..', '..', '..', 'models.json')
    const data = JSON.parse(fs.readFileSync(modelsPath, 'utf8'))
    const bedrock = data.chat.find((c: any) => c.name === 'awsChatBedrock')
    return bedrock.models
}

/** Build agentflow JSON matching ResearchAgent pattern (Start → Agent → DirectReply) */
export function buildFlowData(modelId: string, region = 'us-east-1'): object {
    return {
        nodes: [
            {
                id: 'startAgentflow_0',
                type: 'agentFlow',
                position: { x: -134, y: 47 },
                data: {
                    id: 'startAgentflow_0',
                    label: 'Start',
                    version: 1.1,
                    name: 'startAgentflow',
                    type: 'Start',
                    color: '#7EE787',
                    hideInput: true,
                    baseClasses: ['Start'],
                    category: 'Agent Flows',
                    description: 'Starting point of the agentflow',
                    inputParams: [
                        {
                            label: 'Input Type',
                            name: 'startInputType',
                            type: 'options',
                            options: [{ label: 'Chat Input', name: 'chatInput' }],
                            default: 'chatInput',
                            id: 'startAgentflow_0-input-startInputType-options',
                            display: true
                        },
                        {
                            label: 'Ephemeral Memory',
                            name: 'startEphemeralMemory',
                            type: 'boolean',
                            optional: true,
                            id: 'startAgentflow_0-input-startEphemeralMemory-boolean',
                            display: true
                        }
                    ],
                    inputAnchors: [],
                    inputs: { startInputType: 'chatInput', startEphemeralMemory: true },
                    outputAnchors: [{ id: 'startAgentflow_0-output-startAgentflow', label: 'Start', name: 'startAgentflow' }],
                    outputs: {}
                }
            },
            {
                id: 'agentAgentflow_0',
                type: 'agentFlow',
                position: { x: 60, y: 37 },
                data: {
                    id: 'agentAgentflow_0',
                    label: 'Agent 0',
                    version: 3.2,
                    name: 'agentAgentflow',
                    type: 'Agent',
                    color: '#4DD0E1',
                    baseClasses: ['Agent'],
                    category: 'Agent Flows',
                    description: 'Dynamically choose and utilize tools during runtime',
                    inputParams: [
                        {
                            label: 'Model',
                            name: 'agentModel',
                            type: 'asyncOptions',
                            loadMethod: 'listModels',
                            loadConfig: true,
                            id: 'agentAgentflow_0-input-agentModel-asyncOptions',
                            display: true
                        }
                    ],
                    inputAnchors: [],
                    inputs: {
                        agentModel: 'awsChatBedrock',
                        agentMessages: [],
                        agentTools: [],
                        agentKnowledgeDocumentStores: '',
                        agentKnowledgeVSEmbeddings: '',
                        agentEnableMemory: true,
                        agentMemoryType: 'allMessages',
                        agentUserMessage: '',
                        agentReturnResponseAs: 'userMessage',
                        agentStructuredOutput: '',
                        agentUpdateState: '',
                        agentModelConfig: {
                            cache: '',
                            region,
                            model: modelId,
                            customModel: '',
                            endpointHost: '',
                            streaming: true,
                            temperature: 0.7,
                            max_tokens_to_sample: 200,
                            allowImageUploads: '',
                            latencyOptimized: '',
                            agentModel: 'awsChatBedrock'
                        }
                    },
                    outputAnchors: [{ id: 'agentAgentflow_0-output-agentAgentflow', label: 'Agent', name: 'agentAgentflow' }],
                    outputs: {}
                }
            },
            {
                id: 'directReplyAgentflow_0',
                type: 'agentFlow',
                position: { x: 449, y: 49 },
                data: {
                    id: 'directReplyAgentflow_0',
                    label: 'Direct Reply 0',
                    version: 1,
                    name: 'directReplyAgentflow',
                    type: 'DirectReply',
                    color: '#4DDBBB',
                    hideOutput: true,
                    baseClasses: ['DirectReply'],
                    category: 'Agent Flows',
                    description: 'Directly reply to the user with a message',
                    inputParams: [
                        {
                            label: 'Message',
                            name: 'directReplyMessage',
                            type: 'string',
                            rows: 4,
                            acceptVariable: true,
                            id: 'directReplyAgentflow_0-input-directReplyMessage-string',
                            display: true
                        }
                    ],
                    inputAnchors: [],
                    inputs: {
                        directReplyMessage:
                            '<p><span class="variable" data-type="mention" data-id="agentAgentflow_0" data-label="agentAgentflow_0">{{ agentAgentflow_0 }}</span> </p>'
                    },
                    outputAnchors: [],
                    outputs: {}
                }
            }
        ],
        edges: [
            {
                source: 'startAgentflow_0',
                sourceHandle: 'startAgentflow_0-output-startAgentflow',
                target: 'agentAgentflow_0',
                targetHandle: 'agentAgentflow_0',
                data: { sourceColor: '#7EE787', targetColor: '#4DD0E1', isHumanInput: false },
                type: 'agentFlow',
                id: 'startAgentflow_0-startAgentflow_0-output-startAgentflow-agentAgentflow_0-agentAgentflow_0'
            },
            {
                source: 'agentAgentflow_0',
                sourceHandle: 'agentAgentflow_0-output-agentAgentflow',
                target: 'directReplyAgentflow_0',
                targetHandle: 'directReplyAgentflow_0',
                data: { sourceColor: '#4DD0E1', targetColor: '#4DDBBB', isHumanInput: false },
                type: 'agentFlow',
                id: 'agentAgentflow_0-agentAgentflow_0-output-agentAgentflow-directReplyAgentflow_0-directReplyAgentflow_0'
            }
        ]
    }
}

/** Build agentflow JSON using the CONVERSE node with a customModel override */
export function buildConverseFlowWithCustomModel(customModel: string, region = 'us-east-1'): object {
    const base = buildFlowData('anthropic.claude-haiku-4-5-20251001-v1:0', region) as any
    base.nodes[1].data.inputs.agentModelConfig.customModel = customModel
    return base
}

/** Create a Converse flow with customModel override via API */
export async function createConverseFlowWithCustomModelViaAPI(
    request: APIRequestContext,
    name: string,
    customModel: string,
    region = 'us-east-1'
): Promise<string> {
    await ensureAPIAuth(request)
    const resp = await request.post(`${API_BASE}/api/v1/chatflows`, {
        headers: INTERNAL_HEADERS,
        data: {
            name,
            type: 'AGENTFLOW',
            flowData: JSON.stringify(buildConverseFlowWithCustomModel(customModel, region))
        }
    })
    const data = await resp.json()
    return data.id
}

/** List imported models from Bedrock via AWS CLI */
export async function listImportedModels(): Promise<Array<{ name: string; arn: string }>> {
    const { execSync } = require('child_process')
    try {
        const output = execSync('aws bedrock list-imported-models --region us-east-1 --output json', {
            encoding: 'utf8',
            timeout: 15000
        })
        const data = JSON.parse(output)
        return (data.modelSummaries || []).map((m: any) => ({
            name: m.modelName,
            arn: m.modelArn
        }))
    } catch {
        return []
    }
}

/** Ensure the API request context is authenticated */
async function ensureAPIAuth(request: APIRequestContext): Promise<void> {
    await request.post(`${API_BASE}/api/v1/auth/login`, {
        data: { email: EMAIL, password: PASSWORD }
    })
}

/** Create a flow via API and return its ID */
export async function createFlowViaAPI(request: APIRequestContext, name: string, modelId: string, region = 'us-east-1'): Promise<string> {
    await ensureAPIAuth(request)
    const resp = await request.post(`${API_BASE}/api/v1/chatflows`, {
        headers: INTERNAL_HEADERS,
        data: {
            name,
            type: 'AGENTFLOW',
            flowData: JSON.stringify(buildFlowData(modelId, region))
        }
    })
    const data = await resp.json()
    return data.id
}

/** Delete a flow via API */
export async function deleteFlowViaAPI(request: APIRequestContext, flowId: string): Promise<void> {
    await ensureAPIAuth(request)
    await request.delete(`${API_BASE}/api/v1/chatflows/${flowId}`, {
        headers: INTERNAL_HEADERS
    })
}

/** Send a chat message via API and return the response text */
export async function sendMessageViaAPI(request: APIRequestContext, flowId: string, question: string): Promise<string> {
    await ensureAPIAuth(request)
    const resp = await request.post(`${API_BASE}/api/v1/internal-prediction/${flowId}`, {
        headers: INTERNAL_HEADERS,
        data: { question },
        timeout: 120_000
    })
    const data = await resp.json()
    if (data.text) return data.text
    if (data.message) return `ERROR: ${data.message}`
    return `UNKNOWN: ${JSON.stringify(data).slice(0, 200)}`
}
