<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader
        :show-filter="true"
        title="python脚本运行器（预警监控&Mock服务）"
        @search="onSearchRefresh"
        @reset-search="onResetSearch"
      >
        <template #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="onSearchRefresh">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="onSearchRefresh"
                  @clear="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="enumStore.monitoring_task_status"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'cascader' && item.key === 'project_product'">
                <ProjectProductSelect
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  @change="(value) => doRefresh(value, true, true)"
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
        :scroll="{ x: 1100 }"
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
              {{ formatProjectProductPath(record?.project_product) }}
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.status]" size="small"
                >{{ enumStore.monitoring_task_status[record.status]?.title || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'is_notice'" #cell="{ record }">
              <a-tag :color="record.is_notice === 1 ? 'green' : 'gray'" size="small">
                {{ record.is_notice === 1 ? '是' : '否' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'notice_group'" #cell="{ record }">
              {{ record.notice_group?.name || '-' }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { label: '启动', hidden: record.status === 1, onClick: () => onStart(record) },
                  { label: '停止', hidden: record.status !== 1, onClick: () => onStop(record) },
                  { label: '日志', onClick: () => onLogs(record) },
                  { label: '编辑', onClick: () => onUpdate(record) },
                  { label: '文件', onClick: () => onViewFile(record) },
                  { label: '删除', danger: true, onClick: () => onDelete(record) },
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

  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
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
            <ProjectProductSelect
              v-model="item.value"
              :placeholder="item.placeholder"
              @change="onProjectChange(item.value)"
            />
          </template>
          <template v-else-if="item.type === 'switch'">
            <a-switch v-model="item.value" :checked-value="1" :unchecked-value="0" />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'notice_group'">
            <a-select
              v-model="item.value"
              :options="data.noticeList"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>

  <BaseSidePanel
    :visible="logDrawer.visible"
    :title="'任务日志'"
    :data="{ taskId: logDrawer.taskId }"
    @update:visible="
      (val) => {
        logDrawer.visible = val
      }
    "
    @cancel="
      () => {
        logDrawer.visible = false
      }
    "
  >
    <template #default>
      <div class="log-drawer-content">
        <div class="log-drawer-body">
          <CodeEditor
            ref="logEditorRef"
            v-model="logCodeText"
            placeholder="日志内容"
            :codeStyle="{ height: '100%' }"
            :dark="true"
          />
        </div>
      </div>
    </template>
    <template #extra-buttons>
      <a-button status="success" :loading="logDownloadLoading" @click="handleDownloadLog"
        >下载</a-button
      >
      <a-button type="primary" :loading="logRefreshLoading" @click="fetchLogData">刷新</a-button>
    </template>
  </BaseSidePanel>

  <BaseSidePanel
    :visible="fileDrawer.visible"
    :title="'任务文件'"
    :data="{ taskId: fileDrawer.taskId, task: fileDrawer.task }"
    @update:visible="
      (val) => {
        fileDrawer.visible = val
      }
    "
    @cancel="onFileCancel"
  >
    <template #default>
      <div class="file-drawer-content">
        <div class="file-drawer-body">
          <CodeEditor
            ref="fileEditorRef"
            v-model="fileDrawer.codeText"
            placeholder="脚本内容"
            :codeStyle="{ height: '100%' }"
            :dark="true"
          />
        </div>
      </div>
    </template>
    <template #extra-buttons>
      <a-button type="primary" :loading="fileSaving" @click="onFileSave">保存</a-button>
    </template>
  </BaseSidePanel>
</template>

<script lang="ts" setup>
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, nextTick, onMounted, reactive, ref } from 'vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import { ModalDialogType } from '@/types/components'
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { getFormItems } from '@/utils/datacleaning'
  import { conditionItems, formItems, tableColumns } from './config'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import { formatProjectProductPath } from '@/utils/business-format'
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
  import { getSystemNoticeName } from '@/api/system/notice_group'

  const modalDialogRef = ref<ModalDialogType | null>(null)

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
    noticeList: [],
  })

  const logCodeText = ref('')
  const logEditorRef = ref<any>(null)
  const logRefreshLoading = ref(false)
  const logDownloadLoading = ref(false)
  const fileSaving = ref(false)

  const logDrawer = reactive({
    visible: false,
    taskId: 0,
  })

  const fileDrawer = reactive({
    visible: false,
    codeText: '',
    taskId: 0,
    task: null as any,
  })

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = ''
    })
    doRefresh(null, false, true)
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
      onBeforeOk: () => {
        return deleteMonitoringTask(batch ? selectedRowKeys.value : record.id)
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
    // 编辑模式下跳过 script_content 的验证
    const itemsToValidate = data.isAdd
      ? formItems
      : formItems.filter((it) => it.key !== 'script_content')

    if (itemsToValidate.every((it) => (it.validator ? it.validator() : true))) {
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
        // 编辑时不包含 script_content 字段
        delete value['script_content']
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
    // 先加载通知组列表
    if (item.project_product?.id) {
      onProjectChange(item.project_product.id)
    }
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = item[it.key]
        if (typeof propName === 'object' && propName !== null) {
          if (it.key === 'project_product') {
            it.value = propName.id
          } else if (it.key === 'notice_group') {
            it.value = propName?.id || ''
          } else {
            it.value = propName.id
          }
        } else {
          it.value = propName ?? ''
        }
      })
      // 更新时默认不覆盖脚本内容，需用户手动粘贴
      const scriptItem = formItems.find((it) => it.key === 'script_content')
      if (scriptItem) scriptItem.value = ''
    })
  }

  function onProjectChange(projectProductId: number | number[]) {
    // 获取项目产品ID（级联选择器可能返回数组）
    let id: number | null = null
    if (Array.isArray(projectProductId)) {
      id = projectProductId[projectProductId.length - 1] as number
    } else if (typeof projectProductId === 'number') {
      id = projectProductId
    }

    if (!id) {
      data.noticeList = []
      // 清空通知组选择
      const noticeGroupItem = formItems.find((it) => it.key === 'notice_group')
      if (noticeGroupItem) noticeGroupItem.value = ''
      return
    }

    getSystemNoticeName(id)
      .then((res) => {
        data.noticeList = (res.data || []).map((item: any) => ({
          key: item.value,
          label: item.label,
          value: item.value,
        }))
      })
      .catch(console.log)
  }

  function onSearchRefresh() {
    doRefresh(null, false, true)
  }

  function doRefresh(projectProductId: any = null, bool_ = false, showLoading = false) {
    if (showLoading) {
      table.tableLoading.value = true
    }
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
      .finally(() => {
        if (showLoading) {
          table.tableLoading.value = false
        }
      })
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

  async function onLogs(record: any) {
    logDrawer.taskId = record.id
    logDrawer.visible = true
    // 等待组件渲染完成后获取日志数据
    nextTick(() => {
      fetchLogData()
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
    if (fileSaving.value) return
    fileSaving.value = true
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
        Message.error('保存失败')
      })
      .finally(() => {
        fileSaving.value = false
      })
  }

  // 日志相关方法
  async function fetchLogData() {
    if (!logDrawer.taskId) return
    if (logRefreshLoading.value) return
    logRefreshLoading.value = true
    try {
      const res = await getMonitoringTaskLogs(logDrawer.taskId, 300)
      logCodeText.value = (res.data || []).join('')
    } catch (error) {
      console.log(error)
    } finally {
      logRefreshLoading.value = false
    }
  }

  async function handleDownloadLog() {
    if (!logDrawer.taskId) {
      Message.warning('请先选择任务')
      return
    }
    if (logDownloadLoading.value) return
    logDownloadLoading.value = true
    try {
      const res: any = await downloadMonitoringTaskLog(logDrawer.taskId)
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
    } catch (error) {
      Message.error('下载失败')
    } finally {
      logDownloadLoading.value = false
    }
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
    })
  })
