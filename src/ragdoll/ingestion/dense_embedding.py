"""Dense embeddings via AWS Bedrock Titan Embeddings V2.

Titan V2's InvokeModel takes exactly one `inputText` per call — there is no
batch endpoint. Concurrency across chunks happens on our side.
"""
import asyncio
import json
import random
from typing import Any

MODEL_ID = "amazon.titan-embed-text-v2:0"
DIMENSIONS = 1024


def _embed_one_sync(client: Any, text: str) -> list[float]:
    """Single synchronous Bedrock call for one chunk of text."""
    body = json.dumps({"inputText": text, "dimensions": DIMENSIONS, "normalize": True})
    response = client.invoke_model(modelId=MODEL_ID, body=body)
    payload = json.loads(response["body"].read())
    embedding: list[float] = payload["embedding"]
    return embedding

async def worker(
    client: Any, texts: list[str], item_id: int, semaphore: asyncio.Semaphore
) -> list[float]:
    """Embed one chunk, retrying on failure with exponential backoff + jitter.

    Re-raises the last exception if all 5 attempts fail.
    """
    async with semaphore:
        exception: Exception | None = None
        for attempt in range(5):
            base_delay = 2**attempt
            jitter_range = 1
            try:
                return await asyncio.to_thread(_embed_one_sync, client, texts[item_id])
            except Exception as e:
                exception = e
                delay = base_delay + random.uniform(0, jitter_range)
                await asyncio.sleep(delay)
        assert exception is not None
        raise exception


async def embed_texts(client: Any, texts: list[str], max_concurrency: int = 5) -> list[list[float]]:
    """Embed multiple chunks concurrently without blocking the event loop."""
    semaphore = asyncio.Semaphore(max_concurrency)
    thread_tasks = [worker(client, texts, item_id, semaphore) for item_id in range(len(texts))]
    return await asyncio.gather(*thread_tasks)