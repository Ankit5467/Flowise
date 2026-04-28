#!/usr/bin/env python3
"""Test that changing a model ID in a flow actually routes to the new model.

Creates a flow with model A, asks a question, updates the flow to model B,
asks the same question again, and compares responses.
"""
import json, copy, os
import requests

FLOWISE_URL = "http://localhost:3000"
_cfg_path = os.path.join(os.path.dirname(__file__), "test-config.json")
with open(_cfg_path) as _f:
    _config = __import__("json").load(_f)
EMAIL = _config["email"]
PASSWORD = _config["password"]
HEADERS = {"x-request-from": "internal"}
PROMPT = "Who is your maker? Reply in one short sentence."

MODEL_A = "anthropic.claude-haiku-4-5-20251001-v1:0"
MODEL_B = "amazon.nova-micro-v1:0"


def login():
    s = requests.Session()
    resp = s.post(f"{FLOWISE_URL}/api/v1/auth/login",
                  json={"email": EMAIL, "password": PASSWORD})
    if resp.status_code != 200:
        print(f"Login failed: {resp.text[:200]}")
        exit(1)
    return s


def build_flow_data(model_id):
    return {
        "nodes": [
            {
                "id": "startAgentflow_0", "type": "agentFlow",
                "position": {"x": 0, "y": 0},
                "data": {
                    "id": "startAgentflow_0", "label": "Start", "version": 1.1,
                    "name": "startAgentflow", "type": "Start", "color": "#7EE787",
                    "hideInput": True, "baseClasses": ["Start"], "category": "Agent Flows",
                    "description": "Starting point",
                    "inputParams": [
                        {"label": "Input Type", "name": "startInputType", "type": "options",
                         "options": [{"label": "Chat Input", "name": "chatInput"}],
                         "default": "chatInput", "id": "s0-input", "display": True},
                        {"label": "Ephemeral Memory", "name": "startEphemeralMemory",
                         "type": "boolean", "optional": True, "id": "s0-mem", "display": True}
                    ],
                    "inputAnchors": [],
                    "inputs": {"startInputType": "chatInput", "startEphemeralMemory": True},
                    "outputAnchors": [{"id": "s0-out", "label": "Start", "name": "startAgentflow"}],
                    "outputs": {}
                }
            },
            {
                "id": "agentAgentflow_0", "type": "agentFlow",
                "position": {"x": 200, "y": 0},
                "data": {
                    "id": "agentAgentflow_0", "label": "Agent 0", "version": 3.2,
                    "name": "agentAgentflow", "type": "Agent", "color": "#4DD0E1",
                    "baseClasses": ["Agent"], "category": "Agent Flows", "description": "Agent",
                    "inputParams": [
                        {"label": "Model", "name": "agentModel", "type": "asyncOptions",
                         "loadMethod": "listModels", "loadConfig": True,
                         "id": "a0-model", "display": True}
                    ],
                    "inputAnchors": [],
                    "inputs": {
                        "agentModel": "awsChatBedrock",
                        "agentMessages": [], "agentTools": [],
                        "agentKnowledgeDocumentStores": "", "agentKnowledgeVSEmbeddings": "",
                        "agentEnableMemory": False, "agentMemoryType": "allMessages",
                        "agentUserMessage": "", "agentReturnResponseAs": "userMessage",
                        "agentStructuredOutput": "", "agentUpdateState": "",
                        "agentModelConfig": {
                            "cache": "", "region": "us-east-1",
                            "model": model_id,
                            "customModel": "", "endpointHost": "",
                            "streaming": True, "temperature": 0.7,
                            "max_tokens_to_sample": 200,
                            "allowImageUploads": "", "latencyOptimized": "",
                            "agentModel": "awsChatBedrock"
                        }
                    },
                    "outputAnchors": [{"id": "a0-out", "label": "Agent", "name": "agentAgentflow"}],
                    "outputs": {}
                }
            },
            {
                "id": "directReplyAgentflow_0", "type": "agentFlow",
                "position": {"x": 400, "y": 0},
                "data": {
                    "id": "directReplyAgentflow_0", "label": "Direct Reply 0", "version": 1,
                    "name": "directReplyAgentflow", "type": "DirectReply", "color": "#4DDBBB",
                    "hideOutput": True, "baseClasses": ["DirectReply"], "category": "Agent Flows",
                    "description": "Direct reply",
                    "inputParams": [
                        {"label": "Message", "name": "directReplyMessage", "type": "string",
                         "rows": 4, "acceptVariable": True, "id": "dr0-msg", "display": True}
                    ],
                    "inputAnchors": [],
                    "inputs": {
                        "directReplyMessage": '<p><span class="variable" data-type="mention" data-id="agentAgentflow_0" data-label="agentAgentflow_0">{{ agentAgentflow_0 }}</span> </p>'
                    },
                    "outputAnchors": [], "outputs": {}
                }
            }
        ],
        "edges": [
            {"source": "startAgentflow_0", "sourceHandle": "s0-out",
             "target": "agentAgentflow_0", "targetHandle": "agentAgentflow_0",
             "data": {"sourceColor": "#7EE787", "targetColor": "#4DD0E1", "isHumanInput": False},
             "type": "agentFlow", "id": "e1"},
            {"source": "agentAgentflow_0", "sourceHandle": "a0-out",
             "target": "directReplyAgentflow_0", "targetHandle": "directReplyAgentflow_0",
             "data": {"sourceColor": "#4DD0E1", "targetColor": "#4DDBBB", "isHumanInput": False},
             "type": "agentFlow", "id": "e2"}
        ]
    }


