<template>
  <a-table
    :columns="columns"
    :data="rows"
    :pagination="false"
    :row-key="'name'"
    :scroll="{ x: 1120, y: 420 }"
    size="small"
  >
    <template #columns>
      <a-table-column
        v-for="item of columns"
        :key="item.key"
        :data-index="item.key"
        :ellipsis="item.ellipsis"
        :tooltip="item.tooltip"
        :title="item.title"
        :width="item.width"
      >
        <template v-if="item.key === 'default_generator_type'" #cell="{ record }">
          <a-tag :color="enumStore.colors[record.generator_type]" size="small">
            {{ enumTitle(record.generator_type) }}
          </a-tag>
        </template>
        <template v-else-if="item.key === 'override_generator_type'" #cell="{ record }">
          <a-select
            :model-value="getOverrideType(record)"
            :options="overrideTypeOptions"
            :field-names="{ value: 'key', label: 'title' }"
            :disabled="readonly"
            allow-clear
            placeholder="不覆盖"
            @change="(value) => changeOverrideType(record, value)"
          />
        </template>
        <template v-else-if="item.key === 'override_config'" #cell="{ record }">
          <a-select
            v-if="isEnumConfig(record)"
            :model-value="getEffectiveEnumValue(record)"
            :options="getEnumSelectOptions(record)"
            :disabled="readonly"
            allow-clear
            placeholder="请选择枚举值"
            @change="(value) => changeEnumOverrideValue(record, value)"
          />
          <a-input
            v-else
            :disabled="readonly || isDisabledConfig(record)"
            :model-value="getConfigInputValue(record)"
            :placeholder="getConfigPlaceholder(record)"
            allow-clear
            @input="(value) => changeOverrideConfigValue(record, value)"
          />
        </template>
        <template v-else-if="item.key === 'output_enabled'" #cell="{ record }">
          <a-switch
            :model-value="isOutputEnabled(record)"
            :disabled="readonly"
            size="small"
            @change="(value) => changeOutputEnabled(record, value)"
          />
        </template>
        <template v-else-if="item.key === 'output_key'" #cell="{ record }">
          <a-input
            :disabled="readonly || !isOutputEnabled(record)"
            :model-value="getOutputKey(record)"
            allow-clear
            placeholder="输出名称"
            @input="(value) => changeOutputKey(record, value)"
          />
        </template>
        <template v-else-if="item.key === 'preview_value'" #cell="{ record }">
          {{ formatPreviewValue(getPreviewItem(record)?.value) }}
        </template>
        <template v-else-if="item.key === 'preview_valid'" #cell="{ record }">
          <a-tag :color="getPreviewItem(record)?.valid ? 'green' : 'red'">
            {{ getPreviewItem(record)?.valid ? '正常' : '需配置' }}
          </a-tag>
        </template>
        <template v-else-if="item.key === 'preview_message'" #cell="{ record }">
          {{ getPreviewItem(record)?.message || '-' }}
        </template>
      </a-table-column>
    </template>
  </a-table>
</template>

