"""Evaluation MCP tools delegate to scoped domain queries and services."""

from src.interfaces.mcp.common import current_user, ok
from src.apps.evaluation import presenters
from src.apps.evaluation.selectors import assets
from src.apps.evaluation.selectors.case import get_case
from src.apps.evaluation.selectors.dataset_version import get_dataset_version
from src.apps.evaluation.selectors.dataset_item import get_dataset_item
from src.apps.evaluation.selectors.execution import case_executions, get_execution
from src.apps.evaluation.selectors.querysets import EvaluationQuerySelector
from src.apps.evaluation.services import assets as mutations
from src.apps.evaluation.services.graders import EvaluationGraderRegistry
from src.apps.evaluation.services.dataset_version import EvaluationDatasetVersionService
from src.apps.evaluation.services.dataset_item import EvaluationDatasetItemService
from src.apps.evaluation.services.versioning import EvaluationVersionService
from src.apps.evaluation.services.execution import EvaluationCaseExecutionService


def register_evaluation_tools(mcp):
    @mcp.tool()
    def list_evaluation_ai_profiles(case_id: int, page: int = 1, page_size: int = 10) -> dict:
        """分页列出 Case 可选效果测评 AI，仅返回标识、名称、模型和启用状态，不返回密钥或地址。"""
        from src.apps.evaluation.services.ai import ai_options
        options = ai_options(case_id, current_user())
        page, page_size = max(1, page), max(1, min(50, page_size))
        return ok({"items": options[(page-1)*page_size:page*page_size], "count": len(options), "page": page, "page_size": page_size})

    @mcp.tool()
    def get_evaluation_schema() -> dict:
        """读取效果 Case 的严格配置契约，包括运行时上下文和数组投影。"""
        from src.apps.evaluation.schemas.case import EvaluationCaseConfig
        from src.apps.evaluation.schemas.dataset import EvaluationDatasetSchema
        from src.apps.evaluation.schemas.item import EvaluationDatasetItemPayload
        return ok({**EvaluationCaseConfig.model_json_schema(), "dataset_schema": EvaluationDatasetSchema.model_json_schema(), "item_schema": EvaluationDatasetItemPayload.model_json_schema()})

    @mcp.tool()
    def create_evaluation_dataset(name: str, task_type: list[str], description: str = "") -> dict:
        """按名称复用全局题库；不存在时创建草稿，仍要求数据集权限。"""
        record, created = mutations.ensure_dataset({"name": name,
            "task_type": task_type, "description": description}, current_user())
        return ok({"dataset": presenters.dataset_record(record), "created": created})

    @mcp.tool()
    def list_evaluation_datasets(name: str | None = None,
                                 page: int = 1, page_size: int = 20) -> dict:
        """分页盘点已有数据集；不自动新建或复制题库。"""
        return ok(assets.page(assets.datasets(current_user(), name), presenters.dataset_record, page, page_size))

    @mcp.tool()
    def list_evaluation_dataset_versions(dataset_id: int, page: int = 1, page_size: int = 20) -> dict:
        """查询已有数据集版本及固定内容摘要。"""
        return ok(assets.page(assets.versions(dataset_id, current_user()), presenters.version_record, page, page_size))

    @mcp.tool()
    def list_evaluation_dataset_items(version_id: int, page: int = 1, page_size: int = 20) -> dict:
        """读取指定版本的输入、金标准、上下文和评分覆盖。"""
        version = get_dataset_version(version_id, current_user())
        return ok(assets.page(assets.version_items(version), presenters.item_record, page, page_size))

    @mcp.tool()
    def get_evaluation_dataset_quality(version_id: int) -> dict:
        """只读检查题库质量，不自动确认警告或发布。"""
        return ok(EvaluationVersionService.dataset_quality(get_dataset_version(version_id, current_user())))

    @mcp.tool()
    def update_evaluation_dataset_item(item_id: int, expected_output: dict, metadata: dict | None = None) -> dict:
        """修改草稿条目的标准答案和可选附加信息；沿用字段校验，已发布条目不可修改，不改变启用状态。"""
        item = get_dataset_item(item_id, current_user())
        values = {"expected_output": expected_output}
        if metadata is not None:
            values["metadata"] = metadata
        record = EvaluationDatasetItemService.save(
            values=values, version=item.dataset_version, instance=item)
        return ok(presenters.item_record(record))

    @mcp.tool()
    def create_evaluation_dataset_item(version_id: int, item: dict) -> dict:
        """新增草稿数据条目，结构见 get_evaluation_schema.item_schema；校验版本、字段和数据来源，不自动发布。"""
        return ok(presenters.item_record(mutations.create_dataset_item(version_id, item, current_user())))

    @mcp.tool()
    def create_evaluation_dataset_version(dataset_id: int, source_version_id: int | None = None,
                                           version_label: str = "", change_summary: str = "", schema_snapshot: dict | None = None) -> dict:
        """为已有数据集创建草稿版本，可复制同一数据集已有版本。"""
        values = {"version_label": version_label, "change_summary": change_summary}
        if schema_snapshot is not None:
            values["schema_snapshot"] = schema_snapshot
        version = EvaluationDatasetVersionService.create(dataset_id=dataset_id, source_version_id=source_version_id,
            values=values, user=current_user())
        return ok(presenters.version_record(version))

    @mcp.tool()
    def update_evaluation_dataset_version(version_id: int, schema_snapshot: dict, version_label: str | None = None) -> dict:
        """编辑草稿的输入变量、数据准备流程和字段定义；已发布版本不可修改。"""
        values = {"schema_snapshot": schema_snapshot}
        if version_label is not None:
            values["version_label"] = version_label
        version = EvaluationDatasetVersionService.update(get_dataset_version(version_id, current_user()), values)
        return ok(presenters.version_record(version))

    @mcp.tool()
    def delete_evaluation_dataset_version(version_id: int) -> dict:
        """删除草稿版本及其数据条目；已发布或被引用的版本不可删除。"""
        EvaluationDatasetVersionService.delete(version_id, current_user())
        return ok({"deleted": True, "version_id": version_id})

    @mcp.tool()
    def list_evaluation_workflow_resources(version_id: int, action: str, project_product_id: int,
                                          search: str = "", page: int = 1, page_size: int = 20, module_id: int | None = None) -> dict:
        """按资源执行权限与项目范围查询 HTTP/SSE 接口、逻辑数据源或数据工厂。"""
        from src.apps.evaluation.selectors.workflow import resource_choices
        from src.apps.evaluation.enums.workflow import EvaluationWorkflowActionEnum
        from src.apps.evaluation.services.validation import invalid_config
        get_dataset_version(version_id, current_user())
        try:
            action_type = EvaluationWorkflowActionEnum(action)
        except ValueError as error:
            raise invalid_config("未知流程资源类型") from error
        return ok(resource_choices(action_type, current_user(), project_product_id, search=search,
                                  page=max(1, page), page_size=min(100, max(1, page_size)), module_id=module_id))

    @mcp.tool()
    def publish_evaluation_dataset_version(version_id: int) -> dict:
        """发布经过质量校验的草稿，不自动忽略质量警告。"""
        user = current_user()
        get_dataset_version(version_id, user)
        return ok(presenters.version_record(EvaluationVersionService.publish_dataset_version(version_id, user)))

    @mcp.tool()
    def list_evaluation_graders() -> dict:
        """只读算法与严格参数目录，不调用裁判模型。"""
        return ok(EvaluationGraderRegistry.catalog())

    @mcp.tool()
    def list_evaluation_cases(project_product_id: int | None = None, page: int = 1, page_size: int = 20) -> dict:
        """分页读取调用者有权访问的效果 Case。"""
        queryset = EvaluationQuerySelector.cases(current_user())
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
        return ok(assets.page(queryset.order_by("-id"), presenters.case_summary, page, page_size))

    @mcp.tool()
    def get_evaluation_case(case_id: int) -> dict:
        """读取效果 Case 及固定数据版本、目标版本和评分配置。"""
        return ok(presenters.case_record(get_case(case_id, current_user())))

    @mcp.tool()
    def create_evaluation_case(name: str, dataset_version_id: int | None = None, config: dict | None = None, description: str = "", project_product_id: int | None = None) -> dict:
        """创建草稿 Case；未绑定题库时必须指定项目产品，之后再配置，不自动启用。"""
        return ok(presenters.case_record(mutations.create_case({"name": name, "dataset_version_id": dataset_version_id,
            "config": config, "description": description, "project_product_id": project_product_id}, current_user())))

    @mcp.tool()
    def update_evaluation_case(case_id: int, config: dict | None = None, name: str | None = None, description: str | None = None, dataset_version_id: int | None = None) -> dict:
        """更新配置及可选名称、说明、数据版本；保留归属、状态和已有历史快照。"""
        values = {"config": config} if config is not None else {}
        for key, value in {"name": name, "description": description, "dataset_version_id": dataset_version_id}.items():
            if value is not None:
                values[key] = value
        return ok(presenters.case_record(mutations.update_case(case_id, values, current_user())))

    @mcp.tool()
    def update_evaluation_case_status(case_id: int, status: str) -> dict:
        """仅修改 Case 状态，独立要求状态权限。"""
        return ok(presenters.case_record(mutations.set_case_status(case_id, status, current_user())))

    @mcp.tool()
    def run_evaluation_case(case_id: int, test_env: int, idempotency_key: str, item_ids: list[int] | None = None) -> dict:
        """异步执行固定 Case；重发必须复用同一幂等键，返回执行编号。"""
        return ok(presenters.execution_record(mutations.execute_case(case_id, test_env, idempotency_key, current_user(), item_ids)))

    @mcp.tool()
    def list_evaluation_case_executions(case_id: int, page: int = 1, page_size: int = 20) -> dict:
        """读取本 Case 历史执行，不生成独立报告。"""
        return ok(assets.page(case_executions(case_id, current_user()).order_by("-id"), presenters.execution_record, page, page_size))

    @mcp.tool()
    def get_evaluation_case_execution(case_id: int, execution_id: int) -> dict:
        """读取执行状态、复现快照和汇总分数。"""
        return ok(presenters.execution_record(get_execution(case_id, execution_id, current_user())))

    @mcp.tool()
    def list_evaluation_item_results(case_id: int, execution_id: int, page: int = 1, page_size: int = 20) -> dict:
        """读取逐条实际输出、评分理由和证据，校验 Case 与执行归属。"""
        execution = get_execution(case_id, execution_id, current_user())
        return ok(assets.page(assets.execution_items(execution), presenters.result_record, page, page_size))

    @mcp.tool()
    def stop_evaluation_case_execution(case_id: int, execution_id: int) -> dict:
        """对指定 Case 的执行写入停止意图，保留历史结果。"""
        record = get_execution(case_id, execution_id, current_user())
        EvaluationCaseExecutionService.stop(record.id)
        return ok({"id": record.id})

    @mcp.tool()
    def retry_evaluation_case_execution(case_id: int, execution_id: int, idempotency_key: str) -> dict:
        """按原快照重试失败条目，不套用后来编辑的用例配置。"""
        user = current_user()
        record = get_execution(case_id, execution_id, user)
        retried = EvaluationCaseExecutionService.retry_failed(record.id, user, idempotency_key)
        EvaluationCaseExecutionService.submit(retried.id)
        return ok(presenters.execution_record(retried))
