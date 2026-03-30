from __future__ import annotations

from backend.utils import excerpt


CANON_CLEAN_MARKERS = ("이상 없음", "문제 없음", "설정 충돌 없음", "충돌 없이", "무리 없음")
CANON_CONCERN_MARKERS = (
    "충돌",
    "헷갈",
    "약해",
    "보완",
    "수정",
    "조정",
    "붕 뜨",
    "정리 필요",
    "부족",
)
POSITIVE_MARKERS = ("좋", "재밌", "궁금", "몰입", "훌륭", "살아", "강해", "선명")
NEGATIVE_MARKERS = ("지루", "늘어", "헷갈", "약해", "짜치", "붕 뜨", "깨", "이탈", "아쉽")
READER_PULL_MARKERS = (
    "계속 보고 싶",
    "계속 읽고 싶",
    "끝까지 읽고 싶",
    "다음 장면이 궁금",
    "다음 장면 궁금",
    "바로 보고 싶",
)


def evaluate_quality(canon_feedback: str, echo_comment: str) -> dict[str, object]:
    normalized_echo_comment = _normalize_echo_comment_for_quality(echo_comment)
    canon_clean_marker = _contains_any(canon_feedback, CANON_CLEAN_MARKERS)
    canon_concern_hits = _count_canon_concerns(canon_feedback)
    positive_hits = _count_matches(normalized_echo_comment, POSITIVE_MARKERS)
    negative_hits = _count_matches(normalized_echo_comment, NEGATIVE_MARKERS)
    reader_pull = _contains_any(normalized_echo_comment, READER_PULL_MARKERS)

    canon_signal = "clean" if canon_clean_marker and canon_concern_hits == 0 else "revise"
    if negative_hits > 0 and positive_hits > 0:
        echo_signal = "mixed"
    elif negative_hits > 0:
        echo_signal = "concern"
    elif positive_hits > 0 or reader_pull:
        echo_signal = "positive"
    else:
        echo_signal = "neutral"

    canon_clean = canon_signal == "clean"
    echo_positive = echo_signal == "positive"
    should_stop = canon_clean and echo_positive

    if should_stop and reader_pull and positive_hits >= 2:
        stop_confidence = "high"
    elif should_stop:
        stop_confidence = "medium"
    else:
        stop_confidence = "low"

    reasons: list[str] = []
    if canon_clean:
        reasons.append("카논이 강한 설정 리스크를 남기지 않았습니다.")
    else:
        reasons.append(f"카논이 아직 손볼 지점을 남겼습니다: {excerpt(canon_feedback, 80)}")

    if echo_signal == "positive":
        reasons.append("에코 반응이 안정적으로 긍정적입니다.")
    elif echo_signal == "mixed":
        reasons.append("에코 반응에 기대와 우려가 함께 있어 한 번 더 다듬는 편이 안전합니다.")
    elif echo_signal == "concern":
        reasons.append(
            f"에코가 몰입 저해 요소를 지적했습니다: {excerpt(normalized_echo_comment, 80)}"
        )
    else:
        reasons.append("에코 반응이 아직 강하게 끌리는 쪽으로 모이지 않았습니다.")

    if should_stop:
        reasons.append("이번 루프에서 조기 종료를 걸어도 되는 수준으로 판단했습니다.")
    else:
        reasons.append("한 번 더 돌리면 품질 판단이 더 안정될 수 있습니다.")

    return {
        "canon_clean": canon_clean,
        "echo_positive": echo_positive,
        "should_stop": should_stop,
        "reasons": reasons,
        "score": (1 if canon_clean else 0) + (1 if echo_positive else 0),
        "canon_signal": canon_signal,
        "echo_signal": echo_signal,
        "canon_concern_hits": canon_concern_hits,
        "positive_hits": positive_hits,
        "negative_hits": negative_hits,
        "reader_pull": reader_pull,
        "stop_confidence": stop_confidence,
    }


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _count_matches(text: str, markers: tuple[str, ...]) -> int:
    return sum(marker in text for marker in markers)


def _count_canon_concerns(text: str) -> int:
    cleaned = text
    for marker in CANON_CLEAN_MARKERS:
        cleaned = cleaned.replace(marker, "")
    return _count_matches(cleaned, CANON_CONCERN_MARKERS)


def _normalize_echo_comment_for_quality(text: str) -> str:
    cleaned_lines: list[str] = []

    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line or (line.startswith("[") and line.endswith("]")):
            continue
        if line in ("반응:", "몰입:", "이탈감:"):
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)
