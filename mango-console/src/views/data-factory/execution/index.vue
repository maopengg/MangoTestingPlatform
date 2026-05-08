<template>
  <TableBody>
    <template #header>
      <a-card title="数据工厂 / 执行记录" :bordered="false">
        <template #extra><a-button size="small" @click="doRefresh">刷新</a-button></template>
      </a-card>
    </template>

    <template #default>
      <a-table :columns="executionTableColumns" :data="table.dataList" :loading="table.tableLoading.value" :pagination="false" :row-key="'id'">
        <template #columns>
          <a-table-column
            v-for="item of executionTableColumns"
            :key="item.key"
            :data-index="item.key"
            :fixed="item.fixed"
            :title="item.title"
            :width="item.width"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'stage'" #cell="{ record }">
              {{ enumTitle(enumStore.data_factory_execution_stage, record.stage) }}
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="record.status === 2 ? 'green' : record.status === 3 ? 'red' : 'orange'">{{ enumTitle(enumStore.data_factory_execution_status, record.status) }}</a-tag>
            </template>
            <template v-else-if="item.key === 'cleanup_status'" #cell="{ record }">
              <a-tag>{{ enumTitle(enumStore.data_factory_cleanup_status, record.cleanup_status) }}</a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-space>
                <a-button size="mini" type="text" @click="openDetail(record)">详情</a-button>
                <a-button size="mini" status="danger" type="text" @click="cleanup(record)">清理</a-button>
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
        <a-table :columns="executionItemColumns" :data="detail.items || []" :pagination="false" :scroll="{ x: 1200 }">
          <template #columns>
            <a-table-column
              v-for="item of executionItemColumns"
              :key="item.key"
              :data-index="item.key"
              :title="item.title"
              :width="item.width"
            >
              <template v-if="item.key === 'index'" #cell="{ record }">
                {{ record.id }}
              </template>
              <template v-else-if="item.key === 'cleanup_status'" #cell="{ record }">
                {{ enumTitle(enumStore.data_factory_cleanup_status, record.cleanup_status) }}
              </template>
              <template v-else-if="item.key === 'data'" #cell="{ record }">
                <a-typography-paragraph copyable>{{ JSON.stringify(record.data) }}</a-typography-paragraph>
              </template>
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
  } from '@/api/data-factory'
  import { usePagination, useTable } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, ref } from 'vue'
  import { executionItemColumns, executionTableColumns } from './config'

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
    if (record.cleanup_status === 1) {
      Message.info('当前执行记录已清理，无需重复清理')
      return
    }
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

  onMounted(() => {
    enumStore.getEnum()
    doRefresh()
  })
</script>
