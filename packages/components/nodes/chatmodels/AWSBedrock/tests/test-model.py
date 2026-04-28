#!/usr/bin/env python3
"""End-to-end integration tests for Bedrock models via the Flowise AgentFlow API.

These are REAL tests — each invocation creates a temporary agentflow in Flowise,
sends a prompt to the actual AWS Bedrock API (costing real tokens), and deletes
the flow afterward. Requires Flowise running on localhost:3000 and valid AWS
credentials (via AWS_PROFILE or environment).

Usage:
  python3 test-model.py                                              # test Nova Micro in us-east-1
  python3 test-model.py amazon.nova-micro-v1:0                       # test specific model in us-east-1
  python3 test-model.py amazon.nova-pro-v1:0 eu-west-1               # test specific model in a specific region
  python3 test-model.py amazon.nova-pro-v1:0 eu-west-1 300           # same, with 300s timeout
  python3 test-model.py nvidia.nemotron-super-3-120b us-east-1 600   # slow model, 10 min timeout

Batch modes:
  python3 test-model.py ALL                                # all 63 models in us-east-1 (~5 min)
  python3 test-model.py PROFILES                           # inference profile models, 2 regions per geo (~10 min)
  python3 test-model.py PROFILES_ALL                       # inference profile models × ALL 16 regions (~28 min)
  python3 test-model.py REGIONS                            # all models × all available regions (~45 min)

Prerequisites:
  - Flowise running: pnpm dev (localhost:3000)
  - AWS credentials: export AWS_PROFILE=<your-profile>
  - Availability map (for REGIONS/PROFILES_ALL): python3 build-availability-map.py
  - pip install requests

Notes:
  - Each test creates and deletes a temporary agentflow (ephemeral memory, no chat history)
  - Auth uses session cookies (email/password hardcoded below — update if needed)
  - 1s delay between calls to avoid throttling
  - PROFILES tests geo-prefix routing: us./eu./apac./jp./au./ca./global.
  - PROFILES_ALL verifies cross-region routing from every Bedrock-enabled region
  - REGIONS tests direct on-demand invocation (non-profile models) in every deployed region
"""
import sys, json, time, os
import requests

FLOWISE_URL = "http://localhost:3000"
_cfg_path = os.path.join(os.path.dirname(__file__), "test-config.json")
with open(_cfg_path) as _f:
    _config = __import__("json").load(_f)
EMAIL = _config["email"]
PASSWORD = _config["password"]
HEADERS = {"x-request-from": "internal"}
PROMPT = "Reply with exactly one sentence: what is your model name and who made you?"


def login(session=None):
    """Login and return a session with auth cookies. Reuses existing session if provided."""
    s = session or requests.Session()
    resp = s.post(f"{FLOWISE_URL}/api/v1/auth/login",
                  json={"email": EMAIL, "password": PASSWORD})
    if resp.status_code != 200 or "error" in resp.json():
        print(f"Login failed: {resp.text[:200]}")
        sys.exit(1)
    return s


def refresh_if_needed(session, resp):
    """Re-login if the response indicates token expiry. Returns True if refreshed."""
    if resp.status_code == 401 or (resp.status_code == 200 and "Token Expired" in resp.text):
        print("[refreshing session] ", end="", flush=True)
        login(session)
        return True
    return False


def build_flow_data(model_id, region="us-east-1", custom_model=""):
    """Build an agentflow JSON with the given model, region, and optional customModel override."""
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


DEFAULT_TIMEOUT = 120

# Models known to lack inference capacity in certain non-US regions.
# Timeouts for these are expected — AWS lists them as available but
# has insufficient capacity to serve requests in a reasonable time.
KNOWN_CAPACITY_ISSUES = {
    "nvidia.nemotron-super-3-120b": ["eu-west-1", "eu-central-1", "eu-north-1", "ap-northeast-1", "ap-south-1", "ap-southeast-2", "sa-east-1"],
    "nvidia.nemotron-nano-9b-v2": ["ap-southeast-2"],
    "nvidia.nemotron-nano-12b-v2": ["ap-southeast-2"],
    "minimax.minimax-m2.1": ["eu-north-1"],
    "minimax.minimax-m2.5": ["eu-north-1"],
    "moonshot.kimi-k2-thinking": ["sa-east-1"],
    "zai.glm-4.7": ["sa-east-1"],
}

