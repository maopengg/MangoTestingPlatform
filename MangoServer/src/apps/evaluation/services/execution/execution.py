import math
import statistics
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from threading import Event, Thread
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from django.db import close_old_connections, transaction
from django.db.models import Q
from django.utils import timezone
from pydantic import ValidationError
from src.apps.evaluation.formatters.case_description import case_description
from src.apps.evaluation.enums import (
    EvaluationExecutionStatusEnum,
    EvaluationGradeStatusEnum,
    EvaluationCaseExecutionStatusEnum,
    EvaluationVerdictEnum,
    EvaluationTriggerTypeEnum,
)
from src.apps.evaluation.exceptions import (
    EVALUATION_DATASET_HAS_NO_ITEMS,
    EVALUATION_GRADER_UNAVAILABLE,
    EVALUATION_OBJECT_NOT_FOUND,
    EVALUATION_EXECUTION_NOT_FOUND,
    EVALUATION_EXECUTION_OPERATION_NOT_ALLOWED,
    EVALUATION_TARGET_CONFIG_INVALID,
    EvaluationError,
)
from src.apps.evaluation.formatters.payload import content_hash, decimal_score, mask_sensitive
from src.apps.evaluation.models import (
    EvaluationGradeResult,
    EvaluationCase,
    EvaluationCaseExecution,
    EvaluationItemResult,
)
from src.apps.evaluation.schemas import EvaluationCaseExecutionCreate, EvaluationExecutionSnapshot
from src.apps.evaluation.services.grading.grading import resolve_graders
from src.apps.evaluation.services.assets.validation import invalid_config
from src.apps.evaluation.schemas.detail import EvaluationGradeSnapshot
from src.apps.evaluation.selectors.scope import ensure_product_scope
from src.apps.evaluation.services.targets.adapters import EvaluationTargetAdapterRegistry
from src.apps.evaluation.services.execution.attempt import EvaluationAttemptService
from src.apps.evaluation.services.model.answer import answer_model_snapshot, generate_answer
from src.apps.evaluation.services.grading.graders import EvaluationGraderRegistry
from src.apps.evaluation.services.execution.failure import failure_message
from src.apps.evaluation.services.assets.case import EvaluationCaseService
from src.apps.evaluation.services.execution.item_detail import update_item_details
from types import SimpleNamespace


