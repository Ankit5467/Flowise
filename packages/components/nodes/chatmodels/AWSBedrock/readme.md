# Implementation Notes

## Change Summary

### Imported/Custom Model Support

-   Built `FlowiseAWSChatBedrockImported.ts` — core class with InvokeModel API, OpenAIChatCompletion + BedrockCompletion formats
-   Format auto-detection via probe at init time (parses supported formats from ValidationException)
-   Auto-detection in Converse node — imported model ARNs in "Custom Model ARN" auto-route to InvokeModel
-   Consolidated to single node — one `awsChatBedrock` handles all model types (built-in, imported, fine-tuned, provisioned)
-   ARN validation — Custom Model ARN requires `arn:aws:bedrock:...`; rejects non-ARN values with actionable errors
-   Tested with 6 imported models across 4 architectures (Llama, Qwen2.5, Qwen3, Qwen2-VL, GPTBigCode)

### Legacy Model Handling

-   Added 9 legacy models back to models.json with `(Legacy)` label
-   Added `inference_profile_geos` to 7 legacy models (verified via API scan across 11 regions)
-   Backward compatibility — saved flows referencing legacy models show in dropdown instead of blank

### UI Fixes

-   **Renamed "Custom Model Name" → "Custom Model ARN"** — field only accepts ARNs, name should reflect that
-   Node card label — shows custom model ARN (stripped prefix) when customModel is set
-   Node description — "Supports built-in, imported, fine-tuned, and provisioned-throughput models"
-   Placeholder — shows imported-model ARN example
-   Model Name field — removed required indicator (`*`)
-   Error messages guide users to the "Model Name" dropdown for built-in models instead of suggesting ARN entry

### User Guidance: Dropdown vs Custom Model ARN

-   **Built-in models:** Always use the "Model Name" dropdown + "Region" dropdown. Inference profiles are auto-applied based on the selected model and region. No need to touch the "Custom Model ARN" field.
-   **Custom Model ARN field:** Only for imported, fine-tuned, or provisioned-throughput models that aren't in the dropdown. Requires a full `arn:aws:bedrock:...` ARN.
-   **Inference profile ARNs:** Can be entered in Custom Model ARN if the user has a specific profile not auto-discovered. But for standard use, the dropdown + region handles this automatically.

### Error Handling

-   Stopped swallowing errors in `getImportedModelInfo()` — real Bedrock errors propagate to UI
-   Updated `normalizeBedrockError()` — removed references to deleted imported node and invalid customModel suggestions

### ARN Types in Custom Model ARN Field

| ARN Type                     | Example                                                    | Behavior                                                                                                                                                                                                                                                                       |
| ---------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Imported model               | `arn:...:imported-model/xyz`                               | Auto-detected → InvokeModel API (if `instructSupported: false`) or Converse API (if `true`)                                                                                                                                                                                    |
| Custom model deployment      | `arn:...:custom-model-deployment/xyz`                      | Passed to Converse API as `applicationInferenceProfile`. Use this ARN for on-demand inference of fine-tuned models                                                                                                                                                             |
| Provisioned throughput       | `arn:...:provisioned-model/xyz`                            | Passed to Converse API as `applicationInferenceProfile`. Use this ARN for fine-tuned models with committed PT capacity                                                                                                                                                         |
| Custom (fine-tuned artifact) | `arn:...:custom-model/xyz`                                 | **Not invokable.** This ARN is just a pointer to the trained artifact — Bedrock will reject it. Deploy the model first with `CreateCustomModelDeployment` or `CreateProvisionedModelThroughput`, then use the resulting `custom-model-deployment/` or `provisioned-model/` ARN |
| Inference profile            | `arn:...:inference-profile/us.anthropic.claude-sonnet-4-6` | Works — passed to Converse API as `applicationInferenceProfile`                                                                                                                                                                                                                |
| Foundation model             | `arn:...:foundation-model/anthropic.claude-sonnet-4-6`     | Fails — foundation model ARN is not a valid inference profile. Bedrock returns "inference profile required" error with guidance to try a different region or provide an inference profile ARN                                                                                  |
| Non-ARN                      | `SantaCoder-1B`, `us.anthropic.claude-sonnet-4-6`          | Rejected at validation — "not a valid ARN, use the dropdown instead"                                                                                                                                                                                                           |

### Global Inference Endpoint Override

-   New `useGlobalEndpoint` boolean field — forces `global.*` inference profile instead of regional

### Test Coverage

