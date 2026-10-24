import unittest
import csv
import uuid
import json
import os
import re
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone

from pydantic import ValidationError

from src.models.perf_model import PerfExecutionRequest
from src.services.perf.k6_runner import K6_BRIDGE_SOURCE, K6_SCRIPT_SOURCE
from src.services.perf.k6_runtime import resolve_k6_binary
from src.services.perf.runner import PerfRunner
from src.storage.sqlite import PerfMetricOutbox


def request_payload():
    return {
        "run_id": 1, "run_node_id": 2, "node_key": "node", "schedule_at": datetime.now(timezone.utc),
        "shard_index": 0, "shard_count": 2,
        "variables": {"tenant": "demo"},
        "scenario": {
            "schema_version": 1, "scenario_id": 3, "scenario_version": 1, "name": "场景",
            "project_product_id": 1, "module_id": 1, "engine": "k6",
            "source_case_id": 11, "source_case_release_id": 21, "source_case_revision_id": 31,
            "source_case_revision_checksum": "a" * 64, "source_case_version_label": "v1",
            "execution_mode": "sequential", "load_type": "concurrency",
            "user_wait_min_ms": 0, "user_wait_max_ms": 100,
            "steps": [{
                "step_key": "step", "name": "首页", "sort": 0, "api_info_id": 1,
                "api_revision_id": 2, "api_revision_checksum": "hash",
                "request": {"http_config": {"method": "GET", "url": "https://example.com/api"}},
            }],
            "stages": [{"stage_key": "stage-1", "name": "稳态", "duration_seconds": 10, "target_users": 100}],
            "performance_goal": {
                "template_key": "recommended",
                "p95_ms": 500,
                "max_error_rate": 0.01,
                "min_load_achievement_rate": 0.95,
            },
        },
    }


