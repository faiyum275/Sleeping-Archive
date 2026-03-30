from __future__ import annotations

from datetime import datetime, timezone
import math
import re


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def local_clock_label() -> str:
    return datetime.now().strftime("%H:%M")


def parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def estimate_tokens(text: str) -> int:
    if not text.strip():
        return 1
    return max(1, math.ceil(len(text) / 4))


def excerpt(text: str, limit: int = 240) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def ensure_label(text: str, label: str) -> str:
    stripped = text.strip()
    if stripped.startswith(label):
        return stripped
    return f"{label}\n{stripped}".strip()


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))
