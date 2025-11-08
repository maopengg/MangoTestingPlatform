<template>
  <div class="key-value-container">
    <div v-for="(item, index) in dataList" :key="index" class="key-value-item">
      <div class="key-value-row">
        <!-- 支持多个字段的展示 -->
        <div v-for="(field, fieldIndex) in fieldConfig" :key="fieldIndex" class="key-value-field">
          <span class="field-label">{{ field.label }}:</span>
          <!-- 支持级联选择器 -->
          <a-cascader
            v-if="field.type === 'cascader'"
            v-model="item[field.field]"
            :options="field.options || []"
            :placeholder="field.placeholder || `请选择${field.label}`"
            :expand-trigger="field.expandTrigger || 'hover'"
            :value-key="field.valueKey || 'key'"
            @change="(value) => field.onChange && field.onChange(value, item, index)"
            :class="field.className || 'key-cascader'"
          />
          <!-- 支持文本域 -->
          <a-textarea
            v-else-if="field.field"
            v-model="item[field.field]"
            :placeholder="field.placeholder || `请输入${field.label}`"
            :auto-size="field.autoSize || { minRows: 1, maxRows: 3 }"
            @blur="onBlur"
            :class="field.className || 'key-input'"
          />
          <!-- 支持数组直接绑定的情况 -->
          <a-textarea
            v-else
            :model-value="item"
            :placeholder="field.placeholder || `请输入${field.label}`"
            :auto-size="field.autoSize || { minRows: 1, maxRows: 3 }"
            @blur="(event) => onItemBlur(event, index)"
            @update:model-value="(value) => onItemUpdate(value, index, item)"
            :class="field.className || 'key-input'"
          />
        </div>
        <!-- 插槽支持额外操作按钮 -->
        <slot name="extra" :index="index" :item="item"></slot>
        <a-button
          size="small"
          status="danger"
          type="text"
          @click="onDelete(index)"
          class="remove-btn"
        >
          移除
        </a-button>
      </div>
    </div>
    <div v-if="!dataList || dataList.length === 0" class="empty-placeholder">
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
    type?: 'input' | 'textarea' | 'cascader' // 字段类型
    // 级联选择器特有属性
    options?: any[] // 选项数据
    expandTrigger?: 'click' | 'hover' // 次级菜单展开方式
    valueKey?: string // 选项值的键名
    onChange?: (value: any, item: any, index: number) => void // 值改变时的回调
    autoSize?: { minRows: number; maxRows: number } // 文本域自动调整大小
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
  .key-value-container {
    padding: 10px 0;
  }

  .key-value-item {
    margin-bottom: 12px;
    border: 1px solid #e5e5e5;
    border-radius: 4px;
    padding: 12px;
    background-color: #fafafa;
  }

  .key-value-row {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    flex-wrap: wrap;
  }

  .key-value-field {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 150px;
  }

  .field-label {
    font-size: 12px;
    color: #666;
    font-weight: 500;
  }

  .key-input,
  .value-input,
  .sql-input,
  .key-cascader {
    width: 100%;
  }

  .remove-btn {
    align-self: flex-start;
    margin-top: 18px;
  }

  .empty-placeholder {
    text-align: center;
    color: #999;
    font-size: 14px;
    padding: 20px;
    border: 1px dashed #e5e5e5;
    border-radius: 4px;
    margin-top: 10px;
  }
</style>