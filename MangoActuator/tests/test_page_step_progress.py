from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from mangoautomation.models import ElementResultModel
from src.network import ActuatorUiEventEnum
from src.services.ui.page_steps import PageSteps


class PageStepProgressTest(IsolatedAsyncioTestCase):
    async def test_linear_flow_records_real_next_node_before_pushing(self):
        service = PageSteps.__new__(PageSteps)
        first_node = SimpleNamespace(id=11, type=0, precondition=None, postcondition=None)
        second_node = SimpleNamespace(id=12, type=0, precondition=None, postcondition=None)
        service.page_steps_model = SimpleNamespace(
            element_list=[first_node, second_node],
        )
        first_result = ElementResultModel(id=11, type=0, status=1)
        second_result = ElementResultModel(id=12, type=0, status=1)
        service._ope_steps = AsyncMock(side_effect=[first_result, second_result])
        service._record_element_result = AsyncMock()
        service._update_element_data = AsyncMock(side_effect=lambda _, element: element)

        result = await service.test_flow_data(
            {
                "id": 11,
                "children": [{"id": 12, "children": []}],
            }
        )

        self.assertIs(result, second_result)
        self.assertEqual(first_result.next_node_id, 12)
        self.assertEqual(
            service._record_element_result.await_args_list[0].args[0].next_node_id,
            12,
        )

    @patch("src.services.ui.page_steps.socket_conn.async_send", new_callable=AsyncMock)
    async def test_case_node_progress_is_lightweight_and_targets_trigger_user(self, async_send):
        service = PageSteps.__new__(PageSteps)
        service.progress_mode = PageSteps.PROGRESS_MODE_CASE
        service.progress_user = "maopeng"
        service.page_steps_model = SimpleNamespace(id=7, name="创建订单")
        service.page_step_result_model = SimpleNamespace(
            execution_id="execution-1",
            id=7,
            case_step_details_id=21,
            slot_id="slot-1",
            executor_connection_id="connection-1",
            element_result_list=[],
        )
        result = ElementResultModel(id=31, type=0, status=1, next_node_id=32)
        service.page_step_result_model.element_result_list.append(result)

        await service._send_node_progress(result)

        payload = async_send.await_args.kwargs
        self.assertEqual(payload["func_name"], ActuatorUiEventEnum.PAGE_STEP_NODE_PROGRESS.value)
        self.assertEqual(payload["user"], "maopeng")
        self.assertEqual(payload["func_args"]["execution_id"], "execution-1")
        self.assertEqual(payload["func_args"]["completed_count"], 1)
