<template>
  <a-table
    :columns="columns"
    :data="rows"
    :pagination="false"
    :row-key="'name'"
    size="small"
  >
    <template #columns>
      <a-table-column
        v-for="item of columns"
        :key="item.key"
        :data-index="item.key"
        :title="item.title"
        :width="item.width"
      >
        <template v-if="item.key === 'default_generator_type'" #cell="{ record }">
          {{ enumTitle(record.generator_type) }}
        </template>
        <template v-else-if="item.key === 'override_generator_type'" #cell="{ record }">
          <a-select
            :model-value="getOverrideType(record)"
            :options="overrideTypeOptions"
            :field-names="{ value: 'key', label: 'title' }"
            allow-clear
            placeholder="不覆盖"
            @change="(value) => changeOverrideType(record, value)"
          />
        </template>
        <template v-else-if="item.key === 'override_config'" #cell="{ record }">
          <a-input
            v-if="!isReadonlyConfig(record)"
            :model-value="getOverrideConfigValue(record)"
            :placeholder="getConfigPlaceholder(record)"
            allow-clear
            @input="(value) => changeOverrideConfigValue(record, value)"
          />
          <a-input
            v-else
            :model-value="getReadonlyConfigText(record)"
            readonly
          />
        </template>
        <template v-else-if="item.key === 'nullable'" #cell="{ record }">
          <a-tag :color="record.nullable ? 'gray' : 'orange'">
            {{ record.nullable ? '可空' : '必填' }}
          </a-tag>
        </template>
        <template v-else-if="item.key === 'primary_key'" #cell="{ record }">
          <a-tag :color="record.primary_key ? 'arcoblue' : 'gray'">
            {{ record.primary_key ? '主键' : '普通' }}
          </a-tag>
        </template>
        <template v-else-if="item.key === 'autoincrement'" #cell="{ record }">
          <a-tag :color="record.autoincrement ? 'green' : 'gray'">
            {{ record.autoincrement ? '自增' : '否' }}
          </a-tag>
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
  } from '@/types/data-factory'
  import { computed } from 'vue'

  interface EnumOption {
    key: number | null
    title: string
  }

  const props = defineProps<{
    fields: DataFactoryFieldRule[]
    modelValue: DataFactoryFieldOverrides
    generatorOptions: EnumOption[]
  }>()

  const emit = defineEmits<{
    (event: 'update:modelValue', value: DataFactoryFieldOverrides): void
  }>()

  const GENERATOR_TYPE_SKIP = 0
  const GENERATOR_TYPE_FIXED = 1
  const GENERATOR_TYPE_DEPENDENCY_FIELD = 11

  const columns = [
    { title: '字段', key: 'name', dataIndex: 'name', width: 140 },
    { title: '说明', key: 'label', dataIndex: 'label', width: 150 },
    { title: '默认生成方式', key: 'default_generator_type', dataIndex: 'default_generator_type', width: 130 },
    { title: '覆盖方式', key: 'override_generator_type', dataIndex: 'override_generator_type', width: 170 },
    { title: '覆盖配置', key: 'override_config', dataIndex: 'override_config', width: 260 },
    { title: '可空', key: 'nullable', dataIndex: 'nullable', width: 80 },
    { title: '主键', key: 'primary_key', dataIndex: 'primary_key', width: 80 },
    { title: '自增', key: 'autoincrement', dataIndex: 'autoincrement', width: 80 },
    { title: 'DB类型', key: 'db_type', dataIndex: 'db_type', width: 130 },
    { title: '平台类型', key: 'platform_type', dataIndex: 'platform_type', width: 110 },
  ]

  const rows = computed(() => props.fields || [])
  const overrideTypeOptions = computed(() => [
    { key: null, title: '不覆盖' },
    ...(props.generatorOptions || []),
  ])

  function enumTitle(value: any) {
    const title = props.generatorOptions.find((it) => it.key === value)?.title
    return title || (value ?? '-')
  }

  function getOverrideRule(row: DataFactoryFieldRule): DataFactoryFieldOverrideRule | undefined {
    return props.modelValue?.[row.name]
  }

  function getOverrideType(row: DataFactoryFieldRule) {
    return getOverrideRule(row)?.generator_type ?? null
  }

  function updateOverride(row: DataFactoryFieldRule, rule?: DataFactoryFieldOverrideRule) {
    const next: DataFactoryFieldOverrides = { ...(props.modelValue || {}) }
    if (!rule) {
      delete next[row.name]
    } else {
      next[row.name] = rule
    }
    emit('update:modelValue', next)
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
    if (generatorType === GENERATOR_TYPE_SKIP) {
      return { reason: '模板跳过' }
    }
    if (generatorType === GENERATOR_TYPE_DEPENDENCY_FIELD) {
      return { template_id: null, field: 'id', strategy: 'reuse_or_create' }
    }
    if (generatorType === GENERATOR_TYPE_FIXED) {
      return { value: '' }
    }
    return { ...(row.generator_config || {}) }
  }

  function isReadonlyConfig(row: DataFactoryFieldRule) {
    const generatorType = getOverrideType(row)
    return generatorType === null || generatorType === GENERATOR_TYPE_SKIP || generatorType === GENERATOR_TYPE_DEPENDENCY_FIELD
  }

  function getOverrideConfigValue(row: DataFactoryFieldRule) {
    const config = getOverrideRule(row)?.generator_config || {}
    if (config.value !== undefined && config.value !== null) {
      return String(config.value)
    }
    if (config.expression) {
      return String(config.expression)
    }
    return ''
  }

  function getReadonlyConfigText(row: DataFactoryFieldRule) {
    const generatorType = getOverrideType(row)
    if (generatorType === null) {
      return '使用实体默认规则'
    }
    const config = getOverrideRule(row)?.generator_config || {}
    if (generatorType === GENERATOR_TYPE_SKIP) {
      return config.reason || '模板跳过'
    }
    if (generatorType === GENERATOR_TYPE_DEPENDENCY_FIELD) {
      return JSON.stringify(config)
    }
    return ''
  }

  function getConfigPlaceholder(row: DataFactoryFieldRule) {
    const generatorType = getOverrideType(row)
    if (generatorType === GENERATOR_TYPE_FIXED) {
      return '固定值，留空表示空字符串'
    }
    return '填写 value，例如 ${{character_email()}}'
  }

  function changeOverrideConfigValue(row: DataFactoryFieldRule, value: string) {
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
</script>
