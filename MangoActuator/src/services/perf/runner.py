import asyncio
import json
import os
import signal
import time
from datetime import timedelta
from datetime import datetime, timezone

import psutil

from src.models.perf_model import PerfExecutionRequest
from src.network import HTTP
from src.services.perf.k6_runner import K6Runner
from src.services.perf.k6_runtime import resolve_k6_binary
from src.storage.sqlite import PerfMetricOutbox
from src.tools.executor_task_context import get_executor_task_context
from src.tools.log_collector import log


class PerfRunner:
    CONTROL_INTERVAL_SECONDS = 3

    def __init__(self, payload: dict):
        self.request = PerfExecutionRequest.model_validate(payload)
        _, self.connection_id = get_executor_task_context()
        if not self.connection_id:
            raise RuntimeError("性能任务缺少执行器连接标识")
        self.engine = None
        self.process = None
        self._last_control_at = 0.0
        self._stopping = False
        self._pending_errors = []
        self._clock_offset_ms = 0
        self._result_reported = False

    async def run(self) -> dict:
        try:
            return await self._run()
        except asyncio.CancelledError:
            raise
        except Exception as error:
            if not self._result_reported:
                try:
                    await HTTP.perf.result(self.request.run_node_id, self.connection_id, {
                        "status": "failed", "result_summary": {}, "resource_summary": {},
                        "error_code": "executor_runtime_error", "error_message": str(error)[:2048],
                    })
                    self._result_reported = True
                except Exception as report_error:
                    log.error(f"性能节点失败结果回传失败，将由服务端超时恢复: {report_error}")
            raise
        finally:
            if self.engine:
                self.engine.close()

    async def _run(self) -> dict:
        await self._restore_runtime_secrets()
        self.engine = K6Runner(self.request)
        await self._synchronize_clock()
        now = datetime.now(timezone.utc)
        schedule_at = datetime.fromtimestamp(self.request.schedule_at_epoch_ms / 1000, timezone.utc) if self.request.schedule_at_epoch_ms else self.request.schedule_at
        if schedule_at.tzinfo is None:
            schedule_at = schedule_at.astimezone()
        delay = max(0, (schedule_at - now).total_seconds())
        await HTTP.perf.ready(self.request.run_node_id, self.connection_id, {
            "engine_version": self._engine_version(), "clock_offset_ms": self._clock_offset_ms,
        })
        if delay and not await self._wait_until_start(delay):
            result = {"status": "stopped", "engine": self.request.scenario.engine, "before_start": True}
            await HTTP.perf.result(self.request.run_node_id, self.connection_id, {
                "status": "stopped", "result_summary": result, "resource_summary": {},
            })
            self._result_reported = True
            return result
        self.process = await self.engine.start()
        ps_process = psutil.Process(self.process.pid)
        try:
            await self._consume(ps_process)
            return_code = await self.process.wait()
            status = "stopped" if self._stopping else "success" if return_code == 0 else "failed"
            result = {"status": status, "exit_code": return_code, "engine": self.request.scenario.engine}
            await self._flush_outbox()
            await self._flush_errors()
            result["capture"] = await self._upload_capture()
            await HTTP.perf.result(self.request.run_node_id, self.connection_id, {
                "status": status, "result_summary": result, "resource_summary": self._resources(ps_process),
                "error_code": None if return_code == 0 else "engine_exit_nonzero",
                "error_message": None if return_code == 0 else f"{self.request.scenario.engine} 退出码：{return_code}",
            })
            self._result_reported = True
            return result
        except asyncio.CancelledError:
            await self.stop()
            await HTTP.perf.result(self.request.run_node_id, self.connection_id, {"status": "cancelled", "result_summary": {}})
            self._result_reported = True
            raise
        finally:
            self.engine.close()

    async def _upload_capture(self) -> dict:
        if not any(self.request.capture.values()):
            return {"status": "disabled"}
        artifact = self.engine.capture_artifact()
        if not artifact:
            return {"status": "failed", "message": "执行器未生成请求记录"}
        result = {key: value for key, value in artifact.items() if key != "path"}
        if artifact["status"] != "ready":
            return result
        name = f"perf-run-{self.request.run_id}-node-{self.request.run_node_id}.csv"
        try:
            upload_task = asyncio.create_task(HTTP.system.upload_file(
                artifact["path"], name, file_field="test_file", file_dir="perf/capture", timeout=180,
            ))
            while not upload_task.done():
                await asyncio.wait({upload_task}, timeout=20)
                if not upload_task.done():
                    try:
                        await HTTP.perf.heartbeat(self.request.run_node_id, self.connection_id, {"engine_pid": None})
                    except Exception as heartbeat_error:
                        log.warning(f"性能请求记录上传期间心跳失败：{type(heartbeat_error).__name__}")
            upload = await upload_task
            if upload.success:
                return {**result, "status": "uploaded", "path": upload.path}
            return {**result, "status": "upload_failed", "message": upload.error_message or "上传失败"}
        except Exception as error:
            log.warning(f"性能请求记录上传失败：{type(error).__name__}")
            return {**result, "status": "upload_failed", "message": "对象存储上传失败"}

    async def _wait_until_start(self, delay_seconds: float) -> bool:
        deadline = asyncio.get_running_loop().time() + delay_seconds
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                return True
            await asyncio.sleep(min(10, remaining))
            response = await HTTP.perf.heartbeat(self.request.run_node_id, self.connection_id, {})
            if (response.get("data") or {}).get("stop_requested"):
                self._stopping = True
                return False

    async def _consume(self, ps_process):
        while self.process.returncode is None:
            try:
                line = await asyncio.wait_for(self.process.stdout.readline(), timeout=1.0)
            except asyncio.TimeoutError:
                line = b""
            if line:
                text = line.decode("utf-8", errors="replace").strip()
                if text.startswith("MANGO_METRIC "):
                    payload = json.loads(text[len("MANGO_METRIC "):])
                    await self._send_metric(payload, ps_process)
                elif text.startswith("MANGO_ERROR "):
                    payload = json.loads(text[len("MANGO_ERROR "):])
                    self._pending_errors.append(payload)
                else:
                    log.debug(f"k6: {text[:1000]}")
            await self._flush_outbox()
            await self._flush_errors()
            loop_time = asyncio.get_running_loop().time()
            if loop_time - self._last_control_at >= self.CONTROL_INTERVAL_SECONDS:
                self._last_control_at = loop_time
                response = await HTTP.perf.heartbeat(self.request.run_node_id, self.connection_id, {
                    "engine_pid": self.process.pid,
                })
                control = response.get("data") or {}
                if control.get("stop_requested"):
                    await self.stop()
                    return

    async def _send_metric(self, payload: dict, ps_process):
        points = payload.get("points") or []
        resources = self._resources(ps_process)
        for point in points:
            window_start = datetime.fromisoformat(str(point["window_start"]).replace("Z", "+00:00"))
            point["window_start"] = (window_start + timedelta(milliseconds=self._clock_offset_ms)).replace(microsecond=0).isoformat()
            point["generator_metrics"] = {
                "cpu_percent": resources.get("cpu_percent"), "memory_bytes": resources.get("memory_bytes"),
                "outbox_items": 0,
            }
        batch = {"schema_version": 1, "run_id": self.request.run_id,
                 "run_node_id": self.request.run_node_id, "points": points}
        sequence = int(payload["sequence"])
        PerfMetricOutbox.upsert(self.request.node_key, self.request.run_node_id, sequence, batch)
        await self._flush_outbox()

    async def _flush_outbox(self):
        for row in PerfMetricOutbox.list_due(self.request.node_key):
            try:
                await HTTP.perf.metrics(self.request.run_node_id, self.connection_id, row["payload"])
            except Exception as error:
                PerfMetricOutbox.mark_failed(row["id"], row["retry_count"], error)
                break
            PerfMetricOutbox.delete(row["id"])

    async def _flush_errors(self):
        if not self._pending_errors:
            return
        samples = self._pending_errors[:100]
        try:
            await HTTP.perf.errors(self.request.run_node_id, self.connection_id, {
                "schema_version": 1, "run_id": self.request.run_id,
                "run_node_id": self.request.run_node_id, "samples": samples,
            })
        except Exception as error:
            log.warning(f"性能错误样本暂未上报，将在本次运行内重试: {error}")
            return
        del self._pending_errors[:len(samples)]

    async def stop(self):
        self._stopping = True
        if not self.process or self.process.returncode is not None:
            return
        try:
            os.killpg(self.process.pid, signal.SIGTERM)
            await asyncio.wait_for(self.process.wait(), timeout=10)
        except asyncio.TimeoutError:
            os.killpg(self.process.pid, signal.SIGKILL)
            await self.process.wait()
        except ProcessLookupError:
            pass

    async def _restore_runtime_secrets(self):
        response = await HTTP.perf.secrets(self.request.run_node_id, self.connection_id)
        values = (response.get("data") or {}).get("values") or {}
        if not values:
            return
        payload = self.request.model_dump(mode="python")
        for path, value in values.items():
            target = payload["scenario"]
            parts = path.split(".")
            for part in parts[:-1]:
                target = target[int(part)] if isinstance(target, list) else target[part]
            final = parts[-1]
            if isinstance(target, list):
                target[int(final)] = value
            else:
                target[final] = value
        self.request = PerfExecutionRequest.model_validate(payload)

    async def _synchronize_clock(self):
        started_ms = time.time() * 1000
        response = await HTTP.perf.control(self.request.run_node_id, self.connection_id)
        finished_ms = time.time() * 1000
        server_ms = float((response.get("data") or {}).get("server_epoch_ms") or finished_ms)
        self._clock_offset_ms = int(server_ms - ((started_ms + finished_ms) / 2))

    @staticmethod
    def _resources(process):
        try:
            processes = [process, *process.children(recursive=True)]
            return {
                "cpu_percent": sum(item.cpu_percent() for item in processes),
                "memory_bytes": sum(item.memory_info().rss for item in processes),
            }
        except (psutil.Error, AttributeError):
            return {}

    @staticmethod
    def _engine_version():
        import subprocess
        binary = resolve_k6_binary()
        if not binary:
            return "unavailable"
        try:
            return subprocess.run([binary, "version"], capture_output=True, text=True, timeout=5).stdout.strip()[:32]
        except (OSError, subprocess.SubprocessError):
            return "unknown"
