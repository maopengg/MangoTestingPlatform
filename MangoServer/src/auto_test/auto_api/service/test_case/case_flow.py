# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 使用 Semaphore 安全控制 API 用例并发执行
# @Time   : 2026-01-16
# @Author : Qwen (based on 毛鹏's original)

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from django.db import close_old_connections, transaction
from django.utils import timezone
from django.db.models import F

from src.auto_test.auto_system.models import TestSuite, TestSuiteDetails
from src.enums.tools_enum import TaskEnum, TestCaseTypeEnum
from src.models.system_model import ConsumerCaseModel
from src.settings import API_MAX_TASKS, RETRY_FREQUENCY
from src.tools.decorator.retry import async_task_db_connection
from src.tools.log_collector import log


class ApiCaseFlow:
    # 线程池：可稍大于并发上限，避免 submit 阻塞
    executor = ThreadPoolExecutor(max_workers=API_MAX_TASKS * 2)

    # 核心：使用 Semaphore 限制真正执行的并发数
    _task_semaphore = threading.Semaphore(API_MAX_TASKS)

    # 防止多个线程同时拉取同一条任务
    _get_case_lock = threading.Lock()

    # 后台线程引用
    thread = None

    @classmethod
    def start(cls):
        """启动后台任务获取线程"""
        if cls.thread is not None and cls.thread.is_alive():
            log.api.info('API任务获取线程已在运行，跳过重复启动')
            return
        cls.thread = threading.Thread(target=cls._background_task_fetcher, daemon=True)
        cls.thread.start()
        log.api.info('API任务获取线程已启动')

    @classmethod
    def _background_task_fetcher(cls):
        """后台循环拉取任务"""
        log.api.info('API用例执行启动成功！')
        while True:
            try:
                cls.get_case()
                time.sleep(0.5)
            except Exception as e:
                log.api.error(f'API任务获取器出错: {e}')
                time.sleep(3)

    @classmethod
    def get_case(cls):
        """从数据库拉取一条待执行的 API 用例"""
        with cls._get_case_lock:
            close_old_connections()
            test_suite_details = TestSuiteDetails.objects.filter(
                status=TaskEnum.STAY_BEGIN.value,
                retry__lt=RETRY_FREQUENCY + 1,
                type=TestCaseTypeEnum.API.value
            ).order_by('id').first()
            if test_suite_details:
                try:
                    test_suite = TestSuite.objects.get(id=test_suite_details.test_suite.id)
                    case_model = ConsumerCaseModel(
                        test_suite_details=test_suite_details.id,
                        test_suite=test_suite_details.test_suite.id,
                        case_id=test_suite_details.case_id,
                        case_name=test_suite_details.case_name,
                        test_env=test_suite_details.test_env,
                        user_id=test_suite.user.id,
                        tasks_id=test_suite.tasks.id if test_suite.tasks else None,
                        parametrize=test_suite_details.parametrize,
                    )
                    log.api.info(f'API发送用例：{case_model.model_dump_json()}')
                    # 提交任务，真正的并发控制在 execute_task 内部
                    cls.executor.submit(cls.execute_task, case_model)
                except Exception as error:
                    log.api.error(f'准备任务失败（ID={test_suite_details.id}）: {error}')
                    cls.mark_task_failed(test_suite_details.id)
            close_old_connections()

    @classmethod
    @async_task_db_connection(max_retries=1, retry_delay=1)
    def execute_task(cls, case_model: ConsumerCaseModel):
        """
        执行单个 API 用例，受 Semaphore 限制并发数
        """
        # 获取信号量（阻塞直到有空位）
        cls._task_semaphore.acquire()
        try:
            # 真正开始执行，更新状态为 PROCEED（仅当仍是 STAY_BEGIN）
            cls.update_status_to_proceed(case_model.test_suite_details)

            from src.auto_test.auto_api.service.test_case.test_case import TestCase
            test_case = TestCase(
                user_id=case_model.user_id,
                test_env=case_model.test_env,
                case_id=case_model.case_id,
                test_suite=case_model.test_suite,
                test_suite_details=case_model.test_suite_details,
            )
            result = test_case.test_case()
            cls.mark_task_success(case_model.test_suite_details)
            return result
        except Exception as e:
            log.api.error(f"任务执行失败（ID={case_model.test_suite_details}）: {e}")
            cls.mark_task_failed(case_model.test_suite_details)
        finally:
            cls._task_semaphore.release()  # 必须释放！

    @classmethod
    def update_status_to_proceed(cls, detail_id: int):
        """原子性地将任务状态设为 PROCEED（仅当仍为 STAY_BEGIN）"""
        with transaction.atomic():
            detail = TestSuiteDetails.objects.select_for_update().get(id=detail_id)
            if detail.status == TaskEnum.STAY_BEGIN.value:
                detail.status = TaskEnum.PROCEED.value
                detail.push_time = timezone.now()
                detail.save(update_fields=['status', 'push_time'])

    @classmethod
    def mark_task_success(cls, detail_id: int):
        """标记任务成功"""
        TestSuiteDetails.objects.filter(id=detail_id).update(
            status=TaskEnum.SUCCESS.value,
            end_time=timezone.now()
        )

    @classmethod
    def mark_task_failed(cls, detail_id: int):
        """标记任务失败，并增加重试次数"""
        TestSuiteDetails.objects.filter(id=detail_id).update(
            status=TaskEnum.FAIL.value,
            retry=F('retry') + 1,
            end_time=timezone.now()
        )