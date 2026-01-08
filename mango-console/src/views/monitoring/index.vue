<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader
        :show-filter="true"
        title="脚本运行器"
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
                  @blur="() => doRefresh()"
                />
              </template>
              <template v-else-if="item.type === 'select'">
                <a-select
                  style="width: 150px"
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="enumStore.monitoring_task_status"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'cascader' && item.key === 'project_product'">
                <a-cascader
                  style="width: 150px"
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="projectInfo.projectProduct"
                  value-key="key"
                  allow-clear
                  allow-search
                  @change="doRefresh(item.value, true)"
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>

    <template #default>
      <a-tabs>
        <template #extra>
          <div>
            <a-space>
              <a-button type="primary" size="small" @click="onAdd">新增</a-button>
              <a-button status="danger" size="small" @click="onDelete(null)">批量删除</a-button>
            </a-space>
          </div>
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
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ record?.project_product?.project?.name + '/' + record?.project_product?.name }}
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="getStatusColor(record.status)" size="small">{{
                enumStore.monitoring_task_status[record.status].title
              }}</a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-space>
                <a-button
                  type="text"
                  size="mini"
                  class="custom-mini-btn"
                  :disabled="record.status === 1"
                  @click="onStart(record)"
                  >启动</a-button
                >
                <a-button
                  type="text"
                  size="mini"
                  class="custom-mini-btn"
                  :disabled="record.status !== 1"
                  @click="onStop(record)"
                  >停止</a-button
                >
                <a-dropdown trigger="hover">
                  <a-button size="mini" type="text">···</a-button>
                  <template #content>
                    <a-doption>
                      <a-button
                        type="text"
                        size="mini"
                        class="custom-mini-btn"
                        @click="onUpdate(record)"
                        >编辑</a-button
                      >
                    </a-doption>
                    <a-doption>
                      <a-button
                        type="text"
                        size="mini"
                        class="custom-mini-btn"
                        @click="onLogs(record)"
                        >日志</a-button
                      >
                    </a-doption>
                    <a-doption>
                      <a-button
                        type="text"
                        size="mini"
                        class="custom-mini-btn"
                        @click="onViewFile(record)"
                        >文件</a-button
                      >
                    </a-doption>
                    <a-doption>
                      <a-button
                        status="danger"
                        type="text"
                        size="mini"
                        class="custom-mini-btn"
                        @click="onDelete(record)"
                        >删除</a-button
                      >
                    </a-doption>
                  </template>
                </a-dropdown>
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

  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
          :label="item.label"
          v-for="item of filteredFormItems"
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
          <template v-else-if="item.type === 'cascader'">
            <a-cascader
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="projectInfo.projectProduct"
              allow-search
              allow-clear
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
    :footer="false"
  >
    <template #title>
      <div class="log-drawer-title">
        <span>任务日志</span>
        <a-space>
          <a-button size="small" @click="onDownloadLogs">下载</a-button>
          <a-button size="small" type="primary" @click="onRefreshLogs">刷新</a-button>
        </a-space>
      </div>
    </template>
    <div class="log-drawer-body">
      <CodeEditor
        ref="logEditorRef"
        v-model="logDrawer.codeText"
        placeholder="日志内容"
        :codeStyle="{ height: '100%' }"
        :dark="true"
      />
    </div>
  </a-drawer>

  <a-drawer
    :width="1000"
    :visible="fileDrawer.visible"
    placement="right"
    @cancel="onFileCancel"
    unmountOnClose
    :footer="false"
  >
    <template #title>
      <div class="log-drawer-title">
        <span>任务文件</span>
        <a-space>
          <a-button size="small" @click="onFileCancel">取消</a-button>
          <a-button size="small" type="primary" @click="onFileSave">保存</a-button>
        </a-space>
      </div>
    </template>
    <div class="log-drawer-body">
      <CodeEditor
        ref="fileEditorRef"
        v-model="fileDrawer.codeText"
        placeholder="脚本内容"
        :codeStyle="{ height: '100%' }"
        :dark="true"
      />
    </div>
  </a-drawer>
</template>

