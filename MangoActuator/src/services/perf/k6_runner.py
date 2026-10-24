import asyncio
import json
import os
import stat
import sys
import tempfile
from pathlib import Path

from mangotools.perf.k6_script import K6_SCRIPT_SOURCE

from src.services.perf.k6_runtime import resolve_k6_binary


K6_BRIDGE_SOURCE = r'''
import collections
import csv
import datetime
import io
import json
import math
import os
import subprocess
import sys
import threading
import uuid


def bucket(value):
    return max(0, int(round(value)))


def new_item():
    return {"count": 0, "failure": 0, "sum": 0, "min": None, "max": None, "buckets": collections.defaultdict(int)}


def main():
    ir = json.loads(os.environ["MANGO_PERF_IR_JSON"])
    capture_enabled = os.environ.get("MANGO_PERF_CAPTURE_REQUEST") == "1" or os.environ.get("MANGO_PERF_CAPTURE_RESPONSE") == "1"
    capture_path = os.environ.get("MANGO_PERF_CAPTURE_PATH", "")
    process = subprocess.Popen(
        [os.environ["MANGO_K6_BINARY"], "run", "--quiet", "--log-format=json", "--out", "json=-", os.environ["MANGO_K6_SCRIPT"]],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE if capture_enabled else sys.stderr,
        text=True, env=os.environ.copy(), bufsize=1,
    )
    capture_stats = {"rows": 0, "bytes": 0, "overflow": False, "write_error": False}
    capture_fields = ("timestamp", "run_id", "node_id", "shard_index", "vu", "iteration", "step_key", "step_name", "method", "url", "request_headers", "request_body", "response_status", "response_headers", "response_body", "duration_ms", "error")

    def safe_cell(value):
        text = str(value)
        return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text

    def capture_logs():
        max_bytes = 100_000_000
        try:
            output = open(capture_path, "wb")
        except OSError:
            output = None
            capture_stats["write_error"] = True
        try:
            header = io.StringIO()
            csv.writer(header).writerow(capture_fields)
            encoded = b"\xef\xbb\xbf" + header.getvalue().encode("utf-8")
            if output:
                try:
                    output.write(encoded)
                    capture_stats["bytes"] = len(encoded)
                except OSError:
                    capture_stats["write_error"] = True
            for line in process.stderr:
                try:
                    item = json.loads(line)
                    message = item.get("msg", "")
                    if not message.startswith("MANGO_CAPTURE "):
                        sys.stderr.write(line)
                        continue
                    if capture_stats["overflow"] or capture_stats["write_error"]:
                        continue
                    data = json.loads(message[len("MANGO_CAPTURE "):])
                    data.update(run_id=os.environ["MANGO_PERF_RUN_ID"], node_id=os.environ["MANGO_PERF_NODE_ID"], shard_index=os.environ["MANGO_SHARD_INDEX"])
                    row = io.StringIO()
                    csv.writer(row).writerow([safe_cell(data.get(key, "")) for key in capture_fields])
                    encoded = row.getvalue().encode("utf-8")
                    if capture_stats["bytes"] + len(encoded) > max_bytes:
                        capture_stats["overflow"] = True
                        continue
                    output.write(encoded)
                    capture_stats["bytes"] += len(encoded)
                    capture_stats["rows"] += 1
                except OSError:
                    capture_stats["write_error"] = True
                    continue
                except (ValueError, TypeError, csv.Error):
                    continue
        finally:
            if output:
                try:
                    output.close()
                except OSError:
                    capture_stats["write_error"] = True
        try:
            with open(capture_path + ".json", "w", encoding="utf-8") as metadata:
                json.dump(capture_stats, metadata)
        except OSError:
            pass

    capture_thread = threading.Thread(target=capture_logs, daemon=True) if capture_enabled else None
    if capture_thread:
        capture_thread.start()
    windows = collections.defaultdict(lambda: collections.defaultdict(new_item))
    users = collections.defaultdict(int)
    failed = collections.defaultdict(lambda: collections.defaultdict(int))
    iterations = collections.defaultdict(int); dropped = collections.defaultdict(int)
    sent = collections.defaultdict(int); received = collections.defaultdict(int)
    connections = collections.defaultdict(lambda: collections.defaultdict(int))
    connect_errors = collections.defaultdict(lambda: collections.defaultdict(int))
    timing_sums = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(float)))
    timing_counts = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(int)))
    sequence = 0
    emitted_errors = set()

    def emit(timestamp):
        nonlocal sequence
        if not timestamp or timestamp not in windows:
            return
        sequence += 1; points = []
        elapsed = sequence - 1; cursor = 0; stage = ir["stages"][-1]
        for candidate in ir["stages"]:
            cursor += candidate["duration_seconds"]
            if elapsed < cursor:
                stage = candidate; break
        for key, item in windows.pop(timestamp).items():
            failure = sum(failed[timestamp].values()) if key == "__all__" else failed[timestamp][key]
            failure = min(item["count"], failure)
            timing_breakdown = {
                field: timing_sums[timestamp][key][field] / timing_counts[timestamp][key][field]
                for field in timing_sums[timestamp][key]
                if timing_counts[timestamp][key][field]
            }
            points.append({
                "sequence": sequence, "window_start": timestamp + "+00:00", "window_seconds": 1,
                "scope_type": "global" if key == "__all__" else "request", "scope_key": key,
                "stage_key": stage["stage_key"],
                "target_load": {"users": stage.get("target_users"), "rate": stage.get("target_rate")},
                "actual_load": {"users": users[timestamp]}, "request_count": item["count"],
                "failure_count": failure, "response_time_sum_ms": item["sum"],
                "iteration_count": iterations[timestamp] if key == "__all__" else 0,
                "dropped_count": dropped[timestamp] if key == "__all__" else 0,
                "bytes_sent": sent[timestamp] if key == "__all__" else 0,
                "bytes_received": received[timestamp] if key == "__all__" else 0,
                "connection_count": connections[timestamp][key],
                "connect_error_count": connect_errors[timestamp][key],
                "min_response_time_ms": item["min"], "max_response_time_ms": item["max"],
                "histogram": json.dumps(item["buckets"], separators=(",", ":")),
                "timing_breakdown": timing_breakdown,
            })
        failed.pop(timestamp, None); users.pop(timestamp, None); iterations.pop(timestamp, None); dropped.pop(timestamp, None); sent.pop(timestamp, None); received.pop(timestamp, None)
        connections.pop(timestamp, None); connect_errors.pop(timestamp, None); timing_sums.pop(timestamp, None); timing_counts.pop(timestamp, None)
        print("MANGO_METRIC " + json.dumps({"sequence": sequence, "points": points}, separators=(",", ":")), flush=True)

    last_timestamp = None
    for line in process.stdout:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if value.get("type") != "Point":
            continue
        data = value.get("data") or {}; tags = data.get("tags") or {}; timestamp = str(data.get("time", ""))[:19]
        if last_timestamp and timestamp != last_timestamp:
            emit(last_timestamp)
        last_timestamp = timestamp
        windows[timestamp]["__all__"]
        name = tags.get("step_key") or tags.get("name") or "__all__"; metric = value.get("metric")
        if metric == "vus": users[timestamp] = max(users[timestamp], int(data.get("value") or 0))
        elif metric == "iterations": iterations[timestamp] += int(data.get("value") or 0)
        elif metric == "dropped_iterations": dropped[timestamp] += int(data.get("value") or 0)
        elif metric == "data_sent": sent[timestamp] += int(data.get("value") or 0)
        elif metric == "data_received": received[timestamp] += int(data.get("value") or 0)
        elif metric in ("http_req_failed", "mango_check_failures") and float(data.get("value") or 0) > 0:
            failed[timestamp][name] += 1
            error_code = str(tags.get("error_code") or "")
            if metric == "http_req_failed" and error_code.startswith(("11", "12", "13")):
                for key in ("__all__", name): connect_errors[timestamp][key] += 1
            error_key = (timestamp, name, metric)
            if error_key not in emitted_errors:
                emitted_errors.add(error_key)
                print("MANGO_ERROR " + json.dumps({
                    "sample_key": uuid.uuid4().hex, "occurred_at": timestamp + "+00:00",
                    "step_key": tags.get("step_key") or "", "error_type": "k6_check" if metric == "mango_check_failures" else "k6_http",
                    "error_code": metric, "message": "k6 响应检查失败" if metric == "mango_check_failures" else "k6 HTTP 请求失败",
                }, separators=(",", ":")), flush=True)
        elif metric == "http_req_duration":
            duration = max(0, int(float(data.get("value") or 0)))
            for key in ("__all__", name):
                item = windows[timestamp][key]; item["count"] += 1; item["sum"] += duration
                item["min"] = duration if item["min"] is None else min(item["min"], duration)
                item["max"] = duration if item["max"] is None else max(item["max"], duration)
                item["buckets"][bucket(duration)] += 1
        elif metric in ("http_req_connecting", "http_req_tls_handshaking", "http_req_waiting", "http_req_receiving"):
            field = {
                "http_req_connecting": "connect_ms", "http_req_tls_handshaking": "tls_ms",
                "http_req_waiting": "ttfb_ms", "http_req_receiving": "download_ms",
            }[metric]
            metric_value = max(0, float(data.get("value") or 0))
            for key in ("__all__", name):
                timing_sums[timestamp][key][field] += metric_value
                timing_counts[timestamp][key][field] += 1
                if metric == "http_req_connecting" and metric_value > 0: connections[timestamp][key] += 1
    emit(last_timestamp)
    code = process.wait()
    if capture_thread:
        capture_thread.join(timeout=30)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
'''