class EvaluationCaseExecutionService:
    _executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="evaluation-execution")

    @classmethod
    @transaction.atomic
    def create(cls, values: dict, user):
        try:
            payload = EvaluationCaseExecutionCreate.model_validate(values)
        except ValidationError as error:
            raise invalid_config(str(error)) from error
        case = EvaluationCase.objects.select_for_update().select_related(
            "project_product", "module", "dataset_version__dataset",
        ).filter(id=payload.case_id).first()
        if case is None:
            raise EvaluationError(EVALUATION_OBJECT_NOT_FOUND)
        ensure_product_scope(user, case.project_product_id)
        request_hash = content_hash(payload.model_dump(mode="json", exclude={"idempotency_key"}))
        key = "eval:" + content_hash({"user": user.id, "case": case.id, "environment": payload.test_env, "key": payload.idempotency_key}) if payload.idempotency_key else None
        if key:
            existing = EvaluationCaseExecution.objects.filter(idempotency_key=key).first()
            if existing:
                if existing.snapshot["request"]["payload_hash"] != request_hash:
                    raise invalid_config("相同幂等键不能提交不同的执行请求")
                return existing
        config, target = EvaluationCaseService.validate_execution(case, user)
        from src.apps.evaluation.services.workflow.workflow_resources import freeze_dataset_configuration
        dataset_config = freeze_dataset_configuration(case.dataset_version.schema_snapshot, user, product_id=case.project_product_id, target_ref_id=config.target.ref_id)
        items = EvaluationCaseService.selected_items(case.dataset_version, config, payload.item_ids)
        from src.apps.evaluation.services.dataset.versioning import EvaluationVersionService
        target_values = config.target.model_dump(mode="json")
        checksum = EvaluationVersionService.target_version_checksum(target)
        if not checksum:
            raise invalid_config("无法核实目标固定版本的内容摘要")
        target_values.update(content_hash=checksum, config_verified=True,
                             version_verified=target_values["type"] == "script")
        bindings, implementations, snapshots = {}, {}, []
        judge_snapshots = {}
        for item in items:
            item_snapshot = {"id": item.id, **EvaluationVersionService.item_payload(item)}
            from src.apps.evaluation.services.dataset.item_source import freeze_item_source
            item_snapshot["data_source"] = freeze_item_source(item_snapshot.get("data_source"), user, product_id=case.project_product_id)
            if getattr(item, "_dependency_only", False):
                item_snapshot["dependency_only"] = True
            item_snapshot["content_hash"] = item.content_hash
            references = []
            for binding, source in resolve_graders(config.grading, item.grading_config):
                frozen = binding.model_dump(mode="json")
                if EvaluationGraderRegistry.is_model(binding.grader_key):
                    from src.apps.evaluation.services.model.ai import model_snapshot
                    prompt_id = EvaluationGraderRegistry.prompt_id(binding.grader_key)
                    if prompt_id not in judge_snapshots:
                        judge_snapshots[prompt_id] = model_snapshot(config.ai.judge_profile_id, prompt_id)
                    frozen["parameters"] = {**frozen["parameters"], "_judge_snapshot": judge_snapshots[prompt_id]}
                digest = content_hash(frozen)
                bindings[digest] = frozen
                implementations[digest] = EvaluationGraderRegistry.implementation_hash(binding.grader_key, binding.grader_version)
                references.append({"binding_hash": digest, "source": source})
            item_snapshot["effective_graders"] = references
            snapshots.append((item, mask_sensitive(item_snapshot)))
        selection = {"item_ids": [item.id for item in items], "items_hash": content_hash([data for _, data in snapshots]),
                     "scope": "subset" if payload.item_ids is not None else "full"}
        snapshot = {
            "schema_version": 1, "hash_version": 1,
            "case": {"id": case.id, "name": case.name, "description": case_description(case), "config_hash": content_hash(case.config)},
            "dataset": {"id": case.dataset_version.dataset_id, "version_id": case.dataset_version_id,
                        "version_no": case.dataset_version.version_no, "content_hash": case.dataset_version.content_hash},
            "selection": selection, "target": target_values, "mapping": config.mapping.model_dump(mode="json"),
            "grader_bindings": bindings, "grader_implementations": implementations,
            "grading": {"aggregation": config.grading.aggregation.model_dump(mode="json"),
                        "quality_gates": [gate.model_dump(mode="json") for gate in config.grading.quality_gates]},
            "execution": config.execution.model_dump(mode="json"), "environment": {"test_env": payload.test_env},
            "request": {"payload_hash": request_hash}, "signatures": {},
            "input_variable": dataset_config.input_variables[0].name,
            "dataset_config": dataset_config.model_dump(mode="json"),
            "answering": config.answering.model_dump(mode="json") if config.answering else None,
            "answer_model": answer_model_snapshot(config.ai.answer_profile_id) if config.answering else None,
            "summary_model": None,
        }
        if config.ai.summary_profile_id:
            from src.apps.evaluation.services.model.ai import model_snapshot
            snapshot["summary_model"] = model_snapshot(config.ai.summary_profile_id, "evaluation.summary")
        snapshot = EvaluationExecutionSnapshot.model_validate(snapshot).model_dump(mode="json")
        snapshot["signatures"] = {
            "dataset": content_hash({"dataset": snapshot["dataset"], "selection": selection}),
            "grading": content_hash({"bindings": bindings, "implementations": implementations, "grading": snapshot["grading"]}),
            "execution": content_hash({"mapping": snapshot["mapping"], "dataset_config": snapshot["dataset_config"], "execution": snapshot["execution"], "environment": snapshot["environment"], "answering": snapshot["answering"]}),
            "target": content_hash({"retrieval": target_values, "answer_model": snapshot["answer_model"]}) if config.answering else content_hash(target_values),
        }
        snapshot["signatures"]["manifest"] = content_hash(snapshot)
        snapshot = EvaluationExecutionSnapshot.model_validate(snapshot).model_dump(mode="json")
        execution = EvaluationCaseExecution.objects.create(case=case, dataset_version=case.dataset_version,
            test_env=payload.test_env, trigger_type=payload.trigger_type, idempotency_key=key, snapshot=snapshot, created_by=user)
        EvaluationItemResult.objects.bulk_create([
            EvaluationItemResult(execution=execution, dataset_item=item,
                                 repeat_index=repeat, item_snapshot=deepcopy(data))
            for item, data in snapshots for repeat in range(1, config.execution.repeat_count + 1)
        ], batch_size=500)
        from src.apps.evaluation.services.reporting.report import create_report
        create_report(execution, case, user)
        return execution

    @classmethod
    def submit(cls, execution_id):
        worker_id = f"web-{uuid.uuid4().hex}"
        cls._executor.submit(cls._execute_safe, execution_id, worker_id)

    @classmethod
    def _execute_safe(cls, execution_id, worker_id=None):
        worker_id = worker_id or f"worker-{uuid.uuid4().hex}"
        close_old_connections()
        try:
            cls.execute(execution_id, worker_id=worker_id)
        except Exception as error:
            previous_details = EvaluationCaseExecution.objects.filter(id=execution_id).values_list("details", flat=True).first() or {}
            EvaluationCaseExecution.objects.filter(
                id=execution_id,
                lease_owner=worker_id,
                status__in=[
                    EvaluationCaseExecutionStatusEnum.PREPARING.value,
                    EvaluationCaseExecutionStatusEnum.RUNNING.value,
                    EvaluationCaseExecutionStatusEnum.AGGREGATING.value,
                    EvaluationCaseExecutionStatusEnum.STOPPING.value,
                ],
            ).update(
                status=EvaluationCaseExecutionStatusEnum.FAILED.value,
                verdict=EvaluationVerdictEnum.INVALID.value,
                details={**previous_details, "schema_version": 1, "error_category": "execution_failed", "error_message": failure_message(error), "diagnostic_ref": {}}, finished_at=timezone.now(),
                lease_owner=None, lease_expires_at=None, update_time=timezone.now(),
            )
        finally:
            from src.apps.evaluation.services.reporting.report import sync_report
            record = EvaluationCaseExecution.objects.filter(id=execution_id).first()
            if record is not None:
                sync_report(record)
            close_old_connections()

    @classmethod
    def execute(cls, execution_id, worker_id=None):
        worker_id = worker_id or f"worker-{uuid.uuid4().hex}"
        now = timezone.now()
        lease_expires_at = now + timedelta(minutes=15)
        claimed = EvaluationCaseExecution.objects.filter(
            Q(status=EvaluationCaseExecutionStatusEnum.PENDING.value)
            | Q(
                status__in=[
                    EvaluationCaseExecutionStatusEnum.PREPARING.value,
                    EvaluationCaseExecutionStatusEnum.RUNNING.value,
                    EvaluationCaseExecutionStatusEnum.AGGREGATING.value,
                    EvaluationCaseExecutionStatusEnum.STOPPING.value,
                ],
            ) & (Q(lease_expires_at__lt=now) | Q(lease_expires_at__isnull=True)),
            id=execution_id,
        ).update(
            status=EvaluationCaseExecutionStatusEnum.PREPARING.value,
            finished_at=None,
            lease_owner=worker_id,
            lease_expires_at=lease_expires_at,
            update_time=now,
        )
        execution = EvaluationCaseExecution.objects.select_related("created_by", "case").filter(id=execution_id).first()
        if not execution:
            raise EvaluationError(EVALUATION_EXECUTION_NOT_FOUND)
        # 重复提交只返回当前运行，不得把已完成或执行中的运行覆盖为失败。
        if not claimed:
            return execution
        from src.apps.evaluation.services.reporting.report import sync_report
        sync_report(execution)
        if execution.stop_requested:
            return cls._finish_stopped(execution)
        if execution.started_at is None:
            execution.started_at = now
            execution.save(update_fields=["started_at", "update_time"])
        with cls._renew_lease(execution.id, worker_id):
            config = EvaluationExecutionSnapshot.model_validate(execution.snapshot)
            cls._heartbeat(execution.id, worker_id, config.execution.item_timeout_seconds)
            target_snapshot = execution.snapshot.get("target") or {}
            frozen_target = EvaluationCaseService.runtime_target(target_snapshot, execution.case.project_product_id)
            frozen_mapping = SimpleNamespace(input_variable=config.input_variable,
                                             input_variables=[item.model_dump() for item in config.dataset_config.input_variables],
                                             output_mapping=config.mapping.output.model_dump(mode="json"))
            EvaluationCaseService.ensure_target_access(frozen_target, execution.created_by)
            adapter = EvaluationTargetAdapterRegistry.get(frozen_target.target_type)
            adapter.validate_target(frozen_target)
            from src.apps.evaluation.services.dataset.versioning import EvaluationVersionService
            frozen_checksum = target_snapshot.get("content_hash")
            if frozen_checksum and EvaluationVersionService.target_version_checksum(frozen_target) != frozen_checksum:
                raise EvaluationError(EVALUATION_TARGET_CONFIG_INVALID, value=("评测目标固定版本校验失败",))
            cls._validate_graders(config)
            item_results = list(execution.item_results.select_related("dataset_item").order_by("id"))
            cls._validate_snapshot(execution.snapshot, item_results)
            from src.apps.evaluation.services.workflow.workflow_resources import freeze_dataset_configuration
            freeze_dataset_configuration(config.dataset_config.model_dump(mode="json"), execution.created_by, product_id=execution.case.project_product_id, target_ref_id=config.target.get("ref_id"))
            if config.dataset_config.workflow.steps or config.dataset_config.workflow.sequence.value != "independent" or any((row.item_snapshot.get("data_source") or {}).get("kind", "manual") != "manual" for row in item_results):
                return cls._execute_workflow(execution, config, adapter, frozen_target, frozen_mapping, item_results, worker_id)
            execution.status = EvaluationCaseExecutionStatusEnum.RUNNING.value
            execution.save(update_fields=["status", "update_time"])
            total = len(item_results)
            completed_count = sum(
                item_result.grade_status in {EvaluationGradeStatusEnum.GRADED.value, EvaluationGradeStatusEnum.INVALID.value, EvaluationGradeStatusEnum.FAILED.value}
                for item_result in item_results
            )
            pending_item_results = [
                item_result for item_result in item_results
                if item_result.grade_status not in {EvaluationGradeStatusEnum.GRADED.value, EvaluationGradeStatusEnum.INVALID.value, EvaluationGradeStatusEnum.FAILED.value}
            ]
            if config.execution.max_concurrency > 1 and not config.execution.stop_on_critical_failure:
                stop_detected = False
                with ThreadPoolExecutor(
                    max_workers=config.execution.max_concurrency,
                    thread_name_prefix=f"evaluation-{execution.id}",
                ) as executor:
                    futures = {
                        executor.submit(
                            cls._execute_item_in_thread,
                            execution.id, item_result.id, config, frozen_target, frozen_mapping,
                        ): item_result.id
                        for item_result in pending_item_results
                    }
                    for future in as_completed(futures):
                        future.result()
                        completed_count += 1
                        EvaluationCaseExecution.objects.filter(id=execution.id).update(
                            progress=min(99, int(completed_count / total * 100)),
                        )
                        cls._heartbeat(execution.id, worker_id, config.execution.item_timeout_seconds)
                        if EvaluationCaseExecution.objects.filter(id=execution.id, stop_requested=True).exists():
                            stop_detected = True
                            for queued in futures:
                                if not queued.running() and not queued.done():
                                    queued.cancel()
                            break
                execution.refresh_from_db(fields=["stop_requested"])
                if stop_detected or execution.stop_requested:
                    return cls._finish_stopped(execution)
            else:
                for item_result in pending_item_results:
                    execution.refresh_from_db(fields=["stop_requested"])
                    if execution.stop_requested:
                        return cls._finish_stopped(execution)
                    cls._execute_item(execution, item_result, config, adapter, frozen_target, frozen_mapping)
                    completed_count += 1
                    EvaluationCaseExecution.objects.filter(id=execution.id).update(progress=min(99, int(completed_count / total * 100)))
                    cls._heartbeat(execution.id, worker_id, config.execution.item_timeout_seconds)
                    if (
                        config.execution.stop_on_critical_failure
                        and item_result.grade_results.filter(hard_gate=True, passed=False).exists()
                    ):
                        cls._cancel_pending_items(execution, "critical_gate_stopped")
                        break
            execution.refresh_from_db(fields=["stop_requested"])
            if execution.stop_requested:
                return cls._finish_stopped(execution)
            execution.status = EvaluationCaseExecutionStatusEnum.AGGREGATING.value
            execution.save(update_fields=["status", "update_time"])
            cls.aggregate(execution, config)
            return execution

    @classmethod
    @contextmanager
    def _renew_lease(cls, execution_id, worker_id):
        stopped = Event()

        def renew():
            close_old_connections()
            try:
                while not stopped.wait(30):
                    cls._heartbeat(execution_id, worker_id)
            finally:
                close_old_connections()

        worker = Thread(target=renew, name=f"evaluation-lease-{execution_id}", daemon=True)
        worker.start()
        try:
            yield
        finally:
            stopped.set()
            worker.join(timeout=2)

    @staticmethod
    def _validate_snapshot(snapshot, rows):
        if "item_ids" not in snapshot.get("selection", {}):
            raise invalid_config("历史执行使用条目编码，请按当前用例配置重新执行")
        frozen = deepcopy(snapshot)
        manifest = frozen["signatures"].pop("manifest", None)
        if not manifest or content_hash(frozen) != manifest:
            raise invalid_config("执行配置快照摘要不匹配")
        selected = rows
        if snapshot["selection"]["scope"] != "retry_subset":
            unique = {}
            for row in rows:
                unique.setdefault(row.dataset_item_id, row)
            selected = list(unique.values())
        if content_hash([row.item_snapshot for row in selected]) != snapshot["selection"]["items_hash"]:
            raise invalid_config("执行数据快照摘要不匹配")

    @classmethod
    def _execute_item_in_thread(cls, execution_id, item_result_id, config, frozen_target, frozen_mapping):
        close_old_connections()
        try:
            execution = EvaluationCaseExecution.objects.select_related("created_by", "case").get(id=execution_id)
            item_result = EvaluationItemResult.objects.select_related("dataset_item").get(id=item_result_id)
            adapter = EvaluationTargetAdapterRegistry.get(frozen_target.target_type)
            cls._execute_item(execution, item_result, config, adapter, frozen_target, frozen_mapping)
        finally:
            close_old_connections()

    @staticmethod
    def _finish_stopped(execution):
        EvaluationCaseExecutionService._cancel_pending_items(execution, "execution_stopped")
        execution.status = EvaluationCaseExecutionStatusEnum.STOPPED.value
        execution.verdict = EvaluationVerdictEnum.INVALID.value
        execution.finished_at = timezone.now()
        execution.lease_owner = None
        execution.lease_expires_at = None
        execution.save(update_fields=[
            "status", "verdict", "finished_at", "lease_owner", "lease_expires_at", "update_time",
        ])
        from src.apps.evaluation.services.reporting.report import sync_report
        sync_report(execution)
        return execution

    @classmethod
    def _execute_workflow(cls, execution, config, adapter, target, mapping, rows, worker_id):
        from src.apps.evaluation.services.workflow.workflow_execution import execute_dataset_workflow
        return execute_dataset_workflow(cls, execution, config, adapter, target, mapping, rows, worker_id)

    @staticmethod
    def _cancel_pending_items(execution, reason):
        execution.item_results.exclude(grade_status__in=[
            EvaluationGradeStatusEnum.GRADED.value, EvaluationGradeStatusEnum.INVALID.value,
            EvaluationGradeStatusEnum.FAILED.value,
        ]).update(execution_status=EvaluationExecutionStatusEnum.CANCELLED.value,
                  grade_status=EvaluationGradeStatusEnum.INVALID.value,
                  verdict=EvaluationVerdictEnum.INVALID.value, error_category=reason,
                  update_time=timezone.now())

    @staticmethod
    def _heartbeat(execution_id, worker_id, item_timeout_seconds=600):
        now = timezone.now()
        EvaluationCaseExecution.objects.filter(id=execution_id, lease_owner=worker_id).update(
            lease_expires_at=now + timedelta(seconds=max(300, int(item_timeout_seconds) + 60)),
            update_time=now,
        )

    @classmethod
    def recoverable_execution_ids(cls, limit=20):
        now = timezone.now()
        return list(EvaluationCaseExecution.objects.filter(
            Q(status=EvaluationCaseExecutionStatusEnum.PENDING.value)
            | (Q(
                status__in=[
                    EvaluationCaseExecutionStatusEnum.PREPARING.value,
                    EvaluationCaseExecutionStatusEnum.RUNNING.value,
                    EvaluationCaseExecutionStatusEnum.AGGREGATING.value,
                    EvaluationCaseExecutionStatusEnum.STOPPING.value,
                ],
            ) & (Q(lease_expires_at__lt=now) | Q(lease_expires_at__isnull=True))),
        ).order_by("id").values_list("id", flat=True)[:limit])

    @classmethod
    def _validate_graders(cls, config):
        for digest, binding in config.grader_bindings.items():
            implementation = EvaluationGraderRegistry.implementation_hash(binding.grader_key, binding.grader_version)
            if not implementation or implementation != config.grader_implementations.get(digest):
                raise EvaluationError(EVALUATION_GRADER_UNAVAILABLE, value=(binding.grader_key, binding.grader_version))

    @classmethod
    def _execute_item(cls, execution, item_result, config, adapter, frozen_target, frozen_mapping):
        item_snapshot = item_result.item_snapshot or {}
        frozen_sample = SimpleNamespace(
            input_data=item_snapshot.get("input_data", {}),
            expected_output=item_snapshot.get("expected_output") or {},
            context=item_snapshot.get("context") or {},
            metadata=item_snapshot.get("metadata") or {},
        )
        update_item_details(item_result, references={"raw_output": {}, "execution": {}},
                            timing={"execution_ms": None, "grade_ms": None}, error_message=None)
        cls._execute_item_core(execution, item_result, config, adapter, frozen_target, frozen_mapping, frozen_sample)

    @classmethod
    def _execute_item_core(cls, execution, item_result, config, adapter, frozen_target, frozen_mapping, frozen_sample):
        cls._save_grade_results(item_result, [])
        sample_target = SimpleNamespace(**{
            **vars(frozen_target),
            "executor_config": dict(frozen_target.executor_config or {}),
        })
        item_result.execution_status = EvaluationExecutionStatusEnum.RUNNING.value
        item_result.grade_status = EvaluationGradeStatusEnum.PENDING.value
        item_result.error_category = None
        update_item_details(item_result, error_message=None)
        item_result.save(update_fields=["execution_status", "grade_status", "error_category", "details", "update_time"])
        # 恢复或重试评测时重新生成指标，避免历史半成品触发唯一键冲突。
        item_result.resolved_expected_output = mask_sensitive(getattr(frozen_sample, "expected_output", {}))
        item_result.save(update_fields=["resolved_expected_output", "update_time"])
        execution_started = time.monotonic()
        result = None
        for _ in range(config.execution.retry_count + 1):
            attempt_started = time.monotonic()
            attempt = EvaluationAttemptService.start(item_result)
            try:
                elapsed_seconds = time.monotonic() - execution_started
                sample_target.executor_config["_timeout_seconds"] = max(
                    1, config.execution.item_timeout_seconds - int(elapsed_seconds),
                )
                result = adapter.execute(
                    target=sample_target, dataset_item=frozen_sample, mapping=frozen_mapping,
                    execution=execution, user_id=execution.created_by_id,
                )
                if getattr(config, "answering", None):
                    result["output"] = generate_answer(settings=config.answering, frozen_model=config.answer_model,
                        dataset_item=frozen_sample, retrieved=result.get("output", {}),
                        timeout_seconds=max(1, config.execution.item_timeout_seconds - int(time.monotonic() - execution_started)))
                EvaluationAttemptService.finish(
                    item_result, attempt, status=EvaluationExecutionStatusEnum.SUCCESS,
                    duration_ms=round((time.monotonic() - attempt_started) * 1000),
                    output_snapshot=mask_sensitive(result.get("output", {})),
                    execution_ref=mask_sensitive(result.get("execution_ref") or {}),
                )
                break
            except Exception as error:
                result = None
                item_result.error_category = "target_execution_failed"
                update_item_details(item_result, error_message=failure_message(error))
                EvaluationAttemptService.finish(
                    item_result, attempt, status=EvaluationExecutionStatusEnum.FAILED,
                    duration_ms=round((time.monotonic() - attempt_started) * 1000),
                    error_category=item_result.error_category,
                    error_message=item_result.details["error_message"],
                )
        update_item_details(item_result, timing={"execution_ms": round((time.monotonic() - execution_started) * 1000)})
        if result is None:
            item_result.execution_status = EvaluationExecutionStatusEnum.FAILED.value
            item_result.grade_status = EvaluationGradeStatusEnum.INVALID.value
            item_result.verdict = EvaluationVerdictEnum.INVALID.value
            item_result.save()
            return
        if item_result.details["timing"]["execution_ms"] > config.execution.item_timeout_seconds * 1000:
            EvaluationAttemptService.finish(
                item_result, attempt,
                status=EvaluationExecutionStatusEnum.TIMEOUT.value,
                error_category="item_timeout",
                error_message=f"数据条目执行超过 {config.execution.item_timeout_seconds} 秒",
            )
            item_result.execution_status = EvaluationExecutionStatusEnum.TIMEOUT.value
            item_result.grade_status = EvaluationGradeStatusEnum.INVALID.value
            item_result.verdict = EvaluationVerdictEnum.INVALID.value
            item_result.error_category = "item_timeout"
            update_item_details(item_result, error_message=f"数据条目执行超过 {config.execution.item_timeout_seconds} 秒")
            item_result.save()
            return
        item_result.execution_status = EvaluationExecutionStatusEnum.SUCCESS.value
        item_result.actual_output = result.get("output", {})
        update_item_details(item_result, references={"raw_output": result.get("raw_output_ref") or {}})
        update_item_details(item_result, references={"execution": result.get("execution_ref") or {}})
        item_result.grade_status = EvaluationGradeStatusEnum.GRADING.value
        item_result.save()
        evaluation_started = time.monotonic()
        hard_failed = False
        requires_review = False
        weighted_score = 0.0
        total_weight = 0.0
        assertion_results = []
        grade_results = []
        try:
            evaluation_dataset_item = {
                **item_result.item_snapshot,
                "input_data": getattr(frozen_sample, "input_data", item_result.item_snapshot.get("input_data", {})),
                "context": getattr(frozen_sample, "context", item_result.item_snapshot.get("context", {})),
                "expected_output": item_result.resolved_expected_output,
            }
            for reference in item_result.item_snapshot["effective_graders"]:
                binding_hash = reference["binding_hash"]
                binding = config.grader_bindings[binding_hash]
                if not binding.enabled:
                    continue
                grader, default_config = EvaluationGraderRegistry.resolve(
                    binding.grader_key, binding.grader_version,
                )
                if grader is None:
                    raise EvaluationError(EVALUATION_GRADER_UNAVAILABLE, value=(binding.grader_key, binding.grader_version))
                evaluated = grader.evaluate(
                    dataset_item=evaluation_dataset_item,
                    actual=item_result.actual_output,
                    config={**default_config, **binding.parameters},
                    metric_key=binding.metric_key,
                    threshold=binding.threshold,
                )
                EvaluationGraderRegistry.validate_result(
                    binding.grader_key, binding.grader_version, evaluated,
                )
                primary = next((metric for metric in evaluated.metrics if metric.key == binding.metric_key), None)
                if primary is None:
                    raise invalid_config("评分器未返回约定的主指标")
                requires_review = requires_review or ((evaluated.requires_review or primary.score is None) and (binding.hard_gate or binding.weight > 0))
                for metric in evaluated.metrics:
                    is_primary = metric.key == binding.metric_key
                    metric_passed = metric.passed
                    if is_primary and binding.hard_gate and not metric_passed:
                        hard_failed = True
                    if is_primary and not binding.hard_gate and binding.weight > 0:
                        assertion_results.append(metric_passed and metric.score is not None)
                    if is_primary and metric.score is not None and not binding.hard_gate and binding.weight > 0:
                        weighted_score += metric.score * binding.weight
                        total_weight += binding.weight
                    grade_results.append(EvaluationGradeResult(
                        item_result=item_result,
                        grader_key=binding.grader_key,
                        grader_version=binding.grader_version,
                        score=decimal_score(metric.score),
                        raw_value=metric.raw_value,
                        passed=metric_passed,
                        grading_snapshot=EvaluationGradeSnapshot(
                            binding_hash=binding_hash, metric=metric.key, threshold=binding.threshold, weight=binding.weight if is_primary else 0,
                        ).model_dump(mode="json"),
                        hard_gate=binding.hard_gate if is_primary else False,
                        evidence=mask_sensitive(metric.evidence),
                        reason=metric.reason,
                        confidence=Decimal(str(metric.confidence)) if metric.confidence is not None else None,
                    ))
            cls._save_grade_results(item_result, grade_results)
            score = weighted_score / total_weight if total_weight else None
            item_result.score = decimal_score(score)
            update_item_details(item_result, timing={"grade_ms": round((time.monotonic() - evaluation_started) * 1000)})
            if requires_review:
                item_result.grade_status = EvaluationGradeStatusEnum.INVALID.value
                item_result.verdict = EvaluationVerdictEnum.INVALID.value
                item_result.error_category = "judge_uncertain"
                update_item_details(item_result, error_message="评分器证据或置信度不足，无法可靠判分")
            else:
                item_result.grade_status = EvaluationGradeStatusEnum.GRADED.value
                if hard_failed or not assertion_results or not all(assertion_results):
                    item_result.verdict = EvaluationVerdictEnum.FAILED.value
                else:
                    item_result.verdict = EvaluationVerdictEnum.PASSED.value
            item_result.save()
        except Exception as error:
            item_result.grade_status = EvaluationGradeStatusEnum.FAILED.value
            item_result.verdict = EvaluationVerdictEnum.INVALID.value
            item_result.error_category = "judge_output_invalid" if isinstance(error, ValidationError) else "grading_failed"
            update_item_details(item_result, error_message=failure_message(error))
            update_item_details(item_result, timing={"grade_ms": round((time.monotonic() - evaluation_started) * 1000)})
            item_result.save()

    @classmethod
    def aggregate(cls, execution, config=None):
        config = config or EvaluationExecutionSnapshot.model_validate(execution.snapshot)
        all_rows = list(execution.item_results.all())
        rows = [row for row in all_rows if not getattr(row, "item_snapshot", {}).get("dependency_only")]
        total = len(rows)
        valid_rows = [row for row in rows if row.grade_status == EvaluationGradeStatusEnum.GRADED.value]
        invalid = total - len(valid_rows)
        passed = sum(row.verdict == EvaluationVerdictEnum.PASSED.value for row in valid_rows)
        failed = sum(row.verdict == EvaluationVerdictEnum.FAILED.value for row in valid_rows)
        warning = sum(row.verdict == EvaluationVerdictEnum.WARNING.value for row in valid_rows)
        valid_weight = sum(float(row.item_snapshot.get("weight") or 1) for row in valid_rows)
        passed_weight = sum(float(row.item_snapshot.get("weight") or 1) for row in valid_rows if row.verdict == EvaluationVerdictEnum.PASSED.value)
        scores = [(float(row.score), float(row.item_snapshot.get("weight") or 1)) for row in valid_rows if row.score is not None]
        average_score = sum(score * weight for score, weight in scores) / sum(weight for _, weight in scores) if scores else None
        valid_rate = len(valid_rows) / total if total else 0
        effect_pass_rate = passed_weight / valid_weight if valid_weight else None
        metric_groups = cls._metric_summary(execution)
        summary = {
            "total": total, "valid": len(valid_rows), "invalid": invalid,
            "dependency_count": len(all_rows) - len(rows),
            "attempt_total": len(rows),
            "item_count": len({row.dataset_item_id for row in rows}),
            "passed": passed, "failed": failed, "warning": warning,
            "valid_rate": round(valid_rate, 4), "effect_pass_rate": round(effect_pass_rate, 4) if effect_pass_rate is not None else None,
            "average_score": round(average_score, 2) if average_score is not None else None,
            "metrics": metric_groups,
            "hard_gate_failed_count": EvaluationGradeResult.objects.filter(
                item_result__execution=execution, hard_gate=True, passed=False,
            ).values("item_result_id").distinct().count(),
        }
        summary["classification"] = cls._classification_summary(execution)
        if any(binding.grader_key == "memory_qa" for binding in config.grader_bindings.values()):
            grades = EvaluationGradeResult.objects.filter(item_result__execution=execution, grader_key="memory_qa").values("item_result_id", "raw_value", "grading_snapshot")
            summary["memory_qa"] = cls._memory_qa_summary(rows, grades)
        summary["performance"] = cls._performance_summary(rows)
        cleanup_errors = (getattr(execution, "details", {}) or {}).get("cleanup_errors")
        summary["cleanup_failed_count"] = len(cleanup_errors) if cleanup_errors is not None else sum(bool((row.details or {}).get("cleanup_error")) for row in rows)
        summary["groups"] = cls._group_summary(valid_rows)
        summary["stability"] = cls._stability_summary([
            row for row in rows if row.grade_status in {
                EvaluationGradeStatusEnum.GRADED.value,
            }
        ])
        gates = cls._evaluate_gates(summary, config)
        summary["gates"] = gates
        critical_failed = any(not gate["passed"] and gate["severity"] == "critical" for gate in gates)
        warning_failed = any(not gate["passed"] and gate["severity"] == "warning" for gate in gates)
        if critical_failed or summary["hard_gate_failed_count"]:
            verdict = EvaluationVerdictEnum.FAILED.value
        elif valid_rate < config.grading.aggregation.min_valid_rate:
            verdict = EvaluationVerdictEnum.INVALID.value
        elif effect_pass_rate is None:
            verdict = EvaluationVerdictEnum.INVALID.value
        elif effect_pass_rate < config.grading.aggregation.min_effect_pass_rate:
            verdict = EvaluationVerdictEnum.FAILED.value
        elif warning_failed or summary["cleanup_failed_count"]:
            verdict = EvaluationVerdictEnum.WARNING.value
        else:
            verdict = EvaluationVerdictEnum.PASSED.value
        execution.summary = summary
        if config.summary_model:
            from src.apps.evaluation.services.reporting.summary import generate_summary
            try:
                summary["ai_summary"] = generate_summary(execution, config)
            except Exception as error:
                summary["ai_summary"] = {"status": "failed", "model": config.summary_model.model_dump(mode="json"), "error_message": failure_message(error)}
        execution.verdict = verdict
        execution.status = EvaluationCaseExecutionStatusEnum.COMPLETED.value
        execution.progress = 100
        execution.finished_at = timezone.now()
        execution.lease_owner = None
        execution.lease_expires_at = None
        execution.save(update_fields=[
            "summary", "verdict", "status", "progress", "finished_at",
            "lease_owner", "lease_expires_at", "update_time",
        ])
        from src.apps.evaluation.services.reporting.report import sync_report
        sync_report(execution)
        return execution

    @staticmethod
    def _memory_qa_summary(rows, grades):
        from src.apps.evaluation.enums.answer import EvaluationAnswerVerdictEnum
        counts = {item.value: 0 for item in EvaluationAnswerVerdictEnum}
        valid_items = 0
        invalid_items = 0
        by_result = {}
        for grade in grades:
            by_result.setdefault(grade["item_result_id"], []).append(grade)
        for row in rows:
            turns = (getattr(row, "item_snapshot", {}).get("scenario") or {}).get("turns") or []
            if turns:
                outcomes = {item["index"]: item for item in (row.details or {}).get("turns", [])}
                for index, turn in enumerate(turns, 1):
                    if not turn.get("score", True):
                        continue
                    values = [grade["raw_value"] for grade in by_result.get(row.id, []) if grade.get("grading_snapshot", {}).get("turn_index") == index]
                    judgments = [value.get("classification") for value in values if isinstance(value, dict)]
                    if outcomes.get(index, {}).get("verdict") not in (None, EvaluationVerdictEnum.INVALID.value) and len(judgments) == 1 and judgments[0] in counts:
                        counts[judgments[0]] += 1
                        valid_items += 1
                    else:
                        invalid_items += 1
                continue
            judgments = [grade["raw_value"].get("classification") for grade in by_result.get(row.id, []) if isinstance(grade["raw_value"], dict)]
            if row.grade_status == EvaluationGradeStatusEnum.GRADED.value and len(judgments) == 1 and judgments[0] in counts:
                counts[judgments[0]] += 1
                valid_items += 1
            else:
                invalid_items += 1
        return {"counts": counts, "valid": valid_items, "invalid": invalid_items,
                "rates": {key: round(value / valid_items, 4) if valid_items else None for key, value in counts.items()}}

    @staticmethod
    @transaction.atomic
    def _save_grade_results(item_result, grade_results):
        identities = [(grade.grader_key, grade.grader_version, grade.grading_snapshot["metric"]) for grade in grade_results]
        if len(identities) != len(set(identities)):
            raise invalid_config("评分器返回了重复的指标结果")
        EvaluationItemResult.objects.select_for_update().get(pk=item_result.pk)
        turn = getattr(item_result, "_workflow_turn", None)
        if turn is None:
            item_result.grade_results.all().delete()
        elif not grade_results:
            return
        else:
            item_result.grade_results.filter(grading_snapshot__turn_index=turn).delete()
            for grade in grade_results:
                grade.grading_snapshot["turn_index"] = turn
        EvaluationGradeResult.objects.bulk_create(grade_results)

    @staticmethod
    def _metric_summary(execution):
        repeated = {}
        for item in EvaluationGradeResult.objects.filter(item_result__execution=execution, item_result__grade_status=EvaluationGradeStatusEnum.GRADED.value).values(
            "item_result__dataset_item_id", "score", "passed", "grader_key", "grader_version", "grading_snapshot",
        ):
            identity = (item["grading_snapshot"]["metric"], item["grader_key"], item["grader_version"], item["grading_snapshot"]["binding_hash"])
            repeated.setdefault((item["item_result__dataset_item_id"], identity), []).append(item)
        groups = {}
        for (_item_id, identity), items in repeated.items():
            bucket = groups.setdefault(identity, {"scores": [], "total": 0, "passed": 0})
            scores = [float(item["score"]) for item in items if item["score"] is not None]
            if scores:
                bucket["scores"].extend(scores)
            bucket["total"] += len(items)
            bucket["passed"] += sum(bool(item["passed"]) for item in items)
        result = {}
        for (metric, grader, version, digest), value in groups.items():
            result.setdefault(metric, []).append({
                "grader_key": grader, "grader_version": version, "binding_hash": digest,
                "average_score": round(sum(value["scores"]) / len(value["scores"]), 2) if value["scores"] else None,
                "total": value["total"], "passed": value["passed"],
                "pass_rate": round(value["passed"] / value["total"], 4) if value["total"] else None,
            })
        return {key: variants[0] if len(variants) == 1 else {"average_score": None, "variants": variants}
                for key, variants in result.items()}

    @staticmethod
    def _group_summary(rows):
        groups = {"priority": {}, "tag": {}}
        for row in rows:
            dimensions = {
                "priority": [row.item_snapshot.get("priority") or "unknown"],
                "tag": row.item_snapshot.get("tags") or ["untagged"],
            }
            for dimension, values in dimensions.items():
                for value in values:
                    bucket = groups[dimension].setdefault(str(value), {"total": 0, "passed": 0, "score_total": 0, "score_count": 0})
                    bucket["total"] += 1
                    bucket["passed"] += row.verdict == EvaluationVerdictEnum.PASSED.value
                    if row.score is not None:
                        bucket["score_total"] += float(row.score)
                        bucket["score_count"] += 1
        for dimension in groups.values():
            for bucket in dimension.values():
                bucket["pass_rate"] = round(bucket["passed"] / bucket["total"], 4) if bucket["total"] else 0
                score_total = bucket.pop("score_total")
                score_count = bucket.pop("score_count")
                bucket["average_score"] = round(score_total / score_count, 2) if score_count else None
        return groups

    @staticmethod
    def _classification_summary(execution):
        grouped = {}
        for item in EvaluationGradeResult.objects.filter(
            item_result__execution=execution, grader_key="classification", item_result__grade_status=EvaluationGradeStatusEnum.GRADED.value,
        ).values("item_result__dataset_item_id", "raw_value", "grading_snapshot"):
            raw = item["raw_value"]
            if isinstance(raw, dict) and "expected" in raw and "actual" in raw:
                grouped.setdefault((item["grading_snapshot"]["binding_hash"], item["item_result__dataset_item_id"]), []).append(
                    (str(raw["expected"]), str(raw["actual"])),
                )
        signatures = {identity[0] for identity in grouped}
        if len(signatures) > 1:
            return {"comparable": False, "binding_hashes": sorted(signatures)}
        pairs = []
        for values in grouped.values():
            pairs.extend(values)
        if not pairs:
            return None
        labels = sorted({value for pair in pairs for value in pair})
        matrix = {
            expected: {actual: sum(left == expected and right == actual for left, right in pairs) for actual in labels}
            for expected in labels
        }
        f1_values = []
        for label in labels:
            true_positive = matrix[label][label]
            false_positive = sum(matrix[other][label] for other in labels if other != label)
            false_negative = sum(matrix[label][other] for other in labels if other != label)
            precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0
            recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0
            f1_values.append(2 * precision * recall / (precision + recall) if precision + recall else 0)
        return {
            "labels": labels,
            "confusion_matrix": matrix,
            "accuracy": round(sum(left == right for left, right in pairs) / len(pairs), 4),
            "macro_f1": round(sum(f1_values) / len(f1_values), 4) if f1_values else None,
        }

    @staticmethod
    def _performance_summary(rows):
        def percentile(values, ratio):
            if not values:
                return None
            ordered = sorted(values)
            index = min(len(ordered)-1, max(0, math.ceil(len(ordered) * ratio)-1))
            return ordered[index]

        execution = [value for row in rows if (value := (row.details or {}).get("timing", {}).get("execution_ms")) is not None]
        evaluation = [value for row in rows if (value := (row.details or {}).get("timing", {}).get("grade_ms")) is not None]
        return {
            "execution_p50_ms": percentile(execution, 0.5),
            "execution_p95_ms": percentile(execution, 0.95),
            "execution_max_ms": max(execution) if execution else None,
            "grade_p50_ms": percentile(evaluation, 0.5),
            "grade_p95_ms": percentile(evaluation, 0.95),
            "total_attempts": sum(len(row.attempts) for row in rows),
        }

    @staticmethod
    def _stability_summary(rows):
        scores = {}
        verdicts = {}
        for row in rows:
            if row.score is not None:
                scores.setdefault(row.dataset_item_id, []).append(float(row.score))
            verdicts.setdefault(row.dataset_item_id, set()).add(row.verdict)
        repeated = [values for values in scores.values() if len(values) > 1]
        return {
            "repeated_item_count": len(repeated),
            "average_score_stddev": round(sum(statistics.pstdev(values) for values in repeated) / len(repeated), 4) if repeated else None,
            "verdict_flip_count": sum(len(values) > 1 for values in verdicts.values()),
        }

    @staticmethod
    def _evaluate_gates(summary, config):
        gates = []
        for gate in config.grading.quality_gates:
            if gate.group_by:
                dimension, separator, bucket_key = gate.group_by.partition(":")
                buckets = summary.get("groups", {}).get(dimension, {})
                if separator:
                    value = (buckets.get(bucket_key) or {}).get(gate.key)
                else:
                    values = [item.get(gate.key) for item in buckets.values() if item.get(gate.key) is not None]
                    value = min(values) if values else None
            elif gate.metric_key:
                value = (summary.get("metrics", {}).get(gate.metric_key) or {}).get("average_score")
            else:
                value = summary.get(gate.key)
            operators = {
                "gte": lambda left, right: left >= right, "gt": lambda left, right: left > right,
                "lte": lambda left, right: left <= right, "lt": lambda left, right: left < right,
                "eq": lambda left, right: left == right, "zero": lambda left, _right: left == 0,
            }
            passed = value is not None and operators[gate.operator](float(value), gate.threshold)
            gates.append({
                "key": gate.key, "metric_key": gate.metric_key, "operator": gate.operator,
                "group_by": gate.group_by, "threshold": gate.threshold, "value": value,
                "severity": gate.severity, "passed": passed,
            })
        return gates

    @classmethod
    def stop(cls, execution_id):
        pending = EvaluationCaseExecution.objects.filter(
            id=execution_id, status=EvaluationCaseExecutionStatusEnum.PENDING.value,
        ).update(
            stop_requested=True,
            status=EvaluationCaseExecutionStatusEnum.STOPPED.value,
            verdict=EvaluationVerdictEnum.INVALID.value,
            finished_at=timezone.now(),
        )
        if pending:
            EvaluationItemResult.objects.filter(execution_id=execution_id).update(
                execution_status=EvaluationExecutionStatusEnum.CANCELLED.value,
                grade_status=EvaluationGradeStatusEnum.INVALID.value,
                verdict=EvaluationVerdictEnum.INVALID.value, error_category="execution_stopped",
                update_time=timezone.now(),
            )
            from src.apps.evaluation.services.reporting.report import sync_report
            sync_report(EvaluationCaseExecution.objects.get(id=execution_id))
            return
        updated = EvaluationCaseExecution.objects.filter(
            id=execution_id,
            status__in=[
                EvaluationCaseExecutionStatusEnum.PREPARING.value,
                EvaluationCaseExecutionStatusEnum.RUNNING.value,
                EvaluationCaseExecutionStatusEnum.AGGREGATING.value,
                EvaluationCaseExecutionStatusEnum.STOPPING.value,
            ],
        ).update(stop_requested=True, status=EvaluationCaseExecutionStatusEnum.STOPPING.value)
        if not updated:
            raise EvaluationError(EVALUATION_EXECUTION_OPERATION_NOT_ALLOWED)

    @classmethod
    @transaction.atomic
    def retry_failed(cls, execution_id, user, idempotency_key=None):
        source = EvaluationCaseExecution.objects.select_for_update().select_related("case").filter(id=execution_id).first()
        if source is None:
            raise EvaluationError(EVALUATION_EXECUTION_NOT_FOUND)
        ensure_product_scope(user, source.case.project_product_id)
        if source.status not in EvaluationCaseExecutionStatusEnum.terminal_values():
            raise EvaluationError(EVALUATION_EXECUTION_OPERATION_NOT_ALLOWED)
        key = "eval-retry:" + content_hash({"source": source.id, "user": user.id, "key": idempotency_key}) if idempotency_key else None
        if key:
            existing = EvaluationCaseExecution.objects.filter(idempotency_key=key).first()
            if existing:
                return existing
        failed_keys = list(source.item_results.exclude(verdict__in=[EvaluationVerdictEnum.PASSED.value, EvaluationVerdictEnum.WARNING.value]).values_list("dataset_item_id", flat=True))
        if not failed_keys:
            raise EvaluationError(EVALUATION_DATASET_HAS_NO_ITEMS)
        rows = list(source.item_results.filter(dataset_item_id__in=failed_keys))
        rows = [row for row in rows if not row.item_snapshot.get("dependency_only")]
        failed_keys = sorted({row.dataset_item_id for row in rows})
        if not rows:
            raise EvaluationError(EVALUATION_DATASET_HAS_NO_ITEMS)
        snapshot = deepcopy(source.snapshot)
        workflow = snapshot.get("dataset_config", {}).get("workflow", {})
        if workflow.get("sequence", "independent") != "independent":
            groups = {}
            for row in rows:
                scenario = row.item_snapshot.get("scenario") or {}
                if scenario.get("group_key"):
                    identity = (scenario["group_key"], row.repeat_index)
                    groups[identity] = max(groups.get(identity, 0), scenario.get("order", 0))
            selected_ids = {row.id for row in rows}
            for row in source.item_results.order_by("id"):
                scenario = row.item_snapshot.get("scenario") or {}
                identity = (scenario.get("group_key"), row.repeat_index)
                if row.id not in selected_ids and identity in groups and scenario.get("order", 0) <= groups[identity]:
                    row.item_snapshot = {**row.item_snapshot, "dependency_only": True}
                    rows.append(row)
            rows.sort(key=lambda row: row.id)
        if "item_ids" not in snapshot.get("selection", {}) or "input_variable" not in snapshot or "paths" not in snapshot.get("mapping", {}).get("output", {}):
            raise invalid_config("历史执行使用旧输入或输出配置，请按当前用例配置重新执行")
        if snapshot.get("grading", {}).get("aggregation", {}).get("policy_version") != 2:
            raise invalid_config("历史执行使用旧判定规则，请按当前用例配置重新执行")
        snapshot["selection"] = {"item_ids": sorted(set(failed_keys)), "scope": "retry_subset",
                                 "items_hash": content_hash([row.item_snapshot for row in rows])}
        snapshot["request"] = {"payload_hash": content_hash({"retry_of": source.id})}
        snapshot["signatures"]["dataset"] = content_hash({"dataset": snapshot["dataset"], "selection": snapshot["selection"]})
        snapshot["signatures"].pop("manifest", None)
        snapshot["signatures"]["manifest"] = content_hash(snapshot)
        execution = EvaluationCaseExecution.objects.create(case_id=source.case_id, dataset_version_id=source.dataset_version_id,
            test_env=source.test_env, trigger_type=EvaluationTriggerTypeEnum.RETRY.value, retry_of=source, snapshot=snapshot,
            idempotency_key=key, created_by=user)
        EvaluationItemResult.objects.bulk_create([
            EvaluationItemResult(execution=execution, dataset_item_id=row.dataset_item_id,
                                 repeat_index=row.repeat_index, item_snapshot=deepcopy(row.item_snapshot))
            for row in rows
        ], batch_size=500)
        from src.apps.evaluation.services.reporting.report import create_report
        create_report(execution, source.case, user)
        return execution
