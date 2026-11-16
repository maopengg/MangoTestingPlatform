<template>
  <div class="mango-api-case-scenario-header">
    <div class="custom-header">
      <a-tooltip :content="`场景名称：${item.name}`" position="top">
        <span class="custom-header__name">场景名称：{{ item.name }}</span>
      </a-tooltip>
      <div class="custom-header__tags">
        <a-tooltip v-if="isFailure(item)" :content="failureMessage(item)" position="top" mini>
          <a-tag :color="statusColor(item)">{{ statusText(item) }}</a-tag>
        </a-tooltip>
        <a-tag v-else :color="statusColor(item)">{{ statusText(item) }}</a-tag>
        <a-tag v-if="item.result_data?.automatic_retry_condition" color="orange">
          自动重试后{{ Number(item.result_data.status) === 1 ? '通过' : '失败' }}
        </a-tag>
        <a-tag v-else color="purple">
          {{
            item.error_retry
              ? `重试 ${item.error_retry} 次 / ${item.retry_interval ? item.retry_interval : 0}s`
              : '不重试'
          }}
        </a-tag>
        <a-tag v-if="item.allow_failure" color="orange">允许失败</a-tag>
      </div>
    </div>
    <MangoTableActions :max-inline="2" :actions="actions" @click.stop />
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import { useScenarioCurl } from '@/hooks/useScenarioCurl'

  const props = defineProps<{
    item: any
    editLocked: boolean
    statusText: (record: any) => string
    statusColor: (record: any) => string
    isFailure: (record: any) => boolean
    failureMessage: (record: any) => string
  }>()

  const emit = defineEmits<{
    (event: 'edit'): void
    (event: 'copy'): void
    (event: 'delete'): void
  }>()

  const { copyScenarioCurl } = useScenarioCurl()

  const actions = computed(() => [
    {  label: '编辑', disabled: props.editLocked, onClick: () => emit('edit') },
    { label: '复制 cURL', onClick: () => copyScenarioCurl(props.item) },
    {  label: '复制', disabled: props.editLocked, onClick: () => emit('copy') },
    {
      label: '删除',
      danger: true,
      disabled: props.editLocked,
      onClick: () => emit('delete'),
    },
  ])
</script>

<style scoped>
  .mango-api-case-scenario-header {
    display: flex;
    width: 100%;
    min-width: 0;
    align-items: center;
    gap: 8px;
  }

  .custom-header {
    display: flex;
    min-width: 0;
    overflow: hidden;
    flex: 1;
    align-items: center;
  }

  .custom-header__name {
    min-width: 0;
    overflow: hidden;
    flex: 1;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 500;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .custom-header__tags {
    display: flex;
    width: 200px;
    flex-shrink: 0;
    align-items: center;
    gap: 6px;
  }
</style>
