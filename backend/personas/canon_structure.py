from __future__ import annotations

from typing import Any
import re


SECTION_ORDER = (
    ("setting", "설정"),
    ("structure", "구조"),
    ("future_risk", "미래 리스크"),
    ("next_action", "다음 액션"),
)

SECTION_KEYWORDS = {
    "setting": ("설정", "세계관", "정보", "규칙", "개연", "인물", "관계", "배경", "동기"),
    "structure": ("구조", "장면", "전개", "흐름", "호흡", "템포", "문장", "도입", "후반", "전환", "리듬"),
    "future_risk": ("미래", "이후", "다음", "향후", "복선", "후속", "결말", "리스크"),
    "next_action": ("보완", "수정", "조정", "정리", "유지", "다듬", "줄", "늘", "밀어", "눌러", "강조"),
}

CLEAN_MARKERS = ("이상 없음", "문제 없음", "설정 충돌 없음", "충돌 없이", "무리 없음")
CONCERN_MARKERS = ("충돌", "헷갈", "약해", "보완", "수정", "조정", "붕 뜨", "정리 필요", "부족")
SUPPORTIVE_ACTION_MARKERS = ("괜찮", "안정적", "유지", "최종본", "바로 정리", "문제 없음")


def normalize_canon_feedback(text: str) -> dict[str, Any]:
    body = _strip_feedback_label(text)
    parsed = _parse_structured_body(body)
    if parsed is None:
        parsed = _classify_freeform_body(body)

    verdict = parsed.get("verdict") or _detect_verdict(body, parsed["sections"])
    return {
        "verdict": verdict,
        "verdict_label": "이상 없음" if verdict == "ok" else "수정 필요",
        "sections": {
            key: _dedupe_points(parsed["sections"].get(key, []))
            for key, _ in SECTION_ORDER
        },
    }


def format_structured_canon_feedback(payload: dict[str, Any]) -> str:
    lines = [
        "[피드백]",
        f"판정: {payload.get('verdict_label') or '수정 필요'}",
        "",
    ]

    sections = payload.get("sections") or {}
    for key, label in SECTION_ORDER:
        lines.append(f"{label}:")
        items = sections.get(key) or ["없음"]
        lines.extend(f"- {item}" for item in items)
        lines.append("")

    return "\n".join(lines).strip()


def _parse_structured_body(body: str) -> dict[str, Any] | None:
    if "판정:" not in body:
        return None

    section_labels = {label: key for key, label in SECTION_ORDER}
    sections: dict[str, list[str]] = {key: [] for key, _ in SECTION_ORDER}
    current_key: str | None = None
    verdict: str | None = None

    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("판정:"):
            verdict = "ok" if "이상 없음" in line else "revise"
            continue
        if line.endswith(":") and line[:-1] in section_labels:
            current_key = section_labels[line[:-1]]
            continue
        if current_key is None:
            continue
        normalized = re.sub(r"^[-*•]\s*", "", line).strip()
        if normalized:
            sections[current_key].append(normalized)

    if not any(sections.values()):
        return None

    return {"verdict": verdict, "sections": sections}


def _classify_freeform_body(body: str) -> dict[str, Any]:
    sections: dict[str, list[str]] = {key: [] for key, _ in SECTION_ORDER}
    points = _extract_points(body)

    for point in points:
        target = _classify_point(point)
        sections[target].append(point)

    if not any(sections.values()) and body.strip():
        sections["structure"].append(body.strip())

    if not sections["next_action"]:
        if _contains_any(body, CLEAN_MARKERS):
            sections["next_action"].append("현재 구조를 유지한 채 최종본으로 정리해도 괜찮습니다.")
        else:
            sections["next_action"].append("카논이 짚은 지점을 반영해 다음 루프에서 다시 점검하세요.")

    return {"verdict": None, "sections": sections}


def _detect_verdict(body: str, sections: dict[str, list[str]]) -> str:
    issue_sections = ("setting", "structure", "future_risk")
    has_issue = any(
        point and point != "없음" and not _is_supportive_clean_point(point)
        for key in issue_sections
        for point in sections.get(key, [])
    )

    if _contains_any(body, CLEAN_MARKERS):
        concern_source = body
        for marker in CLEAN_MARKERS:
            concern_source = concern_source.replace(marker, "")
        if not _contains_any(concern_source, CONCERN_MARKERS) and not has_issue:
            return "ok"

    return "revise" if has_issue else "ok"


def _extract_points(body: str) -> list[str]:
    lines = [
        _normalize_point_text(re.sub(r"^[-*•]\s*", "", line.strip()))
        for line in body.splitlines()
        if line.strip()
    ]
    lines = [line for line in lines if line and not _is_clean_marker_line(line)]
    if lines:
        return lines

    sentences = [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+|\n+", body)
        if part.strip()
    ]
    return [part for part in sentences if part not in CLEAN_MARKERS]


def _classify_point(point: str) -> str:
    if _is_supportive_clean_point(point):
        return "next_action"
    scores = {
        key: sum(keyword in point for keyword in keywords)
        for key, keywords in SECTION_KEYWORDS.items()
    }
    best_key = max(scores, key=scores.get)
    if scores[best_key] == 0:
        return "structure"
    return best_key


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _strip_feedback_label(text: str) -> str:
    return re.sub(r"^\[피드백\]\s*", "", str(text or "").strip(), flags=re.MULTILINE)


def _dedupe_points(points: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for point in points:
        normalized = point.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
    return cleaned


def _normalize_point_text(point: str) -> str:
    normalized = point.strip()
    normalized = re.sub(r"^(다만|또는|그리고)\s+", "", normalized)
    return normalized


def _is_clean_marker_line(point: str) -> bool:
    compact = point.rstrip(".! ").strip()
    return compact in CLEAN_MARKERS


def _is_supportive_clean_point(point: str) -> bool:
    if _contains_any(point, SUPPORTIVE_ACTION_MARKERS):
        concern_source = point
        for marker in CLEAN_MARKERS:
            concern_source = concern_source.replace(marker, "")
        return not _contains_any(concern_source, CONCERN_MARKERS)
    return False
