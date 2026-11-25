from mangoautomation.uidrives import BaseData

from src.customization import ObtainAssertion, ObtainTestData
from src.services.runtime_config import get_ai_config
from src.services.ui.element_locator_engine import UiElementLocatorEngine
from src.tools import project_dir
from src.tools.log_collector import log
from src.services.system_error_reporter import ActuatorSystemErrorReporter


class RuntimeBaseDataFactory:
    @staticmethod
    def create(test_env: int | None = None, test_data: ObtainTestData | None = None) -> BaseData:
        ai_config = get_ai_config()
        return BaseData(test_data or ObtainTestData(), log) \
            .set_system_error_callback(ActuatorSystemErrorReporter.report) \
            .set_file_path(project_dir.download(), project_dir.screenshot()) \
            .set_assertion_class(ObtainAssertion) \
            .set_locator_engine(UiElementLocatorEngine(test_env, logger=log)) \
            .set_agent(
                ai_config.can_locate(),
                ai_config.api_key,
                base_url=ai_config.base_url,
                model=ai_config.model,
            )
