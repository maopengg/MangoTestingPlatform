<template>
  <TableBody ref="tableBody" title="执行器列表">
    <template #header></template>

    <template #default>
      <a-tabs>
        <template #extra>
          <a-space>
            <div></div>
          </a-space>
        </template>
      </a-tabs>
      <a-table
        :bordered="false"
        :columns="tableColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :rowKey="rowKey"
        @selection-change="onSelectionChange"
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
          >
            <template v-if="item.key === 'index'" #cell="{ record }" :class="record">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'is_open'" #cell="{ record }">
              <a-switch
                :beforeChange="(newValue) => onModifyStatus(newValue, record.username)"
                :default-checked="record.is_open === true"
              />
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-space>
                <a-button
                  disabled
                  size="mini"
                  status="danger"
                  type="text"
                  class="custom-mini-btn"
                  @click="onDelete(record)"
                  >下线
                </a-button>
              </a-space>
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

<script lang="ts" setup>
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { Message } from '@arco-design/web-vue'
  import { onMounted, nextTick } from 'vue'
  import { tableColumns } from './config'
  import { getSystemSocketUserList, getSystemSocketPutOpenStatus } from '@/api/system/socket_api'

  const pagination = usePagination(doRefresh)
  const { onSelectionChange } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')

  function doRefresh() {
    getSystemSocketUserList({
      page: pagination.page,
      pageSize: pagination.pageSize,
    })
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
  }

  function onReceive() {
    Message.warning('开发中.....')
  }
  const onModifyStatus = async (newValue: any, id: string) => {
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value: any = false
          await getSystemSocketPutOpenStatus(id, newValue ? 1 : 0)
            .then((res) => {
              Message.success(res.msg)
              value = res.code === 200
            })
            .catch(reject)
          resolve(value)
        } catch (error) {
          reject(error)
        }
      }, 300)
    })
  }
  onMounted(() => {
    nextTick(async () => {
      doRefresh()
    })
  })
</script>
