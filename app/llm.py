import json
import logging
import httpx
from .config import settings
from .web_tools import search_web, fetch_page_text

logger = logging.getLogger(__name__)

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"


async def call_claude(system: str, user_message: str, max_tokens: int = 2000) -> str:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            ANTHROPIC_URL,
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
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


async def call_claude_with_browsing(
    system: str, user_message: str, max_rounds: int = 3
) -> str:
    """
    A light agentic loop for research/marketing agents: the model can ask for a
    live search or a live page fetch, we run it and hand back real results, for
    up to `max_rounds` — then it must give a final answer grounded in what it
    actually found (not memory).
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
        reply = await call_claude(system_with_tools, transcript)
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

    # ran out of rounds — force a final answer with what's been gathered so far
    final = await call_claude(
        system, transcript + "\n\nGive your final answer now, no more searching."
    )
    return final


async def delegate(manager_system: str, brief: str) -> list[dict]:
    """Used by any manager node (CEO or a department head) to fan out work."""
    raw = await call_claude(manager_system, brief)
    try:
        return json.loads(raw)["delegations"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return []


async def review(review_system: str, team_results: str) -> dict:
    """Used by any manager node to approve or send work back for revision."""
    raw = await call_claude(review_system, team_results)
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
        return await call_claude_with_browsing(system, message)
    return await call_claude(system, message)
