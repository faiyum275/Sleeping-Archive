from __future__ import annotations

from typing import Any

from backend.personas.canon_structure import (
    format_structured_canon_feedback,
    normalize_canon_feedback,
)
from backend.personas.prompts import build_prompt_request
from backend.utils import ensure_label


async def review_draft(
    client: Any,
    *,
    draft: str,
    settings: dict[str, str],
    previous_context: dict[str, str],
    iteration: int,
    affinity_stage: str,
) -> dict[str, Any]:
    prompt = build_prompt_request(
        "canon_review",
        affinity_stage=affinity_stage,
        draft=draft,
        settings=settings,
        previous_context=previous_context,
        iteration=iteration,
    )
    response = await client.generate_text(
        persona="canon_review",
        system_prompt=prompt["system_prompt"],
        user_prompt=prompt["user_prompt"],
        temperature=0.4,
    )
    response["text"] = ensure_label(response["text"], "[피드백]")
    response["structured"] = normalize_canon_feedback(response["text"])
    response["text"] = format_structured_canon_feedback(response["structured"])
    response["prompt"] = prompt["meta"]
    return response
