from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.system.services.socket_link.consumer.ui import UIConsumer


class UiExecutorCallbackTest(SimpleTestCase):
    @patch(
        "src.apps.system.services.socket_link.consumer.ui.ExecutorSlotLeaseService.set_running"
    )
    def test_final_result_releases_executor_slot_running_state(self, set_running):
        UIConsumer._finish_executor_slot({
            "slot_id": "slot-1",
            "executor_connection_id": "connection-1",
            "execution_id": "execution-1",
        })

        set_running.assert_called_once_with(
            "connection-1",
            "slot-1",
            False,
            execution_id="execution-1",
        )

    @patch(
        "src.apps.system.services.socket_link.consumer.ui.TestReportWriting.update_page_step_status"
    )
    @patch(
        "src.apps.system.services.socket_link.consumer.ui.ExecutorSlotLeaseService.set_running"
    )
    def test_page_step_increment_does_not_release_executor_slot(
            self,
            set_running,
            update_status,
    ):
        data = {
            "id": 7,
            "name": "步骤",
            "type": 0,
            "project_product_id": 1,
            "project_product_name": "产品",
            "cache_data": {},
            "test_object": "https://example.test",
            "status": 3,
            "is_final": False,
            "element_result_list": [],
            "slot_id": "slot-1",
            "executor_connection_id": "connection-1",
        }

        UIConsumer.u_page_steps.__wrapped__(UIConsumer, data)

        set_running.assert_not_called()
        update_status.assert_called_once()

    @patch(
        "src.apps.system.services.socket_link.consumer.ui.TestReportWriting.update_page_step_status"
    )
    @patch(
        "src.apps.system.services.socket_link.consumer.ui.ExecutorSlotLeaseService.set_running"
    )
    def test_page_step_final_releases_executor_slot(
            self,
            set_running,
            update_status,
    ):
        data = {
            "id": 7,
            "name": "步骤",
            "type": 0,
            "project_product_id": 1,
            "project_product_name": "产品",
            "cache_data": {},
            "test_object": "https://example.test",
            "status": 1,
            "is_final": True,
            "element_result_list": [],
            "slot_id": "slot-1",
            "executor_connection_id": "connection-1",
        }

        UIConsumer.u_page_steps.__wrapped__(UIConsumer, data)

        set_running.assert_called_once_with(
            "connection-1",
            "slot-1",
            False,
            execution_id="7",
        )
        update_status.assert_called_once()

    @patch(
        "src.apps.system.services.socket_link.consumer.ui.TestReportWriting.update_page_step_status"
    )
    @patch(
        "src.apps.system.services.socket_link.consumer.ui.ExecutorSlotLeaseService.set_running"
    )
    def test_case_step_final_does_not_release_case_executor_slot(
            self,
            set_running,
            update_status,
    ):
        data = {
            "id": 7,
            "name": "步骤",
            "type": 0,
            "project_product_id": 1,
            "project_product_name": "产品",
            "case_step_details_id": 12,
            "cache_data": {},
            "test_object": "https://example.test",
            "status": 1,
            "is_final": True,
            "element_result_list": [],
            "slot_id": "slot-1",
            "executor_connection_id": "connection-1",
        }

        UIConsumer.u_page_steps.__wrapped__(UIConsumer, data)

        set_running.assert_not_called()
        update_status.assert_called_once()

    @patch(
        "src.apps.system.services.socket_link.consumer.ui.TestReportWriting.update_page_step_status"
    )
    @patch(
        "src.apps.system.services.socket_link.consumer.ui.UiPageStepResult"
    )
    def test_page_step_debug_result_is_saved(self, result_model, update_status):
        result = object()
        result_model.return_value = result
        data = {"workspace_id": "workspace-1", "status": 1}

        UIConsumer.u_page_steps.__wrapped__(UIConsumer, data)

        result_model.assert_called_once_with(**data)
        update_status.assert_called_once_with(result)

    @patch(
        "src.apps.system.services.socket_link.consumer.ui.GrayCaseExecutionRunner.restore_by_config_ids"
    )
    @patch(
        "src.apps.system.services.socket_link.consumer.ui.TestReportWriting.update_test_case"
    )
    @patch(
        "src.apps.system.services.socket_link.consumer.ui.UiCaseExecutionResult"
    )
    def test_case_execution_result_is_saved_and_gray_config_is_restored(
            self,
            result_model,
            update_case,
            restore_gray,
    ):
        result = type("Result", (), {
            "gray_config_ids": [7],
            "gray_execution_log_ids": [9],
            "id": 12,
            "name": "Mango Mock UI 执行与直播",
            "test_env": 1,
        })()
        result_model.return_value = result
        data = {"id": 12, "status": 1}

        UIConsumer.u_test_case.__wrapped__(UIConsumer, data)

        update_case.assert_called_once_with(result)
        restore_gray.assert_called_once()
