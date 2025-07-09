# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-28 17:58
# @Author : 毛鹏
import json

from mangotools.enums import NoticeEnum
from mangotools.exceptions import MangoToolsError
from mangotools.models import TestReportModel, WeChatNoticeModel, EmailNoticeModel
from mangotools.notice import EmailSend, WeChatSend

from src.auto_test.auto_system.models import NoticeConfig, CacheData, TestSuiteDetails, TestSuite, TestObject
from src.auto_test.auto_user.models import User
from src.enums.system_enum import CacheDataKeyEnum
from src.enums.tools_enum import StatusEnum, EnvironmentEnum, TestCaseTypeEnum
from src.exceptions import *
from src.tools.log_collector import log


class NoticeMain:

    @classmethod
    def notice_main(cls, test_env: int, project_product: int, test_suite_id: int):
        test_object = TestObject.objects.get(environment=test_env, project_product=project_product)
        notice_obj = NoticeConfig.objects.filter(test_object=test_object.id, status=StatusEnum.SUCCESS.value)
        test_report = cls.test_report(test_suite_id)
        for i in notice_obj:
            try:
                if i.type == NoticeEnum.MAIL.value:
                    cls.__wend_mail_send(i, test_report)
                elif i.type == NoticeEnum.WECOM.value:
                    cls.__we_chat_send(i, test_report)
                else:
                    log.system.error('暂不支持钉钉打卡')
            except MangoToolsError as error:
                raise ToolsError(error.code, error.msg)

    @classmethod
    def test_notice_send(cls, _id):
        notice_obj = NoticeConfig.objects.get(id=_id)
        test_report = TestReportModel(**{
            "test_suite_id": 197899881973,
            "project_id": 1,
            "project_name": "演示DEMO",
            "test_environment": "生产环境",
            "case_sum": 6,
            "api_case_sum": 1,
            "api_fail": 0,
            "api_call": 1,
            "ui_case_sum": 2,
            "ui_fail": 0,
            "ui_step_call": 7,
            "pytest_case_sum": 3,
            "pytest_fail": 0,
            "pytest_func_call": 3,
            "success": 6,
            "success_rate": 100.0,
            "warning": 0,
            "fail": 0,
            "execution_duration": "03:40:36",
            "test_time": "2025-07-05 06:26:47"
        })
        if notice_obj.type == NoticeEnum.MAIL.value:
            cls.__wend_mail_send(notice_obj, test_report)
        elif notice_obj.type == NoticeEnum.WECOM.value:
            cls.__we_chat_send(notice_obj, test_report)
        else:
            log.system.error('暂不支持钉钉打卡')

    @classmethod
    def __we_chat_send(cls, i, test_report: TestReportModel | None = None):
        try:
            wechat = WeChatSend(WeChatNoticeModel(webhook=i.config), test_report, cls.get_domain_name())
            wechat.send_wechat_notification()
        except ToolsError as error:
            raise MangoServerError(error.code, error.msg)

    @classmethod
    def __wend_mail_send(cls, i, test_report: TestReportModel | None = None):
        try:
            user_info = User.objects.filter(name__in=json.loads(i.config))
        except json.decoder.JSONDecodeError:
            raise SystemEError(*ERROR_MSG_0012)
        else:
            send_list = []
            for i in user_info:
                try:
                    send_list += i.mailbox
                except TypeError:
                    pass
            if not send_list:
                raise SystemEError(*ERROR_MSG_0048)
        send_user, email_host, stamp_key = cls.mail_config()
        email = EmailSend(EmailNoticeModel(
            send_user=send_user,
            email_host=email_host,
            stamp_key=stamp_key,
            send_list=send_list,
        ), test_report, cls.get_domain_name())
        email.send_main()

    @classmethod
    def test_report(cls, test_suite_id: int) -> TestReportModel:
        test_suite = TestSuite.objects.get(id=test_suite_id)
        execution_duration = test_suite.update_time - test_suite.create_time

        # 获取API和UI的统计数据
        api_case_sum, api_call, api_success, api_fail, api_warning = cls.__api(test_suite_id)
        ui_case_sum, ui_step_call, ui_success, ui_fail, ui_warning = cls.__ui(test_suite_id)
        pytest_case_sum, pytest_func_call, pytest_success, pytest_fail, pytest_warning = cls.__pytest(test_suite_id)

        # 合计所有统计数据（只计算非None的值）
        case_sum = (api_case_sum or 0) + (ui_case_sum or 0) + (pytest_case_sum or 0)
        success = (api_success or 0) + (ui_success or 0) + (pytest_success or 0)
        fail = (api_fail or 0) + (ui_fail or 0) + (pytest_fail or 0)
        warning = (api_warning or 0) + (ui_warning or 0) + (pytest_warning or 0)
        # 计算成功率
        success_rate = 100 if case_sum == 0 else round(success / case_sum * 100, 2)

        # 将秒数转换为HH:MM:SS格式
        total_seconds = int(execution_duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        execution_duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        return TestReportModel(
            test_suite_id=test_suite_id,
            case_sum=case_sum,
            success=success,
            success_rate=success_rate,
            warning=warning,
            fail=fail,
            api_case_sum=api_case_sum,
            api_fail=api_fail,
            ui_fail=ui_fail,
            pytest_fail=pytest_fail,
            ui_case_sum=ui_case_sum,
            pytest_case_sum=pytest_case_sum,
            api_call=api_call,
            ui_step_call=ui_step_call,
            pytest_func_call=pytest_func_call,
            execution_duration=execution_duration_str,
            test_time=test_suite.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            test_environment=EnvironmentEnum.get_value(test_suite.test_env),
            project_name=test_suite.project_product.project.name,
            project_id=test_suite.project_product.project.id)

    @staticmethod
    def __api(test_suite_id):
        case_result = TestSuiteDetails.objects.filter(test_suite_id=test_suite_id, type=TestCaseTypeEnum.API.value)
        api_case_sum = 0
        api_call = 0
        success = 0
        fail = 0
        warning = 0
        if not case_result.exists():
            return None, None, None, None, None

        for i in case_result:
            for r in i.result_data:
                api_case_sum += 1
                api_call += 1
                if r.get('status') == StatusEnum.SUCCESS.value:
                    success += 1
                else:
                    fail += 1
        return api_case_sum, api_call, success, fail, warning

    @staticmethod
    def __pytest(test_suite_id):
        case_result = TestSuiteDetails.objects.filter(test_suite_id=test_suite_id, type=TestCaseTypeEnum.PYTEST.value)
        pytest_case_sum = 0
        pytest_func_call = 0
        success = 0
        fail = 0
        warning = 0
        if not case_result.exists():
            return None, None, None, None, None

        for i in case_result:
            for r in i.result_data:
                pytest_case_sum += 1
                pytest_func_call += 1
                if r.get('status') == StatusEnum.SUCCESS.value:
                    success += 1
                else:
                    fail += 1
        return pytest_case_sum, pytest_func_call, success, fail, warning

    @staticmethod
    def __ui(test_suite_id):
        case_result = TestSuiteDetails.objects.filter(test_suite_id=test_suite_id, type=TestCaseTypeEnum.UI.value)
        if not case_result.exists():
            return None, None, None, None, None

        ui_case_sum = case_result.count()
        ui_step_call = 0
        success = case_result.filter(status=StatusEnum.SUCCESS.value).count()
        fail = case_result.filter(status=StatusEnum.FAIL.value).count()
        warning = 0
        for i in case_result:
            ui_step_call += len(i.result_data)
        return ui_case_sum, ui_step_call, success, fail, warning

    @staticmethod
    def mail_config():
        try:
            send_user = CacheData.objects.get(key=CacheDataKeyEnum.SEND_USER.name).value
            email_host = CacheData.objects.get(key=CacheDataKeyEnum.EMAIL_HOST.name).value
            stamp_key = CacheData.objects.get(key=CacheDataKeyEnum.STAMP_KET.name).value
        except CacheData.DoesNotExist:
            raise SystemEError(*ERROR_MSG_0031)
        else:
            if send_user is None or email_host is None or stamp_key is None:
                raise SystemEError(*ERROR_MSG_0031)
        return send_user, email_host, stamp_key

    @classmethod
    def get_domain_name(cls):
        domain_name = f'请先到系统管理->系统设置中设置：{CacheDataKeyEnum.DOMAIN_NAME.value}，此处才会显示跳转连接'
        try:
            cache_data_obj = CacheData.objects.get(key=CacheDataKeyEnum.DOMAIN_NAME.name)
        except CacheData.DoesNotExist:
            pass
        else:
            if cache_data_obj.value:
                domain_name = cache_data_obj.value
        return domain_name
