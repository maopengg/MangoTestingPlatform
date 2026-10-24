import type { DataFactoryFieldRule } from '@/types/data-factory'

const booleanLabels: Record<string, [string, string]> = {
  nullable: ['必填', '可空'],
  primary_key: ['普通', '主键'],
  autoincrement: ['非自增', '自增'],
}

const booleanOptions = [
  { key: 0, title: '否' },
  { key: 1, title: '是' },
]
const typeOptions = ['integer', 'decimal', 'string', 'boolean', 'datetime', 'date', 'json', 'enum']
  .map((key) => ({ key, title: key }))

export function getFieldTag(record: DataFactoryFieldRule, field: string) {
  if (booleanLabels[field]) {
    const value = record[field as 'nullable' | 'primary_key' | 'autoincrement']
    const key = value === true ? 1 : value === false ? 0 : null
    return {
      label: key === null ? '-' : booleanLabels[field][key],
      key,
      options: booleanOptions,
    }
  }
  const label = (field === 'db_type' ? record.db_type : record.platform_type) || '-'
  return {
    label,
    key: label === '-' ? null : record.platform_type?.trim().toLowerCase() || null,
    options: typeOptions,
  }
}
