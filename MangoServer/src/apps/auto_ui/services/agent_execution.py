from __future__ import annotations

import base64
import hashlib
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import binascii
from django.core import signing
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone
from mangotools.enums import TaskEnum
from pydantic import ValidationError

from src.apps.auto_ui.enums import AgentUiArtifactKind, AgentUiStepStatus, UiAuthTypeEnum
from src.apps.auto_ui.exceptions import (
    AutoUiError,
    UI_AGENT_ARTIFACT_INVALID,
    UI_AGENT_CAPABILITY_MISSING,
    UI_AGENT_CASE_CHANGED,
    UI_AGENT_CASE_FEATURE_UNSUPPORTED,
    UI_AGENT_CASE_NOT_FOUND,
    UI_AGENT_COMPLETE_INVALID,
    UI_AGENT_REPORT_INVALID,
    UI_AGENT_STEP_OUT_OF_ORDER,
    UI_AGENT_EXECUTION_TOKEN_INVALID,
    UI_CASE_STEPS_EMPTY,
)
from src.apps.auto_ui.models import PageSteps, UiCase, UiCaseStepsDetailed
from src.apps.auto_ui.schemas.agent_execution import (
    AgentUiCapabilityManifest,
    AgentUiCompletionReport,
    AgentUiEvidencePolicy,
    AgentUiStepReport,
)
from src.apps.auto_ui.services.test_case.test_case import TestCase
from src.apps.auto_ui.services.ui_auth import UiAuthManager
from src.apps.test_center.models import ExecutionResult
from src.apps.test_center.services.execution_result import ExecutionResultService
from src.common.storage import build_public_file_url


