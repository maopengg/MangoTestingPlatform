from unittest.mock import AsyncMock, patch

import pytest

from src.exceptions import UiError
from src.services.system_error_reporter import ActuatorSystemErrorReporter


@pytest.mark.asyncio
async def test_report_sends_sanitized_error_to_server():
    error = RuntimeError('runtime failed')
    with patch(
        'src.network.HTTP.actuator_tasks.report_system_error',
        new=AsyncMock(return_value={'code': 200}),
    ) as report:
        result = await ActuatorSystemErrorReporter.report(
            error,
            'runtime:test',
            traceback_text='traceback text',
        )

    assert result is True
    report.assert_awaited_once_with(
        operation='runtime:test',
        exception_type='RuntimeError',
        message='runtime failed',
        traceback_text='traceback text',
    )


@pytest.mark.asyncio
async def test_business_error_is_not_reported():
    error = UiError(100, 'expected failure')
    with patch(
        'src.network.HTTP.actuator_tasks.report_system_error',
        new=AsyncMock(),
    ) as report:
        result = await ActuatorSystemErrorReporter.report(error, 'ui:test')

    assert result is False
    report.assert_not_awaited()


@pytest.mark.asyncio
async def test_report_failure_does_not_replace_original_flow():
    with patch(
        'src.network.HTTP.actuator_tasks.report_system_error',
        new=AsyncMock(side_effect=OSError('offline')),
    ):
        result = await ActuatorSystemErrorReporter.report(RuntimeError('failed'), 'runtime:test')

    assert result is False
