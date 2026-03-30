from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import APP_CONFIG
from backend.loop.runner import LoopRunner
from backend.models import CostEstimateRequest, RunRequest, SettingsUpdateRequest
from backend.pricing import enrich_usage, scale_usage_summary, summarize_usage_records
from backend.personas.client import GeminiClient, GeminiClientError
from backend.personas.prompts import build_estimate_prompt_request
from backend.personas.sil import SilMaintainer
from backend.storage.repository import Repository
from backend.utils import estimate_tokens, utc_now_iso


repository = Repository()
repository.ensure_storage()
sil = SilMaintainer(repository)
gemini_client = GeminiClient()
runner = LoopRunner(repository, sil, gemini_client)

app = FastAPI(title="Sleeping Archive")
app.mount("/static", StaticFiles(directory=str(repository.frontend_dir)), name="static")


@app.on_event("startup")
async def startup_event() -> None:
    runner.recover_interrupted_run()


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request, error: Exception
) -> JSONResponse:
    sil_entry = sil.record_error(error, context={"path": str(request.url.path)})
    return JSONResponse(
        status_code=500,
        content={
            "detail": "서고에 균열이 발생했습니다. Sil 로그를 확인하세요.",
            "sil": sil_entry,
        },
    )


@app.get("/", response_class=FileResponse)
async def index() -> FileResponse:
    return FileResponse(repository.frontend_dir / "index.html")


@app.get("/api/state")
async def get_state() -> dict[str, Any]:
    meta, greeting, days_away, _ = repository.record_visit()
    if days_away > 0:
        sil.log_absence(days_away)
    return {
        "greeting": greeting,
        "settings": repository.get_settings(),
        "loop_state": repository.get_loop_state(),
        "sil_log": repository.get_sil_log(),
        "history": repository.list_history(),
        "meta": meta,
        "service": {
            "mode": gemini_client.mode,
            "model": gemini_client.model,
            "configured": bool(APP_CONFIG.gemini_api_key),
            "timeout_seconds": APP_CONFIG.request_timeout_seconds,
            "retry_policy": {
                "max_retries": APP_CONFIG.gemini_max_retries,
                "base_delay_seconds": APP_CONFIG.gemini_retry_base_delay_seconds,
                "max_delay_seconds": APP_CONFIG.gemini_retry_max_delay_seconds,
            },
            "generated_at": utc_now_iso(),
        },
    }


@app.get("/api/loop-state")
async def get_loop_state() -> dict[str, Any]:
    return repository.get_loop_state()


@app.get("/api/history")
async def get_history() -> list[dict[str, Any]]:
    return repository.list_history()


@app.get("/api/sil-log")
async def get_sil_log() -> list[dict[str, Any]]:
    return repository.get_sil_log()


@app.put("/api/settings")
async def update_settings(payload: SettingsUpdateRequest) -> dict[str, Any]:
    settings = repository.save_settings(model_to_dict(payload.settings))
    return {"settings": settings}


