from __future__ import annotations

from typing import Any

from backend.personas.prompts import build_prompt_request
from backend.utils import ensure_label


async def create_draft(
    client: Any,
    *,
    plot: str,
    settings: dict[str, str],
    previous_context: dict[str, str],
    iteration: int,
    affinity_stage: str,
) -> dict[str, Any]:
    prompt = build_prompt_request(
        "rune_draft",
        affinity_stage=affinity_stage,
        plot=plot,
        settings=settings,
        previous_context=previous_context,
        iteration=iteration,
    )
    response = await client.generate_text(
        persona="rune_draft",
        system_prompt=prompt["system_prompt"],
        user_prompt=prompt["user_prompt"],
        temperature=0.95,
    )
    response["text"] = ensure_label(response["text"], "[초안]")
    response["prompt"] = prompt["meta"]
    return response


async def create_final(
    client: Any,
    *,
    plot: str,
    settings: dict[str, str],
    previous_context: dict[str, str],
    draft: str,
    feedback: str,
    comment: str,
    iteration: int,
    affinity_stage: str,
) -> dict[str, Any]:
    prompt = build_prompt_request(
        "rune_final",
        affinity_stage=affinity_stage,
        plot=plot,
        settings=settings,
        previous_context=previous_context,
        draft=draft,
        feedback=feedback,
        comment=comment,
        iteration=iteration,
    )
    response = await client.generate_text(
        persona="rune_final",
        system_prompt=prompt["system_prompt"],
        user_prompt=prompt["user_prompt"],
        temperature=0.9,
    )
    response["text"] = ensure_label(response["text"], "[최종본]")
    response["prompt"] = prompt["meta"]
    return response
