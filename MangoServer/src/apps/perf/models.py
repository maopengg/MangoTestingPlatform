import uuid
from decimal import Decimal

from django.db import models

from src.apps.auto_api.models import ApiCase, ApiCaseRelease, ApiCaseRevision
from src.apps.perf.enums import (
    PerfScenarioExecutionModeEnum,
    PerfEngineEnum,
    PerfNodeFailurePolicyEnum,
    PerfLoadTypeEnum,
    PerfLoadProfileEnum,
    PerfRunStatusEnum,
    PerfRunVerdictEnum,
    PerfRunNodeStatusEnum,
    PerfReservationStatusEnum,
)
from src.apps.task_center.models import ExecutorTask, SocketConnection
from src.apps.test_center.models import ProductModule, ProjectProduct
from src.apps.user.models import User


class AuditModel(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)

    class Meta:
        abstract = True


class PerfScenario(AuditModel):
    project_product = models.ForeignKey(ProjectProduct, on_delete=models.PROTECT, related_name="perf_scenarios")
    module = models.ForeignKey(ProductModule, on_delete=models.PROTECT, related_name="perf_scenarios")
    name = models.CharField(max_length=128)
    description = models.TextField(null=True, blank=True)
    engine = models.CharField(max_length=24, choices=PerfEngineEnum.choices(), default=PerfEngineEnum.K6.value)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="owned_perf_scenarios")
    tags = models.JSONField(default=list, blank=True, help_text="string[]")
    execution_mode = models.CharField(max_length=24, choices=PerfScenarioExecutionModeEnum.choices(),
                                      default=PerfScenarioExecutionModeEnum.SEQUENTIAL.value)
    source_api_case = models.ForeignKey(ApiCase, on_delete=models.PROTECT, null=True, blank=True,
                                        related_name="perf_scenarios")
    source_case_release = models.ForeignKey(ApiCaseRelease, on_delete=models.PROTECT, null=True, blank=True,
                                            related_name="perf_scenarios")
    source_case_revision = models.ForeignKey(ApiCaseRevision, on_delete=models.PROTECT, null=True, blank=True,
                                             related_name="perf_scenarios")
    load_type = models.CharField(max_length=24, choices=PerfLoadTypeEnum.choices(),
                                 default=PerfLoadTypeEnum.CONCURRENCY.value)
    load_profile = models.CharField(max_length=32, choices=PerfLoadProfileEnum.choices(),
                                    default=PerfLoadProfileEnum.CONSTANT_CONCURRENCY.value)
    load_name = models.CharField(max_length=64, default="基础负载")
    duration_seconds = models.PositiveIntegerField(default=60)
    total_iterations = models.PositiveBigIntegerField(null=True, blank=True)
    start_users = models.PositiveIntegerField(null=True, blank=True)
    step_users = models.PositiveIntegerField(null=True, blank=True)
    step_interval_seconds = models.PositiveIntegerField(null=True, blank=True)
    ramp_seconds = models.PositiveIntegerField(null=True, blank=True)
    hold_seconds = models.PositiveIntegerField(null=True, blank=True)
    baseline_seconds = models.PositiveIntegerField(null=True, blank=True)
    recovery_seconds = models.PositiveIntegerField(null=True, blank=True)
    target_users = models.PositiveIntegerField(null=True, blank=True, default=10)
    target_rate = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    rate_time_unit = models.CharField(max_length=16, null=True, blank=True)
    preallocated_vus = models.PositiveIntegerField(null=True, blank=True)
    max_vus = models.PositiveIntegerField(null=True, blank=True)
    ramp_type = models.CharField(max_length=16, default="step")
    spawn_rate = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    goal_template_key = models.CharField(max_length=16, default="recommended")
    goal_p95_ms = models.PositiveIntegerField(default=500)
    goal_max_error_rate = models.DecimalField(max_digits=7, decimal_places=6, default=Decimal("0.01"))
    goal_min_load_achievement_rate = models.DecimalField(max_digits=7, decimal_places=6, default=Decimal("0.95"))
    default_executor_count = models.PositiveSmallIntegerField(default=1)
    node_failure_policy = models.CharField(max_length=24, choices=PerfNodeFailurePolicyEnum.choices(),
                                           default=PerfNodeFailurePolicyEnum.STRICT.value)
    min_ready_nodes = models.PositiveSmallIntegerField(null=True, blank=True)
    user_wait_min_ms = models.PositiveIntegerField(default=0)
    user_wait_max_ms = models.PositiveIntegerField(default=0)
    status = models.SmallIntegerField(default=1, db_index=True)
    version = models.PositiveIntegerField(default=1)
    update_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="updated_perf_scenarios")

    class Meta:
        db_table = "perf_scenario"
        ordering = ["-update_time", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["project_product", "name"], name="uniq_perf_scenario_product_name"),
            models.CheckConstraint(condition=models.Q(default_executor_count__gte=1),
                                   name="perf_scenario_executor_count_gte_1"),
            models.CheckConstraint(condition=models.Q(user_wait_max_ms__gte=models.F("user_wait_min_ms")),
                                   name="perf_scenario_wait_range_valid"),
            models.CheckConstraint(condition=models.Q(duration_seconds__gte=1), name="perf_scenario_duration_gte_1"),
            models.CheckConstraint(condition=models.Q(goal_template_key__in=["recommended", "custom"]),
                                   name="perf_scenario_goal_template_valid"),
            models.CheckConstraint(condition=models.Q(goal_p95_ms__gte=1), name="perf_scenario_goal_p95_gte_1"),
            models.CheckConstraint(condition=models.Q(goal_max_error_rate__gte=0, goal_max_error_rate__lte=1),
                                   name="perf_scenario_goal_error_rate_range"),
            models.CheckConstraint(
                condition=models.Q(goal_min_load_achievement_rate__gte=0, goal_min_load_achievement_rate__lte=1),
                name="perf_scenario_goal_load_rate_range"),
            models.CheckConstraint(
                condition=(models.Q(load_type=PerfLoadTypeEnum.CONCURRENCY.value, target_users__isnull=False)
                           | models.Q(
                            load_type__in=[PerfLoadTypeEnum.ARRIVAL_RATE.value, PerfLoadTypeEnum.ITERATION_RATE.value],
                            target_rate__isnull=False)),
                name="perf_scenario_load_target_required",
            ),
        ]
        indexes = [models.Index(fields=["project_product", "status", "update_time"], name="idx_perf_scenario_list")]


