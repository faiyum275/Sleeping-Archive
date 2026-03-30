from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import sys


def _resource_root_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent.parent


def _app_home_dir() -> Path:
    configured = os.getenv("SLEEPING_ARCHIVE_HOME", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "SleepingArchiveData"
    return _resource_root_dir()


ROOT_DIR = _resource_root_dir()
APP_HOME_DIR = _app_home_dir()
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
STORAGE_DIR = APP_HOME_DIR / "storage"
HISTORY_DIR = STORAGE_DIR / "history"
SETTINGS_PATH = STORAGE_DIR / "settings.json"
LOOP_STATE_PATH = STORAGE_DIR / "loop_state.json"
SIL_LOG_PATH = STORAGE_DIR / "sil_log.json"
APP_META_PATH = STORAGE_DIR / "app_meta.json"

DEFAULT_SETTINGS = {
    "base": (
        "잠든 서고는 미완성 이야기들이 떠다니는 거대한 도서관이자 극장이다.\n"
        "저자는 세계의 무게중심이며, 돌아오면 서고 전체가 다시 선명해진다."
    ),
    "spoiler": "",
    "style": (
        "문체는 밤의 도서관처럼 조용하고 따뜻하게 유지한다.\n"
        "과한 설명을 줄이고, 장면의 감각과 정서를 우선한다."
    ),
}

DEFAULT_LOOP_STATE = {
    "status": "idle",
    "run_id": None,
    "stage": "idle",
    "message": "서고가 조용히 숨을 고르고 있습니다.",
    "title": "",
    "plot": "",
    "current_iteration": 0,
    "config": {
        "max_loops": 3,
        "early_stop_enabled": True,
        "parallel_feedback": True,
    },
    "cards": [],
    "iterations": [],
    "active_persona": None,
    "started_at": None,
    "completed_at": None,
    "updated_at": None,
    "last_quality": None,
    "usage_summary": None,
    "error": None,
}

DEFAULT_META = {
    "first_visit_at": None,
    "last_visit_at": None,
    "last_reentry_log_date": None,
    "visit_count": 0,
    "total_runs": 0,
    "total_completed_loops": 0,
    "last_return_days": 0,
    "affinity_stage": "distant",
}


@dataclass(frozen=True)
class AppConfig:
    gemini_api_key: str
    gemini_model: str
    gemini_endpoint: str
    request_timeout_seconds: float
    gemini_max_retries: int
    gemini_retry_base_delay_seconds: float
    gemini_retry_max_delay_seconds: float
    default_max_loops: int
    input_cost_per_1m: float
    input_cost_per_1m_large: float
    output_cost_per_1m: float
    output_cost_per_1m_large: float
    pricing_threshold_tokens: int


def load_config() -> AppConfig:
    gemini_retry_base_delay_seconds = max(
        0.0, float(os.getenv("GEMINI_RETRY_BASE_DELAY_SECONDS", "1.5"))
    )
    gemini_retry_max_delay_seconds = max(
        gemini_retry_base_delay_seconds,
        float(os.getenv("GEMINI_RETRY_MAX_DELAY_SECONDS", "8")),
    )

    return AppConfig(
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-pro").strip(),
        gemini_endpoint=os.getenv(
            "GEMINI_API_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta",
        ).rstrip("/"),
        request_timeout_seconds=float(os.getenv("GEMINI_TIMEOUT_SECONDS", "120")),
        gemini_max_retries=max(0, int(os.getenv("GEMINI_MAX_RETRIES", "2"))),
        gemini_retry_base_delay_seconds=gemini_retry_base_delay_seconds,
        gemini_retry_max_delay_seconds=gemini_retry_max_delay_seconds,
        default_max_loops=int(os.getenv("DEFAULT_MAX_LOOPS", "3")),
        input_cost_per_1m=float(os.getenv("GEMINI_INPUT_COST_PER_1M", "1.25")),
        input_cost_per_1m_large=float(
            os.getenv("GEMINI_INPUT_COST_PER_1M_LARGE", "2.50")
        ),
        output_cost_per_1m=float(os.getenv("GEMINI_OUTPUT_COST_PER_1M", "10.00")),
        output_cost_per_1m_large=float(
            os.getenv("GEMINI_OUTPUT_COST_PER_1M_LARGE", "15.00")
        ),
        pricing_threshold_tokens=int(
            os.getenv("GEMINI_PRICING_THRESHOLD_TOKENS", "200000")
        ),
    )


APP_CONFIG = load_config()
