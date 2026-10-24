# -*- coding: utf-8 -*-
from django.apps import AppConfig


class AiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "src.apps.ai"
    label = "auto_ai"

    def ready(self):
        from src.common.prompts import checks  # noqa: F401
