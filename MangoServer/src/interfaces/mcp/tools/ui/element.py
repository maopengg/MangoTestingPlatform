from __future__ import annotations

from src.apps.auto_ui.services.elements.element_service import PageElementService
from src.interfaces.mcp.common import paginate_list
from .helpers import _ui_service_call
from .helpers import (
    current_user,
)


def register_element_tools(mcp):
    @mcp.tool()
    def search_ui_elements(
            page_id: int | None = None,
            keyword: str | None = None,
            category: str | None = None,
            ai_heal_status: int | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """搜索 UI 元素。支持按页面、元素分类、AI 自愈状态筛选。"""
        return _ui_service_call(PageElementService.search_elements, page_id, keyword, category, ai_heal_status, page,
                                page_size)

    @mcp.tool()
    def get_ui_element_detail(element_id: int) -> dict:
        """查询 UI 元素详情。"""
        return _ui_service_call(PageElementService.get_element_detail, element_id)

    @mcp.tool()
    def create_ui_element(
            page_id: int,
            name: str,
            category: str,
            exp: int | None = None,
            loc: str | None = None,
            exp2: int | None = None,
            loc2: str | None = None,
            exp3: int | None = None,
            loc3: str | None = None,
            sleep: int | None = None,
            sub: int | None = None,
            sub2: int | None = None,
            sub3: int | None = None,
            is_iframe: int | None = 0,
            prompt: str | None = None,
            location_description: str | None = None,
            surrounding_text: str | None = None,
            expected_event: dict | None = None,
    ) -> dict:
        """
        创建 UI 元素。

        规则：
        - category 为必填，用于页面元素分类，例如：搜索区域、表格、弹窗、登录表单。
        - exp/exp2/exp3 必须属于 ElementExpEnum。不传定位组时，prompt、location_description、surrounding_text 至少填写一项。
        - location_description 用于填写元素位置和周边文字等正向识别线索；surrounding_text 仅用于填写需要排除的同名或相似元素。
        - expected_event 为非必填的“预期事件/预期输入”模板；页面步骤工作台选择该元素时，会自动带入到步骤配置，用户仍可在步骤里修改。
        - expected_event 结构示例：
          {"ope_key":"w_input","ope_value":[{"f":"input_value","n":"输入内容","p":"请输入输入内容","d":true,"v":"${{username}}"}]}
        - 点击类元素可传：
          {"ope_key":"w_click","ope_value":[]}
        """
        user = current_user()
        result = _ui_service_call(
            PageElementService.create_element,
            page_id=page_id,
            name=name,
            category=category,
            user_id=user.id,
            exp=exp,
            loc=loc,
            exp2=exp2,
            loc2=loc2,
            exp3=exp3,
            loc3=loc3,
            sleep=sleep,
            sub=sub,
            sub2=sub2,
            sub3=sub3,
            is_iframe=is_iframe,
            prompt=prompt,
            location_description=location_description,
            surrounding_text=surrounding_text,
            expected_event=expected_event,
        )
        if result.get("success"):
            action = (result.get("data") or {}).get("action")
            result["message"] = "同名 UI 元素已更新" if action == "update" else "UI 元素创建成功"
        return result

    @mcp.tool()
    def update_ui_element(element_id: int, fields: dict) -> dict:
        """
        更新 UI 元素。

        fields 使用 PageElement 字段名；category 为空会被拒绝；exp/exp2/exp3 会校验枚举。
        location_description 填写元素位置和周边文字等正向识别线索；surrounding_text 仅填写排除项。
        如需维护“预期事件/预期输入”，在 fields.expected_event 中传：
        {"ope_key":"w_input","ope_value":[{"f":"input_value","n":"输入内容","p":"请输入输入内容","d":true,"v":"${{username}}"}]}
        该模板会在页面步骤工作台选择此元素时自动带入，用户仍可在步骤里重新定义。
        """
        user = current_user()
        result = _ui_service_call(PageElementService.update_element, element_id, fields, user.id)
        if result.get("success"):
            result["message"] = "UI 元素更新成功"
        return result

    @mcp.tool()
    def list_ui_element_categories(page_id: int, page: int = 1, page_size: int = 10) -> dict:
        """查询页面元素分类聚合，包含分类下元素数、待确认修复数、无基线数。"""
        result = _ui_service_call(PageElementService.list_element_categories, page_id)
        if not result.get("success"):
            return result
        items, count, page, page_size = paginate_list(result.get("data", {}).get("items") or [], page, page_size)
        result["data"] = {"items": items, "count": count, "page": page, "page_size": page_size}
        return result

    @mcp.tool()
    def get_ui_element_ai_info(element_id: int, test_env_id: int | None = None) -> dict:
        """查询元素 AI 基线快照、自愈记录和运行统计信息。"""
        return _ui_service_call(PageElementService.get_element_ai_info, element_id, test_env_id)

    @mcp.tool()
    def create_ui_element_snapshot(snapshot_data: dict) -> dict:
        """
        创建元素基线快照。snapshot_data 至少包含 element、test_env、exp、loc、url。
        可选字段包括 source/status/title/frame_url/sub/match_count/element_text/outer_html/parent_html/nearby_html 等。
        """
        result = _ui_service_call(PageElementService.create_element_snapshot, snapshot_data)
        if result.get("success"):
            result["message"] = "UI 元素基线快照保存成功"
        return result

    @mcp.tool()
    def create_ui_element_heal_record(heal_data: dict) -> dict:
        """
        创建元素 AI 自愈记录。heal_data 至少包含 element、test_env、page_url。
        candidates 建议为候选定位器数组，每项包含 exp、loc、sub、verified、confidence/final_score。
        """
        result = _ui_service_call(PageElementService.create_element_heal_record, heal_data)
        if result.get("success"):
            result["message"] = "UI 元素 AI 自愈记录保存成功"
        return result

    @mcp.tool()
    def update_ui_element_from_heal_record(record_id: int, candidate_index: int = 0, target_slot: int = 1) -> dict:
        """确认采用某条 AI 自愈记录的候选定位器，并写回元素定位槽位。target_slot 支持 1/2/3。"""
        user = current_user()
        result = _ui_service_call(PageElementService.apply_element_heal_record, record_id, candidate_index, target_slot,
                                  user.id)
        if result.get("success"):
            result["message"] = "UI 元素定位器已根据自愈记录更新"
        return result

    @mcp.tool()
    def update_ui_element_ai_records_page(source_page_id: int, target_page_id: int,
                                          element_ids: list[int] | None = None) -> dict:
        """将 UI 元素 AI 快照和自愈记录从旧页面迁移到新页面，用于页面合并后的安全清理。"""
        result = _ui_service_call(PageElementService.update_element_ai_records_page, source_page_id, target_page_id,
                                  element_ids)
        if result.get("success"):
            result["message"] = "UI 元素 AI 记录页面引用迁移成功"
        return result

    @mcp.tool()
    def set_ui_element_iframe(element_id: int, is_iframe: int) -> dict:
        """设置元素是否在 iframe 中。"""
        user = current_user()
        result = _ui_service_call(PageElementService.set_element_iframe, element_id, is_iframe, user.id)
        if result.get("success"):
            result["message"] = "iframe 状态更新成功"
        return result

    @mcp.tool()
    def test_ui_element(element_payload: dict, test_env_id: int | None = None, is_send: bool = True) -> dict:
        """测试一个 UI 元素定位。element_payload 使用页面 test_element 接口同等结构。"""
        user = current_user()
        payload = dict(element_payload or {})
        result = _ui_service_call(
            PageElementService.check_element,
            payload.get("element_id") or payload.get("id"),
            user.id,
            user.username,
            test_env_id if test_env_id is not None else payload.get("test_env"),
            payload.get("workspace_id"),
            payload.get("check_mode"),
            payload.get("runtime_variables"),
        )
        if result.get("success"):
            result["message"] = "元素测试已发送执行器"
        return result