class PerfRun(AuditModel):
    scenario = models.ForeignKey(PerfScenario, on_delete=models.PROTECT, related_name="runs")
    name = models.CharField(max_length=128)
    status = models.CharField(max_length=24, choices=PerfRunStatusEnum.choices(),
                              default=PerfRunStatusEnum.CREATED.value, db_index=True)
    verdict = models.CharField(max_length=24, choices=PerfRunVerdictEnum.choices(),
                               default=PerfRunVerdictEnum.NOT_EVALUATED.value, db_index=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="created_perf_runs")
    project_product = models.ForeignKey(ProjectProduct, on_delete=models.PROTECT, related_name="perf_runs")
    module = models.ForeignKey(ProductModule, on_delete=models.PROTECT, null=True, blank=True, related_name="perf_runs")
    test_env = models.SmallIntegerField()
    test_env_title = models.CharField(max_length=64, blank=True, default="")
    engine = models.CharField(max_length=24, choices=PerfEngineEnum.choices(), default=PerfEngineEnum.K6.value)
    engine_version = models.CharField(max_length=32, blank=True, default="")
    schema_version = models.PositiveSmallIntegerField(default=1)
    scenario_snapshot = models.JSONField(default=dict, blank=True,
                                         help_text="PerfScenarioIR v1; plaintext secrets forbidden")
    snapshot_hash = models.CharField(max_length=64)
    requested_node_count = models.PositiveSmallIntegerField(default=1)
    actual_node_count = models.PositiveSmallIntegerField(default=0)
    peak_target_users = models.PositiveIntegerField(default=0)
    duration_seconds = models.PositiveIntegerField(default=0)
    execution_policy = models.JSONField(default=dict, blank=True, help_text="PerfRunExecutionPolicy v1")
    schedule_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    stop_requested_at = models.DateTimeField(null=True, blank=True)
    summary = models.JSONField(default=dict, blank=True, help_text="PerfRunSummary v1")
    load_summary = models.JSONField(default=dict, blank=True, help_text="PerfRunLoadSummary v1")
    validity_results = models.JSONField(default=list, blank=True, help_text="PerfValidityResult[] v1")
    performance_goal_result = models.JSONField(default=dict, blank=True, help_text="PerfPerformanceGoalResult v1")
    capacity_result = models.JSONField(default=dict, blank=True, help_text="PerfCapacityResult v1")
    error_code = models.CharField(max_length=64, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    remark = models.CharField(max_length=512, null=True, blank=True)
    revision = models.PositiveBigIntegerField(default=1)

    class Meta:
        db_table = "perf_run"
        ordering = ["-create_time", "-id"]
        indexes = [models.Index(fields=["scenario", "create_time"], name="idx_perf_run_scenario"),
                   models.Index(fields=["status", "create_time"], name="idx_perf_run_status")]


class PerfRunNode(AuditModel):
    run = models.ForeignKey(PerfRun, on_delete=models.CASCADE, related_name="nodes")
    node_key = models.UUIDField(default=uuid.uuid4, editable=False)
    shard_index = models.PositiveSmallIntegerField()
    shard_count = models.PositiveSmallIntegerField()
    executor_fingerprint = models.CharField(max_length=128, null=True, blank=True, db_index=True)
    target_executor_connection = models.ForeignKey(SocketConnection, on_delete=models.SET_NULL, null=True, blank=True,
                                                   related_name="targeted_perf_run_nodes")
    actual_executor_connection = models.ForeignKey(SocketConnection, on_delete=models.SET_NULL, null=True, blank=True,
                                                   related_name="actual_perf_run_nodes")
    executor_task = models.OneToOneField(ExecutorTask, on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name="perf_run_node")
    status = models.CharField(max_length=24, choices=PerfRunNodeStatusEnum.choices(),
                              default=PerfRunNodeStatusEnum.CREATED.value, db_index=True)
    control_revision = models.PositiveIntegerField(default=1)
    allocated_load = models.JSONField(default=dict, blank=True, help_text="PerfAllocatedLoad v1")
    capacity_type = models.CharField(max_length=16, blank=True, default="")
    reserved_value = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    reservation_status = models.CharField(max_length=16, choices=PerfReservationStatusEnum.choices(), null=True,
                                          blank=True, db_index=True)
    lease_token_hash = models.CharField(max_length=64, blank=True, default="")
    lease_expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    last_metric_at = models.DateTimeField(null=True, blank=True)
    clock_offset_ms = models.IntegerField(null=True, blank=True)
    engine_pid = models.IntegerField(null=True, blank=True)
    engine_version = models.CharField(max_length=32, blank=True, default="")
    resource_summary = models.JSONField(default=dict, blank=True, help_text="PerfGeneratorResourceSummary v1")
    result_summary = models.JSONField(default=dict, blank=True, help_text="PerfNodeResultSummary v1")
    error_code = models.CharField(max_length=64, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "perf_run_node"
        ordering = ["run_id", "shard_index"]
        constraints = [models.UniqueConstraint(fields=["run", "node_key"], name="uniq_perf_run_node_key"),
                       models.UniqueConstraint(fields=["run", "shard_index"], name="uniq_perf_run_node_shard")]
        indexes = [models.Index(fields=["run", "status"], name="idx_perf_run_node_status")]


class PerfMetricInterval(models.Model):
    run = models.ForeignKey(PerfRun, on_delete=models.CASCADE, related_name="metric_intervals")
    run_node = models.ForeignKey(PerfRunNode, on_delete=models.CASCADE, related_name="metric_intervals")
    sequence = models.PositiveBigIntegerField()
    window_start = models.DateTimeField(db_index=True)
    window_seconds = models.PositiveSmallIntegerField(default=1)
    scope_type = models.CharField(max_length=16, default="global")
    scope_key = models.CharField(max_length=128, default="__all__")
    stage_key = models.CharField(max_length=64, blank=True, default="")
    target_load = models.JSONField(default=dict, blank=True, help_text="PerfLoadPoint v1")
    actual_load = models.JSONField(default=dict, blank=True, help_text="PerfLoadPoint v1")
    request_count = models.PositiveBigIntegerField(default=0)
    failure_count = models.PositiveBigIntegerField(default=0)
    iteration_count = models.PositiveBigIntegerField(default=0)
    dropped_count = models.PositiveBigIntegerField(default=0)
    response_time_sum_ms = models.PositiveBigIntegerField(default=0)
    min_response_time_ms = models.PositiveIntegerField(null=True, blank=True)
    max_response_time_ms = models.PositiveIntegerField(null=True, blank=True)
    bytes_sent = models.PositiveBigIntegerField(default=0)
    bytes_received = models.PositiveBigIntegerField(default=0)
    connection_count = models.PositiveBigIntegerField(default=0)
    connect_error_count = models.PositiveBigIntegerField(default=0)
    histogram = models.TextField(blank=True, default="")
    timing_breakdown = models.JSONField(default=dict, blank=True, help_text="PerfTimingBreakdown v1")
    generator_metrics = models.JSONField(default=dict, blank=True, help_text="PerfGeneratorMetrics v1")
    schema_version = models.PositiveSmallIntegerField(default=1)
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "perf_metric_interval"
        ordering = ["window_start", "id"]
        constraints = [
            models.UniqueConstraint(fields=["run_node", "sequence", "window_start", "scope_type", "scope_key"],
                                    name="uniq_perf_metric_batch_scope")]
        indexes = [models.Index(fields=["run", "window_start"], name="idx_perf_metric_run_time"),
                   models.Index(fields=["run", "scope_type", "scope_key", "window_start"],
                                name="idx_perf_metric_scope")]


class PerfRequestSummary(AuditModel):
    run = models.ForeignKey(PerfRun, on_delete=models.CASCADE, related_name="request_summaries")
    step_key = models.CharField(max_length=36, blank=True, default="")
    request_name = models.CharField(max_length=128, blank=True, default="")
    method = models.CharField(max_length=16, blank=True, default="")
    url_path = models.CharField(max_length=512, blank=True, default="")
    request_count = models.PositiveBigIntegerField(default=0)
    failure_count = models.PositiveBigIntegerField(default=0)
    avg_ms = models.DecimalField(max_digits=16, decimal_places=3, default=0)
    min_ms = models.DecimalField(max_digits=16, decimal_places=3, default=0)
    max_ms = models.DecimalField(max_digits=16, decimal_places=3, default=0)
    p50_ms = models.DecimalField(max_digits=16, decimal_places=3, default=0)
    p90_ms = models.DecimalField(max_digits=16, decimal_places=3, default=0)
    p95_ms = models.DecimalField(max_digits=16, decimal_places=3, default=0)
    p99_ms = models.DecimalField(max_digits=16, decimal_places=3, default=0)
    rps = models.DecimalField(max_digits=16, decimal_places=4, default=0)
    max_rps = models.DecimalField(max_digits=16, decimal_places=4, default=0)
    bytes_sent = models.PositiveBigIntegerField(default=0)
    bytes_received = models.PositiveBigIntegerField(default=0)
    histogram = models.TextField(blank=True, default="")

    class Meta:
        db_table = "perf_request_summary"
        ordering = ["run_id", "id"]
        constraints = [models.UniqueConstraint(fields=["run", "step_key"], name="uniq_perf_request_summary")]


class PerfRunError(AuditModel):
    run = models.ForeignKey(PerfRun, on_delete=models.CASCADE, related_name="errors")
    step_key = models.CharField(max_length=36, blank=True, default="")
    fingerprint = models.CharField(max_length=64)
    error_type = models.CharField(max_length=64)
    error_code = models.CharField(max_length=64, blank=True, default="")
    message_template = models.TextField()
    count = models.PositiveBigIntegerField(default=0)
    first_seen_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    node_count = models.PositiveIntegerField(default=1)
    node_ids = models.JSONField(default=list, blank=True, help_text="int[]")
    samples = models.JSONField(default=list, blank=True, help_text="PerfErrorSample[] v1")

    class Meta:
        db_table = "perf_run_error"
        ordering = ["-count", "id"]
        constraints = [
            models.UniqueConstraint(fields=["run", "step_key", "fingerprint"], name="uniq_perf_error_fingerprint")]


class PerfRunEvent(models.Model):
    run = models.ForeignKey(PerfRun, on_delete=models.CASCADE, related_name="events")
    run_node = models.ForeignKey(PerfRunNode, on_delete=models.CASCADE, null=True, blank=True, related_name="events")
    event_type = models.CharField(max_length=64, db_index=True)
    level = models.CharField(max_length=16, default="info")
    message = models.CharField(max_length=512)
    detail = models.JSONField(default=dict, blank=True, help_text="PerfRunEventDetail v1")
    occurred_at = models.DateTimeField(db_index=True)
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "perf_run_event"
        ordering = ["occurred_at", "id"]


class PerfRunSecretEnvelope(models.Model):
    run = models.ForeignKey(PerfRun, on_delete=models.CASCADE, related_name="secret_envelopes")
    envelope_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    cipher_text = models.BinaryField()
    key_reference = models.CharField(max_length=255)
    algorithm = models.CharField(max_length=32)
    expires_at = models.DateTimeField(db_index=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "perf_run_secret_envelope"
        ordering = ["-create_time"]


class PerfBaseline(AuditModel):
    scenario = models.ForeignKey(PerfScenario, on_delete=models.PROTECT, related_name="baselines")
    run = models.ForeignKey(PerfRun, on_delete=models.PROTECT, related_name="baseline_references")
    name = models.CharField(max_length=128)
    environment_key = models.CharField(max_length=64)
    engine = models.CharField(max_length=24, choices=PerfEngineEnum.choices())
    snapshot_hash = models.CharField(max_length=64)
    active = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="created_perf_baselines")

    class Meta:
        db_table = "perf_baseline"
        ordering = ["-create_time"]
        constraints = [
            models.UniqueConstraint(fields=["scenario", "environment_key", "engine"], condition=models.Q(active=True),
                                    name="uniq_active_perf_baseline")]
