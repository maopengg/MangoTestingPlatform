<template>
  <div style="display: flex; flex-direction: column; gap: 15px; margin-top: 10px">
    <a-card class="resource-card" hoverable>
      <div class="resource-item" @click="handleDownloadExecutor">
        <icon-download class="resource-icon" />
        <div class="resource-info">
          <div class="resource-title">执行器下载</div>
          <div class="resource-desc">下载最新版本的执行器</div>
        </div>
      </div>
    </a-card>

    <a-card class="resource-card" hoverable>
      <div class="resource-item" @click="handleDownloadPlugin">
        <icon-download class="resource-icon" />
        <div class="resource-info">
          <div class="resource-title">插件下载</div>
          <div class="resource-desc">获取元素定位插件</div>
        </div>
      </div>
    </a-card>

    <a-card class="resource-card" hoverable>
      <div class="resource-item" @click="handleViewHelp">
        <icon-book class="resource-icon" />
        <div class="resource-info">
          <div class="resource-title">帮助文档</div>
          <div class="resource-desc">查看详细的使用说明</div>
        </div>
      </div>
    </a-card>

    <a-card class="resource-card" hoverable>
      <div class="resource-item" @click="handleContactAuthor">
        <icon-user class="resource-icon" />
        <div class="resource-info">
          <div class="resource-title">联系作者</div>
          <div class="resource-desc">获取技术支持和反馈</div>
        </div>
      </div>
    </a-card>
  </div>
</template>

<script lang="ts" setup>
  import { IconDownload, IconBook, IconUser } from '@arco-design/web-vue/es/icon'

  const emit = defineEmits(['download-executor', 'download-plugin', 'view-help', 'contact-author'])

  function handleDownloadExecutor() {
    emit('download-executor')
  }

  function handleDownloadPlugin() {
    emit('download-plugin')
  }

  function handleViewHelp() {
    emit('view-help')
  }

  function handleContactAuthor() {
    emit('contact-author')
  }
</script>

<style lang="less" scoped>
  // 资源中心卡片样式
  .resource-card {
    border: 1px solid var(--color-neutral-3);
    border-radius: 8px;
    transition: all 0.3s ease;
    cursor: pointer;
    height: 50px;

    // 移除悬浮效果
    &:hover {
      border-color: rgb(var(--primary-6));
      // 移除阴影和位移效果
    }

    :deep(.arco-card-body) {
      padding: 8px;
    }
  }

  .resource-item {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .resource-icon {
    font-size: 16px;
    color: rgb(var(--primary-6));
  }

  .resource-info {
    flex: 1;
  }

  .resource-title {
    font-size: 12px;
    font-weight: 500;
    color: var(--color-text-1);
    margin-bottom: 0px;
  }

  .resource-desc {
    font-size: 10px;
    color: var(--color-text-3);
  }
</style>
