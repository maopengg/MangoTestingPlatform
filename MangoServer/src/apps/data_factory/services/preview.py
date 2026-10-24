# -*- coding: utf-8 -*-

from src.apps.data_factory.services.runner import DataFactoryRunner


class DataFactoryPreviewService:
    """数据工厂预览统一入口，HTTP 与 MCP 只负责协议参数转换。"""

    @staticmethod
    def preview_template(
            template_id: int,
            overrides: dict | None = None,
            output_config: list | None = None,
            post_insert_updates: list | None = None,
            context: dict | None = None,
            test_object_id: int | None = None,
            test_env: int | None = None,
            activation_validation: bool = False,
    ) -> dict:
        return DataFactoryRunner.preview_template(
            template_id=template_id,
            overrides=overrides or {},
            output_config=output_config,
            post_insert_updates=post_insert_updates,
            context=context or {},
            test_object_id=test_object_id,
            test_env=test_env,
            activation_validation=activation_validation,
        )
