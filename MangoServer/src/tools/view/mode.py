# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-07-23 14:10
# @Author : 毛鹏
import traceback


def get(self, request, project_product, log, **kwargs,):
    query_dict = {}
    for k, v in dict(request.query_params.lists()).items():
        if k and isinstance(v[0], str) and k not in self.not_matching_str and 'id' not in k:
            query_dict[f'{k}__contains'] = v[0]
        else:
            query_dict[k] = v[0]
    #
    project_id = request.headers.get('Project', None)
    if project_id and hasattr(self.model, 'project_product'):
        project_product = project_product.objects.filter(project_id=project_id)
        if self.model.__name__ in self.pytest_model:
            from src.auto_test.auto_pytest.models import PytestProduct
            product = PytestProduct.objects.filter(
                project_product_id__in=project_product.values_list('id', flat=True))
            query_dict['project_product_id__in'] = product.values_list('id', flat=True)
        else:
            query_dict['project_product_id__in'] = project_product.values_list('id', flat=True)
    try:
        if request.query_params.get("pageSize") and request.query_params.get("page"):
            del query_dict['pageSize'], query_dict['page']
            try:
                self.model._meta.get_field('case_sort')
                books = self.model.objects.filter(**query_dict).order_by('case_sort')
            except kwargs.get('field_does_note_xist'):
                books = self.model.objects.filter(**query_dict)
            data_list, count = self.paging_list(request.query_params.get("pageSize"),
                                                request.query_params.get("page"),
                                                books,
                                                self.get_serializer_class())
            return kwargs.get('response_data').success(kwargs.get('001'), data_list, count)
        else:
            try:
                self.model._meta.get_field('case_sort')
                books = self.model.objects.filter(**query_dict).order_by('case_sort')
            except kwargs.get('field_does_note_xist'):
                books = self.model.objects.filter(**query_dict)
            serializer = self.get_serializer_class()
            try:
                books = serializer.setup_eager_loading(books)
            except kwargs.get('field_error'):
                pass
            return kwargs.get('response_data').success(kwargs.get('001'),
                                        serializer(instance=books, many=True).data,
                                        books.count())
    except kwargs.get('s3_error') as error:
        log.system.error(f'GET请求发送异常，请排查问题：{error}, error:{traceback.print_exc()}')
        return kwargs.get('response_data').fail(kwargs.get('026'), )
    except Exception as error:
        log.system.error(f'GET请求发送异常，请排查问题：{error}, error:{traceback.print_exc()}')
        return kwargs.get('response_data').fail(kwargs.get('027'), )