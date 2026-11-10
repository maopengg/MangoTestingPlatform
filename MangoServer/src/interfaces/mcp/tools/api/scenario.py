from __future__ import annotations

from typing import Literal

from django.forms import model_to_dict
from genson import SchemaBuilder

from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_api.services.api_case.mutation import ApiCaseAggregateMutationService
from src.apps.auto_api.services.api_case.mutation_io import ApiCaseParameterMutationService
from src.apps.auto_api.services.api_case.schema import ApiCaseScenarioSchemaService
from src.interfaces.mcp.audit import mcp_current_user_id, mcp_with_update_user
from src.interfaces.mcp.common import ok, paginate_queryset
from .helper_parts.execution import _find_json_paths
from .helpers import (
    Any,
    fail,
    jsonlib,
)
from .helpers import (
    _json_string,
    _normalize_ass_jsonpath,
    _normalize_scenario_payload,
    _require_published_api_case_modify_confirmation,
    _validate_api_case_sql_datasources,
)


def register_scenario_tools(mcp):
    @mcp.tool()
    def list_api_case_scenarios(step_id: int, page: int = 1, page_size: int = 10) -> dict:
        """查询 API case 步骤下的场景参数。"""
        queryset = ApiQuerySelector.api_case_detailed_parameter().filter(case_detailed_id=step_id).order_by("id")
        queryset, count, page, page_size = paginate_queryset(queryset, page, page_size)
        items = [model_to_dict(item) for item in queryset]
        return ok({"items": items, "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def create_api_case_scenario(
            step_id: int,
            name: str,
            error_retry: int | None = None,
            retry_interval: int | None = None,
            allow_failure: bool = False,
            headers: list[int] | None = None,
            params: str | dict | list | None = None,
            body_config: dict | None = None,
            sse_config: dict | None = None,
            front_sql: list | None = None,
            front_func: str | None = None,
            ass_jsonpath: list | None = None,
            ass_general: list | None = None,
            ass_json_all: dict | list | None = None,
            ass_text_all: str | None = None,
            ass_schema: dict | None = None,
            posterior_response: list | None = None,
            posterior_response_text: list | None = None,
            posterior_sql: list | None = None,
            posterior_sleep: int | None = None,
            posterior_func: str | None = None,
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """给步骤创建一个场景参数。

        复杂字段格式见 get_api_case_schema.api_case_scenario_fields。
        优先平台配置：简单/嵌套 JSON 直接填 body_config，动态值用变量/数据方法；取值用提取器，验证用断言。
        仅现有配置无法表达的请求计算或响应解码/派生计算才用 front_func/posterior_func，并说明能力缺口；不得为 JSON 拼装/序列化或原样返回写函数，也不改响应或吞错刷通过。详见 get_api_case_schema.execution_rules.function_usage。
        allow_failure=true 时，场景在全部重试后仍失败会标记为警告并继续执行后续步骤；默认 false。
        headers 只传 ApiHeaders.id 数组；只要 headers 非空，就会完全覆盖 API case 的 front_headers，不会合并。
        headers 为空时回退到 API case.front_headers；如果 front_headers 也为空，则使用当前项目产品下 status=1 的 ApiHeaders。
        front_sql/posterior_sql 每条 SQL 必须传 datasource_alias；可传 test_envs 多选执行环境，不传、null 或 [] 表示全部环境执行。
        SQL 的 key 支持单个缓存变量，也支持 id,name 这种英文逗号分隔多 key；查询结果取第一行，按列名优先、列顺序兜底写入多个缓存变量。
        先调用 list_data_factory_datasource_aliases 查询数据库。
        ass_jsonpath 是响应提取断言；assertion_type=jsonpath 时 actual 是 JSONPath，regex 时 actual 是正则表达式，cache 时 actual 必须是完整的 ${{key}} 缓存表达式；不传默认 jsonpath。取值后再执行 method。
        断言关系可传 group_name/group_logic；group_logic=AND 是且，OR 是或，不传默认 AND。
        如果 method 的参数只有 actual、没有 expect，例如 p_is_none/p_is_true/p_is_false，expect 传 null。
        场景执行统一使用该步骤绑定的 ApiInfo 协议和请求体类型。
        body_config/sse_config 是场景级数据，必须匹配步骤绑定 ApiInfo 的 body_type/protocol_type；sse_config 暂时保留，后续会并入 body_config。
        protocol_type=mcp 时 body_config 表示 Tool Arguments；如需执行配置，放到 body_config.mcp_config，支持 expected_result、validate_input_schema、timeout_seconds。
        protocol_type=grpc 时 body_config 推荐标准包装 {source_type:"value", body:{...}}，也兼容直接请求 Message 简写；如需执行配置，放到 body_config.grpc_config，支持 target、expected_status、timeout_seconds、ignore_unknown_fields、include_default_values。expected_status 默认 OK，ANY 表示不按 gRPC status 自动失败。一期只支持 unary RPC。
        protocol_type=websocket 时 body_config 表示消息脚本，结构为 {connect,messages,close}；messages[].direction 支持 send/receive/sleep/ping，send.message_type 支持 json/text/binary，receive.until 支持 jsonpath/regex/contains/text。
        posterior_response 每项使用 {key, value}，value 是 JSONPath，不使用 json_path 字段；posterior_response_text 同样使用 {key, value}，value 是正则表达式。
        posterior_response/posterior_response_text/posterior_sql/posterior_sleep/posterior_func 属于场景响应后置，
        只在请求成功返回后、断言前执行；如果失败发生在数据工厂前置、front_sql、front_func 或请求阶段，场景后置不会执行。
        需要失败后也执行的清理逻辑，请放到 API case.posterior_sql 或数据工厂 cleanup，不要依赖场景后置兜底。
        如果 Case 已有已发布版本，必须先调用 preview_modify_published_api_case_impact 并传回 preview_token/confirm_text。
        """
        sql_error = _validate_api_case_sql_datasources(front_sql, posterior_sql)
        if sql_error:
            return fail(sql_error, "DATASOURCE_ALIAS_REQUIRED")
        step = ApiQuerySelector.api_case_detailed().get(id=step_id)
        confirm_error = _require_published_api_case_modify_confirmation(step.case_id, preview_token, confirm_text)
        if confirm_error:
            return confirm_error
        payload = {
            "case_detailed": step_id,
            "name": name,
            "error_retry": error_retry,
            "retry_interval": retry_interval,
            "allow_failure": allow_failure,
            "headers": headers or [],
            "params": _json_string(params),
            "body_config": body_config,
            "sse_config": sse_config,
            "front_sql": front_sql or [],
            "front_func": front_func,
            "ass_jsonpath": _normalize_ass_jsonpath(ass_jsonpath),
            "ass_general": ass_general or [],
            "ass_json_all": ass_json_all,
            "ass_text_all": ass_text_all,
            "ass_schema": ass_schema,
            "posterior_response": posterior_response or [],
            "posterior_response_text": posterior_response_text or [],
            "posterior_sql": posterior_sql or [],
            "posterior_sleep": posterior_sleep,
            "posterior_func": posterior_func,
        }
        payload = _normalize_scenario_payload(payload)
        data_obj = ApiCaseAggregateMutationService.mutate(
            step.case_id,
            action="create_parameter",
            operation=lambda _: ApiCaseParameterMutationService.create(
                mcp_with_update_user(payload),
                record_config=False,
                source="mcp",
            ),
            operator_id=mcp_current_user_id(),
            source="mcp",
        )
        return ok({"scenario_id": data_obj["id"], **data_obj}, "场景参数创建成功")

    @mcp.tool()
    def update_api_case_scenario(
            scenario_id: int,
            fields: dict,
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """更新场景参数。fields 使用 ApiCaseDetailedParameter 字段名。

        字段格式见 get_api_case_schema.api_case_scenario_fields。fields.headers 非空时会覆盖 API case 的 front_headers。
        前后置函数遵循 get_api_case_schema.execution_rules.function_usage：JSON/变量、提取、常规断言优先现有配置；仅不可表达的计算/解码才写函数，不改响应或吞错刷通过。改已有脚本须保留类型、动态值、测试意图及断言强度。
        fields.allow_failure=true 时，场景在全部重试后仍失败会标记为警告并继续执行后续步骤。
        fields.front_sql/fields.posterior_sql 每条 SQL 必须传 datasource_alias；可传 test_envs 多选执行环境，不传、null 或 [] 表示全部环境执行。
        SQL 的 key 支持单个缓存变量，也支持 id,name 这种英文逗号分隔多 key；查询结果取第一行，按列名优先、列顺序兜底写入多个缓存变量。
        先调用 list_data_factory_datasource_aliases 查询数据库。
        fields.ass_jsonpath 的规则同 create_api_case_scenario：单参数断言方法 expect 传 null。
        场景执行统一使用该步骤绑定的 ApiInfo 协议和请求体类型。
        fields.body_config/fields.sse_config 是场景级数据，必须匹配步骤绑定 ApiInfo 的 body_type/protocol_type；sse_config 暂时保留，后续会并入 body_config。
        protocol_type=mcp 时 body_config 表示 Tool Arguments；如需执行配置，放到 body_config.mcp_config，支持 expected_result、validate_input_schema、timeout_seconds。
        protocol_type=grpc 时 body_config 推荐标准包装 {source_type:"value", body:{...}}，也兼容直接请求 Message 简写；如需执行配置，放到 body_config.grpc_config，支持 target、expected_status、timeout_seconds、ignore_unknown_fields、include_default_values。expected_status 默认 OK，ANY 表示不按 gRPC status 自动失败。一期只支持 unary RPC。
        protocol_type=websocket 时 fields.body_config 表示消息脚本，结构为 {connect,messages,close}；messages[].direction 支持 send/receive/sleep/ping，send.message_type 支持 json/text/binary，receive.until 支持 jsonpath/regex/contains/text。
        fields.posterior_response 每项使用 {key, value}，value 是 JSONPath，不使用 json_path 字段；fields.posterior_response_text 的 value 是正则表达式。
        fields.posterior_* 属于场景响应后置，只在请求成功返回后、断言前执行；请求前或请求阶段失败时不会执行。
        失败后必须清理的数据请放到 API case.posterior_sql 或数据工厂 cleanup。
        如果 Case 已有已发布版本，必须先调用 preview_modify_published_api_case_impact 并传回 preview_token/confirm_text。
        """
        sql_error = _validate_api_case_sql_datasources(fields.get("front_sql"), fields.get("posterior_sql"))
        if sql_error:
            return fail(sql_error, "DATASOURCE_ALIAS_REQUIRED")
        payload = {"id": scenario_id, **fields}
        payload = _normalize_scenario_payload(payload)
        scenario = ApiQuerySelector.api_case_detailed_parameter().select_related("case_detailed").get(id=scenario_id)
        confirm_error = _require_published_api_case_modify_confirmation(
            scenario.case_detailed.case_id,
            preview_token,
            confirm_text,
        )
        if confirm_error:
            return confirm_error
        data_obj = ApiCaseAggregateMutationService.mutate(
            scenario.case_detailed.case_id,
            action="update_parameter",
            operation=lambda _: ApiCaseParameterMutationService.update(
                scenario_id,
                mcp_with_update_user(payload),
                record_config=False,
                source="mcp",
            ),
            operator_id=mcp_current_user_id(),
            source="mcp",
        )
        return ok({"scenario_id": data_obj["id"], **data_obj}, "场景参数更新成功")

    @mcp.tool()
    def generate_api_case_scenario_assertions(
            response_sample: dict | list | str,
            assertion_style: Literal["status_code", "jsonpath", "schema", "full"] = "jsonpath",
    ) -> dict:
        """根据响应样例生成场景断言草稿，不落库。"""
        sample: Any = response_sample
        if isinstance(response_sample, str):
            try:
                sample = jsonlib.loads(response_sample)
            except jsonlib.JSONDecodeError:
                sample = response_sample
        result: dict[str, Any] = {
            "ass_jsonpath": [],
            "ass_general": [],
            "ass_json_all": None,
            "ass_text_all": None,
            "ass_schema": None,
        }
        if assertion_style in ("jsonpath", "full") and isinstance(sample, (dict, list)):
            for path, value in _find_json_paths(sample):
                if isinstance(value, (str, int, float, bool)) or value is None:
                    if value is None:
                        method = "p_is_none"
                        expect = None
                    elif value is True:
                        method = "p_is_true"
                        expect = None
                    elif value is False:
                        method = "p_is_false"
                        expect = None
                    else:
                        method = "p_is_equal_to"
                        expect = str(value)
                    result["ass_jsonpath"].append(
                        {
                            "assertion_type": "jsonpath",
                            "actual": path,
                            "method": method,
                            "expect": expect,
                        }
                    )
        if assertion_style in ("schema", "full") and isinstance(sample, (dict, list)):
            builder = SchemaBuilder()
            builder.add_object(sample)
            result["ass_schema"] = builder.to_schema()
        if assertion_style == "full":
            if isinstance(sample, (dict, list)):
                result["ass_json_all"] = sample
            else:
                result["ass_text_all"] = str(sample)
        return ok(result)

    @mcp.tool()
    def generate_api_case_scenario_extractors(
            response_sample: dict | list | str,
            target_fields: list[str] | None = None,
    ) -> dict:
        """根据响应样例生成后置提取草稿，不落库。"""
        sample: Any = response_sample
        if isinstance(response_sample, str):
            try:
                sample = jsonlib.loads(response_sample)
            except jsonlib.JSONDecodeError:
                sample = response_sample
        posterior_response = []
        posterior_response_text = []
        targets = set(target_fields or ["token", "access_token", "id", "order_id", "user_id"])
        if isinstance(sample, (dict, list)):
            for path, value in _find_json_paths(sample, limit=50):
                key = path.split(".")[-1].replace("[0]", "")
                if key in targets:
                    posterior_response.append({"key": key, "value": path})
        else:
            for target in targets:
                posterior_response_text.append({"key": target, "value": f"{target}=([^&\\\\s]+)"})
        return ok(
            {
                "posterior_response": posterior_response,
                "posterior_response_text": posterior_response_text if not posterior_response else [],
            }
        )

    @mcp.tool()
    def auto_generate_api_case_scenario_schema(
            scenario_id: int,
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """根据场景最近一次响应 JSON 生成 schema 断言并保存。已发布 Case 必须先预览确认。"""
        parameter = ApiQuerySelector.api_case_detailed_parameter().select_related("case_detailed").get(id=scenario_id)
        confirm_error = _require_published_api_case_modify_confirmation(
            parameter.case_detailed.case_id,
            preview_token,
            confirm_text,
        )
        if confirm_error:
            return confirm_error
        result = ApiCaseScenarioSchemaService.generate(
            scenario_id,
            operator_id=mcp_current_user_id(),
            source="mcp",
        )
        return ok(result, "schema 断言生成成功")
