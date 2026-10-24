from src.common.enums.base import BaseEnum


class TaskCaseVersionPolicyEnum(BaseEnum):
    """定时任务中的用例版本选择策略。"""

    PINNED = 'pinned'

    @classmethod
    def obj(cls):
        return {
            cls.PINNED.value: '固定版本',
        }


class TaskCaseVersionStatusEnum(BaseEnum):
    """定时任务执行 API Case 时动态跟随的版本状态。"""

    PUBLISHED = 'published'
    UNPUBLISHED = 'unpublished'

    @classmethod
    def obj(cls):
        return {
            cls.PUBLISHED.value: '已发布',
            cls.UNPUBLISHED.value: '未发布',
        }
