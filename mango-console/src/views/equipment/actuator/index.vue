<template>
  <TableBody ref="tableBody" title="执行器列表">
    <template #header></template>

    <template #default>
      <a-tabs>
        <template #extra>
          <a-space>
            <div> </div>
          </a-space>
        </template>
      </a-tabs>
      <a-table
        :bordered="false"
        :loading="table.tableLoading.value"
        :data="table.dataList"
        :columns="tableColumns"
        :pagination="false"
        :rowKey="rowKey"
        @selection-change="onSelectionChange"
      >
        <template #columns>
          <a-table-column
            v-for="item of tableColumns"
            :key="item.key"
            :align="item.align"
            :title="item.title"
            :width="item.width"
            :data-index="item.key"
            :fixed="item.fixed"
          >
            <template v-if="item.key === 'index'" :class="record" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <template v-if="record.username === 'admin'">
                <a-space>
                  <a-button type="text" size="mini" @click="onReceive(record)">领取</a-button>
                  <a-button
                    status="danger"
                    type="text"
                    size="mini"
                    @click="onDelete(record)"
                    disabled
                    >下线
                  </a-button>
                </a-space>
              </template>
              <template v-if="record.username !== 'admin'">
                <a-space>
                  <a-button
                    status="danger"
                    type="text"
                    size="mini"
                    @click="onDelete(record)"
                    disabled
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
