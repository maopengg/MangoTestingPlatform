from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.user.api.serializers.department import DepartmentSerializers, \
    DepartmentProjectProductPermissionSerializersC
from src.apps.user.models import Department, DepartmentProjectProductPermission
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0208, RESPONSE_MSG_0209


class DepartmentCRUD(ModelCRUD):
    model = Department
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializers
    serializer = DepartmentSerializers


class DepartmentViews(ViewSet):

    @action(methods=['get'], detail=False)
    @error_response('user')
    def get_product_scope(self, request: Request):
        """获取部门项目产品授权范围"""
        department_id = request.query_params.get('department_id')
        queryset = DepartmentProjectProductPermission.objects.filter(department_id=department_id)
        serializer = DepartmentProjectProductPermissionSerializersC.setup_eager_loading(queryset)
        data = DepartmentProjectProductPermissionSerializersC(instance=serializer, many=True).data
        return ResponseData.success(RESPONSE_MSG_0208, data)

    @action(methods=['put'], detail=False)
    @error_response('user')
    def put_product_scope(self, request: Request):
        """保存部门项目产品授权范围"""
        department_id = request.data.get('department_id')
        project_product_ids = request.data.get('project_product_ids') or []
        DepartmentProjectProductPermission.objects.filter(department_id=department_id).delete()
        update_user_id = request.user.get('id') if isinstance(request.user, dict) else None
        DepartmentProjectProductPermission.objects.bulk_create([
            DepartmentProjectProductPermission(
                department_id=department_id,
                project_product_id=project_product_id,
                update_user_id=update_user_id,
            )
            for project_product_id in project_product_ids
        ])
        return ResponseData.success(RESPONSE_MSG_0209)
