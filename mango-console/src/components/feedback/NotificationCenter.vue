<template>
  <div class="mango-notification-center">
    <a-tabs
      v-model:active-key="activeTab"
      class="mango-notification-center__tabs"
      size="small"
      lazy-load
    >
      <a-tab-pane key="todo">
        <template #title>
          <span class="mango-notification-center__tab-title">
            风险待办
            <a-badge :count="notificationMessage.todoPendingCount" :max-count="99" />
          </span>
        </template>
        <div class="mango-notification-center__panel">
          <RiskTodos />
        </div>
      </a-tab-pane>
      <a-tab-pane key="message">
        <template #title>
          <span class="mango-notification-center__tab-title">
            消息中心
            <a-badge :count="notificationMessage.messageUnreadCount" :max-count="99" />
          </span>
        </template>
        <div class="mango-notification-center__panel">
          <MessageContent />
        </div>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script lang="ts" setup>
  import { ref } from 'vue'
  import { useNotificationMessage } from '@/store/modules/notification-message'
  import RiskTodos from '@/views/index/components/RiskTodos.vue'
  import MessageContent from './MessageContent.vue'

  const activeTab = ref('todo')
  const notificationMessage = useNotificationMessage()
</script>

<style lang="less" scoped>
  .mango-notification-center {
    width: 420px;
    height: 430px;
    color: var(--m-text);
    background: var(--m-surface);

    :deep(.mango-notification-center__tabs) {
      height: 100%;
    }

    :deep(.mango-notification-center__tabs > .arco-tabs-nav) {
      margin-bottom: 0;
      padding: 0 8px;
    }

    :deep(.mango-notification-center__tabs > .arco-tabs-content) {
      height: calc(100% - 38px);
      padding-top: 0;
    }

    :deep(.mango-notification-center__tabs > .arco-tabs-content > .arco-tabs-content-list) {
      height: 100%;
    }

    :deep(
        .mango-notification-center__tabs
          > .arco-tabs-content
          > .arco-tabs-content-list
          > .arco-tabs-content-item-active
      ),
    :deep(
        .mango-notification-center__tabs
          > .arco-tabs-content
          > .arco-tabs-content-list
          > .arco-tabs-content-item-active
          > .arco-tabs-pane
      ) {
      height: 100%;
    }
  }

  .mango-notification-center__tab-title {
    display: inline-flex;
    min-width: 104px;
    align-items: center;
    justify-content: center;
    gap: 6px;
  }

  .mango-notification-center__panel {
    height: 100%;
    min-height: 0;
    border-top: 1px solid var(--m-border-soft);
  }
</style>
