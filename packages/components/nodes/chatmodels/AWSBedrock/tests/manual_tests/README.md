# Manual Test Suite — AWS Bedrock Integration

33 test cases covering built-in models, legacy models, imported models, fine-tuned models, cross-region routing, stopSequences, streaming, image uploads, tool calling, and error handling.

## Prerequisites

-   Flowise running: `pnpm dev` (UI on localhost:8080, API on localhost:3000)
-   AWS credentials configured: `export AWS_PROFILE=[your aws cli profile]`
-   Imported models in Bedrock (for Section 5): SantaCoder-1B, Qwen2.5-Coder-0.5B, Qwen3-0.6B

**Before running:** The test JSON files contain placeholder AWS account IDs and model ARNs. Replace them with your own:

-   Search for `123456789000` (placeholder account ID) and replace with your AWS account ID
-   For imported/custom model tests (Sections 5, 6, 11): update the `customModel` ARN in `agentModelConfig` to match your actual imported or deployed model ARN

## How to Test

For each test case:

1. Import the JSON: Flowise UI → Agent Flows → Upload/Import → select the `.json` file
2. Send the prompt listed below in the chat panel
3. Verify the expected result
4. Delete the flow when done (to keep things clean)

**Important:** After importing, always clear chat history (eraser icon) before sending a prompt.

**Prompt for all tests** (unless noted otherwise):

> What is 2+2? Reply in one sentence.

---

## Section 1: Built-in Models (Various Providers)

Tests that built-in models from the dropdown work in us-east-1.

| #   | File                                       | Model                | Expected Result                                                    |
| --- | ------------------------------------------ | -------------------- | ------------------------------------------------------------------ |
| 01  | `01-builtin-nova-micro-us-east-1.json`     | Amazon Nova Micro    | Response renders. Fast (~1-2s).                                    |
| 02  | `02-builtin-claude-haiku-us-east-1.json`   | Claude Haiku 4.5     | Response renders. Identifies as Claude/Anthropic.                  |
| 03  | `03-builtin-claude-sonnet-us-east-1.json`  | Claude Sonnet 4.6    | Response renders. Higher quality than Haiku.                       |
| 04  | `04-builtin-llama4-scout-us-east-1.json`   | Llama 4 Scout 17B    | Response renders. May identify as Meta/Llama.                      |
| 05  | `05-builtin-deepseek-r1-us-east-1.json`    | DeepSeek R1          | Response renders. No stopSequences error. May show `<think>` tags. |
| 06  | `06-builtin-mistral-large3-us-east-1.json` | Mistral Large 3 675B | Response renders. May be slow (~5-10s).                            |

**What to verify:**

-   Response appears in the chat panel
-   No error messages
-   Streaming tokens visible (text appears word by word)

---

## Section 2: Legacy Models

Tests that legacy (deprecated) models still work and display correctly.

| #   | File                                        | Model                     | Expected Result                                                             |
| --- | ------------------------------------------- | ------------------------- | --------------------------------------------------------------------------- |
| 07  | `07-legacy-claude3-haiku-us-east-1.json`    | Claude 3 Haiku (Legacy)   | Response renders OR Bedrock returns deprecation error. Both are acceptable. |
| 08  | `08-legacy-llama32-1b-us-east-1.json`       | Llama 3.2 1B (Legacy)     | Same — response or deprecation error.                                       |
| 09  | `09-legacy-cohere-command-r-us-east-1.json` | Cohere Command R (Legacy) | Same — response or deprecation error.                                       |

**What to verify:**

-   Dropdown shows model with `(Legacy)` suffix
-   Flow imports successfully (no crash)
-   If model still works: response renders normally
-   If model is deprecated: error message appears in chat (NOT a blank/broken UI)

---

## Section 3: Cross-Region (Inference Profiles)

Tests that models work in non-US regions via automatic inference profile routing.

| #   | File                                          | Model             | Region                  | Profile Expected                                                    |
| --- | --------------------------------------------- | ----------------- | ----------------------- | ------------------------------------------------------------------- |
| 10  | `10-region-nova-micro-eu-west-1.json`         | Nova Micro        | eu-west-1               | `eu.amazon.nova-micro-v1:0`                                         |
| 11  | `11-region-claude-haiku-ap-northeast-1.json`  | Claude Haiku 4.5  | ap-northeast-1 (Tokyo)  | `jp.anthropic.claude-haiku-4-5-20251001-v1:0`                       |
| 12  | `12-region-claude-sonnet-ap-southeast-2.json` | Claude Sonnet 4.6 | ap-southeast-2 (Sydney) | `au.anthropic.claude-sonnet-4-6`                                    |
| 13  | `13-region-nova-lite-ca-central-1.json`       | Nova Lite         | ca-central-1 (Canada)   | `ca.amazon.nova-lite-v1:0`                                          |
| 14  | `14-region-claude-haiku-sa-east-1.json`       | Claude Haiku 4.5  | sa-east-1 (São Paulo)   | `global.anthropic.claude-haiku-4-5-20251001-v1:0` (global fallback) |

