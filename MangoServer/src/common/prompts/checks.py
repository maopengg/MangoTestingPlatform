"""Django 启动检查：提示词目录必须完整且可解析。"""

from django.core.checks import Error, register

from src.common.prompts.loader import validate_prompt_catalog


@register()
def check_prompt_catalog(app_configs, **kwargs):
    try:
        validate_prompt_catalog()
    except Exception as exc:
        return [
            Error(
                f"提示词目录校验失败：{exc}",
                id="prompts.E001",
            )
        ]
    return []
