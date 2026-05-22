<template>
  <div class="pending-table-wrap">
    <a-table
      :bordered="false"
      :columns="(tableColumns as any)"
      :data="(dataList as any)"
      :loading="(loading as any)"
      :pagination="false"
      :rowKey="(rowKey as any)"
      :scrollbar="true"
      :scroll="{ y: '100%' }"
      class="pending-tasks-table"
      size="small"
    >
      <template #columns>
        <a-table-column
          v-for="item of (tableColumns as any)"
          :key="(item.key as any)"
          :align="(item.align as any)"
          :data-index="(item.key as any)"
          :ellipsis="(item.ellipsis as any)"
          :title="(item.title as any)"
          :tooltip="(item.tooltip as any)"
          :width="(item.width as any)"
        >
          <template v-if="(item.key as any) === 'index'" #cell="{ record }">
            <span class="task-id">{{ record.id }}</span>
          </template>
          <template v-else-if="(item.key as any) === 'timing_strategy'" #cell="{ record }">
            {{ record.timing_strategy?.name || '手动/未配置策略' }}
          </template>
          <template v-else-if="(item.key as any) === 'case_people'" #cell="{ record }">
            {{ record.case_people?.name || '-' }}
          </template>
          <template v-else-if="(item.key as any) === 'test_env'" #cell="{ record }">
            <a-tag :color="enumStore.colors[record.test_env]" size="small">
              {{
                record.test_env !== null ? enumStore.environment_type[record.test_env]?.title : '-'
              }}
            </a-tag>
          </template>
        </a-table-column>
      </template>
    </a-table>
  </div>
</template>
<script lang="ts" setup>
  import { useRowKey, useTableColumn } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'
  import { getSystemTasks } from '@/api/system/tasks'
  import { ref, onMounted } from 'vue'

  const rowKey = useRowKey('id')
  const enumStore = useEnum()
  // 组件内部数据
  const dataList = ref<any[]>([])
  const loading = ref(true)

  const tableColumns = useTableColumn([
    {
      title: 'ID',
      key: 'index',
      width: 86,
      dataIndex: 'index',
      align: 'center',
    },
    {
      title: '任务名称',
      key: 'name',
      dataIndex: 'name',
      align: 'left',
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '定时策略',
      key: 'timing_strategy',
      dataIndex: 'timing_strategy',
      align: 'left',
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '环境',
      key: 'test_env',
      dataIndex: 'test_env',
      width: 86,
    },
    {
      title: '负责人',
      key: 'case_people',
      dataIndex: 'case_people',
      width: 96,
    },
  ])

  // 获取数据的方法
  function fetchData() {
    loading.value = true
    getSystemTasks({
      pageSize: 100,
      page: 1,
    })
      .then((res) => {
        dataList.value = res.data
        loading.value = false
      })
      .catch(() => {
        loading.value = false
      })
  }

  // 组件挂载时获取数据
  onMounted(() => {
    fetchData()
  })

  // 暴露刷新方法给父组件
  defineExpose({
    refresh: fetchData,
  })
</script>

<style lang="less" scoped>
  .pending-table-wrap {
    height: 100%;
    min-height: 0;
    padding-top: 8px;
  }

  .pending-tasks-table {
    height: 100%;

    :deep(.arco-spin),
    :deep(.arco-spin-children),
    :deep(.arco-table),
    :deep(.arco-table-container),
    :deep(.arco-table-content) {
      height: 100%;
    }

    :deep(.arco-table-th) {
      height: 34px;
      background: var(--m-table-header-bg);
      color: var(--m-text-2);
      font-size: 12px;
    }

    :deep(.arco-table-td) {
      height: 38px;
      color: var(--m-text-2);
      font-size: 12px;
    }
  }

  .task-id {
    color: var(--m-primary);
    font-size: 12px;
    font-weight: 600;
  }
</style>
