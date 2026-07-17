import json
from unittest.mock import MagicMock

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
    # TODO:
    # 1. patch asyncio.sleep so the test doesn't actually wait:
    #    monkeypatch.setattr("asyncio.sleep", ...) — needs to be an async
    #    no-op callable, since `worker` does `await asyncio.sleep(delay)`
    # 2. build a mock client whose `invoke_model` raises an exception on the
    #    first call, then returns _mock_response([0.1, 0.2, ...]) on the
    #    second — use `side_effect=[Exception("throttled"), _mock_response(...)]`
    # 3. call `await embed_texts(client, ["some text"])`
    # 4. assert the result is the embedding from the *successful* call, and
    #    that invoke_model was called exactly twice (proves it retried once,
    #    not zero times and not more)
    raise NotImplementedError


async def test_embed_texts_raises_after_five_attempts(monkeypatch):
    # TODO:
    # 1. patch asyncio.sleep the same way as above
    # 2. build a mock client whose invoke_model always raises
    #    (side_effect=Exception("throttled") — no list, so every call raises)
    # 3. assert `embed_texts` re-raises (pytest.raises) instead of swallowing
    #    the error or returning a partial/None result
    # 4. assert invoke_model was called exactly 5 times (proves it doesn't
    #    retry forever, and doesn't give up early)
    raise NotImplementedError
