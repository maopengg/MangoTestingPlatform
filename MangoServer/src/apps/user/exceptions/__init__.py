"""Business exceptions owned by this Django app."""

from src.common.exceptions.base import MangoServerError
from src.common.exceptions.definitions import ErrorDefinition


class UserError(MangoServerError):
    pass


USER_REQUEST_FORMAT_INVALID = ErrorDefinition(code=1093,
                                              message='请求数据格式错误，请检查请求头 Content-Type 和请求体格式：{}')
USER_CACHE_CACHE_USER_INVALID = ErrorDefinition(code=41000, message='用户缓存值格式不正确')
USER_CREDENTIAL_INVALID = ErrorDefinition(code=41001, message='请输入正确的邮箱地址。')
USER_CREDENTIAL_USER_BINDING_INVALID = ErrorDefinition(code=41002,
                                                       message='该用户尚未切换为邮箱登录，请用户先在个人中心修改密码并绑定登录邮箱。')
USER_CREDENTIAL_USER_INVALID = ErrorDefinition(code=41003, message='该邮箱已被其他用户使用，请更换邮箱。')
USER_CREDENTIAL_EMAIL_CONFIG_FAILED = ErrorDefinition(code=41004,
                                                      message='邮件发送失败，请前往“系统运维 → 配置管理 → 邮箱配置”检查配置后重试。')
USER_CREDENTIAL_USER_NOT_ALLOWED = ErrorDefinition(code=41005, message='用户昵称不允许为空。')
USER_CREDENTIAL_CONFIG_REQUIRED = ErrorDefinition(code=41006,
                                                  message='系统邮箱尚未配置完整，请联系管理员前往“系统运维 → 配置管理 → 邮箱配置”完成配置后重试。')
USER_CREDENTIAL_NOT_FOUND = ErrorDefinition(code=41007, message='所选角色不存在，请刷新角色列表后重试。')
USER_CREDENTIAL_PERMISSION_INVALID = ErrorDefinition(code=41008, message='只有超级管理员可以授予超级管理员权限。')
USER_TEST_ENVIRONMENT_NOT_FOUND = ErrorDefinition(code=41009, message='测试环境不存在，请重新选择。')

USER_GENERAL_USER_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=41010,
                                                                    message='用户-有关联数据，请先删除绑定的数据后再删除！')

USER_GENERAL_CASE_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=41011,
                                                                    message='API测试用例-有关联数据，请先删除绑定的数据后再删除！')

USER_GENERAL_CASE_RELATION_DELETE_BINDING_INVALID_CODE_CASE_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(
    code=41012, message='UI测试用例-有关联数据，请先删除绑定的数据后再删除！')

USER_GENERAL_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=41013,
                                                               message='测试对象-有关联数据，请先删除绑定的数据后再删除！')

USER_GENERAL_TASK_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=41014,
                                                                    message='定时任务-有关联数据，请先删除绑定的数据后再删除！')

USER_GENERAL_USER_RELATION_DELETE_BINDING_INVALID_CODE_USER_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(
    code=41015, message='用户部门-有关联数据，请先删除绑定的数据后再删除！')

USER_GENERAL_PROJECT_PRODUCT_PERMISSION_RELATION_DELETE_BINDING_INVALID = ErrorDefinition(code=41016,
                                                                                          message='部门项目产品权限-有关联数据，请先删除绑定的数据后再删除！')

USER_PROJECT_PRODUCT_OWNER_DELETE_BINDING_INVALID = ErrorDefinition(code=41017,
                                                                    message='项目产品负责人-有关联数据，请先更换负责人后再删除用户！')
USER_ENDPOINT_PERMISSION_INVALID = ErrorDefinition(code=41018, message='角色菜单或接口授权配置无效，请刷新后重试。')
USER_CONFIG_INVALID = ErrorDefinition(code=41019, message='用户配置格式无效，请检查后重试。')
USER_ROLE_AUTHORIZATION_INVALID = ErrorDefinition(code=41020, message='角色授权配置格式无效，请联系管理员检查。')
USER_ROLE_AUTHORIZATION_TRANSFER_INVALID = ErrorDefinition(code=41021, message='授权备份、角色身份或现有授权冲突，未写入授权，请检查后重试。')
USER_HTTP_PERMISSION_POLICY_MISSING = ErrorDefinition(code=41022, message='接口未登记权限策略，请联系开发人员补充配置。')