-   153 jest unit tests, 9 Playwright specs, 5 Python API scripts, 33 manual test JSONs
-   Manual tests include: streaming verification, image uploads (built-in + imported multimodal), tool calling (Calculator with Claude + Nova)
-   Playwright tests include: streaming UI rendering, token usage metadata check, Calculator tool invocation E2E

---

## models.json Changes

All changes validated against `aws bedrock list-foundation-models` API.

### Removed: non-chat model

-   `twelvelabs.pegasus-1-2-v1:0` -- video understanding model, not a text chat model. Converse API rejects it.

### Legacy models — kept in catalog with "(Legacy)" label

These models have `modelLifecycle.status: LEGACY` per the AWS API. They are kept in models.json rather than removed, for two reasons:

1. **Backward compatibility.** Existing saved flows store the model ID in their JSON. If we remove the model from the catalog, the dropdown shows blank when a user opens the flow config — it looks like the model selection was lost. Keeping it in the catalog means the dropdown still shows the model name.
2. **Let Bedrock decide.** Legacy models may still be callable. If AWS fully deprecates them, the Converse API will return an error, and our `normalizeBedrockError()` will surface it. The catalog shouldn't enforce what the API doesn't.

**UI treatment:** Label includes `(Legacy)` suffix, description is `"Legacy"`. Users can still select these models for new flows if they want.

Legacy models (9):

-   `amazon.nova-premier-v1:0` — Nova Premier
-   `anthropic.claude-3-haiku-20240307-v1:0` — Claude 3 Haiku
-   `anthropic.claude-3-5-haiku-20241022-v1:0` — Claude 3.5 Haiku
-   `cohere.command-r-v1:0` — Command R
-   `cohere.command-r-plus-v1:0` — Command R+
-   `meta.llama3-2-1b-instruct-v1:0` — Llama 3.2 1B
-   `meta.llama3-2-3b-instruct-v1:0` — Llama 3.2 3B
-   `meta.llama3-2-11b-instruct-v1:0` — Llama 3.2 11B
-   `meta.llama3-2-90b-instruct-v1:0` — Llama 3.2 90B

### Removed: stale/wrong IDs (not returned by AWS API)

-   `deepseek.v3-v1:0`
-   `meta.llama3-1-405b-instruct-v1:0`
-   `mistral.mistral-large-2407-v1:0`
-   `nvidia.nemotron-3-super-120b-a12b` (wrong ID, replaced with correct one below)
-   `qwen.qwen3-235b-a22b-2507-v1:0`
-   `qwen.qwen3-coder-480b-a35b-v1:0`

### Fixed model ID

-   `nvidia.nemotron-3-super-120b-a12b` → `nvidia.nemotron-super-3-120b` (correct ID per AWS API)

### Added: ACTIVE models missing from catalog

-   `writer.palmyra-vision-7b` -- $0.15/1M input, $0.60/1M output (pricing from AWS Bedrock pricing page)
-   `minimax.minimax-m2.5` -- $0.30/1M input, $1.20/1M output
-   `zai.glm-5` -- $1.00/1M input, $3.20/1M output

### Other

-   Default model in `AWSChatBedrock.ts` changed from `anthropic.claude-3-haiku-20240307-v1:0` (removed) to `anthropic.claude-haiku-4-5-20251001-v1:0`

---

## Test Scripts

All scripts are in `packages/components/nodes/chatmodels/AWSBedrock/tests/`. Requires `pip install requests boto3` and Flowise running on localhost:3000.

All commands below assume you're in the `Flowise/` root directory. For brevity, set:

```bash
TESTS=packages/components/nodes/chatmodels/AWSBedrock/tests
```

### Quick Reference — API Tests

```bash
# Run from Flowise/ directory with Flowise running (pnpm dev)

python3 $TESTS/test-imported-models.py                # all imported models (dynamic)
python3 $TESTS/test-custom-model-routing.py           # full routing decision tree (9 sections)
python3 $TESTS/test-model.py ALL                      # all 72 built-in models in us-east-1
python3 $TESTS/test-model-switch.py                   # model switching verification
```

### `test-model.py` -- Test models and inference profiles

```bash
python3 $TESTS/test-model.py                                        # test Nova Micro in us-east-1
python3 $TESTS/test-model.py "amazon.nova-2-lite-v1:0"              # test specific model in us-east-1
python3 $TESTS/test-model.py "amazon.nova-pro-v1:0" eu-west-1       # test specific model in EU region
python3 $TESTS/test-model.py ALL                                    # test all models in us-east-1
python3 $TESTS/test-model.py PROFILES                               # test inference profiles across us/eu/apac geos
```

