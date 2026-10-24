# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-11-02 12:48
# @Author : 毛鹏
from rest_framework.response import Response

from src.common.exceptions.definitions import ErrorDefinition


class ResponseData:

    @staticmethod
    def _message_parts(msg: tuple | ErrorDefinition) -> tuple[int, str]:
        if isinstance(msg, ErrorDefinition):
            return msg.code, msg.message
        return msg[0], msg[1]

    @classmethod
    def success(cls,
                msg: tuple | ErrorDefinition,
                data: None | str | list | dict = None,
                total_size=None,
                status=None,
                template_name=None,
                headers=None,
                exception=False,
                content_type=None,
                value: tuple | None = None) -> Response:
        code, message = cls._message_parts(msg)
        data = {
            'code': code,
            'msg': message.format(*value) if value else message,
            'data': data
        }

        if total_size:
            data['totalSize'] = total_size
        return Response(
            data=data,
            status=status,
            template_name=template_name,
            headers=headers,
            exception=exception,
            content_type=content_type
        )

    @classmethod
    def fail(cls,
             msg: tuple | ErrorDefinition,
             data: None | str | list | dict = None,
             total_size=None,
             status=None,
             template_name=None,
             headers=None,
             exception=False,
             content_type=None,
             value: tuple | None = None,
             renderer_context=None) -> Response:
        code, message = cls._message_parts(msg)
        data = {
            'code': code,
            'msg': message.format(*value) if value else message,
            'data': data
        }
        if total_size:
            data['totalSize'] = total_size
        response = Response(
            data=data,
            status=status,
            template_name=template_name,
            headers=headers,
            exception=exception,
            content_type=content_type
        )

        if renderer_context:
            response.renderer_context = renderer_context

        return response
