import type { GeneratorConfig, FieldRecord, FieldRow, JsonValue, EnumOption } from './types'
import { fieldMetadata } from './form'
export const GENERATOR_TYPE_SKIP = 0
export const GENERATOR_TYPE_FIXED = 1
export const GENERATOR_TYPE_RANDOM_STRING = 2
export const GENERATOR_TYPE_RANDOM_INTEGER = 3
export const GENERATOR_TYPE_RANDOM_DECIMAL = 4
export const GENERATOR_TYPE_NOW = 5
export const GENERATOR_TYPE_RELATIVE_TIME = 6
export const GENERATOR_TYPE_UUID = 7
export const GENERATOR_TYPE_ENUM = 9
export const GENERATOR_TYPE_DEPENDENCY_FIELD = 11
export const GENERATOR_TYPE_FUNCTION = 13
export const REMOVED_GENERATOR_TYPES = [8, 10, 12]
export const GENERATOR_TYPE_ORDER = [
  GENERATOR_TYPE_SKIP,
  GENERATOR_TYPE_FIXED,
  GENERATOR_TYPE_FUNCTION,
  GENERATOR_TYPE_RANDOM_STRING,
  GENERATOR_TYPE_RANDOM_INTEGER,
  GENERATOR_TYPE_RANDOM_DECIMAL,
  GENERATOR_TYPE_NOW,
  GENERATOR_TYPE_RELATIVE_TIME,
  GENERATOR_TYPE_UUID,
  GENERATOR_TYPE_ENUM,
  GENERATOR_TYPE_DEPENDENCY_FIELD,
]

export function cloneValue(value: JsonValue): JsonValue {
  if (Array.isArray(value)) return value.map(cloneValue)
  if (value !== null && typeof value === 'object')
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, cloneValue(item)]))
  return value
}
export function copyGeneratorConfig(config: GeneratorConfig = {}): GeneratorConfig {
  return {
    ...config,
    ...(config.value !== undefined ? { value: cloneValue(config.value) } : {}),
    ...(config.values ? { values: config.values.map(cloneValue) } : {}),
    ...(config.options
      ? {
          options: config.options.map((item) => ({
            label: item.label,
            value: cloneValue(item.value),
          })),
        }
      : {}),
  }
}

export function getGeneratorTypeOrder(value: number | string) {
  const index = GENERATOR_TYPE_ORDER.indexOf(Number(value))
  return index === -1 ? GENERATOR_TYPE_ORDER.length + Number(value) : index
}

export function getGeneratorTypeTitle(option: { key: number | string; title: string }) {
  const titleMap: Record<number, string> = {
    [GENERATOR_TYPE_RANDOM_STRING]: '随机字符串（长度8）',
    [GENERATOR_TYPE_RANDOM_INTEGER]: '随机整数（1-100）',
    [GENERATOR_TYPE_RANDOM_DECIMAL]: '随机小数（1-100，2位）',
  }
  return titleMap[Number(option.key)] || option.title
}

export function formatPreviewDisplayValue(record: FieldRow) {
  if (record.preview_valid === false && record.preview_message) {
    return record.preview_message
  }
  return formatPreviewValue(record.preview_value)
}

export function formatPreviewValue(value: JsonValue | undefined) {
  if (value === undefined) {
    return 'null'
  }
  if (value === null) {
    return 'null'
  }
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  return String(value)
}

export function normalizeFieldRow(row: FieldRecord): FieldRow {
  const generatorConfig = copyGeneratorConfig(
    row.generator_config || row.recommend?.generator_config || {}
  )
  if (row.generator_type === GENERATOR_TYPE_DEPENDENCY_FIELD && !generatorConfig.field) {
    generatorConfig.field = 'id'
  }
  return {
    ...row,
    enum_values: row.enum_values?.map(cloneValue) || [],
    generator_type: row.generator_type ?? row.recommend?.generator_type ?? 1,
    generator_config: generatorConfig,
    generator_config_value: getGeneratorConfigValue({
      ...row,
      generator_config: generatorConfig,
    }),
    preview_value: undefined,
    preview_valid: true,
    preview_message: '',
  }
}