</script>

<style scoped lang="less">
  .log-drawer-title {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    gap: 16px;
  }

  .log-drawer-body {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    height: 100%;

    :deep(.cm-editor) {
      flex: 1;
      display: flex;
      flex-direction: column;
      min-height: 0;

      .cm-scroller {
        flex: 1;
        overflow-y: auto !important;
        height: auto !important;
      }
    }
  }

  .log-drawer-footer {
    margin-top: 12px;
    padding-bottom: 12px;
    display: flex;
    justify-content: flex-start;
  }

  :deep(.arco-drawer-body) {
    padding: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    height: calc(100vh - 60px) !important;
  }

  .log-drawer-content {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
  }

  /* 自定义滚动条样式 */
  :deep(.log-drawer-body)::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }

  :deep(.log-drawer-body)::-webkit-scrollbar-track {
    background: var(--m-scrollbar-track);
    border-radius: 4px;
  }

  :deep(.log-drawer-body)::-webkit-scrollbar-thumb {
    background: var(--m-scrollbar-thumb);
    border-radius: 4px;
  }

  :deep(.log-drawer-body)::-webkit-scrollbar-thumb:hover {
    background: var(--m-scrollbar-thumb-hover);
  }

  /* CodeMirror编辑器的滚动条 */
  :deep(.cm-scroller)::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }

  :deep(.cm-scroller)::-webkit-scrollbar-track {
    background: var(--m-scrollbar-track);
    border-radius: 4px;
  }

  :deep(.cm-scroller)::-webkit-scrollbar-thumb {
    background: var(--m-scrollbar-thumb);
    border-radius: 4px;
  }

  :deep(.cm-scroller)::-webkit-scrollbar-thumb:hover {
    background: var(--m-scrollbar-thumb-hover);
  }
</style>
