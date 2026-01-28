<template>
  <a-drawer
    v-model:visible="localVisible"
    :width="width"
    :title="title"
    :mask-closable="false"
    :footer="false"
    unmount-on-close
  >
    <template #title>
      <div class="side-panel-header">
        <span>{{ title }}</span>
        <div class="side-panel-actions">
          <slot name="header-actions"></slot>
        </div>
      </div>
    </template>

    <!-- 内容区域 -->
    <div class="side-panel-content">
      <slot :data="data"></slot>
    </div>

    <!-- 底部操作栏 -->
    <div class="side-panel-footer">
      <a-space>
        <slot name="footer-buttons" :data="data">
          <!-- 默认按钮组 -->
          <slot name="extra-buttons" :data="data"></slot>
          <a-button @click="handleCancel">取消</a-button>
        </slot>
      </a-space>
    </div>
  </a-drawer>
</template>

<script lang="ts" setup>
  import { ref, watch } from 'vue'

  interface Props {
    visible?: boolean
    title: string
    width?: string | number
    data?: any
    showConfirmButton?: boolean
    confirmLoading?: boolean
    confirmButtonText?: string
    cancelButtonText?: string
  }

  const props = withDefaults(defineProps<Props>(), {
    visible: false,
    width: 800,
    data: undefined,
    showConfirmButton: true,
    confirmLoading: false,
    confirmButtonText: '确定',
    cancelButtonText: '取消',
  })

  // 使用 defineEmits 定义事件
  const emit = defineEmits<{
    (e: 'update:visible', value: boolean): void
    (e: 'cancel'): void
    (e: 'confirm'): void
  }>()

  // 响应式本地状态
  const localVisible = ref(props.visible)

  // 监听外部可见性变化
  watch(
    () => props.visible,
    (newVal) => {
      localVisible.value = newVal
    }
  )

  // 监听本地状态变化并同步到父组件
  watch(localVisible, (newVal) => {
    emit('update:visible', newVal)
  })

  // 取消操作
  const handleCancel = () => {
    localVisible.value = false
    emit('cancel')
  }
</script>

<style scoped>
  .side-panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
  }

  .side-panel-actions {
    display: flex;
    gap: 8px;
  }

  .side-panel-content {
    height: calc(100% - 80px); /* 减去底部操作栏的高度 */
    overflow-y: auto;
  }

  .side-panel-footer {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 16px;
    background-color: var(--color-bg-1);
    border-top: 1px solid var(--color-border);
    display: flex;
    justify-content: flex-start;
  }
</style>
