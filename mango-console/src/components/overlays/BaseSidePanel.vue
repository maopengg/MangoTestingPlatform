<template>
  <a-drawer
    v-model:visible="localVisible"
    :width="width"
    :title="title"
    :mask-closable="false"
    unmount-on-close
  >
    <template #title>
      <div class="mango-side-mango-panel-header">
        <span>{{ title }}</span>
        <div class="mango-side-panel-actions">
          <slot name="header-actions"></slot>
        </div>
      </div>
    </template>

    <div class="mango-side-panel-content">
      <slot :data="data"></slot>
    </div>

    <template #footer>
      <a-space class="mango-side-panel-footer-actions">
        <slot name="footer-buttons" :data="data">
          <slot name="extra-buttons" :data="data"></slot>
          <a-button @click="handleCancel">{{ cancelButtonText }}</a-button>
        </slot>
      </a-space>
    </template>
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
  .mango-side-mango-panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    color: var(--m-text);
  }

  .mango-side-panel-actions {
    display: flex;
    gap: 8px;
  }

  :deep(.arco-drawer-body) {
    min-height: 0;
    padding: 0;
  }

  .mango-side-panel-content {
    height: 100%;
    overflow: auto;
    padding: 16px;
    color: var(--m-text-2);
  }

  .mango-side-panel-footer-actions {
    width: 100%;
    justify-content: flex-start;
  }
</style>
