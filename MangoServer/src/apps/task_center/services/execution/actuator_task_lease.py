# -*- coding: utf-8 -*-
import json
from datetime import timedelta

from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.test_center.models import TestSuiteDetails
from src.common.logging import log


class ActuatorTaskLease:
    PREFIX = '__ACTUATOR_LEASE__:'
    EXPIRE_SECONDS = 30

    @classmethod
    def marker(cls, message_id: str | None, username: str | None, dispatch_id: str):
        return cls.PREFIX + json.dumps({
            'message_id': message_id,
            'username': username,
            'dispatch_id': dispatch_id,
            'leased_at': timezone.now().isoformat(),
        }, ensure_ascii=False)

    @classmethod
    def parse_marker(cls, value: str | None) -> dict | None:
        if not value or not value.startswith(cls.PREFIX):
            return None
        try:
            marker = json.loads(value[len(cls.PREFIX):])
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        return marker if isinstance(marker, dict) else None

    @classmethod
    def marker_matches(cls, value: str | None, username: str, message_id: str, dispatch_id: str) -> bool:
        marker = cls.parse_marker(value)
        return bool(
            marker
            and marker.get('username') == username
            and marker.get('message_id') == message_id
            and marker.get('dispatch_id') == dispatch_id
        )

    @classmethod
    def set_lease(cls, detail_id: int, message_id: str | None, username: str | None, dispatch_id: str):
        TestSuiteDetails.objects.filter(id=detail_id).update(
            error_message=cls.marker(message_id, username, dispatch_id),
            push_time=timezone.now(),
            update_time=timezone.now(),
        )

    @classmethod
    def recover_expired(cls):
        expire_time = timezone.now() - timedelta(seconds=cls.EXPIRE_SECONDS)
        rows = list(TestSuiteDetails.objects.filter(
            status=TaskEnum.PROCEED.value,
            error_message__startswith=cls.PREFIX,
            push_time__lt=expire_time,
        ).values('id', 'retry'))
        for row in rows:
            TestSuiteDetails.objects.filter(id=row['id']).update(
                status=TaskEnum.STAY_BEGIN.value,
                retry=max(0, int(row.get('retry') or 0) - 1),
                error_message=None,
                push_time=None,
                update_time=timezone.now(),
            )
        if rows:
            log.system.warning(f'恢复执行器未ACK的过期任务租约，数量：{len(rows)}')
        return len(rows)

    @classmethod
    def ack_items(cls, items: list[dict], username: str, message_id: str):
        accepted = 0
        rejected = 0
        for item in items:
            dispatch_id = item.get('dispatch_id')
            if not dispatch_id:
                continue
            detail_id = cls.detail_id_from_dispatch_id(dispatch_id)
            if not detail_id:
                continue
            row = TestSuiteDetails.objects.filter(id=detail_id).values('retry', 'error_message').first()
            lease_value = (row or {}).get('error_message')
            if not cls.marker_matches(lease_value, username, message_id, dispatch_id):
                log.system.warning(
                    f'忽略不匹配的执行器任务确认：username={username}, message_id={message_id}, '
                    f'dispatch_id={dispatch_id}'
                )
                continue
            if item.get('status') == 'accepted':
                updated = TestSuiteDetails.objects.filter(
                    id=detail_id,
                    error_message=lease_value,
                ).update(error_message=None, update_time=timezone.now())
                accepted += updated
            elif item.get('status') == 'rejected':
                updated = TestSuiteDetails.objects.filter(id=detail_id, error_message=lease_value).update(
                    status=TaskEnum.STAY_BEGIN.value,
                    retry=max(0, int((row or {}).get('retry') or 0) - 1),
                    error_message=None,
                    push_time=None,
                    update_time=timezone.now(),
                )
                rejected += updated
        return accepted, rejected

    @staticmethod
    def detail_id_from_dispatch_id(dispatch_id: str):
        try:
            return int(str(dispatch_id).split(':', 1)[1])
        except Exception:
            return None