class AgentUiExecutionService:
    """由外部智能代理执行 UI Case 的无状态协议服务。"""

    EXECUTION_TOKEN_SALT = "mango.agent-ui-execution.v2"
    ARTIFACT_TOKEN_SALT = "mango.agent-ui-artifact.v2"
    TOKEN_MAX_AGE_SECONDS = 6 * 60 * 60
    MAX_ARTIFACT_BYTES = 8 * 1024 * 1024
    ALLOWED_CONTENT_TYPES = {
        "image/png", "image/jpeg", "image/webp", "text/plain", "application/json", "application/zip",
    }
    SENSITIVE_KEYS = {
        "authorization", "cookie", "password", "token", "secret", "api_key", "apikey",
        "access_token", "refresh_token", "storage_state", "auth_cache", "ui_auth_cache",
    }

    @classmethod
    def get_case(cls, *, case_id: int, parameter_set_index: int = 0) -> dict:
        """返回 Case 结构，不返回环境、授权或运行期敏感数据。"""
        case, case_steps = cls._case_and_steps(case_id, parameter_set_index)
        snapshot = cls._case_snapshot(case, case_steps, parameter_set_index=parameter_set_index)
        return cls._sanitize_value({
            "case_id": case.id,
            "case_name": case.name,
            "project_product_id": case.project_product_id,
            "module_id": case.module_id,
            "case_update_time": case.update_time.isoformat(),
            "parameter_set_count": len(case.parametrize or []),
            "parameter_set_index": parameter_set_index,
            "steps": snapshot["steps"],
            "requires_setup": bool(case.front_custom or case.front_sql),
            "requires_cleanup": bool(case.posterior_sql),
        })

    @classmethod
    def create_execution(
            cls,
            *,
            case_id: int,
            test_env: int,
            user_id: int,
            username: str,
            capability_manifest: dict | None = None,
            evidence_policy: dict | None = None,
            parameter_set_index: int = 0,
    ) -> dict:
        """生成短期执行令牌并一次性返回 Case 运行数据，不创建运行状态记录。"""
        case, case_steps = cls._case_and_steps(case_id, parameter_set_index)
        cls._ensure_supported_case_features(case)
        try:
            capabilities = AgentUiCapabilityManifest.model_validate(capability_manifest or {})
            policy = AgentUiEvidencePolicy.model_validate(evidence_policy or {})
        except ValidationError as error:
            raise AutoUiError(UI_AGENT_REPORT_INVALID, value=(cls._validation_message(error),)) from error
        if not capabilities.available_tools:
            raise AutoUiError(UI_AGENT_CAPABILITY_MISSING)

        auth_page_step = cls._auth_page_step(case, test_env)
        snapshot = cls._case_snapshot(case, case_steps, auth_page_step, parameter_set_index)
        execution_id = uuid.uuid4().hex
        started_at = timezone.now()
        token_payload = {
            "version": 2,
            "execution_id": execution_id,
            "user_id": user_id,
            "case_id": case.id,
            "project_product_id": case.project_product_id,
            "test_env": test_env,
            "case_update_time": case.update_time.isoformat(),
            "parameter_set_index": parameter_set_index,
            "started_at": started_at.isoformat(),
            "steps": [
                {
                    "case_step_id": item["case_step_id"],
                    "page_step_id": item["page_step_id"],
                    "config_version": item["config_version"],
                    "is_auth_step": item["is_auth_step"],
                }
                for item in snapshot["steps"]
            ],
            "evidence_policy": policy.model_dump(mode="json"),
        }
        execution_token = signing.dumps(token_payload, salt=cls.EXECUTION_TOKEN_SALT, compress=True)
        runtime_builder = TestCase(user_id, username, test_env, is_send=False)
        runtime_steps = []
        for index, snapshot_step in enumerate(snapshot["steps"]):
            case_step = None
            if snapshot_step["is_auth_step"]:
                page_step = auth_page_step
            else:
                case_step = next(item for item in case_steps if item.id == snapshot_step["case_step_id"])
                page_step = case_step.page_step
            runtime = runtime_builder.case_steps_model(
                page_step.id,
                case_steps_detailed=case_step,
                switch_step_open_url=bool(case_step.switch_step_open_url) if case_step else True,
                is_auth_step=snapshot_step["is_auth_step"],
                front_public_ids=case.front_public,
            )
            runtime_steps.append({
                "step_index": index,
                "case_step_id": snapshot_step["case_step_id"],
                "page_step_id": snapshot_step["page_step_id"],
                "is_auth_step": snapshot_step["is_auth_step"],
                "runtime_step": runtime.model_dump(mode="json"),
            })
        browser_auth = runtime_builder.ui_auth_cache(case.project_product_id, case.front_auth_config)
        parameter_sets = case.parametrize or []
        selected_parameter_set = parameter_sets[parameter_set_index] if parameter_sets else None
        return {
            "execution_id": execution_id,
            "execution_token": execution_token,
            "case_id": case.id,
            "case_name": case.name,
            "project_product_id": case.project_product_id,
            "test_env_id": test_env,
            "started_at": started_at.isoformat(),
            "runtime_steps": runtime_steps,
            "browser_auth": browser_auth.model_dump(mode="json") if browser_auth else None,
            "case_context": {
                "front_custom": case.front_custom,
                "front_sql": case.front_sql,
                "selected_parameter_set": selected_parameter_set,
                "posterior_sql": case.posterior_sql,
            },
            "evidence_policy": policy.model_dump(mode="json"),
            "security_notice": "运行数据可能包含授权和环境信息，仅用于本次执行，不得写入日志或回答正文。",
        }

    @classmethod
    @transaction.atomic
    def report_step(
            cls,
            *,
            execution_token: str,
            project_product_id: int,
            user_id: int,
            step_index: int,
            report: dict,
    ) -> dict:
        token_data, case = cls._execution_context(execution_token, user_id, project_product_id)
        steps = token_data["steps"]
        if step_index < 0 or step_index >= len(steps):
            raise AutoUiError(UI_AGENT_STEP_OUT_OF_ORDER)
        snapshot_step = steps[step_index]
        cls._validate_step_version(snapshot_step)
        try:
            step_report = AgentUiStepReport.model_validate(report)
        except ValidationError as error:
            raise AutoUiError(UI_AGENT_REPORT_INVALID, value=(cls._validation_message(error),)) from error
        artifact_refs = list(step_report.artifact_refs)
        for assertion in step_report.assertion_results:
            artifact_refs.extend(assertion.evidence_artifact_refs)
        artifact_data = [
            cls._verify_artifact_ref(value, token_data, expected_step_index=step_index)
            for value in dict.fromkeys(artifact_refs)
        ]
        trace_id = cls._step_trace_id(token_data["execution_id"], step_index, step_report.idempotency_key)
        existing = ExecutionResult.objects.filter(
            source_type=ExecutionResultService.SOURCE_MCP,
            target_type=ExecutionResultService.TARGET_UI_PAGE_STEP,
            target_id=snapshot_step["page_step_id"],
            trace_id=trace_id,
        ).first()
        if existing:
            return {"duplicate": True, "execution_result_id": existing.id, "step_index": step_index}

        passed = step_report.status in {AgentUiStepStatus.PASSED.value, AgentUiStepStatus.SKIPPED.value}
        status = TaskEnum.SUCCESS.value if passed else TaskEnum.FAIL.value
        result = cls._sanitize_value({
            **cls._step_report_payload(step_report),
            "execution_id": token_data["execution_id"],
            "step_index": step_index,
            "case_step_id": snapshot_step["case_step_id"],
            "page_step_id": snapshot_step["page_step_id"],
            "artifacts": artifact_data,
            "reported_at": timezone.now().isoformat(),
        })
        execution_result = ExecutionResultService.save_result(
            source_type=ExecutionResultService.SOURCE_MCP,
            target_type=ExecutionResultService.TARGET_UI_PAGE_STEP,
            target_id=snapshot_step["page_step_id"],
            test_env=token_data["test_env"],
            status=status,
            error_message=step_report.error_message,
            duration=(step_report.duration_ms / 1000) if step_report.duration_ms is not None else None,
            trigger_user_id=user_id,
            trace_id=trace_id,
            source_snapshot={
                "runner": "agent_ui", "execution_id": token_data["execution_id"],
                "case_id": case.id, "step_index": step_index,
            },
            result_data=result,
        )
        if snapshot_step.get("case_step_id"):
            UiCaseStepsDetailed.objects.filter(id=snapshot_step["case_step_id"], case_id=case.id).update(
                status=status, error_message=step_report.error_message,
            )
        PageSteps.objects.filter(id=snapshot_step["page_step_id"]).update(status=status)
        return {
            "duplicate": False,
            "execution_result_id": execution_result.id,
            "step_index": step_index,
            "status": step_report.status,
        }

    @classmethod
    def upload_artifact(
            cls,
            *,
            execution_token: str,
            project_product_id: int,
            user_id: int,
            file_name: str,
            content_type: str,
            content_base64: str,
            kind: str = "screenshot",
            step_index: int | None = None,
    ) -> dict:
        token_data, _ = cls._execution_context(execution_token, user_id, project_product_id)
        if step_index is not None and (step_index < 0 or step_index >= len(token_data["steps"])):
            raise AutoUiError(UI_AGENT_STEP_OUT_OF_ORDER)
        if content_type not in cls.ALLOWED_CONTENT_TYPES:
            raise AutoUiError(UI_AGENT_ARTIFACT_INVALID, value=(f"不支持的类型 {content_type}",))
        if kind not in {item.value for item in AgentUiArtifactKind}:
            raise AutoUiError(UI_AGENT_ARTIFACT_INVALID, value=(f"不支持的证据类型 {kind}",))
        try:
            raw = base64.b64decode(content_base64, validate=True)
        except (ValueError, binascii.Error) as error:
            raise AutoUiError(UI_AGENT_ARTIFACT_INVALID, value=("content_base64 不是有效 Base64",)) from error
        if not raw or len(raw) > cls.MAX_ARTIFACT_BYTES:
            raise AutoUiError(UI_AGENT_ARTIFACT_INVALID, value=("文件为空或超过 8 MiB",))

        artifact_id = uuid.uuid4().hex
        safe_name = cls._safe_file_name(file_name)
        object_key = (
            f"uitest/agent-executions/{timezone.now():%Y/%m/%d}/{token_data['execution_id']}/"
            f"{artifact_id}-{safe_name}"
        )
        saved_name = default_storage.save(object_key, ContentFile(raw)).replace("\\", "/")
        artifact = {
            "artifact_id": artifact_id,
            "execution_id": token_data["execution_id"],
            "kind": kind,
            "file_name": safe_name,
            "content_type": content_type,
            "size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "object_key": saved_name,
            "step_index": step_index,
            "created_at": timezone.now().isoformat(),
        }
        artifact_ref = signing.dumps(artifact, salt=cls.ARTIFACT_TOKEN_SALT, compress=True)
        return {
            "artifact_id": artifact_id,
            "artifact_ref": artifact_ref,
            "kind": kind,
            "file_name": safe_name,
            "size": len(raw),
            "sha256": artifact["sha256"],
            "step_index": step_index,
            "url": build_public_file_url(saved_name),
        }

    @classmethod
    @transaction.atomic
    def complete_execution(
            cls,
            *,
            execution_token: str,
            project_product_id: int,
            user_id: int,
            report: dict,
    ) -> dict:
        token_data, case = cls._execution_context(execution_token, user_id, project_product_id)
        try:
            completion = AgentUiCompletionReport.model_validate(report)
        except ValidationError as error:
            raise AutoUiError(UI_AGENT_REPORT_INVALID, value=(cls._validation_message(error),)) from error
        if completion.status == AgentUiStepStatus.PASSED.value and len(completion.steps) != len(token_data["steps"]):
            raise AutoUiError(UI_AGENT_COMPLETE_INVALID)
        seen_indexes = set()
        step_results = []
        for item in completion.steps:
            if item.step_index in seen_indexes or item.step_index < 0 or item.step_index >= len(token_data["steps"]):
                raise AutoUiError(UI_AGENT_STEP_OUT_OF_ORDER)
            seen_indexes.add(item.step_index)
            if completion.status == AgentUiStepStatus.PASSED.value and item.report.status not in {
                AgentUiStepStatus.PASSED.value,
                AgentUiStepStatus.SKIPPED.value,
            }:
                raise AutoUiError(UI_AGENT_COMPLETE_INVALID)
            step_payload = cls._step_report_payload(item.report)
            step_payload["step_index"] = item.step_index
            step_artifact_refs = list(item.report.artifact_refs)
            for assertion in item.report.assertion_results:
                step_artifact_refs.extend(assertion.evidence_artifact_refs)
            step_payload["artifacts"] = [
                cls._verify_artifact_ref(value, token_data, expected_step_index=item.step_index)
                for value in dict.fromkeys(step_artifact_refs)
            ]
            step_results.append(step_payload)
        artifacts = [cls._verify_artifact_ref(value, token_data) for value in completion.artifact_refs]
        passed = completion.status == AgentUiStepStatus.PASSED.value
        status = TaskEnum.SUCCESS.value if passed else TaskEnum.FAIL.value
        case.status = status
        case.save(update_fields=["status"])
        started_at = datetime.fromisoformat(token_data["started_at"])
        duration_seconds = (
            completion.duration_ms / 1000
            if completion.duration_ms is not None
            else max((timezone.now() - started_at).total_seconds(), 0)
        )
        result_data = cls._sanitize_value({
            "execution_id": token_data["execution_id"],
            "runner": "agent_ui",
            "status": completion.status,
            "summary": completion.summary,
            "error_message": completion.error_message,
            "steps": step_results,
            "artifacts": artifacts,
        })
        execution_result = ExecutionResultService.save_result(
            source_type=ExecutionResultService.SOURCE_MCP,
            target_type=ExecutionResultService.TARGET_UI_CASE,
            target_id=case.id,
            test_env=token_data["test_env"],
            status=status,
            error_message=completion.error_message,
            duration=duration_seconds,
            trigger_user_id=user_id,
            trace_id=token_data["execution_id"],
            source_snapshot={
                "runner": "agent_ui",
                "case_update_time": token_data["case_update_time"],
                "parameter_set_index": token_data["parameter_set_index"],
            },
            result_data=result_data,
        )
        return {
            "execution_id": token_data["execution_id"],
            "execution_result_id": execution_result.id,
            "case_id": case.id,
            "status": completion.status,
            "completed_steps": len(completion.steps),
            "total_steps": len(token_data["steps"]),
        }

    @classmethod
    def _case_and_steps(cls, case_id: int, parameter_set_index: int):
        case = UiCase.objects.select_related("project_product", "module").filter(id=case_id).first()
        if case is None:
            raise AutoUiError(UI_AGENT_CASE_NOT_FOUND)
        case_steps = list(
            UiCaseStepsDetailed.objects.select_related("page_step", "page_step__page")
            .filter(case_id=case_id).order_by("case_sort", "id")
        )
        if not case_steps:
            raise AutoUiError(UI_CASE_STEPS_EMPTY)
        parameter_sets = case.parametrize or []
        if (
                parameter_set_index < 0
                or (parameter_sets and parameter_set_index >= len(parameter_sets))
                or (not parameter_sets and parameter_set_index != 0)
        ):
            raise AutoUiError(UI_AGENT_REPORT_INVALID, value=("parameter_set_index 超出 Case 参数组范围",))
        return case, case_steps

    @staticmethod
    def _auth_page_step(case: UiCase, test_env: int):
        auth = UiAuthManager.get_enabled_auth_configs(
            case.project_product_id, test_env, case.front_auth_config,
        ).filter(
            auth_type=UiAuthTypeEnum.PAGE_STEP.value,
            page_step_id__isnull=False,
        ).select_related("page_step", "page_step__page").first()
        return auth.page_step if auth else None

    @classmethod
    def _execution_context(cls, token: str, user_id: int, project_product_id: int):
        try:
            data = signing.loads(token, salt=cls.EXECUTION_TOKEN_SALT, max_age=cls.TOKEN_MAX_AGE_SECONDS)
        except signing.BadSignature as error:
            raise AutoUiError(UI_AGENT_EXECUTION_TOKEN_INVALID) from error
        if data.get("version") != 2 or data.get("user_id") != user_id:
            raise AutoUiError(UI_AGENT_EXECUTION_TOKEN_INVALID)
        if data.get("project_product_id") != project_product_id:
            raise AutoUiError(UI_AGENT_EXECUTION_TOKEN_INVALID)
        case = UiCase.objects.filter(id=data.get("case_id"), project_product_id=project_product_id).first()
        if case is None or case.update_time.isoformat() != data.get("case_update_time"):
            raise AutoUiError(UI_AGENT_CASE_CHANGED)
        return data, case

    @staticmethod
    def _validate_step_version(snapshot_step: dict):
        page_step = PageSteps.objects.filter(id=snapshot_step["page_step_id"]).first()
        if page_step is None or page_step.config_version != snapshot_step["config_version"]:
            raise AutoUiError(UI_AGENT_CASE_CHANGED)

    @classmethod
    def _verify_artifact_ref(cls, ref: str, token_data: dict, expected_step_index: int | None = None) -> dict:
        try:
            artifact = signing.loads(ref, salt=cls.ARTIFACT_TOKEN_SALT, max_age=cls.TOKEN_MAX_AGE_SECONDS)
        except signing.BadSignature as error:
            raise AutoUiError(UI_AGENT_ARTIFACT_INVALID, value=("附件引用无效或已过期",)) from error
        if artifact.get("execution_id") != token_data["execution_id"]:
            raise AutoUiError(UI_AGENT_ARTIFACT_INVALID, value=("附件不属于本次执行",))
        if expected_step_index is not None and artifact.get("step_index") not in {None, expected_step_index}:
            raise AutoUiError(UI_AGENT_ARTIFACT_INVALID, value=("附件不属于当前步骤",))
        return {
            key: artifact[key]
            for key in (
                "artifact_id", "kind", "file_name", "content_type", "size", "sha256", "object_key",
                "step_index", "created_at",
            )
        }

    @staticmethod
    def _step_trace_id(execution_id: str, step_index: int, idempotency_key: str) -> str:
        return hashlib.sha256(f"{execution_id}:{step_index}:{idempotency_key}".encode()).hexdigest()[:64]

    @staticmethod
    def _step_report_payload(report: AgentUiStepReport) -> dict:
        payload = report.model_dump(mode="json")
        payload.pop("artifact_refs", None)
        for assertion in payload.get("assertion_results", []):
            assertion.pop("evidence_artifact_refs", None)
        return payload

    @staticmethod
    def _case_snapshot(case, case_steps, auth_page_step=None, parameter_set_index=0):
        steps = []
        if auth_page_step:
            steps.append({
                "case_step_id": None, "case_sort": -1, "page_step_id": auth_page_step.id,
                "page_step_name": auth_page_step.name, "page_id": auth_page_step.page_id,
                "page_url": auth_page_step.page.url, "config_version": auth_page_step.config_version,
                "goal": auth_page_step.goal, "entry_criteria": auth_page_step.entry_criteria,
                "success_criteria": auth_page_step.success_criteria, "switch_step_open_url": 1,
                "is_auth_step": True,
            })
        steps.extend({
                         "case_step_id": item.id, "case_sort": item.case_sort, "page_step_id": item.page_step_id,
                         "page_step_name": item.page_step.name, "page_id": item.page_step.page_id,
                         "page_url": item.page_step.page.url, "config_version": item.page_step.config_version,
                         "goal": item.page_step.goal, "entry_criteria": item.page_step.entry_criteria,
                         "success_criteria": item.page_step.success_criteria,
                         "switch_step_open_url": item.switch_step_open_url, "is_auth_step": False,
                     } for item in case_steps)
        return {
            "case_id": case.id, "case_name": case.name, "case_update_time": case.update_time.isoformat(),
            "project_product_id": case.project_product_id, "module_id": case.module_id,
            "parameter_set_index": parameter_set_index, "steps": steps,
        }

    @classmethod
    def _sanitize_value(cls, value: Any, key: str = "") -> Any:
        if key.lower() in cls.SENSITIVE_KEYS:
            return "***"
        if isinstance(value, dict):
            return {str(item_key): cls._sanitize_value(item, str(item_key)) for item_key, item in value.items()}
        if isinstance(value, list):
            return [cls._sanitize_value(item) for item in value]
        if isinstance(value, str):
            return value[:4000]
        return value

    @staticmethod
    def _safe_file_name(file_name: str) -> str:
        name = Path(file_name or "artifact.bin").name
        name = re.sub(r"[^0-9A-Za-z._\-\u4e00-\u9fff]", "_", name)[:120]
        return name or "artifact.bin"

    @staticmethod
    def _ensure_supported_case_features(case: UiCase):
        from mangotools.enums import StatusEnum
        from src.apps.data_factory.enums import DataFactoryCaseSourceTypeEnum
        from src.apps.data_factory.models import DataFactoryCaseConfig
        from src.apps.gray_config.enums import GrayCaseScopeEnum, GrayCaseTypeEnum
        from src.apps.gray_config.models import AutomationCaseGrayConfig

        unsupported = []
        if DataFactoryCaseConfig.objects.filter(
                source_type=DataFactoryCaseSourceTypeEnum.UI_CASE.value,
                source_id=case.id,
                status=StatusEnum.SUCCESS.value,
        ).exists():
            unsupported.append("数据工厂绑定")
        if AutomationCaseGrayConfig.objects.filter(
                case_type=GrayCaseTypeEnum.UI.value,
                scope=GrayCaseScopeEnum.CASE.value,
                ui_case_id=case.id,
                status=StatusEnum.SUCCESS.value,
        ).exists():
            unsupported.append("灰度配置切换")
        if unsupported:
            raise AutoUiError(UI_AGENT_CASE_FEATURE_UNSUPPORTED, value=("、".join(unsupported),))

    @staticmethod
    def _validation_message(error: ValidationError) -> str:
        return "; ".join(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors()[:10]
        )


__all__ = ["AgentUiExecutionService"]
