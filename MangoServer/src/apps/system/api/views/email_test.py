from rest_framework.viewsets import ViewSet

from src.apps.system.api.serializers.email_test import EmailTestSerializer
from src.apps.system.services.configuration.email_test import EmailConfigTestService
from src.apps.user.exceptions import UserError
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0163


class EmailTestViews(ViewSet):

    @error_response('system')
    def test(self, request):
        """测试邮箱配置"""
        serializer = EmailTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            EmailConfigTestService.send(serializer.validated_data['recipient'])
        except UserError:
            return ResponseData.success(RESPONSE_MSG_0163, {
                'status': False,
                'message': '测试邮件发送失败，请检查邮箱发送人、SMTP 域名和授权密钥。',
            })
        return ResponseData.success(RESPONSE_MSG_0163, {
            'status': True,
            'message': '测试邮件已提交邮件服务器，请检查收件箱或垃圾邮件。',
        })
