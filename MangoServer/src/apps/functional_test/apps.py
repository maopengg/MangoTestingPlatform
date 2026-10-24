# -*- coding: utf-8 -*-
from django.apps import AppConfig


class FunctionalTestConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "src.apps.functional_test"
    verbose_name = "研发协同"