-   `ALL`: creates a temp agentflow for each model, sends a prompt, prints the response, deletes the flow.
-   `PROFILES`: for each model with `inference_profile_geos` in models.json, tests with a region from each supported geo (us-east-1, eu-west-1, ap-southeast-1). Also tests explicit profile IDs via the customModel field.

### `test-model-switch.py` -- Verify model switching works

```bash
python3 $TESTS/test-model-switch.py
```

Creates a flow with Claude Haiku 4.5, asks "who is your maker?", updates the flow to Nova Micro, asks again, and compares. Confirms the model actually changes by checking if response A mentions Anthropic and response B mentions Amazon.

### `test-imported-models.py` -- Test all imported models (dynamic)

```bash
python3 $TESTS/test-imported-models.py                              # test all currently imported models
python3 $TESTS/test-imported-models.py arn:aws:bedrock:...:imported-model/xyz   # test specific ARN
```

Dynamically fetches all imported models from Bedrock (`ListImportedModels`), creates a Converse node flow with each ARN in `customModel`, sends a prompt. Includes retry logic for cold-start warmup (up to 5 retries, 30s/60s/90s backoff).

### `test-custom-model-routing.py` -- Full routing decision tree

```bash
python3 $TESTS/test-custom-model-routing.py
```

Tests every branch of the custom model routing in `AWSChatBedrock.ts init()`:

1. Imported model ARNs via `customModel` (dynamic, all imported models)
2. Built-in model baseline (Nova Micro, no customModel)
3. Inference profile override (`us.claude-haiku`)
4. Streaming disabled (both imported and built-in)
5. StopSequences model (DeepSeek R1)
6. Cross-region (eu-west-1)
7. Nonexistent imported ARN (error handling)

### Playwright E2E Tests (UI)

9 test files:

-   `e2e/01-login.spec.ts` (3) — login page, valid/invalid credentials
-   `e2e/02-create-agentflow.spec.ts` (4) — create flow, canvas rendering, node config, save
-   `e2e/03-model-selection.spec.ts` (3) — dropdown count, key models, no legacy models
-   `e2e/04-invoke-all-models.spec.ts` (63) — invoke every built-in model via UI chat
-   `e2e/05-model-switch.spec.ts` (2) — switch model, verify response changes
-   `e2e/06-custom-model-field.spec.ts` (3) — field descriptions, ARN input
-   `e2e/07-region-selection.spec.ts` (7) — us/eu/tokyo/sydney/canada/sa regions
-   `e2e/08-error-handling.spec.ts` (3) — DeepSeek/OpenAI stopSeq, chat UI response
-   `e2e/09-custom-model-routing.spec.ts` (13) — imported model auto-detection (API + UI), built-in baseline (API + UI), DeepSeek stopSeq, eu-west-1 region, error cases (nonexistent ARN, non-ARN, foundation-model ARN), inference profile ARN, streaming UI, token usage metadata, Calculator tool calling

**Prerequisites:** Flowise running (`pnpm dev`), AWS credentials configured.
**Important:** Use `workers: 1` (already in config) — parallel workers cause SQLite lock errors.
**Auth:** Each test logs in via the `authedPage` fixture (browser session). API calls use `authedPage.request` to inherit browser cookies.

### Credentials

All test scripts read from `$TESTS/test-config.json`:

```json
{
    "email": "your email here",
    "password": "your password",
    "apiBase": "http://localhost:3000",
    "uiBase": "http://localhost:8080"
}
```

This file is in `.gitignore` — credentials are not committed. To change credentials, edit `test-config.json`.

---

## Model Catalog & Inference Profiles Summary

All built-in Bedrock models work across all AWS regions with automatic inference profile routing.

All 63 built-in models invoked successfully through the UI across all supported regions.

---

## Imported Model Support Summary

Imported models are supported through the **same AWS Bedrock node** — no separate node needed. Users paste an imported model ARN in "Custom Model ARN" and it auto-detects the correct API.

### What Was Built

-   **Auto-detection in `AWSChatBedrock.ts init()`** — detects `:imported-model/` ARNs, calls `GetImportedModel` to check `instructSupported`, probes `InvokeModel` for supported formats, routes to `BedrockImportedChat` (InvokeModel API) when Converse is not supported.
-   **`FlowiseAWSChatBedrockImported.ts`** — core class extending `BaseChatModel` with InvokeModel/InvokeModelWithResponseStream, supports both OpenAI ChatCompletion and BedrockCompletion formats, format auto-detected via probe.
-   **Format probe** — sends `{}` to InvokeModel at init time to discover supported formats from the ValidationException error message. Also detects "prompt must be provided" for models without chat templates.

