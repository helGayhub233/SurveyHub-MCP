from __future__ import annotations

import inspect
import asyncio
import tempfile
import unittest
import warnings
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from mcp import ClientSession
from mcp.client._memory import InMemoryTransport
from mcp.shared.exceptions import MCPDeprecationWarning
from mcp.types import SetLevelRequestParams

from surveyhub_mcp import common, fofa, hunter_enterprise, hunter_personal, quake
from surveyhub_mcp.hunter_enterprise import search_hunter_enterprise
from surveyhub_mcp.hunter_personal import search_hunter_personal
from surveyhub_mcp.server import create_server


class HunterQueryTests(unittest.TestCase):
    def test_exact_semantics_are_the_default(self) -> None:
        # Non-excluded fields are converted to == by default.
        query = 'ip="1.1.1.1" && protocol="http"'
        self.assertEqual(
            common.normalize_hunter_query(query),
            'ip=="1.1.1.1" && protocol=="http"',
        )
        # Text-search fields in the exclusion set keep their contains semantics.
        excluded_query = 'domain="example.com" && web.title="login"'
        self.assertEqual(common.normalize_hunter_query(excluded_query), excluded_query)
        self.assertTrue(inspect.signature(search_hunter_personal).parameters["exact_search"].default)
        self.assertTrue(inspect.signature(search_hunter_enterprise).parameters["exact_search"].default)

    def test_contains_search_remains_an_explicit_opt_out(self) -> None:
        query = 'domain="example.com" && after="2025-01-01"'

        self.assertEqual(common.normalize_hunter_query(query, exact_search=False), query)

    def test_exact_rewrite_does_not_touch_comparisons_inside_quoted_values(self) -> None:
        # Use a non-excluded field so the rewrite actually happens.
        query = 'ip="literal domain=\\"nested.example\\"" && protocol="http"'

        self.assertEqual(
            common.normalize_hunter_query(query),
            'ip=="literal domain=\\"nested.example\\"" && protocol=="http"',
        )

    def test_exact_rewrite_preserves_existing_and_non_equality_operators(self) -> None:
        query = 'domain=="exact.example" && domain!="blocked" && ip.port_count>"2"'

        self.assertEqual(common.normalize_hunter_query(query), query)


class HunterEditionRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_personal_call_redirects_to_enterprise_when_only_enterprise_is_configured(self) -> None:
        with patch.dict(
            common.os.environ,
            {"CN_HUNTER_ENTERPRISE_KEY": "enterprise-test-key"},
            clear=True,
        ), patch.object(hunter_personal, "request_json", new=AsyncMock()) as request:
            result = await hunter_personal.search_hunter_personal(query='domain="example.com"')

        request.assert_not_awaited()
        self.assertEqual(result["error"]["type"], "wrong_hunter_edition")
        self.assertEqual(result["error"]["details"]["configured_edition"], "enterprise")
        self.assertEqual(result["error"]["details"]["configured_env_var"], "CN_HUNTER_ENTERPRISE_KEY")
        self.assertEqual(result["error"]["details"]["recommended_tool"], "hunter_enterprise_search")
        self.assertIn("do not report Hunter as unavailable", result["error"]["message"])

    async def test_enterprise_search_uses_enterprise_specific_key(self) -> None:
        provider_result = {"ok": True, "platform": "Hunter Enterprise", "data": {"data": []}}
        with patch.dict(
            common.os.environ,
            {"CN_HUNTER_ENTERPRISE_KEY": "enterprise-test-key"},
            clear=True,
        ), patch.object(
            hunter_enterprise,
            "request_json",
            new=AsyncMock(return_value=provider_result),
        ) as request:
            result = await hunter_enterprise.search_hunter_enterprise(query='domain="example.com"')

        self.assertTrue(result["ok"])
        self.assertEqual(request.await_args.kwargs["params"]["api-key"], "enterprise-test-key")
        self.assertEqual(result["platform"], "Hunter Enterprise")

    async def test_unprefixed_enterprise_env_is_rejected_with_canonical_guidance(self) -> None:
        with patch.dict(
            common.os.environ,
            {"HUNTER_ENTERPRISE_KEY": "ignored-unprefixed-key"},
            clear=True,
        ):
            result = await hunter_enterprise.search_hunter_enterprise(query='domain="example.com"')

        self.assertEqual(result["error"]["type"], "missing_credentials")
        self.assertEqual(
            result["error"]["details"]["env_vars"],
            ("CN_HUNTER_ENTERPRISE_KEY", "CN_HUNTER_KEY"),
        )
        self.assertIn("CN_HUNTER_ENTERPRISE_KEY", result["error"]["message"])

    async def test_aggregate_server_instructions_expose_enterprise_routing_without_key_value(self) -> None:
        with patch.dict(
            common.os.environ,
            {"CN_HUNTER_ENTERPRISE_KEY": "secret-value-must-not-leak"},
            clear=True,
        ):
            server = create_server()
            tools = await server.list_tools()

        self.assertIn("Hunter Enterprise is configured", server.instructions)
        self.assertIn("Only hunter_enterprise_* tools are exposed", server.instructions)
        self.assertIn("CN_HUNTER_ENTERPRISE_KEY", server.instructions)
        self.assertNotIn("secret-value-must-not-leak", server.instructions)
        tool_names = {tool.name for tool in tools}
        self.assertEqual(len(tools), 21)
        self.assertIn("hunter_enterprise_search", tool_names)
        self.assertNotIn("hunter_personal_search", tool_names)

    async def test_no_hunter_key_keeps_both_editions_discoverable(self) -> None:
        with patch.dict(common.os.environ, {}, clear=True):
            tools = {tool.name for tool in await create_server().list_tools()}

        self.assertIn("hunter_personal_search", tools)
        self.assertIn("hunter_enterprise_search", tools)

    async def test_enterprise_entrypoint_has_a_focused_six_tool_surface(self) -> None:
        tools = await hunter_enterprise.create_server().list_tools()

        self.assertEqual(len(tools), 6)
        self.assertTrue(all(tool.name.startswith("hunter_enterprise_") for tool in tools))


class TdqsDescriptionTests(unittest.IsolatedAsyncioTestCase):
    async def test_account_info_tools_include_selection_and_behavior_guidance(self) -> None:
        tools = {tool.name: tool for tool in await create_server().list_tools()}

        expectations = {
            "fofa_user_info": ("fofa_search", "configured FOFA credentials"),
            "zoomeye_user_info": ("zoomeye_search", "configured paid-account API key"),
        }
        for tool_name, (alternative, prerequisite) in expectations.items():
            description = tools[tool_name].description or ""
            with self.subTest(tool=tool_name):
                self.assertIn(alternative, description)
                self.assertIn("do not use it for asset discovery", description)
                self.assertIn(prerequisite, description)
                self.assertIn("performs no asset search", description)


class QuakeFieldTests(unittest.TestCase):
    def test_unsupported_fields_are_removed_with_a_warning(self) -> None:
        include, exclude, warnings = quake._prepare_service_fields(
            "ip,port,protocol,hostname,service,title",
            "service.http.body,unknown",
        )

        self.assertEqual(include, "ip,port,hostname")
        self.assertEqual(exclude, "service.http.body")
        self.assertEqual(len(warnings), 2)
        self.assertEqual(
            warnings[0]["details"]["removed_fields"],
            ["protocol", "service", "title"],
        )
        self.assertEqual(warnings[0]["details"]["official_source"], "/api/v3/filterable/field/quake_service")


class QuakeSearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_filters_fields_and_uses_safe_only_retry(self) -> None:
        provider_result = {
            "ok": True,
            "platform": "Quake",
            "data": {"data": []},
            "meta": {"attempts": 1},
        }

        with (
            patch.object(quake, "_quake_key", return_value="configured"),
            patch.object(quake, "request_json", new=AsyncMock(return_value=provider_result)) as request,
        ):
            result = await quake.search_quake_service(
                query='domain:"example.com"',
                include="ip,port,protocol,title",
            )

        request.assert_awaited_once()
        request_kwargs = request.await_args.kwargs
        self.assertEqual(request_kwargs["retry_mode"], "safe_only")
        self.assertTrue(request_kwargs["metered_request"])
        self.assertEqual(request_kwargs["json"]["include"], ["ip", "port"])
        self.assertEqual(result["meta"]["executed_query"], 'domain:"example.com"')
        self.assertEqual(result["warnings"][0]["details"]["removed_fields"], ["protocol", "title"])

    def test_multiple_attempts_disclose_possible_duplicate_quota_use(self) -> None:
        warnings = quake._retry_quota_warning({
            "meta": {"attempts": 2, "execution": {"quota": {"risk": "possible_duplicate"}}}
        })

        self.assertEqual(warnings[0]["type"], "retry_may_consume_quota")
        self.assertEqual(warnings[0]["details"]["attempts"], 2)


class FofaCompletenessTests(unittest.IsolatedAsyncioTestCase):
    async def test_undocumented_tip_does_not_drive_retry_or_completeness(self) -> None:
        tip = "当前请求火爆，full字段未生效，返回默认时间范围"
        provider_result = {
            "ok": True,
            "platform": "FOFA",
            "data": {"tip": tip, "results": []},
            "meta": {
                "attempts": 1,
                "execution": common._execution_receipt(
                    request_id="fofa-test",
                    fingerprint="abc",
                    final_state="confirmed_success",
                    transport_state="response_received",
                    attempts=1,
                    retry_safety="safe",
                    retry_recommended=False,
                    reason="provider_response_received",
                    quota_risk="none",
                    completeness="complete",
                ),
            },
        }

        with (
            patch.object(fofa, "request_json", new=AsyncMock(return_value=provider_result)) as request,
        ):
            result = await fofa._request_fofa_search(
                url="https://fofa.info/api/v1/search/all",
                params={"full": True},
                query='domain="example.com"',
                full=True,
            )

        self.assertEqual(request.await_count, 1)
        self.assertNotIn("partial_data", result["meta"])
        self.assertEqual(result["meta"]["execution"]["completeness"]["state"], "unknown")
        self.assertEqual(result["warnings"][0]["type"], "full_range_unverified")
        self.assertEqual(result["data"]["tip"], tip)


class TimeoutRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_read_timeout_is_not_retried_by_default(self) -> None:
        class FakeAsyncClient:
            calls = 0

            def __init__(self, *args: object, **kwargs: object) -> None:
                pass

            async def __aenter__(self) -> "FakeAsyncClient":
                return self

            async def __aexit__(self, *args: object) -> None:
                return None

            async def request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
                type(self).calls += 1
                request = httpx.Request(method, url)
                raise httpx.ReadTimeout("slow provider", request=request)

        policy = common.HttpPolicy(
            attempt_timeout=0.1,
            total_timeout=1.0,
            max_attempts=2,
            retry_base_delay=0.0,
            retry_delay_cap=0.0,
        )

        with patch.object(common.httpx, "AsyncClient", FakeAsyncClient):
            result = await common.request_json(
                platform="Timeout Retry Test",
                method="GET",
                url="https://example.test/search",
                auth_hint="auth",
                forbidden_hint="forbidden",
                http_policy=policy,
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["meta"]["attempts"], 1)
        self.assertEqual(result["meta"]["execution"]["final_state"], "indeterminate")
        self.assertEqual(result["meta"]["execution"]["retry"]["safety"], "unsafe")
        self.assertEqual(FakeAsyncClient.calls, 1)

    async def test_connect_timeout_is_safely_retried(self) -> None:
        class FakeAsyncClient:
            calls = 0

            def __init__(self, *args: object, **kwargs: object) -> None:
                pass

            async def __aenter__(self) -> "FakeAsyncClient":
                return self

            async def __aexit__(self, *args: object) -> None:
                return None

            async def request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
                type(self).calls += 1
                request = httpx.Request(method, url)
                if type(self).calls == 1:
                    raise httpx.ConnectTimeout("connect failed", request=request)
                return httpx.Response(200, json={"data": [1]}, request=request)

        policy = common.HttpPolicy(
            attempt_timeout=0.1,
            total_timeout=1.0,
            max_attempts=2,
            retry_base_delay=0.0,
            retry_delay_cap=0.0,
        )
        with patch.object(common.httpx, "AsyncClient", FakeAsyncClient):
            result = await common.request_json(
                platform="Connect Retry Test",
                method="POST",
                url="https://example.test/search",
                auth_hint="auth",
                forbidden_hint="forbidden",
                http_policy=policy,
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["meta"]["attempts"], 2)
        self.assertEqual(FakeAsyncClient.calls, 2)