export function buildFieldPayloadItem(row: FieldRow) {
  row = { ...row, enum_values: row.enum_values?.map(cloneValue) || [] }
  let generatorConfig = copyGeneratorConfig(row.generator_config)
  if (row.generator_type === GENERATOR_TYPE_ENUM) {
    normalizeEnumFieldForSave(row, generatorConfig)
  } else if (row.generator_type === GENERATOR_TYPE_DEPENDENCY_FIELD) {
    generatorConfig = {
      dependency_entity_id: generatorConfig.dependency_entity_id,
      field: generatorConfig.field || 'id',
    }
  } else if (row.generator_type === GENERATOR_TYPE_SKIP) {
    generatorConfig = generatorConfig.reason ? { reason: generatorConfig.reason } : {}
  } else if (row.generator_type === GENERATOR_TYPE_RANDOM_STRING) {
    generatorConfig = pickGeneratorConfig(generatorConfig, ['prefix', 'length'])
  } else if (row.generator_type === GENERATOR_TYPE_RANDOM_INTEGER) {
    generatorConfig = pickGeneratorConfig(generatorConfig, ['min', 'max'])
  } else if (row.generator_type === GENERATOR_TYPE_RANDOM_DECIMAL) {
    generatorConfig = pickGeneratorConfig(generatorConfig, ['min', 'max', 'precision'])
  } else if (row.generator_type === GENERATOR_TYPE_NOW) {
    generatorConfig = {}
  } else if (row.generator_type === GENERATOR_TYPE_RELATIVE_TIME) {
    generatorConfig = pickGeneratorConfig(generatorConfig, ['days', 'hours', 'minutes'])
  } else if (row.generator_type === GENERATOR_TYPE_UUID) {
    generatorConfig = pickGeneratorConfig(generatorConfig, ['dash'])
  } else if (!isReadonlyGeneratorConfig(row)) {
    const value = row.generator_config_value ?? ''
    if (row.generator_type === GENERATOR_TYPE_FIXED) {
      generatorConfig = { value }
    } else if (row.generator_type === GENERATOR_TYPE_FUNCTION) {
      generatorConfig = { value }
    } else if (value === '') {
      delete generatorConfig.value
    } else {
      generatorConfig.value = value
    }
  }
  return {
    ...fieldMetadata(row),
    generator_type: row.generator_type,
    generator_config: generatorConfig,
  }
}

export function pickGeneratorConfig(
  config: GeneratorConfig,
  keys: Array<keyof GeneratorConfig>
): GeneratorConfig {
  return Object.fromEntries(
    keys
      .filter((key) => config[key] !== undefined && config[key] !== null && config[key] !== '')
      .map((key) => [key, config[key]])
  )
}

export function changeGeneratorType(row: FieldRow) {
  row.generator_config = getDefaultGeneratorConfig(row)
  row.generator_config_value = getGeneratorConfigValue(row)
  row.preview_value = undefined
  row.preview_valid = true
  row.preview_message = ''
}

export function getDefaultGeneratorConfig(row: FieldRow): GeneratorConfig {
  if (row.generator_type === GENERATOR_TYPE_RANDOM_STRING) {
    return { prefix: '', length: 8 }
  }
  if (row.generator_type === GENERATOR_TYPE_RANDOM_INTEGER) {
    return { min: 1, max: 100 }
  }
  if (row.generator_type === GENERATOR_TYPE_RANDOM_DECIMAL) {
    return { min: 1, max: 100, precision: 2 }
  }
  if (row.generator_type === GENERATOR_TYPE_UUID) {
    return { dash: false }
  }
  if (row.generator_type === GENERATOR_TYPE_ENUM) {
    const values = row.enum_values || []
    return values.length ? { values, value: values[0], mode: 'fixed' } : {}
  }
  if (row.generator_type === GENERATOR_TYPE_DEPENDENCY_FIELD) {
    return { field: 'id' }
  }
  if (
    row.generator_type === GENERATOR_TYPE_FIXED ||
    row.generator_type === GENERATOR_TYPE_FUNCTION
  ) {
    return { value: '' }
  }
  return {}
}

