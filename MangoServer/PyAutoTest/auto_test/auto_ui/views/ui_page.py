# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-01-15 10:56
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.models import UiPage, UiElement
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD, ModelC


class UiPageSerializers(serializers.ModelSerializer):
    class Meta:
        model = UiPage
        fields = '__all__'


class UiPageCRUD(ModelCRUD):
    model = UiPage
    queryset = UiPage.objects.all()
    serializer_class = UiPageSerializers


class UiPageC(ModelC):
    model = UiPage
    serializer_class = UiPageSerializers


class UiPageViews(ViewSet):

    @action(methods=['get'], detail=False)
    def get_page_name1(self, request):
        """
        获取所有的页面名称和元素
        @param request:
        @return:
        """
        data = []
        results = UiPage.objects.values_list('id', 'name')
        for result in results:
            page = {'label': result[1], 'value': result[0], 'children': []}
            for i in UiElement.objects.filter(page=result[0]):
                page['children'].append({'label': i.name, 'value': i.id})
            data.append(page)
        return Response({
            'code': 200,
            'msg': '获取数据成功~',
            'data': data
        })

    @action(methods=['GET'], detail=False)
    def get_page_name(self, request):
        data = []
        res = UiPage.objects.values_list('id', 'name')
        for _id, name in res:
            data.append({'value': _id, 'label': name})
        return Response({
            'code': 200,
            'msg': '获取数据成功~',
            'data': data
        })

"""

django orm 如何返回的时候，返回子model对象

header-icon
在 Django ORM 中，要返回子模型对象可以使用 select_related 方法。该方法用于在查询中包含关联的对象，以避免多次查询数据库。
例如：

python
Copy code
from myapp.models import ParentModel
parent = ParentModel.objects.select_related('childmodel').get(id=1)
child = parent.childmodel

在上面的代码中，我们使用 select_related 方法包含了关联的子模型对象。然后我们可以通过访问 parent 对象的 childmodel 属性来获取子模型对象。

header-icon
需要返回给前端json格式数据

header-icon
在 Django ORM 中，可以使用 Django 的序列化器来将查询结果转换成 JSON 格式的数据。Django 内置了多个序列化器，其中最常用的是 JSON 序列化器。
首先，需要在视图函数中进行查询，并使用序列化器将查询结果转换成 JSON 格式的数据。例如，在视图函数中查询 ParentModel 和 ChildModel，并将查询结果转换成 JSON 格式的数据：

python
Copy code
from django.core import serializers
from django.http import JsonResponse
from myapp.models import ParentModel
def my_view(request):
    parents = ParentModel.objects.select_related('childmodel').all()
    data = serializers.serialize('json', parents)
    return JsonResponse(data, safe=False)

在上面的代码中，我们使用 select_related 方法包含了关联的子模型对象。然后我们通过 serializers.serialize 方法将查询结果转换成 JSON 格式的数据，并使用 JsonResponse 返回给前端。
注意：JsonResponse 的第二个参数是 safe，如果返回的数据是列表或字典类型，需要将 safe 设置为False。

header-icon
使用的是rest_framework呢？需要怎么修改

header-icon
如果你使用的是 Django REST framework（DRF），你可以使用 DRF 的序列化器和视图类来将查询结果转换成 JSON 格式的数据并返回给前端。
首先，你可以创建一个序列化器类，用于将模型对象序列化成 JSON 格式的数据。例如，在序列化器中定义一个 ParentModelSerializer：

python
Copy code
from rest_framework import serializers
from myapp.models import ParentModel, ChildModel
class ChildModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChildModel
        fields = '__all__'
class ParentModelSerializer(serializers.ModelSerializer):
    childmodel = ChildModelSerializer(read_only=True)
    class Meta:
        model = ParentModel
        fields = '__all__'

在上面的代码中，我们定义了 ParentModelSerializer 和 ChildModelSerializer 两个序列化器类。ParentModelSerializer 中的 childmodel 字段使用了 ChildModelSerializer，用于序列化 ChildModel 对象。
然后，你可以创建一个视图类，用于查询数据库并将查询结果序列化成 JSON 格式的数据。例如，在视图类中查询 ParentModel 和 ChildModel，并将查询结果序列化成 JSON 格式的数据：

python
Copy code
from rest_framework import generics
from myapp.models import ParentModel
from .serializers import ParentModelSerializer
class ParentModelList(generics.ListAPIView):
    queryset = ParentModel.objects.select_related('childmodel').all()
    serializer_class = ParentModelSerializer

在上面的代码中，我们使用 generics.ListAPIView 创建了一个视图类 ParentModelList，并指定了 queryset 和 serializer_class 属性。其中，queryset 属性用于查询 ParentModel 和关联的 ChildModel，serializer_class 属性用于将查询结果序列化成 JSON 格式的数据。
最后，在 urls.py 中将视图类映射到 URL：

python
Copy code
from django.urls import path
from .views import ParentModelList
urlpatterns = [
    path('parent-models/', ParentModelList.as_view()),
]

现在你可以通过访问 /parent-models/ URL 来获取查询结果的 JSON 格式数据。

header-icon
可以给出一个返回例子吗？

header-icon
当我们使用 DRF 的序列化器和视图类查询数据库并将查询结果序列化成 JSON 格式的数据后，返回给前端的数据格式如下所示：

json
Copy code
[
    {
        "id": 1,
        "parent_field_1": "parent_value_1",
        "parent_field_2": "parent_value_2",
        "childmodel": {
            "id": 1,
            "child_field_1": "child_value_1",
            "child_field_2": "child_value_2"
        }
    },
    {
        "id": 2,
        "parent_field_1": "parent_value_3",
        "parent_field_2": "parent_value_4",
        "childmodel": {
            "id": 2,
            "child_field_1": "child_value_3",
            "child_field_2": "child_value_4"
        }
    }
]

在上面的 JSON 格式数据中，每个对象代表一个 ParentModel 对象，包含了 ParentModel 的所有字段和关联的 ChildModel 对象的字段。ChildModel 对象的字段位于 parent 对象的 childmodel 字段中。
"""