def is_pass(result):
    """Check if a test result is a pass (contains '- OK:' after the latency prefix)."""
    return "- OK:" in result

def test_model(session, model_id, region="us-east-1", custom_model="", timeout=DEFAULT_TIMEOUT):
    """Create a temp agentflow, send a prompt, return the response, then delete the flow."""
    flow_data = build_flow_data(model_id, region, custom_model)
    create_payload = {"name": f"test-{model_id}-{region}", "type": "AGENTFLOW",
                      "flowData": json.dumps(flow_data)}

    # Create flow (with token refresh retry)
    resp = session.post(f"{FLOWISE_URL}/api/v1/chatflows", headers=HEADERS, json=create_payload)
    if refresh_if_needed(session, resp):
        resp = session.post(f"{FLOWISE_URL}/api/v1/chatflows", headers=HEADERS, json=create_payload)
    if resp.status_code != 200:
        return f"FAIL (create): {resp.text[:200]}"

    flow_id = resp.json()["id"]

    # Send prompt
    try:
        t0 = time.time()
        pred = session.post(f"{FLOWISE_URL}/api/v1/internal-prediction/{flow_id}",
                            headers=HEADERS, json={"question": PROMPT}, timeout=timeout)
        if refresh_if_needed(session, pred):
            t0 = time.time()
            pred = session.post(f"{FLOWISE_URL}/api/v1/internal-prediction/{flow_id}",
                                headers=HEADERS, json={"question": PROMPT}, timeout=timeout)
        elapsed = int(time.time() - t0)
        data = pred.json()
        if "text" in data:
            result = f"{elapsed}s - OK: {data['text'][:150]}"
        elif "message" in data:
            result = f"{elapsed}s - ERROR: {data['message']}"
        else:
            result = f"{elapsed}s - UNKNOWN: {json.dumps(data)}"
    except requests.exceptions.Timeout:
        known_regions = KNOWN_CAPACITY_ISSUES.get(model_id, [])
        if region in known_regions:
            result = f"TIMEOUT ({timeout}s) — EXPECTED: this model lacks inference capacity in {region}. Not a Flowise bug."
        else:
            result = f"TIMEOUT ({timeout}s)"
    except Exception as e:
        result = f"EXCEPTION: {e}"

    # Cleanup
    session.delete(f"{FLOWISE_URL}/api/v1/chatflows/{flow_id}", headers=HEADERS)
    return result


def load_catalog():
    """Load models from models.json."""
    models_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'models.json')
    with open(models_path) as f:
        catalog = json.load(f)
    return next(c for c in catalog['chat'] if c['name'] == 'awsChatBedrock')


def test_all(session):
    """Test every model in the catalog with default region."""
    bedrock = load_catalog()
    models = [m['name'] for m in bedrock['models']]
    print(f"Testing {len(models)} models (region: us-east-1)...\n")
    results = []
    for m in models:
        print(f"  {m:<55} ", end="", flush=True)
        r = test_model(session, m)
        print(r[:80])
        results.append((m, r))
        time.sleep(5)
    print(f"\n{'='*80}")
    passed = sum(1 for _, r in results if is_pass(r))
    failed = sum(1 for _, r in results if not is_pass(r))
    print(f"PASSED: {passed}  FAILED: {failed}  TOTAL: {len(results)}")
    return results


