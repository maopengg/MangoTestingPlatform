<template>
  <div class="resource-grid">
    <button class="resource-card mango-soft-panel" type="button" @click="handleDownloadExecutor">
      <icon-download class="resource-icon" />
      <span class="resource-title">执行器下载</span>
    </button>

    <button class="resource-card mango-soft-panel" type="button" @click="handleViewSkill">
      <icon-code class="resource-icon" />
      <span class="resource-title">Skill 中心</span>
    </button>

    <button class="resource-card mango-soft-panel" type="button" @click="handleViewHelp">
      <icon-book class="resource-icon" />
      <span class="resource-title">帮助文档</span>
    </button>

    <button class="resource-card mango-soft-panel" type="button" @click="handleContactAuthor">
      <icon-user class="resource-icon" />
      <span class="resource-title">联系作者</span>
    </button>
  </div>
</template>

<script lang="ts" setup>
  import { IconDownload, IconBook, IconUser, IconCode } from '@arco-design/web-vue/es/icon'

  const emit = defineEmits(['download-executor', 'view-skill', 'view-help', 'contact-author'])

  function handleDownloadExecutor() {
    emit('download-executor')
  }

  function handleViewSkill() {
    emit('view-skill')
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
    display: flex;
    height: auto;
    min-height: 0;
    align-items: center;
    justify-content: flex-start;
    gap: 5px;
    overflow-x: auto;
    overflow-y: hidden;
    padding-top: 2px;
  }

  .resource-card {
    display: flex;
    flex: 0 0 auto;
    cursor: pointer;
    min-height: 0;
    min-width: max-content;
    align-items: center;
    justify-content: flex-start;
    gap: 4px;
    padding: 4px 7px;
    color: var(--m-text);
    font-family: inherit;
    text-align: left;
    transition: border-color 0.2s ease, background-color 0.2s ease;

    &:hover {
      border-color: var(--m-primary);
      background: var(--m-primary-soft);
    }
  }

  .resource-icon {
    flex: none;
    font-size: 14px;
    color: var(--m-primary);
  }

  .resource-title {
    display: block;
    font-size: 11px;
    font-weight: 500;
    color: var(--m-text);
    white-space: nowrap;
  }
</style>
