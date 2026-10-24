from __future__ import annotations

import uuid

from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.utils import timezone

from src.apps.auto_ui.enums import ElementExpEnum
from src.apps.auto_ui.exceptions import (
    AUTO_UI_ELEMENT_SERVICE_ELEMENT_NAME_REQUIRED,
    AUTO_UI_ELEMENT_SERVICE_ELEMENT_LOCATOR_EXPRESSION_MINIMUM_REQUIRED,
    AUTO_UI_ELEMENT_SERVICE_INVALID,
    AUTO_UI_ELEMENT_SERVICE_ELEMENT_REQUIRED,
    AUTO_UI_ELEMENT_SERVICE_ELEMENT_DELETE_NOT_FOUND,
    AUTO_UI_ELEMENT_SERVICE_NOT_FOUND,
    AUTO_UI_ELEMENT_SERVICE_ELEMENT_EXECUTION_ACCESS_DENIED,
    AUTO_UI_ELEMENT_SERVICE_TEST_ENVIRONMENT_USER_INVALID,
    AUTO_UI_ELEMENT_SERVICE_INVALID_CODE_INVALID,
    AUTO_UI_ELEMENT_SERVICE_ELEMENT_REQUIRED_CODE_ELEMENT_REQUIRED,
    AUTO_UI_ELEMENT_SERVICE_FIELD_REQUIRED,
    AutoUiError,
    UI_ELEMENT_PAGE_DELETE_NOT_FOUND,
    UI_ELEMENT_PAGE_ELEMENT_INVALID,
    UI_ELEMENT_PAGE_ELEMENT_ACCESS_DENIED,
    UI_LIVE_NOT_FOUND,
)
from src.apps.auto_ui.models import Page, PageElement, UiElementHealRecord, UiElementSnapshot
from src.apps.auto_ui.services.element_ai import ElementAiService
from src.apps.auto_ui.services.element_ai.data_sanitizer import ElementAiDataSanitizer
from src.apps.auto_ui.services.persistence import UiPersistenceService
from src.apps.auto_ui.services.test_case.test_case import TestCase
from src.apps.system.enums import ClientNameEnum
from src.apps.user.formatters import format_user_simple
from src.apps.user.models import User
from src.common.database import ModelMutationValidationError, save_model
from src.common.database import model_payload
from src.common.exceptions import SAVE_VALIDATION_FAILED


