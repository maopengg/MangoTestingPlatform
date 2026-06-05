<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader
        :show-filter="true"
        title="触发记录"
        @search="doRefresh"
        @reset-search="onResetSearch"
      >
        <template #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="doRefresh">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="doRefresh"
                  @clear="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select'">
                <a-select
                  v-model="item.value"
                  :options="item.optionItems"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  @change="doRefresh"
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>

    <template #default>
      <a-table
        :scroll="{ x: 1600 }"
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
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'time_task'" #cell="{ record }">
              {{ record.time_task_label || record.time_task?.name || '-' }}
            </template>
            <template v-else-if="item.key === 'source_type'" #cell="{ record }">
              <a-tag size="small">{{ record.source_type_name || '-' }}</a-tag>
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="statusColor(record.status)" size="small">
                {{ record.status_name || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  {
                    label: '报告',
                    disabled: !record.test_suite,
                    onClick: () => openReport(record),
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
  import { defineComponent, onMounted } from 'vue'
  import { usePagination, useRowKey, useTable } from '@/hooks/table'
  import { useRouter } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'
  import { getSystemTaskFireRecord } from '@/api/system/tasks'
  import { conditionItems, tableColumns } from './config'

  export default defineComponent({
    name: 'TimingFireRecord',
    setup() {
      const table = useTable()
      const rowKey = useRowKey('id')
      const router = useRouter()
      const pagination = usePagination(doRefresh)

      function doRefresh() {
        const value = getFormItems(conditionItems as any)
        value.page = pagination.page
        value.pageSize = pagination.pageSize
        getSystemTaskFireRecord(value)
          .then((res) => {
            table.handleSuccess(res)
            pagination.setTotalSize((res as any).totalSize)
          })
          .catch(console.log)
      }

      function onResetSearch() {
        conditionItems.forEach((item) => {
          item.value = ''
        })
        doRefresh()
      }

      function statusColor(status: number) {
        if (status === 3) return 'green'
        if (status === 4) return 'red'
        if (status === 1 || status === 2) return 'blue'
        if (status === 5 || status === 6) return 'gray'
        return 'orange'
      }

      function openReport(record: any) {
        const id = record.test_suite?.id || record.test_suite
        if (!id) return
        router.push({
          path: '/report/system/details',
          query: { id },
        })
      }

      onMounted(() => {
        doRefresh()
      })

      return {
        conditionItems,
        tableColumns,
        table,
        pagination,
        rowKey,
        doRefresh,
        onResetSearch,
        statusColor,
        openReport,
      }
    },
  })
</script>