**What to verify:**

-   Response renders — model works in that region
-   No "inference profile required" or "invalid model" error
-   Check Flowise server logs for profile auto-application (look for `[AWSBedrock]` log lines)

---

## Section 4: StopSequences Models

Tests that models with `stop_sequences: false` don't produce stopSequences errors.

| #   | File                                    | Model              | Expected Result                                             |
| --- | --------------------------------------- | ------------------ | ----------------------------------------------------------- |
| 15  | `15-stopseq-deepseek-v3-us-east-1.json` | DeepSeek V3.2      | Response renders. No "doesn't support stopSequences" error. |
| 16  | `16-stopseq-gpt-oss-20b-us-east-1.json` | OpenAI GPT-OSS 20B | Response renders. No stopSequences error.                   |

**What to verify:**

-   Response appears (content may be terse for small prompts)
-   No error mentioning "stopSequences" or "unsupported field"

---

## Section 5: Imported Models (Custom Model ARN)

Tests that imported model ARNs in the "Custom Model ARN" field auto-route to InvokeModel.

**Note:** These tests require the imported models to exist in your Bedrock account. If models are cold (not invoked recently), the first request may take 30-60s to warm up or return "model not ready" — wait and retry.

| #   | File                                      | Imported Model     | Architecture | Expected Result                                                                     |
| --- | ----------------------------------------- | ------------------ | ------------ | ----------------------------------------------------------------------------------- |
| 17  | `17-imported-santacoder-us-east-1.json`   | SantaCoder 1B      | GPTBigCode   | Response renders (code completion, may be terse). Uses `bedrock-completion` format. |
| 18  | `18-imported-qwen25-coder-us-east-1.json` | Qwen2.5 Coder 0.5B | Qwen2.5      | Response renders. Uses `openai-chat-completion` format.                             |
| 19  | `19-imported-qwen3-us-east-1.json`        | Qwen3 0.6B         | Qwen3        | Response renders. May include `<think>` tags. Uses `openai-chat-completion` format. |

**What to verify:**

-   Open agent config → "Custom Model ARN" shows the imported model ARN
-   Response renders in the chat panel
-   Check server logs for `[AWSBedrockImported]` or format probe messages
-   If "model not ready": wait 60s and retry

**To verify with different imported models:** Edit the JSON file and replace the `customModel` ARN value in `agentModelConfig`, or manually change it in the Flowise UI after importing.

---

## Section 6: Streaming Off

Tests non-streaming mode for both built-in and imported models.

| #   | File                                         | Model                           | Expected Result                                    |
| --- | -------------------------------------------- | ------------------------------- | -------------------------------------------------- |
| 20  | `20-no-stream-nova-micro-us-east-1.json`     | Nova Micro (no stream)          | Response appears all at once (not token by token). |
| 21  | `21-no-stream-imported-qwen3-us-east-1.json` | Qwen3 0.6B imported (no stream) | Response appears all at once.                      |

**What to verify:**

-   Response appears as a single block, not streamed word by word
-   No errors

---

## Section 7: Error Cases

Tests that invalid inputs produce clear, actionable error messages — not blank screens or crashes.

