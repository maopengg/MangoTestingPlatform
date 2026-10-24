<template>
  <div
    class="mango-key-value-container"
    :class="{
      'mango-key-value-container--environment': layout === 'environment-key-value',
      'mango-key-value-container--assertion': layout === 'assertion',
    }"
  >
    <div v-for="(item, index) in dataList" :key="index" class="mango-key-value-item">
      <div class="mango-key-value-row">
        <!-- 支持多个字段的展示 -->
        <div
          v-for="(field, fieldIndex) in getVisibleFields(item)"
          :key="fieldIndex"
          class="mango-key-value-field"
          :class="field.containerClassName"
        >
          <span class="mango-field-label">{{ getFieldLabel(field, item) }}:</span>
          <!-- 支持级联选择器 -->
          <a-cascader
            v-if="field.type === 'cascader'"
            v-model="item[field.field]"
            :options="field.options || []"
            :placeholder="getFieldPlaceholder(field, item, '请选择')"
            :expand-trigger="field.expandTrigger || 'hover'"
            :value-key="field.valueKey || 'key'"
            @change="(value) => field.onChange && field.onChange(value, dataList, index)"
            :class="field.className || 'mango-key-cascader'"
          />
          <a-select
            v-else-if="field.type === 'select' && field.field"
            :model-value="getFieldModelValue(field, item)"
            :allow-clear="getSelectAllowClear(field)"
            :options="field.options || []"
            :placeholder="getFieldPlaceholder(field, item, '请选择')"
            :field-names="field.fieldNames"
            :multiple="field.multiple"
            :max-tag-count="getSelectMaxTagCount(field)"
            :class="field.className || 'mango-key-select'"
            @change="(value) => onSelectChange(field, value, item, index)"
            @popup-visible-change="(visible) => onSelectPopupVisibleChange(field, visible, index)"
          />
          <a-tooltip
            v-else-if="field.type === 'input' && field.field"
            :content="getFieldTitle(field, item)"
            :disabled="!getFieldTitle(field, item)"
            class="mango-key-value-tooltip"
          >
            <a-input
              v-model="item[field.field]"
              :placeholder="getFieldPlaceholder(field, item, '请输入')"
              @blur="onBlur"
              :class="field.className || 'mango-key-input'"
            />
          </a-tooltip>
          <!-- 支持文本域 -->
          <a-tooltip
            v-else-if="field.field"
            :content="getFieldTitle(field, item)"
            :disabled="!getFieldTitle(field, item)"
            class="mango-key-value-tooltip"
          >
            <a-textarea
              v-model="item[field.field]"
              :placeholder="getFieldPlaceholder(field, item, '请输入')"
              :auto-size="field.autoSize || { minRows: 1, maxRows: 3 }"
              @blur="onBlur"
              :class="field.className || 'mango-key-input'"
            />
          </a-tooltip>
          <!-- 支持数组直接绑定的情况 -->
          <a-textarea
            v-else
            :model-value="item"
            :placeholder="getFieldPlaceholder(field, item, '请输入')"
            :auto-size="field.autoSize || { minRows: 1, maxRows: 3 }"
            @blur="(event) => onItemBlur(event, index)"
            @update:model-value="(value) => onItemUpdate(value, index, item)"
            :class="field.className || 'mango-key-input'"
          />
        </div>
        <!-- 按钮容器，确保按钮在同一行 -->
        <div class="mango-button-container">
          <!-- 插槽支持额外操作按钮 -->
          <slot name="extra" :index="index" :item="item"></slot>
          <a-button
            size="small"
            status="danger"
            type="text"
            @click="onDelete(index)"
            class="mango-remove-btn" data-testid="qa-components-forms-keyvaluelist-button-移除"
          >
            移除
          </a-button>
        </div>
      </div>
    </div>
    <div v-if="!dataList || dataList.length === 0" class="mango-empty-placeholder">
      {{ emptyText }}
    </div>
  </div>
</template>