class MCPExecutionNotificationTests(unittest.IsolatedAsyncioTestCase):
    class FakeSession:
        def __init__(self) -> None:
            self.protocol_version = "2025-11-25"
            self._connection = SimpleNamespace(state={})
            self.progress: list[tuple[float, float | None, str | None]] = []
            self.notifications: list[tuple[object, str | None]] = []

        async def report_progress(
            self,
            progress: float,
            total: float | None = None,
            message: str | None = None,
        ) -> None:
            self.progress.append((progress, total, message))

        async def send_notification(self, notification: object, related_request_id: str | None = None) -> None:
            self.notifications.append((notification, related_request_id))

    async def test_progress_is_monotonic_across_nested_provider_calls(self) -> None:
        session = self.FakeSession()
        context = SimpleNamespace(session=session, request_id="mcp-request-1")
        token = common._CURRENT_MCP_EXECUTION.set(common._MCPExecutionState(context=context))
        try:
            await common.ExecutionReporter(platform="FOFA", request_id="provider-1").event(
                "attempt_started", "Starting FOFA attempt."
            )
            await common.ExecutionReporter(platform="Quake", request_id="provider-2").event(
                "attempt_started", "Starting Quake attempt."
            )
        finally:
            common._CURRENT_MCP_EXECUTION.reset(token)

        self.assertEqual([item[0] for item in session.progress], [1, 2])
        self.assertEqual(session.notifications, [])  # Default legacy level is warning.

    async def test_structured_logs_respect_connection_level(self) -> None:
        session = self.FakeSession()
        session._connection.state[common._LOG_LEVEL_STATE_KEY] = "debug"
        context = SimpleNamespace(session=session, request_id="mcp-request-2")
        token = common._CURRENT_MCP_EXECUTION.set(common._MCPExecutionState(context=context))
        try:
            await common.ExecutionReporter(platform="Hunter", request_id="provider-3").event(
                "retry_scheduled",
                "Hunter retry scheduled.",
                level="warning",
                attempt=1,
                delay_seconds=2.0,
            )
        finally:
            common._CURRENT_MCP_EXECUTION.reset(token)

        notification, related_request_id = session.notifications[0]
        self.assertEqual(related_request_id, "mcp-request-2")
        self.assertEqual(notification.params.logger, "surveyhub.execution")
        self.assertEqual(notification.params.data["event"], "retry_scheduled")
        self.assertEqual(notification.params.data["delay_seconds"], 2.0)
        self.assertNotIn("query", notification.params.data)

    async def test_server_advertises_and_applies_legacy_logging_level(self) -> None:
        server = create_server()
        capabilities = server._lowlevel_server.get_capabilities(protocol_version="2025-11-25")
        self.assertIsNotNone(capabilities.logging)

        session = self.FakeSession()
        context = SimpleNamespace(session=session)
        handler = server._lowlevel_server.get_request_handler("logging/setLevel")
        self.assertIsNotNone(handler)
        await handler.handler(context, SetLevelRequestParams(level="error"))
        self.assertEqual(session._connection.state[common._LOG_LEVEL_STATE_KEY], "error")

    async def test_real_mcp_call_delivers_progress_and_structured_logs(self) -> None:
        class SuccessfulAsyncClient:
            def __init__(self, *args: object, **kwargs: object) -> None:
                pass

            async def __aenter__(self) -> "SuccessfulAsyncClient":
                return self

            async def __aexit__(self, *args: object) -> None:
                return None

            async def request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
                request = httpx.Request(method, url)
                return httpx.Response(200, json={"email": "masked@example.test"}, request=request)

        progress: list[tuple[float, float | None, str | None]] = []
        logs: list[object] = []

        async def on_progress(value: float, total: float | None, message: str | None) -> None:
            progress.append((value, total, message))

        async def on_log(params: object) -> None:
            logs.append(params)

        with patch.dict(common.os.environ, {"CN_FOFA_KEY": "test-key"}), patch.object(
            common.httpx, "AsyncClient", SuccessfulAsyncClient
        ):
            async with InMemoryTransport(create_server()) as streams:
                async with ClientSession(*streams, logging_callback=on_log, log_level="debug") as client:
                    await client.initialize()
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", MCPDeprecationWarning)
                        await client.set_logging_level("debug")
                    result = await client.call_tool("fofa_user_info", progress_callback=on_progress)

        self.assertFalse(result.is_error)
        self.assertEqual([item[0] for item in progress], [1, 2])
        self.assertEqual(
            [item.data["event"] for item in logs],
            ["attempt_started", "request_completed"],
        )
        self.assertTrue(all(item.logger == "surveyhub.execution" for item in logs))

    async def test_cancellation_marks_metered_request_indeterminate(self) -> None:
        request_started = asyncio.Event()

        class BlockingAsyncClient:
            def __init__(self, *args: object, **kwargs: object) -> None:
                pass

            async def __aenter__(self) -> "BlockingAsyncClient":
                return self

            async def __aexit__(self, *args: object) -> None:
                return None

            async def request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
                request_started.set()
                await asyncio.Event().wait()
                raise AssertionError("unreachable")

        request_kwargs = {"json": {"query": "domain:cancelled.example"}}
        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(
            common.os.environ, {"SURVEYHUB_STATE_DIR": temp_dir}
        ), patch.object(common.httpx, "AsyncClient", BlockingAsyncClient):
            task = asyncio.create_task(
                common.request_json(
                    platform="Cancellation Test",
                    method="POST",
                    url="https://example.test/search",
                    metered_request=True,
                    auth_hint="auth",
                    forbidden_hint="forbidden",
                    **request_kwargs,
                )
            )
            await request_started.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task

            fingerprint = common.request_fingerprint(
                "Cancellation Test",
                "POST",
                "https://example.test/search",
                request_kwargs,
            )
            ledger = common.RequestLedger(Path(temp_dir) / "requests")
            duplicate = ledger.begin(fingerprint, "follow-up")

        self.assertIsNotNone(duplicate)
        self.assertEqual(duplicate["state"], "indeterminate")


