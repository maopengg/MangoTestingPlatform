<template>
  <div class="mango-message-content">
    <a-tabs
      v-model:active-key="activeFilter"
      class="mango-message-content__tabs"
      size="small"
      hide-content
    >
      <a-tab-pane key="all">
        <template #title>
          <span class="mango-message-tab-title"
            >全部 <small>{{ messageCount }}</small></span
          >
        </template>
      </a-tab-pane>
      <a-tab-pane key="success">
        <template #title>
          <span class="mango-message-tab-title"
            >成功 <small>{{ successCount }}</small></span
          >
        </template>
      </a-tab-pane>
      <a-tab-pane key="failed">
        <template #title>
          <span class="mango-message-tab-title"
            >失败 <small>{{ failedCount }}</small></span
          >
        </template>
      </a-tab-pane>
      <template #extra>
        <a-space size="mini">
          <a-button
            type="outline"
            size="mini"
            :disabled="notificationMessage.messageUnreadCount === 0"
            @click="notificationMessage.markAllMessagesRead()"
            data-testid="qa-components-feedback-messagecontent-button-全部已读"
            >全部已读</a-button
          >
          <a-button
            type="outline"
            size="mini"
            @click="clearMsg"
            data-testid="qa-components-feedback-messagecontent-button-清空消息"
            >清空消息</a-button
          >
        </a-space>
      </template>
    </a-tabs>

    <div class="mango-message-content-list mango-custom-scrollbar">
      <a-list :bordered="false" :scrollbar="false" class="mango-message-list" size="small">
        <a-list-item
          v-for="(item, index) of filteredMessages"
          :key="index"
          :class="{
            'is-unread': item.read === false,
            'is-unread-success': item.read === false && item.status === 1,
          }"
        >
          <a-list-item-meta>
            <template #avatar>
              <template v-if="item.status === 1">
                <a-avatar
                  class="mango-message-content-avatar mango-message-content-avatar--success"
                >
                  <icon-check />
                </a-avatar>
              </template>
              <template v-else>
                <a-avatar class="mango-message-content-avatar mango-message-content-avatar--danger">
                  <icon-close />
                </a-avatar>
              </template>
            </template>
            <template #title>
              <div v-if="item.kind === 'task_result'" class="mango-message-result__title">
                <span>{{ item.resultName || '测试任务' }}</span>
                <span
                  class="mango-message-result__status"
                  :class="
                    item.status === 1
                      ? 'mango-message-result__status--success'
                      : 'mango-message-result__status--danger'
                  "
                >
                  {{ item.statusText || (item.status === 1 ? '执行通过' : '执行失败') }}
                </span>
              </div>
              <span v-else>{{ item.title }}</span>
            </template>
            <template #description>
              <div v-if="item.kind === 'task_result'" class="mango-message-result">
                <div data-feedback-kind="execution-result" v-if="item.status !== 1" class="mango-message-result__reason">
                  失败原因：{{ item.errorMessage || '未返回具体原因，请进入结果详情查看' }}
                </div>
                <div v-else class="mango-message-result__summary">
                  测试执行完成，结果符合预期。
                </div>
                <div class="mango-message-result__meta">
                  <span>{{ item.title }}</span>
                  <span v-if="item.durationSeconds !== null && item.durationSeconds !== undefined">
                    耗时 {{ formatDuration(item.durationSeconds) }}
                  </span>
                  <span v-if="item.taskId">任务 #{{ item.taskId }}</span>
                </div>
                <a-button
                  v-if="canViewResult(item)"
                  type="text"
                  size="mini"
                  class="mango-message-result__action"
                  @click="viewResult(item)"
                >
                  查看用例
                </a-button>
              </div>
              <span v-else>{{ item.description }}</span>
            </template>
          </a-list-item-meta>
        </a-list-item>
        <div v-if="filteredMessages.length === 0" class="mango-message-content-list__empty">
          暂无{{ activeFilter === 'all' ? '' : activeFilter === 'success' ? '成功' : '失败' }}消息
        </div>
      </a-list>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { computed, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import {
    type NotificationMessageItem,
    useNotificationMessage,
  } from '@/store/modules/notification-message'

  const notificationMessage = useNotificationMessage()
  const router = useRouter()
  const activeFilter = ref<'all' | 'success' | 'failed'>('all')
  const messageCount = computed(() => notificationMessage.messageContentList.length)
  const successCount = computed(
    () => notificationMessage.messageContentList.filter((item) => item.status === 1).length
  )
  const failedCount = computed(
    () => notificationMessage.messageContentList.filter((item) => item.status !== 1).length
  )
  const filteredMessages = computed(() => {
    if (activeFilter.value === 'success') {
      return notificationMessage.messageContentList.filter((item) => item.status === 1)
    }
    if (activeFilter.value === 'failed') {
      return notificationMessage.messageContentList.filter((item) => item.status !== 1)
    }
    return notificationMessage.messageContentList
  })

  function clearMsg() {
    notificationMessage.clearMessages()
  }

  function formatDuration(value: number | null | undefined) {
    const total = Math.max(0, Number(value) || 0)
    const minutes = Math.floor(total / 60)
    const seconds = total % 60
    return minutes > 0 ? `${minutes}分${seconds}秒` : `${seconds}秒`
  }

  function canViewResult(item: NotificationMessageItem) {
    return Boolean(
      item.businessId && ['ui_case', 'ui_case_step'].includes(String(item.taskType || ''))
    )
  }

  function viewResult(item: NotificationMessageItem) {
    if (!canViewResult(item)) return
    router.push({
      path: '/uitest/case/details',
      query: { id: String(item.businessId) },
    })
  }
</script>

<style scoped>
  .mango-message-content {
    display: flex;
    width: 100%;
    height: 100%;
    min-height: 0;
    flex-direction: column;
    color: var(--m-text);
    background: var(--m-surface);
  }

  .mango-message-content__tabs {
    flex: none;
    padding: 0 8px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-message-content__tabs :deep(.arco-tabs-nav) {
    min-height: 38px;
    margin-bottom: 0;
  }

  .mango-message-content__tabs :deep(.arco-tabs-nav-extra) {
    display: flex;
    height: 38px;
    align-items: center;
  }

  .mango-message-tab-title {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }

  .mango-message-tab-title small {
    color: var(--m-muted);
    font-size: 11px;
    font-weight: 400;
  }

  .mango-message-content-list {
    min-height: 0;
    flex: 1;
    overflow-x: hidden;
    overflow-y: auto;
    overscroll-behavior: contain;
    scrollbar-gutter: stable;
  }

  .mango-message-list :deep(.arco-list-spin) {
    height: auto;
    overflow: visible;
  }

  :deep(.arco-list-item) {
    border-bottom-color: var(--m-border-soft);
    transition: background-color 0.16s ease;
  }

  :deep(.arco-list-item:hover) {
    background: var(--m-table-row-hover);
  }

  :deep(.arco-list-item.is-unread) {
    box-shadow: inset 2px 0 0 var(--m-danger);
  }

  :deep(.arco-list-item.is-unread-success) {
    box-shadow: inset 2px 0 0 var(--m-success);
  }

  :deep(.arco-list-item-meta-title) {
    color: var(--m-text);
  }

  :deep(.arco-list-item-meta-description) {
    color: var(--m-muted);
  }

  .mango-message-content-avatar {
    color: var(--m-on-primary);
  }

  .mango-message-content-avatar--success {
    background: var(--m-success);
  }

  .mango-message-content-avatar--danger {
    background: var(--m-danger);
  }

  .mango-message-result__title {
    display: flex;
    min-width: 0;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .mango-message-result__title > span:first-child {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-message-result__status {
    flex: none;
    font-size: 12px;
    font-weight: 600;
  }

  .mango-message-result__status--success {
    color: var(--m-success);
  }

  .mango-message-result__status--danger,
  .mango-message-result__reason {
    color: var(--m-danger);
  }

  .mango-message-result__reason,
  .mango-message-result__summary {
    margin-bottom: 4px;
    line-height: 1.55;
  }

  .mango-message-result__meta {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 10px;
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-message-result__action {
    height: 24px;
    margin-top: 4px;
    padding: 0;
  }

  .mango-message-content-list__empty {
    display: flex;
    min-height: 280px;
    align-items: center;
    justify-content: center;
    color: var(--m-muted);
  }

  .mango-custom-scrollbar::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }
  .mango-custom-scrollbar::-webkit-scrollbar-thumb {
    background: var(--m-scrollbar-thumb);
    border-radius: 4px;
  }
</style>