def ask(session, flow_id, question):
    resp = session.post(f"{FLOWISE_URL}/api/v1/internal-prediction/{flow_id}",
                        headers=HEADERS, json={"question": question}, timeout=30)
    data = resp.json()
    if "text" in data:
        return data["text"]
    elif "message" in data:
        return f"ERROR: {data['message']}"
    return f"UNKNOWN: {json.dumps(data)[:200]}"


if __name__ == "__main__":
    print("Logging in...")
    session = login()
    print("Logged in.\n")

    # Step 1: Create flow with Model A
    print(f"Step 1: Creating flow with MODEL A = {MODEL_A}")
    flow_data_a = build_flow_data(MODEL_A)
    resp = session.post(f"{FLOWISE_URL}/api/v1/chatflows", headers=HEADERS,
                        json={"name": "test-model-switch", "type": "AGENTFLOW",
                              "flowData": json.dumps(flow_data_a)})
    if resp.status_code != 200:
        print(f"Failed to create flow: {resp.text[:200]}")
        exit(1)
    flow = resp.json()
    flow_id = flow["id"]
    print(f"  Flow created: {flow_id}\n")

    # Step 2: Ask question with Model A
    print(f"Step 2: Asking '{PROMPT}' with MODEL A ({MODEL_A})")
    answer_a = ask(session, flow_id, PROMPT)
    print(f"  Response A: {answer_a[:200]}\n")

    # Step 3: Update the flow to use Model B
    print(f"Step 3: Updating flow to MODEL B = {MODEL_B}")
    flow_data_b = build_flow_data(MODEL_B)
    update_resp = session.put(f"{FLOWISE_URL}/api/v1/chatflows/{flow_id}",
                              headers=HEADERS,
                              json={"flowData": json.dumps(flow_data_b)})
    if update_resp.status_code != 200:
        print(f"  Failed to update: {update_resp.text[:200]}")
    else:
        print(f"  Flow updated successfully.\n")

    # Step 4: Ask the same question with Model B
    print(f"Step 4: Asking '{PROMPT}' with MODEL B ({MODEL_B})")
    answer_b = ask(session, flow_id, PROMPT)
    print(f"  Response B: {answer_b[:200]}\n")

    # Step 5: Compare
    print("=" * 70)
    print(f"MODEL A ({MODEL_A}):")
    print(f"  {answer_a[:200]}")
    print(f"\nMODEL B ({MODEL_B}):")
    print(f"  {answer_b[:200]}")
    print()

    a_mentions_anthropic = "anthropic" in answer_a.lower() or "claude" in answer_a.lower()
    b_mentions_amazon = "amazon" in answer_b.lower() or "nova" in answer_b.lower()

    if a_mentions_anthropic and b_mentions_amazon:
        print("PASS: Model switch confirmed. A=Anthropic, B=Amazon.")
    elif a_mentions_anthropic and not b_mentions_amazon:
        print("FAIL: Model B still responded as if it were Model A (Anthropic).")
    else:
        print(f"INCONCLUSIVE: Check responses manually.")

    # Cleanup
    session.delete(f"{FLOWISE_URL}/api/v1/chatflows/{flow_id}", headers=HEADERS)
    print("Test flow deleted.")