| #   | File                                            | What's Wrong                                                                                | Expected Error                                                                                         |
| --- | ----------------------------------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| 22  | `22-error-invalid-custom-model-name.json`       | `customModel = "SantaCoder-1B"` (not an ARN)                                                | `"SantaCoder-1B" is not a valid ARN. The "Custom Model ARN" field requires a full Bedrock ARN...`      |
| 23  | `23-error-nonexistent-imported-arn.json`        | `customModel = arn:...:imported-model/nonexistent999`                                       | Bedrock validation error: model identifier failed to satisfy constraint (invalid format or not found). |
| 24  | `24-error-geo-prefix-in-custom-model.json`      | `customModel = "us.anthropic.claude-haiku-4-5-20251001-v1:0"` (geo prefix, not ARN)         | `"us.anthropic..." is not a valid ARN...`                                                              |
| 25  | `25-error-deleted-imported-model.json`          | `customModel = arn:...:imported-model/aaaaaaaaaaaa` (valid ARN format, model doesn't exist) | Bedrock error: model not found / ResourceNotFoundException.                                            |
| 26  | `26-inference-profile-arn-in-custom-model.json` | `customModel = arn:...:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0`       | Response renders. Inference profile ARN used as-is via Converse API.                                   |
| 27  | `27-foundation-model-arn-in-custom-model.json`  | `customModel = arn:...:foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0`           | Bedrock error — foundation model ARN is not a valid inference profile. Use the dropdown instead.       |

**What to verify:**

-   Error message appears in the chat panel (not a blank/broken UI)
-   Error message is actionable — tells the user what to do
-   Flowise does not crash

---

## Section 8: Streaming Verification

Verifies that streaming tokens appear incrementally in the UI.

| #   | File                               | Model                           | Expected Result                                                |
| --- | ---------------------------------- | ------------------------------- | -------------------------------------------------------------- |
| 28  | `28-streaming-builtin-claude.json` | Claude Haiku 4.5 (streaming on) | Tokens appear word by word in the chat panel, not all at once. |

**What to verify:**

-   Watch the chat panel as the response generates
-   Text should appear incrementally (streaming), not as a single block
-   Compare with Section 6 (streaming off) to confirm the difference

---

## Section 9: Image Uploads

Tests that image input works for multimodal models. Requires uploading an image in the chat panel.

| #   | File                                    | Model                                 | Expected Result                                                                                                                 |
| --- | --------------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| 29  | `29-image-upload-claude.json`           | Claude Haiku 4.5 (images enabled)     | Upload a small image (PNG/JPG) via the chat attachment button. Ask "What is in this image?" Response should describe the image. |
| 30  | `30-image-upload-imported-qwen2vl.json` | Qwen2-VL 2B imported (images enabled) | Same — upload image, ask about it. Requires Qwen2-VL imported in Bedrock. Update ARN if needed.                                 |

**What to verify:**

-   Image attachment button appears in the chat input area
-   After uploading an image and sending a prompt, the model responds with a description
-   No "remote URL" errors — only base64 data URLs are supported for imported models

**Note:** Test 30 requires `Qwen2-VL-2B-Instruct` imported in your Bedrock account. Update the `customModel` ARN in the JSON if your model ARN differs.

---

## Section 10: Tool Calling

Tests that the model can invoke tools (Calculator) and return computed results.

**Prompt for tool tests:**

> What is 1847 multiplied by 293? Use the calculator tool.

| #   | File                                     | Model                         | Expected Result                                                                                                         |
| --- | ---------------------------------------- | ----------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| 31  | `31-tool-calling-calculator-claude.json` | Claude Haiku 4.5 + Calculator | Response includes the correct answer (541,171). Model should invoke the Calculator tool and return the computed result. |
| 32  | `32-tool-calling-calculator-nova.json`   | Nova Micro + Calculator       | Same — correct multiplication result via tool call.                                                                     |

**What to verify:**

-   Response contains the correct numerical answer (541,171)
-   The model used the Calculator tool (check "Process Flow" expandable in the chat for tool invocation steps)
-   No "tool not found" or "tool_calls not supported" errors

---

## Section 11: Fine-Tuned Models (Custom Model ARN)

Tests that fine-tuned model deployment ARNs in the "Custom Model ARN" field work via the Converse API. Unlike imported models (Section 5), these ARNs skip the format probe and route directly to Converse as an `applicationInferenceProfile`.

**Which ARN to use:**

-   `arn:...:custom-model-deployment/<id>` — **on-demand inference** (pay-per-token, for Nova Lite/Micro/Pro, Nova 2 Lite, Llama 3.3 70B in us-east-1/us-west-2). This is the common default.
-   `arn:...:provisioned-model/<id>` — **Provisioned Throughput** (committed capacity). Also works.
-   `arn:...:custom-model/<id>` — just the trained artifact. **Not directly invocable.** Don't use this.

**Note:** Requires a deployed custom model in your Bedrock account. Replace the placeholder deployment ID in the JSON with your actual deployment identifier. Find it via:

```bash
aws bedrock list-custom-model-deployments --region us-east-1
```

| #   | File                                 | Model                  | Expected Result                                                                                    |
| --- | ------------------------------------ | ---------------------- | -------------------------------------------------------------------------------------------------- |
| 33  | `33-custom-finetuned-us-east-1.json` | Fine-tuned (on-demand) | Response renders. No format probe in logs (Converse path). Model behaves per its fine-tuning data. |

**What to verify:**

-   Open agent config → "Custom Model ARN" shows the deployment ARN (`arn:...:custom-model-deployment/...`)
-   Response renders in the chat panel
-   Check server logs — no `[AWSBedrockImported]` messages (this is the Converse path, not InvokeModel)
-   If deployment is not `ACTIVE` or was deleted: expect a clear Bedrock error surfaced via `normalizeBedrockError()`

---

## Quick Reference: Updating Imported Model ARNs

If you import different models, update the ARNs in the Section 5 and 6 JSON files:

```bash
# List your current imported models
aws bedrock list-imported-models --region us-east-1

# Then edit the JSON files — change the "customModel" value in agentModelConfig
```

## Quick Reference: Test All Sections via API (automated)

If you prefer automated testing over manual UI testing:

```bash
TESTS=packages/components/nodes/chatmodels/AWSBedrock/tests

# Built-in models + routing + errors
python3 $TESTS/test-custom-model-routing.py

# Imported models (dynamic — tests whatever is currently imported)
python3 $TESTS/test-imported-models.py

# Pricing validation
python3 $TESTS/test-pricing.py

# All unit tests
cd packages/components && npx jest nodes/chatmodels/AWSBedrock/ --no-cache

# Playwright E2E (everything except 63-model invocation)
npx playwright test --config=$TESTS/playwright.config.ts --grep-invert "Invoke all Bedrock" --reporter=list,html
```
