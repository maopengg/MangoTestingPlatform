<template>
  <a-table
    :bordered="false"
    :columns="columns"
    :data="data"
    :loading="loading"
    :draggable="editLocked || executionActive ? undefined : { type: 'handle', width: 40 }"
    :pagination="false"
    :row-class="rowClass"
    :scroll="{ x: 760 }"
    @change="$emit('reorder', $event)"
    @row-click="$emit('select', $event)"
  >
    <template #columns>
      <a-table-column
        v-for="item of columns"
        :key="item.key || item.dataIndex"
        :align="item.align"
        :data-index="item.dataIndex"
        :ellipsis="item.ellipsis"
        :fixed="item.fixed"
        :resizable="item.resizable"
        :title="item.title"
        :tooltip="item.tooltip"
        :width="item.width"
      >
        <template v-if="item.dataIndex === 'api_name'" #cell="{ record }">
          <a-space size="mini">
            <span>{{ record.api_info.name }}</span>
            <a-tag v-if="record.execution_config?.is_recovery" size="small">恢复</a-tag>
            <a-tag v-if="record.api_info_snapshot_source_missing" color="orange" size="small">
              历史快照·原接口已删除
            </a-tag>
          </a-space>
        </template>
        <template v-else-if="item.dataIndex === 'name'" #cell="{ record }">
          <a-tag>{{ record.name }}</a-tag>
        </template>
        <template v-else-if="item.dataIndex === 'status'" #cell="{ record }">
          <a-tag :color="statusColor(record)" size="small">{{ statusText(record) }}</a-tag>
        </template>
        <template v-else-if="item.dataIndex === 'actions'" #cell="{ record }">
          <MangoTableActions :actions="rowActions(record)" />
        </template>
      </a-table-column>
    </template>
  </a-table>
</template>

<script setup lang="ts">
  import MangoTableActions from '@/components/table/MangoTableActions.vue'

  const props = defineProps<{
    columns: any[]
    data: any[]
    loading: boolean
    selectedStepId?: string | number | null
    debugRunningStepId?: string | number | null
    editLocked: boolean
    executionActive: boolean
    statusText: (record: any) => string
    statusColor: (record: any) => string
    getApiInfoId: (record: any) => string | number
  }>()

  const emit = defineEmits<{
    (event: 'reorder', value: any): void
    (event: 'select', value: any): void
    (event: 'debug', value: any): void
    (event: 'refresh', value: any): void
    (event: 'api-info', value: any): void
    (event: 'delete', value: any): void
    (event: 'edit', value: any): void
  }>()

  function rowActions(record: any) {
    return [
      {
        label: '编辑',
        disabled: props.editLocked || props.executionActive,
        onClick: () => emit('edit', record),
      },
      {
        label: '调试',
        loading: String(props.debugRunningStepId) === String(record.id),
        disabled: props.editLocked || props.executionActive,
        onClick: () => emit('debug', record),
      },
      {
        label: '同步',
        disabled: props.editLocked,
        onClick: () => emit('refresh', record.id),
      },
      {
        label: '接口详情',
        disabled: !props.getApiInfoId(record),
        onClick: () => emit('api-info', record),
      },
      {
        label: '删除',
        danger: true,
        disabled: props.editLocked,
        onClick: () => emit('delete', record),
      },
    ]
  }

  function rowClass(record: any) {
    if (props.selectedStepId === null || props.selectedStepId === undefined) return ''
    return String(record?.id ?? '') === String(props.selectedStepId ?? '')
      ? 'mango-api-case-step-row--selected'
      : ''
  }
</script>

<style scoped>
  :deep(.arco-table-tr) {
    cursor: pointer;
  }

  :deep(.mango-api-case-step-row--selected .arco-table-td) {
    background: color-mix(in srgb, var(--m-warning) 12%, var(--m-surface)) !important;
  }

  :deep(.mango-api-case-step-row--selected .arco-table-td:first-child) {
    box-shadow: inset 3px 0 0 var(--m-warning);
  }
</style>
