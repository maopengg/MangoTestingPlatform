# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-07-23 14:10
# @Author : 毛鹏
import json
import traceback


def get(self, **kwargs, ):
    query_dict = {}
    for k, v in dict(kwargs.get('request').query_params.lists()).items():
        if k and isinstance(v[0], str) and k not in self.not_matching_str and 'id' not in k:
            query_dict[f'{k}__contains'] = v[0]
        else:
            query_dict[k] = v[0]
    #
    project_id = kwargs.get('request').headers.get('Project', None)
    if project_id and hasattr(self.model, 'project_product'):
        project_product = kwargs.get('project_product').objects.filter(project_id=project_id)
        if self.model.__name__ in self.pytest_model:
            from src.auto_test.auto_pytest.models import PytestProduct
            product = PytestProduct.objects.filter(
                project_product_id__in=project_product.values_list('id', flat=True))
            query_dict['project_product_id__in'] = product.values_list('id', flat=True)
        else:
            query_dict['project_product_id__in'] = project_product.values_list('id', flat=True)
    try:
        if kwargs.get('request').query_params.get("pageSize") and kwargs.get('request').query_params.get("page"):
            del query_dict['pageSize'], query_dict['page']
            try:
                self.model._meta.get_field('case_sort')
                books = self.model.objects.filter(**query_dict).order_by('case_sort')
            except kwargs.get('field_does_note_xist'):
                books = self.model.objects.filter(**query_dict)
            data_list, count = self.paging_list(kwargs.get('request').query_params.get("pageSize"),
                                                kwargs.get('request').query_params.get("page"),
                                                books,
                                                self.get_serializer_class())
            return kwargs.get('response_data').success(kwargs.get('m_001'), data_list, count)
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
            return kwargs.get('response_data').success(kwargs.get('m_0001'),
                                                       serializer(instance=books, many=True).data,
                                                       books.count())
    except kwargs.get('s3_error') as error:
        kwargs.get('log').system.error(f'GET请求发送异常，请排查问题：{error}, error:{traceback.print_exc()}')
        return kwargs.get('response_data').fail(kwargs.get('m_0026'), )
    except Exception as error:
        kwargs.get('log').system.error(f'GET请求发送异常，请排查问题：{error}, error:{traceback.print_exc()}')
        return kwargs.get('response_data').fail(kwargs.get('m_0027'), )


def post(self, **kwargs):
    serializer = self.serializer(data=kwargs.get('request').data)
    if serializer.is_valid():
        serializer.save()
        self.asynchronous_callback(kwargs.get('request').data.get('parent_id'))
        return kwargs.get('response_data').success(kwargs.get('m_0002'), serializer.data)
    else:
        kwargs.get('log').system.error(
            f'执行保存时报错，请检查！数据：{kwargs.get("request").data}, 报错信息：{json.dumps(serializer.errors)}')
        return kwargs.get('response_data').fail(kwargs.get('m_0003'), serializer.errors)


def put(self, **kwargs):
    if isinstance(kwargs.get("request"), dict):
        data = kwargs.get("request")
        serializer = self.serializer(
            instance=self.model.objects.get(pk=kwargs.get("request").get('id')),
            data=data,
            partial=True
        )
    else:
        data = kwargs.get("request").data
        serializer = self.serializer(
            instance=self.model.objects.get(pk=kwargs.get("request").data.get('id')),
            data=data,
            partial=True
        )
    if serializer.is_valid():
        serializer.save()
        self.asynchronous_callback(kwargs.get("request").data.get('parent_id'))
        return kwargs.get('response_data').success(kwargs.get('m_0082'), serializer.data)
    else:
        kwargs.get('log').system.error(f'执行修改时报错，请检查！数据：{data}, 报错信息：{str(serializer.errors)}')
        return kwargs.get('response_data').fail(kwargs.get('m_0004'), serializer.errors)


def delete(self, **kwargs):
    _id = kwargs.get('request').query_params.get('id')
    id_list = [int(id_str) for id_str in kwargs.get('request').query_params.getlist('id[]')]
    try:
        if not _id and id_list:
            for i in id_list:
                self.model.objects.get(pk=i).delete()
        else:
            self.model.objects.get(id=_id).delete()
            self.asynchronous_callback(kwargs.get('request').query_params.get('parent_id'))
    except kwargs.get('tools_error') as error:
        return kwargs.get('response_data').fail((error.code, error.msg))
    except self.model.DoesNotExist:
        return kwargs.get('response_data').fail(kwargs.get('m_0029'))
    else:
        return kwargs.get('response_data').success(kwargs.get('m_0005'))


def paging_list(cls, size: int, current: int, books: QuerySet, serializer) -> tuple[list, int]:

    count = books.count()
    if count <= int(size):
        current = 1
    try:
        return serializer(
            instance=Paginator(serializer.setup_eager_loading(books), size).page(current),
            many=True).data, count
    except FieldError:
        return serializer(
            instance=Paginator(books, size).page(current),
            many=True).data, count


def inside_post(cls, data: dict) -> dict:
    serializer = cls.serializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return serializer.data
    else:
        log.system.error(f'执行内部保存时报错，请检查！数据：{data}, 报错信息：{json.dumps(serializer.errors)}')
        raise ToolsError(*RESPONSE_MSG_0116, value=(serializer.errors,))


def inside_put(cls, _id: int, data: dict) -> dict:
    serializer = cls.serializer(instance=cls.model.objects.get(pk=_id), data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return serializer.data
    else:
        log.system.error(f'执行内部修改时报错，请检查！id:{_id}, 数据：{data}, 报错信息：{str(serializer.errors)}')
        raise ToolsError(*RESPONSE_MSG_0117, value=(serializer.errors,))


def inside_delete(cls, _id: int) -> None:
    """
    删除一条记录
    @param _id:
    @return:
    """
    cls.model.objects.get(id=_id).delete()
