"""芒果测试平台统一提示词目录。"""
from src.common.prompts.base import render_template
from src.common.prompts.loader import get_prompt, validate_prompt_catalog
from src.common.schemas.prompt import PromptDefinition

__all__ = ["PromptDefinition", "get_prompt", "render_template", "validate_prompt_catalog"]
