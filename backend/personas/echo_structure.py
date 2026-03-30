from __future__ import annotations

from typing import Any
import re


SECTION_ORDER = (
    ("reaction", "반응"),
    ("immersion", "몰입"),
    ("dropoff", "이탈감"),
)

SECTION_KEYWORDS = {
    "reaction": (
        "좋",
        "궁금",
        "재밌",
        "여운",
        "끌",
        "인상",
        "선명",
        "감정",
        "반응",
    ),
    "immersion": (
        "몰입",
        "계속",
        "다음",
        "읽고",
        "넘기",
        "호흡",
        "리듬",
        "속도",
        "빠져",
        "끌어당",
    ),
    "dropoff": (
        "이탈",
        "늘어",
        "끊",
        "헷갈",
        "지루",
        "깨",
        "멈칫",
        "튀",
        "막혔",
        "불명확",
        "약해",
    ),
}

DROPOFF_MARKERS = (
    "이탈",
    "늘어",
    "끊",
    "헷갈",
    "지루",
    "깨",
    "멈칫",
    "튀",
    "막혔",
    "약해",
)
IMMERSION_MARKERS = (
    "몰입",
    "계속",
    "다음",
    "읽고",
    "넘기",
    "호흡",
    "리듬",
    "빠져",
)
CLAUSE_SPLIT_RE = re.compile(
    r"\s*(?:,|;|그런데|하지만|근데|다만|한데|그리고)\s*"
)


def normalize_echo_comment(text: str) -> dict[str, Any]:
    body = _strip_comment_label(text)
    parsed = _parse_structured_body(body)
    if parsed is None:
        parsed = _classify_freeform_body(body)

    return {
        "sections": {
            key: _dedupe_points(parsed["sections"].get(key, []))
            for key, _ in SECTION_ORDER
        }
    }


def format_structured_echo_comment(payload: dict[str, Any]) -> str:
    lines = ["[댓글]", ""]
    sections = payload.get("sections") or {}

    for key, label in SECTION_ORDER:
        lines.append(f"{label}:")
        items = sections.get(key) or ["없음"]
        lines.extend(f"- {item}" for item in items)
        lines.append("")

    return "\n".join(lines).strip()


def _parse_structured_body(body: str) -> dict[str, Any] | None:
    section_labels = {label: key for key, label in SECTION_ORDER}
    if not any(f"{label}:" in body for label in section_labels):
        return None

    sections: dict[str, list[str]] = {key: [] for key, _ in SECTION_ORDER}
    current_key: str | None = None

    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        direct_match = next(
            (
                (key, line[len(label) + 1 :].strip())
                for label, key in section_labels.items()
                if line.startswith(f"{label}:")
            ),
            None,
        )
        if direct_match is not None:
            current_key, remainder = direct_match
            if remainder:
                sections[current_key].append(remainder)
            continue

        if line.endswith(":") and line[:-1] in section_labels:
            current_key = section_labels[line[:-1]]
            continue

        if current_key is None:
            continue

        normalized = re.sub(r"^[-*•\s]+", "", line).strip()
        if normalized:
            sections[current_key].append(normalized)

    if not any(sections.values()):
        return None

    return {"sections": sections}


def _classify_freeform_body(body: str) -> dict[str, Any]:
    sections: dict[str, list[str]] = {key: [] for key, _ in SECTION_ORDER}

    for point in _extract_points(body):
        sections[_classify_point(point)].append(point)

    if not any(sections.values()) and body.strip():
        sections["reaction"].append(body.strip())

    return {"sections": sections}


def _extract_points(body: str) -> list[str]:
    lines = [
        re.sub(r"^[-*•\s]+", "", line.strip())
        for line in body.splitlines()
        if line.strip()
    ]

    raw_points = lines or [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+|\n+", body)
        if part.strip()
    ]

    points: list[str] = []
    for raw_point in raw_points:
        for chunk in CLAUSE_SPLIT_RE.split(raw_point):
            normalized = _normalize_point_text(chunk)
            if normalized:
                points.append(normalized)
    return points


def _classify_point(point: str) -> str:
    scores = {
        key: sum(keyword in point for keyword in keywords)
        for key, keywords in SECTION_KEYWORDS.items()
    }

    if _contains_any(point, DROPOFF_MARKERS):
        scores["dropoff"] += 2
    if _contains_any(point, IMMERSION_MARKERS):
        scores["immersion"] += 1

    best_key = max(scores, key=scores.get)
    if scores[best_key] == 0:
        return "reaction"
    return best_key


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _strip_comment_label(text: str) -> str:
    return re.sub(r"^\[[^\]]+\]\s*", "", str(text or "").strip(), flags=re.MULTILINE)


def _dedupe_points(points: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for point in points:
        normalized = point.strip()
        if not normalized or normalized == "없음" or normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
    return cleaned


def _normalize_point_text(point: str) -> str:
    normalized = point.strip()
    normalized = re.sub(
        r"^(?:그리고|그런데|하지만|근데|다만)\s+",
        "",
        normalized,
    )
    return normalized
