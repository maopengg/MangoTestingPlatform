<template>
  <a-modal
    v-model:visible="enumEditorVisible"
    :on-before-ok="saveEnumOptions"
    :title="`${name || ''} 枚举配置`"
    :width="620"
    unmount-on-close
    @cancel="close"
  >
    <a-space direction="vertical" fill>
      <div class="mango-enum-editor-tip">
        枚举值会按字段平台类型转换后保存。比如 integer 字段中输入 1，会保存为数字 1。
      </div>
      <a-grid
        v-for="(option, index) in enumOptionRows"
        :key="index"
        class="mango-enum-option-row"
        :cols="24"
        :col-gap="8"
        align="center"
      >
        <a-grid-item :span="3">
          <span class="mango-enum-option-label">显示文案</span>
        </a-grid-item>
        <a-grid-item :span="7">
          <a-input v-model="option.label" />
        </a-grid-item>
        <a-grid-item :span="3">
          <span class="mango-enum-option-label">入库值</span>
        </a-grid-item>
        <a-grid-item :span="7">
          <a-input v-model="option.value" />
        </a-grid-item>
        <a-grid-item :span="4">
          <a-button
            size="mini"
            status="danger"
            type="text"
            @click="removeEnumOption(index)"
            data-testid="qa-views-data-factory-entity-button-删除"
          >
            删除
          </a-button>
        </a-grid-item>
      </a-grid>
      <a-button
        type="dashed"
        @click="addEnumOption"
        data-testid="qa-views-data-factory-entity-button-新增枚举项"
        >新增枚举项</a-button
      >
    </a-space>
  </a-modal>
</template>
<script setup lang="ts">
  import { ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { getEnumOptionRows, formatPreviewValue, castEnumValue } from '../generators'
  import { useEntityScope } from '../composables/useEntityScope'
  import type { FieldRow, EnumOption } from '../types'
  const emit = defineEmits<{ (event: 'apply', name: string, options: EnumOption[]): void }>()
  const enumEditorVisible = ref(false),
    name = ref<string | null>(null),
    platformType = ref('')
  const enumOptionRows = ref<Array<{ label: string; value: string }>>([])
  const scope = useEntityScope(close)
  function open(row: FieldRow) {
    if (!scope.isActive()) return
    name.value = row.name
    platformType.value = row.platform_type || ''
    enumOptionRows.value = getEnumOptionRows(row).map((option) => ({
      label: option.label,
      value: formatPreviewValue(option.value),
    }))
    if (!enumOptionRows.value.length) enumOptionRows.value = [{ label: '', value: '' }]
    enumEditorVisible.value = true
  }
  function close() {
    enumEditorVisible.value = false
    name.value = null
    enumOptionRows.value = []
  }
  function addEnumOption() {
    enumOptionRows.value.push({ label: '', value: '' })
  }
  function removeEnumOption(index: number) {
    enumOptionRows.value.splice(index, 1)
  }
  function saveEnumOptions(): boolean {
    if (!enumEditorVisible.value || name.value === null || !scope.isActive()) return false
    const options = enumOptionRows.value
      .filter((option) => option.value !== '')
      .map((option) => {
        const value = castEnumValue(option.value, platformType.value)
        return { label: option.label || String(value), value }
      })
    if (options.some((option) => typeof option.value === 'number' && Number.isNaN(option.value))) {
      Message.error('枚举值类型不合法，请按字段平台类型填写')
      return false
    }
    if (!options.length) {
      Message.error('请至少配置一个枚举项')
      return false
    }
    emit('apply', name.value, options)
    close()
    return true
  }
  defineExpose({ open, close })
</script>
<style scoped>
  .mango-enum-editor-tip {
    background: var(--m-surface-soft);
    border-left: 3px solid var(--m-border-strong);
    border-radius: 3px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 20px;
    padding: 6px 10px;
  }

  .mango-enum-option-row {
    margin-bottom: 6px;
  }

  .mango-enum-option-label {
    color: var(--m-text-2);
    display: inline-block;
    font-size: 14px;
    line-height: 18px;
    white-space: nowrap;
  }
</style>
