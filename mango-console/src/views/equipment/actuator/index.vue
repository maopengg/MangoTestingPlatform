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
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <template v-if="record.username === 'admin'">
                <a-space>
                  <a-button size="mini" type="text" @click="onReceive(record)">领取</a-button>
                  <a-button
                    disabled
                    size="mini"
                    status="danger"
                    type="text"
                    @click="onDelete(record)"
                    >下线
                  </a-button>
                </a-space>
              </template>
              <template v-if="record.username !== 'admin'">
                <a-space>
                  <a-button
                    disabled
                    size="mini"
                    status="danger"
                    type="text"
                    @click="onDelete(record)"
                    >下线
                  </a-button>
                </a-space>
              </template>
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
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, nextTick } from 'vue'
  import { tableColumns } from './config'
  import { getSystemSocketUserList } from '@/api/system/socket_api'

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

  // function onDelete(data: any) {
  //   Modal.confirm({
  //     title: '提示',
  //     content: '是否要下线此执行器？',
  //     cancelText: '取消',
  //     okText: '删除',
  //     onOk: () => {
  //       deleteSystemSocketUserList(data.id)
  //         .then((res) => {
  //           Message.success(res.msg)
  //           doRefresh()
  //         })
  //         .catch(console.log)
  //     },
  //   })
  // }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
    })
  })
</script>
