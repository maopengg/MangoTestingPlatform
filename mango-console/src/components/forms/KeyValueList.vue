<template>
  <div class="mango-key-value-container">
    <div v-for="(item, index) in dataList" :key="index" class="mango-key-value-item">
      <div class="mango-key-value-row">
        <!-- 支持多个字段的展示 -->
        <div
          v-for="(field, fieldIndex) in getVisibleFields(item)"
          :key="fieldIndex"
          class="mango-key-value-field"
        >
          <span class="mango-field-label">{{ field.label }}:</span>
          <!-- 支持级联选择器 -->
          <a-cascader
            v-if="field.type === 'cascader'"
            v-model="item[field.field]"
            :options="field.options || []"
            :placeholder="field.placeholder || `请选择${field.label}`"
            :expand-trigger="field.expandTrigger || 'hover'"
            :value-key="field.valueKey || 'key'"
            @change="(value) => field.onChange && field.onChange(value, dataList, index)"
            :class="field.className || 'mango-key-cascader'"
          />
          <a-select
            v-else-if="field.type === 'select' && field.field"
            v-model="item[field.field]"
            :allow-clear="field.allowClear !== false"
            :options="field.options || []"
            :placeholder="field.placeholder || `请选择${field.label}`"
            :field-names="field.fieldNames"
            :class="field.className || 'mango-key-select'"
            @change="onBlur"
          />
          <!-- 支持文本域 -->
          <a-textarea
            v-else-if="field.field"
            v-model="item[field.field]"
            :placeholder="field.placeholder || `请输入${field.label}`"
            :auto-size="field.autoSize || { minRows: 1, maxRows: 3 }"
            @blur="onBlur"
            :class="field.className || 'mango-key-input'"
          />
          <!-- 支持数组直接绑定的情况 -->
          <a-textarea
            v-else
            :model-value="item"
            :placeholder="field.placeholder || `请输入${field.label}`"
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
            class="mango-remove-btn"
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
    label: string // 显示标签
    className?: string // 自定义类名
    placeholder?: string // 占位符文本
    type?: 'input' | 'textarea' | 'cascader' | 'select' // 字段类型
    // 级联选择器特有属性
    options?: any[] // 选项数据
    expandTrigger?: 'click' | 'hover' // 次级菜单展开方式
    valueKey?: string // 选项值的键名
    fieldNames?: any
    allowClear?: boolean
    onChange?: (value: any, item: any, index: number) => void // 值改变时的回调
    autoSize?: { minRows: number; maxRows: number } // 文本域自动调整大小
    visible?: (item: any) => boolean // 控制字段是否展示
  }

  // 定义组件属性
  interface Props {
    dataList: any[] // 数据列表
    fieldConfig: FieldConfig[] // 字段配置数组
    emptyText?: string // 空状态文本
    onDeleteItem: (index: number) => void // 删除回调
    onSave?: () => void // 保存回调（可选）
  }

  // 定义事件
  const emit = defineEmits<{
    (e: 'update:item', index: number, value: any, item: any): void
  }>()

  // 定义默认属性
  const props = withDefaults(defineProps<Props>(), {
    emptyText: '暂无数据，点击上方"增加"按钮添加',
  })

  const getVisibleFields = (item: any) => {
    return props.fieldConfig.filter((field) => !field.visible || field.visible(item))
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
    background-color: var(--m-surface);
    transition: border-color 0.16s ease, box-shadow 0.16s ease, background-color 0.16s ease;
  }

  .mango-key-value-item:hover {
    background-color: var(--m-surface-2);
    border-color: var(--m-primary-border);
    box-shadow: var(--m-shadow-soft);
  }

  .mango-key-value-row {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    flex-wrap: nowrap; /* 防止换行 */
    width: 100%;
    min-width: 0; /* 允许子元素收缩 */
    overflow-x: hidden; /* 防止水平滚动 */
  }

  .mango-key-value-field {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 100px; /* 减小最小宽度 */
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
