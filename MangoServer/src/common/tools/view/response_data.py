# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-11-02 12:48
# @Author : 毛鹏
from rest_framework.response import Response


class ResponseData:

    @classmethod
    def success(cls,
                msg: tuple,
                data: None | str | list | dict = None,
                total_size=None,
                status=None,
                template_name=None,
                headers=None,
                exception=False,
                content_type=None,
                value: tuple | None = None) -> Response:
        data = {
            'code': msg[0],
            'msg': msg[1].format(*value) if value else msg[1],
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
             msg: tuple,
             data: None | str | list | dict = None,
             total_size=None,
             status=None,
             template_name=None,
             headers=None,
             exception=False,
             content_type=None,
             value: tuple | None = None,
             renderer_context=None) -> Response:
        data = {
            'code': msg[0],
            'msg': msg[1].format(*value) if value else msg[1],
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
