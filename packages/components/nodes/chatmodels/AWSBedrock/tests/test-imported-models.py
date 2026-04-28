#!/usr/bin/env python3
"""End-to-end integration tests for Bedrock IMPORTED models via the Flowise AgentFlow API.

Dynamically fetches all imported models from Bedrock (ListImportedModels),
creates a temporary agentflow for each using the Converse node (awsChatBedrock)
with the imported model ARN in the customModel field (auto-detected → InvokeModel),
sends a prompt, and verifies the response.

Usage:
  python3 test-imported-models.py                # test all imported models
  python3 test-imported-models.py <model-arn>    # test a specific model by ARN

Prerequisites:
  - Flowise running: pnpm dev (localhost:3000)
  - AWS credentials: export AWS_PROFILE=<your-profile>
  - pip install requests boto3
"""
import sys, json, time, os
import requests
import boto3

FLOWISE_URL = "http://localhost:3000"
_cfg_path = os.path.join(os.path.dirname(__file__), "test-config.json")
with open(_cfg_path) as _f:
    _config = __import__("json").load(_f)
EMAIL = _config["email"]
PASSWORD = _config["password"]
HEADERS = {"x-request-from": "internal"}
PROMPT = "Reply with exactly one sentence: what is your model name and who made you?"
REGION = "us-east-1"
TIMEOUT = 120


def login(session=None):
    s = session or requests.Session()
    resp = s.post(f"{FLOWISE_URL}/api/v1/auth/login",
                  json={"email": EMAIL, "password": PASSWORD})
    if resp.status_code != 200 or "error" in resp.json():
        print(f"Login failed: {resp.text[:200]}")
        sys.exit(1)
    return s


def refresh_if_needed(session, resp):
    if resp.status_code == 401 or (resp.status_code == 200 and "Token Expired" in resp.text):
        print("[refreshing session] ", end="", flush=True)
        login(session)
        return True
    return False


def list_imported_models():
    client = boto3.client("bedrock", region_name=REGION)
    resp = client.list_imported_models()
    models = resp.get("modelSummaries", [])
    return [(m["modelName"], m["modelArn"]) for m in models]


def build_converse_flow_with_custom_model(model_arn, region="us-east-1"):
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
                            "cache": "", "region": region,
                            "model": "anthropic.claude-haiku-4-5-20251001-v1:0",
                            "customModel": model_arn,
                            "endpointHost": "",
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


def test_imported_model(session, model_name, model_arn):
    print(f"\n{'='*60}")
    print(f"Testing: {model_name}")
    print(f"ARN:     {model_arn}")
    print(f"{'='*60}")

    flow_data = build_converse_flow_with_custom_model(model_arn, REGION)
    resp = session.post(f"{FLOWISE_URL}/api/v1/chatflows",
                        headers=HEADERS,
                        json={"name": f"e2e-imported-{model_name}",
                              "type": "AGENTFLOW",
                              "flowData": json.dumps(flow_data)})
    if refresh_if_needed(session, resp):
        resp = session.post(f"{FLOWISE_URL}/api/v1/chatflows",
                            headers=HEADERS,
                            json={"name": f"e2e-imported-{model_name}",
                                  "type": "AGENTFLOW",
                                  "flowData": json.dumps(flow_data)})

    flow_id = resp.json().get("id")
    if not flow_id:
        print(f"  FAIL: Could not create flow: {resp.text[:200]}")
        return False

    max_retries = 5
    try:
        for attempt in range(1, max_retries + 1):
            start = time.time()
            resp = session.post(f"{FLOWISE_URL}/api/v1/internal-prediction/{flow_id}",
                                headers=HEADERS,
                                json={"question": PROMPT},
                                timeout=TIMEOUT)
            elapsed = time.time() - start

            if refresh_if_needed(session, resp):
                continue

            data = resp.json()
            text = data.get("text", "")
            error = data.get("message", "")

            if error and "not ready" in error.lower():
                wait = 30 * attempt
                print(f"  Model not ready (attempt {attempt}/{max_retries}), waiting {wait}s...")
                time.sleep(wait)
                continue

            if error:
                print(f"  FAIL ({elapsed:.1f}s): {error[:200]}")
                return False
            elif text:
                print(f"  OK ({elapsed:.1f}s): {text[:150]}")
                return True
            else:
                print(f"  UNKNOWN ({elapsed:.1f}s): {json.dumps(data)[:200]}")
                return False

        print(f"  FAIL: Model still not ready after {max_retries} retries")
        return False

    except requests.exceptions.Timeout:
        print(f"  FAIL: Timeout after {TIMEOUT}s")
        return False
    except Exception as e:
        print(f"  FAIL: {e}")
        return False
    finally:
        session.delete(f"{FLOWISE_URL}/api/v1/chatflows/{flow_id}", headers=HEADERS)
        time.sleep(2)


def main():
    if len(sys.argv) > 1 and sys.argv[1].startswith("arn:"):
        models = [("manual", sys.argv[1])]
    else:
        print("Fetching imported models from Bedrock...")
        models = list_imported_models()
        if not models:
            print("No imported models found. Import models first.")
            sys.exit(1)
        print(f"Found {len(models)} imported model(s):")
        for name, arn in models:
            print(f"  - {name}: {arn}")

    session = login()
    passed, failed = 0, 0

    for name, arn in models:
        ok = test_imported_model(session, name, arn)
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\n{'='*60}")
    print(f"RESULTS: {passed} passed, {failed} failed, {len(models)} total")
    print(f"{'='*60}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
