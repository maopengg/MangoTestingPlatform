"""YAML 提示词加载、缓存和启动前校验。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from ruamel.yaml import YAML

from src.common.prompts.registry import PROMPT_FILES
from src.common.schemas.prompt import PromptDefinition

CATALOG_DIR = Path(__file__).resolve().parent / "catalog"


@lru_cache(maxsize=None)
def get_prompt(prompt_id: str) -> PromptDefinition:
    try:
        file_name = PROMPT_FILES[prompt_id]
    except KeyError as exc:
        raise KeyError(f"提示词未注册：{prompt_id}") from exc

    path = CATALOG_DIR / file_name
    yaml = YAML(typ="safe")
    with path.open("r", encoding="utf-8") as stream:
        raw = yaml.load(stream) or {}
    prompt = PromptDefinition.model_validate(raw)
    if prompt.id != prompt_id:
        raise ValueError(f"提示词文件 {file_name} 的 id={prompt.id}，与注册 id={prompt_id} 不一致")
    return prompt


def validate_prompt_catalog() -> tuple[PromptDefinition, ...]:
    prompts = tuple(get_prompt(prompt_id) for prompt_id in PROMPT_FILES)
    file_names = list(PROMPT_FILES.values())
    if len(file_names) != len(set(file_names)):
        raise ValueError("提示词注册表存在重复文件")
    catalog_files = {path.name for path in CATALOG_DIR.glob("*.yaml")}
    unregistered = sorted(catalog_files - set(file_names))
    missing = sorted(set(file_names) - catalog_files)
    if unregistered or missing:
        raise ValueError(f"提示词文件注册不完整：未注册={unregistered}，缺失={missing}")
    return prompts
