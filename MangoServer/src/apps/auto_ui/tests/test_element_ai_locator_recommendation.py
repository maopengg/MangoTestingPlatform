import json
from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from src.apps.auto_ui.exceptions import AutoUiError
from src.apps.auto_ui.services.element_ai import ElementAiLocatorRecommendationService


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "element-ai-locator-recommendation-tests",
        }
    }
)
class ElementAiLocatorRecommendationServiceTest(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @staticmethod
    def _response(*candidates, reason=""):
        return {
            "choices": [{
                "message": {
                    "content": {"candidates": list(candidates), "reason": reason},
                }
            }]
        }

    @patch("src.apps.auto_ui.services.element_ai.locator_recommendation.AgentModelGateway.json_chat")
    def test_generates_safe_first_batch_and_caches_snapshot(self, json_chat):
        json_chat.return_value = self._response(
            {
                "strategy": "role",
                "role": "button",
                "value": "提交",
                "exact": True,
                "reason": "角色和名称稳定",
                "confidence": 92,
            },
            {
                "strategy": "css",
                "value": "button[data-testid=submit]",
                "reason": "测试属性稳定",
                "confidence": 88,
            },
            {
                "strategy": "javascript",
                "value": "document.body",
                "reason": "不支持的策略",
                "confidence": 100,
            },
        )

        result = ElementAiLocatorRecommendationService.recommend(
            {
                "context": {
                    "tag": "button",
                    "role": "button",
                    "accessible_name": "提交",
                    "baseline_snapshot": {
                        "outer_html": '<button data-testid="submit">提交</button>',
                        "parent_html": '<form><button data-testid="submit">提交</button></form>',
                    },
                },
                "existing_locators": [],
            },
            user_id=7,
        )

        self.assertTrue(result["snapshot_id"])
        self.assertEqual(result["batch"], 1)
        self.assertEqual(len(result["candidates"]), 2)
        self.assertEqual(result["candidates"][0]["exp"], 2)
        self.assertEqual(
            result["candidates"][0]["loc"],
            'get_by_role("button", name="提交", exact=True)',
        )
        self.assertEqual(result["candidates"][1]["exp"], 9)

    @patch("src.apps.auto_ui.services.element_ai.locator_recommendation.AgentModelGateway.json_chat")
    def test_returns_up_to_five_candidates_for_browser_validation(self, json_chat):
        json_chat.return_value = self._response(*[
            {
                "strategy": "text",
                "value": f"候选 {index}",
                "exact": True,
                "confidence": 90 - index,
            }
            for index in range(6)
        ])

        result = ElementAiLocatorRecommendationService.recommend(
            {"context": {"tag": "button", "text": "提交"}},
            user_id=8,
        )

        self.assertEqual(len(result["candidates"]), 5)
        self.assertEqual(result["diagnostics"]["available_count"], 5)

    @patch("src.apps.auto_ui.services.element_ai.locator_recommendation.AgentModelGateway.json_chat")
    def test_refresh_batch_reuses_snapshot_and_filters_previous_locator(self, json_chat):
        first = {
            "strategy": "text",
            "value": "保存",
            "exact": True,
            "reason": "文本明确",
            "confidence": 80,
        }
        second = {
            "strategy": "role",
            "role": "button",
            "value": "保存",
            "exact": True,
            "reason": "角色更稳定",
            "confidence": 90,
        }
        json_chat.side_effect = [self._response(first), self._response(first, second)]
        initial = ElementAiLocatorRecommendationService.recommend(
            {"context": {"tag": "button", "text": "保存"}},
            user_id=9,
        )
        refreshed = ElementAiLocatorRecommendationService.recommend(
            {"snapshot_id": initial["snapshot_id"]},
            user_id=9,
        )

        self.assertEqual(refreshed["batch"], 2)
        self.assertEqual(len(refreshed["candidates"]), 1)
        self.assertEqual(refreshed["candidates"][0]["strategy"], "role")

    @patch("src.apps.auto_ui.services.element_ai.locator_recommendation.AgentModelGateway.json_chat")
    def test_refresh_batch_uses_sanitized_user_guidance(self, json_chat):
        json_chat.side_effect = [
            self._response(reason="缺少上下文"),
            self._response({
                "strategy": "role",
                "role": "button",
                "value": "删除",
                "exact": True,
                "reason": "结合删除确认弹窗定位",
                "confidence": 95,
            }),
        ]
        initial = ElementAiLocatorRecommendationService.recommend(
            {"context": {"tag": "button", "text": "删除"}},
            user_id=20,
        )

        result = ElementAiLocatorRecommendationService.recommend(
            {
                "snapshot_id": initial["snapshot_id"],
                "location_description": "  删除确认弹窗内，附近有删除后无法恢复  ",
                "surrounding_text": " 列表操作列中的删除按钮 ",
            },
            user_id=20,
        )

        prompt = json.loads(json_chat.call_args.kwargs["messages"][1]["content"])
        self.assertEqual(
            prompt["user_guidance"],
            {
                "location_description": "删除确认弹窗内，附近有删除后无法恢复",
                "surrounding_text": "列表操作列中的删除按钮",
            },
        )
        self.assertIn("surrounding_text 是排除条件", "\n".join(prompt["rules"]))
        self.assertEqual(len(result["candidates"]), 1)

    @patch("src.apps.auto_ui.services.element_ai.locator_recommendation.AgentModelGateway.json_chat")
    def test_refresh_without_guidance_fields_preserves_previous_guidance(self, json_chat):
        json_chat.side_effect = [
            self._response(reason="需要更多上下文"),
            self._response(reason="仍需要更多上下文"),
        ]
        initial = ElementAiLocatorRecommendationService.recommend(
            {
                "context": {"tag": "button", "text": "删除"},
                "location_description": "删除确认弹窗内",
            },
            user_id=21,
        )

        ElementAiLocatorRecommendationService.recommend(
            {"snapshot_id": initial["snapshot_id"]},
            user_id=21,
        )

        prompt = json.loads(json_chat.call_args.kwargs["messages"][1]["content"])
        self.assertEqual(
            prompt["user_guidance"]["location_description"],
            "删除确认弹窗内",
        )

    def test_sanitizes_and_limits_user_guidance(self):
        guidance = ElementAiLocatorRecommendationService._sanitize_user_guidance({
            "location_description": "  " + "位" * 1200 + "  ",
            "surrounding_text": "  " + "文" * 600 + "  ",
        })

        self.assertLessEqual(len(guidance["location_description"]), 1000)
        self.assertLessEqual(len(guidance["surrounding_text"]), 500)
        self.assertNotIn(" ", guidance["location_description"])

    def test_refresh_rejects_expired_or_foreign_snapshot(self):
        with self.assertRaises(AutoUiError):
            ElementAiLocatorRecommendationService.recommend(
                {"snapshot_id": "missing"},
                user_id=1,
            )

    @patch("src.apps.auto_ui.services.element_ai.locator_recommendation.AgentModelGateway.json_chat")
    def test_accepts_common_model_field_aliases(self, json_chat):
        json_chat.return_value = {
            "choices": [{
                "message": {
                    "content": {
                        "data": {
                            "locators": [{
                                "type": "get_by_role",
                                "role": "button",
                                "name": "提交",
                                "confidence": 91,
                            }]
                        }
                    }
                }
            }]
        }

        result = ElementAiLocatorRecommendationService.recommend(
            {"context": {"tag": "button", "accessible_name": "提交"}},
            user_id=10,
        )

        self.assertEqual(len(result["candidates"]), 1)
        self.assertEqual(result["candidates"][0]["strategy"], "role")
        self.assertEqual(result["diagnostics"]["invalid_count"], 0)

    @patch("src.apps.auto_ui.services.element_ai.locator_recommendation.AgentModelGateway.json_chat")
    def test_accepts_safe_direct_playwright_expression(self, json_chat):
        json_chat.return_value = self._response({
            "locator": 'page.get_by_text("提交", exact=True)',
            "reason": "按钮文字稳定",
        })

        result = ElementAiLocatorRecommendationService.recommend(
            {"context": {"tag": "button", "text": "提交"}},
            user_id=11,
        )

        self.assertEqual(len(result["candidates"]), 1)
        self.assertEqual(result["candidates"][0]["loc"], 'get_by_text("提交", exact=True)')

    @patch("src.apps.auto_ui.services.element_ai.locator_recommendation.AgentModelGateway.json_chat")
    def test_reports_when_all_candidates_are_duplicates(self, json_chat):
        json_chat.return_value = self._response({
            "strategy": "text",
            "value": "保存",
            "exact": True,
        })

        result = ElementAiLocatorRecommendationService.recommend(
            {
                "context": {"tag": "button", "text": "保存"},
                "existing_locators": [{
                    "exp": 2,
                    "loc": 'get_by_text("保存", exact=True)',
                }],
            },
            user_id=12,
        )

        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["diagnostics"]["duplicate_count"], 1)
        self.assertIn("重复", result["diagnostics"]["message"])

    @patch("src.apps.auto_ui.services.element_ai.locator_recommendation.AgentModelGateway.json_chat")
    def test_reports_ai_reason_when_model_cannot_generate_candidates(self, json_chat):
        json_chat.return_value = self._response(
            reason="目标只有普通 div 标签，缺少文本、角色和稳定属性，无法可靠区分"
        )

        result = ElementAiLocatorRecommendationService.recommend(
            {"context": {"tag": "div"}},
            user_id=13,
        )

        self.assertEqual(result["candidates"], [])
        self.assertIn("缺少文本", result["diagnostics"]["message"])
        self.assertEqual(
            result["diagnostics"]["ai_reason"],
            "目标只有普通 div 标签，缺少文本、角色和稳定属性，无法可靠区分",
        )

    @patch("src.apps.auto_ui.services.element_ai.locator_recommendation.AgentModelGateway.json_chat")
    def test_reports_empty_model_content_instead_of_unknown_reason(self, json_chat):
        json_chat.return_value = {
            "choices": [{"message": {"content": {}}}],
        }

        result = ElementAiLocatorRecommendationService.recommend(
            {"context": {"tag": "button", "text": "删除"}},
            user_id=14,
        )

        self.assertEqual(result["candidates"], [])
        self.assertEqual(
            result["diagnostics"]["message"],
            "AI 服务返回内容为空，未生成定位器候选（已自动重试 1 次，仍未获得定位器候选）",
        )
        self.assertEqual(result["diagnostics"]["model_attempts"], 2)
        self.assertEqual(json_chat.call_count, 2)

    @patch("src.apps.auto_ui.services.element_ai.locator_recommendation.AgentModelGateway.json_chat")
    def test_retries_empty_response_and_uses_second_response(self, json_chat):
        json_chat.side_effect = [
            {"choices": [{"finish_reason": "stop", "message": {"content": ""}}]},
            self._response({
                "strategy": "text",
                "value": "删除",
                "exact": True,
                "reason": "第二次请求返回有效结果",
                "confidence": 90,
            }),
        ]

        result = ElementAiLocatorRecommendationService.recommend(
            {"context": {"tag": "button", "text": "删除"}},
            user_id=17,
        )

        self.assertEqual(len(result["candidates"]), 1)
        self.assertEqual(result["diagnostics"]["model_attempts"], 2)
        self.assertEqual(json_chat.call_count, 2)
        self.assertEqual(json_chat.call_args.kwargs["max_tokens"], 5000)
        self.assertEqual(
            json_chat.call_args.kwargs["thinking"],
            {"type": "disabled"},
        )

    @patch("src.apps.auto_ui.services.element_ai.locator_recommendation.AgentModelGateway.json_chat")
    def test_reports_reasoning_only_response_without_logging_content(self, json_chat):
        json_chat.return_value = {
            "choices": [{
                "finish_reason": "stop",
                "message": {
                    "content": "",
                    "reasoning_content": "内部推理内容不应进入诊断文案",
                },
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
        }

        result = ElementAiLocatorRecommendationService.recommend(
            {"context": {"tag": "button", "text": "删除"}},
            user_id=18,
        )

        self.assertIn("仅返回了推理内容", result["diagnostics"]["message"])
        self.assertNotIn("内部推理内容", result["diagnostics"]["message"])

    @patch("src.apps.auto_ui.services.element_ai.locator_recommendation.AgentModelGateway.json_chat")
    def test_reports_reasoning_token_exhaustion_as_truncated_output(self, json_chat):
        json_chat.return_value = {
            "choices": [{
                "finish_reason": "length",
                "message": {
                    "content": "",
                    "reasoning_content": "内部推理内容",
                },
            }],
        }

        result = ElementAiLocatorRecommendationService.recommend(
            {"context": {"tag": "button", "text": "删除"}},
            user_id=19,
        )

        self.assertIn("最终 JSON 被截断", result["diagnostics"]["message"])

    @patch("src.apps.auto_ui.services.element_ai.locator_recommendation.AgentModelGateway.json_chat")
    def test_reports_empty_candidate_list_without_model_reason(self, json_chat):
        json_chat.return_value = self._response()

        result = ElementAiLocatorRecommendationService.recommend(
            {"context": {"tag": "button", "text": "删除"}},
            user_id=15,
        )

        self.assertEqual(result["candidates"], [])
        self.assertEqual(
            result["diagnostics"]["message"],
            "AI 明确返回了空候选列表，但未按约定说明无法生成的原因（已自动重试 1 次，仍未获得定位器候选）",
        )

    @patch("src.apps.auto_ui.services.element_ai.locator_recommendation.AgentModelGateway.json_chat")
    def test_reports_missing_candidate_contract_fields(self, json_chat):
        json_chat.return_value = {
            "choices": [{"message": {"content": {"summary": "无法判断"}}}],
        }

        result = ElementAiLocatorRecommendationService.recommend(
            {"context": {"tag": "button", "text": "删除"}},
            user_id=16,
        )

        self.assertEqual(result["candidates"], [])
        self.assertEqual(
            result["diagnostics"]["message"],
            "AI 返回内容缺少 candidates 和 reason 字段，无法提取定位器候选（已自动重试 1 次，仍未获得定位器候选）",
        )