<script lang="ts" setup>
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
  import { ModalDialogType } from '@/types/components'
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { getFormItems } from '@/utils/datacleaning'
  import { conditionItems, formItems, tableColumns } from './config'
  import CodeEditor from '@/components/CodeEditor.vue'
  import { useProject } from '@/store/modules/get-project'
  import {
    deleteMonitoringTask,
    downloadMonitoringTaskLog,
    getMonitoringTask,
    getMonitoringTaskDetail,
    getMonitoringTaskLogs,
    postMonitoringTask,
    postMonitoringTaskStart,
    postMonitoringTaskStop,
    putMonitoringTask,
  } from '@/api/monitoring/task'
  import { useEnum } from '@/store/modules/get-enum'
  import { fieldNames } from '@/setting'

  const projectInfo = useProject()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const logEditorRef = ref<any>(null)
  const fileEditorRef = ref<any>(null)
  const pagination = usePagination(doRefresh)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const enumStore = useEnum()
  const filteredFormItems = computed(() =>
    data.isAdd ? formItems : formItems.filter((it) => it.key !== 'script_content')
  )

  const data: any = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
  })

  const logDrawer = reactive({
    visible: false,
    codeText: '',
    taskId: 0,
  })

  const fileDrawer = reactive({
    visible: false,
    codeText: '',
    taskId: 0,
    task: null as any,
  })

  function getStatusColor(status: number) {
    const map: Record<number, string> = {
      0: 'arcoblue', // 待执行
      1: 'green', // 运行中
      2: 'gray', // 已停止
      3: 'red', // 失败
      4: 'orangered', // 已完成
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
        if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
        } else {
          it.value = propName ?? ''
        }
      })
      // 更新时默认不覆盖脚本内容，需用户手动粘贴
      const scriptItem = formItems.find((it) => it.key === 'script_content')
      if (scriptItem) scriptItem.value = ''
    })
  }

  function doRefresh(projectProductId: number | string | null = null, bool_ = false) {
    const value = getFormItems(conditionItems)
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    if (projectProductId && bool_) {
      value['project_product'] = projectProductId
    }
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

  function scrollToBottom() {
    // 使用多次 nextTick 和 setTimeout 确保 DOM 完全渲染后再滚动
    nextTick(() => {
      setTimeout(() => {
        // 方法1: 使用 CodeEditor 暴露的 scrollToBottom 方法
        if (logEditorRef.value && logEditorRef.value.scrollToBottom) {
          logEditorRef.value.scrollToBottom()
          return
        }
        // 方法2: 通过 ref 访问 CodeMirror 实例
        if (logEditorRef.value) {
          const codemirrorInstance = logEditorRef.value.codemirror
          if (codemirrorInstance && codemirrorInstance.scrollDOM) {
            codemirrorInstance.scrollDOM.scrollTop = codemirrorInstance.scrollDOM.scrollHeight
            return
          }
        }
        // 方法3: 通过 DOM 查询直接访问滚动容器
        const scrollContainer = document.querySelector('.log-drawer-body .cm-scroller')
        if (scrollContainer) {
          ;(scrollContainer as HTMLElement).scrollTop = (
            scrollContainer as HTMLElement
          ).scrollHeight
        }
      }, 300)
    })
  }

  function fetchLogs() {
    if (!logDrawer.taskId) return
    getMonitoringTaskLogs(logDrawer.taskId, 300)
      .then((res) => {
        logDrawer.codeText = (res.data || []).join('')
        scrollToBottom()
      })
      .catch(console.log)
  }

  // 监听日志内容变化，自动滚动到底部
  watch(
    () => logDrawer.codeText,
    () => {
      if (logDrawer.visible) {
        scrollToBottom()
      }
    }
  )

  // 监听 drawer 打开状态，打开时滚动到底部
  watch(
    () => logDrawer.visible,
    (visible) => {
      if (visible && logDrawer.codeText) {
        scrollToBottom()
      }
    }
  )

  function onLogs(record: any) {
    logDrawer.taskId = record.id
    logDrawer.visible = true
    // drawer 打开后再加载日志，确保滚动功能正常
    nextTick(() => {
      fetchLogs()
    })
  }

  function onRefreshLogs() {
    fetchLogs()
  }

  function onDownloadLogs() {
    if (!logDrawer.taskId) {
      Message.warning('请先选择任务')
      return
    }
    downloadMonitoringTaskLog(logDrawer.taskId)
      .then((res: any) => {
        // 后端返回的是文件流
        const blob = new Blob([res.data], { type: 'text/plain;charset=utf-8' })
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `任务日志_${logDrawer.taskId}_${new Date().getTime()}.log`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
        Message.success('日志下载成功')
      })
      .catch((error) => {
        console.log(error)
        Message.error('下载失败')
      })
  }

  function onViewFile(record: any) {
    fileDrawer.taskId = record.id
    fileDrawer.task = record
    fileDrawer.visible = true
    // 如果 record 中已经有 script_content，直接使用
    if (record.script_content) {
      fileDrawer.codeText = record.script_content
    } else {
      // 否则从后端获取任务详情
      getMonitoringTaskDetail(record.id)
        .then((res: any) => {
          if (res.data && res.data.script_content) {
            fileDrawer.codeText = res.data.script_content
          } else {
            fileDrawer.codeText = '暂无脚本内容'
          }
        })
        .catch((error) => {
          console.log(error)
          Message.error('获取文件内容失败')
          fileDrawer.codeText = '获取文件内容失败'
        })
    }
  }

  function onFileCancel() {
    fileDrawer.visible = false
  }

  function onFileSave() {
    if (!fileDrawer.taskId || !fileDrawer.task) {
      Message.warning('未选择任务')
      return
    }
    const payload: any = {
      id: fileDrawer.taskId,
      name: fileDrawer.task.name,
      description: fileDrawer.task.description || '',
      script_content: fileDrawer.codeText,
    }
    putMonitoringTask(payload)
      .then((res: any) => {
        Message.success(res.msg || '保存成功')
        fileDrawer.visible = false
        doRefresh()
      })
      .catch((error) => {
        console.log(error)
        Message.error('保存失败')
      })
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

  .log-drawer-title {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    gap: 16px;
  }

  .log-drawer-body {
    height: 100%;
    display: flex;
    flex-direction: column;

    :deep(.cm-editor) {
      height: 100%;

      .cm-scroller {
        overflow: auto !important;
      }
    }
  }
</style>
