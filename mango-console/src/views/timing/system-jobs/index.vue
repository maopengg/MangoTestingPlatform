<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader title="系统任务" @search="doRefresh" />
    </template>

    <template #default>
      <a-table
        :scroll="{ x: 1450 }"
        :bordered="false"
        :columns="tableColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :rowKey="rowKey"
      >
        <template #columns>
          <a-table-column
            v-for="item of tableColumns"
            :key="item.key"
            :align="item.align"
            :data-index="item.key"
            :fixed="item.fixed"
            :title="item.title"
            :width="item.width"
            :ellipsis="item.ellipsis"
            :tooltip="item.tooltip"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.key }}
            </template>
            <template v-else-if="item.key === 'source_type'" #cell="{ record }">
              <a-tag size="small">{{ record.source_type_name || '-' }}</a-tag>
            </template>
            <template v-else-if="item.key === 'latest_status'" #cell="{ record }">
              <a-tag v-if="record.latest_fire" :color="statusColor(record.latest_fire.status)" size="small">
                {{ record.latest_fire.status_name || '-' }}
              </a-tag>
              <span v-else>-</span>
            </template>
            <template v-else-if="item.key === 'latest_planned_at'" #cell="{ record }">
              {{ record.latest_fire?.planned_at || '-' }}
            </template>
            <template v-else-if="item.key === 'latest_fired_at'" #cell="{ record }">
              {{ record.latest_fire?.fired_at || '-' }}
            </template>
            <template v-else-if="item.key === 'latest_error_message'" #cell="{ record }">
              {{ record.latest_fire?.error_message || '-' }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  {
                    label: '立即触发',
                    loading: data.triggeringKey === record.key,
                    onClick: () => onTrigger(record),
                  },
                ]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>
    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>
</template>

<script lang="ts">
  import { defineComponent, onMounted, reactive } from 'vue'
  import { usePagination, useRowKey, useTable, useTableColumn } from '@/hooks/table'
  import { getSystemTaskSystemJobs, postSystemTaskSystemJobTrigger } from '@/api/system/tasks'
  import { Message, Modal } from '@arco-design/web-vue'

  const tableColumns = useTableColumn([
    {
      title: '任务标识',
      key: 'index',
      dataIndex: 'index',
      align: 'left',
      width: 190,
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '任务名称',
      key: 'name',
      dataIndex: 'name',
      align: 'left',
      width: 180,
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '任务说明',
      key: 'description',
      dataIndex: 'description',
      align: 'left',
      width: 280,
      ellipsis: true,
      tooltip: true,
    },
    {
      title: 'Cron',
      key: 'cron',
      dataIndex: 'cron',
      width: 130,
    },
    {
      title: '触发类型',
      key: 'source_type',
      dataIndex: 'source_type',
      width: 110,
    },
    {
      title: '下次触发时间',
      key: 'next_fire_at',
      dataIndex: 'next_fire_at',
      width: 180,
    },
    {
      title: '最近状态',
      key: 'latest_status',
      dataIndex: 'latest_status',
      width: 110,
    },
    {
      title: '最近计划时间',
      key: 'latest_planned_at',
      dataIndex: 'latest_planned_at',
      width: 180,
    },
    {
      title: '最近触发时间',
      key: 'latest_fired_at',
      dataIndex: 'latest_fired_at',
      width: 180,
    },
    {
      title: '最近错误',
      key: 'latest_error_message',
      dataIndex: 'latest_error_message',
      align: 'left',
      width: 220,
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '操作',
      key: 'actions',
      dataIndex: 'actions',
      fixed: 'right',
      width: 130,
    },
  ])

  export default defineComponent({
    name: 'TimingSystemJobs',
    setup() {
      const table = useTable()
      const rowKey = useRowKey('key')
      const pagination = usePagination(doRefresh)
      const data = reactive({
        triggeringKey: '',
      })

      function doRefresh() {
        getSystemTaskSystemJobs()
          .then((res) => {
            table.handleSuccess(res)
            pagination.setTotalSize((res as any).totalSize)
          })
          .catch(console.log)
      }

      function statusColor(status: number) {
        if (status === 3) return 'green'
        if (status === 4) return 'red'
        if (status === 1 || status === 2) return 'blue'
        if (status === 5 || status === 6) return 'gray'
        return 'orange'
      }

      function onTrigger(record: any) {
        Modal.confirm({
          title: '确认触发系统任务',
          content: `确认立即触发系统任务「${record.name || record.key}」吗？该操作会立即执行一次并写入触发记录。`,
          okText: '确认触发',
          cancelText: '取消',
          onOk: () => {
            data.triggeringKey = record.key
            postSystemTaskSystemJobTrigger(record.key)
              .then((res) => {
                Message.success(res.msg)
                doRefresh()
              })
              .catch((error) => {
                Message.error(error?.msg || '触发失败')
              })
              .finally(() => {
                data.triggeringKey = ''
              })
          },
        })
      }

      onMounted(() => {
        doRefresh()
      })

      return {
        tableColumns,
        table,
        pagination,
        rowKey,
        data,
        doRefresh,
        statusColor,
        onTrigger,
      }
    },
  })
</script>
