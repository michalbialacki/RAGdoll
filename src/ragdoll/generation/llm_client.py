"""Claude Haiku generation via Bedrock, called through a cross-region inference profile.

Claude models on Bedrock require invoking via an inference profile ID/ARN, not the
bare model ID — `anthropic.claude-haiku-4-5-20251001-v1:0` alone is rejected by
InvokeModel for this model. The IAM policy granting bedrock:InvokeModel must target
the inference profile ARN too (Phase 05 concern), not just the underlying model ARN.

Same bedrock-runtime client as dense_embedding.py — one AWS service, different
modelId/body shape per call, no separate client needed.
"""

import asyncio
import json
from typing import Any

INFERENCE_PROFILE_ID = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"
ANTHROPIC_VERSION = "bedrock-2023-05-31"
MAX_TOKENS = 1024


def _invoke_sync(client: Any, system_prompt: str, user_prompt: str) -> str:
    body = json.dumps(
        {
            "anthropic_version": ANTHROPIC_VERSION,
            "max_tokens": MAX_TOKENS,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
    )
    response = client.invoke_model(modelId=INFERENCE_PROFILE_ID, body=body)
    payload = json.loads(response["body"].read())
    text: str = payload["content"][0]["text"]
    return text


async def generate_answer(bedrock_client: Any, system_prompt: str, user_prompt: str) -> str:
    """Async wrapper — boto3 invoke_model is sync, offload to a thread like dense_embedding does."""
    return await asyncio.to_thread(_invoke_sync, bedrock_client, system_prompt, user_prompt)