<script lang="ts" setup>
  // 定义字段配置接口
  interface FieldConfig {
    field?: string // 字段名（可选，为空时表示直接绑定数组元素）
    label: string | ((item: any) => string) // 显示标签
    className?: string // 自定义类名
    containerClassName?: string // 自定义字段容器类名
    placeholder?: string | ((item: any) => string) // 占位符文本
    type?: 'input' | 'textarea' | 'cascader' | 'select' // 字段类型
    // 级联选择器特有属性
    options?: any[] // 选项数据
    expandTrigger?: 'click' | 'hover' // 次级菜单展开方式
    valueKey?: string // 选项值的键名
    fieldNames?: any
    allowClear?: boolean
    multiple?: boolean
    maxTagCount?: number
    onChange?: (value: any, item: any, index: number) => void // 值改变时的回调
    getValue?: (item: any) => any
    setValue?: (value: any, item: any, index: number) => void
    autoSize?: { minRows: number; maxRows: number } // 文本域自动调整大小
    visible?: (item: any) => boolean // 控制字段是否展示
    showTitle?: boolean // hover 时展示完整值
  }

  // 定义组件属性
  interface Props {
    dataList: any[] // 数据列表
    fieldConfig: FieldConfig[] // 字段配置数组
    emptyText?: string // 空状态文本
    onDeleteItem: (index: number) => void // 删除回调
    onSave?: () => void // 保存回调（可选）
    layout?: 'default' | 'environment-key-value' | 'assertion'
  }

  // 定义事件
  const emit = defineEmits<{
    (e: 'update:item', index: number, value: any, item: any): void
  }>()

  // 定义默认属性
  const props = withDefaults(defineProps<Props>(), {
    emptyText: '暂无数据，点击上方"增加"按钮添加',
    layout: 'default',
  })
  const openedSelectKeys = new Set<string>()
  const pendingSelectSaveKeys = new Set<string>()

  const getSelectStateKey = (field: FieldConfig, index: number) =>
    `${field.field || 'array'}:${index}`

  const getVisibleFields = (item: any) => {
    return props.fieldConfig.filter((field) => !field.visible || field.visible(item))
  }

  const getFieldLabel = (field: FieldConfig, item: any) => {
    return typeof field.label === 'function' ? field.label(item) : field.label
  }

  const getFieldPlaceholder = (field: FieldConfig, item: any, prefix: string) => {
    if (typeof field.placeholder === 'function') {
      return field.placeholder(item)
    }
    return field.placeholder || `${prefix}${getFieldLabel(field, item)}`
  }

  const getFieldModelValue = (field: FieldConfig, item: any) => {
    if (field.getValue) {
      return field.getValue(item)
    }
    return item[field.field as string]
  }

  const getSelectMaxTagCount = (field: FieldConfig) => {
    if (field.maxTagCount !== undefined) return field.maxTagCount
    if (props.layout === 'environment-key-value' && field.field === 'test_envs') return 1
    return undefined
  }

  const getSelectAllowClear = (field: FieldConfig) => {
    if (field.allowClear !== undefined) return field.allowClear
    return !(props.layout === 'environment-key-value' && field.field === 'test_envs')
  }

  const getFieldTitle = (field: FieldConfig, item: any) => {
    if (!field.showTitle || !field.field) return undefined
    const value = item[field.field]
    return value === undefined || value === null ? '' : String(value)
  }

  // 删除项
  const onDelete = (index: number) => {
    props.onDeleteItem(index)
  }

  // 失去焦点时触发保存
  const onBlur = () => {
    if (props.onSave) {
      props.onSave()
    }
  }

  const onSelectChange = (field: FieldConfig, value: any, item: any, index: number) => {
    if (field.setValue) {
      field.setValue(value, item, index)
    } else if (field.onChange) {
      field.onChange(value, item, index)
      return
    } else if (field.field) {
      item[field.field] = value
    }

    const stateKey = getSelectStateKey(field, index)
    if (field.multiple && openedSelectKeys.has(stateKey)) {
      pendingSelectSaveKeys.add(stateKey)
      return
    }
    onBlur()
  }

  const onSelectPopupVisibleChange = (
    field: FieldConfig,
    visible: boolean,
    index: number
  ) => {
    if (!field.multiple) return
    const stateKey = getSelectStateKey(field, index)
    if (visible) {
      openedSelectKeys.add(stateKey)
      return
    }
    openedSelectKeys.delete(stateKey)
    if (pendingSelectSaveKeys.delete(stateKey)) {
      onBlur()
    }
  }

  // 数组元素更新时的处理
  const onItemUpdate = (value: any, index: number, item: any) => {
    // 通过事件通知父组件更新数组元素
    emit('update:item', index, value, item)
  }

  // 数组元素失去焦点时的处理
  const onItemBlur = (event: any, index: number) => {
    if (props.onSave) {
      props.onSave()
    }
  }
</script>