class PerfRuntimeTests(unittest.TestCase):
    def test_request_response_capture_writes_per_node_csv_and_redacts_secrets(self):
        binary = resolve_k6_binary()
        if not binary:
            self.skipTest("当前环境没有 k6")

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", "0")))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"ok":true,"token":"private-value"}')

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            scenario = request_payload()["scenario"]
            scenario.update(load_profile="fixed_iterations", total_iterations=3,
                            stages=[{"stage_key": "load", "name": "count", "duration_seconds": 10, "target_users": 1}])
            scenario["steps"] = [{"step_key": "step", "name": "capture", "sort": 0,
                                  "request": {"method": "POST", "url": f"http://127.0.0.1:{server.server_port}/?token=private-value", "body_type": "json"},
                                  "request_override": {"headers": {"Authorization": "private-value"}, "body": {"password": "private-value", "name": "visible"}}}]
            scenario["user_wait_min_ms"] = scenario["user_wait_max_ms"] = 0
            with tempfile.TemporaryDirectory(prefix="mango-perf-capture-") as temp_dir:
                script = Path(temp_dir) / "scenario.js"
                bridge = Path(temp_dir) / "bridge.py"
                capture = Path(temp_dir) / "capture.csv"
                script.write_text(K6_SCRIPT_SOURCE, encoding="utf-8")
                bridge.write_text(K6_BRIDGE_SOURCE, encoding="utf-8")
                result = subprocess.run([os.sys.executable, str(bridge)], capture_output=True, text=True, timeout=30,
                    env={**os.environ, "MANGO_K6_BINARY": binary, "MANGO_K6_SCRIPT": str(script),
                         "MANGO_PERF_IR_JSON": json.dumps(scenario), "MANGO_PERF_RUN_ID": "42", "MANGO_PERF_NODE_ID": "7",
                         "MANGO_SHARD_INDEX": "0", "MANGO_SHARD_COUNT": "1", "MANGO_RUNTIME_VARIABLES": "{}",
                         "MANGO_PERF_CAPTURE_REQUEST": "1", "MANGO_PERF_CAPTURE_RESPONSE": "1", "MANGO_PERF_CAPTURE_PATH": str(capture)})
                self.assertEqual(result.returncode, 0, result.stderr[-1500:])
                with capture.open(encoding="utf-8-sig", newline="") as source:
                    rows = list(csv.DictReader(source))
                self.assertEqual(len(rows), 3)
                self.assertEqual(rows[0]["response_status"], "200")
                self.assertEqual(rows[0]["run_id"], "42")
                self.assertEqual(rows[0]["node_id"], "7")
                self.assertEqual(json.loads(rows[0]["request_body"])["password"], "***")
                self.assertEqual(json.loads(rows[0]["response_body"])["token"], "***")
                self.assertNotIn("private-value", capture.read_text(encoding="utf-8-sig"))
                self.assertFalse(json.loads(Path(f"{capture}.json").read_text())["overflow"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_fixed_iterations_are_split_exactly_across_two_executors(self):
        binary = resolve_k6_binary()
        if not binary:
            self.skipTest("当前环境没有 k6")
        received = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                received.append(self.path)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ok")

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            scenario = request_payload()["scenario"]
            scenario.update(load_profile="fixed_iterations", total_iterations=9,
                            stages=[{"stage_key": "load", "name": "count", "duration_seconds": 10, "target_users": 2}])
            scenario["steps"] = [{"step_key": "step", "name": "count", "sort": 0,
                                  "request": {"method": "GET", "url": f"http://127.0.0.1:{server.server_port}/"}}]
            scenario["user_wait_min_ms"] = scenario["user_wait_max_ms"] = 0
            with tempfile.TemporaryDirectory(prefix="mango-perf-count-") as temp_dir:
                script = Path(temp_dir) / "scenario.js"
                script.write_text(K6_SCRIPT_SOURCE, encoding="utf-8")
                for shard in range(2):
                    result = subprocess.run(
                        [binary, "run", "--quiet", str(script)], capture_output=True, text=True, timeout=20,
                        env={**os.environ, "MANGO_PERF_IR_JSON": json.dumps(scenario), "MANGO_PERF_RUN_ID": "42",
                             "MANGO_SHARD_INDEX": str(shard), "MANGO_SHARD_COUNT": "2", "MANGO_RUNTIME_VARIABLES": "{}"},
                    )
                    self.assertEqual(result.returncode, 0, result.stderr[-1500:])
            self.assertEqual(len(received), 9)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_k6_generates_new_performance_values_per_iteration(self):
        binary = resolve_k6_binary()
        if not binary:
            self.skipTest("当前环境没有 k6")
        received = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                size = int(self.headers.get("Content-Length", "0"))
                received.append(json.loads(self.rfile.read(size)))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"ok":true}')

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            scenario = request_payload()["scenario"]
            scenario["stages"] = [{"stage_key": "load", "name": "smoke", "duration_seconds": 4, "target_users": 1, "ramp_type": "step"}]
            scenario["user_wait_min_ms"] = 100
            scenario["user_wait_max_ms"] = 100
            functions = {
                "perf_uuid": {}, "perf_snowflake_id": {}, "perf_random_string": {"length": 16},
                "perf_random_digits": {"length": 8}, "perf_trace_id": {},
                "perf_timestamp_ms": {}, "perf_random_int": {"left": 1, "right": 10},
            }
            scenario["perf_functions"] = [
                {"expression": "${{" + name + "()}}", "name": name, "args": args,
                 "cache_key": "event_id" if name == "perf_snowflake_id" else None}
                for name, args in functions.items()
            ]
            for item in scenario["perf_functions"]:
                if item["args"]:
                    item["expression"] = "${{" + item["name"] + "(" + ",".join(str(value) for value in item["args"].values()) + ")}}"
            scenario["steps"] = [{
                "step_key": "step", "name": "smoke", "sort": 0,
                "request": {"method": "POST", "url": f"http://127.0.0.1:{server.server_port}/", "body_type": "json"},
                "request_override": {"body": {
                    "id": "${{perf_snowflake_id()|event_id}}", "same_id": "${{event_id}}",
                    "uuid": "${{perf_uuid()}}", "text": "${{perf_random_string(16)}}",
                    "digits": "${{perf_random_digits(8)}}", "trace": "${{perf_trace_id()}}",
                    "timestamp": "${{perf_timestamp_ms()}}", "integer": "${{perf_random_int(1,10)}}",
                }},
            }]
            scenario["perf_functions"][1]["expression"] = "${{perf_snowflake_id()|event_id}}"
            with tempfile.TemporaryDirectory(prefix="mango-perf-methods-") as temp_dir:
                script = Path(temp_dir) / "scenario.js"
                script.write_text(K6_SCRIPT_SOURCE, encoding="utf-8")
                result = subprocess.run(
                    [binary, "run", "--quiet", str(script)], capture_output=True, text=True, timeout=20,
                    env={**os.environ, "MANGO_PERF_IR_JSON": json.dumps(scenario), "MANGO_PERF_RUN_ID": "42",
                         "MANGO_SHARD_INDEX": "0", "MANGO_SHARD_COUNT": "1", "MANGO_RUNTIME_VARIABLES": "{}"},
                )
            self.assertEqual(result.returncode, 0, result.stderr[-1500:])
            self.assertGreaterEqual(len(received), 2, (result.stdout + result.stderr)[-3000:])
            self.assertEqual(len({item["id"] for item in received}), len(received))
            for item in received:
                self.assertEqual(item["id"], item["same_id"])
                self.assertRegex(item["uuid"], r"^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
                self.assertRegex(item["text"], r"^[A-Za-z0-9]{16}$")
                self.assertRegex(item["digits"], r"^[0-9]{8}$")
                self.assertRegex(item["trace"], r"^[0-9a-f]{32}$")
                self.assertTrue(re.fullmatch(r"\d{13}", item["timestamp"]))
                self.assertTrue(1 <= item["integer"] <= 10)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    @patch("src.services.perf.runner.resolve_k6_binary", return_value=None)
    def test_missing_k6_binary_reports_unavailable_without_instance_binding_error(self, _resolve):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(PerfRunner._engine_version(), "unavailable")

    def test_k6_bridge_is_valid_python_and_script_has_unified_output(self):
        compile(K6_BRIDGE_SOURCE, "<k6-bridge>", "exec")
        self.assertIn("constant-arrival-rate", K6_SCRIPT_SOURCE)
        self.assertIn("ramping-vus", K6_SCRIPT_SOURCE)
        self.assertIn("shared-iterations", K6_SCRIPT_SOURCE)
        self.assertIn("constant-vus", K6_SCRIPT_SOURCE)
        self.assertIn("MANGO_METRIC", K6_BRIDGE_SOURCE)
        self.assertIn('"timing_breakdown": timing_breakdown', K6_BRIDGE_SOURCE)
        self.assertIn('"connection_count": connections[timestamp][key]', K6_BRIDGE_SOURCE)

    def test_k6_template_prioritizes_bound_environment_base_url(self):
        self.assertIn('const base = root.base_url || root.host || value.base_url || value.host || ""', K6_SCRIPT_SOURCE)
        self.assertIn('url = url.replace(/^https?:\\/\\/[^/]+/, "") || "/"', K6_SCRIPT_SOURCE)
        self.assertIn('url = base.replace(/\\/$/, "") + "/" + url.replace(/^\\//, "")', K6_SCRIPT_SOURCE)

    def test_invalid_shard_is_rejected(self):
        payload = request_payload()
        payload["shard_index"] = 2
        with self.assertRaises(ValidationError):
            PerfExecutionRequest.model_validate(payload)

    def test_non_k6_engine_is_rejected(self):
        payload = request_payload()
        payload["scenario"]["engine"] = "locust"
        with self.assertRaises(ValidationError):
            PerfExecutionRequest.model_validate(payload)

    def test_performance_goal_must_be_one_object(self):
        payload = request_payload()
        payload["scenario"]["performance_goal"] = [payload["scenario"]["performance_goal"]]
        with self.assertRaises(ValidationError):
            PerfExecutionRequest.model_validate(payload)

    def test_templates_support_case_variables_and_cross_shard_unique_ids(self):
        self.assertIn("MANGO_RUNTIME_VARIABLES", K6_SCRIPT_SOURCE)
        self.assertIn("SHARD_INDEX + ((__VU - 1) * SHARD_COUNT)", K6_SCRIPT_SOURCE)
        self.assertNotIn("IR.parameter_sets", K6_SCRIPT_SOURCE)
        self.assertIn(r"\$\{\{([^{}]+)\}\}", K6_SCRIPT_SOURCE)

    def test_k6_template_supports_json_subset_and_array_jsonpath(self):
        self.assertIn('const contains = (left, right) =>', K6_SCRIPT_SOURCE)
        self.assertIn('function jsonPath(value, expression)', K6_SCRIPT_SOURCE)
        self.assertIn('jsonPath(response.json(), extractor.expression)', K6_SCRIPT_SOURCE)

    def test_metric_outbox_uses_stable_node_key_instead_of_reused_database_id(self):
        first_key = f"test-{uuid.uuid4()}"
        second_key = f"test-{uuid.uuid4()}"
        PerfMetricOutbox.upsert(first_key, 7, 1, {"run_id": 1})
        PerfMetricOutbox.upsert(second_key, 7, 1, {"run_id": 2})
        first_rows = PerfMetricOutbox.list_due(first_key)
        second_rows = PerfMetricOutbox.list_due(second_key)
        try:
            self.assertEqual(first_rows[0]["payload"]["run_id"], 1)
            self.assertEqual(second_rows[0]["payload"]["run_id"], 2)
        finally:
            for row in first_rows + second_rows:
                PerfMetricOutbox.delete(row["id"])


if __name__ == "__main__":
    unittest.main()
