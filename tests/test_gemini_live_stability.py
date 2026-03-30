from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

import httpx

from backend.personas.client import GeminiClient, GeminiClientError
from backend.personas.sil import SilMaintainer


class AsyncClientStub:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, *, headers=None, json=None):
        self.calls.append({"url": url, "headers": headers, "json": json})
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeRepository:
    def __init__(self):
        self.entries = []

    def append_sil_log(self, entry):
        self.entries.append(entry)
        return entry


def make_response(status_code: int, payload: dict | None = None, headers=None) -> httpx.Response:
    request = httpx.Request("POST", "https://example.test")
    return httpx.Response(
        status_code,
        request=request,
        json=payload,
        headers=headers,
    )


class GeminiClientLiveStabilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_text_retries_rate_limit_then_succeeds(self):
        client = GeminiClient()
        client.api_key = "test-key"
        client.mode = "live"
        client.max_retries = 2
        client.base_retry_delay_seconds = 0.1
        client.max_retry_delay_seconds = 1.0

        request = httpx.Request("POST", "https://example.test")
        rate_limited_response = httpx.Response(
            429,
            request=request,
            headers={"Retry-After": "1"},
            json={"error": {"message": "slow down"}},
        )
        success_response = make_response(
            200,
            {
                "candidates": [{"content": {"parts": [{"text": "live text"}]}}],
                "usageMetadata": {
                    "promptTokenCount": 12,
                    "candidatesTokenCount": 8,
                    "totalTokenCount": 20,
                },
            },
        )
        stub = AsyncClientStub(
            [
                httpx.HTTPStatusError(
                    "rate limited",
                    request=request,
                    response=rate_limited_response,
                ),
                success_response,
            ]
        )
        sleep_mock = AsyncMock()

        with (
            patch.object(client, "_build_http_client", return_value=stub),
            patch("backend.personas.client.asyncio.sleep", sleep_mock),
        ):
            result = await client.generate_text(
                persona="rune_draft",
                system_prompt="system",
                user_prompt="user",
                temperature=0.8,
            )

        self.assertEqual(result["text"], "live text")
        self.assertEqual(len(stub.calls), 2)
        sleep_mock.assert_awaited_once()

    async def test_count_tokens_rejects_missing_total_tokens(self):
        client = GeminiClient()
        client.api_key = "test-key"
        client.mode = "live"
        stub = AsyncClientStub([make_response(200, {"totalBillableCharacters": 12})])

        with patch.object(client, "_build_http_client", return_value=stub):
            with self.assertRaises(GeminiClientError) as raised:
                await client.count_tokens(
                    system_prompt="system",
                    user_prompt="user",
                )

        self.assertEqual(raised.exception.code, "GEMINI_INVALID_RESPONSE")

    def test_extract_text_rejects_blocked_prompt(self):
        client = GeminiClient()

        with self.assertRaises(GeminiClientError) as raised:
            client._extract_text({"promptFeedback": {"blockReason": "SAFETY"}})

        self.assertEqual(raised.exception.code, "GEMINI_BLOCKED_PROMPT")


class SilMaintainerClassificationTests(unittest.TestCase):
    def test_retryable_gemini_failure_is_not_marked_repaired(self):
        repository = FakeRepository()
        sil = SilMaintainer(repository)

        entry = sil.record_error(
            GeminiClientError(
                "timed out after retries",
                code="GEMINI_TIMEOUT",
                retryable=True,
                attempts=3,
            )
        )

        self.assertFalse(entry["repaired"])
        self.assertTrue(entry["retryable"])
        self.assertIn("자동 복구 한계 초과", entry["display"])
        self.assertNotIn("epilogue", entry)


if __name__ == "__main__":
    unittest.main()
