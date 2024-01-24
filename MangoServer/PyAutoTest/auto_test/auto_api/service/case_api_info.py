# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-12-20 10:44
# @Author : 毛鹏
import json

from pydantic import BaseModel

from PyAutoTest.auto_test.auto_api.models import ApiCaseDetailed, ApiCaseResult


class RequestDataModel(BaseModel):
    api_info_id: int
    method: int
    client: int
    name: str
    url: str
    header: str | None
    params: str | None
    data: str | None
    json_data: str | None
    file: str | None
    front_sql: list
    ass_sql: list
    ass_response_whole: str | None
    ass_response_value: list
    posterior_sql: list
    posterior_response: list
    dump_data: list
    response_code: str | None
    response_time: str | None
    response_headers: str | None
    response_text: str | None
    response_json: str | None
    status: int | None


class CaseApiInfo:

    def __init__(self, case_id, api_info_id=None):
        self.case_id = case_id
        self.api_info_id = api_info_id

    def main(self):
        if self.api_info_id:
            api_case_detailed = ApiCaseDetailed.objects.filter(case=self.case_id, api_info=self.api_info_id).order_by(
                'case_sort')
        else:
            api_case_detailed = ApiCaseDetailed.objects.filter(case=self.case_id).order_by('case_sort')
        data = []
        for i in api_case_detailed:
            api_result = ApiCaseResult.objects.raw(
                f'SELECT MAX(create_time) AS create_time,id, api_info_id,response_code,response_time,response_headers,response_text,response_json,`status` FROM `api_result` WHERE case_id = {self.case_id} AND api_info_id = {i.api_info.id} GROUP BY api_info_id;')
            data.append(RequestDataModel(
                api_info_id=i.api_info.id,
                method=i.api_info.method,
                client=i.api_info.client,
                name=i.api_info.name,
                url=i.url,
                header=i.header,
                params=json.dumps(i.params),
                data=json.dumps(i.data),
                json_data=json.dumps(i.json),
                file=i.file,
                front_sql=i.front_sql,
                ass_sql=i.ass_sql,
                ass_response_whole=i.ass_response_whole,
                ass_response_value=i.ass_response_value,
                posterior_sql=i.posterior_sql,
                posterior_response=i.posterior_response,
                dump_data=i.dump_data,
                response_code=api_result[0].response_code if api_result else None,
                response_time=api_result[0].response_time if api_result else None,
                response_headers=api_result[0].response_headers if api_result else None,
                response_text=api_result[0].response_text if api_result else None,
                response_json=api_result[0].response_json if api_result else None,
                status=api_result[0].status if api_result else None,
            ).dict())
        return data