@app.post("/api/cost-estimate")
async def estimate_cost(payload: CostEstimateRequest) -> dict[str, Any]:
    settings = resolve_settings(payload.settings)
    loop_config = runner.normalize_loop_config(model_to_dict(payload.loop_config))
    previous_context = model_to_dict(payload.previous_context)
    affinity_stage = repository.get_meta().get("affinity_stage", "distant")

    prompt_bundle = [
        build_estimate_prompt_request(
            prompt_key,
            affinity_stage=affinity_stage,
            plot=payload.plot,
            settings=settings,
            previous_context=previous_context,
        )
        for prompt_key in ("rune_draft", "canon_review", "echo_comment", "rune_final")
    ]

    tokens_per_call: list[dict[str, Any]] = []
    per_loop_usages: list[dict[str, Any]] = []
    for prompt in prompt_bundle:
        persona_name = prompt["meta"]["key"]
        if gemini_client.mode == "mock":
            prompt_tokens = estimate_tokens(prompt["system_prompt"]) + estimate_tokens(
                prompt["user_prompt"]
            )
            estimate_mode = "heuristic"
        else:
            try:
                prompt_tokens = await gemini_client.count_tokens(
                    system_prompt=prompt["system_prompt"],
                    user_prompt=prompt["user_prompt"],
                )
                estimate_mode = "api"
            except GeminiClientError:
                prompt_tokens = estimate_tokens(prompt["system_prompt"]) + estimate_tokens(
                    prompt["user_prompt"]
                )
                estimate_mode = "heuristic"

        if persona_name == "canon_review":
            output_tokens = max(220, prompt_tokens // 6)
        elif persona_name == "echo_comment":
            output_tokens = max(180, prompt_tokens // 7)
        elif persona_name == "rune_final":
            output_tokens = max(900, prompt_tokens // 2)
        else:
            output_tokens = max(700, prompt_tokens // 3)

        usage = enrich_usage(
            {
                "prompt_tokens": prompt_tokens,
                "candidate_tokens": output_tokens,
                "thoughts_tokens": 0,
                "total_tokens": prompt_tokens + output_tokens,
            },
            source="estimate",
            approximate=estimate_mode != "api",
        )
        per_loop_usages.append(usage)
        tokens_per_call.append(
            {
                "persona": persona_name,
                "prompt_version": prompt["meta"]["version"],
                "prompt_tokens": usage["prompt_tokens"],
                "estimated_output_tokens": usage["output_tokens"],
                "output_tokens": usage["output_tokens"],
                "total_tokens": usage["total_tokens"],
                "mode": estimate_mode,
                "pricing_tier": usage["pricing_tier"],
                "input_cost_usd": usage["input_cost_usd"],
                "output_cost_usd": usage["output_cost_usd"],
                "estimated_cost_usd": usage["total_cost_usd"],
            }
        )

    per_loop_summary = summarize_usage_records(per_loop_usages)
    total_summary = scale_usage_summary(per_loop_summary, loop_config["max_loops"])

    return {
        "tokens_per_call": tokens_per_call,
        "per_loop": {
            "prompt_tokens": per_loop_summary["prompt_tokens"],
            "estimated_output_tokens": per_loop_summary["output_tokens"],
            "output_tokens": per_loop_summary["output_tokens"],
            "total_tokens": per_loop_summary["total_tokens"],
            "input_cost_usd": per_loop_summary["input_cost_usd"],
            "output_cost_usd": per_loop_summary["output_cost_usd"],
            "estimated_cost_usd": per_loop_summary["total_cost_usd"],
            "approximate": per_loop_summary["approximate"],
        },
        "total": {
            "prompt_tokens": total_summary["prompt_tokens"],
            "estimated_output_tokens": total_summary["output_tokens"],
            "output_tokens": total_summary["output_tokens"],
            "total_tokens": total_summary["total_tokens"],
            "input_cost_usd": total_summary["input_cost_usd"],
            "output_cost_usd": total_summary["output_cost_usd"],
            "estimated_cost_usd": total_summary["total_cost_usd"],
            "approximate": total_summary["approximate"],
        },
        "loop_config": loop_config,
    }


@app.post("/api/run")
async def start_run(payload: RunRequest) -> dict[str, Any]:
    if repository.get_loop_state().get("status") == "running":
        raise HTTPException(status_code=409, detail="이미 실행 중인 루프가 있습니다.")

    resolved_settings = resolve_settings(payload.settings)
    repository.save_settings(resolved_settings)
    meta = repository.get_meta()
    state = await runner.start(
        payload={
            **model_to_dict(payload),
            "settings": resolved_settings,
            "loop_config": model_to_dict(payload.loop_config),
            "previous_context": model_to_dict(payload.previous_context),
        },
        affinity_stage=meta.get("affinity_stage", "distant"),
    )
    return {"run_id": state["run_id"], "loop_state": state}


@app.post("/api/run/cancel")
async def cancel_run() -> dict[str, Any]:
    try:
        state = await runner.cancel()
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"loop_state": state}


def model_to_dict(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def resolve_settings(payload: Any) -> dict[str, Any]:
    saved = repository.get_settings()
    if payload is None:
        return saved
    incoming = model_to_dict(payload)
    return {
        "base": incoming.get("base", saved.get("base", "")),
        "spoiler": incoming.get("spoiler", saved.get("spoiler", "")),
        "style": incoming.get("style", saved.get("style", "")),
    }
