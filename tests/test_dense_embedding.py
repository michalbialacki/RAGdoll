import json
from unittest.mock import MagicMock
import asyncio

import pytest

from ragdoll.ingestion.dense_embedding import embed_texts

# NOTE: worker() sleeps between retries (exponential backoff + jitter). Left
# un-patched, the exhaustion test below would take ~30s real time (2^0..2^4).
# We patch asyncio.sleep so retries are instant — we're testing the retry
# *logic*, not real timing.


def _mock_response(embedding: list[float]) -> MagicMock:
    body = MagicMock()
    body.read.return_value = json.dumps({"embedding": embedding}).encode()
    response = {"body": body}
    return response


async def test_embed_texts_retries_then_succeeds(monkeypatch):
    async def mock_sleep(delay=None):
        return None

    monkeypatch.setattr(asyncio, "sleep", mock_sleep)

    client = MagicMock()
    client.invoke_model.side_effect = [
        Exception("throttled"),
        _mock_response([0.1, 0.2, 0.3]),
    ]

    result = await embed_texts(client, ["ragdoll_chunks"])

    assert result == [[0.1, 0.2, 0.3]]
    assert client.invoke_model.call_count == 2


async def test_embed_texts_raises_after_five_attempts(monkeypatch):
    async def mock_sleep(delay=None):
        return None

    monkeypatch.setattr(asyncio, "sleep", mock_sleep)

    client = MagicMock()
    client.invoke_model.side_effect = Exception("throttled")

    with pytest.raises(Exception, match="throttled"):
        await embed_texts(client, ["ragdoll_chunks"])

    assert client.invoke_model.call_count == 5
