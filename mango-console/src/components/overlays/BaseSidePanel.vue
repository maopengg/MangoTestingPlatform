<template>
  <a-drawer
    v-model:visible="localVisible"
    :class="['mango-side-panel', `mango-side-panel--${mode}`]"
    :width="width"
    :title="title"
    :mask-closable="maskClosable"
    :header="mode !== 'page'"
    :footer="mode !== 'page' && showFooter"
    body-class="mango-side-panel-body"
    unmount-on-close
  >
    <template v-if="mode !== 'page'" #title>
      <div class="mango-side-mango-panel-header">
        <span>{{ title }}</span>
        <div class="mango-side-panel-actions">
          <slot name="header-actions"></slot>
        </div>
      </div>
    </template>

    <div v-if="mode === 'page'" class="mango-side-panel-page">
      <header class="mango-side-panel-page__header">
        <div class="mango-side-panel-page__heading">
          <div class="mango-side-panel-page__title">{{ title }}</div>
          <div v-if="pageDescription" class="mango-side-panel-page__description">
            {{ pageDescription }}
          </div>
        </div>
        <a-button type="text" shape="circle" aria-label="关闭当前页面" @click="handleCancel">
          <template #icon><icon-close /></template>
        </a-button>
      </header>
      <main class="mango-side-panel-page__main">
        <slot :data="data"></slot>
      </main>
      <footer class="mango-side-panel-page__footer">
        <Footer />
      </footer>
    </div>
    <div v-else class="mango-side-panel-content">
      <slot :data="data"></slot>
    </div>

    <template v-if="mode !== 'page'" #footer>
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
  import { IconClose } from '@arco-design/web-vue/es/icon'
  import Footer from '@/layouts/footer/index.vue'

  interface Props {
    visible?: boolean
    title: string
    width?: string | number
    data?: any
    showConfirmButton?: boolean
    confirmLoading?: boolean
    confirmButtonText?: string
    cancelButtonText?: string
    maskClosable?: boolean
    showFooter?: boolean
    mode?: 'action' | 'page'
    pageDescription?: string
  }

  const props = withDefaults(defineProps<Props>(), {
    visible: false,
    width: 800,
    data: undefined,
    showConfirmButton: true,
    confirmLoading: false,
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    maskClosable: true,
    showFooter: true,
    mode: 'action',
    pageDescription: '',
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

  :global(.mango-side-panel-body) {
    min-height: 0;
    padding: 0;
  }

  :global(.mango-side-panel--page .arco-drawer-body) {
    display: flex;
    flex: 1 1 auto;
    min-height: 0;
    padding: 0;
    overflow: hidden;
    background: var(--m-bg);
  }

  .mango-side-panel-content {
    box-sizing: border-box;
    height: 100%;
    min-width: 0;
    min-height: 0;
    padding: var(--m-page-gap);
    overflow: auto;
    color: var(--m-text-2);
  }

  .mango-side-panel-page {
    box-sizing: border-box;
    display: flex;
    flex: 1 1 auto;
    width: 100%;
    height: auto;
    min-width: 0;
    min-height: 0;
    padding: var(--m-page-gap);
    flex-direction: column;
    gap: var(--m-page-gap);
    overflow: hidden;
    background: var(--m-bg);
    color: var(--m-text-2);
  }

  .mango-side-panel-page__header {
    box-sizing: border-box;
    display: flex;
    flex: none;
    min-height: 56px;
    padding: var(--m-card-padding) var(--m-page-gap);
    align-items: center;
    justify-content: space-between;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
    box-shadow: var(--m-shadow);
  }

  .mango-side-panel-page__heading {
    min-width: 0;
  }

  .mango-side-panel-page__title {
    color: var(--m-text);
    font-size: 16px;
    font-weight: 600;
    line-height: 24px;
  }

  .mango-side-panel-page__description {
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-side-panel-page__main {
    display: flex;
    flex: 1 1 auto;
    min-height: 0;
    overflow: visible;
  }

  :global(.mango-side-panel--page .mango-side-panel-page__main > *) {
    flex: 1 1 auto;
    min-height: 0;
  }

  .mango-side-panel-page__footer {
    flex: none;
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
    box-shadow: var(--m-shadow);
  }

  .mango-side-panel-page__footer :deep(.mango-footer-container) {
    border-radius: 0;
    box-shadow: none;
  }

  .mango-side-panel-footer-actions {
    width: 100%;
    justify-content: flex-start;
  }
</style>
