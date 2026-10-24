# -*- coding: utf-8 -*-
import socket
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta

import time
from django.db import IntegrityError, transaction
from django.utils import timezone

from src.apps.gray_config.enums import GrayConfigTypeEnum, GrayExecutionLockStatusEnum
from src.apps.gray_config.exceptions import (
    GRAY_REPOSITORY_TASK_GRAY_INVALID,
    GrayConfigError,
)
from src.apps.gray_config.models import GrayExecutionLock, GrayFeature, GrayRepository
from src.common.logging import log


@dataclass
class GrayLockResource:
    lock_key: str
    repository: GrayRepository | None = None
    branch: str | None = None
    owner_type: str | None = None
    owner_id: str | None = None
    execution_log_id: int | None = None
    remark: str | None = None


class GrayLockHandle:
    def __init__(self, resource: GrayLockResource):
        self.resource = resource
        self.lock_key = resource.lock_key
        self._stop_event = threading.Event()
        self._renew_thread: threading.Thread | None = None
        self._released = False

    def start_renewal(self):
        if self._renew_thread:
            return
        self._renew_thread = threading.Thread(
            target=self._renew_loop,
            name=f"gray-lock-renew-{self.lock_key[:32]}",
            daemon=True,
        )
        self._renew_thread.start()

    def release(self):
        if self._released:
            return
        self._released = True
        self._stop_event.set()
        if self._renew_thread and self._renew_thread.is_alive():
            self._renew_thread.join(timeout=1)
        GrayExecutionLockService.release(self)

    def _renew_loop(self):
        while not self._stop_event.wait(GrayExecutionLockService.RENEW_INTERVAL_SECONDS):
            try:
                GrayExecutionLockService.renew(self)
            except Exception as error:
                log.system.warning(f"续期灰度执行锁失败：key={self.lock_key}, error={error}")


