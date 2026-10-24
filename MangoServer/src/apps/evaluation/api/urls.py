from django.urls import path
from src.apps.evaluation.api.views.dataset import DatasetCRUD
from src.apps.evaluation.api.views.dataset_version import DatasetVersionViews
from src.apps.evaluation.api.views.dataset_item import DatasetItemViews
from src.apps.evaluation.api.views.case import CaseViews
from src.apps.evaluation.api.views.execution import CaseExecutionViews
from src.apps.evaluation.api.views.item_result import ItemResultViews
from src.apps.evaluation.api.views.grader import GraderViews


urlpatterns = [
    path("dataset", DatasetCRUD.as_view()),
    path("dataset/graders", GraderViews.as_view({"get": "dataset_catalog"})),
    path("dataset/<int:dataset_id>/versions", DatasetVersionViews.as_view({"get": "list", "post": "create"})),
    path("dataset/version/<int:pk>", DatasetVersionViews.as_view({"get": "retrieve", "put": "update", "delete": "delete"})),
    path("dataset/version/<int:pk>/workflow-resources", DatasetVersionViews.as_view({"get": "workflow_resources"})),
    path("dataset/version/<int:pk>/input-preview", DatasetVersionViews.as_view({"post": "input_preview"})),
    path("dataset/version/<int:pk>/publish", DatasetVersionViews.as_view({"post": "publish"})),
    path("dataset/version/<int:pk>/quality", DatasetVersionViews.as_view({"get": "quality"})),
    path("dataset/version/<int:pk>/quality/acknowledge", DatasetVersionViews.as_view({"post": "acknowledge_quality"})),
    path("dataset/version/<int:pk>/diff", DatasetVersionViews.as_view({"get": "diff"})),
    path("dataset/version/<int:pk>/api-cases/audit", DatasetVersionViews.as_view({"post": "audit_api_cases"})),
    path("dataset/version/<int:pk>/api-cases/import", DatasetVersionViews.as_view({"post": "import_api_cases"})),
    path("dataset/version/<int:version_id>/items", DatasetItemViews.as_view({"get": "list", "post": "create"})),
    path("dataset/item/<int:pk>", DatasetItemViews.as_view({"put": "update", "delete": "delete"})),
    path("case", CaseViews.as_view({"get": "list", "post": "create", "put": "update", "delete": "delete"})),
    path("case/graders", CaseViews.as_view({"get": "graders"})),
    path("case/<int:pk>", CaseViews.as_view({"get": "retrieve"})),
    path("case/<int:pk>/interfaces", CaseViews.as_view({"get": "interfaces"})),
    path("case/<int:pk>/ai-profiles", CaseViews.as_view({"get": "ai_profiles"})),
    path("case/<int:pk>/validate", CaseViews.as_view({"post": "validate"})),
    path("case/<int:pk>/grading-preview", CaseViews.as_view({"get": "grading_preview"})),
    path("case/<int:pk>/copy", CaseViews.as_view({"post": "copy"})),
    path("case/<int:case_id>/execute", CaseExecutionViews.as_view({"post": "create"})),
    path("case/<int:case_id>/executions", CaseExecutionViews.as_view({"get": "list"})),
    path("case/<int:case_id>/executions/latest", CaseExecutionViews.as_view({"get": "latest"})),
    path("case/<int:case_id>/executions/<int:execution_id>", CaseExecutionViews.as_view({"get": "retrieve"})),
    path("case/<int:case_id>/executions/<int:execution_id>/stop", CaseExecutionViews.as_view({"post": "stop"})),
    path("case/<int:case_id>/executions/<int:execution_id>/retry", CaseExecutionViews.as_view({"post": "retry"})),
    path("case/<int:case_id>/executions/<int:execution_id>/items", ItemResultViews.as_view({"get": "list"})),
    path("case/<int:case_id>/executions/<int:execution_id>/items/<int:item_result_id>", ItemResultViews.as_view({"get": "retrieve"})),
    path("graders", GraderViews.as_view({"get": "list"})),
    path("graders/<str:grader_key>/versions/<int:version>", GraderViews.as_view({"get": "retrieve"})),
]
