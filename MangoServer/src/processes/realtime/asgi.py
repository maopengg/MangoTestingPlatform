import json
import socket
import uuid

from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import re_path

from src.processes.realtime.consumer import RealtimeConsumer
from src.processes.realtime.live_stream.consumers import (
    LiveStreamPublisherConsumer,
    LiveStreamSubscriberConsumer,
)
from src.processes.realtime.live_stream.registry import LiveStreamRegistry
from src.processes.realtime.registry import LocalConnectionRegistry
from src.processes.realtime.supervisor import RealtimeSupervisor

SERVICE_INSTANCE = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
REGISTRY = LocalConnectionRegistry()
LIVE_STREAM_REGISTRY = LiveStreamRegistry()
SUPERVISOR = RealtimeSupervisor(REGISTRY, SERVICE_INSTANCE, LIVE_STREAM_REGISTRY)

websocket_application = ProtocolTypeRouter(
    {
        "websocket": URLRouter(
            [
                re_path(
                    r"^ws/web/socket/?$",
                    RealtimeConsumer.as_asgi(
                        registry=REGISTRY,
                        service_instance=SERVICE_INSTANCE,
                    ),
                ),
                re_path(
                    r"^ws/client/socket/?$",
                    RealtimeConsumer.as_asgi(
                        registry=REGISTRY,
                        service_instance=SERVICE_INSTANCE,
                    ),
                ),
                re_path(
                    r"^ws/ui-stream/subscribe/(?P<stream_id>[^/]+)/?$",
                    LiveStreamSubscriberConsumer.as_asgi(registry=LIVE_STREAM_REGISTRY),
                ),
                re_path(
                    r"^ws/ui-stream/publish/(?P<stream_id>[^/]+)/?$",
                    LiveStreamPublisherConsumer.as_asgi(registry=LIVE_STREAM_REGISTRY),
                ),
            ]
        )
    }
)


async def application(scope, receive, send):
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                try:
                    await SUPERVISOR.start()
                except BaseException as error:
                    await send({"type": "lifespan.startup.failed", "message": str(error)})
                    raise
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await SUPERVISOR.stop()
                await send({"type": "lifespan.shutdown.complete"})
                return
        return
    if scope["type"] == "http":
        path_value = scope.get("path") or ""
        status = 200
        payload = {"status": "ok", "service": "realtime-service"}
        if path_value == "/health/ready":
            try:
                SUPERVISOR.assert_healthy()
                payload["connections"] = await REGISTRY.counts()
                payload["live_stream"] = await LIVE_STREAM_REGISTRY.stats()
            except Exception as error:
                status = 503
                payload = {"status": "error", "service": "realtime-service", "message": str(error)}
        elif path_value != "/health/live":
            status = 404
            payload = {"status": "not_found"}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"application/json; charset=utf-8")],
        })
        await send({"type": "http.response.body", "body": body})
        return
    SUPERVISOR.assert_healthy()
    return await websocket_application(scope, receive, send)