export function getEnumOptionRows(row: FieldRow) {
  const config = row.generator_config || {}
  const optionRows = Array.isArray(config.options) ? config.options : []
  if (optionRows.length) {
    return optionRows.map((option: EnumOption) => ({
      label: option.label ?? String(option.value ?? ''),
      value: option.value,
    }))
  }
  const values = config.values || row.enum_values || []
  return values.map((value: JsonValue) => ({
    label: String(value),
    value,
  }))
}

export function getEnumSelectOptions(row: FieldRow) {
  return getEnumOptionRows(row).map((option: EnumOption) => ({
    label: `${option.label}（${formatPreviewValue(option.value)}）`,
    value: option.value,
  }))
}

export function castEnumValue(value: JsonValue, platformType?: string) {
  if (platformType === 'integer') {
    return Number.parseInt(String(value), 10)
  }
  if (platformType === 'decimal') {
    return Number(value)
  }
  if (platformType === 'boolean') {
    if (value === true || value === 'true' || value === '1' || value === 1) {
      return true
    }
    if (value === false || value === 'false' || value === '0' || value === 0) {
      return false
    }
  }
  return value
}

export function refreshEnumConfigValue(row: FieldRow) {
  row.generator_config = row.generator_config || {}
  row.generator_config_value = getGeneratorConfigValue(row)
  row.preview_value = undefined
  row.preview_message = ''
}

export function normalizeEnumFieldForSave(row: FieldRow, generatorConfig: GeneratorConfig) {
  const options = getEnumOptionRows({ ...row, generator_config: generatorConfig })
  const values = options.map((option: EnumOption) => castEnumValue(option.value, row.platform_type))
  row.enum_values = values
  generatorConfig.values = values
  generatorConfig.options = options.map((option: EnumOption, index: number) => ({
    label: option.label || String(values[index]),
    value: values[index],
  }))
  if (
    generatorConfig.value !== undefined &&
    generatorConfig.value !== null &&
    generatorConfig.value !== ''
  ) {
    generatorConfig.value = castEnumValue(generatorConfig.value, row.platform_type)
  } else if (values.length) {
    generatorConfig.value = values[0]
  }
}

export function getGeneratorConfigValue(row: FieldRecord) {
  const config = row.generator_config || {}
  if (config.value !== undefined && config.value !== null) {
    return String(config.value)
  }
  if (row.generator_type === GENERATOR_TYPE_SKIP) {
    return config.reason || '数据库生成'
  }
  if (row.generator_type === GENERATOR_TYPE_DEPENDENCY_FIELD) {
    const targetField = config.field || 'id'
    if (config.alias) {
      return `${config.alias}.${targetField}`
    }
    if (config.dependency_entity_id) {
      return `entity:${config.dependency_entity_id}.${targetField}`
    }
    return `请选择依赖实体.${targetField}`
  }
  if (row.generator_type === GENERATOR_TYPE_ENUM) {
    if (config.value !== undefined && config.value !== null) {
      return String(config.value)
    }
    return ''
  }
  return ''
}

export function isReadonlyGeneratorConfig(row: FieldRow) {
  return [
    GENERATOR_TYPE_SKIP,
    GENERATOR_TYPE_RANDOM_STRING,
    GENERATOR_TYPE_RANDOM_INTEGER,
    GENERATOR_TYPE_RANDOM_DECIMAL,
    GENERATOR_TYPE_NOW,
    GENERATOR_TYPE_RELATIVE_TIME,
    GENERATOR_TYPE_UUID,
    GENERATOR_TYPE_DEPENDENCY_FIELD,
  ].includes(row.generator_type)
}

export function getGeneratorConfigPlaceholder(row: FieldRow) {
  if (isReadonlyGeneratorConfig(row)) {
    return '自动生成'
  }
  if (row.generator_type === GENERATOR_TYPE_FIXED) {
    return '输入值'
  }
  if (row.generator_type === GENERATOR_TYPE_ENUM) {
    return '选枚举'
  }
  if (row.generator_type === GENERATOR_TYPE_FUNCTION) {
    return '测试方法'
  }
  return '生成配置'
}
