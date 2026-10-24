# -*- coding: utf-8 -*-
import hashlib

from django.db.models import Max

from src.apps.ai.models import AiSkillVersion


class SkillVersionService:
    @staticmethod
    def resolve(skill, user_id=None):
        if not skill:
            return None
        content_hash = hashlib.sha256((skill.content or "").encode("utf-8")).hexdigest()
        existing = AiSkillVersion.objects.filter(skill=skill, content_hash=content_hash).order_by("-version").first()
        if existing:
            return existing
        version = (AiSkillVersion.objects.filter(skill=skill).aggregate(value=Max("version"))["value"] or 0) + 1
        return AiSkillVersion.objects.create(
            skill=skill,
            version=version,
            content=skill.content or "",
            content_hash=content_hash,
            create_user_id=user_id,
        )
