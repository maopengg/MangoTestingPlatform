"""统一提示词目录的数据契约。"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PromptDefinition(BaseModel):
    """一份可版本化的静态提示词定义。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    description: str = Field(min_length=1)
    system: str = ""
    templates: dict[str, str] = Field(default_factory=dict)
    values: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id", "version", "owner", "description", "system", mode="before")
    @classmethod
    def normalize_text(cls, value: Any) -> str:
        return str(value or "").strip()

    def template(self, key: str) -> str:
        try:
            return self.templates[key]
        except KeyError as exc:
            raise KeyError(f"提示词 {self.id} 未定义模板：{key}") from exc

    def render(self, key: str, **variables: Any) -> str:
        from src.common.prompts.base import render_template

        return render_template(self.template(key), **variables)