### Files Modified/Created

| File                               | What                                                                             |
| ---------------------------------- | -------------------------------------------------------------------------------- |
| `AWSChatBedrock.ts`                | Imported model auto-detection in `init()`, updated customModel description       |
| `FlowiseAWSChatBedrockImported.ts` | **New** — core class (InvokeModel, format probe, streaming, error normalization) |
| `AWSChatBedrockImported.test.ts`   | **New** — 30 unit tests for core class                                           |
| `AWSChatBedrock.test.ts`           | Added 24 routing decision tree tests                                             |
| `EvaluationRunTracer.ts`           | `bedrock-imported` → `awsChatBedrock` provider mapping                           |
| `test-imported-models.py`          | **New** — dynamic API tests for all imported models                              |
| `test-custom-model-routing.py`     | **New** — full routing decision tree API tests                                   |
| `09-custom-model-routing.spec.ts`  | **New** — 13 Playwright E2E tests                                                |

### Models Tested (6 pass)

| Model                 | Architecture | Params | Result                         |
| --------------------- | ------------ | ------ | ------------------------------ |
| TinyLlama 1.1B        | Llama        | 1.1B   | PASS                           |
| Qwen2.5 0.5B Instruct | Qwen2.5      | 0.5B   | PASS                           |
| Qwen3 0.6B            | Qwen3        | 0.6B   | PASS                           |
| Qwen2.5 Coder 0.5B    | Qwen2.5      | 0.5B   | PASS                           |
| Qwen2-VL 2B Instruct  | Qwen2-VL     | 2B     | PASS                           |
| SantaCoder 1B         | GPTBigCode   | 1B     | PASS (needed format probe fix) |

### Imported Model Test Coverage

-   **30 jest unit tests** for imported model core class + 24 routing decision tree tests
-   **13 Playwright E2E tests** for custom model routing (imported, built-in, errors, streaming, tool calling, usage metadata)
-   **2 Python API test scripts** (test-imported-models.py, test-custom-model-routing.py)

### Design Decision: Single Node

Originally built as a separate `awsChatBedrockImported` node. Consolidated into the existing `awsChatBedrock` node with auto-detection. User doesn't need to know which API their model uses — just paste the ARN. The separate node definition was deleted; the core class remains as an internal implementation detail.

---

## Imported Model Compatibility Analysis

### Single Node Architecture

One node (`awsChatBedrock`) handles all Bedrock model types:

-   **Built-in models** → "Model Name" dropdown → Converse API
-   **Custom models** (imported, fine-tuned, provisioned) → "Custom Model ARN" field (ARN required) → auto-detects API

### Custom Model ARN Routing

Accepts only `arn:aws:bedrock:...` ARNs. Routing based on ARN pattern:

| ARN Type                                                  | Route                            |
| --------------------------------------------------------- | -------------------------------- |
| `arn:...:imported-model/...` + `instructSupported: false` | InvokeModel (format auto-probed) |
| `arn:...:imported-model/...` + `instructSupported: true`  | Converse API                     |
| `arn:...:provisioned-model/...`                           | Converse API                     |
| `arn:...:custom-model/...`                                | Converse API                     |
| Anything not starting with `arn:aws:bedrock:`             | ValidationError                  |

### Bedrock InvokeModel Request Formats (per AWS docs)

| Format                   | Request                                        | Response                            | Our Support                              |
| ------------------------ | ---------------------------------------------- | ----------------------------------- | ---------------------------------------- |
| **BedrockCompletion**    | `{ prompt, max_gen_len, temperature }`         | `{ generation, stop_reason }`       | Implemented (`bedrock-completion`)       |
| **OpenAICompletion**     | `{ prompt, max_tokens, temperature }`          | `{ choices: [{ text }], usage }`    | Not implemented (not needed — see below) |
| **OpenAIChatCompletion** | `{ messages: [...], max_tokens, temperature }` | `{ choices: [{ message }], usage }` | Implemented (`openai-chat-completion`)   |