class PageElementService:
    """UI 页面元素业务能力，供 HTTP 和 MCP 共用。"""

    @classmethod
    def resolve_element_identity(
            cls,
            page_id: int,
            name: str,
            category: str,
            current_id: int | None = None,
    ) -> dict:
        normalized_name = str(name or "").strip()
        normalized_category = str(category or "").strip()
        if not normalized_name or not normalized_category:
            raise AutoUiError(AUTO_UI_ELEMENT_SERVICE_ELEMENT_NAME_REQUIRED)
        queryset = PageElement.objects.filter(
            page_id=page_id,
            name=normalized_name,
            category=normalized_category,
        )
        match_count = queryset.count()
        element = None
        if current_id:
            element = queryset.filter(id=current_id).first()
        if element is None:
            element = queryset.order_by("-id").first()
        return {
            "exists": element is not None,
            "action": "update" if element is not None else "create",
            "match_count": match_count,
            "element": (
                {
                    "id": element.id,
                    "page_id": element.page_id,
                    "name": element.name,
                    "category": element.category,
                    "is_current": bool(current_id and element.id == current_id),
                }
                if element is not None else None
            ),
        }

    @classmethod
    @transaction.atomic
    def upsert_element(cls, payload: dict, *, user_id: int | None = None) -> tuple[PageElement, bool]:
        data = dict(payload)
        page = data.get("page")
        page_id = getattr(page, "id", page)
        name = str(data.get("name") or "").strip()
        category = str(data.get("category") or "").strip()
        Page.objects.select_for_update().get(id=page_id)
        existing = PageElement.objects.filter(
            page_id=page_id,
            name=name,
            category=category,
        ).order_by("-id").first()
        data.update({"page": page_id, "name": name, "category": category, "update_user": user_id})
        try:
            saved = save_model(
                PageElement,
                data,
                instance=existing,
                partial=existing is not None,
            )
        except ModelMutationValidationError as error:
            raise AutoUiError(SAVE_VALIDATION_FAILED, value=(error.errors,)) from error
        return saved, existing is None

    @classmethod
    def search_elements(
            cls,
            page_id: int | None = None,
            keyword: str | None = None,
            category: str | None = None,
            ai_heal_status: int | None = None,
            page: int = 1,
            page_size: int = 20,
    ) -> dict:
        queryset = PageElement.objects.select_related("page", "update_user").all()
        if page_id is not None:
            queryset = queryset.filter(page_id=page_id)
        if category:
            queryset = queryset.filter(category=category)
        if ai_heal_status is not None:
            queryset = queryset.filter(ai_heal_status=ai_heal_status)
        if keyword:
            queryset = queryset.filter(
                Q(name__contains=keyword)
                | Q(loc__contains=keyword)
                | Q(category__contains=keyword)
                | Q(location_description__contains=keyword)
                | Q(surrounding_text__contains=keyword)
            )
        return UiPersistenceService.paginate_with_presenter(
            queryset.order_by("-id"),
            page,
            page_size,
            cls._present_element,
        )

    @classmethod
    def get_element_detail(cls, element_id: int) -> dict:
        return model_to_dict(PageElement.objects.get(id=element_id))

    @classmethod
    def create_element(
            cls,
            page_id: int,
            name: str,
            category: str,
            user_id: int,
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
        cls._validate_element_category(category)
        has_locator = any(str(value or '').strip() for value in (loc, loc2, loc3))
        has_description = any(
            str(value or '').strip()
            for value in (prompt, location_description, surrounding_text)
        )
        if not has_locator and not has_description:
            raise AutoUiError(AUTO_UI_ELEMENT_SERVICE_ELEMENT_LOCATOR_EXPRESSION_MINIMUM_REQUIRED)
        cls._validate_element_exp(exp, "exp")
        cls._validate_element_exp(exp2, "exp2")
        cls._validate_element_exp(exp3, "exp3")
        payload = {
            "page": page_id,
            "name": name,
            "category": category.strip(),
            "exp": exp,
            "loc": loc,
            "exp2": exp2,
            "loc2": loc2,
            "exp3": exp3,
            "loc3": loc3,
            "sleep": sleep,
            "sub": sub,
            "sub2": sub2,
            "sub3": sub3,
            "is_iframe": is_iframe,
            "prompt": prompt,
            "location_description": location_description,
            "surrounding_text": surrounding_text,
            "expected_event": expected_event or {},
            "update_user": user_id,
        }
        normalized_name = str(name or '').strip()
        normalized_category = str(category or '').strip()
        payload['name'] = normalized_name
        payload['category'] = normalized_category
        # 所有“新增元素”入口遵循同一身份规则：同页面、名称、分类重复即编辑。
        # 锁 Page 可串行化并发创建，数据库唯一约束负责最终兜底。
        with transaction.atomic():
            Page.objects.select_for_update().get(id=page_id)
            existing = PageElement.objects.filter(
                page_id=page_id,
                name=normalized_name,
                category=normalized_category,
            ).order_by('-id').first()
            if existing:
                data = UiPersistenceService.update_model(
                    existing,
                    cls._normalize_element_payload(existing, payload),
                    cls._present_element,
                )
                action = 'update'
            else:
                data = UiPersistenceService.create_model(
                    PageElement,
                    cls._normalize_element_payload(None, payload),
                    cls._present_element,
                )
                action = 'create'
        return {"element_id": data["id"], "action": action, **data}

    @classmethod
    def update_element(cls, element_id: int, fields: dict, user_id: int) -> dict:
        data = dict(fields or {})
        if "category" in data:
            cls._validate_element_category(data.get("category"))
            data["category"] = str(data["category"]).strip()
        for field in ["exp", "exp2", "exp3"]:
            if field in data:
                cls._validate_element_exp(data.get(field), field)
        instance = PageElement.objects.get(id=element_id)
        data = UiPersistenceService.update_model(
            instance,
            cls._normalize_element_payload(
                instance,
                {"id": element_id, **data, "update_user": user_id},
            ),
            cls._present_element,
        )
        return {"element_id": data["id"], **data}

    @staticmethod
    def set_iframe(element_id: int, is_iframe: int | None, user_id: int | None) -> PageElement:
        element = PageElement.objects.get(id=element_id)
        element.is_iframe = is_iframe
        element.update_user_id = user_id
        element.save(update_fields=["is_iframe", "update_user", "update_time"])
        return element

    @classmethod
    def list_element_categories(cls, page_id: int) -> dict:
        return {"items": ElementAiService.category_list(page_id)}

    @classmethod
    def get_element_ai_info(cls, element_id: int, test_env_id: int | None = None) -> dict:
        return ElementAiService.ai_info(element_id, test_env_id)

    @classmethod
    def create_element_snapshot(cls, snapshot_data: dict) -> dict:
        cls._validate_required_fields(snapshot_data, ["element", "test_env", "exp", "loc", "url"], "创建元素基线快照")
        return ElementAiService.save_snapshot(snapshot_data)

    @classmethod
    def create_element_heal_record(cls, heal_data: dict) -> dict:
        cls._validate_required_fields(heal_data, ["element", "test_env", "page_url"], "创建元素 AI 自愈记录")
        return ElementAiService.save_heal_record(heal_data)

    @classmethod
    def apply_element_heal_record(cls, record_id: int, candidate_index: int, target_slot: int, user_id: int) -> dict:
        return ElementAiService.apply_heal_record(record_id, candidate_index, target_slot, user_id)

    @classmethod
    def update_element_ai_records_page(
            cls,
            source_page_id: int,
            target_page_id: int,
            element_ids: list[int] | None = None,
    ) -> dict:
        source_page = Page.objects.get(id=source_page_id)
        target_page = Page.objects.select_related("project_product").get(id=target_page_id)
        snapshot_queryset = UiElementSnapshot.objects.filter(page=source_page)
        heal_queryset = UiElementHealRecord.objects.filter(page=source_page)
        if element_ids:
            snapshot_queryset = snapshot_queryset.filter(element_id__in=element_ids)
            heal_queryset = heal_queryset.filter(element_id__in=element_ids)
        snapshot_count = snapshot_queryset.update(page=target_page, project_product=target_page.project_product)
        heal_count = heal_queryset.update(page=target_page, project_product=target_page.project_product)
        return {
            "source_page_id": source_page_id,
            "target_page_id": target_page_id,
            "element_ids": element_ids or [],
            "snapshot_count": snapshot_count,
            "heal_record_count": heal_count,
        }

    @classmethod
    def set_element_iframe(cls, element_id: int, is_iframe: int, user_id: int) -> dict:
        if is_iframe not in [0, 1]:
            raise AutoUiError(AUTO_UI_ELEMENT_SERVICE_INVALID)
        PageElement.objects.filter(id=element_id).update(
            is_iframe=is_iframe,
            update_user_id=user_id,
            update_time=timezone.now(),
        )
        return {"element_id": element_id, "is_iframe": is_iframe}

    @classmethod
    def check_element(cls, element_id: int, user_id: int, username: str,
                      test_env_id: int | None = None, workspace_id: str | None = None,
                      check_mode: str | None = None,
                      runtime_variables: dict | None = None) -> dict:
        if not element_id:
            raise AutoUiError(AUTO_UI_ELEMENT_SERVICE_ELEMENT_REQUIRED)
        if not PageElement.objects.filter(id=element_id).exists():
            raise AutoUiError(AUTO_UI_ELEMENT_SERVICE_ELEMENT_DELETE_NOT_FOUND)
        env_id = cls._selected_env(user_id, test_env_id)
        check_id = str(uuid.uuid4())
        normalized_check_mode = 'deep' if check_mode == 'deep' else 'normal'
        actuator_username = cls._workspace_actuator_username(workspace_id, username)
        test_case = TestCase(
            user_id,
            username,
            env_id,
            is_send=True,
            actuator_username=actuator_username,
        )
        check_args = (element_id, check_id, workspace_id, normalized_check_mode)
        if normalized_check_mode == 'deep' and runtime_variables:
            test_case.check_element(*check_args, runtime_variables=runtime_variables)
        else:
            test_case.check_element(*check_args)
        task = test_case.last_executor_task
        return {
            "client": ClientNameEnum.DRIVER.value,
            "check_id": check_id,
            "workspace_id": workspace_id,
            "actuator_username": actuator_username or username,
            "check_mode": normalized_check_mode,
            "task_id": task.id if task else None,
            "task_status": task.status if task else None,
        }

    @classmethod
    def scan_page_elements(
            cls,
            page_id: int,
            user_id: int,
            username: str,
            workspace_id: str,
            scan_mode: str,
    ) -> dict:
        from src.apps.auto_ui.services.live_stream.workspace_service import LiveWorkspaceService
        from src.apps.system.enums import ExecutorModeEnum
        from src.apps.system.enums import ServerUiCommandEnum
        from src.apps.system.enums import ClientTypeEnum
        from mangotools.contracts import SocketCommandContract, SocketEnvelopeContract
        from src.apps.system.services.socket_link.message_service import SocketMessageService

        if not Page.objects.filter(id=page_id).exists():
            raise AutoUiError(UI_ELEMENT_PAGE_DELETE_NOT_FOUND)
        if scan_mode not in {"quick", "deep", "region"}:
            raise AutoUiError(UI_ELEMENT_PAGE_ELEMENT_INVALID)
        workspace = LiveWorkspaceService.get_workspace(str(workspace_id or ""))
        if workspace is None:
            raise AutoUiError(UI_LIVE_NOT_FOUND)
        if workspace.username != username or int(workspace.user_id or 0) != int(user_id):
            raise AutoUiError(UI_ELEMENT_PAGE_ELEMENT_ACCESS_DENIED)

        task = SocketMessageService.send_socket_data(
            SocketEnvelopeContract(
                code=200,
                msg="页面元素扫描任务已创建",
                user=workspace.executor_username,
                is_notice=ClientTypeEnum.ACTUATOR,
                data=SocketCommandContract(
                    func_name=ServerUiCommandEnum.PAGE_SCAN.value,
                    func_args={
                        "page_id": int(page_id),
                        "workspace_id": workspace.workspace_id,
                        "workspace_type": workspace.workspace_type,
                        "mode": scan_mode,
                        "send_user": username,
                    },
                ),
            ),
            executor_mode=ExecutorModeEnum.WORKSPACE.value,
            ttl_seconds=0,
            execution_timeout_seconds=5 * 60,
        )
        return {
            "task_id": task.id,
            "task_status": task.status,
            "workspace_id": workspace.workspace_id,
            "scan_mode": scan_mode,
        }

    @classmethod
    def _workspace_actuator_username(cls, workspace_id: str | None, username: str) -> str | None:
        if not workspace_id:
            return None
        from src.apps.auto_ui.services.live_stream.workspace_service import LiveWorkspaceService

        workspace = LiveWorkspaceService.get_workspace(str(workspace_id))
        if workspace is None:
            raise AutoUiError(AUTO_UI_ELEMENT_SERVICE_NOT_FOUND)
        if workspace.username != username:
            raise AutoUiError(AUTO_UI_ELEMENT_SERVICE_ELEMENT_EXECUTION_ACCESS_DENIED)
        return workspace.executor_username

    @classmethod
    def _selected_env(cls, user_id: int, test_env_id: int | None) -> int:
        if test_env_id is not None:
            return test_env_id
        user = User.objects.get(id=user_id)
        from src.apps.user.services.user_cache import UserCacheService

        selected_environment = UserCacheService.selected_environment(user)
        if selected_environment is None:
            raise AutoUiError(AUTO_UI_ELEMENT_SERVICE_TEST_ENVIRONMENT_USER_INVALID)
        return selected_environment

    @classmethod
    def _validate_element_exp(cls, value: int | None, name: str):
        if value is not None and value not in ElementExpEnum.get_key_list():
            raise AutoUiError(AUTO_UI_ELEMENT_SERVICE_INVALID_CODE_INVALID, value=(name,))

    @classmethod
    def _validate_element_category(cls, category: str | None):
        if not str(category or "").strip():
            raise AutoUiError(AUTO_UI_ELEMENT_SERVICE_ELEMENT_REQUIRED_CODE_ELEMENT_REQUIRED)

    @classmethod
    def _validate_required_fields(cls, data: dict, fields: list[str], action_name: str):
        missing = [field for field in fields if data.get(field) in [None, ""]]
        if missing:
            raise AutoUiError(AUTO_UI_ELEMENT_SERVICE_FIELD_REQUIRED, value=(action_name, ', '.join(missing)))

    @staticmethod
    def _present_element(instance: PageElement) -> dict:
        data = model_payload(instance)
        data["page"] = model_payload(instance.page) if instance.page_id else None
        data["update_user"] = format_user_simple(instance.update_user) if instance.update_user_id else None
        data["latest_runtime_snapshot"] = ElementAiDataSanitizer.runtime_snapshot(
            data.get("latest_runtime_snapshot") or {}
        )
        return data

    @staticmethod
    def _normalize_element_payload(instance: PageElement | None, payload: dict) -> dict:
        attrs = dict(payload)
        for suffix in ("", "2", "3"):
            loc_key = f"loc{suffix}"
            if loc_key in attrs and not str(attrs.get(loc_key) or "").strip():
                attrs[loc_key] = None
                attrs[f"exp{suffix}"] = None
                attrs[f"sub{suffix}"] = None
        descriptions = [
            attrs.get(field, getattr(instance, field, None))
            for field in ("location_description", "surrounding_text", "prompt")
        ]
        locators = [
            attrs.get(f"loc{suffix}", getattr(instance, f"loc{suffix}", None))
            for suffix in ("", "2", "3")
        ]
        if not any(str(value or "").strip() for value in locators + descriptions):
            raise AutoUiError(AUTO_UI_ELEMENT_SERVICE_ELEMENT_LOCATOR_EXPRESSION_MINIMUM_REQUIRED)
        for field in ("prompt", "location_description", "surrounding_text"):
            if field in attrs and not str(attrs.get(field) or "").strip():
                attrs[field] = None
        if "frame_path" in attrs:
            frame_path = attrs.get("frame_path")
            if isinstance(frame_path, list):
                frame_path = {"schema_version": 1, "frames": frame_path}
            if not isinstance(frame_path, dict) or not isinstance(frame_path.get("frames", []), list):
                raise AutoUiError(AUTO_UI_ELEMENT_SERVICE_INVALID)
            attrs["frame_path"] = {"schema_version": 1, "frames": frame_path.get("frames") or []}
        expected_event = attrs.get("expected_event")
        if "expected_event" in attrs:
            if not isinstance(expected_event, dict) or not expected_event.get("ope_key"):
                attrs["expected_event"] = {}
            else:
                attrs["expected_event"] = {
                    "ope_key": expected_event["ope_key"],
                    "ope_value": expected_event.get("ope_value") if isinstance(expected_event.get("ope_value"),
                                                                               list) else [],
                }
        if instance is not None:
            version_fields = {
                "name", "category", "prompt", "location_description", "surrounding_text",
                "exp", "loc", "sub", "exp2", "loc2", "sub2", "exp3", "loc3", "sub3", "frame_path",
            }
            if any(field in attrs and getattr(instance, field, None) != attrs[field] for field in version_fields):
                attrs["locator_version"] = int(instance.locator_version or 0) + 1
        return attrs
