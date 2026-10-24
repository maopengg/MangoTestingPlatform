from django.urls import path

from src.apps.perf.api.views.capacity import PerfCapacityViews
from src.apps.perf.api.views.internal import PerfRunNodeViews
from src.apps.perf.api.views.run import PerfRunCRUD, PerfRunViews
from src.apps.perf.api.views.scenario import PerfScenarioCRUD, PerfScenarioViews

urlpatterns = [
    path("capacity/overview", PerfCapacityViews.as_view({"get": "overview"})),
    path("scenario", PerfScenarioCRUD.as_view()),
    path("scenario/executors", PerfScenarioViews.as_view({"get": "executors"})),
    path("scenario/<int:pk>", PerfScenarioViews.as_view({"get": "retrieve"})),
    path("scenario/<int:pk>/source-api-cases", PerfScenarioViews.as_view({"get": "source_api_cases"})),
    path("scenario/<int:pk>/validate", PerfScenarioViews.as_view({"post": "validate"})),
    path("scenario/<int:pk>/script-preview", PerfScenarioViews.as_view({"get": "script_preview"})),
    path("scenario/<int:pk>/configuration", PerfScenarioViews.as_view({"put": "configuration"})),
    path("scenario/<int:pk>/execute", PerfScenarioViews.as_view({"post": "execute"})),
    path("scenario/<int:pk>/preflight", PerfScenarioViews.as_view({"post": "preflight"})),
    path("run", PerfRunCRUD.as_view()),
    path("run/<int:pk>", PerfRunViews.as_view({"get": "retrieve"})),
    path("run/<int:pk>/overview", PerfRunViews.as_view({"get": "overview"})),
    path("run/<int:pk>/metrics", PerfRunViews.as_view({"get": "metrics"})),
    path("run/<int:pk>/requests", PerfRunViews.as_view({"get": "requests"})),
    path("run/<int:pk>/stages", PerfRunViews.as_view({"get": "stages"})),
    path("run/<int:pk>/nodes", PerfRunViews.as_view({"get": "nodes"})),
    path("run/<int:pk>/nodes/<int:node_id>/capture/download", PerfRunViews.as_view({"get": "capture_download"})),
    path("run/<int:pk>/errors", PerfRunViews.as_view({"get": "errors"})),
    path("run/<int:pk>/thresholds", PerfRunViews.as_view({"get": "thresholds"})),
    path("run/<int:pk>/validity", PerfRunViews.as_view({"get": "validity"})),
    path("run/<int:pk>/events", PerfRunViews.as_view({"get": "events"})),
    path("run/<int:pk>/snapshot", PerfRunViews.as_view({"get": "snapshot"})),
    path("run/<int:pk>/export", PerfRunViews.as_view({"get": "export"})),
    path("run/<int:pk>/rerun", PerfRunViews.as_view({"post": "rerun"})),
    path("run/<int:pk>/stop", PerfRunViews.as_view({"post": "stop"})),
    path("run/<int:pk>/cancel", PerfRunViews.as_view({"post": "cancel"})),
    path("run/<int:pk>/finalize", PerfRunViews.as_view({"post": "finalize"})),
    path("run/<int:pk>/set-baseline", PerfRunViews.as_view({"post": "set_baseline"})),
    path("run/<int:pk>/comparison", PerfRunViews.as_view({"get": "comparison"})),
    path("run/<int:pk>/realtime-subscription",
         PerfRunViews.as_view({"post": "subscription", "delete": "subscription"})),
    path("run-node/<int:pk>/ready", PerfRunNodeViews.as_view({"post": "ready"})),
    path("run-node/<int:pk>/control", PerfRunNodeViews.as_view({"get": "control"})),
    path("run-node/<int:pk>/heartbeat", PerfRunNodeViews.as_view({"post": "heartbeat"})),
    path("run-node/<int:pk>/metrics/batch", PerfRunNodeViews.as_view({"post": "metrics"})),
    path("run-node/<int:pk>/errors/batch", PerfRunNodeViews.as_view({"post": "errors"})),
    path("run-node/<int:pk>/secrets", PerfRunNodeViews.as_view({"get": "secrets"})),
    path("run-node/<int:pk>/result", PerfRunNodeViews.as_view({"post": "result"})),
]