<style scoped>
  /* Key-Value 样式 */
  .mango-key-value-container {
    padding: 10px 0;
  }

  .mango-key-value-item {
    margin-bottom: 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    padding: 12px;
    overflow: visible;
    background-color: var(--m-surface);
    transition:
      border-color 0.16s ease,
      box-shadow 0.16s ease,
      background-color 0.16s ease;
  }

  .mango-key-value-item:hover {
    background-color: var(--m-surface-2);
    border-color: var(--m-primary-border);
    box-shadow: var(--m-shadow-soft);
  }

  .mango-key-value-container--environment {
    width: 100%;
    min-width: 480px;
  }

  .mango-key-value-container--environment .mango-key-value-item {
    box-sizing: border-box;
    overflow: hidden;
    padding: 10px;
  }

  .mango-key-value-container--environment .mango-key-value-row {
    display: flex;
    width: 100%;
    min-width: 0;
    gap: 8px;
  }

  .mango-key-value-container--environment .mango-case-custom-env-field {
    flex: 0 0 135px;
    min-width: 135px;
    max-width: 135px;
  }

  .mango-key-value-container--environment
    .mango-case-custom-env-field
    :deep(.arco-select-view-multiple) {
    height: 32px;
    min-height: 32px;
    align-items: center;
    overflow: hidden;
  }

  .mango-key-value-container--environment
    .mango-case-custom-env-field
    :deep(.arco-select-view-inner.arco-select-view-nowrap) {
    min-width: 0;
    flex-wrap: nowrap;
    align-items: center;
  }

  .mango-key-value-container--environment
    .mango-case-custom-env-field
    :deep(.arco-select-view-tag) {
    min-width: 0;
    flex: 0 1 auto;
    white-space: nowrap;
  }

  .mango-key-value-container--environment
    .mango-case-custom-env-field
    :deep(.arco-select-view-input) {
    width: 0;
    min-width: 0;
    flex: 0 0 0;
  }

  .mango-key-value-container--environment
    .mango-case-custom-env-field
    :deep(.arco-select-view-suffix) {
    padding-left: 4px;
  }

  .mango-key-value-container--environment .mango-case-custom-key-field {
    flex: 0 1 76px;
    min-width: 64px;
  }

  .mango-key-value-container--environment .mango-case-custom-value-field {
    flex: 1 1 140px;
    width: auto;
    min-width: 112px;
    max-width: none;
  }

  .mango-key-value-container--environment
    .mango-case-custom-key-input
    :deep(.arco-input),
  .mango-key-value-container--environment
    .mango-case-custom-value-input
    :deep(.arco-input) {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-key-value-container--environment .mango-button-container {
    flex: 0 0 40px;
    min-width: 40px;
    justify-content: center;
  }

  .mango-key-value-container--environment .mango-remove-btn {
    padding: 0 4px;
  }

  .mango-key-value-row {
    display: inline-flex;
    align-items: flex-start;
    gap: 12px;
    flex-wrap: nowrap; /* 防止换行 */
    width: max-content;
    min-width: 100%;
    overflow-x: visible;
  }

  .mango-key-value-container--assertion .mango-key-value-item {
    box-sizing: border-box;
    min-width: 0;
  }

  .mango-key-value-container--assertion .mango-key-value-row {
    display: flex;
    width: 100%;
    min-width: 0;
    flex-wrap: wrap;
    gap: var(--m-space-sm);
  }

  .mango-key-value-container--assertion .mango-key-value-field {
    min-width: 0;
    flex: 1 1 180px;
  }

  .mango-key-value-container--assertion .mango-button-container {
    margin-left: auto;
    align-self: flex-end;
  }

  .mango-key-value-container--assertion .mango-remove-btn {
    margin-top: 0;
  }

  .mango-key-value-field {
    flex: 1 0 160px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 120px;
    overflow: hidden; /* 防止内容溢出 */
  }

  .mango-button-container {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    flex-shrink: 0; /* 防止按钮容器被压缩 */
    white-space: nowrap; /* 防止按钮内文字换行 */
    min-width: fit-content; /* 确保按钮容器不会收缩 */
  }

  .mango-field-label {
    font-size: 12px;
    color: var(--m-muted);
    font-weight: 500;
    flex-shrink: 0; /* 防止标签被压缩 */
  }

  .mango-key-input,
  .value-input,
  .sql-input,
  .mango-key-cascader,
  .mango-key-select {
    width: 100%;
    min-width: 0; /* 允许输入框收缩 */
  }

  .mango-key-value-tooltip,
  .mango-key-value-tooltip :deep(.arco-trigger),
  .mango-key-value-tooltip :deep(.arco-input-wrapper),
  .mango-key-value-tooltip :deep(.arco-textarea-wrapper) {
    width: 100%;
    min-width: 0;
  }

  .mango-remove-btn {
    align-self: flex-start;
    margin-top: 18px;
    flex-shrink: 0; /* 防止按钮被压缩 */
  }

  /* 确保插槽中的按钮也正确对齐 */
  :deep(.mango-button-container .arco-btn) {
    align-self: flex-start;
    margin-top: 18px;
    flex-shrink: 0; /* 防止按钮被压缩 */
    min-width: fit-content; /* 确保按钮不会收缩 */
  }

  .mango-key-value-container--assertion :deep(.mango-button-container .arco-btn) {
    margin-top: 0;
  }

  .mango-empty-placeholder {
    text-align: center;
    color: var(--m-muted);
    font-size: 14px;
    padding: 20px;
    border: 1px dashed var(--m-border);
    border-radius: var(--m-radius-md);
    margin-top: 10px;
    background: var(--m-surface-soft);
  }

  /* 响应式处理：在小屏幕上允许换行，但保持按钮在同一行 */
  @media (max-width: 1px) {
    .mango-key-value-row {
      flex-wrap: wrap;
    }

    .mango-key-value-field {
      min-width: 120px;
    }

    .mango-button-container {
      width: 100%;
      justify-content: flex-end;
      margin-top: 8px;
    }

    .mango-remove-btn {
      margin-top: 0;
      align-self: center;
    }

    /* 确保插槽中的按钮在小屏幕上也正确对齐 */
    :deep(.mango-button-container .arco-btn) {
      margin-top: 0;
      align-self: center;
    }
  }
</style>