OpenAICompletion (#2) is not implemented. Verified empirically (2026-04-21): models that support OpenAICompletion always also support a format we handle. No model requires it exclusively:

-   **SantaCoder (GPTBigCode)**: only BedrockCompletion (`max_gen_len` → `generation`). Rejects `max_tokens`.
-   **Qwen2.5-Coder**: supports OpenAICompletion (`max_tokens` → `choices[0].text`) AND ChatCompletion. We use ChatCompletion.
-   **TinyLlama**: supports BedrockMetaCompletion AND ChatCompletion. We use ChatCompletion.

### Format Auto-Detection (Probe)

At init time, sends `{}` to InvokeModel — the ValidationException lists supported formats:

-   `"Available for this model: ChatCompletionRequest, BedrockMetaCompletionRequest, ..."` → parse and pick best
-   `"prompt must be provided"` → model has no chat template, use `bedrock-completion`
-   Prefer `ChatCompletionRequest` when available (structured messages, tool_calls, token usage)

### Compatibility by Architecture

| Architecture          | Converse Support               | InvokeModel Formats                                                             | Tested?                          |
| --------------------- | ------------------------------ | ------------------------------------------------------------------------------- | -------------------------------- |
| Llama (2/3/3.x)       | Depends on `instructSupported` | ChatCompletion, BedrockMetaCompletion, Completion                               | Yes (TinyLlama 1.1B)             |
| Qwen2 / Qwen2.5       | No (must use InvokeModel)      | ChatCompletion, OpenAICompletion                                                | Yes (Qwen2.5 0.5B, Coder 0.5B)   |
| Qwen3                 | No (must use InvokeModel)      | ChatCompletion                                                                  | Yes (Qwen3 0.6B)                 |
| Qwen2-VL / Qwen2.5-VL | No (must use InvokeModel)      | ChatCompletion (with image support)                                             | Yes (Qwen2-VL 2B)                |
| GPTBigCode            | Depends on `instructSupported` | BedrockCompletion only (`max_gen_len`). Rejects `max_tokens`. No chat template. | Yes (SantaCoder 1B)              |
| Mistral               | Depends on `instructSupported` | ChatCompletion, BedrockCompletion                                               | Not tested (smallest is 7B)      |
| Mixtral               | Depends on `instructSupported` | ChatCompletion, BedrockCompletion                                               | Not tested (smallest is 47B)     |
| Mllama                | Depends on `instructSupported` | ChatCompletion (with image support)                                             | Not tested                       |
| GPT-OSS               | No (must use InvokeModel)      | ChatCompletion (with tool_calls)                                                | Not tested (not user-importable) |

### Edge Cases Handled

-   **Models without chat templates** (e.g. SantaCoder): probe detects → falls back to `bedrock-completion`
-   **Cold start / ModelNotReady**: test scripts retry up to 5 times with backoff (30s/60s/90s)
-   **Multimodal image input**: base64 data URLs only, remote URLs rejected with clear error
-   **Tool calling**: parsed from OpenAIChatCompletion response if present (GPT-OSS only)

### Conclusion

Works with **all currently importable architectures**: Llama, Mistral, Mixtral, Qwen2/2.5/3, Qwen2-VL/2.5-VL, GPTBigCode, Mllama, GPT-OSS. Format probe eliminates hardcoded assumptions. Verified with 6 real models across 4 architectures.

---

## Inference Profile Geo Routing

### What

Auto-applies the correct geo-prefixed inference profile (us., eu., apac., jp., au., ca., global.) based on the user's selected AWS region. Verified against `aws bedrock list-inference-profiles` across 15+ regions.

### How

-   `models.json`: Each model with inference profiles has `inference_profile_geos` array (e.g., `["us", "eu", "jp", "au", "global"]`). Single source of truth.
-   `utils.ts` → `regionToGeoCandidates(region)`: Maps region to ordered candidate list. Country-specific prefixes tried first:
    -   `ap-northeast-1/3` → `[jp, apac]` (Tokyo/Osaka)
    -   `ap-southeast-2` → `[au, apac]` (Sydney)
    -   `ca-*` → `[ca, us]` (Canada)
    -   `sa-*` → `[]` (South America — global fallback only)
-   `utils.ts` → `resolveBedrockModel()`: Iterates candidates, first match against model's geos wins. Then tries `global`, then `us`. Zero API calls — purely in-memory lookup.
-   `GEO_PREFIX_RE` recognizes: `us`, `eu`, `apac`, `jp`, `au`, `ca`, `global`

### Test coverage: 66 unit tests

Covers all region types (US, EU, APAC, Tokyo, Osaka, Sydney, Canada, South America, unknown) with both auto-apply and fallback scenarios.

---

## Runtime Inference Profile Discovery

### Problem

Our static `inference_profile_geos` in models.json says `eu.amazon.nova-pro-v1:0` exists. Our code applied it for all `eu-*` regions. But `eu.` profiles don't exist in every `eu-*` region — eu-west-2 has the model deployed for direct on-demand invocation but doesn't have the `eu.` inference profile. Sending `eu.amazon.nova-pro-v1:0` to eu-west-2 returns "invalid model identifier."

### Root cause

Inference profile availability is **per-region**, not per-geo. `eu.` ≠ "all EU regions." The static geos in models.json were too coarse.

### Fix

Added runtime discovery: on first use of a region, call `ListInferenceProfiles` (Bedrock control-plane API) to get the exact set of profiles available in that region. Only apply a profile that's confirmed to exist.

### Implementation

-   **`utils.ts` → `discoverInferenceProfiles(region, credentials)`** — Calls `@aws-sdk/client-bedrock` `ListInferenceProfilesCommand` with pagination, caches result in-memory per region (process lifetime). Uses the same credentials the user configured (UI creds, AssumeRole, or SDK default chain). On error returns empty set (falls back to direct invocation).
-   **`resolveBedrockModel()` new parameter `availableProfiles`** — When provided, only applies a profile confirmed to exist in the region. Fallback chain: preferred geo → global → us → none → skip profile (direct invocation). When `undefined` (no runtime data), trusts models.json geos (backward compat for tests).
-   **`AWSChatBedrock.ts` `init()`** — Credentials resolved first, then `discoverInferenceProfiles()`, then `resolveBedrockModel()` with the discovered set.
-   **Pagination bug fix** — Bedrock returns ~13 profiles per page despite `maxResults: 100`. Added `do/while` pagination loop on `nextToken`.

### Dependencies

-   Added `@aws-sdk/client-bedrock: 3.966.0` to `packages/components/package.json` (control-plane client for `ListInferenceProfiles`)

### Custom Model ARN field

Updated description to: "For imported, fine-tuned, or provisioned-throughput models." Accepts any model ARN. Imported models (`arn:...:imported-model/...`) are auto-detected and routed to InvokeModel API instead of Converse.

### Test script changes

-   `test-model.py` timeout: 60s → 120s (for slow models like NVIDIA Nemotron)
-   `test-model.py` delay: 1s → 2s (avoid Bedrock throttling)
-   Error message output: truncation increased from 100 to 200 chars
-   New mode `PROFILES_ALL`: 21 profile models × 16 regions = 336 combinations
-   New mode `REGIONS`: 63 models × available regions = 544 combinations
-   New script `build-availability-map.py`: discovers model availability per region

### Unit tests: 163 passing (as of 2026-04-24)

Includes runtime discovery, imported model routing, format probe, stopSequences stripping, error normalization, global endpoint override.

---

## Models Without Guaranteed Regional Capacity

Some models are listed as ACTIVE by `list-foundation-models` in non-US regions but have no guaranteed inference capacity there. Requests time out (10+ minutes, no error returned) because Bedrock has insufficient or no pre-provisioned capacity for these large/niche models outside major US regions.

**Affected models and regions (observed timeouts):**

-   `nvidia.nemotron-super-3-120b` — times out in: eu-west-1, eu-central-1, eu-north-1, ap-northeast-1, ap-south-1, ap-southeast-2, sa-east-1. Works in: us-east-1, us-west-2.
-   `nvidia.nemotron-nano-9b-v2` — times out in: ap-southeast-2
-   `nvidia.nemotron-nano-12b-v2` — times out in: ap-southeast-2
-   `minimax.minimax-m2.1` — times out in: eu-north-1
-   `minimax.minimax-m2.5` — times out in: eu-north-1
-   `moonshot.kimi-k2-thinking` — times out in: sa-east-1
-   `zai.glm-4.7` — times out in: sa-east-1

**Not a Flowise bug.** These are capacity limitations — the model is "available" per the API but lacks inference capacity in that region. Nothing we can fix in code.

---

## Model Deprecation Lifecycle

AWS/Anthropic are actively deprecating older models. Observed:

-   `anthropic.claude-3-haiku-20240307-v1:0` — Legacy since 2026-03-10, EOL 2026-09-10
-   `anthropic.claude-sonnet-4-20250514-v1:0` — Legacy since 2026-04-14, EOL 2026-10-14

### Current approach: keep legacy models in catalog

Legacy models are **not removed** from models.json. Instead they are labeled with `(Legacy)` in the dropdown and `"Legacy"` in the description. Rationale:

-   **Backward compatibility:** Saved flows store the model ID. Removing from the catalog makes the dropdown show blank when editing — confusing for users.
-   **Let Bedrock decide:** The model may still be callable during its deprecation window. If AWS fully deprecates it, the Converse API returns an error and `normalizeBedrockError()` surfaces it. The catalog shouldn't preempt the API.
-   **No fabricated migration guidance:** We don't tell users which model to switch to — that depends on their use case.

### When a model becomes legacy

1. Run `aws bedrock get-foundation-model --model-identifier <id> --query 'modelDetails.modelLifecycle.status'`
2. If `LEGACY`: add `(Legacy)` to the label in models.json, set description to `"Legacy"`
3. Do NOT remove the model from the catalog

### Long-term automation (not implemented)

A CI job or startup check that calls `list-foundation-models`, detects status changes to LEGACY, and auto-appends `(Legacy)` to labels. Not needed for the prototype but would reduce manual maintenance.

---

## Architectural Rationale

### Why models.json is the single source of truth

`inference_profile_geos` and `stop_sequences` flags are in models.json. Code reads from it via the model loader (`modelLoader.ts`). This means the same data works when Flowise loads models from the upstream remote GitHub catalog in production. No hardcoded maps in code that could diverge.

### Why runtime discovery over static geo maps

eu-west-2 has Nova models deployed for direct on-demand invocation but does NOT have `eu.` inference profiles. The static `inference_profile_geos` in models.json says `eu` exists — which is true, but not in every `eu-*` region. Profile availability is per-region, not per-geo. Runtime `ListInferenceProfiles` call (cached per region) gives the exact set.

### Why exact model IDs for stop_sequences (not prefix matching)

Originally used prefix matching (`deepseek.`, `openai.gpt-oss`). Changed because a future DeepSeek model might support stopSequences — prefix matching would silently strip them with no error. Exact model IDs from models.json are explicit and safe.

### Why resolveBedrockModel() is async

Loads model catalog via model loader on first call (cached). Originally sync with a hardcoded `MODELS_REQUIRING_PROFILE` map. Changed to async when we moved inference profile data and stop_sequences flags to models.json.

### Why credential-first init flow

`AWSChatBedrock.ts` `init()` resolves AWS credentials BEFORE model resolution so `discoverInferenceProfiles()` can reuse the same creds. Previous order was model resolution first, credentials after — but that meant the profile discovery had no credentials to call the Bedrock API with.

### Why authedPage.request for API calls in Playwright

Flowise auth uses HttpOnly cookies (`token`, `refreshToken`, `connect.sid`). Playwright's standalone `request` fixture creates a separate HTTP client that doesn't share the browser's cookies. `authedPage.request` inherits the browser's cookie jar — same as how a real user's browser makes API calls.

### Why temperature uses try/retry instead of a models.json flag

Some models (e.g., Claude Opus 4.7) reject the `temperature` parameter with "temperature is deprecated." We handle this with a try/retry approach in `FlowiseAWSChatBedrock.ts` rather than a per-model flag:

1. **No API to query supported parameters.** Bedrock's `GetFoundationModel` doesn't expose which inference config fields a model supports. We'd have to maintain the list manually.
2. **UI can't conditionally disable fields.** Flowise's form renderer doesn't support disabling an input field based on the currently selected dropdown value. The temperature field is always visible regardless of model — a flag in models.json would silently ignore the value with no visual feedback, which is worse UX than a fast retry.
3. **Minimal latency.** The "temperature deprecated" error is a validation failure returned instantly — no inference cost. The retry (without temperature) adds ~1s on the first call only. Subsequent calls use the cached state.

The approach: `_generate()` and `_streamResponseChunks()` catch the error, set `temperature = undefined`, and retry. The fix persists for the lifetime of the BedrockChat instance.

---

## Dependencies Added

-   `@aws-sdk/client-bedrock: 3.966.0` in `packages/components/package.json` — Bedrock control plane client for `ListInferenceProfilesCommand`. The `client-bedrock-runtime` (already a dep) only has runtime APIs, not the control plane.
-   `@playwright/test@1.42.1` in root `package.json` — must match existing `playwright@1.42.1` from components package. Version 1.49.1 causes "two different versions of @playwright/test" error in pnpm monorepo due to hoisting.

---

## Flowise UI Gotchas

-   **Save agent config**: Close the config modal, then Ctrl+S or click the save (floppy disk) button. Changes to model/region/parameters do NOT persist without explicit save.
-   **Clear chat history when switching models**: Conversation memory causes the new model to see the old model's "I was made by Anthropic" response and repeat it. Must click eraser icon to clear.
-   **Rebuild after code changes**: `pnpm --filter flowise-components build` required after modifying `.ts` files in packages/components. `pnpm dev` hot-reloads UI code but NOT the compiled server-side component JS.
-   **SQLite locking under load**: Heavy concurrent API calls (e.g., running all E2E tests with multiple workers) causes `SQLITE_BUSY: database is locked`. Fix: restart server, use `workers: 1` in Playwright config.
-   **"The provided model identifier is invalid"**: This means the selected model is not available in the selected region. Either switch to a region where the model is deployed, or choose a different model that is available in the current region. Not all models are available in all regions — check `aws bedrock list-foundation-models --region <region>` to see what's available.

---

## Test Script Additional Modes

| Mode                      | Command                                                   | Tests | ~Time   |
| ------------------------- | --------------------------------------------------------- | ----- | ------- |
| Single model              | `python3 $TESTS/test-model.py <model> [region] [timeout]` | 1     | ~20s    |
| All models (us-east-1)    | `python3 $TESTS/test-model.py ALL`                        | 63    | ~5 min  |
| Profiles (2 regions/geo)  | `python3 $TESTS/test-model.py PROFILES`                   | ~120  | ~10 min |
| Profiles (all 16 regions) | `python3 $TESTS/test-model.py PROFILES_ALL`               | 336   | ~28 min |
| All regions               | `python3 $TESTS/test-model.py REGIONS`                    | 544   | ~45 min |

-   Configurable timeout: 3rd argument in seconds (e.g., `python3 $TESTS/test-model.py nvidia.nemotron-super-3-120b us-east-1 600`)
-   `KNOWN_CAPACITY_ISSUES` dict: annotates expected timeouts with helpful message
-   Latency printed per invocation: `3s - OK: I'm an AI system created by Amazon.`
-   Auto session refresh: `refresh_if_needed()` re-logins when Flowise JWT expires during long runs
-   Delay between tests: 5 seconds (prevents Bedrock throttling and SQLite locking)

### Playwright

Run from `Flowise/` directory. Requires Flowise running (`pnpm dev`).

```bash
# All tests except built-in model invocations (~8 min)
npx playwright test --config=$TESTS/playwright.config.ts --grep-invert "Invoke all Bedrock" --reporter=list

# All tests including 63 built-in models (~35 min)
npx playwright test --config=$TESTS/playwright.config.ts --reporter=list

# Specific spec file
npx playwright test --config=$TESTS/playwright.config.ts --grep "Custom model routing" --reporter=list

# Watch in browser (skip built-in models)
npx playwright test --config=$TESTS/playwright.config.ts --grep-invert "Invoke all Bedrock" --headed --reporter=list,html

# HTML report with screenshots after a run
npx playwright show-report

# run playwright tests with and generate html report
npx playwright test --config=$TESTS/playwright.config.ts --headed --reporter=list,html

```

### Test Layer Summary

| Test Type              | What it validates                                                                                        | Speed       | Cost       | Catches                                                      |
| ---------------------- | -------------------------------------------------------------------------------------------------------- | ----------- | ---------- | ------------------------------------------------------------ |
| Unit tests (jest)      | Pure logic: resolveBedrockModel(), validateEndpointHost(), stopSequences, format detection, routing tree | <1s each    | Free       | Logic bugs, regressions when code changes                    |
| API tests (Python)     | Full backend: does Flowise + Bedrock actually invoke the model and return a response?                    | 5-120s each | Real AWS $ | Integration bugs, inference profile routing, credential flow |
| E2E tests (Playwright) | Full UI: can a user log in, create a flow, chat, get a response, switch models, use tools?               | 20-30s each | Real AWS $ | UI rendering, form behavior, chat panel, streaming           |
| Manual tests (JSON)    | Edge cases: image uploads, legacy models, error messages, ARN types, cross-region                        | Manual      | Real AWS $ | UX issues, visual regressions                                |

Why unit tests matter even though we have API/E2E:

1. **Speed** — 163 tests run in 25 seconds. Run after every code change. API tests take 45 minutes and cost money.
2. **Precision** — If resolveBedrockModel() breaks, the unit test tells you exactly which function, input, and geo prefix failed.
3. **No dependencies** — Work offline, without Flowise running, without AWS credentials.
4. **Edge cases** — Cover scenarios hard to trigger end-to-end: model loader failure, empty profile cache, ARN migration, South America fallback.
5. **PR gate** — These should run in CI on every PR. API/Playwright tests are too slow and expensive for that.
