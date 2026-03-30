from __future__ import annotations

import asyncio
from pathlib import Path
import shutil
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

import backend.main as app_module
from backend.loop.runner import LoopRunner
from backend.personas.client import GeminiClient
from backend.personas.sil import SilMaintainer
from backend.storage.repository import Repository


TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp_test"


def build_temp_repository(root: Path) -> Repository:
    repository = Repository()
    storage_dir = root / "storage"
    repository.storage_dir = storage_dir
    repository.history_dir = storage_dir / "history"
    repository.settings_path = storage_dir / "settings.json"
    repository.loop_state_path = storage_dir / "loop_state.json"
    repository.sil_log_path = storage_dir / "sil_log.json"
    repository.app_meta_path = storage_dir / "app_meta.json"
    repository.ensure_storage()
    return repository


class MockModeSmokeTests(unittest.TestCase):
    def test_mock_mode_run_flow_completes_and_persists_outputs(self):
        payload = {
            "title": "mock smoke",
            "plot": "잠든 서고의 문장이 깨어나는 첫 장면",
            "settings": {
                "base": "기본 설정",
                "spoiler": "",
                "style": "문체 설정",
            },
            "previous_context": {
                "mode": "hybrid",
                "recent_full_text": "이전 원문",
                "summary": "이전 요약",
            },
            "loop_config": {
                "max_loops": 2,
                "early_stop_enabled": True,
                "parallel_feedback": True,
            },
        }

        TEST_TEMP_ROOT.mkdir(exist_ok=True)

        temp_dir = TEST_TEMP_ROOT / f"run_{uuid4().hex}"
        temp_dir.mkdir()

        try:
            repository = build_temp_repository(temp_dir)
            gemini_client = GeminiClient()
            gemini_client.api_key = ""
            gemini_client.mode = "mock"
            sil = SilMaintainer(repository)
            runner = LoopRunner(repository, sil, gemini_client)

            with patch.multiple(
                app_module,
                repository=repository,
                sil=sil,
                gemini_client=gemini_client,
                runner=runner,
            ):
                with TestClient(app_module.app) as client:
                    state_response = client.get("/api/state")
                    self.assertEqual(state_response.status_code, 200)
                    state_payload = state_response.json()
                    self.assertEqual(state_payload["service"]["mode"], "mock")
                    self.assertEqual(state_payload["loop_state"]["status"], "idle")

                    estimate_response = client.post("/api/cost-estimate", json=payload)
                    self.assertEqual(estimate_response.status_code, 200)
                    estimate = estimate_response.json()
                    self.assertEqual(len(estimate["tokens_per_call"]), 4)
                    self.assertTrue(
                        all(item["mode"] == "heuristic" for item in estimate["tokens_per_call"])
                    )
                    self.assertEqual(estimate["loop_config"]["max_loops"], 2)

                    run_response = client.post("/api/run", json=payload)
                    self.assertEqual(run_response.status_code, 200)
                    started = run_response.json()
                    self.assertEqual(started["loop_state"]["status"], "running")

                    loop_state = None
                    for _ in range(100):
                        loop_state = client.get("/api/loop-state").json()
                        if loop_state["status"] != "running":
                            break
                        time.sleep(0.05)

                    self.assertIsNotNone(loop_state)
                    self.assertEqual(loop_state["status"], "completed")
                    self.assertEqual(loop_state["stage"], "completed")
                    self.assertIsNone(loop_state["active_persona"])
                    self.assertEqual(loop_state["cards"][0]["status"], "done")
                    self.assertEqual(loop_state["cards"][1]["status"], "skipped")
                    self.assertEqual(len(loop_state["iterations"]), 1)
                    self.assertEqual(loop_state["iterations"][0]["status"], "done")
                    self.assertEqual(loop_state["usage_summary"]["call_count"], 4)
                    self.assertGreater(loop_state["usage_summary"]["total_tokens"], 0)
                    self.assertGreater(loop_state["usage_summary"]["total_cost_usd"], 0)
                    self.assertTrue(loop_state["last_quality"]["should_stop"])
                    self.assertIn("[최종본]", loop_state["iterations"][0]["final"])
                    self.assertTrue(loop_state["iterations"][0]["history_file"])
                    self.assertEqual(
                        loop_state["iterations"][0]["usage_summary"]["call_count"], 4
                    )

                    history_response = client.get("/api/history")
                    self.assertEqual(history_response.status_code, 200)
                    history = history_response.json()
                    self.assertEqual(len(history), 1)
                    self.assertEqual(history[0]["run_id"], started["run_id"])
                    self.assertEqual(history[0]["loop_index"], 1)
                    self.assertEqual(history[0]["usage_summary"]["call_count"], 4)
                    self.assertGreater(history[0]["usage_summary"]["total_cost_usd"], 0)
                    self.assertTrue(history[0]["quality"]["should_stop"])
                    self.assertIn("[초안]", history[0]["outputs"]["draft"])
                    self.assertIn("[최종본]", history[0]["outputs"]["final"])

                    sil_response = client.get("/api/sil-log")
                    self.assertEqual(sil_response.status_code, 200)
                    sil_log = sil_response.json()
                    self.assertTrue(any(entry["kind"] == "loop" for entry in sil_log))
                    self.assertFalse(any(entry["kind"] == "error" for entry in sil_log))

                    self.assertEqual(len(list(repository.history_dir.glob("*.json"))), 1)
                    self.assertEqual(repository.get_settings()["base"], "기본 설정")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_cancel_endpoint_stops_running_loop(self):
        payload = {
            "title": "cancel smoke",
            "plot": "서고가 갑자기 닫히기 전에 작업을 멈추는 장면",
            "settings": {
                "base": "기본 설정",
                "spoiler": "",
                "style": "문체 설정",
            },
            "previous_context": {
                "mode": "summary",
                "recent_full_text": "",
                "summary": "이전 요약",
            },
            "loop_config": {
                "max_loops": 3,
                "early_stop_enabled": False,
                "parallel_feedback": True,
            },
        }

        TEST_TEMP_ROOT.mkdir(exist_ok=True)

        temp_dir = TEST_TEMP_ROOT / f"run_{uuid4().hex}"
        temp_dir.mkdir()

        try:
            repository = build_temp_repository(temp_dir)
            gemini_client = SlowGeminiClient()
            sil = SilMaintainer(repository)
            runner = LoopRunner(repository, sil, gemini_client)

            with patch.multiple(
                app_module,
                repository=repository,
                sil=sil,
                gemini_client=gemini_client,
                runner=runner,
            ):
                with TestClient(app_module.app) as client:
                    run_response = client.post("/api/run", json=payload)
                    self.assertEqual(run_response.status_code, 200)

                    loop_state = None
                    for _ in range(40):
                        loop_state = client.get("/api/loop-state").json()
                        if loop_state["status"] == "running" and loop_state["stage"] == "rune_draft":
                            break
                        time.sleep(0.05)

                    self.assertIsNotNone(loop_state)
                    self.assertEqual(loop_state["status"], "running")

                    cancel_response = client.post("/api/run/cancel")
                    self.assertEqual(cancel_response.status_code, 200)
                    cancelled = cancel_response.json()["loop_state"]
                    self.assertEqual(cancelled["status"], "cancelled")
                    self.assertEqual(cancelled["stage"], "cancelled")
                    self.assertIsNone(cancelled["active_persona"])
                    self.assertEqual(cancelled["cards"][0]["status"], "cancelled")
                    self.assertEqual(cancelled["cards"][1]["status"], "skipped")
                    self.assertEqual(cancelled["cards"][2]["status"], "skipped")

                    persisted = client.get("/api/loop-state").json()
                    self.assertEqual(persisted["status"], "cancelled")

                    history = client.get("/api/history").json()
                    self.assertEqual(history, [])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_startup_recovers_previous_running_state(self):
        TEST_TEMP_ROOT.mkdir(exist_ok=True)

        temp_dir = TEST_TEMP_ROOT / f"run_{uuid4().hex}"
        temp_dir.mkdir()

        try:
            repository = build_temp_repository(temp_dir)
            persisted = repository.get_loop_state()
            persisted.update(
                {
                    "status": "running",
                    "run_id": "restart-smoke",
                    "stage": "review",
                    "message": "카논과 에코가 초안을 읽고 있습니다.",
                    "title": "restart smoke",
                    "plot": "재시작 전에 멈춘 작업",
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
                            "history_file": "restart_loop01.json",
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
            repository.save_loop_state(persisted)

            gemini_client = GeminiClient()
            gemini_client.api_key = ""
            gemini_client.mode = "mock"
            sil = SilMaintainer(repository)
            runner = LoopRunner(repository, sil, gemini_client)

            with patch.multiple(
                app_module,
                repository=repository,
                sil=sil,
                gemini_client=gemini_client,
                runner=runner,
            ):
                with TestClient(app_module.app) as client:
                    loop_state = client.get("/api/loop-state").json()
                    self.assertEqual(loop_state["status"], "error")
                    self.assertEqual(loop_state["stage"], "interrupted")
                    self.assertEqual(loop_state["active_persona"], "sil")
                    self.assertEqual(loop_state["cards"][0]["status"], "done")
                    self.assertEqual(loop_state["cards"][1]["status"], "cancelled")
                    self.assertEqual(loop_state["cards"][2]["status"], "skipped")
                    self.assertEqual(loop_state["iterations"][1]["status"], "interrupted")
                    self.assertEqual(
                        loop_state["error"]["error_code"], "RUN_INTERRUPTED_ON_RESTART"
                    )

                    sil_log = client.get("/api/sil-log").json()
                    self.assertTrue(
                        any(
                            entry.get("error_code") == "RUN_INTERRUPTED_ON_RESTART"
                            for entry in sil_log
                        )
                    )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class SlowGeminiClient:
    RESPONSES = {
        "rune_draft": "[초안]\n느리게 열리는 초안입니다.",
        "canon_review": "[피드백]\n이상 없음.",
        "echo_comment": "[댓글]\n계속 읽고 싶어요.",
        "rune_final": "[최종본]\n정리된 최종본입니다.",
    }

    def __init__(self) -> None:
        self.mode = "mock"
        self.model = "mock-slow"

    async def count_tokens(self, *, system_prompt, user_prompt):
        return 100

    async def generate_text(self, *, persona, system_prompt, user_prompt, temperature):
        await asyncio.sleep(10)
        text = self.RESPONSES[persona]
        return {
            "text": text,
            "usage": {
                "prompt_tokens": 10,
                "candidate_tokens": 20,
                "thoughts_tokens": 0,
                "total_tokens": 30,
            },
            "raw": {"mode": "mock"},
        }


if __name__ == "__main__":
    unittest.main()