class GrayExecutionLockService:
    LOCK_SECONDS = 300
    WAIT_SECONDS = 300
    SLEEP_SECONDS = 1
    RENEW_INTERVAL_SECONDS = 60

    @classmethod
    @contextmanager
    def locked(cls, feature: GrayFeature, target_value: str | None = None):
        handles = cls.acquire_for_features([feature], owner_type="manual", owner_id=str(feature.id))
        try:
            yield
        finally:
            cls.release_handles(handles)

    @classmethod
    @contextmanager
    def locked_resources(cls, resources: list[GrayLockResource]):
        handles = cls.acquire_resources(resources)
        try:
            yield handles
        finally:
            cls.release_handles(handles)

    @classmethod
    def acquire_for_features(
            cls,
            features: list[GrayFeature],
            owner_type: str | None = None,
            owner_id: str | None = None,
            remark: str | None = None,
    ) -> list[GrayLockHandle]:
        return cls.acquire_resources([
            cls.resource_for_feature(feature, owner_type=owner_type, owner_id=owner_id, remark=remark)
            for feature in features
        ])

    @classmethod
    def acquire_resources(cls, resources: list[GrayLockResource], renew: bool = True) -> list[GrayLockHandle]:
        unique_resources = cls.unique_resources(resources)
        if not unique_resources:
            return []
        handles: list[GrayLockHandle] = []
        try:
            for resource in unique_resources:
                handle = cls.acquire_one(resource)
                if renew:
                    handle.start_renewal()
                handles.append(handle)
            return handles
        except Exception:
            cls.release_handles(handles)
            raise

    @classmethod
    def acquire_one(cls, resource: GrayLockResource) -> GrayLockHandle:
        deadline = time.monotonic() + cls.WAIT_SECONDS
        while time.monotonic() <= deadline:
            if cls.try_acquire(resource):
                return GrayLockHandle(resource)
            time.sleep(cls.SLEEP_SECONDS)
        raise GrayConfigError(GRAY_REPOSITORY_TASK_GRAY_INVALID)

    @classmethod
    def try_acquire(cls, resource: GrayLockResource) -> bool:
        now = timezone.now()
        expired_at = now + timedelta(seconds=cls.LOCK_SECONDS)
        try:
            with transaction.atomic():
                lock = cls.get_or_create_lock_for_update(resource)
                if lock.status == GrayExecutionLockStatusEnum.LOCKED.value and lock.expired_at and lock.expired_at > now:
                    return False
                if lock.status == GrayExecutionLockStatusEnum.LOCKED.value:
                    lock.status = GrayExecutionLockStatusEnum.EXPIRED.value
                cls.fill_locked(lock, resource, now, expired_at)
                lock.save()
                return True
        except IntegrityError:
            return False

    @classmethod
    def get_or_create_lock_for_update(cls, resource: GrayLockResource) -> GrayExecutionLock:
        lock = GrayExecutionLock.objects.select_for_update().filter(lock_key=resource.lock_key).first()
        if lock:
            return lock
        try:
            GrayExecutionLock.objects.create(
                lock_key=resource.lock_key,
                status=GrayExecutionLockStatusEnum.RELEASED.value,
            )
        except IntegrityError:
            pass
        return GrayExecutionLock.objects.select_for_update().get(lock_key=resource.lock_key)

    @classmethod
    def fill_locked(
            cls,
            lock: GrayExecutionLock,
            resource: GrayLockResource,
            locked_at,
            expired_at,
    ):
        lock.repository = resource.repository
        lock.branch = resource.branch
        lock.owner_type = resource.owner_type
        lock.owner_id = resource.owner_id
        lock.execution_log_id = resource.execution_log_id
        lock.status = GrayExecutionLockStatusEnum.LOCKED.value
        lock.locked_at = locked_at
        lock.expired_at = expired_at
        lock.released_at = None
        lock.node_name = cls.node_name()
        lock.remark = resource.remark

    @classmethod
    def renew(cls, handle: GrayLockHandle):
        now = timezone.now()
        expired_at = now + timedelta(seconds=cls.LOCK_SECONDS)
        with transaction.atomic():
            lock = GrayExecutionLock.objects.select_for_update().filter(lock_key=handle.lock_key).first()
            if not lock or lock.status != GrayExecutionLockStatusEnum.LOCKED.value:
                return
            if not cls.is_same_owner(lock, handle.resource):
                return
            lock.expired_at = expired_at
            lock.save(update_fields=["expired_at", "update_time"])

    @classmethod
    def release(cls, handle: GrayLockHandle):
        try:
            cls.release_resource(handle.resource)
        except Exception as error:
            log.system.warning(f"释放灰度执行锁失败：key={handle.lock_key}, error={error}")

    @classmethod
    def release_resource(cls, resource: GrayLockResource):
        with transaction.atomic():
            lock = GrayExecutionLock.objects.select_for_update().filter(lock_key=resource.lock_key).first()
            if not lock or lock.status != GrayExecutionLockStatusEnum.LOCKED.value:
                return
            if not cls.is_same_owner(lock, resource):
                return
            lock.status = GrayExecutionLockStatusEnum.RELEASED.value
            lock.released_at = timezone.now()
            lock.save(update_fields=["status", "released_at", "update_time"])

    @classmethod
    def release_resources(cls, resources: list[GrayLockResource] | None):
        for resource in reversed(cls.unique_resources(resources or [])):
            try:
                cls.release_resource(resource)
            except Exception as error:
                log.system.warning(f"释放灰度执行锁失败：key={resource.lock_key}, error={error}")

    @classmethod
    def bind_execution_log(cls, resource: GrayLockResource, execution_log_id: int | None):
        if not execution_log_id:
            return
        try:
            with transaction.atomic():
                lock = GrayExecutionLock.objects.select_for_update().filter(lock_key=resource.lock_key).first()
                if not lock or lock.status != GrayExecutionLockStatusEnum.LOCKED.value:
                    return
                if not cls.is_same_owner(lock, resource):
                    return
                lock.execution_log_id = execution_log_id
                lock.save(update_fields=["execution_log_id", "update_time"])
        except Exception as error:
            log.system.warning(
                f"绑定灰度执行锁记录失败：key={resource.lock_key}, log_id={execution_log_id}, error={error}")

    @staticmethod
    def is_same_owner(lock: GrayExecutionLock, resource: GrayLockResource) -> bool:
        return (
                str(lock.owner_type or "") == str(resource.owner_type or "")
                and str(lock.owner_id or "") == str(resource.owner_id or "")
        )

    @classmethod
    def release_handles(cls, handles: list[GrayLockHandle] | None):
        for handle in reversed(handles or []):
            handle.release()

    @classmethod
    def resource_for_feature(
            cls,
            feature: GrayFeature,
            owner_type: str | None = None,
            owner_id: str | None = None,
            execution_log_id: int | None = None,
            remark: str | None = None,
    ) -> GrayLockResource:
        if feature.config_type == GrayConfigTypeEnum.YAML.value:
            binding = getattr(feature, "yaml_file_binding", None)
            repository = getattr(binding, "repository", None) if binding else None
            repository_id = getattr(repository, "id", None) or "none"
            branch = getattr(repository, "branch", None) or "master"
            return GrayLockResource(
                lock_key=f"gray_repo:{repository_id}:{branch}",
                repository=repository,
                branch=branch,
                owner_type=owner_type,
                owner_id=owner_id,
                execution_log_id=execution_log_id,
                remark=remark,
            )
        if feature.config_type == GrayConfigTypeEnum.SQL.value:
            return GrayLockResource(
                lock_key=f"gray_sql:{feature.database_id or 'none'}:{feature.feature_key}",
                owner_type=owner_type,
                owner_id=owner_id,
                execution_log_id=execution_log_id,
                remark=remark,
            )
        if feature.config_type == GrayConfigTypeEnum.CODE.value:
            return GrayLockResource(
                lock_key=f"gray_code:{feature.id}",
                owner_type=owner_type,
                owner_id=owner_id,
                execution_log_id=execution_log_id,
                remark=remark,
            )
        return GrayLockResource(
            lock_key=f"gray_feature:{feature.id}",
            owner_type=owner_type,
            owner_id=owner_id,
            execution_log_id=execution_log_id,
            remark=remark,
        )

    @staticmethod
    def unique_resources(resources: list[GrayLockResource]) -> list[GrayLockResource]:
        result = {}
        for resource in resources or []:
            if resource and resource.lock_key:
                result.setdefault(resource.lock_key, resource)
        return [result[key] for key in sorted(result.keys())]

    @staticmethod
    def node_name() -> str:
        return socket.gethostname()
