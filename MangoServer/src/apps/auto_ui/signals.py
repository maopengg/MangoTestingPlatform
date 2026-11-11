from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from src.apps.auto_ui.models import UiPublic
from src.common.utils.variable_tag_cache import VariableTagSummaryCache


@receiver([post_save, post_delete], sender=UiPublic, dispatch_uid='auto_ui.public_tags.invalidate')
def invalidate_public_tag_summary(sender, using, **kwargs):
    VariableTagSummaryCache.invalidate_after_commit(sender._meta.label_lower, using)
