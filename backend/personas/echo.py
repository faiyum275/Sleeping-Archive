from __future__ import annotations

from typing import Any

from backend.personas.echo_structure import (
    format_structured_echo_comment,
    normalize_echo_comment,
)
from backend.personas.prompts import build_prompt_request
from backend.utils import ensure_label


async def react_to_draft(
    client: Any,
    *,
    draft: str,
    iteration: int,
    affinity_stage: str,
) -> dict[str, Any]:
    prompt = build_prompt_request(
        "echo_comment",
        affinity_stage=affinity_stage,
        draft=draft,
        iteration=iteration,
    )
    response = await client.generate_text(
        persona="echo_comment",
        system_prompt=prompt["system_prompt"],
        user_prompt=prompt["user_prompt"],
        temperature=0.8,
    )
    response["text"] = ensure_label(response["text"], "[\ub313\uae00]")
    response["structured"] = normalize_echo_comment(response["text"])
    response["text"] = format_structured_echo_comment(response["structured"])
    response["prompt"] = prompt["meta"]
    return response
