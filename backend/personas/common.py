from __future__ import annotations

from typing import Any

from backend.utils import excerpt


def prompt_block(title: str, body: str) -> str:
    value = body.strip() or "없음"
    return f"## {title}\n{value}"


def format_previous_context(previous_context: dict[str, Any]) -> str:
    mode = previous_context.get("mode", "hybrid")
    recent_full_text = previous_context.get("recent_full_text", "").strip()
    summary = previous_context.get("summary", "").strip()

    if mode == "recent":
        return prompt_block("이전 내용 (최근 전문)", recent_full_text)
    if mode == "summary":
        return prompt_block("이전 내용 (요약)", summary)
    return "\n\n".join(
        [
            prompt_block("이전 내용 (최근 전문)", recent_full_text),
            prompt_block("이전 내용 (요약)", summary),
        ]
    )


def intimacy_note(persona: str, affinity_stage: str) -> str:
    table = {
        "rune": {
            "distant": "말투는 정중하고 조심스럽게 유지합니다.",
            "warm": "말투는 여전히 공손하지만 저자에게 조금 더 기대는 기색을 드러냅니다.",
            "close": "말투는 편안하지만 섬세함을 잃지 않습니다.",
        },
        "canon": {
            "distant": "피드백은 정확하고 절제된 문장으로 씁니다.",
            "warm": "정확함을 유지하되 배려가 더 드러나도록 씁니다.",
            "close": "단호하되 한층 익숙한 톤으로 씁니다.",
        },
        "echo": {
            "distant": "직설적이되 필요 이상으로 거칠어지지 않습니다.",
            "warm": "감정 표현을 더 적극적으로 드러냅니다.",
            "close": "아주 솔직하고 친근하게 반응합니다.",
        },
    }
    return table.get(persona, {}).get(affinity_stage, "")


def summarize_for_ui(text: str) -> str:
    return excerpt(text, 140)
