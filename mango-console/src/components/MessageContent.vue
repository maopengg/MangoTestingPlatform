<template>
  <a-list
    :bordered="false"
    :style="{
      width: '350px',
      height: '400px',
      overflowY: 'auto',
    }"
    class="custom-scrollbar"
    size="small"
  >
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
            <a-avatar :style="{ backgroundColor: '#2ECC71' }">
              <icon-check />
            </a-avatar>
          </template>
          <template v-else>
            <a-avatar :style="{ backgroundColor: '#E74C3C' }">
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
  /* 强制穿透样式 */
  :deep(.arco-list) {
    height: 400px !important;
    overflow-y: auto !important;
  }
  /* 滚动条样式 */
  .custom-scrollbar::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: rgba(0, 0, 0, 0.2);
    border-radius: 4px;
  }
</style>
