# -*- coding: utf-8 -*-
from src.apps.functional_test.services.common import ManualTestValidationService


class FunctionalCaseNormalizer:
    @staticmethod
    def normalize(payload: dict) -> dict:
        return ManualTestValidationService.normalize_suite_cases(payload)
