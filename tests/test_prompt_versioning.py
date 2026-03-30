from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from backend.config import DEFAULT_LOOP_STATE
from backend.loop.runner import LoopRunner
from backend.personas.prompts import build_estimate_prompt_request, prompt_meta


class FakeRepository:
    def __init__(self):
        self.state = deepcopy(DEFAULT_LOOP_STATE)
        self.history_entries = []
        self.completed_loops = 0

    def get_loop_state(self):
        return deepcopy(self.state)

    def save_loop_state(self, payload):
        self.state = deepcopy(payload)
        return deepcopy(self.state)

    def save_history_entry(self, payload):
        self.history_entries.append(deepcopy(payload))
        return Path("history/test.json")

    def increment_run_stats(self, completed_loops):
        self.completed_loops = completed_loops
        return {"completed_loops": completed_loops}


class FakeSil:
    def __init__(self):
        self.loop_logs = []
        self.errors = []

    def log_loop_completion(self, loop_index):
        self.loop_logs.append(loop_index)
        return {"loop_index": loop_index}

    def record_error(self, error, *, code=None, context=None):
        entry = {
            "error": str(error),
            "error_code": code or "UNEXPECTED_ERROR",
            "display": str(error),
            "context": context or {},
        }
        self.errors.append(entry)
        return entry


class FakeGeminiClient:
    RESPONSES = {
        "rune_draft": "[초안]\n서고의 문장이 천천히 깨어납니다.",
        "canon_review": "[피드백]\n이상 없음.",
        "echo_comment": "[댓글]\n좋고 몰입돼. 다음 장면이 궁금해.",
        "rune_final": "[최종본]\n조금 더 선명해진 최종본입니다.",
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
            "raw": {
                "persona": persona,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "temperature": temperature,
            },
        }


class PromptVersioningTests(unittest.IsolatedAsyncioTestCase):
    async def test_runner_persists_prompt_versions_in_state_and_history(self):
        repository = FakeRepository()
        sil = FakeSil()
        runner = LoopRunner(repository, sil, FakeGeminiClient())

        await runner.start(
            payload={
                "title": "prompt meta",
                "plot": "잠든 문장을 깨우는 장면",
                "settings": {"base": "기본 설정", "spoiler": "스포일러", "style": "문체"},
                "previous_context": {
                    "mode": "hybrid",
                    "recent_full_text": "이전 전문",
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
        self.assertEqual(
            iteration["prompts"]["rune_draft"]["version"],
            prompt_meta("rune_draft")["version"],
        )
        self.assertEqual(
            iteration["prompts"]["canon_review"]["version"],
            prompt_meta("canon_review")["version"],
        )
        self.assertEqual(
            iteration["prompts"]["echo_comment"]["version"],
            prompt_meta("echo_comment")["version"],
        )
        self.assertEqual(
            iteration["prompts"]["rune_final"]["version"],
            prompt_meta("rune_final")["version"],
        )
        self.assertEqual(repository.history_entries[0]["prompts"], iteration["prompts"])
        self.assertEqual(iteration["usage_summary"]["call_count"], 4)
        self.assertGreater(iteration["usage_summary"]["total_tokens"], 0)
        self.assertGreater(iteration["usage_summary"]["total_cost_usd"], 0)
        self.assertEqual(
            repository.history_entries[0]["usage_summary"], iteration["usage_summary"]
        )
        self.assertEqual(repository.state["usage_summary"]["call_count"], 4)
        self.assertEqual(repository.completed_loops, 1)
        self.assertEqual(sil.loop_logs, [1])

    def test_estimate_prompt_request_uses_registry_version(self):
        prompt = build_estimate_prompt_request(
            "canon_review",
            affinity_stage="distant",
            plot="테스트 플롯",
            settings={"base": "기본", "spoiler": "반전", "style": "문체"},
            previous_context={"mode": "summary", "recent_full_text": "", "summary": "요약"},
        )

        self.assertEqual(prompt["meta"], prompt_meta("canon_review"))
        self.assertIn("설정_스포일러", prompt["user_prompt"])
        self.assertIn("당신은 카논입니다.", prompt["system_prompt"])

    async def test_runner_recovers_interrupted_run_state(self):
        repository = FakeRepository()
        repository.state.update(
            {
                "status": "running",
                "run_id": "restart123",
                "stage": "review",
                "message": "카논과 에코가 초안을 읽고 있습니다.",
                "current_iteration": 2,
                "config": {
                    "max_loops": 3,
                    "early_stop_enabled": True,
                    "parallel_feedback": True,
                },
                "cards": [
                    {"loop_index": 1, "status": "done"},
                    {"loop_index": 2, "status": "active"},
                    {"loop_index": 3, "status": "pending"},
                ],
                "iterations": [
                    {
                        "loop_index": 1,
                        "status": "done",
                        "draft": "[초안] 1",
                        "feedback": "[피드백] 1",
                        "comment": "[댓글] 1",
                        "final": "[최종본] 1",
                        "draft_summary": "",
                        "feedback_summary": "",
                        "comment_summary": "",
                        "final_summary": "",
                        "quality": {"should_stop": False, "score": 0, "reasons": []},
                        "history_file": "history-1.json",
                        "usage": {},
                        "prompts": {},
                    },
                    {
                        "loop_index": 2,
                        "status": "review_ready",
                        "draft": "[초안] 2",
                        "feedback": "[피드백] 2",
                        "comment": "[댓글] 2",
                        "final": "",
                        "draft_summary": "",
                        "feedback_summary": "",
                        "comment_summary": "",
                        "final_summary": "",
                        "quality": None,
                        "history_file": None,
                        "usage": {},
                        "prompts": {},
                    },
                ],
                "active_persona": "canon_echo",
                "started_at": "2026-03-21T10:00:00Z",
                "completed_at": None,
                "updated_at": "2026-03-21T10:00:03Z",
                "last_quality": None,
                "error": None,
            }
        )
        sil = FakeSil()
        runner = LoopRunner(repository, sil, FakeGeminiClient())

        recovered = runner.recover_interrupted_run()

        self.assertIsNotNone(recovered)
        self.assertEqual(recovered["status"], "error")
        self.assertEqual(recovered["stage"], "interrupted")
        self.assertEqual(recovered["active_persona"], "sil")
        self.assertEqual(
            recovered["message"],
            "서버가 다시 깨어나는 동안 이전 루프가 끊겼습니다. 마지막 저장 지점까지만 남겼습니다.",
        )
        self.assertEqual(recovered["cards"][0]["status"], "done")
        self.assertEqual(recovered["cards"][1]["status"], "cancelled")
        self.assertEqual(recovered["cards"][2]["status"], "skipped")
        self.assertEqual(recovered["iterations"][0]["status"], "done")
        self.assertEqual(recovered["iterations"][1]["status"], "interrupted")
        self.assertEqual(recovered["error"]["error_code"], "RUN_INTERRUPTED_ON_RESTART")
        self.assertEqual(sil.errors[0]["context"]["run_id"], "restart123")
        self.assertEqual(sil.errors[0]["context"]["stage"], "review")
        self.assertEqual(sil.errors[0]["context"]["current_iteration"], 2)


if __name__ == "__main__":
    unittest.main()
