from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from src.apps.test_center.models import ProductModule, Project, ProjectProduct
from src.apps.test_center.services.project.product_module_cache import ProductModuleCacheService
from src.apps.test_center.services.project.project_product_cache import ProjectProductCacheService


@receiver(pre_save, sender=ProductModule)
def capture_product_module_cache_scope(sender, instance, **kwargs):
    if not instance.pk:
        instance._cache_old_project_product_id = None
        return
    instance._cache_old_project_product_id = (
        sender.objects.filter(pk=instance.pk)
        .values_list('project_product_id', flat=True)
        .first()
    )


@receiver(post_save, sender=ProductModule)
def invalidate_product_module_cache_after_save(sender, instance, **kwargs):
    project_product_ids = {
        getattr(instance, '_cache_old_project_product_id', None),
        instance.project_product_id,
    }
    transaction.on_commit(
        lambda: ProductModuleCacheService.invalidate_many(project_product_ids)
    )


@receiver(post_delete, sender=ProductModule)
def invalidate_product_module_cache_after_delete(sender, instance, **kwargs):
    project_product_id = instance.project_product_id
    transaction.on_commit(
        lambda: ProductModuleCacheService.invalidate(project_product_id)
    )


@receiver(pre_save, sender=ProjectProduct)
def capture_project_product_cache_scope(sender, instance, **kwargs):
    if not instance.pk:
        instance._cache_old_project_id = None
        return
    instance._cache_old_project_id = (
        sender.objects.filter(pk=instance.pk)
        .values_list('project_id', flat=True)
        .first()
    )


@receiver(post_save, sender=ProjectProduct)
def invalidate_product_cache_after_product_save(sender, instance, **kwargs):
    project_product_id = instance.id
    project_ids = (
        getattr(instance, '_cache_old_project_id', None),
        instance.project_id,
    )

    def clear_cache():
        ProductModuleCacheService.invalidate(project_product_id)
        ProjectProductCacheService.invalidate_many(project_ids)

    transaction.on_commit(clear_cache)


@receiver(post_delete, sender=ProjectProduct)
def invalidate_product_cache_after_product_delete(sender, instance, **kwargs):
    project_product_id = instance.id
    project_id = instance.project_id

    def clear_cache():
        ProductModuleCacheService.invalidate(project_product_id)
        ProjectProductCacheService.invalidate(project_id)

    transaction.on_commit(clear_cache)


@receiver([post_save, post_delete], sender=Project)
def invalidate_project_product_cache_after_project_change(sender, instance, **kwargs):
    project_id = instance.id
    transaction.on_commit(
        lambda: ProjectProductCacheService.invalidate(project_id)
    )
