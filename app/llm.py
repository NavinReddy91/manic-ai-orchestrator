"""
LLM provider abstraction. Supports multiple backends via environment config:
  - anthropic  (Claude)
  - openai     (GPT-4o, etc.)
  - groq       (Llama, Mixtral — fast, cheap)
  - gemini     (Google Gemini)
  - openrouter (any model via OpenRouter)

Set LLM_PROVIDER in .env to choose. Each provider uses its own API format.
All providers expose the same call_llm() interface.
"""

import json
import logging
import httpx
from .config import settings
from .web_tools import search_web, fetch_page_text

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------


async def _call_anthropic(system: str, user_message: str, max_tokens: int) -> str:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.llm_api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.llm_model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user_message}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        text_blocks = [
            b["text"] for b in data.get("content", []) if b.get("type") == "text"
        ]
        return "\n".join(text_blocks)


async def _call_openai_compatible(
    system: str, user_message: str, max_tokens: int, base_url: str
) -> str:
    """Works for OpenAI, Groq, OpenRouter, and any OpenAI-compatible API."""
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.llm_model,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_message},
                ],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def _call_openai(system: str, user_message: str, max_tokens: int) -> str:
    return await _call_openai_compatible(
        system, user_message, max_tokens, "https://api.openai.com/v1"
    )


async def _call_groq(system: str, user_message: str, max_tokens: int) -> str:
    return await _call_openai_compatible(
        system, user_message, max_tokens, "https://api.groq.com/openai/v1"
    )


async def _call_openrouter(system: str, user_message: str, max_tokens: int) -> str:
    return await _call_openai_compatible(
        system, user_message, max_tokens, "https://openrouter.ai/api/v1"
    )


async def _call_gemini(system: str, user_message: str, max_tokens: int) -> str:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.llm_model}:generateContent",
            params={"key": settings.llm_api_key},
            headers={"Content-Type": "application/json"},
            json={
                "system_instruction": {"parts": [{"text": system}]},
                "contents": [{"parts": [{"text": user_message}]}],
                "generationConfig": {"maxOutputTokens": max_tokens},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


_PROVIDERS = {
    "anthropic": _call_anthropic,
    "openai": _call_openai,
    "groq": _call_groq,
    "gemini": _call_gemini,
    "openrouter": _call_openrouter,
}


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


async def call_llm(system: str, user_message: str, max_tokens: int = 2000) -> str:
    """
    Call the configured LLM provider. Set LLM_PROVIDER and LLM_API_KEY in .env.
    """
    provider = settings.llm_provider.lower()
    if provider not in _PROVIDERS:
        raise ValueError(
            f"Unknown LLM provider: {provider}. Choose from: {list(_PROVIDERS.keys())}"
        )

    logger.info(f"Calling LLM: provider={provider}, model={settings.llm_model}")
    return await _PROVIDERS[provider](system, user_message, max_tokens)


async def call_llm_with_browsing(
    system: str, user_message: str, max_rounds: int = 3
) -> str:
    """
    Agentic loop: the model can request web search or page fetch by putting
    SEARCH: or FETCH: as the first line of its reply. Runs up to max_rounds
    iterations, then forces a final answer.
    """
    browsing_instructions = (
        "\n\nYou have live web access. To use it, put ONE of these as the very "
        "first line of your reply and nothing else on that line:\n"
        "SEARCH: <query>\n"
        "FETCH: <url>\n"
        "You'll get real results back and can search/fetch again, or give your "
        "final answer once you have enough — in the exact format your "
        "instructions specify (which may be plain text or strict JSON). Don't "
        "say SEARCH or FETCH once you're ready to give that final answer."
    )
    system_with_tools = system + browsing_instructions
    transcript = user_message

    for _ in range(max_rounds):
        reply = await call_llm(system_with_tools, transcript)
        first_line = reply.strip().split("\n", 1)[0].strip()

        if first_line.upper().startswith("SEARCH:"):
            query = first_line.split(":", 1)[1].strip()
            results = await search_web(query)
            results_text = (
                "\n".join(
                    f"- {r['title']} ({r['url']}): {r['snippet']}" for r in results
                )
                or "No results."
            )
            transcript += f"\n\n[SEARCH: {query}]\n{results_text}\n\nNow continue — search/fetch again or give your final answer."
            continue

        if first_line.upper().startswith("FETCH:"):
            url = first_line.split(":", 1)[1].strip()
            try:
                page_text = await fetch_page_text(url)
            except Exception as e:
                page_text = f"(Could not fetch: {e})"
            transcript += f"\n\n[FETCHED: {url}]\n{page_text}\n\nNow continue — search/fetch again or give your final answer."
            continue

        return reply  # final answer, no more tool calls requested

    # ran out of rounds — force a final answer
    final = await call_llm(
        system, transcript + "\n\nGive your final answer now, no more searching."
    )
    return final


async def delegate(manager_system: str, brief: str) -> list[dict]:
    """Used by any manager node (CEO or a department head) to fan out work."""
    raw = await call_llm(manager_system, brief)
    try:
        return json.loads(raw)["delegations"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return []


async def review(review_system: str, team_results: str) -> dict:
    """Used by any manager node to approve or send work back for revision."""
    raw = await call_llm(review_system, team_results)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"decision": "approve", "summary": raw}


async def run_worker(
    agent_key: str, system: str, instructions: str, context: str, uses_browse: bool
) -> str:
    message = (
        instructions
        if not context
        else f"{instructions}\n\n---\nContext from teammates so far:\n{context}"
    )
    if uses_browse:
        return await call_llm_with_browsing(system, message)
    return await call_llm(system, message)
