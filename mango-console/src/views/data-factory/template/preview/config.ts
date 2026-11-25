import { fieldRuleColumns } from '../../entity/config'

export const entityRuleColumns = fieldRuleColumns.filter((item) => item.key !== 'preview_value')

export const entityRuleTableScrollWidth = 1400

export const cleanupResourceDescription =
  'SQL已清理不等于ES已清理。verify只等待并验证，不会删除；delete_and_verify才会核验归属并条件删除，需环境读写权限。index_template支持固定索引、example_{tenant}或{tenant}，不是${{变量}}表达式。document_id_field明确指定ES文档ID来源字段，不传/null才用SQL主键；指定字段缺值禁止回退。tenant_path取实际ES租户路径；局部文档可配置tenant_lineage，证明同执行完整子记录集合。索引缺失不自动创建。规则冻结后仅影响后续执行，旧执行使用原快照和正式补偿入口；[]清空后续规则。'
export const cleanupResourceExample = JSON.stringify(
  [
    {
      datasource_alias_id: 1,
      index_template: 'example_template_{tenant}',
      document_id_field: 'id',
      tenant_field: 'tenant_id',
      tenant_path: 'tenant_id',
      mode: 'verify',
      timeout_seconds: 15,
      poll_seconds: 1,
    },
  ],
  null,
  2
)
