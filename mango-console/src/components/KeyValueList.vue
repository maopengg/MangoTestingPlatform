<template>
  <div class="key-value-container">
    <div v-for="(item, index) in dataList" :key="index" class="key-value-item">
      <div class="key-value-row">
        <!-- 支持多个字段的展示 -->
        <div v-for="(field, fieldIndex) in fieldConfig" :key="fieldIndex" class="key-value-field">
          <span class="field-label">{{ field.label }}:</span>
          <!-- 支持空字段名的情况 -->
          <a-input
            v-if="field.field"
            v-model="item[field.field]"
            :placeholder="field.placeholder || `请输入${field.label}`"
            @blur="onBlur"
            :class="field.className || 'key-input'"
          />
          <!-- 支持数组直接绑定的情况 -->
          <a-input
            v-else
            v-model="item[field.field]"
            :placeholder="field.placeholder || `请输入${field.label}`"
            @blur="onBlur"
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
  import { Message } from '@arco-design/web-vue'

  // 定义字段配置接口
  interface FieldConfig {
    field?: string // 字段名（可选，为空时表示直接绑定数组元素）
    label: string // 显示标签
    className?: string // 自定义类名
  }

  // 定义组件属性
  interface Props {
    dataList: any[] // 数据列表
    fieldConfig: FieldConfig[] // 字段配置数组
    emptyText?: string // 空状态文本
    onDeleteItem: (index: number) => void // 删除回调
    onSave?: () => void // 保存回调（可选）
  }

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
    align-items: center;
    gap: 12px;
  }

  .key-value-field {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .field-label {
    font-size: 12px;
    color: #666;
    font-weight: 500;
  }

  .key-input,
  .value-input,
  .sql-input {
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
