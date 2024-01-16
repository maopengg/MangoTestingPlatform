# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-11-02 12:48
# @Author : 毛鹏
from rest_framework.response import Response


class ResponseData:

    @classmethod
    def success(cls,
                msg: str,
                data: None | str | list | dict = None,
                total_size=None,
                code=200,
                status=None,
                template_name=None,
                headers=None,
                exception=False,
                content_type=None) -> Response:
        data = {
            'code': code,
            'msg': msg,
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
             msg: str,
             data: None | str | list | dict = None,
             total_size=None,
             code=300,
             status=None,
             template_name=None,
             headers=None,
             exception=False,
             content_type=None) -> Response:
        data = {
            'code': code,
            'msg': msg,
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
