from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from backend.config import DEFAULT_LOOP_STATE
from backend.loop.quality_check import evaluate_quality
from backend.loop.runner import LoopRunner


class QualityCheckTests(unittest.TestCase):
    def test_mixed_echo_feedback_does_not_trigger_early_stop(self) -> None:
        quality = evaluate_quality(
            "이상 없음.",
            "좋고 궁금하긴 한데 중간이 조금 늘어져서 몰입이 깨져.",
        )

        self.assertTrue(quality["canon_clean"])
        self.assertFalse(quality["echo_positive"])
        self.assertFalse(quality["should_stop"])
        self.assertEqual(quality["echo_signal"], "mixed")
        self.assertEqual(quality["stop_confidence"], "low")
        self.assertGreaterEqual(quality["positive_hits"], 1)
        self.assertGreaterEqual(quality["negative_hits"], 1)

    def test_strong_positive_reader_pull_allows_early_stop(self) -> None:
        quality = evaluate_quality(
            "이상 없음.",
            "좋고 몰입돼. 다음 장면이 궁금하고 계속 보고 싶어.",
        )

        self.assertTrue(quality["canon_clean"])
        self.assertTrue(quality["echo_positive"])
        self.assertTrue(quality["reader_pull"])
        self.assertTrue(quality["should_stop"])
        self.assertEqual(quality["stop_confidence"], "high")
        self.assertEqual(quality["score"], 2)

    def test_structured_echo_comment_ignores_section_labels_for_quality(self) -> None:
        quality = evaluate_quality(
            "이상 없음.",
            "[댓글]\n반응:\n- 분위기가 좋고 다음 장면이 궁금해.\n몰입:\n- 계속 읽고 싶어.\n이탈감:\n- 없음",
        )

        self.assertTrue(quality["canon_clean"])
        self.assertTrue(quality["echo_positive"])
        self.assertTrue(quality["reader_pull"])
        self.assertTrue(quality["should_stop"])
        self.assertEqual(quality["echo_signal"], "positive")

    def test_canon_concern_blocks_early_stop_even_when_echo_is_positive(self) -> None:
        quality = evaluate_quality(
            "설정 충돌은 없지만 감정선이 약해서 보완이 필요합니다.",
            "좋고 궁금해. 다음 장면도 바로 보고 싶어.",
        )

        self.assertFalse(quality["canon_clean"])
        self.assertFalse(quality["should_stop"])
        self.assertEqual(quality["canon_signal"], "revise")
        self.assertGreaterEqual(quality["canon_concern_hits"], 1)


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


class MixedReactionGeminiClient:
    RESPONSES = {
        "rune_draft": "[초안]\n초안입니다.",
        "canon_review": "[피드백]\n이상 없음.",
        "echo_comment": "[코멘트]\n좋고 궁금하긴 한데 중간이 조금 늘어져서 몰입이 깨져.",
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


class EarlyStopIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_runner_continues_when_echo_signal_is_mixed(self) -> None:
        repository = FakeRepository()
        sil = FakeSil()
        runner = LoopRunner(repository, sil, MixedReactionGeminiClient())

        await runner.start(
            payload={
                "title": "mixed quality",
                "plot": "루프를 한 번 더 돌려야 하는 장면",
                "settings": {"base": "기본", "spoiler": "", "style": "문체"},
                "previous_context": {
                    "mode": "summary",
                    "recent_full_text": "",
                    "summary": "이전 요약",
                },
                "loop_config": {
                    "max_loops": 2,
                    "early_stop_enabled": True,
                    "parallel_feedback": True,
                },
            },
            affinity_stage="warm",
        )
        await runner._task

        self.assertEqual(repository.state["status"], "completed")
        self.assertEqual(len(repository.state["iterations"]), 2)
        self.assertEqual(repository.state["cards"][0]["status"], "done")
        self.assertEqual(repository.state["cards"][1]["status"], "done")
        self.assertFalse(repository.state["iterations"][0]["quality"]["should_stop"])
        self.assertEqual(repository.state["iterations"][0]["quality"]["echo_signal"], "mixed")
        self.assertEqual(len(repository.history_entries), 2)
        self.assertEqual(repository.completed_loops, 2)
        self.assertEqual(sil.loop_logs, [1, 2])


if __name__ == "__main__":
    unittest.main()
