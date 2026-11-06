import { fieldRuleColumns } from '../../entity/config'

export const entityRuleColumns = fieldRuleColumns.filter((item) => item.key !== 'preview_value')

export const entityRuleTableScrollWidth = 1340

export const cleanupResourceDescription = '仅配置同产品的ES逻辑数据源。document_id_field指定本次落库记录的ES业务ID字段，例如SQL主键为_id而ES用id时填"id"；不传/null才用SQL主键，指定字段缺值不会回退。tenant_field取实体租户值，tenant_path指定ES租户路径。verify仅回查；delete_and_verify精确删除后回查，需环境读写权限。规则执行时冻结，不接管历史记录；[]清空。'
export const cleanupResourceExample = JSON.stringify([
  { datasource_alias_id: 1, index_template: 'example_template_{tenant}', document_id_field: 'id', tenant_field: 'tenant_id', tenant_path: 'tenant_id', mode: 'verify', timeout_seconds: 15, poll_seconds: 1 },
], null, 2)
