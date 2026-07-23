"""Unit tests for the Bedrock Claude Haiku call (Phase 03 Step 01/03).

bedrock_client.invoke_model is mocked — we're verifying we call it with the right
inference profile ID and request shape, and parse the Anthropic-on-Bedrock response
shape correctly, not that AWS actually responds.
"""

import io
import json
from unittest.mock import MagicMock

import pytest

from ragdoll.generation.llm_client import INFERENCE_PROFILE_ID, generate_answer


def _mock_response(text: str) -> dict:
    body = json.dumps({"content": [{"type": "text", "text": text}]}).encode()
    return {"body": io.BytesIO(body)}


@pytest.mark.asyncio
async def test_generate_answer_calls_inference_profile_with_system_and_user_prompt():
    client = MagicMock()
    client.invoke_model.return_value = _mock_response("the answer")

    result = await generate_answer(client, "system instructions", "user question")

    assert result == "the answer"
    client.invoke_model.assert_called_once()
    _, kwargs = client.invoke_model.call_args
    assert kwargs["modelId"] == INFERENCE_PROFILE_ID

    body = json.loads(kwargs["body"])
    assert body["system"] == "system instructions"
    assert body["messages"] == [{"role": "user", "content": "user question"}]
    assert body["anthropic_version"] == "bedrock-2023-05-31"