def test_profiles(session):
    """Test inference profile routing across us, eu, and apac geos.

    For each model that has inference_profile_geos, test with a region
    from each supported geo to verify the correct profile is applied.
    """
    bedrock = load_catalog()
    # Two regions per geo to validate cross-region routing within each geo.
    # jp is a Tokyo-specific prefix -- tested from ap-northeast-1.
    geo_regions = {
        "us": ["us-east-1", "us-west-2"],
        "eu": ["eu-west-1", "eu-central-1"],
        "apac": ["ap-southeast-1", "ap-southeast-2"],
        "jp": ["ap-northeast-1"],
    }

    # Collect models with inference profiles
    profile_models = [m for m in bedrock['models'] if m.get('inference_profile_geos')]
    print(f"Testing inference profiles for {len(profile_models)} models across geos (2 regions each)...\n")

    results = []

    test_cases = []
    for m in profile_models:
        geos = m['inference_profile_geos']
        for geo in geos:
            if geo == "global":
                continue  # global uses same region as us, skip to avoid duplicate
            for region in geo_regions.get(geo, []):
                test_cases.append((m['name'], geo, region))

    print(f"Total test cases: {len(test_cases)}\n")
    print(f"  {'Model':<50} {'Geo':<6} {'Region':<18} Result")
    print(f"  {'-'*50} {'-'*6} {'-'*18} {'-'*40}")

    for model_id, geo, region in test_cases:
        print(f"  {model_id:<50} {geo:<6} {region:<18} ", end="", flush=True)
        r = test_model(session, model_id, region=region)
        status = "PASS" if is_pass(r) else "FAIL"
        print(f"{status}: {r[:65]}")
        results.append((model_id, geo, region, r))
        time.sleep(5)

    # Also test explicit profile via customModel field
    print(f"\n  --- Explicit profile via customModel field ---")
    explicit_cases = [
        ("anthropic.claude-sonnet-4-6", "eu.anthropic.claude-sonnet-4-6", "eu-west-1"),
        ("anthropic.claude-sonnet-4-6", "eu.anthropic.claude-sonnet-4-6", "eu-central-1"),
        ("amazon.nova-pro-v1:0", "apac.amazon.nova-pro-v1:0", "ap-southeast-1"),
        ("amazon.nova-pro-v1:0", "apac.amazon.nova-pro-v1:0", "ap-southeast-2"),
        ("anthropic.claude-sonnet-4-6", "jp.anthropic.claude-sonnet-4-6", "ap-northeast-1"),
        ("anthropic.claude-opus-4-5-20251101-v1:0", "global.anthropic.claude-opus-4-5-20251101-v1:0", "us-east-1"),
        ("anthropic.claude-opus-4-5-20251101-v1:0", "global.anthropic.claude-opus-4-5-20251101-v1:0", "eu-west-1"),
    ]
    for model_id, custom_model, region in explicit_cases:
        print(f"  {custom_model:<50} {'explicit':<6} {region:<18} ", end="", flush=True)
        r = test_model(session, model_id, region=region, custom_model=custom_model)
        status = "PASS" if is_pass(r) else "FAIL"
        print(f"{status}: {r[:65]}")
        results.append((model_id, custom_model, region, r))
        time.sleep(5)

    # Summary
    print(f"\n{'='*80}")
    passed = sum(1 for r in results if is_pass(r[-1]))
    failed = sum(1 for r in results if not is_pass(r[-1]))
    print(f"PASSED: {passed}  FAILED: {failed}  TOTAL: {len(results)}")

    if failed > 0:
        print(f"\nFailed tests:")
        for r in results:
            if not is_pass(r[-1]):
                print(f"  {r[0]} ({r[1]}, {r[2]}): {r[-1][:100]}")

    return results


