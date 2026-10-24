<template>
  <div class="mango-excel-assertion-editor">
    <div class="mango-excel-assertion-editor__head">
      <div>
        <div class="mango-excel-assertion-editor__title">Excel 断言配置</div>
        <div class="mango-excel-assertion-editor__description">
          文件路径支持绝对路径、下载地址或缓存表达式
        </div>
      </div>
      <a-tag size="small">{{ methodLabel }}</a-tag>
    </div>

    <div
      v-for="section in sections"
      :key="section.field"
      class="mango-excel-assertion-editor__section"
    >
      <div class="mango-excel-assertion-editor__section-title">{{ section.title }}</div>
      <a-form-item
        v-for="field in section.fields"
        :key="`${section.field}-${field.key}`"
        :label="field.key"
        required
      >
        <a-textarea
          v-if="field.inputType === 'json'"
          :model-value="displayFieldValue(section.field, field)"
          :disabled="disabled"
          :auto-size="{ minRows: 3, maxRows: 6 }"
          :placeholder="field.placeholder"
          allow-clear
          @update:model-value="updateFieldValue(section.field, field, $event)"
        />
        <a-input
          v-else
          :model-value="displayFieldValue(section.field, field)"
          :disabled="disabled"
          :placeholder="field.placeholder"
          allow-clear
          @update:model-value="updateFieldValue(section.field, field, $event)"
        />
      </a-form-item>

      <a-form-item v-if="section.field === 'actual' && fileOptions.length" label="测试文件">
        <a-cascader
          :model-value="selectedFileValue"
          :disabled="disabled"
          :loading="fileLoading"
          :options="fileOptions"
          placeholder="可选：从测试文件中选择 Excel"
          allow-clear
          allow-search
          expand-trigger="hover"
          path-mode
          @change="selectTestFile" data-testid="qa-components-forms-excelassertioneditor-cascader-可选-从测试文件中选择-excel"
        />
      </a-form-item>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { getUiUploadFileValueFromCascader } from '@/utils/ui-test-file'

  type AssertionField = 'actual' | 'expect'

  interface MethodParameter {
    f?: string
    n?: string
    v?: unknown
  }

  interface EditorField {
    key: string
    placeholder: string
    inputType: 'input' | 'json'
  }

  const props = withDefaults(
    defineProps<{
      methodKey: string
      methodLabel?: string
      parameters?: MethodParameter[]
      actualValue?: unknown
      expectValue?: unknown
      disabled?: boolean
      fileOptions?: any[]
      fileLoading?: boolean
    }>(),
    {
      methodLabel: 'Excel 断言',
      parameters: () => [],
      actualValue: '',
      expectValue: '',
      disabled: false,
      fileOptions: () => [],
      fileLoading: false,
    }
  )

  const emit = defineEmits<{
    (event: 'update:actualValue', value: string): void
    (event: 'update:expectValue', value: string): void
  }>()

  function parseObject(value: unknown): Record<string, any> {
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      return { ...(value as Record<string, any>) }
    }
    if (typeof value !== 'string' || !value.trim()) return {}
    try {
      const parsed = JSON.parse(value)
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
    } catch {
      return {}
    }
  }

  function normalizeSchema(field: AssertionField, value: unknown): Record<string, string> {
    const schema = parseObject(value)
    if (
      props.methodKey === 'assert_excel_column_count' &&
      field === 'expect' &&
      schema['预期行数'] &&
      !schema['预期列数']
    ) {
      schema['预期列数'] = String(schema['预期行数'])
      delete schema['预期行数']
    }
    return Object.fromEntries(
      Object.entries(schema).map(([key, placeholder]) => [key, String(placeholder ?? '')])
    )
  }

  function inputType(key: string, placeholder: string): EditorField['inputType'] {
    const jsonKeywords = ['JSON', 'json', '列表', '行数据', '表头']
    return jsonKeywords.some((keyword) => key.includes(keyword) || placeholder.includes(keyword))
      ? 'json'
      : 'input'
  }

  const sections = computed(() =>
    (['actual', 'expect'] as AssertionField[])
      .map((field) => {
        const parameter = props.parameters.find((item) => item?.f === field)
        const schema = normalizeSchema(field, parameter?.v)
        return {
          field,
          title: field === 'actual' ? '文件设置' : '断言条件',
          fields: Object.entries(schema).map(([key, placeholder]) => ({
            key,
            placeholder,
            inputType: inputType(key, placeholder),
          })),
        }
      })
      .filter((section) => section.fields.length)
  )

  function valueObject(field: AssertionField) {
    return parseObject(field === 'actual' ? props.actualValue : props.expectValue)
  }

  function fieldValue(field: AssertionField, item: EditorField) {
    const value = valueObject(field)[item.key]
    if (value === item.placeholder && item.placeholder.startsWith('请输入')) return ''
    if (value === undefined || value === null) {
      return item.placeholder.startsWith('请输入') ? '' : item.placeholder
    }
    return value
  }

  function displayFieldValue(field: AssertionField, item: EditorField): string {
    const value = fieldValue(field, item)
    if (typeof value === 'string') return value
    if (value === undefined || value === null) return ''
    try {
      return JSON.stringify(value, null, 2)
    } catch {
      return String(value)
    }
  }

  function parsedInputValue(item: EditorField, value: string) {
    if (item.inputType !== 'json' || !value.trim()) return value
    try {
      return JSON.parse(value)
    } catch {
      return value
    }
  }

  function emitObject(field: AssertionField, value: Record<string, any>) {
    const serialized = JSON.stringify(value)
    if (field === 'actual') emit('update:actualValue', serialized)
    else emit('update:expectValue', serialized)
  }

  function updateFieldValue(field: AssertionField, item: EditorField, value: string) {
    emitObject(field, {
      ...valueObject(field),
      [item.key]: parsedInputValue(item, value),
    })
  }

  const selectedFileValue = computed(() => {
    const filePath = String(valueObject('actual')['文件路径'] || '')
    const matched = filePath.match(/^\$\{\{get_file_by_id\((.+)\)\}\}$/)
    if (!matched) return []
    const target = `file:${matched[1]}`
    const findPath = (options: any[], parentPath: string[] = []): string[] => {
      for (const option of options || []) {
        const currentPath = [...parentPath, option.value]
        if (option.value === target) return currentPath
        const childPath = findPath(option.children || [], currentPath)
        if (childPath.length) return childPath
      }
      return []
    }
    return findPath(props.fileOptions)
  })

  function selectTestFile(value: any) {
    if (!value) return
    const fileValue = getUiUploadFileValueFromCascader(value, props.fileOptions)
    const filePath = fileValue?.local_path || fileValue?.download_url
    if (!filePath) return
    emitObject('actual', {
      ...valueObject('actual'),
      文件路径: filePath,
    })
  }

  function validate() {
    for (const section of sections.value) {
      for (const item of section.fields) {
        const value = fieldValue(section.field, item)
        if (value === '' || value === undefined || value === null) {
          Message.error(`请填写 Excel 断言的“${item.key}”`)
          return false
        }
        if (item.inputType === 'json' && typeof value === 'string') {
          try {
            JSON.parse(value)
          } catch {
            Message.error(`Excel 断言的“${item.key}”不是有效的 JSON`)
            return false
          }
        }
      }
    }
    return true
  }

  defineExpose({ validate })
</script>

<style scoped>
  .mango-excel-assertion-editor {
    margin-top: 8px;
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }

  .mango-excel-assertion-editor__head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 10px;
  }

  .mango-excel-assertion-editor__title,
  .mango-excel-assertion-editor__section-title {
    color: var(--m-text);
    font-weight: 600;
  }

  .mango-excel-assertion-editor__description {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-excel-assertion-editor__section + .mango-excel-assertion-editor__section {
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid var(--m-border);
  }

  .mango-excel-assertion-editor__section-title {
    margin-bottom: 6px;
    font-size: 12px;
  }
</style>
