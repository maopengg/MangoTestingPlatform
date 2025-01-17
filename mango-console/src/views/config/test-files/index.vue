<template>
  <a-card>
    <a-space direction="vertical" fill>
      <a-space :style="{ width: '100%' }">
        <div class="container">
          <span>测试文件</span>
        </div>
        <a-upload @before-upload="beforeUpload" :show-file-list="false" />
      </a-space>

      <a-tabs />
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
              <a-button
                type="text"
                size="mini"
                @click="onDownload(record)"
                download="{{ record.file_name }}"
                >下载
              </a-button>
              <a-button status="danger" type="text" size="mini" @click="onDelete(record)"
                >删除</a-button
              >
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-space>
  </a-card>
</template>

<script lang="ts" setup>
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, nextTick } from 'vue'
  import { tableColumns } from './config'
  import { deleteUserFile, getUserFile, postUserFile } from '@/api/system/file_data'
  import { useProject } from '@/store/modules/get-project'
  const pagination = usePagination(doRefresh)
  const { onSelectionChange } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const projectInfo: any = useProject()

  function doRefresh() {
    getUserFile()
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
  }

  // function onDownload(record: any) {
  //   get({
  //     url: userFilesDownload,
  //     data: () => {
  //       return {
  //         project_id: record.project_id,
  //         file_name: record.file_name,
  //       }
  //     },
  //   })
  //     .then((res) => {})
  //     .catch(console.log)
  // }

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此文件？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteUserFile(record.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  const beforeUpload = (file: any) => {
    return new Promise((resolve, reject) => {
      Modal.confirm({
        title: '上传文件',
        content: `确认上传：${file.name}`,
        onOk: () => {
          const formData = new FormData()
          formData.append('test_file', file)
          formData.append('type', '0')
          formData.append('name', file.name)
          postUserFile(formData)
            .then((res) => {
              Message.success(res.msg)
              doRefresh()
              // resolve(true)
            })
            .catch(console.log)
        },
        onCancel: () => reject('cancel'),
      })
    })
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
    })
  })
</script>
<style>
  .container span {
    font-size: 25px;
  }
</style>
