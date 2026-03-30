from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from backend.config import APP_CONFIG
from backend.utils import estimate_tokens, excerpt


class GeminiClientError(RuntimeError):
    """Raised when the Gemini API fails."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "GEMINI_HTTP_ERROR",
        status_code: int | None = None,
        retryable: bool = False,
        attempts: int = 1,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.retryable = retryable
        self.attempts = attempts
        self.retry_after_seconds = retry_after_seconds


class GeminiClient:
    RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}

    def __init__(self) -> None:
        self.api_key = APP_CONFIG.gemini_api_key
        self.model = APP_CONFIG.gemini_model
        self.endpoint = APP_CONFIG.gemini_endpoint
        self.timeout = APP_CONFIG.request_timeout_seconds
        self.max_retries = APP_CONFIG.gemini_max_retries
        self.base_retry_delay_seconds = APP_CONFIG.gemini_retry_base_delay_seconds
        self.max_retry_delay_seconds = max(
            self.base_retry_delay_seconds,
            APP_CONFIG.gemini_retry_max_delay_seconds,
        )
        self.mode = "live" if self.api_key else "mock"

    async def generate_text(
        self,
        *,
        persona: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
    ) -> dict[str, Any]:
        if not self.api_key:
            return self._mock_generate(
                persona=persona,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

        payload = self._generate_payload(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
        )
        data = await self._post_json(action="generateContent", payload=payload)
        text = self._extract_text(data)
        return {
            "text": text,
            "usage": self._normalize_usage(
                data.get("usageMetadata", {}),
                prompt_source=system_prompt + user_prompt,
                response_text=text,
            ),
            "raw": data,
        }

    async def count_tokens(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> int:
        if not self.api_key:
            return estimate_tokens(system_prompt) + estimate_tokens(user_prompt)

        generate_payload = self._generate_payload(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.8,
        )
        body = {"generateContentRequest": generate_payload}
        data = await self._post_json(action="countTokens", payload=body)

        total_tokens = self._safe_int(
            data.get("totalTokens") or data.get("total_tokens") or 0
        )
        if total_tokens <= 0:
            raise GeminiClientError(
                "Gemini countTokens response is missing totalTokens.",
                code="GEMINI_INVALID_RESPONSE",
            )
        return total_tokens

    async def _post_json(self, *, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.endpoint}/models/{self.model}:{action}"
        headers = {"x-goog-api-key": self.api_key}

        async with self._build_http_client() as client:
            for attempt in range(1, self.max_retries + 2):
                try:
                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    return self._parse_json_response(response, attempts=attempt)
                except GeminiClientError as error:
                    if self._should_retry(error, attempt):
                        await self._sleep_before_retry(error, attempt)
                        continue
                    raise
                except httpx.TimeoutException as error:
                    gemini_error = GeminiClientError(
                        "Gemini request timed out.",
                        code="GEMINI_TIMEOUT",
                        retryable=True,
                        attempts=attempt,
                    )
                    if self._should_retry(gemini_error, attempt):
                        await self._sleep_before_retry(gemini_error, attempt)
                        continue
                    raise gemini_error from error
                except httpx.HTTPStatusError as error:
                    gemini_error = self._map_http_status_error(error, attempt=attempt)
                    if self._should_retry(gemini_error, attempt):
                        await self._sleep_before_retry(gemini_error, attempt)
                        continue
                    raise gemini_error from error
                except httpx.HTTPError as error:
                    gemini_error = GeminiClientError(
                        f"Gemini network error: {error}",
                        code="GEMINI_NETWORK_ERROR",
                        retryable=True,
                        attempts=attempt,
                    )
                    if self._should_retry(gemini_error, attempt):
                        await self._sleep_before_retry(gemini_error, attempt)
                        continue
                    raise gemini_error from error

        raise GeminiClientError("Gemini request failed after retry exhaustion.")

    def _build_http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self.timeout)

    def _parse_json_response(
        self,
        response: httpx.Response,
        *,
        attempts: int,
    ) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as error:
            raise GeminiClientError(
                "Gemini returned invalid JSON.",
                code="GEMINI_INVALID_RESPONSE",
                status_code=response.status_code,
                attempts=attempts,
            ) from error

        if not isinstance(payload, dict):
            raise GeminiClientError(
                "Gemini returned a non-object JSON payload.",
                code="GEMINI_INVALID_RESPONSE",
                status_code=response.status_code,
                attempts=attempts,
            )
        return payload

    def _should_retry(self, error: GeminiClientError, attempt: int) -> bool:
        return error.retryable and attempt <= self.max_retries

    async def _sleep_before_retry(
        self,
        error: GeminiClientError,
        attempt: int,
    ) -> None:
        delay = self._retry_delay(error, attempt)
        if delay > 0:
            await asyncio.sleep(delay)

    def _retry_delay(self, error: GeminiClientError, attempt: int) -> float:
        if error.retry_after_seconds is not None:
            return min(self.max_retry_delay_seconds, max(0.0, error.retry_after_seconds))
        return min(
            self.max_retry_delay_seconds,
            self.base_retry_delay_seconds * (2 ** (attempt - 1)),
        )

    def _map_http_status_error(
        self,
        error: httpx.HTTPStatusError,
        *,
        attempt: int,
    ) -> GeminiClientError:
        status_code = error.response.status_code
        detail = self._response_error_detail(error.response)
        retry_after = self._parse_retry_after(
            error.response.headers.get("Retry-After")
        )

        if status_code == 429:
            message = "Gemini rate limit reached."
            code = "GEMINI_RATE_LIMIT"
            retryable = True
        elif status_code in self.RETRYABLE_STATUS_CODES:
            message = f"Gemini service temporarily unavailable ({status_code})."
            code = "GEMINI_SERVICE_UNAVAILABLE"
            retryable = True
        else:
            message = f"Gemini request failed with status {status_code}."
            code = "GEMINI_HTTP_ERROR"
            retryable = False

        if detail:
            message = f"{message} {detail}"

        return GeminiClientError(
            message,
            code=code,
            status_code=status_code,
            retryable=retryable,
            attempts=attempt,
            retry_after_seconds=retry_after,
        )

    def _response_error_detail(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return excerpt(response.text or "", 180)

        if isinstance(payload, dict):
            error_payload = payload.get("error", {})
            if isinstance(error_payload, dict) and error_payload.get("message"):
                return excerpt(str(error_payload["message"]), 180)
            if payload.get("message"):
                return excerpt(str(payload["message"]), 180)
        return excerpt(response.text or "", 180)

    def _parse_retry_after(self, value: str | None) -> float | None:
        if not value:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            pass

        try:
            retry_at = parsedate_to_datetime(value)
        except (TypeError, ValueError, IndexError):
            return None

        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)
        return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())

    def _generate_payload(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
    ) -> dict[str, Any]:
        return {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "thinkingConfig": {
                    "thinkingBudget": -1,
                    "includeThoughts": False,
                },
            },
        }

    def _extract_text(self, payload: dict[str, Any]) -> str:
        prompt_feedback = payload.get("promptFeedback") or {}
        blocked_reason = (
            prompt_feedback.get("blockReason")
            if isinstance(prompt_feedback, dict)
            else None
        )
        if blocked_reason:
            raise GeminiClientError(
                f"Gemini blocked the prompt ({blocked_reason}).",
                code="GEMINI_BLOCKED_PROMPT",
            )

        candidates = payload.get("candidates") or []
        if not isinstance(candidates, list) or not candidates:
            raise GeminiClientError(
                "Gemini returned no candidates.",
                code="GEMINI_INVALID_RESPONSE",
            )

        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            content = candidate.get("content") or {}
            parts = content.get("parts") or []
            if not isinstance(parts, list):
                continue
            text_parts = []
            for part in parts:
                if not isinstance(part, dict):
                    continue
                text = str(part.get("text") or "").strip()
                if text:
                    text_parts.append(text)
            if text_parts:
                return "\n".join(text_parts).strip()

        finish_reasons = [
            candidate.get("finishReason")
            for candidate in candidates
            if isinstance(candidate, dict) and candidate.get("finishReason")
        ]
        if "SAFETY" in finish_reasons:
            raise GeminiClientError(
                "Gemini blocked the response for safety reasons.",
                code="GEMINI_BLOCKED_RESPONSE",
            )

        suffix = (
            f" finish_reason={finish_reasons[0]}"
            if finish_reasons
            else ""
        )
        raise GeminiClientError(
            f"Gemini returned an empty candidate.{suffix}",
            code="GEMINI_INVALID_RESPONSE",
        )

    def _normalize_usage(
        self,
        usage: dict[str, Any],
        *,
        prompt_source: str,
        response_text: str,
    ) -> dict[str, int]:
        usage_dict = usage if isinstance(usage, dict) else {}
        prompt_tokens = self._safe_int(usage_dict.get("promptTokenCount", 0) or 0)
        candidate_tokens = self._safe_int(
            usage_dict.get("candidatesTokenCount", 0) or 0
        )
        thoughts_tokens = self._safe_int(usage_dict.get("thoughtsTokenCount", 0) or 0)
        total_tokens = self._safe_int(usage_dict.get("totalTokenCount", 0) or 0)

        if not prompt_tokens:
            prompt_tokens = estimate_tokens(prompt_source)
        if not candidate_tokens:
            candidate_tokens = max(60, estimate_tokens(response_text))
        if not total_tokens:
            total_tokens = prompt_tokens + candidate_tokens + thoughts_tokens

        return {
            "prompt_tokens": prompt_tokens,
            "candidate_tokens": candidate_tokens,
            "thoughts_tokens": thoughts_tokens,
            "total_tokens": total_tokens,
        }

    def _safe_int(self, value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    def _mock_generate(
        self,
        *,
        persona: str,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        if persona == "rune_draft":
            text = (
                "[초안]\n"
                f"촛불 냄새가 배어 있는 장면으로 시작합니다. 중심 갈등은 {excerpt(user_prompt, 120)} 입니다.\n\n"
                "인물은 서로를 완전히 믿지 못한 채 움직이고, 서고의 정적은 문장 사이마다 얇게 번집니다.\n\n"
                "조금 떨리지만, 이번 장면은 끝까지 따라가 보고 싶어요."
            )
        elif persona == "canon_review":
            text = (
                "[피드백]\n"
                "이상 없음.\n"
                "지금 구조면 설정 충돌 없이 바로 최종본으로 정리해도 괜찮습니다."
            )
        elif persona == "echo_comment":
            text = (
                "[댓글]\n"
                "반응:\n"
                "- 도입 분위기가 바로 붙고 다음 장면이 궁금하다.\n"
                "몰입:\n"
                "- 초반에서 바로 끌려 들어가서 계속 읽고 싶다.\n"
                "이탈감:\n"
                "- 없음"
            )
        else:
            text = (
                "[최종본]\n"
                "서고의 정적과 인물의 불안을 더 단단하게 묶어 최종본으로 정리합니다.\n"
                "장면 전환은 조금 더 매끈하게 다듬고, 감정선은 초안보다 선명하게 밀어 올립니다.\n\n"
                "이제는 조금 덜 두렵습니다."
            )

        usage = {
            "prompt_tokens": estimate_tokens(system_prompt) + estimate_tokens(user_prompt),
            "candidate_tokens": estimate_tokens(text),
            "thoughts_tokens": 0,
            "total_tokens": (
                estimate_tokens(system_prompt)
                + estimate_tokens(user_prompt)
                + estimate_tokens(text)
            ),
        }
        return {"text": text, "usage": usage, "raw": {"mode": "mock"}}