class K6Runner:
    def __init__(self, request):
        self.request = request
        self._temp_dir = None

    async def start(self):
        binary = resolve_k6_binary()
        if not binary:
            raise RuntimeError("执行器未安装 k6，无法执行性能场景")
        self._temp_dir = tempfile.TemporaryDirectory(prefix="mango-k6-")
        directory = Path(self._temp_dir.name)
        script_path = directory / "scenario.js"
        bridge_path = directory / "bridge.py"
        script_path.write_text(K6_SCRIPT_SOURCE, encoding="utf-8")
        bridge_path.write_text(K6_BRIDGE_SOURCE, encoding="utf-8")
        os.chmod(script_path, stat.S_IRUSR | stat.S_IWUSR)
        os.chmod(bridge_path, stat.S_IRUSR | stat.S_IWUSR)
        environment = os.environ.copy()
        environment.update({
            "MANGO_K6_BINARY": binary, "MANGO_K6_SCRIPT": str(script_path),
            "MANGO_PERF_IR_JSON": self.request.scenario.model_dump_json(),
            "MANGO_SHARD_INDEX": str(self.request.shard_index), "MANGO_SHARD_COUNT": str(self.request.shard_count),
            "MANGO_PERF_RUN_ID": str(self.request.run_id),
            "MANGO_PERF_NODE_ID": str(self.request.run_node_id),
            "MANGO_PERF_CAPTURE_REQUEST": "1" if self.request.capture.get("request") else "0",
            "MANGO_PERF_CAPTURE_RESPONSE": "1" if self.request.capture.get("response") else "0",
            "MANGO_PERF_CAPTURE_PATH": str(directory / "capture.csv"),
            "MANGO_RUNTIME_VARIABLES": json.dumps(self.request.variables, ensure_ascii=False),
        })
        return await asyncio.create_subprocess_exec(
            sys.executable, str(bridge_path), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            env=environment, cwd=str(directory), start_new_session=True,
        )

    def capture_artifact(self):
        if not self._temp_dir or not any(self.request.capture.values()):
            return None
        path = Path(self._temp_dir.name) / "capture.csv"
        metadata = Path(f"{path}.json")
        if not path.is_file() or not metadata.is_file():
            return {"status": "failed", "message": "执行器未生成请求记录"}
        result = json.loads(metadata.read_text(encoding="utf-8"))
        status = "failed" if result.get("write_error") else "too_large" if result["overflow"] else "ready"
        return {"status": status, "path": str(path), "rows": result["rows"], "bytes": result["bytes"]}

    def close(self):
        if self._temp_dir:
            self._temp_dir.cleanup()
            self._temp_dir = None
