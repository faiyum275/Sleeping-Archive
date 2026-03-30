from __future__ import annotations

import traceback
from typing import Any

import httpx

from backend.personas.client import GeminiClientError
from backend.storage.repository import Repository
from backend.utils import local_clock_label, utc_now_iso


class SilMaintainer:
    RETRYABLE_CODES = {
        "GEMINI_TIMEOUT",
        "GEMINI_RATE_LIMIT",
        "GEMINI_NETWORK_ERROR",
        "GEMINI_SERVICE_UNAVAILABLE",
        "TRANSIENT_STORAGE_ERROR",
    }

    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    def log_absence(self, days: int) -> dict[str, Any]:
        entry = self._entry(
            kind="heartbeat",
            display=f"[저자 부재 {days}일차] 이상 없음.",
        )
        return self.repository.append_sil_log(entry)

    def log_loop_completion(self, loop_index: int) -> dict[str, Any]:
        entry = self._entry(
            kind="loop",
            display=f"[루프 #{loop_index} 완료] 최종본 저장됨.",
        )
        return self.repository.append_sil_log(entry)

    def record_error(
        self,
        error: Exception,
        *,
        code: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        error_code = code or self._code_for_exception(error)
        retryable = self._is_retryable(error, error_code=error_code)
        tail = (
            "자동 복구 한계 초과. 다음 실행에서 다시 시도할 수 있습니다."
            if retryable
            else "수선 불가. 다음 실행을 위해 흔적을 남깁니다."
        )
        display = f"[{local_clock_label()}] 균열 발생 (오류 코드: {error_code}). {tail}"

        entry = self._entry(
            kind="error",
            display=display,
            error_code=error_code,
            repaired=False,
            retryable=retryable,
            context=context or {},
            detail="".join(traceback.format_exception(type(error), error, error.__traceback__)),
            silhouette=True,
        )
        if not retryable:
            entry["epilogue"] = "기다리고 있었습니다."
        return self.repository.append_sil_log(entry)

    def _code_for_exception(self, error: Exception) -> str:
        if isinstance(error, GeminiClientError):
            return error.code
        if isinstance(error, httpx.TimeoutException):
            return "GEMINI_TIMEOUT"
        if isinstance(error, httpx.HTTPStatusError):
            if error.response.status_code == 429:
                return "GEMINI_RATE_LIMIT"
            return "GEMINI_HTTP_ERROR"
        if isinstance(error, (OSError, ValueError)):
            return "TRANSIENT_STORAGE_ERROR"
        return "UNEXPECTED_ERROR"

    def _is_retryable(self, error: Exception, *, error_code: str) -> bool:
        if isinstance(error, GeminiClientError):
            return error.retryable or error_code in self.RETRYABLE_CODES
        return error_code in self.RETRYABLE_CODES

    def _entry(self, **payload: Any) -> dict[str, Any]:
        return {
            "timestamp": utc_now_iso(),
            "display": payload.pop("display"),
            "kind": payload.pop("kind"),
            **payload,
        }
