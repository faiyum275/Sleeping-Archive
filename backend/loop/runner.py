from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any
from uuid import uuid4

from backend.config import DEFAULT_LOOP_STATE
from backend.loop.quality_check import evaluate_quality
from backend.pricing import enrich_usage, summarize_usage_records
from backend.personas import canon, echo, rune
from backend.personas.common import summarize_for_ui
from backend.personas.sil import SilMaintainer
from backend.storage.repository import Repository
from backend.utils import clamp, utc_now_iso


class LoopRunner:
    def __init__(
        self,
        repository: Repository,
        sil: SilMaintainer,
        gemini_client: Any,
    ) -> None:
        self.repository = repository
        self.sil = sil
        self.gemini_client = gemini_client
        self._task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    async def start(self, payload: dict[str, Any], affinity_stage: str) -> dict[str, Any]:
        async with self._lock:
            if self._task and not self._task.done():
                raise RuntimeError("이미 실행 중인 루프가 있습니다.")

            config = self.normalize_loop_config(payload.get("loop_config", {}))
            run_id = uuid4().hex[:12]
            state = deepcopy(DEFAULT_LOOP_STATE)
            state.update(
                {
                    "status": "running",
                    "run_id": run_id,
                    "stage": "queued",
                    "message": "서고가 촛불을 밝히고 첫 장을 넘기고 있습니다.",
                    "title": payload.get("title", "").strip(),
                    "plot": payload.get("plot", "").strip(),
                    "config": config,
                    "cards": [
                        {"loop_index": index, "status": "pending"}
                        for index in range(1, config["max_loops"] + 1)
                    ],
                    "iterations": [],
                    "active_persona": None,
                    "started_at": utc_now_iso(),
                    "completed_at": None,
                    "updated_at": utc_now_iso(),
                    "last_quality": None,
                    "error": None,
                }
            )
            self.repository.save_loop_state(state)
            self._task = asyncio.create_task(
                self._execute_run(
                    run_id=run_id,
                    payload=deepcopy(payload),
                    affinity_stage=affinity_stage,
                )
            )
            return state

    def recover_interrupted_run(self) -> dict[str, Any] | None:
        state = self.repository.get_loop_state()
        if state.get("status") != "running":
            return None

        previous_stage = state.get("stage")
        current_iteration = int(state.get("current_iteration") or 0)
        self._finalize_interrupted_cards(state, current_iteration=current_iteration)
        self._mark_interrupted_iteration(state, current_iteration=current_iteration)
        self._refresh_usage_summaries(state)

        sil_entry = self.sil.record_error(
            RuntimeError("Previous background loop interrupted by restart."),
            code="RUN_INTERRUPTED_ON_RESTART",
            context={
                "run_id": state.get("run_id"),
                "stage": previous_stage,
                "current_iteration": current_iteration,
            },
        )

        state["status"] = "error"
        state["stage"] = "interrupted"
        state["active_persona"] = "sil"
        state["message"] = (
            "서버가 다시 깨어나는 동안 이전 루프가 끊겼습니다. "
            "마지막 저장 지점까지만 남겼습니다."
        )
        state["error"] = sil_entry
        state["completed_at"] = utc_now_iso()
        self.repository.save_loop_state(state)
        return state

    async def cancel(self) -> dict[str, Any]:
        async with self._lock:
            state = self.repository.get_loop_state()
            if not self._task or self._task.done() or state.get("status") != "running":
                raise RuntimeError("취소할 실행 중인 루프가 없습니다.")

            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            return self.repository.get_loop_state()

    def normalize_loop_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "max_loops": clamp(int(payload.get("max_loops", 3) or 3), 1, 10),
            "early_stop_enabled": bool(payload.get("early_stop_enabled", True)),
            "parallel_feedback": bool(payload.get("parallel_feedback", True)),
        }

    async def _execute_run(
        self,
        *,
        run_id: str,
        payload: dict[str, Any],
        affinity_stage: str,
    ) -> None:
        state = self.repository.get_loop_state()
        plot = payload.get("plot", "").strip()
        settings = payload.get("settings", {})
        previous_context = payload.get("previous_context", {})
        config = state["config"]
        completed_loops = 0

        try:
            for loop_index in range(1, config["max_loops"] + 1):
                completed_loops = loop_index
                self._mark_card(state, loop_index, "active")
                self._set_stage(
                    state,
                    stage="rune_draft",
                    active_persona="rune",
                    message="루네가 실마리를 문장으로 잇고 있습니다.",
                    current_iteration=loop_index,
                )
                draft = await rune.create_draft(
                    self.gemini_client,
                    plot=plot,
                    settings=settings,
                    previous_context=previous_context,
                    iteration=loop_index,
                    affinity_stage=affinity_stage,
                )
                iteration_entry = self._ensure_iteration(state, loop_index)
                iteration_entry["draft"] = draft["text"]
                iteration_entry["draft_summary"] = summarize_for_ui(draft["text"])
                iteration_entry["usage"]["rune_draft"] = self._normalize_stage_usage(
                    draft["usage"]
                )
                iteration_entry["prompts"]["rune_draft"] = draft.get("prompt")
                iteration_entry["status"] = "draft_ready"
                self._refresh_usage_summaries(state)
                self.repository.save_loop_state(state)

                self._set_stage(
                    state,
                    stage="review",
                    active_persona="canon_echo"
                    if config["parallel_feedback"]
                    else "canon",
                    message="카논과 에코가 각자의 방식으로 초안을 읽고 있습니다.",
                )
                if config["parallel_feedback"]:
                    feedback, comment = await asyncio.gather(
                        canon.review_draft(
                            self.gemini_client,
                            draft=draft["text"],
                            settings=settings,
                            previous_context=previous_context,
                            iteration=loop_index,
                            affinity_stage=affinity_stage,
                        ),
                        echo.react_to_draft(
                            self.gemini_client,
                            draft=draft["text"],
                            iteration=loop_index,
                            affinity_stage=affinity_stage,
                        ),
                    )
                else:
                    feedback = await canon.review_draft(
                        self.gemini_client,
                        draft=draft["text"],
                        settings=settings,
                        previous_context=previous_context,
                        iteration=loop_index,
                        affinity_stage=affinity_stage,
                    )
                    comment = await echo.react_to_draft(
                        self.gemini_client,
                        draft=draft["text"],
                        iteration=loop_index,
                        affinity_stage=affinity_stage,
                    )

                iteration_entry["feedback"] = feedback["text"]
                iteration_entry["feedback_structured"] = feedback.get("structured")
                iteration_entry["comment"] = comment["text"]
                iteration_entry["comment_structured"] = comment.get("structured")
                iteration_entry["feedback_summary"] = summarize_for_ui(feedback["text"])
                iteration_entry["comment_summary"] = summarize_for_ui(comment["text"])
                iteration_entry["usage"]["canon"] = self._normalize_stage_usage(
                    feedback["usage"]
                )
                iteration_entry["usage"]["echo"] = self._normalize_stage_usage(
                    comment["usage"]
                )
                iteration_entry["prompts"]["canon_review"] = feedback.get("prompt")
                iteration_entry["prompts"]["echo_comment"] = comment.get("prompt")
                iteration_entry["status"] = "review_ready"
                self._refresh_usage_summaries(state)
                self.repository.save_loop_state(state)

                self._set_stage(
                    state,
                    stage="rune_final",
                    active_persona="rune",
                    message="루네가 피드백과 댓글을 엮어 최종본을 다듬고 있습니다.",
                )
                final = await rune.create_final(
                    self.gemini_client,
                    plot=plot,
                    settings=settings,
                    previous_context=previous_context,
                    draft=draft["text"],
                    feedback=feedback["text"],
                    comment=comment["text"],
                    iteration=loop_index,
                    affinity_stage=affinity_stage,
                )

                quality = evaluate_quality(feedback["text"], comment["text"])
                iteration_entry["final"] = final["text"]
                iteration_entry["final_summary"] = summarize_for_ui(final["text"])
                iteration_entry["quality"] = quality
                iteration_entry["usage"]["rune_final"] = self._normalize_stage_usage(
                    final["usage"]
                )
                iteration_entry["prompts"]["rune_final"] = final.get("prompt")
                iteration_entry["status"] = "done"
                state["last_quality"] = quality
                self._refresh_usage_summaries(state)

                history_payload = {
                    "run_id": run_id,
                    "loop_index": loop_index,
                    "title": state["title"] or "untitled",
                    "created_at": utc_now_iso(),
                    "plot": plot,
                    "settings_snapshot": settings,
                    "previous_context": previous_context,
                    "outputs": {
                        "draft": draft["text"],
                        "feedback": feedback["text"],
                        "comment": comment["text"],
                        "final": final["text"],
                    },
                    "feedback_structured": feedback.get("structured"),
                    "comment_structured": comment.get("structured"),
                    "quality": quality,
                    "usage": iteration_entry["usage"],
                    "usage_summary": deepcopy(iteration_entry["usage_summary"]),
                    "prompts": deepcopy(iteration_entry["prompts"]),
                }
                history_path = self.repository.save_history_entry(history_payload)
                iteration_entry["history_file"] = history_path.name
                self._mark_card(state, loop_index, "done")
                self.sil.log_loop_completion(loop_index)
                self.repository.save_loop_state(state)

                if config["early_stop_enabled"] and quality["should_stop"]:
                    for remaining in range(loop_index + 1, config["max_loops"] + 1):
                        self._mark_card(state, remaining, "skipped")
                    state["message"] = "카논과 에코가 모두 고개를 끄덕였습니다. 이번 루프에서 정리합니다."
                    break

            state["status"] = "completed"
            state["stage"] = "completed"
            state["active_persona"] = None
            state["completed_at"] = utc_now_iso()
            state["updated_at"] = utc_now_iso()
            self.repository.save_loop_state(state)
            self.repository.increment_run_stats(completed_loops)
        except asyncio.CancelledError:
            current_iteration = int(state.get("current_iteration") or 0)
            if current_iteration:
                self._mark_card(state, current_iteration, "cancelled")
                for remaining in range(current_iteration + 1, config["max_loops"] + 1):
                    self._mark_card(state, remaining, "skipped")

            state["status"] = "cancelled"
            state["stage"] = "cancelled"
            state["active_persona"] = None
            state["message"] = "저자가 루프를 멈췄습니다. 여기까지의 흔적만 남깁니다."
            state["error"] = None
            state["completed_at"] = utc_now_iso()
            state["updated_at"] = utc_now_iso()
            self.repository.save_loop_state(state)
        except Exception as error:
            sil_entry = self.sil.record_error(
                error,
                context={"run_id": run_id, "stage": state.get("stage")},
            )
            state["status"] = "error"
            state["stage"] = "error"
            state["active_persona"] = "sil"
            state["message"] = "실이 균열을 붙잡고 있습니다. 로그를 확인하세요."
            state["error"] = sil_entry
            state["completed_at"] = utc_now_iso()
            self.repository.save_loop_state(state)
        finally:
            self._task = None

    def _ensure_iteration(self, state: dict[str, Any], loop_index: int) -> dict[str, Any]:
        while len(state["iterations"]) < loop_index:
            next_index = len(state["iterations"]) + 1
            state["iterations"].append(
                {
                    "loop_index": next_index,
                    "status": "pending",
                    "draft": "",
                    "feedback": "",
                    "feedback_structured": None,
                    "comment": "",
                    "comment_structured": None,
                    "final": "",
                    "draft_summary": "",
                    "feedback_summary": "",
                    "comment_summary": "",
                    "final_summary": "",
                    "quality": None,
                    "history_file": None,
                    "usage": {},
                    "usage_summary": None,
                    "prompts": {},
                }
            )
        return state["iterations"][loop_index - 1]

    def _mark_card(self, state: dict[str, Any], loop_index: int, status: str) -> None:
        for card in state["cards"]:
            if card["loop_index"] == loop_index:
                card["status"] = status
                break

    def _finalize_interrupted_cards(
        self, state: dict[str, Any], *, current_iteration: int
    ) -> None:
        active_found = False
        for card in state.get("cards", []):
            if card.get("status") == "active":
                card["status"] = "cancelled"
                active_found = True
            elif card.get("status") == "pending":
                card["status"] = "skipped"

        if current_iteration and not active_found:
            self._mark_card(state, current_iteration, "cancelled")

    def _mark_interrupted_iteration(
        self, state: dict[str, Any], *, current_iteration: int
    ) -> None:
        if not current_iteration:
            return

        for iteration in state.get("iterations", []):
            if iteration.get("loop_index") != current_iteration:
                continue
            if iteration.get("status") in {"done", "cancelled", "skipped"}:
                return
            iteration["status"] = "interrupted"
            return

    def _normalize_stage_usage(self, usage: dict[str, Any] | None) -> dict[str, Any]:
        source = getattr(self.gemini_client, "mode", None)
        return enrich_usage(usage, source=source)

    def _refresh_usage_summaries(self, state: dict[str, Any]) -> None:
        all_usage_records: list[dict[str, Any]] = []

        for iteration in state.get("iterations", []):
            usage_map = iteration.get("usage") or {}
            normalized_usage = {
                stage_key: self._normalize_stage_usage(stage_usage)
                for stage_key, stage_usage in usage_map.items()
                if isinstance(stage_usage, dict)
            }
            iteration["usage"] = normalized_usage
            all_usage_records.extend(normalized_usage.values())

            usage_summary = summarize_usage_records(normalized_usage.values())
            iteration["usage_summary"] = (
                usage_summary if usage_summary["call_count"] else None
            )

        state_summary = summarize_usage_records(all_usage_records)
        state["usage_summary"] = state_summary if state_summary["call_count"] else None

    def _set_stage(
        self,
        state: dict[str, Any],
        *,
        stage: str,
        active_persona: str | None,
        message: str,
        current_iteration: int | None = None,
    ) -> None:
        state["stage"] = stage
        state["active_persona"] = active_persona
        state["message"] = message
        if current_iteration is not None:
            state["current_iteration"] = current_iteration
        state["updated_at"] = utc_now_iso()
        self.repository.save_loop_state(state)
