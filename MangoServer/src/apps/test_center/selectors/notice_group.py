from src.apps.test_center.models import NoticeGroup, ProjectProduct
from src.apps.user.services.permission import ProjectProductScopeService


class NoticeGroupOptionSelector:
    @staticmethod
    def options(user, project_product_id):
        try:
            product_id = int(project_product_id)
        except (TypeError, ValueError):
            return []
        if user is None or not ProjectProductScopeService.has_project_product(user, product_id):
            return []
        project_id = ProjectProduct.objects.filter(id=product_id).values_list('project_id', flat=True).first()
        if project_id is None:
            return []
        return list(NoticeGroup.objects.filter(project_id=project_id).values('id', 'name'))
