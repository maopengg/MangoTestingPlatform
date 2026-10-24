"""Business exceptions owned by the evaluation app."""

from src.common.exceptions import ErrorDefinition, MangoServerError


class EvaluationError(MangoServerError):
    pass


EVALUATION_OBJECT_NOT_FOUND = ErrorDefinition(code=62001, message='评测对象不存在')
EVALUATION_DATASET_VERSION_NOT_FOUND = ErrorDefinition(code=62002, message='评测数据集版本不存在')
EVALUATION_PUBLISHED_VERSION_IMMUTABLE = ErrorDefinition(code=62003, message='已发布版本不可修改')
EVALUATION_CASE_CONFIG_INVALID = ErrorDefinition(code=62004, message='评测用例配置不合法：{}')
EVALUATION_TARGET_CONFIG_INVALID = ErrorDefinition(code=62005, message='评测目标配置不合法：{}')
EVALUATION_EXECUTION_NOT_FOUND = ErrorDefinition(code=62006, message='Case 执行记录不存在')
EVALUATION_EXECUTION_OPERATION_NOT_ALLOWED = ErrorDefinition(code=62007, message='Case 执行当前状态不允许执行该操作')
EVALUATION_GRADER_UNAVAILABLE = ErrorDefinition(code=62008, message='评分器不存在或未启用：{}@{}')
EVALUATION_ADAPTER_UNSUPPORTED = ErrorDefinition(code=62009, message='评测目标适配器不支持：{}')
EVALUATION_DATASET_HAS_NO_ITEMS = ErrorDefinition(code=62010, message='数据集没有可执行数据条目')
EVALUATION_PROJECT_PRODUCT_ACCESS_DENIED = ErrorDefinition(code=62011, message='没有当前项目产品的数据权限')
EVALUATION_ITEM_SCHEMA_INVALID = ErrorDefinition(code=62013, message='数据集数据条目不符合Schema：{}')
EVALUATION_ASSET_CONFIG_INVALID = ErrorDefinition(code=62015, message='评测资产配置不合法：{}')
EVALUATION_JUDGE_SNAPSHOT_CHANGED = ErrorDefinition(code=62016, message='AI评审配置或提示词版本已变化，不能按原运行快照复现')
EVALUATION_EXECUTION_FAILED = ErrorDefinition(code=62017, message='评测执行异常，请联系管理员查看服务端日志')
EVALUATION_ATTEMPT_NOT_FOUND = ErrorDefinition(code=62018, message='评测执行尝试记录不存在')
EVALUATION_TARGET_ACCESS_DENIED = ErrorDefinition(code=62019, message='没有被测业务对象的执行权限')
EVALUATION_TARGET_CALL_FAILED = ErrorDefinition(code=62020, message='被测接口调用失败：{}')
EVALUATION_ANSWER_MODEL_CHANGED = ErrorDefinition(code=62022, message='问答生成模型或提示词已变化，请重新创建执行')
EVALUATION_DATASET_ACCESS_DENIED = ErrorDefinition(code=62023, message='没有评测数据集的访问权限')
