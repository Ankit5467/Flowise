#!/bin/bash
# Test a single Bedrock model via the Flowise AgentFlow API
# Usage: ./test-models.sh [model-id]
# Default: amazon.nova-micro-v1:0 (cheapest/fastest)

MODEL="${1:-amazon.nova-micro-v1:0}"
FLOWISE_URL="http://localhost:3000"
PROMPT="Reply with exactly one sentence: what is your model name?"

echo "=== Testing model: $MODEL ==="

# Step 1: Create a temporary agentflow with the specified model
FLOW_JSON=$(cat <<ENDJSON
{
  "name": "test-${MODEL}",
  "type": "AGENTFLOW",
  "flowData": "{\"nodes\":[{\"id\":\"startAgentflow_0\",\"type\":\"agentFlow\",\"position\":{\"x\":0,\"y\":0},\"data\":{\"id\":\"startAgentflow_0\",\"label\":\"Start\",\"version\":1.1,\"name\":\"startAgentflow\",\"type\":\"Start\",\"color\":\"#7EE787\",\"hideInput\":true,\"baseClasses\":[\"Start\"],\"category\":\"Agent Flows\",\"description\":\"Starting point of the agentflow\",\"inputParams\":[{\"label\":\"Input Type\",\"name\":\"startInputType\",\"type\":\"options\",\"options\":[{\"label\":\"Chat Input\",\"name\":\"chatInput\"}],\"default\":\"chatInput\",\"id\":\"startAgentflow_0-input-startInputType-options\",\"display\":true},{\"label\":\"Ephemeral Memory\",\"name\":\"startEphemeralMemory\",\"type\":\"boolean\",\"optional\":true,\"id\":\"startAgentflow_0-input-startEphemeralMemory-boolean\",\"display\":true}],\"inputAnchors\":[],\"inputs\":{\"startInputType\":\"chatInput\",\"startEphemeralMemory\":true},\"outputAnchors\":[{\"id\":\"startAgentflow_0-output-startAgentflow\",\"label\":\"Start\",\"name\":\"startAgentflow\"}],\"outputs\":{}}},{\"id\":\"agentAgentflow_0\",\"type\":\"agentFlow\",\"position\":{\"x\":200,\"y\":0},\"data\":{\"id\":\"agentAgentflow_0\",\"label\":\"Agent 0\",\"version\":3.2,\"name\":\"agentAgentflow\",\"type\":\"Agent\",\"color\":\"#4DD0E1\",\"baseClasses\":[\"Agent\"],\"category\":\"Agent Flows\",\"description\":\"Agent\",\"inputParams\":[{\"label\":\"Model\",\"name\":\"agentModel\",\"type\":\"asyncOptions\",\"loadMethod\":\"listModels\",\"loadConfig\":true,\"id\":\"agentAgentflow_0-input-agentModel-asyncOptions\",\"display\":true}],\"inputAnchors\":[],\"inputs\":{\"agentModel\":\"awsChatBedrock\",\"agentMessages\":\"\",\"agentTools\":\"\",\"agentKnowledgeDocumentStores\":\"\",\"agentKnowledgeVSEmbeddings\":\"\",\"agentEnableMemory\":false,\"agentMemoryType\":\"allMessages\",\"agentUserMessage\":\"\",\"agentReturnResponseAs\":\"userMessage\",\"agentStructuredOutput\":\"\",\"agentUpdateState\":\"\",\"agentModelConfig\":{\"cache\":\"\",\"region\":\"us-east-1\",\"model\":\"${MODEL}\",\"customModel\":\"\",\"endpointHost\":\"\",\"streaming\":true,\"temperature\":0.7,\"max_tokens_to_sample\":200,\"allowImageUploads\":\"\",\"latencyOptimized\":\"\",\"agentModel\":\"awsChatBedrock\"}},\"outputAnchors\":[{\"id\":\"agentAgentflow_0-output-agentAgentflow\",\"label\":\"Agent\",\"name\":\"agentAgentflow\"}],\"outputs\":{}}},{\"id\":\"directReplyAgentflow_0\",\"type\":\"agentFlow\",\"position\":{\"x\":400,\"y\":0},\"data\":{\"id\":\"directReplyAgentflow_0\",\"label\":\"Direct Reply 0\",\"version\":1,\"name\":\"directReplyAgentflow\",\"type\":\"DirectReply\",\"color\":\"#4DDBBB\",\"hideOutput\":true,\"baseClasses\":[\"DirectReply\"],\"category\":\"Agent Flows\",\"description\":\"Direct reply\",\"inputParams\":[{\"label\":\"Message\",\"name\":\"directReplyMessage\",\"type\":\"string\",\"rows\":4,\"acceptVariable\":true,\"id\":\"directReplyAgentflow_0-input-directReplyMessage-string\",\"display\":true}],\"inputAnchors\":[],\"inputs\":{\"directReplyMessage\":\"<p><span class=\\\"variable\\\" data-type=\\\"mention\\\" data-id=\\\"agentAgentflow_0\\\" data-label=\\\"agentAgentflow_0\\\">{{ agentAgentflow_0 }}</span> </p>\"},\"outputAnchors\":[],\"outputs\":{}}}],\"edges\":[{\"source\":\"startAgentflow_0\",\"sourceHandle\":\"startAgentflow_0-output-startAgentflow\",\"target\":\"agentAgentflow_0\",\"targetHandle\":\"agentAgentflow_0\",\"data\":{\"sourceColor\":\"#7EE787\",\"targetColor\":\"#4DD0E1\",\"isHumanInput\":false},\"type\":\"agentFlow\",\"id\":\"e1\"},{\"source\":\"agentAgentflow_0\",\"sourceHandle\":\"agentAgentflow_0-output-agentAgentflow\",\"target\":\"directReplyAgentflow_0\",\"targetHandle\":\"directReplyAgentflow_0\",\"data\":{\"sourceColor\":\"#4DD0E1\",\"targetColor\":\"#4DDBBB\",\"isHumanInput\":false},\"type\":\"agentFlow\",\"id\":\"e2\"}]}"
}
ENDJSON
)

# Create the flow
echo "Creating test flow..."
FLOW_RESPONSE=$(curl -s -X POST "$FLOWISE_URL/api/v1/chatflows" \
  -H "Content-Type: application/json" \
  -d "$FLOW_JSON")

FLOW_ID=$(echo "$FLOW_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null)

if [ -z "$FLOW_ID" ]; then
  echo "ERROR: Failed to create flow"
  echo "$FLOW_RESPONSE"
  exit 1
fi
echo "Flow created: $FLOW_ID"

# Send a test message
echo "Sending prompt: '$PROMPT'"
PRED_RESPONSE=$(curl -s -X POST "$FLOWISE_URL/api/v1/internal-prediction/$FLOW_ID" \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"$PROMPT\"}")

# Extract the response text
ANSWER=$(echo "$PRED_RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'text' in data:
    print(data['text'][:200])
elif 'message' in data:
    print('ERROR:', data['message'][:200])
else:
    print(json.dumps(data)[:200])
" 2>/dev/null)

echo ""
echo "Response: $ANSWER"
echo ""

# Clean up: delete the test flow
curl -s -X DELETE "$FLOWISE_URL/api/v1/chatflows/$FLOW_ID" > /dev/null
echo "Test flow deleted."
echo "=== Done ==="
