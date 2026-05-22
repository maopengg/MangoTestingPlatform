<template>
  <div class="resource-grid">
    <section class="resource-card mango-soft-panel">
      <div class="resource-item" @click="handleDownloadExecutor">
        <icon-download class="resource-icon" />
        <div class="resource-info">
          <div class="resource-title">执行器下载</div>
          <div class="resource-desc">下载最新版本的执行器</div>
        </div>
      </div>
    </section>

    <section class="resource-card mango-soft-panel">
      <div class="resource-item" @click="handleDownloadPlugin">
        <icon-download class="resource-icon" />
        <div class="resource-info">
          <div class="resource-title">插件下载</div>
          <div class="resource-desc">获取元素定位插件</div>
        </div>
      </div>
    </section>

    <section class="resource-card mango-soft-panel">
      <div class="resource-item" @click="handleViewHelp">
        <icon-book class="resource-icon" />
        <div class="resource-info">
          <div class="resource-title">帮助文档</div>
          <div class="resource-desc">查看详细的使用说明</div>
        </div>
      </div>
    </section>

    <section class="resource-card mango-soft-panel">
      <div class="resource-item" @click="handleContactAuthor">
        <icon-user class="resource-icon" />
        <div class="resource-info">
          <div class="resource-title">联系作者</div>
          <div class="resource-desc">获取技术支持和反馈</div>
        </div>
      </div>
    </section>
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
  .resource-grid {
    display: grid;
    height: 100%;
    min-height: 0;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    grid-template-rows: repeat(2, minmax(0, 1fr));
    gap: 8px;
    padding-top: 8px;
  }

  .resource-card {
    cursor: pointer;
    min-height: 0;
    padding: 8px;
    transition: border-color 0.2s ease, background-color 0.2s ease;

    &:hover {
      border-color: var(--m-primary);
      background: var(--m-primary-soft);
    }
  }

  .resource-item {
    display: flex;
    height: 100%;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }

  .resource-icon {
    font-size: 16px;
    color: var(--m-primary);
  }

  .resource-info {
    min-width: 0;
    flex: 1;
  }

  .resource-title {
    overflow: hidden;
    font-size: 12px;
    font-weight: 500;
    color: var(--m-text);
    margin-bottom: 0px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .resource-desc {
    overflow: hidden;
    font-size: 10px;
    color: var(--m-muted);
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
