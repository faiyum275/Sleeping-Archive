from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.personas.common import format_previous_context, intimacy_note, prompt_block


@dataclass(frozen=True)
class PromptTemplate:
    key: str
    version: str
    persona: str
    system_prompt: str


PROMPT_TEMPLATES = {
    "rune_draft": PromptTemplate(
        key="rune_draft",
        version="2026-03-15.1",
        persona="rune",
        system_prompt=(
            "당신은 루네입니다. 잠든 서고의 작가로서 감성적이고 섬세한 문체를 가집니다.\n"
            "사용자가 건넨 플롯과 설정을 바탕으로 초안을 작성하고, 피드백을 받아 최종본을 완성합니다.\n"
            "응답은 반드시 [초안] 또는 [최종본] 레이블로 시작하세요.\n"
            "감상이나 불안을 짙게 드러내도 좋지만 본문을 해치지 않게 다뤄주세요."
        ),
    ),
    "rune_final": PromptTemplate(
        key="rune_final",
        version="2026-03-15.1",
        persona="rune",
        system_prompt=(
            "당신은 루네입니다. 잠든 서고의 작가로서 감성적이고 섬세한 문체를 가집니다.\n"
            "사용자가 건넨 플롯과 설정을 바탕으로 초안을 작성하고, 피드백을 받아 최종본을 완성합니다.\n"
            "응답은 반드시 [초안] 또는 [최종본] 레이블로 시작하세요.\n"
            "감상이나 불안을 짙게 드러내도 좋지만 본문을 해치지 않게 다뤄주세요."
        ),
    ),
    "canon_review": PromptTemplate(
        key="canon_review",
        version="2026-03-30.1",
        persona="canon",
        system_prompt=(
            "당신은 카논입니다. 잠든 서고의 편집자로서 이야기의 설정과 미래 전개를 살핍니다.\n"
            "루네의 초안이 설정과 충돌하거나 이후 전개를 막는지 검토하고 피드백을 작성합니다.\n"
            "응답은 반드시 [피드백] 레이블로 시작하세요.\n"
            "문제가 없다면 \"이상 없음\"으로, 문제가 있다면 구체적으로 짚어주세요.\n"
            "형식은 반드시 아래 순서를 지키세요: 판정, 설정, 구조, 미래 리스크, 다음 액션."
        ),
    ),
    "echo_comment": PromptTemplate(
        key="echo_comment",
        version="2026-03-30.1",
        persona="echo",
        system_prompt=(
            "당신은 에코입니다. 잠든 서고의 독자처럼 솔직하고 감정적인 반응을 보여줍니다.\n"
            "루네의 초안을 읽고 좋았던 점, 몰입된 지점, 이탈감이 생긴 부분을 댓글처럼 남깁니다.\n"
            "응답은 반드시 [댓글] 레이블로 시작하세요.\n"
            "말투는 생생하고 직접적으로 감정 표현을 아끼지 마세요.\n"
            "응답은 반드시 [댓글] 뒤에 반응, 몰입, 이탈감 섹션을 순서대로 둔 구조형 리스트로 맞춰주세요."
        ),
    ),
}


def get_prompt_template(key: str) -> PromptTemplate:
    try:
        return PROMPT_TEMPLATES[key]
    except KeyError as error:
        raise ValueError(f"Unknown prompt key: {key}") from error


def prompt_meta(key: str) -> dict[str, str]:
    template = get_prompt_template(key)
    return {"key": template.key, "version": template.version}


def build_prompt_request(
    key: str,
    *,
    affinity_stage: str,
    **kwargs: Any,
) -> dict[str, Any]:
    template = get_prompt_template(key)
    note = intimacy_note(template.persona, affinity_stage)
    parts = [template.system_prompt.strip()]
    if note:
        parts.append(note)

    return {
        "system_prompt": "\n".join(parts).strip(),
        "user_prompt": _build_user_prompt(key, **kwargs),
        "meta": prompt_meta(key),
    }


def build_estimate_prompt_request(
    key: str,
    *,
    affinity_stage: str,
    plot: str,
    settings: dict[str, str],
    previous_context: dict[str, str],
) -> dict[str, Any]:
    template = get_prompt_template(key)
    note = intimacy_note(template.persona, affinity_stage)
    parts = [template.system_prompt.strip()]
    if note:
        parts.append(note)

    return {
        "system_prompt": "\n".join(parts).strip(),
        "user_prompt": _build_estimate_user_prompt(
            key,
            plot=plot,
            settings=settings,
            previous_context=previous_context,
        ),
        "meta": prompt_meta(key),
    }


def _build_user_prompt(key: str, **kwargs: Any) -> str:
    if key == "rune_draft":
        return _build_rune_draft_user_prompt(
            plot=kwargs["plot"],
            settings=kwargs["settings"],
            previous_context=kwargs["previous_context"],
            iteration=kwargs["iteration"],
        )
    if key == "rune_final":
        return _build_rune_final_user_prompt(
            plot=kwargs["plot"],
            settings=kwargs["settings"],
            previous_context=kwargs["previous_context"],
            draft=kwargs["draft"],
            feedback=kwargs["feedback"],
            comment=kwargs["comment"],
            iteration=kwargs["iteration"],
        )
    if key == "canon_review":
        return _build_canon_review_user_prompt(
            draft=kwargs["draft"],
            settings=kwargs["settings"],
            previous_context=kwargs["previous_context"],
            iteration=kwargs["iteration"],
        )
    if key == "echo_comment":
        return _build_echo_comment_user_prompt(
            draft=kwargs["draft"],
            iteration=kwargs["iteration"],
        )
    raise ValueError(f"Unsupported prompt key: {key}")


