import asyncio
import unittest

import httpx

from surveyhub_mcp.common import AsyncCircuitBreaker, MAX_RETRY_DELAY, _retry_delay


class AsyncCircuitBreakerTest(unittest.IsolatedAsyncioTestCase):
    async def test_opens_after_failure_threshold(self) -> None:
        breaker = AsyncCircuitBreaker(failure_threshold=2, recovery_timeout=30.0)

        self.assertEqual(await breaker.allow_request(), (True, 0.0))
        await breaker.record_failure()
        self.assertEqual(await breaker.allow_request(), (True, 0.0))

        await breaker.record_failure()
        allowed, retry_after = await breaker.allow_request()

        self.assertFalse(allowed)
        self.assertGreater(retry_after, 0.0)

    async def test_success_resets_failures(self) -> None:
        breaker = AsyncCircuitBreaker(failure_threshold=2, recovery_timeout=30.0)

        await breaker.record_failure()
        await breaker.record_success()
        await breaker.record_failure()

        self.assertEqual(await breaker.allow_request(), (True, 0.0))

    async def test_half_open_allows_single_probe_after_recovery_timeout(self) -> None:
        breaker = AsyncCircuitBreaker(failure_threshold=1, recovery_timeout=0.01)

        await breaker.record_failure()
        await asyncio.sleep(0.02)

        self.assertEqual(await breaker.allow_request(), (True, 0.0))
        allowed, retry_after = await breaker.allow_request()

        self.assertFalse(allowed)
        self.assertEqual(retry_after, 0.0)


class RetryDelayTest(unittest.TestCase):
    def test_retry_after_header_is_capped(self) -> None:
        response = httpx.Response(429, headers={"Retry-After": "120"})

        self.assertEqual(_retry_delay(response, attempt=0), MAX_RETRY_DELAY)

    def test_exponential_backoff_is_capped(self) -> None:
        response = httpx.Response(429)

        self.assertEqual(_retry_delay(response, attempt=10), MAX_RETRY_DELAY)


if __name__ == "__main__":
    unittest.main()
