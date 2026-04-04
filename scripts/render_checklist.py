from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.checklist import (  # noqa: E402
    ITEMS_PATH,
    MARKDOWN_PATH,
    ChecklistValidationError,
    load_checklist_document,
    load_checklist_events,
    render_checklist_markdown,
    write_rendered_checklist,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render CHECKLIST.md from checklist data.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if CHECKLIST.md does not match the rendered output.",
    )
    args = parser.parse_args()

    try:
        document = load_checklist_document(ITEMS_PATH)
        events = load_checklist_events()
        rendered = render_checklist_markdown(document, events)
    except ChecklistValidationError as error:
        print(error, file=sys.stderr)
        return 1

    if args.check:
        current = MARKDOWN_PATH.read_text(encoding="utf-8") if MARKDOWN_PATH.exists() else ""
        if current != rendered:
            print("CHECKLIST.md 가 checklist 원본과 일치하지 않습니다.", file=sys.stderr)
            return 1
        return 0

    write_rendered_checklist(rendered, MARKDOWN_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
