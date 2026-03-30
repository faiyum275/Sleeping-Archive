from __future__ import annotations

from typing import Any
import re


SECTION_ORDER = (
    ("reaction", "\ubc18\uc751"),
    ("immersion", "\ubab0\uc785"),
    ("dropoff", "\uc774\ud0c8\uac10"),
)

SECTION_KEYWORDS = {
    "reaction": (
        "\uc88b",
        "\uad81\uae08",
        "\uc7ac\ubc0c",
        "\uc5ec\uc6b4",
        "\ub04c",
        "\uc778\uc0c1",
        "\uc120\uba85",
        "\uac10\uc815",
        "\ubc18\uc751",
    ),
    "immersion": (
        "\ubab0\uc785",
        "\uacc4\uc18d",
        "\ub2e4\uc74c",
        "\uc77d\uace0",
        "\ub118\uae30",
        "\ud638\ud761",
        "\ub9ac\ub4ec",
        "\uc18d\ub3c4",
        "\ube60\uc838",
        "\ub04c\uc5b4\ub2f9",
    ),
    "dropoff": (
        "\uc774\ud0c8",
        "\ub298\uc5b4",
        "\ub04a",
        "\ud5f7\uac08",
        "\uc9c0\ub8e8",
        "\uae68",
        "\uba48\uce6b",
        "\ud280",
        "\ub9c9\ud614",
        "\ubd88\uba85\ud655",
        "\uc57d\ud574",
    ),
}

DROPOFF_MARKERS = (
    "\uc774\ud0c8",
    "\ub298\uc5b4",
    "\ub04a",
    "\ud5f7\uac08",
    "\uc9c0\ub8e8",
    "\uae68",
    "\uba48\uce6b",
    "\ud280",
    "\ub9c9\ud614",
    "\uc57d\ud574",
)
IMMERSION_MARKERS = (
    "\ubab0\uc785",
    "\uacc4\uc18d",
    "\ub2e4\uc74c",
    "\uc77d\uace0",
    "\ub118\uae30",
    "\ud638\ud761",
    "\ub9ac\ub4ec",
    "\ube60\uc838",
)
CLAUSE_SPLIT_RE = re.compile(
    r"\s*(?:,|;|\uadf8\ub7f0\ub370|\ud558\uc9c0\ub9cc|\uadfc\ub370|\ub2e4\ub9cc|\ud55c\ub370|\uadf8\ub9ac\uace0)\s*"
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
    lines = ["[\ub313\uae00]", ""]
    sections = payload.get("sections") or {}

    for key, label in SECTION_ORDER:
        lines.append(f"{label}:")
        items = sections.get(key) or ["\uc5c6\uc74c"]
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
        if not normalized or normalized == "\uc5c6\uc74c" or normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
    return cleaned


def _normalize_point_text(point: str) -> str:
    normalized = point.strip()
    normalized = re.sub(
        r"^(?:\uadf8\ub9ac\uace0|\uadf8\ub7f0\ub370|\ud558\uc9c0\ub9cc|\uadfc\ub370|\ub2e4\ub9cc)\s+",
        "",
        normalized,
    )
    return normalized
