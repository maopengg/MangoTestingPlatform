<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader :show-filter="true" title="预警监控" @search="doRefresh" @reset-search="onResetSearch">
        <template #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="doRefresh">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input v-model="item.value" :placeholder="item.placeholder" @blur="() => doRefresh()" />
              </template>
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>

    <template #default>
      <a-tabs>
        <template #extra>
          <a-space>
            <a-button type="primary" size="small" @click="onAdd">新增</a-button>
            <a-button status="danger" size="small" @click="onDelete(null)">批量删除</a-button>
          </a-space>
        </template>
      </a-tabs>
      <a-table
        :bordered="false"
        :row-selection="{ selectedRowKeys, showCheckedAll }"
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
            :ellipsis="item.ellipsis"
            :tooltip="item.tooltip"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="getStatusColor(record.status)" size="small">{{ record.status }}</a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-button
                type="text"
                size="mini"
                class="custom-mini-btn"
                :disabled="record.status === 'running'"
                @click="onStart(record)"
                >启动</a-button
              >
              <a-button
                type="text"
                size="mini"
                class="custom-mini-btn"
                :disabled="record.status !== 'running'"
                @click="onStop(record)"
                >停止</a-button
              >
              <a-button type="text" size="mini" class="custom-mini-btn" @click="onLogs(record)">日志</a-button>
              <a-button status="danger" type="text" size="mini" class="custom-mini-btn" @click="onDelete(record)"
                >删除</a-button
              >
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>
    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>

  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
          :label="item.label"
          v-for="item of formItems"
          :key="item.key"
        >
          <template v-if="item.type === 'input'">
            <a-input :placeholder="item.placeholder" v-model="item.value" />
          </template>
          <template v-else-if="item.type === 'textarea'">
            <a-textarea
              v-model="item.value"
              :placeholder="item.placeholder"
              :auto-size="{ minRows: 3, maxRows: 6 }"
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>

  <a-drawer
    :width="1000"
    :visible="logDrawer.visible"
    placement="right"
    @cancel="logDrawer.visible = false"
    unmountOnClose
  >
  >
    <template #title>任务日志</template>
    <div class="log-drawer-body">
      <div class="log-drawer-actions">
        <a-button size="small" type="primary" @click="onRefreshLogs">刷新</a-button>
      </div>
      <div class="log-drawer-editor">
        <CodeEditor v-model="logDrawer.codeText" placeholder="日志内容" :lineHeight="600" />
      </div>
    </div>
  </a-drawer>
</template>

<script lang="ts" setup>
  import { Message, Modal } from '@arco-design/web-vue'
  import { nextTick, onMounted, reactive, ref } from 'vue'
  import { FormItem, ModalDialogType } from '@/types/components'
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { getFormItems } from '@/utils/datacleaning'
  import { conditionItems, formItems, tableColumns } from './config'
  import CodeEditor from '@/components/CodeEditor.vue'
  import {
    deleteMonitoringTask,
    getMonitoringTask,
    getMonitoringTaskLogs,
    postMonitoringTask,
    postMonitoringTaskStart,
    postMonitoringTaskStop,
    putMonitoringTask,
  } from '@/api/monitoring/task'

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})

  const data: any = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
  })

  const logDrawer = reactive({
    visible: false,
    codeText: '',
  })

  function getStatusColor(status: string) {
    const map: Record<string, string> = {
      running: 'green',
      queued: 'arcoblue',
      stopped: 'gray',
      failed: 'red',
      completed: 'orangered',
    }
    return map[status] || 'arcoblue'
  }

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = ''
    })
    doRefresh()
  }

  function onAdd() {
    data.actionTitle = '新增'
    data.isAdd = true
    modalDialogRef.value?.toggle()
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = ''
      }
    })
  }

  function onDelete(record: any) {
    const batch = record === null
    if (batch) {
      if (selectedRowKeys.value.length === 0) {
        Message.error('请选择要删除的数据')
        return
      }
    }
    Modal.confirm({
      title: '提示',
      content: '是否要删除此任务？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteMonitoringTask(batch ? selectedRowKeys.value : record.id)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
          .finally(() => {
            doRefresh()
            if (batch) {
              selectedRowKeys.value = []
            }
          })
      },
    })
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      const value = getFormItems(formItems)
      if (data.isAdd) {
        postMonitoringTask(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      } else {
        value['id'] = data.updateId
        putMonitoringTask(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      }
    } else {
      modalDialogRef.value?.setConfirmLoading(false)
    }
  }

  function onUpdate(item: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = item[it.key]
        it.value = propName ?? ''
      })
      // 更新时默认不覆盖脚本内容，需用户手动粘贴
      const scriptItem = formItems.find((it) => it.key === 'script_content')
      if (scriptItem) scriptItem.value = ''
    })
  }

  function doRefresh() {
    const value = getFormItems(conditionItems)
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    getMonitoringTask(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
  }

  function onStart(record: any) {
    postMonitoringTaskStart(record.id)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function onStop(record: any) {
    postMonitoringTaskStop(record.id)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function onLogs(record: any) {
    getMonitoringTaskLogs(record.id, 300)
      .then((res) => {
        logDrawer.codeText = (res.data || []).join('')
        logDrawer.visible = true
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
    })
  })
</script>

<style scoped lang="less">
.custom-mini-btn {
  padding: 0 4px;
}
</style>
