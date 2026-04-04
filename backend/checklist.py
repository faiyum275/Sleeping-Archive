from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
CHECKLIST_DIR = ROOT_DIR / "checklist"
ITEMS_PATH = CHECKLIST_DIR / "items.json"
EVENTS_PATH = CHECKLIST_DIR / "events.jsonl"
MARKDOWN_PATH = ROOT_DIR / "CHECKLIST.md"

ALLOWED_ITEM_KINDS = {"capability", "task", "decision"}
ALLOWED_STATUSES = {"todo", "in_progress", "done", "later"}
ALLOWED_PRIORITIES = {"now", "next", "later"}
STATUS_ORDER = {"in_progress": 0, "todo": 1, "later": 2, "done": 3}
STATUS_SUFFIX = {"in_progress": " (진행 중)", "later": " (후순위)"}


class ChecklistValidationError(ValueError):
    pass


def load_checklist_document(path: Path = ITEMS_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_checklist_events(path: Path = EVENTS_PATH) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not path.exists():
        return events

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as error:
                raise ChecklistValidationError(
                    f"events.jsonl {line_number}번째 줄이 올바른 JSON이 아닙니다: {error}"
                ) from error
            events.append(payload)
    return events


def validate_checklist_data(
    document: dict[str, Any], events: list[dict[str, Any]]
) -> None:
    errors: list[str] = []

    for key in (
        "version",
        "updated_at",
        "title",
        "intro",
        "sections",
        "active_items",
        "archived_items",
    ):
        if key not in document:
            errors.append(f"items.json 상단 키 `{key}` 가 없습니다.")

    if errors:
        raise ChecklistValidationError("\n".join(errors))

    _validate_iso_date(document["updated_at"], "items.json `updated_at`", errors)

    sections = document["sections"]
    if not isinstance(sections, list) or not sections:
        errors.append("`sections` 는 비어 있지 않은 배열이어야 합니다.")
        sections = []

    active_items = document["active_items"]
    if not isinstance(active_items, list) or not active_items:
        errors.append("`active_items` 는 비어 있지 않은 배열이어야 합니다.")
        active_items = []

    archived_items = document["archived_items"]
    if not isinstance(archived_items, list):
        errors.append("`archived_items` 는 배열이어야 합니다.")
        archived_items = []

    section_ids: set[str] = set()
    section_defs: dict[str, dict[str, Any]] = {}
    for index, section in enumerate(sections, start=1):
        label = f"sections[{index - 1}]"
        if not isinstance(section, dict):
            errors.append(f"{label} 는 객체여야 합니다.")
            continue

        for key in ("id", "title", "source"):
            if key not in section:
                errors.append(f"{label} 에 `{key}` 가 없습니다.")

        section_id = section.get("id")
        if isinstance(section_id, str):
            if section_id in section_ids:
                errors.append(f"섹션 id `{section_id}` 가 중복되었습니다.")
            else:
                section_ids.add(section_id)
                section_defs[section_id] = section

        source = section.get("source")
        if not isinstance(source, dict):
            errors.append(f"{label}.source 는 객체여야 합니다.")
            continue

        source_type = source.get("type")
        if source_type not in {"spotlight", "priority", "area", "status"}:
            errors.append(f"{label}.source.type `{source_type}` 는 지원되지 않습니다.")
            continue

        if source_type in {"spotlight", "area", "status"}:
            if not isinstance(source.get("value"), str) or not source.get("value"):
                errors.append(f"{label}.source.value 는 비어 있지 않은 문자열이어야 합니다.")
        elif source_type == "priority":
            values = source.get("values")
            if not isinstance(values, list) or not values:
                errors.append(f"{label}.source.values 는 비어 있지 않은 배열이어야 합니다.")
            else:
                invalid = [value for value in values if value not in ALLOWED_PRIORITIES]
                if invalid:
                    errors.append(
                        f"{label}.source.values 에 허용되지 않는 priority 가 있습니다: {invalid}"
                    )

    item_ids: set[str] = set()
    _validate_item_collection(
        active_items,
        collection_name="active_items",
        item_ids=item_ids,
        errors=errors,
        expected_statuses={"todo", "in_progress", "later"},
    )
    _validate_item_collection(
        archived_items,
        collection_name="archived_items",
        item_ids=item_ids,
        errors=errors,
        expected_statuses={"done"},
    )

    for collection_name, collection in (
        ("active_items", active_items),
        ("archived_items", archived_items),
    ):
        for index, item in enumerate(collection, start=1):
            label = f"{collection_name}[{index - 1}]"
            for related_id in item.get("relates_to", []):
                if related_id not in item_ids:
                    errors.append(f"{label}.relates_to 에 알 수 없는 id `{related_id}` 가 있습니다.")

            if item.get("status") == "later" and item.get("priority") == "now":
                errors.append(f"{label} 는 later 상태인데 priority 가 now 입니다.")

            for section_id in item.get("section_ranks", {}):
                if section_id not in section_ids:
                    errors.append(f"{label}.section_ranks 에 알 수 없는 섹션 `{section_id}` 가 있습니다.")

    for index, event in enumerate(events, start=1):
        label = f"events.jsonl[{index}]"
        if not isinstance(event, dict):
            errors.append(f"{label} 는 객체여야 합니다.")
            continue

        for key in ("at", "type", "summary"):
            if key not in event:
                errors.append(f"{label} 에 `{key}` 가 없습니다.")

        _validate_iso_date(event.get("at"), f"{label}.at", errors)

        event_type = event.get("type")
        if not isinstance(event_type, str) or not event_type:
            errors.append(f"{label}.type 는 비어 있지 않은 문자열이어야 합니다.")

        item_id = event.get("item_id")
        if item_id is not None and item_id not in item_ids:
            errors.append(f"{label}.item_id `{item_id}` 는 items.json 에 없습니다.")

        if event_type == "completed" and item_id is None:
            errors.append(f"{label} 는 completed 이벤트인데 item_id 가 없습니다.")

    for section in sections:
        matched_items = [item for item in active_items if _matches_section(item, section)]
        if not matched_items:
            errors.append(f"섹션 `{section['id']}` 에 매칭되는 아이템이 없습니다.")

    if errors:
        raise ChecklistValidationError("\n".join(errors))


def render_checklist_markdown(
    document: dict[str, Any], events: list[dict[str, Any]]
) -> str:
    validate_checklist_data(document, events)

    lines = [
        f"# {document['title']}",
        "",
        "> 이 파일은 생성 결과다. 직접 수정하지 말고 `checklist/items.json` 과 `checklist/events.jsonl` 을 갱신한 뒤 다시 렌더링한다.",
        "",
        f"마지막 업데이트: {document['updated_at']}",
        "",
        "이 문서는 아직 해야 할 일만 보여준다. 완료 기록은 `checklist/items.json` 의 `archived_items` 와 `checklist/events.jsonl` 에 남긴다.",
        "",
        document["intro"],
        "",
    ]

    items = document["active_items"]
    for section in document["sections"]:
        lines.append(f"## {section['title']}")
        lines.append("")

        matching_items = [item for item in items if _matches_section(item, section)]
        matching_items.sort(key=lambda item: _item_sort_key(item, section["id"]))
        rows = [_format_item_line(item) for item in matching_items]

        if rows:
            lines.extend(rows)
        else:
            lines.append("- 없음")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_rendered_checklist(markdown: str, path: Path = MARKDOWN_PATH) -> None:
    path.write_text(markdown, encoding="utf-8")


def _validate_item_collection(
    items: list[dict[str, Any]],
    *,
    collection_name: str,
    item_ids: set[str],
    errors: list[str],
    expected_statuses: set[str],
) -> None:
    for index, item in enumerate(items, start=1):
        label = f"{collection_name}[{index - 1}]"
        if not isinstance(item, dict):
            errors.append(f"{label} 는 객체여야 합니다.")
            continue

        for key in ("id", "title", "kind", "status", "rank", "updated_at"):
            if key not in item:
                errors.append(f"{label} 에 `{key}` 가 없습니다.")

        item_id = item.get("id")
        if isinstance(item_id, str):
            if item_id in item_ids:
                errors.append(f"아이템 id `{item_id}` 가 중복되었습니다.")
            else:
                item_ids.add(item_id)

        if item.get("kind") not in ALLOWED_ITEM_KINDS:
            errors.append(f"{label}.kind `{item.get('kind')}` 는 지원되지 않습니다.")

        status = item.get("status")
        if status not in ALLOWED_STATUSES:
            errors.append(f"{label}.status `{status}` 는 지원되지 않습니다.")
        elif status not in expected_statuses:
            expected = ", ".join(sorted(expected_statuses))
            errors.append(f"{label}.status `{status}` 는 {collection_name} 에 허용되지 않습니다. 허용값: {expected}")

        priority = item.get("priority")
        if priority is not None and priority not in ALLOWED_PRIORITIES:
            errors.append(f"{label}.priority `{priority}` 는 지원되지 않습니다.")

        if not isinstance(item.get("rank"), int):
            errors.append(f"{label}.rank 는 정수여야 합니다.")

        _validate_iso_date(item.get("updated_at"), f"{label}.updated_at", errors)

        for field_name in ("areas", "spotlights", "tags", "acceptance", "relates_to"):
            value = item.get(field_name)
            if value is None:
                continue
            if not isinstance(value, list):
                errors.append(f"{label}.{field_name} 는 배열이어야 합니다.")
                continue
            if any(not isinstance(entry, str) or not entry for entry in value):
                errors.append(f"{label}.{field_name} 에 비어 있거나 문자열이 아닌 값이 있습니다.")

        section_ranks = item.get("section_ranks")
        if section_ranks is not None:
            if not isinstance(section_ranks, dict):
                errors.append(f"{label}.section_ranks 는 객체여야 합니다.")
            else:
                for section_id, rank in section_ranks.items():
                    if not isinstance(section_id, str) or not section_id:
                        errors.append(f"{label}.section_ranks 에 비어 있는 섹션 id 가 있습니다.")
                    if not isinstance(rank, int):
                        errors.append(f"{label}.section_ranks[`{section_id}`] 는 정수여야 합니다.")


def _matches_section(item: dict[str, Any], section: dict[str, Any]) -> bool:
    source = section["source"]
    source_type = source["type"]

    if source_type == "spotlight":
        return source["value"] in item.get("spotlights", [])
    if source_type == "area":
        return source["value"] in item.get("areas", [])
    if source_type == "status":
        return item.get("status") == source["value"]
    if source_type == "priority":
        return item.get("status") in {"todo", "in_progress"} and item.get("priority") in source["values"]
    return False


def _item_sort_key(item: dict[str, Any], section_id: str) -> tuple[int, int, str]:
    section_rank = item.get("section_ranks", {}).get(section_id, item["rank"])
    return (STATUS_ORDER[item["status"]], section_rank, item["title"])


def _format_item_line(item: dict[str, Any]) -> str:
    checked = "x" if item["status"] == "done" else " "
    suffix = STATUS_SUFFIX.get(item["status"], "")
    return f"- [{checked}] {item['title']}{suffix}"


def _validate_iso_date(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value:
        errors.append(f"{label} 는 비어 있지 않은 ISO 날짜 문자열이어야 합니다.")
        return
    try:
        _parse_iso_date(value)
    except ValueError:
        errors.append(f"{label} `{value}` 는 ISO 날짜 또는 ISO datetime 이어야 합니다.")


def _parse_iso_date(value: str) -> date:
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return date.fromisoformat(value)