class RequestDeduplicationTests(unittest.IsolatedAsyncioTestCase):
    async def test_recent_indeterminate_metered_request_is_suppressed(self) -> None:
        class FakeAsyncClient:
            calls = 0

            def __init__(self, *args: object, **kwargs: object) -> None:
                pass

            async def __aenter__(self) -> "FakeAsyncClient":
                return self

            async def __aexit__(self, *args: object) -> None:
                return None

            async def request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
                type(self).calls += 1
                raise httpx.ReadTimeout("response unknown", request=httpx.Request(method, url))

        policy = common.HttpPolicy(attempt_timeout=0.1, total_timeout=1.0, max_attempts=2)
        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(
            common.os.environ, {"SURVEYHUB_STATE_DIR": temp_dir}
        ), patch.object(common.httpx, "AsyncClient", FakeAsyncClient):
            first = await common.request_json(
                platform="Ledger Test",
                method="POST",
                url="https://example.test/search",
                json={"query": "domain:test"},
                metered_request=True,
                auth_hint="auth",
                forbidden_hint="forbidden",
                http_policy=policy,
            )
            second = await common.request_json(
                platform="Ledger Test",
                method="POST",
                url="https://example.test/search",
                json={"query": "domain:test"},
                metered_request=True,
                auth_hint="auth",
                forbidden_hint="forbidden",
                http_policy=policy,
            )

        self.assertEqual(first["meta"]["execution"]["final_state"], "indeterminate")
        self.assertEqual(second["error"]["type"], "duplicate_request_suppressed")
        self.assertEqual(second["meta"]["execution"]["duplicate_of"], first["meta"]["execution"]["request_id"])
        self.assertEqual(FakeAsyncClient.calls, 1)

    async def test_recent_successful_metered_request_uses_cache(self) -> None:
        class FakeAsyncClient:
            calls = 0

            def __init__(self, *args: object, **kwargs: object) -> None:
                pass

            async def __aenter__(self) -> "FakeAsyncClient":
                return self

            async def __aexit__(self, *args: object) -> None:
                return None

            async def request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
                type(self).calls += 1
                request = httpx.Request(method, url)
                return httpx.Response(200, json={"data": ["one"]}, request=request)

        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(
            common.os.environ, {"SURVEYHUB_STATE_DIR": temp_dir}
        ), patch.object(common.httpx, "AsyncClient", FakeAsyncClient):
            first = await common.request_json(
                platform="Cache Test", method="POST", url="https://example.test/search",
                json={"query": "same"}, metered_request=True, auth_hint="auth", forbidden_hint="forbidden",
            )
            second = await common.request_json(
                platform="Cache Test", method="POST", url="https://example.test/search",
                json={"query": "same"}, metered_request=True, auth_hint="auth", forbidden_hint="forbidden",
            )

        self.assertTrue(first["ok"])
        self.assertEqual(second["data"], {"data": ["one"]})
        self.assertTrue(second["meta"]["execution"]["cache_hit"])
        self.assertEqual(second["meta"]["attempts"], 0)
        self.assertEqual(FakeAsyncClient.calls, 1)

    async def test_download_timeout_is_retried_and_attempts_are_reported(self) -> None:
        class FakeAsyncClient:
            calls = 0

            def __init__(self, *args: object, **kwargs: object) -> None:
                pass

            async def __aenter__(self) -> "FakeAsyncClient":
                return self

            async def __aexit__(self, *args: object) -> None:
                return None

            async def request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
                type(self).calls += 1
                request = httpx.Request(method, url)
                if type(self).calls == 1:
                    raise httpx.ReadTimeout("slow download", request=request)
                return httpx.Response(200, content=b"export-data", request=request)

        policy = common.HttpPolicy(
            attempt_timeout=0.1,
            total_timeout=1.0,
            max_attempts=2,
            retry_base_delay=0.0,
            retry_delay_cap=0.0,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "export.csv"
            with patch.object(common.httpx, "AsyncClient", FakeAsyncClient):
                result = await common.request_download(
                    platform="Download Retry Test",
                    method="GET",
                    url="https://example.test/export",
                    output_path=str(output_path),
                    auth_hint="auth",
                    forbidden_hint="forbidden",
                    http_policy=policy,
                )

            self.assertEqual(output_path.read_bytes(), b"export-data")

        self.assertTrue(result["ok"])
        self.assertEqual(result["meta"]["attempts"], 2)
        self.assertEqual(FakeAsyncClient.calls, 2)


if __name__ == "__main__":
    unittest.main()
