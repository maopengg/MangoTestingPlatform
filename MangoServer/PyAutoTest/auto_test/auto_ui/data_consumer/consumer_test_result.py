# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏
import logging

from PyAutoTest.auto_test.auto_ui.models import UiCase

log = logging.getLogger('ui')


class ConsumerTestResult:

    @classmethod
    def case_state_update(cls, case_id: int, result: bool) -> None:
        try:
            res, created = UiCase.objects.get_or_create(id=case_id)
            res.state = 1 if result else 0
            res.save()
        except UiCase.DoesNotExist as e:
            # 处理找不到对应记录的情况
            log.error(f"写入用例失败，不存在需要修改的用例状态：{e}")
