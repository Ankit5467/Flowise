# Bedrock Component Maintenance Guide

## Context

The Bedrock integration depends on external data that changes over time: new models are released, old models are deprecated, pricing changes, and inference profile availability shifts. This guide covers how to keep `models.json` and the component up to date.

All commands assume you're in the `Flowise/` root directory. For brevity:

```bash
TESTS=packages/components/nodes/chatmodels/AWSBedrock/tests
```

## 1. Adding New Models

**When:** AWS announces new foundation models on Bedrock.

**Steps:**

```bash
# Check what's currently available vs what's in our catalog
aws bedrock list-foundation-models --region us-east-1 --query 'modelSummaries[?modelLifecycle.status==`ACTIVE`].[modelId,modelName,providerName]' --output table

# Compare against models.json
python3 -c "
import json
with open('packages/components/models.json') as f:
    d = json.load(f)
bedrock = next(c for c in d['chat'] if c['name'] == 'awsChatBedrock')
print(set(m['name'] for m in bedrock['models']))
"
```

For each new model, add an entry to models.json under `awsChatBedrock.models`:

-   `label`, `name`, `description`
-   `input_cost`, `output_cost` (from aws.amazon.com/bedrock/pricing/)
-   `inference_profile_geos` (run `aws bedrock list-inference-profiles --region us-east-1` and check which `geo.modelId` profiles exist)
-   `stop_sequences: false` if the model rejects stopSequences (test by invoking with stopSequences — if it errors, add the flag)

Then run:

```bash
cd packages/components && npx jest nodes/chatmodels/AWSBedrock/AWSBedrockCatalog.test.ts
```

## 2. Handling Deprecated Models

**When:** A model's `modelLifecycle.status` changes to `LEGACY`.

**Steps:**

```bash
# Check lifecycle status
aws bedrock get-foundation-model --model-identifier <model-id> --query 'modelDetails.modelLifecycle.status'
```

If `LEGACY`:

1. Add `(Legacy)` to the model's `label` in models.json
2. Set `description` to `"<Model Name> - Legacy"`
3. Do NOT remove the model — keep it for backward compatibility
4. Add `inference_profile_geos` if the model requires profiles (check via `list-inference-profiles`)

## 3. Updating Inference Profile Availability

**When:** AWS adds new inference profiles or removes old ones in certain regions.

**Steps:**

```bash
# Scan profiles across regions for a specific model
python3 -c "
import subprocess, json
regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'eu-central-1', 'ap-northeast-1', 'ap-southeast-2', 'ap-south-1', 'sa-east-1']
model = 'anthropic.claude-sonnet-4-6'  # change this
for region in regions:
    profiles = []
    r = subprocess.run(['aws', 'bedrock', 'list-inference-profiles', '--type-equals', 'SYSTEM_DEFINED', '--region', region, '--max-results', '100', '--output', 'json'], capture_output=True, text=True, timeout=30)
    for p in json.loads(r.stdout).get('inferenceProfileSummaries', []):
        if model in p['inferenceProfileId']:
            print(f'{region}: {p[\"inferenceProfileId\"]}')
"
```

Update the model's `inference_profile_geos` array in models.json accordingly.

**Note:** Runtime discovery (`discoverInferenceProfiles()`) handles this automatically at invocation time — models.json geos are a hint, not enforcement. But keeping them accurate improves the static fallback path.

## 5. Full Validation After Changes

```bash
# Unit tests (from packages/components/)
cd packages/components
npx jest nodes/chatmodels/AWSBedrock/ --no-cache

# API tests (requires Flowise running)
python3 $TESTS/test-custom-model-routing.py
python3 $TESTS/test-imported-models.py

# Playwright E2E
npx playwright test --config=$TESTS/playwright.config.ts --grep-invert "Invoke all Bedrock" --reporter=list,html
```

## 6. Scripts Reference

| Script                                | Purpose                                | When to Run                        |
| ------------------------------------- | -------------------------------------- | ---------------------------------- |
| `$TESTS/build-availability-map.py`    | Discover model availability per region | After new model launches           |
| `$TESTS/test-model.py ALL`            | Invoke all 72 models                   | After model catalog changes        |
| `$TESTS/test-custom-model-routing.py` | Full routing test                      | After any AWSChatBedrock.ts change |
| `$TESTS/test-imported-models.py`      | Test imported models                   | After imported model changes       |

## 7. Files to Know

| File                                                                               | What It Contains                                                      |
| ---------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `packages/components/models.json`                                                  | Model catalog: IDs, inference_profile_geos, stop_sequences flags      |
| `packages/components/nodes/chatmodels/AWSBedrock/AWSChatBedrock.ts`                | Node definition, init() with all routing logic                        |
| `packages/components/nodes/chatmodels/AWSBedrock/utils.ts`                         | resolveBedrockModel, discoverInferenceProfiles, normalizeBedrockError |
| `packages/components/nodes/chatmodels/AWSBedrock/FlowiseAWSChatBedrock.ts`         | Converse API wrapper (stopSeq stripping, error normalization)         |
| `packages/components/nodes/chatmodels/AWSBedrock/FlowiseAWSChatBedrockImported.ts` | InvokeModel API wrapper (format probe, imported model support)        |
| `packages/components/src/modelLoader.ts`                                           | getModels(), getRegions()                                             |
| `packages/components/evaluation/EvaluationRunner.ts`                               | Cost calculation for evaluations                                      |
