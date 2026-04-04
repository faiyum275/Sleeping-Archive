from __future__ import annotations

import unittest

from backend.checklist import (
    MARKDOWN_PATH,
    load_checklist_document,
    load_checklist_events,
    render_checklist_markdown,
    validate_checklist_data,
)


class ChecklistDataTest(unittest.TestCase):
    def test_checklist_data_is_valid(self) -> None:
        document = load_checklist_document()
        events = load_checklist_events()
        validate_checklist_data(document, events)

    def test_checklist_markdown_is_current(self) -> None:
        document = load_checklist_document()
        events = load_checklist_events()
        rendered = render_checklist_markdown(document, events)
        current = MARKDOWN_PATH.read_text(encoding="utf-8")
        self.assertEqual(current, rendered)


if __name__ == "__main__":
    unittest.main()
