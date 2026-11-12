"""用户操作日志写入服务。"""

import atexit
from collections import Counter
import logging
import os
from queue import Empty, Full, Queue
from threading import Event, Lock, Thread, current_thread
from time import monotonic

from django.db import close_old_connections

from src.apps.user.models import User, UserLogs
from src.common.database import ModelMutationValidationError, save_model, validate_model

logger = logging.getLogger(__name__)
USER_LOG_QUEUE_CAPACITY = 5000
USER_LOG_BATCH_SIZE = 100
USER_LOG_FLUSH_INTERVAL = 1
USER_LOG_DROP_WARNING_INTERVAL = 60
USER_LOG_SHUTDOWN_TIMEOUT = 5


def _validation_failure_details(error: ModelMutationValidationError) -> set[tuple[str, str]]:
    # Django 的原始错误文案、params 和未知字段名都可能带入请求中的敏感值。
    # 只输出模型白名单字段及错误码对应的固定原因，不直接格式化原异常。
    fields = {field.name: field for field in UserLogs._meta.concrete_fields}
    causes = getattr(error.__cause__, 'error_dict', {})
    errors = error.errors if isinstance(error.errors, dict) else {'__all__': []}
    reasons = {
        'blank': '字段不允许为空', 'null': '字段不允许为 NULL',
        'invalid': '字段格式不正确', 'invalid_choice': '不在允许的选项范围内',
        'invalid_pk_value': '关联主键格式不正确', 'does_not_exist': '关联对象不存在',
        'unique': '字段值重复', 'unique_together': '字段组合重复',
        'max_value': '超过允许的最大值', 'min_value': '小于允许的最小值',
    }
    details = set()
    for name in errors:
        field = fields.get(name)
        safe_name = name if field is not None or name == '__all__' else '<未知字段>'
        for item in causes.get(name, []) or [None]:
            code = getattr(item, 'code', None)
            reason = reasons.get(code, '字段校验失败（未输出原始文案）')
            if code == 'invalid' and field is not None and field.is_relation:
                reason = '关联对象不存在或不可用'
            if code == 'max_length' and field is not None and field.max_length is not None:
                reason = f'长度超过上限（{field.max_length} 字符）'
            if field is None and name != '__all__':
                reason = '提交了模型未定义的字段'
            details.add((safe_name, reason))
    return details or {('__all__', '字段校验失败（未输出原始文案）')}


def _report_validation_failures(invalid: int, failures: Counter) -> None:
    details = [{'field': field, 'reason': reason, 'count': count}
               for (field, reason), count in sorted(failures.items())]
    logger.error('操作日志保存校验未通过，本批跳过 %s 条；字段校验详情：%s', invalid, details)