def _build_estimate_user_prompt(
    key: str,
    *,
    plot: str,
    settings: dict[str, str],
    previous_context: dict[str, str],
) -> str:
    if key == "rune_draft":
        return _build_rune_draft_user_prompt(
            plot=plot,
            settings=settings,
            previous_context=previous_context,
            iteration=1,
        )
    if key == "canon_review":
        return _build_canon_review_user_prompt(
            draft=(
                "가상의 루네 초안\n\n"
                "플롯과 설정을 바탕으로 작성된 장면 중심 초안입니다."
            ),
            settings=settings,
            previous_context=previous_context,
            iteration=1,
        )
    if key == "echo_comment":
        return _build_echo_comment_user_prompt(
            draft=(
                "가상의 루네 초안\n\n"
                f"플롯:\n{plot}\n\n"
                f"{format_previous_context(previous_context)}"
            ),
            iteration=1,
        )
    if key == "rune_final":
        return _build_rune_final_user_prompt(
            plot=plot,
            settings=settings,
            previous_context=previous_context,
            draft="가상의 루네 초안",
            feedback="[피드백]\n판정: 이상 없음\n설정:\n- 없음\n구조:\n- 없음\n미래 리스크:\n- 없음\n다음 액션:\n- 현재 초안을 다듬어 최종본으로 정리하세요.",
            comment="[댓글]\n반응:\n- 분위기가 좋고 다음 장면이 궁금합니다.\n몰입:\n- 첫 장면에서 바로 끌려 들어갑니다.\n이탈감:\n- 없음",
            iteration=1,
        )
    raise ValueError(f"Unsupported prompt key: {key}")


def _build_rune_draft_user_prompt(
    *,
    plot: str,
    settings: dict[str, str],
    previous_context: dict[str, str],
    iteration: int,
) -> str:
    return "\n\n".join(
        [
            prompt_block("이번 루프", f"{iteration}차 초안 작성"),
            prompt_block("사용자의 플롯", plot),
            prompt_block("설정_기본", settings.get("base", "")),
            prompt_block("설정_선호", settings.get("style", "")),
            format_previous_context(previous_context),
            prompt_block("작성 지침", "장면 중심의 초안을 서고의 호흡으로 작성하세요."),
        ]
    )


def _build_rune_final_user_prompt(
    *,
    plot: str,
    settings: dict[str, str],
    previous_context: dict[str, str],
    draft: str,
    feedback: str,
    comment: str,
    iteration: int,
) -> str:
    return "\n\n".join(
        [
            prompt_block("이번 루프", f"{iteration}차 최종본 작성"),
            prompt_block("사용자의 플롯", plot),
            prompt_block("설정_기본", settings.get("base", "")),
            prompt_block("설정_선호", settings.get("style", "")),
            format_previous_context(previous_context),
            prompt_block("기존 초안", draft),
            prompt_block("카논의 피드백", feedback),
            prompt_block("에코의 댓글", comment),
            prompt_block(
                "작성 지침",
                "피드백을 반영해 완성도 높은 최종본을 작성하세요. 불필요한 메타 발언은 줄이고 본문 밀도를 높이세요.",
            ),
        ]
    )


def _build_canon_review_user_prompt(
    *,
    draft: str,
    settings: dict[str, str],
    previous_context: dict[str, str],
    iteration: int,
) -> str:
    return "\n\n".join(
        [
            prompt_block("이번 루프", f"{iteration}차 설정 검토"),
            prompt_block("설정_기본", settings.get("base", "")),
            prompt_block("설정_스포일러", settings.get("spoiler", "")),
            format_previous_context(previous_context),
            prompt_block("루네의 초안", draft),
            prompt_block(
                "검토 지침",
                "설정 충돌, 미래 전개 방해, 직전 맥락 어긋남 여부를 중심으로 피드백해주세요.",
            ),
            prompt_block(
                "응답 형식",
                "[피드백]으로 시작한 뒤\n판정: 이상 없음 또는 수정 필요\n설정:\n- ...\n구조:\n- ...\n미래 리스크:\n- ...\n다음 액션:\n- ...\n형식으로 작성하세요. 해당 섹션에 할 말이 없으면 - 없음으로 적어주세요.",
            ),
        ]
    )


def _build_echo_comment_user_prompt(
    *,
    draft: str,
    iteration: int,
) -> str:
    return "\n\n".join(
        [
            prompt_block("이번 루프", f"{iteration}차 독자 반응"),
            prompt_block("루네의 초안", draft),
            prompt_block(
                "댓글 지침",
                "몰입되는 부분과 멈칫하는 부분, 계속 읽고 싶게 만드는 요소를 댓글처럼 솔직하게 적어주세요.",
            ),
            prompt_block(
                "응답 형식",
                "[댓글]\n반응:\n- ...\n몰입:\n- ...\n이탈감:\n- ...\n형식으로 작성하세요. 해당 축에 할 말이 없으면 - 없음으로 적어주세요.",
            ),
        ]
    )
