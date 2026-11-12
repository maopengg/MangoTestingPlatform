import json
from pydantic import ValidationError
from src.apps.system.schemas.evaluation_ai import EvaluationAiProfile
from src.apps.system.exceptions import SystemError, SYSTEM_EVALUATION_AI_CONFIG_INVALID
from src.apps.system.constants import EVALUATION_DEFAULT_AI_PROFILE_ID

EVALUATION_AI_PROFILES_KEY = "EVALUATION_AI_PROFILES"
SECRET_MASK = "__KEEP_SECRET__"


class EvaluationAiProfileService:
    @staticmethod
    def parse(value):
        try:
            rows = json.loads(value) if isinstance(value, str) else value
            if not isinstance(rows, list) or len(rows) > 50:
                raise SystemError(SYSTEM_EVALUATION_AI_CONFIG_INVALID)
            profiles = [EvaluationAiProfile.model_validate(row) for row in rows]
        except (ValueError, TypeError, ValidationError) as error:
            raise SystemError(SYSTEM_EVALUATION_AI_CONFIG_INVALID) from error
        ids = [profile.id for profile in profiles]
        if EVALUATION_DEFAULT_AI_PROFILE_ID in ids or len(ids) != len(set(ids)) or any(profile.enabled and not profile.api_key.get_secret_value().strip() for profile in profiles):
            raise SystemError(SYSTEM_EVALUATION_AI_CONFIG_INVALID)
        return profiles

    @classmethod
    def masked(cls, value):
        return [{**profile.model_dump(mode="json", exclude={"api_key"}),
                 "api_key": SECRET_MASK if profile.api_key.get_secret_value() else ""} for profile in cls.parse(value or [])]

    @classmethod
    def prepare_save(cls, value, previous):
        old = {profile.id: profile for profile in cls.parse(previous or [])}
        profiles = cls.parse(value)
        for profile in profiles:
            if profile.api_key.get_secret_value() == SECRET_MASK:
                if profile.id not in old:
                    raise SystemError(SYSTEM_EVALUATION_AI_CONFIG_INVALID)
                profile.api_key = old[profile.id].api_key
        return [{**profile.model_dump(mode="json", exclude={"api_key"}),
                 "api_key": profile.api_key.get_secret_value()} for profile in profiles]

    @classmethod
    def profiles(cls):
        from src.apps.system.services.configuration.system_config import SystemConfigService
        return cls.parse(SystemConfigService.get(EVALUATION_AI_PROFILES_KEY, default=[]) or [])

    @classmethod
    def options(cls):
        from src.apps.system.services.ai.client import AiService
        config = AiService.load_config()
        available = bool(config.model and config.base_url and config.api_key)
        default = {"id": EVALUATION_DEFAULT_AI_PROFILE_ID, "name": "系统默认 AI", "model": config.model, "enabled": available}
        if not available:
            default["disabled_reason"] = "未配置完整"
        return [default, *[profile.model_dump(mode="json", include={"id", "name", "model", "enabled"}) for profile in cls.profiles()]]

    @classmethod
    def resolve(cls, profile_id):
        from src.apps.system.services.ai.client import AiConfig, AiService
        if profile_id == EVALUATION_DEFAULT_AI_PROFILE_ID:
            config = AiService.load_config()
            try:
                profile = EvaluationAiProfile.model_validate({"id": profile_id, "name": "系统默认 AI",
                    "provider_type": config.provider_type, "base_url": config.base_url, "model": config.model,
                    "api_key": config.api_key, "timeout": config.timeout})
                if not profile.api_key.get_secret_value().strip():
                    raise SystemError(SYSTEM_EVALUATION_AI_CONFIG_INVALID)
            except (ValueError, TypeError, ValidationError) as error:
                raise SystemError(SYSTEM_EVALUATION_AI_CONFIG_INVALID) from error
            return profile, config
        profile = next((profile for profile in cls.profiles() if profile.id == profile_id and profile.enabled), None)
        if profile is None:
            raise SystemError(SYSTEM_EVALUATION_AI_CONFIG_INVALID)
        return profile, AiConfig(provider_type=profile.provider_type, api_key=profile.api_key.get_secret_value(),
            base_url=profile.base_url, model=profile.model, timeout=profile.timeout)