class _UserLogDispatcher:
    def __init__(self, capacity=USER_LOG_QUEUE_CAPACITY, batch_size=USER_LOG_BATCH_SIZE,
                 flush_interval=USER_LOG_FLUSH_INTERVAL):
        self.queue = Queue(maxsize=capacity)
        self._lock = Lock()
        self._closing = Event()
        self._worker = None
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.dropped_count = 0
        self._unreported_drops = 0
        self._last_drop_warning = None

    def submit(self, payload: dict, username: str | None = None) -> None:
        task = (dict(payload), username)
        reason = '进程退出中'
        with self._lock:
            if not self._closing.is_set():
                try:
                    if self._worker is None or not self._worker.is_alive():
                        self._worker = Thread(target=self._consume, name='user-log-writer', daemon=True)
                        self._worker.start()
                    self.queue.put_nowait(task)
                    return
                except Full:
                    reason = '队列已满'
                except RuntimeError:
                    self._worker = None
                    reason = '消费线程启动失败'
            self.dropped_count += 1
            self._unreported_drops += 1
            now = monotonic()
            report = None
            if self._last_drop_warning is None or now - self._last_drop_warning >= USER_LOG_DROP_WARNING_INTERVAL:
                report = (self._unreported_drops, self.dropped_count)
                self._unreported_drops = 0
                self._last_drop_warning = now
        if report:
            logger.warning('操作日志%s，丢弃新日志 %s 条，本进程累计丢弃 %s 条', reason, *report)

    def _consume(self) -> None:
        pending = []
        deadline = None
        while True:
            if self._closing.is_set() and self.queue.empty() and not pending:
                return
            timeout = 0.1 if deadline is None else min(0.1, max(0, deadline - monotonic()))
            try:
                task = self.queue.get(timeout=timeout)
            except Empty:
                pass
            else:
                pending.append(task)
                if deadline is None:
                    deadline = monotonic() + self.flush_interval
            if not pending:
                continue
            if (len(pending) < self.batch_size and monotonic() < deadline
                    and not (self._closing.is_set() and self.queue.empty())):
                continue
            try:
                self._persist_batch(pending)
            finally:
                for _task in pending:
                    self.queue.task_done()
                pending = []
                deadline = None

    @staticmethod
    def _persist_batch(tasks) -> None:
        try:
            close_old_connections()
            payloads = []
            for source, username in tasks:
                payload = dict(source)
                if payload.get('user') is None and username:
                    try:
                        payload['user'] = User._default_manager.get(username=username).id
                    except User.DoesNotExist:
                        pass
                if payload.get('user') and not User.objects.filter(id=payload['user']).exists():
                    payload['user'] = None
                payloads.append(payload)
            UserLogService.record_batch(payloads)
        except Exception as error:
            # 不打印请求正文或数据库异常原文，避免敏感内容进入文件日志。
            logger.error('操作日志批量保存失败，本批 %s 条，异常类型：%s', len(tasks), type(error).__name__)
        finally:
            try:
                close_old_connections()
            except Exception as error:
                logger.error('操作日志连接清理失败，异常类型：%s', type(error).__name__)

    def shutdown(self, timeout=USER_LOG_SHUTDOWN_TIMEOUT) -> None:
        with self._lock:
            self._closing.set()
            worker = self._worker
            drops = self._unreported_drops
            self._unreported_drops = 0
        if drops:
            logger.warning('操作日志退出统计：新增丢弃 %s 条，本进程累计丢弃 %s 条', drops, self.dropped_count)
        if worker is not None and worker is not current_thread():
            worker.join(timeout=timeout)
        if self.queue.unfinished_tasks:
            logger.warning('操作日志退出等待超时，尚有 %s 条日志未处理完成', self.queue.unfinished_tasks)


_dispatcher = _UserLogDispatcher()


def _reset_after_fork():
    global _dispatcher
    # Gunicorn 预加载后 fork，子进程不能复用父进程的锁、线程或待写日志。
    _dispatcher = _UserLogDispatcher()


def _shutdown_dispatcher():
    _dispatcher.shutdown()


if hasattr(os, 'register_at_fork'):
    os.register_at_fork(after_in_child=_reset_after_fork)
atexit.register(_shutdown_dispatcher)


class UserLogService:
    @staticmethod
    def submit(payload: dict, *, username: str | None = None) -> None:
        _dispatcher.submit(payload, username)

    @staticmethod
    def record(payload: dict) -> UserLogs | None:
        try:
            return save_model(UserLogs, payload)
        except ModelMutationValidationError as error:
            _report_validation_failures(1, Counter(_validation_failure_details(error)))
            return None

    @staticmethod
    def record_batch(payloads: list[dict]) -> int:
        records = []
        invalid = 0
        failures = Counter()
        for payload in payloads:
            try:
                validate_model(UserLogs, payload)
            except ModelMutationValidationError as error:
                invalid += 1
                failures.update(_validation_failure_details(error))
                continue
            values = {
                field.attname: getattr(payload[field.name], 'pk', payload[field.name])
                for field in UserLogs._meta.concrete_fields
                if field.editable and not field.auto_created and field.name in payload
            }
            records.append(UserLogs(**values))
        if invalid:
            _report_validation_failures(invalid, failures)
        if records:
            # UserLogs 没有自定义 save 或保存信号；字段校验保留，写入失败不重试。
            UserLogs.objects.bulk_create(records, batch_size=USER_LOG_BATCH_SIZE)
        return len(records)
