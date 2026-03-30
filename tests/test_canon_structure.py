from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from backend.config import DEFAULT_LOOP_STATE
from backend.loop.runner import LoopRunner
from backend.personas import canon
from backend.personas.canon_structure import (
    format_structured_canon_feedback,
    normalize_canon_feedback,
)


class CanonStructureTests(unittest.TestCase):
    def test_normalize_canon_feedback_from_freeform_text(self) -> None:
        structured = normalize_canon_feedback(
            "[피드백]\n이상 없음.\n다만 후반 장면 전환 호흡은 한 번 더 눌러 주세요.\n다음 루프에서 미래 복선이 흐려질 수 있습니다."
        )

        self.assertEqual(structured["verdict"], "revise")
        self.assertIn("후반 장면 전환 호흡은 한 번 더 눌러 주세요.", structured["sections"]["structure"])
        self.assertIn("다음 루프에서 미래 복선이 흐려질 수 있습니다.", structured["sections"]["future_risk"])
        self.assertTrue(structured["sections"]["next_action"])

    def test_format_structured_canon_feedback_uses_canonical_layout(self) -> None:
        text = format_structured_canon_feedback(
            {
                "verdict": "ok",
                "verdict_label": "이상 없음",
                "sections": {
                    "setting": ["없음"],
                    "structure": ["없음"],
                    "future_risk": ["없음"],
                    "next_action": ["현재 구조를 유지한 채 최종본으로 정리해도 괜찮습니다."],
                },
            }
        )

        self.assertIn("판정: 이상 없음", text)
        self.assertIn("설정:", text)
        self.assertIn("다음 액션:", text)


class DummyCanonClient:
    async def generate_text(self, *, persona, system_prompt, user_prompt, temperature):
        return {
            "text": "[피드백]\n이상 없음.\n도입 구조도 안정적입니다.",
            "usage": {
                "prompt_tokens": 10,
                "candidate_tokens": 20,
                "thoughts_tokens": 0,
                "total_tokens": 30,
            },
            "raw": {"persona": persona},
        }


class CanonReviewDraftTests(unittest.IsolatedAsyncioTestCase):
    async def test_review_draft_returns_structured_payload(self) -> None:
        response = await canon.review_draft(
            DummyCanonClient(),
            draft="초안",
            settings={"base": "기본", "spoiler": "", "style": "문체"},
            previous_context={"mode": "summary", "recent_full_text": "", "summary": ""},
            iteration=1,
            affinity_stage="warm",
        )

        self.assertIn("판정:", response["text"])
        self.assertIn("설정:", response["text"])
        self.assertEqual(response["structured"]["verdict"], "ok")
        self.assertIn("도입 구조도 안정적입니다.", response["structured"]["sections"]["next_action"])


class FakeRepository:
    def __init__(self) -> None:
        self.state = deepcopy(DEFAULT_LOOP_STATE)
        self.history_entries: list[dict] = []

    def get_loop_state(self):
        return deepcopy(self.state)

    def save_loop_state(self, payload):
        self.state = deepcopy(payload)
        return deepcopy(self.state)

    def save_history_entry(self, payload):
        self.history_entries.append(deepcopy(payload))
        return Path("history/test.json")

    def increment_run_stats(self, completed_loops):
        return {"completed_loops": completed_loops}


class FakeSil:
    def log_loop_completion(self, loop_index):
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
        "rune_draft": "[초안]\n초안입니다.",
        "canon_review": "[피드백]\n이상 없음.\n지금 구조면 설정 충돌 없이 바로 최종본으로 정리해도 괜찮습니다.",
        "echo_comment": "[댓글]\n좋고 몰입돼. 다음 장면이 궁금해.",
        "rune_final": "[최종본]\n최종본입니다.",
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


class CanonStructurePersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_runner_persists_feedback_structure(self) -> None:
        repository = FakeRepository()
        runner = LoopRunner(repository, FakeSil(), FakeGeminiClient())

        await runner.start(
            payload={
                "title": "canon structure",
                "plot": "구조화된 피드백을 남길 장면",
                "settings": {"base": "기본", "spoiler": "", "style": "문체"},
                "previous_context": {
                    "mode": "summary",
                    "recent_full_text": "",
                    "summary": "",
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
        self.assertIsNotNone(iteration["feedback_structured"])
        self.assertEqual(iteration["feedback_structured"]["verdict"], "ok")
        self.assertEqual(
            repository.history_entries[0]["feedback_structured"],
            iteration["feedback_structured"],
        )


if __name__ == "__main__":
    unittest.main()