<script lang="ts" setup>
  import type {
    DataFactoryFieldOverrideRule,
    DataFactoryFieldOverrides,
    DataFactoryFieldRule,
    DataFactoryOutputConfig,
  } from '@/types/data-factory'
  import { computed } from 'vue'
  import { useEnum } from '@/store/modules/get-enum'

  interface EnumOption {
    key: number | null
    title: string
  }

  const props = withDefaults(
    defineProps<{
      fields: DataFactoryFieldRule[]
      fieldOverrides: DataFactoryFieldOverrides
      outputConfig: DataFactoryOutputConfig
      generatorOptions: EnumOption[]
      previewFields?: any[]
      readonly?: boolean
      showConfig?: boolean
      showOutput?: boolean
      showPreview?: boolean
    }>(),
    {
      previewFields: () => [],
      readonly: false,
      showConfig: true,
      showOutput: true,
      showPreview: false,
    }
  )

  const emit = defineEmits<{
    (event: 'update:fieldOverrides', value: DataFactoryFieldOverrides): void
    (event: 'update:outputConfig', value: DataFactoryOutputConfig): void
  }>()

  const GENERATOR_TYPE_SKIP = 0
  const GENERATOR_TYPE_FIXED = 1
  const GENERATOR_TYPE_RANDOM_STRING = 2
  const GENERATOR_TYPE_RANDOM_INTEGER = 3
  const GENERATOR_TYPE_RANDOM_DECIMAL = 4
  const GENERATOR_TYPE_NOW = 5
  const GENERATOR_TYPE_RELATIVE_TIME = 6
  const GENERATOR_TYPE_UUID = 7
  const GENERATOR_TYPE_ENUM = 9
  const GENERATOR_TYPE_DEPENDENCY_FIELD = 11
  const GENERATOR_TYPE_FUNCTION = 13
  const REMOVED_GENERATOR_TYPES = [8, 10, 12]
  const enumStore = useEnum()

  const columns = computed(() =>
    [
      {
        title: '字段',
        key: 'name',
        dataIndex: 'name',
        width: 200,
        align: 'left',
        ellipsis: true,
        tooltip: true,
        group: 'base',
      },
      {
        title: '说明',
        key: 'label',
        dataIndex: 'label',
        width: 160,
        align: 'left',
        ellipsis: true,
        tooltip: true,
        group: 'base',
      },
      {
        title: '默认生成方式',
        key: 'default_generator_type',
        dataIndex: 'default_generator_type',
        width: 150,
        group: 'config',
      },
      {
        title: '模板生成方式',
        key: 'override_generator_type',
        dataIndex: 'override_generator_type',
        width: 170,
        group: 'config',
      },
      {
        title: '生成配置',
        key: 'override_config',
        dataIndex: 'override_config',
        width: 260,
        group: 'config',
      },
      {
        title: '输出',
        key: 'output_enabled',
        dataIndex: 'output_enabled',
        width: 80,
        group: 'output',
      },
      {
        title: '输出名称',
        key: 'output_key',
        dataIndex: 'output_key',
        width: 180,
        group: 'output',
      },
      {
        title: '生成值（模拟）',
        key: 'preview_value',
        dataIndex: 'preview_value',
        width: 180,
        align: 'left',
        ellipsis: true,
        tooltip: true,
        group: 'preview',
      },
      {
        title: '状态',
        key: 'preview_valid',
        dataIndex: 'preview_valid',
        width: 110,
        group: 'preview',
      },
      {
        title: '结果说明',
        key: 'preview_message',
        dataIndex: 'preview_message',
        width: 180,
        align: 'left',
        ellipsis: true,
        tooltip: true,
        group: 'preview',
      },
    ].filter((item) => {
      if (item.group === 'config' && !props.showConfig) {
        return false
      }
      if (item.group === 'output' && !props.showOutput) {
        return false
      }
      if (item.group === 'preview' && !props.showPreview) {
        return false
      }
      return true
    })
  )

  const rows = computed(() => props.fields || [])
  const generatorOptions = computed(() =>
    (props.generatorOptions || [])
      .filter((item) => !REMOVED_GENERATOR_TYPES.includes(Number(item.key)))
      .map((item) => ({
        ...item,
        title: getGeneratorTypeTitle(item),
      }))
  )
  const overrideTypeOptions = computed(() => [
    { key: null, title: '不覆盖' },
    ...generatorOptions.value,
  ])

  function enumTitle(value: any) {
    const title = generatorOptions.value.find(
      (it) => Number(it.key) === normalizeGeneratorType(value)
    )?.title
    return title || (value ?? '-')
  }

  function getGeneratorTypeTitle(option: EnumOption) {
    const titleMap: Record<number, string> = {
      [GENERATOR_TYPE_RANDOM_STRING]: '随机字符串（长度8）',
      [GENERATOR_TYPE_RANDOM_INTEGER]: '随机整数（1-100）',
      [GENERATOR_TYPE_RANDOM_DECIMAL]: '随机小数（1-100，2位）',
    }
    return titleMap[Number(option.key)] || option.title
  }

  function getOverrideRule(row: DataFactoryFieldRule): DataFactoryFieldOverrideRule | undefined {
    return props.fieldOverrides?.[row.name]
  }

  function getOverrideType(row: DataFactoryFieldRule) {
    const generatorType = getOverrideRule(row)?.generator_type
    return generatorType === undefined || generatorType === null
      ? null
      : normalizeGeneratorType(generatorType)
  }

  function updateOverride(row: DataFactoryFieldRule, rule?: DataFactoryFieldOverrideRule) {
    const next: DataFactoryFieldOverrides = { ...(props.fieldOverrides || {}) }
    if (!rule) {
      delete next[row.name]
    } else {
      next[row.name] = rule
    }
    emit('update:fieldOverrides', next)
  }

  function changeOverrideType(row: DataFactoryFieldRule, value: any) {
    if (value === null || value === undefined || value === '') {
      updateOverride(row)
      return
    }
    updateOverride(row, {
      generator_type: Number(value),
      generator_config: buildDefaultConfig(Number(value), row),
    })
  }

  function buildDefaultConfig(generatorType: number, row: DataFactoryFieldRule) {
    const normalizedType = normalizeGeneratorType(generatorType)
    if (normalizedType === GENERATOR_TYPE_SKIP) {
      return { reason: '模板跳过' }
    }
    if (normalizedType === GENERATOR_TYPE_DEPENDENCY_FIELD) {
      return { template_id: null, field: 'id', strategy: 'reuse_or_create' }
    }
    if (normalizedType === GENERATOR_TYPE_FIXED) {
      return { value: '' }
    }
    if (normalizedType === GENERATOR_TYPE_ENUM) {
      return buildEnumGeneratorConfig(row)
    }
    return { ...(row.generator_config || {}) }
  }

  function normalizeGeneratorType(value: any) {
    if (value === null || value === undefined || value === '') {
      return null
    }
    const numberValue = Number(value)
    return Number.isNaN(numberValue) ? value : numberValue
  }

  function getEnumOptionRows(row: DataFactoryFieldRule) {
    const overrideConfig = getOverrideRule(row)?.generator_config || {}
    const sourceConfig = Object.keys(overrideConfig).length
      ? overrideConfig
      : row.generator_config || {}
    const optionRows = Array.isArray(sourceConfig.options) ? sourceConfig.options : []
    if (optionRows.length) {
      return optionRows.map((option: any) => ({
        label: option.label ?? String(option.value ?? ''),
        value: option.value,
      }))
    }
    const values = sourceConfig.values || row.enum_values || []
    return values.map((value: any) => ({
      label: String(value),
      value,
    }))
  }

  function getEnumSelectOptions(row: DataFactoryFieldRule) {
    return getEnumOptionRows(row).map((option: any) => ({
      label: `${option.label}（${formatValue(option.value)}）`,
      value: option.value,
    }))
  }

  function buildEnumGeneratorConfig(row: DataFactoryFieldRule, value?: any) {
    const options = getEnumOptionRows(row)
    const values = options.map((option: any) => option.value)
    const defaultValue =
      value ??
      getOverrideRule(row)?.generator_config?.value ??
      row.generator_config?.value ??
      values[0]
    return {
      ...(row.generator_config || {}),
      values,
      options,
      value: defaultValue,
    }
  }

  function isEnumConfig(row: DataFactoryFieldRule) {
    const overrideType = getOverrideType(row)
    return overrideType === GENERATOR_TYPE_ENUM
  }

  function getEffectiveEnumValue(row: DataFactoryFieldRule) {
    const override = getOverrideRule(row)
    if (override) {
      return override.generator_config?.value
    }
    return row.generator_config?.value
  }

  function changeEnumOverrideValue(row: DataFactoryFieldRule, value: any) {
    if (value === null || value === undefined || value === '') {
      updateOverride(row)
      return
    }
    updateOverride(row, {
      generator_type: GENERATOR_TYPE_ENUM,
      generator_config: buildEnumGeneratorConfig(row, value),
    })
  }

  function formatValue(value: any) {
    if (value === null || value === undefined) {
      return 'null'
    }
    if (typeof value === 'object') {
      return JSON.stringify(value)
    }
    return String(value)
  }

  function formatPreviewValue(value: any) {
    if (value === null || value === undefined || value === '') {
      return '空'
    }
    return formatValue(value)
  }

  function getPreviewItem(row: DataFactoryFieldRule) {
    return (props.previewFields || []).find((item: any) => item.name === row.name) || row
  }

  function isDisabledConfig(row: DataFactoryFieldRule) {
    const generatorType = getOverrideType(row)
    return [
      null,
      GENERATOR_TYPE_SKIP,
      GENERATOR_TYPE_RANDOM_STRING,
      GENERATOR_TYPE_RANDOM_INTEGER,
      GENERATOR_TYPE_RANDOM_DECIMAL,
      GENERATOR_TYPE_NOW,
      GENERATOR_TYPE_RELATIVE_TIME,
      GENERATOR_TYPE_UUID,
      GENERATOR_TYPE_DEPENDENCY_FIELD,
    ].includes(generatorType)
  }

  function getConfigInputValue(row: DataFactoryFieldRule) {
    if (getOverrideType(row) === null) {
      return getDefaultConfigDisplayValue(row)
    }
    if (isDisabledConfig(row)) {
      return ''
    }
    const config = getOverrideRule(row)?.generator_config || {}
    if (config.value !== undefined && config.value !== null) {
      return String(config.value)
    }
    return ''
  }

  function getDefaultConfigDisplayValue(row: DataFactoryFieldRule) {
    const generatorType = normalizeGeneratorType(row.generator_type)
    const config = row.generator_config || {}
    if (generatorType === GENERATOR_TYPE_ENUM) {
      if (config.value !== undefined && config.value !== null) {
        const option = getEnumOptionRows(row).find((item: any) => item.value === config.value)
        return option
          ? `${option.label}（${formatValue(option.value)}）`
          : formatValue(config.value)
      }
      return ''
    }
    if (config.value !== undefined && config.value !== null) {
      return String(config.value)
    }
    if (generatorType === GENERATOR_TYPE_SKIP) {
      return config.reason || '数据库生成'
    }
    if (generatorType === GENERATOR_TYPE_DEPENDENCY_FIELD) {
      const targetField = config.field || 'id'
      if (config.alias) {
        return `${config.alias}.${targetField}`
      }
      if (config.template_id) {
        return `template:${config.template_id}.${targetField}`
      }
      return `依赖模板.${targetField}`
    }
    return ''
  }

  function getConfigPlaceholder(row: DataFactoryFieldRule) {
    const generatorType = getOverrideType(row)
    if (generatorType === null) {
      return getDefaultConfigDisplayValue(row) || enumTitle(row.generator_type)
    }
    if (isDisabledConfig(row)) {
      return '自动生成'
    }
    if (generatorType === GENERATOR_TYPE_FIXED) {
      return '输入值'
    }
    if (generatorType === GENERATOR_TYPE_ENUM) {
      return '选枚举'
    }
    if (generatorType === GENERATOR_TYPE_FUNCTION) {
      return '测试方法'
    }
    return '生成配置'
  }

  function changeOverrideConfigValue(row: DataFactoryFieldRule, value: string) {
    if (isDisabledConfig(row)) {
      return
    }
    const rule = getOverrideRule(row)
    if (!rule) {
      return
    }
    updateOverride(row, {
      ...rule,
      generator_config: {
        ...(rule.generator_config || {}),
        value,
      },
    })
  }

  function getOutputItem(row: DataFactoryFieldRule) {
    return (props.outputConfig || []).find((item) => item.field === row.name)
  }

  function isOutputEnabled(row: DataFactoryFieldRule) {
    return Boolean(getOutputItem(row))
  }

  function getOutputKey(row: DataFactoryFieldRule) {
    return getOutputItem(row)?.key || row.name
  }

  function changeOutputEnabled(row: DataFactoryFieldRule, value: any) {
    const enabled = Boolean(value)
    const next = (props.outputConfig || []).filter((item) => item.field !== row.name)
    if (enabled) {
      next.push({ field: row.name, key: row.name })
    }
    emit('update:outputConfig', next)
  }

  function changeOutputKey(row: DataFactoryFieldRule, value: string) {
    const next = (props.outputConfig || []).map((item) => {
      if (item.field !== row.name) {
        return item
      }
      return {
        ...item,
        key: value || row.name,
      }
    })
    emit('update:outputConfig', next)
  }
</script>
