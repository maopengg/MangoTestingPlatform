<template>
  <a-list :bordered="false" class="mango-message-content-list mango-custom-scrollbar" size="small">
    <template #header>
      <a-space>
        <a-button
          type="outline"
          status="success"
          size="mini"
          @click="notificationMessage.addBadgeValue(true)"
          >全部已读</a-button
        >
        <a-button type="outline" status="warning" size="mini" @click="clearMsg"
          >清空消息</a-button
        ></a-space
      >
    </template>
    <a-list-item v-for="(item, index) of notificationMessage.messageContentList" :key="index">
      <a-list-item-meta :description="item.description" :title="item.title">
        <template #avatar>
          <template v-if="item.status === 1">
            <a-avatar class="mango-message-content-avatar mango-message-content-avatar--success">
              <icon-check />
            </a-avatar>
          </template>
          <template v-else>
            <a-avatar class="mango-message-content-avatar mango-message-content-avatar--danger">
              <icon-close />
            </a-avatar>
          </template>
        </template>
      </a-list-item-meta>
    </a-list-item>
  </a-list>
</template>

<script lang="ts" setup>
  import { useNotificationMessage } from '@/store/modules/notification-message'

  const notificationMessage = useNotificationMessage()
  function clearMsg() {
    notificationMessage.addBadgeValue(true)
    notificationMessage.addMessageContentList('1', '1', 1, true)
  }
</script>

<style scoped>
  .mango-message-content-list {
    width: 350px;
    height: 400px;
    color: var(--m-text);
    background: var(--m-surface);
  }

  :deep(.arco-list) {
    height: 400px !important;
    overflow-y: auto !important;
  }

  :deep(.arco-list-header) {
    background: var(--m-surface-2);
    border-bottom-color: var(--m-border);
  }

  :deep(.arco-list-item) {
    border-bottom-color: var(--m-border-soft);
    transition: background-color 0.16s ease;
  }

  :deep(.arco-list-item:hover) {
    background: var(--m-table-row-hover);
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

  .mango-custom-scrollbar::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }
  .mango-custom-scrollbar::-webkit-scrollbar-thumb {
    background: var(--m-scrollbar-thumb);
    border-radius: 4px;
  }
</style>
