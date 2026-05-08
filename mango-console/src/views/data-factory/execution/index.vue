<template>
  <TableBody>
    <template #header>
      <a-card title="数据工厂 / 执行记录" :bordered="false">
        <template #extra><a-button size="small" @click="doRefresh">刷新</a-button></template>
      </a-card>
    </template>

    <template #default>
      <a-table :data="table.dataList" :loading="table.tableLoading.value" :pagination="false" :row-key="'id'">
        <template #columns>
          <a-table-column title="ID" data-index="id" :width="80" />
          <a-table-column title="执行编号" data-index="execution_no" :width="230" />
          <a-table-column title="来源" data-index="source_name" />
          <a-table-column title="阶段" :width="110"><template #cell="{ record }">{{ enumTitle(enumStore.data_factory_execution_stage, record.stage) }}</template></a-table-column>
          <a-table-column title="状态" :width="110">
            <template #cell="{ record }"><a-tag :color="record.status === 2 ? 'green' : record.status === 3 ? 'red' : 'orange'">{{ enumTitle(enumStore.data_factory_execution_status, record.status) }}</a-tag></template>
          </a-table-column>
          <a-table-column title="清理状态" :width="120">
            <template #cell="{ record }"><a-tag>{{ enumTitle(enumStore.data_factory_cleanup_status, record.cleanup_status) }}</a-tag></template>
          </a-table-column>
          <a-table-column title="错误" data-index="error_message" />
          <a-table-column title="创建时间" data-index="create_time" :width="180" />
          <a-table-column title="操作" :width="180" fixed="right">
            <template #cell="{ record }">
              <a-space>
                <a-button size="mini" type="text" @click="openDetail(record)">详情</a-button>
                <a-button size="mini" status="danger" type="text" @click="cleanup(record)">清理</a-button>
                <a-button size="mini" type="text" @click="cleanupRetry(record)">重试</a-button>
              </a-space>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>

    <template #footer><TableFooter :pagination="pagination" /></template>
  </TableBody>

  <a-drawer v-model:visible="detailVisible" title="执行详情" width="860px">
    <a-tabs>
      <a-tab-pane key="context" title="上下文">
        <a-textarea :model-value="JSON.stringify(detail.context || {}, null, 2)" :auto-size="{ minRows: 18, maxRows: 28 }" readonly />
      </a-tab-pane>
      <a-tab-pane key="items" title="创建明细">
        <a-table :data="detail.items || []" :pagination="false" :scroll="{ x: 1200 }">
          <template #columns>
            <a-table-column title="ID" data-index="id" :width="80" />
            <a-table-column title="别名" data-index="alias" :width="120" />
            <a-table-column title="主键" data-index="primary_value" :width="150" />
            <a-table-column title="唯一值" data-index="unique_value" :width="180" />
            <a-table-column title="清理顺序" data-index="cleanup_order" :width="100" />
            <a-table-column title="清理状态" :width="120">
              <template #cell="{ record }">{{ enumTitle(enumStore.data_factory_cleanup_status, record.cleanup_status) }}</template>
            </a-table-column>
            <a-table-column title="数据">
              <template #cell="{ record }"><a-typography-paragraph copyable>{{ JSON.stringify(record.data) }}</a-typography-paragraph></template>
            </a-table-column>
          </template>
        </a-table>
      </a-tab-pane>
      <a-tab-pane key="error" title="错误">
        <a-alert v-if="detail.execution?.error_message" type="error">{{ detail.execution.error_message }}</a-alert>
        <a-empty v-else description="暂无错误" />
      </a-tab-pane>
    </a-tabs>
  </a-drawer>
</template>

<script lang="ts" setup>
  import {
    getDataFactoryExecution,
    getDataFactoryExecutionDetail,
    postDataFactoryExecutionCleanup,
    postDataFactoryExecutionCleanupRetry,
  } from '@/api/data-factory'
  import { usePagination, useTable } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, ref } from 'vue'

  const table = useTable()
  const pagination = usePagination(doRefresh)
  const enumStore = useEnum()
  const detailVisible = ref(false)
  const detail = ref<any>({})

  function enumTitle(options: any[] = [], value: any) {
    return options.find((it) => it.key === value)?.title || value
  }

  function doRefresh() {
    table.tableLoading.value = true
    getDataFactoryExecution({ page: pagination.page, pageSize: pagination.pageSize }).then((res) => {
      table.handleSuccess(res)
      pagination.setTotalSize((res as any).totalSize)
    })
  }

  function openDetail(record: any) {
    getDataFactoryExecutionDetail({ execution_id: record.id }).then((res) => {
      detail.value = res.data || {}
      detailVisible.value = true
    })
  }

  function cleanup(record: any) {
    Modal.confirm({
      title: '清理执行数据',
      content: `确认清理 ${record.execution_no} 创建的数据？`,
      onOk: () =>
        postDataFactoryExecutionCleanup({ execution_id: record.id }).then((res) => {
          Message.success(res.msg)
          doRefresh()
        }),
    })
  }

  function cleanupRetry(record: any) {
    postDataFactoryExecutionCleanupRetry({ execution_id: record.id }).then((res) => {
      Message.success(res.msg)
      doRefresh()
    })
  }

  onMounted(() => {
    enumStore.getEnum()
    doRefresh()
  })
</script>