def test_regions(session):
    """Test non-profile models across all regions they're available in.

    Uses model-availability.json (generated by build-availability-map.py)
    to know which models are deployed in which regions.
    """
    avail_path = os.path.join(os.path.dirname(__file__), 'model-availability.json')
    if not os.path.exists(avail_path):
        print("ERROR: model-availability.json not found.")
        print("Run: python3 build-availability-map.py")
        sys.exit(1)

    with open(avail_path) as f:
        avail = json.load(f)

    bedrock = load_catalog()
    # Get non-profile models (no inference_profile_geos)
    no_profile = [m['name'] for m in bedrock['models'] if not m.get('inference_profile_geos')]
    # Get profile models too — they should also be tested in their regions
    profile_models = [m['name'] for m in bedrock['models'] if m.get('inference_profile_geos')]

    all_models = avail['models']

    # Build test cases: every model+region combo from the availability map
    test_cases = []
    for model_id, regions in sorted(all_models.items()):
        for region in regions:
            test_cases.append((model_id, region))

    print(f"Testing {len(test_cases)} model+region combinations ({len(all_models)} models, {len(avail['regions_scanned'])} regions)...\n")
    print(f"  {'Model':<55} {'Region':<18} Result")
    print(f"  {'-'*55} {'-'*18} {'-'*40}")

    results = []
    for model_id, region in test_cases:
        print(f"  {model_id:<55} {region:<18} ", end="", flush=True)
        r = test_model(session, model_id, region=region)
        status = "PASS" if is_pass(r) else "FAIL"
        short = r[:60]
        print(f"{status}: {short}")
        results.append((model_id, region, r))
        time.sleep(5)

    # Summary
    print(f"\n{'='*80}")
    passed = sum(1 for r in results if is_pass(r[-1]))
    failed = sum(1 for r in results if not is_pass(r[-1]))
    print(f"PASSED: {passed}  FAILED: {failed}  TOTAL: {len(results)}")

    if failed > 0:
        print(f"\nFailed tests:")
        for model_id, region, r in results:
            if not is_pass(r):
                print(f"  {model_id} ({region}): {r[:200]}")

    return results


def test_profiles_all(session):
    """Test every inference-profile model from every Bedrock-enabled region.

    Unlike PROFILES (which tests 2 regions per geo), this tests all 21
    profile models × all 16 regions = 336 combinations.  Verifies that
    our geo routing (us./eu./apac./jp./au./ca./global. fallback) works
    from every region.
    """
    avail_path = os.path.join(os.path.dirname(__file__), 'model-availability.json')
    if not os.path.exists(avail_path):
        print("ERROR: model-availability.json not found.")
        print("Run: python3 build-availability-map.py")
        sys.exit(1)

    with open(avail_path) as f:
        avail = json.load(f)

    bedrock = load_catalog()
    profile_models = [m['name'] for m in bedrock['models'] if m.get('inference_profile_geos')]
    regions = avail['regions_scanned']

    test_cases = [(m, r) for m in sorted(profile_models) for r in regions]

    print(f"Testing {len(profile_models)} inference-profile models × {len(regions)} regions = {len(test_cases)} combinations...\n")
    print(f"  {'Model':<55} {'Region':<18} Result")
    print(f"  {'-'*55} {'-'*18} {'-'*40}")

    results = []
    for model_id, region in test_cases:
        print(f"  {model_id:<55} {region:<18} ", end="", flush=True)
        r = test_model(session, model_id, region=region)
        status = "PASS" if is_pass(r) else "FAIL"
        short = r[:60]
        print(f"{status}: {short}")
        results.append((model_id, region, r))
        time.sleep(5)

    # Summary
    print(f"\n{'='*80}")
    passed = sum(1 for r in results if is_pass(r[-1]))
    failed = sum(1 for r in results if not is_pass(r[-1]))
    print(f"PASSED: {passed}  FAILED: {failed}  TOTAL: {len(results)}")

    if failed > 0:
        print(f"\nFailed tests:")
        for model_id, region, r in results:
            if not is_pass(r):
                print(f"  {model_id} ({region}): {r[:200]}")

    return results


if __name__ == "__main__":
    model_arg = sys.argv[1] if len(sys.argv) > 1 else "amazon.nova-micro-v1:0"
    region_arg = sys.argv[2] if len(sys.argv) > 2 else "us-east-1"
    timeout_arg = int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_TIMEOUT

    print("Logging in...")
    session = login()
    print("Logged in.\n")

    if model_arg == "ALL":
        test_all(session)
    elif model_arg == "PROFILES":
        test_profiles(session)
    elif model_arg == "PROFILES_ALL":
        test_profiles_all(session)
    elif model_arg == "REGIONS":
        test_regions(session)
    else:
        print(f"Testing: {model_arg} (region: {region_arg}, timeout: {timeout_arg}s)")
        result = test_model(session, model_arg, region=region_arg, timeout=timeout_arg)
        print(f"\n{result}")
