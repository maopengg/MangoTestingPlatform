import type { GeneratorConfig } from './types'
interface GeneratorRow {
  generator_type?: number | string
  generator_config?: GeneratorConfig | null
  enum_values?: unknown[]
}

function displayValue(value: unknown): string {
  if (value === undefined) return '未配置'
  if (value === null) return 'null'
  if (value === '') return '空字符串'
  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}

export function getGeneratorDisplay(row: GeneratorRow) {
  const config = row.generator_config || {}
  const type = Number(row.generator_type)
  let text: string
  const automatic = ![1, 9, 13].includes(type)
  switch (type) {
    case 0:
      text = config.reason || '数据库生成'
      break
    case 1:
    case 13:
      text = displayValue(config.value)
      break
    case 2:
      text = `自动生成${config.length == null ? '' : `；长度 ${config.length}`}${
        config.prefix ? `；前缀 ${config.prefix}` : ''
      }`
      break
    case 3:
    case 4:
      text =
        config.min != null || config.max != null
          ? `范围：${config.min ?? '默认'}～${config.max ?? '默认'}`
          : '自动生成'
      if (type === 4 && config.precision != null) text += `；小数位 ${config.precision}`
      break
    case 5:
      text = '自动生成当前时间'
      break
    case 6:
      text = (['days', 'hours', 'minutes'] as const)
        .map((key, index) =>
          config[key] != null ? `${config[key]}${['天', '小时', '分钟'][index]}` : ''
        )
        .filter(Boolean)
        .join('，')
      text = text ? `当前时间偏移：${text}` : '自动生成相对时间'
      break
    case 7:
      text =
        config.dash == null
          ? '自动生成 UUID'
          : `自动生成 UUID（${config.dash ? '带' : '不带'}连字符）`
      break
    case 9: {
      const options: Array<{ label?: string | number | boolean | null; value: unknown }> =
        Array.isArray(config.options) && config.options.length
          ? config.options
          : (config.values || row.enum_values || []).map((value) => ({ value }))
      const selected = options.find((option) => Object.is(option.value, config.value))
      text =
        config.mode === 'random'
          ? `随机选择（${options.length} 项）`
          : selected?.label != null
          ? `${selected.label}（${displayValue(config.value)}）`
          : displayValue(config.value)
      break
    }
    case 11:
      text = config.alias
        ? `${config.alias}.${config.field || 'id'}`
        : config.dependency_entity_id
        ? `依赖实体 ID ${config.dependency_entity_id}，取 ${config.field || 'id'} 字段`
        : '未配置依赖实体'
      break
    default:
      text = '暂不支持展示此生成方式'
  }
  return { text, automatic, enum: type === 9 }
}
