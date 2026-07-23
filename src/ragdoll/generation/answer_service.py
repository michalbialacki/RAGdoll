"""Orchestrates context-gate → prompt build → LLM call for the /query endpoint."""

from typing import Any

from qdrant_client.models import ScoredPoint

from ragdoll.generation.llm_client import generate_answer
from ragdoll.generation.prompt_builder import SYSTEM_PROMPT, build_prompt, has_sufficient_context

NO_CONTEXT_ANSWER = "I don't have enough information in the knowledge base to answer this question."


async def answer_query(bedrock_client: Any, query_text: str, points: list[ScoredPoint]) -> str:
    if not has_sufficient_context(points):
        return NO_CONTEXT_ANSWER
    prompt = build_prompt(query_text, points)
    return await generate_answer(bedrock_client, SYSTEM_PROMPT, prompt)
