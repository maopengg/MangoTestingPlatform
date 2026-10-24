from django.core.cache import cache
from mangotools.contracts import SocketCommandContract, SocketEnvelopeContract
from time import time

from src.apps.system.enums import ClientTypeEnum
from src.apps.system.enums import ServerPerfEventEnum
from src.apps.system.services.socket_link.message_service import SocketMessageService
from src.apps.user.models import User


class PerfRealtimeService:
    TTL_SECONDS = 60

    @classmethod
    def subscribe(cls, scope: str, object_id: int, user_id: int):
        key = cls._key(scope, object_id)
        expires = int(time()) + cls.TTL_SECONDS
        try:
            from django_redis import get_redis_connection
            redis = get_redis_connection("default")
            redis.zadd(key, {str(user_id): expires})
            redis.expire(key, cls.TTL_SECONDS * 2)
        except Exception:
            viewers = cache.get(key, {})
            viewers[str(user_id)] = expires
            cache.set(key, viewers, cls.TTL_SECONDS * 2)

    @classmethod
    def unsubscribe(cls, scope: str, object_id: int, user_id: int):
        key = cls._key(scope, object_id)
        try:
            from django_redis import get_redis_connection
            get_redis_connection("default").zrem(key, str(user_id))
        except Exception:
            viewers = cache.get(key, {})
            viewers.pop(str(user_id), None)
            cache.set(key, viewers, cls.TTL_SECONDS * 2)

    @classmethod
    def viewers(cls, scope: str, object_id: int) -> list[int]:
        key = cls._key(scope, object_id)
        now = int(time())
        try:
            from django_redis import get_redis_connection
            redis = get_redis_connection("default")
            redis.zremrangebyscore(key, 0, now)
            return [int(value) for value in redis.zrangebyscore(key, now + 1, "+inf")]
        except Exception:
            viewers = cache.get(key, {})
            active = {user_id: expiry for user_id, expiry in viewers.items() if expiry > now}
            cache.set(key, active, cls.TTL_SECONDS * 2)
            return [int(user_id) for user_id in active]

    @classmethod
    def notify_run(cls, run):
        cls._notify("run", run.id, ServerPerfEventEnum.RUN_UPDATE.value, {
            "run_id": run.id, "revision": run.revision,
            "status": run.status,
        })

    @classmethod
    def _notify(cls, scope: str, object_id: int, func_name: str, args: dict):
        users = User.objects.filter(id__in=cls.viewers(scope, object_id)).values_list("username", flat=True)
        for username in users:
            SocketMessageService.send_socket_data(SocketEnvelopeContract(
                code=200, msg="性能运行数据已更新", user=username, is_notice=ClientTypeEnum.WEB.value,
                data=SocketCommandContract(func_name=func_name, func_args=args),
            ))

    @staticmethod
    def _key(scope: str, object_id: int) -> str:
        return f"perf:{scope}:{object_id}:viewers"
