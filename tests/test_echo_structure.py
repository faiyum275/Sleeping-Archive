from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from backend.config import DEFAULT_LOOP_STATE
from backend.loop.runner import LoopRunner
from backend.personas.echo_structure import (
    format_structured_echo_comment,
    normalize_echo_comment,
)


class EchoStructureTests(unittest.TestCase):
    def test_normalize_echo_comment_from_freeform_text(self) -> None:
        structured = normalize_echo_comment(
            "[댓글]\n분위기는 좋고 다음 장면이 궁금해.\n첫 장면에서 바로 몰입돼.\n중간 설명이 조금 늘어져서 흐름이 끊겨."
        )

        self.assertTrue(
            any("좋고" in item or "궁금" in item for item in structured["sections"]["reaction"])
        )
        self.assertTrue(
            any("몰입" in item for item in structured["sections"]["immersion"])
        )
        self.assertTrue(
            any("늘어" in item or "끊겨" in item for item in structured["sections"]["dropoff"])
        )

    def test_format_structured_echo_comment_uses_canonical_layout(self) -> None:
        text = format_structured_echo_comment(
            {
                "sections": {
                    "reaction": ["분위기가 선명합니다."],
                    "immersion": ["첫 장면에서 바로 빠져듭니다."],
                    "dropoff": ["없음"],
                }
            }
        )

        self.assertIn("[댓글]", text)
        self.assertIn("반응:", text)
        self.assertIn("- 분위기가 선명합니다.", text)
        self.assertIn("몰입:", text)
        self.assertIn("이탈감:", text)


class FakeRepository:
    def __init__(self) -> None:
        self.state = deepcopy(DEFAULT_LOOP_STATE)
        self.history_entries: list[dict] = []
        self.completed_loops = 0

    def get_loop_state(self):
        return deepcopy(self.state)

    def save_loop_state(self, payload):
        self.state = deepcopy(payload)
        return deepcopy(self.state)

    def save_history_entry(self, payload):
        self.history_entries.append(deepcopy(payload))
        return Path(f"history/test_{len(self.history_entries)}.json")

    def increment_run_stats(self, completed_loops):
        self.completed_loops = completed_loops
        return {"completed_loops": completed_loops}


class FakeSil:
    def __init__(self) -> None:
        self.loop_logs: list[int] = []

    def log_loop_completion(self, loop_index):
        self.loop_logs.append(loop_index)
        return {"loop_index": loop_index}

    def record_error(self, error, *, code=None, context=None):
        return {
            "error": str(error),
            "error_code": code or "UNEXPECTED_ERROR",
            "display": str(error),
            "context": context or {},
        }


class FakeGeminiClient:
    RESPONSES = {
        "rune_draft": "[초안]\n서고 안쪽으로 들어가는 초안입니다.",
        "canon_review": "[피드백]\n판정: 이상 없음\n설정:\n- 없음\n구조:\n- 초반 구조가 안정적입니다.\n미래 리스크:\n- 없음\n다음 액션:\n- 현재 흐름을 유지해도 좋습니다.",
        "echo_comment": "[댓글]\n분위기는 좋고 다음 장면이 궁금해.\n첫 장면에서 바로 몰입돼.\n중간 설명이 조금 늘어져서 흐름이 끊겨.",
        "rune_final": "[최종본]\n다듬어진 최종본입니다.",
    }

    async def generate_text(self, *, persona, system_prompt, user_prompt, temperature):
        return {
            "text": self.RESPONSES[persona],
            "usage": {
                "prompt_tokens": 10,
                "candidate_tokens": 20,
                "thoughts_tokens": 0,
                "total_tokens": 30,
            },
            "raw": {"persona": persona},
        }


class EchoStructureIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_runner_persists_comment_structured_in_state_and_history(self) -> None:
        repository = FakeRepository()
        sil = FakeSil()
        runner = LoopRunner(repository, sil, FakeGeminiClient())

        await runner.start(
            payload={
                "title": "echo structure",
                "plot": "서고 문틈에서 빛이 새어 나오는 장면",
                "settings": {"base": "기본 설정", "spoiler": "", "style": "문체"},
                "previous_context": {
                    "mode": "summary",
                    "recent_full_text": "",
                    "summary": "이전 요약",
                },
                "loop_config": {
                    "max_loops": 1,
                    "early_stop_enabled": True,
                    "parallel_feedback": True,
                },
            },
            affinity_stage="warm",
        )
        await runner._task

        iteration = repository.state["iterations"][0]
        self.assertIsNotNone(iteration["comment_structured"])
        self.assertIn("reaction", iteration["comment_structured"]["sections"])
        self.assertIn("immersion", iteration["comment_structured"]["sections"])
        self.assertIn("dropoff", iteration["comment_structured"]["sections"])
        self.assertEqual(
            repository.history_entries[0]["comment_structured"],
            iteration["comment_structured"],
        )
        self.assertIn("이탈감:", iteration["comment"])


if __name__ == "__main__":
    unittest.main()
