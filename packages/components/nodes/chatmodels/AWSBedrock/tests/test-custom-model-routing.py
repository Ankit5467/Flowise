#!/usr/bin/env python3
"""Tests for the custom model routing decision tree in the Converse node.

Verifies that the AWS Bedrock (Converse) node correctly auto-detects model types
and routes to the appropriate API:
  - Imported models (instructSupported: false) → InvokeModel API
  - Built-in models → Converse API
  - Imported models via the explicit Imported node → InvokeModel API

Dynamically fetches imported models from Bedrock. Also tests built-in models
to verify they still work through the same node.

Usage:
  python3 test-custom-model-routing.py

Prerequisites:
  - Flowise running: pnpm dev (localhost:3000)
  - AWS credentials configured
  - At least one imported model in Bedrock
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
AWS_ACCOUNT_ID = _config.get("awsAccountId", "123456789000")
HEADERS = {"x-request-from": "internal"}
PROMPT = "Reply with exactly one sentence: what is your model name and who made you?"
REGION = "us-east-1"
TIMEOUT = 120
MAX_RETRIES = 5


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
    return [(m["modelName"], m["modelArn"]) for m in resp.get("modelSummaries", [])]


def build_converse_flow(model_id, region="us-east-1", custom_model=""):
    """Build flow using the CONVERSE node (awsChatBedrock) with customModel field."""
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
                            "model": model_id,
                            "customModel": custom_model,
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


def invoke_flow(session, flow_name, flow_data):
    """Create flow, send prompt, return (text, error), delete flow."""
    resp = session.post(f"{FLOWISE_URL}/api/v1/chatflows",
                        headers=HEADERS,
                        json={"name": flow_name, "type": "AGENTFLOW",
                              "flowData": json.dumps(flow_data)})
    if refresh_if_needed(session, resp):
        resp = session.post(f"{FLOWISE_URL}/api/v1/chatflows",
                            headers=HEADERS,
                            json={"name": flow_name, "type": "AGENTFLOW",
                                  "flowData": json.dumps(flow_data)})
    flow_id = resp.json().get("id")
    if not flow_id:
        return None, f"Could not create flow: {resp.text[:200]}"

    try:
        for attempt in range(1, MAX_RETRIES + 1):
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
                print(f"    Model not ready (attempt {attempt}/{MAX_RETRIES}), waiting {wait}s...")
                time.sleep(wait)
                continue
            return text, error
        return None, "Model still not ready after retries"
    except requests.exceptions.Timeout:
        return None, f"Timeout after {TIMEOUT}s"
    except Exception as e:
        return None, str(e)
    finally:
        session.delete(f"{FLOWISE_URL}/api/v1/chatflows/{flow_id}", headers=HEADERS)
        time.sleep(2)


def test_case(session, name, flow_data, expect_pass=True):
    print(f"\n  TEST: {name}")
    text, error = invoke_flow(session, f"routing-{name}", flow_data)
    if expect_pass:
        if error:
            print(f"    FAIL: {error[:200]}")
            return False
        if text:
            print(f"    PASS ({text[:120]})")
            return True
        print(f"    FAIL: Empty response")
        return False
    else:
        if error:
            print(f"    PASS (expected error): {error[:120]}")
            return True
        print(f"    FAIL: Expected error but got: {text[:120]}")
        return False


def main():
    session = login()
    passed, failed = 0, 0
    results = []

    def run(name, flow_data, expect_pass=True):
        nonlocal passed, failed
        ok = test_case(session, name, flow_data, expect_pass)
        results.append((name, ok))
        if ok: passed += 1
        else: failed += 1

    # --- Fetch imported models ---
    imported = list_imported_models()
    print(f"Found {len(imported)} imported model(s)")
    for name, arn in imported:
        print(f"  - {name}: {arn}")

    # =====================================================================
    print("\n" + "="*60)
    print("SECTION 1: Imported models via CONVERSE node (auto-detection)")
    print("  Uses awsChatBedrock with imported ARN in customModel field")
    print("="*60)

    for name, arn in imported:
        flow = build_converse_flow(
            model_id="anthropic.claude-haiku-4-5-20251001-v1:0",
            custom_model=arn,
            region=REGION
        )
        run(f"converse-node-imported-{name}", flow)

    # =====================================================================
    print("\n" + "="*60)
    print("SECTION 2: Built-in model via CONVERSE node (baseline)")
    print("  Verifies normal Converse path still works")
    print("="*60)

    flow = build_converse_flow(
        model_id="amazon.nova-micro-v1:0",
        region=REGION
    )
    run("converse-node-builtin-nova-micro", flow)

    # =====================================================================
    print("\n" + "="*60)
    print("SECTION 3: Built-in model with inference profile override")
    print("="*60)

    flow = build_converse_flow(
        model_id="anthropic.claude-haiku-4-5-20251001-v1:0",
        custom_model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        region=REGION
    )
    run("converse-node-inference-profile", flow)

    # =====================================================================
    print("\n" + "="*60)
    print("SECTION 4: Streaming disabled (non-streaming path)")
    print("="*60)

    if imported:
        name, arn = imported[0]
        flow = build_converse_flow(
            model_id="anthropic.claude-haiku-4-5-20251001-v1:0",
            custom_model=arn,
            region=REGION
        )
        flow["nodes"][1]["data"]["inputs"]["agentModelConfig"]["streaming"] = False
        run(f"converse-node-imported-no-stream-{name}", flow)

    flow = build_converse_flow(model_id="amazon.nova-micro-v1:0", region=REGION)
    flow["nodes"][1]["data"]["inputs"]["agentModelConfig"]["streaming"] = False
    run("converse-node-builtin-no-stream", flow)

    # =====================================================================
    print("\n" + "="*60)
    print("SECTION 5: StopSequences model (DeepSeek)")
    print("="*60)

    flow = build_converse_flow(
        model_id="deepseek.r1-v1:0",
        region=REGION
    )
    run("converse-node-deepseek-stopseq", flow)

    # =====================================================================
    print("\n" + "="*60)
    print("SECTION 6: Different region (eu-west-1)")
    print("="*60)

    flow = build_converse_flow(
        model_id="amazon.nova-micro-v1:0",
        region="eu-west-1"
    )
    run("converse-node-builtin-eu-west-1", flow)

    # =====================================================================
    print("\n" + "="*60)
    print("SECTION 7: Invalid/nonexistent model (error handling)")
    print("="*60)

    flow = build_converse_flow(
        model_id="anthropic.claude-haiku-4-5-20251001-v1:0",
        custom_model=f"arn:aws:bedrock:us-east-1:{AWS_ACCOUNT_ID}:imported-model/nonexistent999",
        region=REGION
    )
    run("converse-node-nonexistent-imported", flow, expect_pass=False)

    # =====================================================================
    print("\n" + "="*60)
    print("SECTION 8: Inference profile ARN in customModel (should work)")
    print("="*60)

    flow = build_converse_flow(
        model_id="anthropic.claude-haiku-4-5-20251001-v1:0",
        custom_model=f"arn:aws:bedrock:us-east-1:{AWS_ACCOUNT_ID}:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0",
        region=REGION
    )
    run("converse-node-inference-profile-arn", flow)

    # =====================================================================
    print("\n" + "="*60)
    print("SECTION 9: Foundation model ARN in customModel (should fail)")
    print("="*60)

    flow = build_converse_flow(
        model_id="anthropic.claude-haiku-4-5-20251001-v1:0",
        custom_model="arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0",
        region=REGION
    )
    run("converse-node-foundation-model-arn", flow, expect_pass=False)

    # =====================================================================
    print(f"\n{'='*60}")
    print(f"RESULTS: {passed} passed, {failed} failed, {passed+failed} total")
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}: {name}")
    print(f"{'='*60}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
