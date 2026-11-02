# -*- coding: utf-8 -*-
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.functional_test.api.serializers.grid_view import FunctionalTestGridViewSerializer
from src.apps.functional_test.exceptions import (
    FUNCTIONAL_TEST_CONFIG_INVALID,
    FunctionalTestError,
)
from src.apps.functional_test.models import FunctionalTestGridView
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001, RESPONSE_MSG_0002, RESPONSE_MSG_0005, RESPONSE_MSG_0082


class FunctionalTestGridViewViews(ViewSet):
    allowed_grid_keys = frozenset()

    @staticmethod
    def _user_id(request: Request):
        return ModelCRUD.get_operator_id(request)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def list(self, request: Request):
        grid_key = self._validate_grid_key(request.query_params.get("grid_key"))
        queryset = FunctionalTestGridView.objects.filter(
            user_id=self._user_id(request), grid_key=grid_key
        )
        return ResponseData.success(RESPONSE_MSG_0001, FunctionalTestGridViewSerializer(queryset, many=True).data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def save(self, request: Request):
        user_id = self._user_id(request)
        grid_key = self._validate_grid_key(request.data.get("grid_key"))
        name = str(request.data.get("name") or "默认视图").strip()
        config = request.data.get("config") or {}
        self._validate_config(config)
        item, created = FunctionalTestGridView.objects.update_or_create(
            user_id=user_id,
            grid_key=grid_key,
            name=name,
            defaults={"config": config, "is_default": bool(request.data.get("is_default", True))},
        )
        if item.is_default:
            FunctionalTestGridView.objects.filter(user_id=user_id, grid_key=grid_key).exclude(id=item.id).update(
                is_default=False)
        return ResponseData.success(RESPONSE_MSG_0002 if created else RESPONSE_MSG_0082,
                                    FunctionalTestGridViewSerializer(item).data)

    @action(methods=["delete"], detail=False)
    @error_response("system")
    def delete(self, request: Request):
        count, _ = FunctionalTestGridView.objects.filter(
            id=request.data.get("id"), user_id=self._user_id(request), grid_key__in=self.allowed_grid_keys
        ).delete()
        return ResponseData.success(RESPONSE_MSG_0005, {"count": count})

    def _validate_grid_key(self, value):
        grid_key = str(value or "").strip()
        if grid_key not in self.allowed_grid_keys:
            raise FunctionalTestError(FUNCTIONAL_TEST_CONFIG_INVALID)
        return grid_key

    @staticmethod
    def _validate_config(config):
        columns = config.get("columns") if isinstance(config, dict) else None
        if not isinstance(columns, list) or len(columns) > 100:
            raise FunctionalTestError(FUNCTIONAL_TEST_CONFIG_INVALID)
        if "merge_same_cells" in config and not isinstance(config["merge_same_cells"], bool):
            raise FunctionalTestError(FUNCTIONAL_TEST_CONFIG_INVALID)
        allowed_fields = {
            "field",
            "title",
            "width",
            "minWidth",
            "fixed",
            "sortable",
            "editable",
            "editor",
            "visible",
            "options",
            "mergeable",
        }
        if any(
                not isinstance(column, dict)
                or not str(column.get("field") or "").strip()
                or not set(column).issubset(allowed_fields)
                for column in columns
        ):
            raise FunctionalTestError(FUNCTIONAL_TEST_CONFIG_INVALID)


class FunctionalCaseGridViewViews(FunctionalTestGridViewViews):
    allowed_grid_keys = frozenset({"functional-case-library"})
