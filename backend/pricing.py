from __future__ import annotations

from typing import Any, Iterable

from backend.config import APP_CONFIG


def usage_pricing_tier(prompt_tokens: int) -> str:
    return (
        "large_context"
        if int(prompt_tokens or 0) > APP_CONFIG.pricing_threshold_tokens
        else "standard"
    )


def calculate_usage_costs(prompt_tokens: int, output_tokens: int) -> dict[str, Any]:
    tier = usage_pricing_tier(prompt_tokens)
    prompt_rate = (
        APP_CONFIG.input_cost_per_1m_large
        if tier == "large_context"
        else APP_CONFIG.input_cost_per_1m
    )
    output_rate = (
        APP_CONFIG.output_cost_per_1m_large
        if tier == "large_context"
        else APP_CONFIG.output_cost_per_1m
    )
    input_cost = int(prompt_tokens or 0) / 1_000_000 * prompt_rate
    output_cost = int(output_tokens or 0) / 1_000_000 * output_rate
    return {
        "pricing_tier": tier,
        "input_cost_usd": round(input_cost, 6),
        "output_cost_usd": round(output_cost, 6),
        "total_cost_usd": round(input_cost + output_cost, 6),
    }


def enrich_usage(
    usage: dict[str, Any] | None,
    *,
    source: str | None = None,
    approximate: bool | None = None,
) -> dict[str, Any]:
    payload = dict(usage or {})
    prompt_tokens = _safe_int(payload.get("prompt_tokens"))
    candidate_tokens = _safe_int(payload.get("candidate_tokens"))
    thoughts_tokens = _safe_int(payload.get("thoughts_tokens"))
    output_tokens = _safe_int(payload.get("output_tokens"))
    if output_tokens <= 0:
        output_tokens = max(0, candidate_tokens + thoughts_tokens)

    total_tokens = _safe_int(payload.get("total_tokens"))
    computed_total = prompt_tokens + candidate_tokens + thoughts_tokens
    if total_tokens <= 0:
        total_tokens = computed_total
    else:
        total_tokens = max(total_tokens, computed_total)

    resolved_source = str(payload.get("source") or source or "").strip() or None
    resolved_approximate = (
        bool(approximate)
        if approximate is not None
        else bool(payload.get("approximate"))
    )
    if resolved_source == "mock":
        resolved_approximate = True

    pricing = calculate_usage_costs(prompt_tokens, output_tokens)
    enriched = {
        **payload,
        "prompt_tokens": prompt_tokens,
        "candidate_tokens": candidate_tokens,
        "thoughts_tokens": thoughts_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "approximate": resolved_approximate,
        **pricing,
    }
    if resolved_source:
        enriched["source"] = resolved_source
    return enriched


def summarize_usage_records(records: Iterable[dict[str, Any] | None]) -> dict[str, Any]:
    summary = {
        "call_count": 0,
        "prompt_tokens": 0,
        "candidate_tokens": 0,
        "thoughts_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "input_cost_usd": 0.0,
        "output_cost_usd": 0.0,
        "total_cost_usd": 0.0,
        "sources": [],
        "approximate": False,
    }

    for usage in records:
        if not isinstance(usage, dict):
            continue
        normalized = enrich_usage(usage)
        summary["call_count"] += 1
        summary["prompt_tokens"] += normalized["prompt_tokens"]
        summary["candidate_tokens"] += normalized["candidate_tokens"]
        summary["thoughts_tokens"] += normalized["thoughts_tokens"]
        summary["output_tokens"] += normalized["output_tokens"]
        summary["total_tokens"] += normalized["total_tokens"]
        summary["input_cost_usd"] += normalized["input_cost_usd"]
        summary["output_cost_usd"] += normalized["output_cost_usd"]
        summary["total_cost_usd"] += normalized["total_cost_usd"]
        summary["approximate"] = summary["approximate"] or bool(
            normalized.get("approximate")
        )

        source = normalized.get("source")
        if source and source not in summary["sources"]:
            summary["sources"].append(source)

    summary["input_cost_usd"] = round(summary["input_cost_usd"], 6)
    summary["output_cost_usd"] = round(summary["output_cost_usd"], 6)
    summary["total_cost_usd"] = round(summary["total_cost_usd"], 6)
    return summary


def scale_usage_summary(summary: dict[str, Any] | None, factor: int) -> dict[str, Any]:
    base = dict(summary or {})
    multiplier = max(0, int(factor or 0))
    return {
        "call_count": int(base.get("call_count", 0)) * multiplier,
        "prompt_tokens": int(base.get("prompt_tokens", 0)) * multiplier,
        "candidate_tokens": int(base.get("candidate_tokens", 0)) * multiplier,
        "thoughts_tokens": int(base.get("thoughts_tokens", 0)) * multiplier,
        "output_tokens": int(base.get("output_tokens", 0)) * multiplier,
        "total_tokens": int(base.get("total_tokens", 0)) * multiplier,
        "input_cost_usd": round(float(base.get("input_cost_usd", 0.0)) * multiplier, 6),
        "output_cost_usd": round(
            float(base.get("output_cost_usd", 0.0)) * multiplier, 6
        ),
        "total_cost_usd": round(float(base.get("total_cost_usd", 0.0)) * multiplier, 6),
        "sources": list(base.get("sources", [])),
        "approximate": bool(base.get("approximate", False)),
    }


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
