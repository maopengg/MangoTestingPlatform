from django.db.models import Q

from src.apps.task_center.models import ScheduledTaskGroup, Tasks


class TaskEfficiencyOptionsSelector:
    @staticmethod
    def options(*, product_ids, product_id=None, kind='tasks', keyword='', page=1, page_size=50):
        model = Tasks if kind == 'tasks' else ScheduledTaskGroup
        queryset = model.objects.all().order_by('-id')
        if product_ids is not None:
            queryset = queryset.filter(project_product_id__in=product_ids)
        if product_id:
            queryset = queryset.filter(project_product_id=product_id)
        if keyword:
            match = Q(name__icontains=keyword)
            if keyword.isdigit():
                match |= Q(id=int(keyword))
            queryset = queryset.filter(match)
        offset = (page - 1) * page_size
        rows = list(queryset.values('id', 'name')[offset:offset + page_size + 1])
        return {'items': rows[:page_size], 'has_more': len(rows) > page_size, 'page': page, 'page_size': page_size}
