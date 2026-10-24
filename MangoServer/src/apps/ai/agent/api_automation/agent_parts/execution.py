# -*- coding: utf-8 -*-
from src.apps.ai.agent.api_automation.executor import ApiAutomationExecutor
from src.apps.ai.agent.api_automation.skill_contract import ApiAutomationSkillContractCompiler
from src.apps.ai.agent.api_automation.tool_catalog import ApiAutomationToolStageCatalog
from src.apps.ai.agent.api_automation.workflow_planner import ApiAutomationWorkflowPlanner
from src.apps.ai.enums import AiAgentTaskStatusEnum, AiSkillTypeEnum
from src.apps.ai.exceptions import ai_service_error
from src.apps.ai.models import AiAgentTask, AiAgentTaskItem, AiMcpServer
from src.apps.ai.services.agent.mcp.registry import AgentMcpRegistry
from src.apps.ai.services.agent.task_step import AiAgentTaskStepService
from src.apps.ai.services.core import AiTaskService
from src.apps.ai.services.harness.artifact import AgentArtifactService
from src.apps.ai.services.skill.service import AgentSkillService
from src.apps.functional_test.enums import ManualTestAutomationTypeEnum
from src.apps.functional_test.selectors.querysets import FunctionalTestQuerySelector


class ApiAutomationExecutionMixin:
    @classmethod
    def run(cls, task: AiAgentTask):
        input_data = task.input_data or {}
        if input_data.get("mode") == "batch":
            return cls.run_batch(task)
        manual_case = FunctionalTestQuerySelector.manual_test_case().select_related("suite", "project_product",
                                                                                    "module").get(
            id=input_data.get("manual_case_id"))
        suite = manual_case.suite
        context_package = cls.load_context_snapshot(task, suite)
        skill = AgentSkillService.materialize_task_skill(
            task,
            AgentSkillService.get_skill(skill_id=input_data.get("skill_id") or None),
        )
        mcp_servers = list(AiMcpServer.objects.filter(id__in=input_data.get("mcp_server_ids") or []))
        task_item = AiAgentTaskItem.objects.get(task=task, manual_case_id=manual_case.id)
        task.active_task_item_id = task_item.id
        task_item.status = AiAgentTaskStatusEnum.RUNNING.value
        task_item.current_step_key = "collect_context"
        task_item.attempt_no += 1
        task_item.save(update_fields=["status", "current_step_key", "attempt_no", "update_time"])
        try:
            cls.execute_checkpointed_step(
                task,
                "collect_context",
                lambda: {
                    "context_hash": context_package["context_hash"],
                    "reuse_context": context_package["reuse_context"],
                    "reuse_context_id": context_package["reuse_context_id"],
                },
                input_data={"selected_context_keys": context_package["context_keys"]},
            )
            if not skill:
                raise ai_service_error("选择的技能不存在或未发布")
            if skill.skill_type != AiSkillTypeEnum.API_AUTOMATION.value:
                raise ai_service_error("生成API自动化只能选择API自动化类型的技能")
            if not mcp_servers:
                raise ai_service_error("选择的MCP服务不存在或已停用")

            def load_capabilities():
                _, tool_map = ApiAutomationExecutor.build_tools(
                    mcp_servers,
                    task.create_user_id,
                    input_data.get("existing_api_case_id") or None,
                    refresh=True,
                )
                capability_catalog = ApiAutomationToolStageCatalog.catalog_for_tools(tool_map)
                mcp_snapshot = AgentMcpRegistry.capability_snapshot(
                    mcp_servers,
                    list({tool.id: tool for tool in tool_map.values()}.values()),
                )
                task.mcp_snapshot = mcp_snapshot
                task.save(update_fields=["mcp_snapshot", "update_time"])
                return {
                    "mcp_server_ids": [server.id for server in mcp_servers],
                    "mcp_server_names": [server.name for server in mcp_servers],
                    "mcp_server_prompts": {server.id: server.prompt or "" for server in mcp_servers},
                    "capabilities": capability_catalog,
                    "snapshot": mcp_snapshot,
                }

            capability_data = cls.execute_checkpointed_step(
                task,
                "load_capabilities",
                load_capabilities,
            )
            capability_catalog = capability_data.get("capabilities") or []
            skill_contract = cls.execute_checkpointed_step(
                task,
                "compile_skill",
                lambda: ApiAutomationSkillContractCompiler.compile(
                    skill,
                    task.skill_version,
                    task=task,
                ),
            )

            workflow_plan = cls.execute_checkpointed_step(
                task,
                "plan_workflow",
                lambda: ApiAutomationWorkflowPlanner.plan(
                    manual_case=manual_case,
                    suite=suite,
                    skill=skill,
                    context_package=context_package,
                    existing_api_case_id=input_data.get("existing_api_case_id") or None,
                    tool_catalog=capability_catalog,
                    user_instruction=input_data.get("user_instruction") or "",
                    ai_role=input_data.get("ai_role") or cls.fixed_role,
                    skill_contract=skill_contract,
                    task=task,
                ),
            )

            def validate_plan():
                available_tools = {
                    name
                    for item in capability_catalog
                    for name in item["available_tool_names"]
                }
                result = {
                    "has_write_tool": bool(available_tools & ApiAutomationExecutor.API_UPDATE_TOOLS),
                    "has_assertion_tool": bool(
                        available_tools & set(ApiAutomationToolStageCatalog.TOOL_GROUPS["assertions"])
                    ),
                    "has_execution_tool": bool(
                        available_tools & set(ApiAutomationToolStageCatalog.TOOL_GROUPS["execution"])
                    ),
                }
                result["missing_skill_capabilities"] = cls.missing_skill_capabilities(
                    skill_contract,
                    available_tools,
                )
                if not all(
                        result[key]
                        for key in ("has_write_tool", "has_assertion_tool", "has_execution_tool")
                ) or result["missing_skill_capabilities"]:
                    raise ai_service_error(f"MCP 能力不满足 API 自动化基础门禁：{result}")
                return result

            cls.execute_checkpointed_step(task, "validate_plan", validate_plan)

            plan = cls.execute_checkpointed_step(
                task,
                "execute_stages",
                lambda: ApiAutomationExecutor.execute(
                    task=task,
                    manual_case=manual_case,
                    suite=suite,
                    skill=skill,
                    mcp_servers=mcp_servers,
                    context_package=context_package,
                    existing_api_case_id=input_data.get("existing_api_case_id") or None,
                    ai_role=input_data.get("ai_role") or cls.fixed_role,
                    user_instruction=input_data.get("user_instruction") or "",
                    user_id=task.create_user_id,
                    skill_contract=skill_contract,
                    workflow_plan=workflow_plan,
                ),
                summarize=lambda value: {
                    "tool_call_count": len(value.get("tool_calls") or []),
                    "api_case_id": value.get("api_case_id"),
                    "execution_record_id": value.get("execution_record_id"),
                },
                artifact_status="committed",
            )
            cls.validate_skill_execution(skill_contract, plan)
            verification = cls.execute_checkpointed_step(
                task,
                "verify_api_assets",
                lambda: {
                    "api_case_id": plan.get("api_case_id"),
                    "assertion_summary": plan.get("assertion_summary") or {},
                },
            )
            AgentArtifactService.evaluate(
                task,
                "api_asset_verifier",
                passed=bool(
                    verification.get("api_case_id")
                    and (verification.get("assertion_summary") or {}).get("total_assertion_count")
                ),
                metrics=verification.get("assertion_summary") or {},
            )
            cls.execute_checkpointed_step(
                task,
                "execute_api_case",
                lambda: {
                    "executed": True,
                    "execution_record_id": plan.get("execution_record_id"),
                },
            )
            cls.execute_checkpointed_step(
                task,
                "diagnose_and_repair",
                lambda: plan.get("asset_repair_report") or {"required": False},
            )
            cls.execute_checkpointed_step(
                task,
                "bind_result",
                lambda: {"binding_id": plan.get("binding_id")},
                artifact_status="committed",
            )
            cls.execute_checkpointed_step(
                task,
                "post_validate",
                lambda: cls.post_validate_plan(task, manual_case, input_data, plan, skill_contract),
            )
            task_item.status = AiAgentTaskStatusEnum.SUCCESS.value
            task_item.api_case_id = plan.get("api_case_id")
            task_item.execution_record_id = plan.get("execution_record_id")
            task_item.current_step_key = "post_validate"
            task_item.result_summary = {
                "summary": plan.get("diff_summary") or "已生成并执行一次",
                "binding_id": plan.get("binding_id"),
            }
            task_item.error_message = None
            task_item.save(
                update_fields=[
                    "status",
                    "api_case_id",
                    "execution_record_id",
                    "current_step_key",
                    "result_summary",
                    "error_message",
                    "update_time",
                ]
            )
            AiTaskService.finish_task(task, plan)
            cls.save_generation_context(
                suite=suite,
                manual_case=manual_case,
                task_snapshot=cls.task_snapshot(task),
                context_package=context_package,
                selected_context_keys=context_package["context_keys"],
                plan=plan,
                user_id=task.create_user_id,
                status=AiAgentTaskStatusEnum.SUCCESS.value,
                user_instruction=input_data.get("user_instruction") or "",
            )
        except Exception as exc:
            running = task.aiagenttaskstep_set.filter(status=AiAgentTaskStatusEnum.RUNNING.value).order_by(
                "-update_time").first()
            if running:
                AiAgentTaskStepService.fail_step(task, running.step_key, exc)
            task_item.status = AiAgentTaskStatusEnum.FAIL.value
            task_item.error_message = str(exc)[:1000]
            task_item.result_summary = {"summary": "生成失败"}
            task_item.save(update_fields=["status", "error_message", "result_summary", "update_time"])
            AiTaskService.fail_task(task, str(exc))
            if skill:
                cls.save_generation_context(
                    suite=suite,
                    manual_case=manual_case,
                    task_snapshot=cls.task_snapshot(task),
                    context_package=context_package,
                    selected_context_keys=context_package["context_keys"],
                    plan={"task_id": task.id, "tool_calls": [], "diff_summary": "生成 API Case 失败"},
                    user_id=task.create_user_id,
                    status=AiAgentTaskStatusEnum.FAIL.value,
                    user_instruction=input_data.get("user_instruction") or "",
                    error_message=str(exc),
                )
            raise
        finally:
            task.active_task_item_id = None

    @classmethod
    def run_batch(cls, task: AiAgentTask):
        input_data = task.input_data or {}
        suite_id = input_data.get("suite_id")
        suite = FunctionalTestQuerySelector.manual_test_suite().get(id=suite_id)
        manual_case_ids = input_data.get("manual_case_ids") or []
        manual_cases = list(
            FunctionalTestQuerySelector.manual_test_case().select_related("suite", "project_product", "module").filter(
                id__in=manual_case_ids, suite_id=suite.id))
        case_map = {case.id: case for case in manual_cases}
        ordered_cases = [case_map[case_id] for case_id in manual_case_ids if case_id in case_map]
        task_item_map = {
            item.manual_case_id: item
            for item in AiAgentTaskItem.objects.filter(task=task)
        }
        retry_case_ids = input_data.get("retry_pending_case_ids") or []
        if retry_case_ids:
            execute_case_ids = [
                case_id
                for case_id in retry_case_ids
                if getattr(task_item_map.get(case_id), "status", None) != AiAgentTaskStatusEnum.SUCCESS.value
            ]
        else:
            recoverable_statuses = {
                AiAgentTaskStatusEnum.PENDING.value,
                AiAgentTaskStatusEnum.CLAIMED.value,
                AiAgentTaskStatusEnum.RUNNING.value,
                AiAgentTaskStatusEnum.WAITING_MODEL.value,
            }
            execute_case_ids = [
                case_id
                for case_id in manual_case_ids
                if getattr(task_item_map.get(case_id), "status", AiAgentTaskStatusEnum.PENDING.value)
                   in recoverable_statuses
            ]
        execute_cases = [case_map[case_id] for case_id in execute_case_ids if case_id in case_map]
        if not ordered_cases:
            raise ai_service_error("批量API自动化任务中的用例已不存在，请重新选择后再生成")
        context_package = cls.load_context_snapshot(task, suite)
        skill = AgentSkillService.materialize_task_skill(
            task,
            AgentSkillService.get_skill(skill_id=input_data.get("skill_id") or None),
        )
        mcp_servers = list(AiMcpServer.objects.filter(id__in=input_data.get("mcp_server_ids") or []))
        items = cls.build_batch_items(task, ordered_cases)
        execute_case_id_set = {case.id for case in execute_cases}
        for item in items:
            if item.get("manual_case_id") in execute_case_id_set and item.get("status") != "success":
                item["status"] = "pending"
                item.pop("error_message", None)
                item["summary"] = "等待继续生成"
        success_count = len([item for item in items if item.get("status") == "success"])
        fail_count = len(
            [
                item
                for item in items
                if item.get("status") == "fail" and item.get("manual_case_id") not in execute_case_id_set
            ]
        )
        try:
            cls.execute_checkpointed_step(
                task,
                "collect_context",
                lambda: {
                    "context_hash": context_package["context_hash"],
                    "reuse_context": context_package["reuse_context"],
                    "reuse_context_id": context_package["reuse_context_id"],
                },
                input_data={"selected_context_keys": context_package["context_keys"]},
            )
            if not skill:
                raise ai_service_error("选择的技能不存在或未发布")
            if skill.skill_type != AiSkillTypeEnum.API_AUTOMATION.value:
                raise ai_service_error("生成API自动化只能选择API自动化类型的技能")
            if not mcp_servers:
                raise ai_service_error("选择的MCP服务不存在或已停用")

            def load_batch_capabilities():
                _, tool_map = ApiAutomationExecutor.build_tools(
                    mcp_servers,
                    task.create_user_id,
                    None,
                    refresh=True,
                )
                capability_catalog = ApiAutomationToolStageCatalog.catalog_for_tools(tool_map)
                mcp_snapshot = AgentMcpRegistry.capability_snapshot(
                    mcp_servers,
                    list({tool.id: tool for tool in tool_map.values()}.values()),
                )
                task.mcp_snapshot = mcp_snapshot
                task.save(update_fields=["mcp_snapshot", "update_time"])
                return {
                    "mcp_server_ids": [server.id for server in mcp_servers],
                    "mcp_server_names": [server.name for server in mcp_servers],
                    "mcp_server_prompts": {server.id: server.prompt or "" for server in mcp_servers},
                    "capabilities": capability_catalog,
                    "snapshot": mcp_snapshot,
                }

            capability_data = cls.execute_checkpointed_step(
                task,
                "load_capabilities",
                load_batch_capabilities,
            )
            capability_catalog = capability_data.get("capabilities") or []
            skill_contract = cls.execute_checkpointed_step(
                task,
                "compile_skill",
                lambda: ApiAutomationSkillContractCompiler.compile(
                    skill,
                    task.skill_version,
                    task=task,
                ),
            )
            cls.execute_checkpointed_step(
                task,
                "plan_workflow",
                lambda: {
                    "mode": "batch",
                    "total": len(ordered_cases),
                    "required_capabilities": skill_contract["required_capabilities"],
                },
            )

            def validate_batch_plan():
                available_tools = {
                    name
                    for item in capability_catalog
                    for name in item["available_tool_names"]
                }
                result = {
                    "has_write_tool": bool(available_tools & ApiAutomationExecutor.API_UPDATE_TOOLS),
                    "has_assertion_tool": bool(
                        available_tools & set(ApiAutomationToolStageCatalog.TOOL_GROUPS["assertions"])
                    ),
                    "has_execution_tool": bool(
                        available_tools & set(ApiAutomationToolStageCatalog.TOOL_GROUPS["execution"])
                    ),
                }
                result["missing_skill_capabilities"] = cls.missing_skill_capabilities(
                    skill_contract,
                    available_tools,
                )
                if not all(
                        result[key]
                        for key in ("has_write_tool", "has_assertion_tool", "has_execution_tool")
                ) or result["missing_skill_capabilities"]:
                    raise ai_service_error(f"MCP 能力不满足 API 自动化基础门禁：{result}")
                return result

            cls.execute_checkpointed_step(task, "validate_plan", validate_batch_plan)

            AiAgentTaskStepService.start_step(task, "execute_stages")
            cls.update_batch_progress(task, items, success_count + fail_count, success_count, fail_count,
                                      f"批量任务已开始，待处理 {len(execute_cases)} 条用例")
            bindings = {
                item.manual_case_id: item
                for item in FunctionalTestQuerySelector.manual_test_automation_binding().filter(
                    manual_case_id__in=[case.id for case in execute_cases],
                    automation_type=ManualTestAutomationTypeEnum.API.value,
                )
            }
            item_map = {item.get("manual_case_id"): item for item in items}
            for index, manual_case in enumerate(execute_cases, start=1):
                item = item_map.get(manual_case.id)
                if not item:
                    continue
                item["status"] = "running"
                task_item = AiAgentTaskItem.objects.get(task=task, manual_case_id=manual_case.id)
                task.active_task_item_id = task_item.id
                task_item.status = AiAgentTaskStatusEnum.RUNNING.value
                task_item.current_step_key = "execute_stages"
                task_item.attempt_no += 1
                task_item.save(update_fields=["status", "current_step_key", "attempt_no", "update_time"])
                cls.update_batch_progress(
                    task,
                    items,
                    success_count + fail_count + 1,
                    success_count,
                    fail_count,
                    f"正在处理 {index}/{len(execute_cases)}：{manual_case.case_no} / {manual_case.title}",
                )
                try:
                    existing = bindings.get(manual_case.id)
                    plan = ApiAutomationExecutor.execute(
                        task=task,
                        manual_case=manual_case,
                        suite=suite,
                        skill=skill,
                        mcp_servers=mcp_servers,
                        context_package=context_package,
                        existing_api_case_id=existing.api_case_id if existing else None,
                        ai_role=input_data.get("ai_role") or cls.fixed_role,
                        user_instruction=input_data.get("user_instruction") or "",
                        user_id=task.create_user_id,
                        skill_contract=skill_contract,
                    )
                    AgentArtifactService.create(
                        task,
                        "tool_plan",
                        plan.get("workflow_plan") or {},
                        task_item=task_item,
                        status="validated",
                    )
                    cls.validate_skill_execution(skill_contract, plan)
                    verification = cls.post_validate_plan(
                        task,
                        manual_case,
                        {"existing_api_case_id": existing.api_case_id if existing else None},
                        plan,
                        skill_contract,
                    )
                    AgentArtifactService.evaluate(
                        task,
                        "api_asset_verifier",
                        passed=True,
                        metrics=verification,
                        task_item=task_item,
                    )
                    item.update(
                        {
                            "status": "success",
                            "api_case_id": plan.get("api_case_id"),
                            "binding_id": plan.get("binding_id"),
                            "summary": plan.get("diff_summary") or "已生成并执行一次",
                        }
                    )
                    success_count += 1
                    task_item.status = AiAgentTaskStatusEnum.SUCCESS.value
                    task_item.api_case_id = plan.get("api_case_id")
                    task_item.execution_record_id = plan.get("execution_record_id")
                    task_item.result_summary = {
                        "summary": item.get("summary"),
                        "binding_id": plan.get("binding_id"),
                    }
                    task_item.error_message = None
                    task_item.save(
                        update_fields=[
                            "status",
                            "api_case_id",
                            "execution_record_id",
                            "result_summary",
                            "error_message",
                            "update_time",
                        ]
                    )
                except Exception as exc:
                    item.update({"status": "fail", "error_message": str(exc)[:1000], "summary": "生成失败"})
                    fail_count += 1
                    task_item.status = AiAgentTaskStatusEnum.FAIL.value
                    task_item.error_message = str(exc)[:1000]
                    task_item.result_summary = {"summary": "生成失败"}
                    task_item.save(update_fields=["status", "error_message", "result_summary", "update_time"])
                finally:
                    task.active_task_item_id = None
                cls.update_batch_progress(
                    task,
                    items,
                    success_count + fail_count,
                    success_count,
                    fail_count,
                    f"已处理 {index}/{len(execute_cases)}：成功 {success_count}，失败 {fail_count}",
                )
            AiAgentTaskStepService.finish_step(task, "execute_stages",
                                               {"success_count": success_count, "fail_count": fail_count,
                                                "total": len(ordered_cases)})
            output = cls.batch_output(task, items, len(ordered_cases), success_count, fail_count)
            status = (
                AiAgentTaskStatusEnum.SUCCESS.value
                if success_count == len(ordered_cases)
                else AiAgentTaskStatusEnum.PARTIAL_SUCCESS.value
                if success_count
                else AiAgentTaskStatusEnum.FAIL.value
            )
            for step_key, step_output in (
                    ("verify_api_assets", {"verified_count": success_count, "failed_count": fail_count}),
                    ("execute_api_case", {"executed_count": success_count}),
                    ("diagnose_and_repair",
                     {"failed_count": fail_count, "continued": True, "item_repairs_recorded": True}),
                    ("bind_result", {"bound_count": success_count}),
                    ("post_validate", output),
            ):
                AiAgentTaskStepService.start_step(task, step_key)
                AiAgentTaskStepService.finish_step(task, step_key, step_output)
            if status == AiAgentTaskStatusEnum.FAIL.value:
                AiTaskService.fail_task(task, "批量生成API自动化全部失败", output)
            else:
                AiTaskService.finish_task(task, output, status=status)
            cls.save_batch_generation_context(
                suite=suite,
                task_snapshot=cls.task_snapshot(task),
                context_package=context_package,
                selected_context_keys=context_package["context_keys"],
                output=output,
                user_id=task.create_user_id,
                status=status,
                user_instruction=input_data.get("user_instruction") or "",
            )
        except Exception as exc:
            running = task.aiagenttaskstep_set.filter(status=AiAgentTaskStatusEnum.RUNNING.value).order_by(
                "-update_time").first()
            if running:
                AiAgentTaskStepService.fail_step(task, running.step_key, exc)
            output = cls.batch_output(task, items, 0, success_count, fail_count)
            AiTaskService.fail_task(task, str(exc), output)
            cls.save_batch_generation_context(
                suite=suite,
                task_snapshot=cls.task_snapshot(task),
                context_package=context_package,
                selected_context_keys=context_package["context_keys"],
                output=output,
                user_id=task.create_user_id,
                status=AiAgentTaskStatusEnum.FAIL.value,
                user_instruction=input_data.get("user_instruction") or "",
                error_message=str(exc),
            )
            raise
