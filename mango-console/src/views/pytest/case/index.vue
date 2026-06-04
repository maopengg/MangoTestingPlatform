<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader
        :show-filter="true"
        title="测试用例"
        @search="doRefresh"
        @reset-search="onResetSearch"
      >
        <template #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="doRefresh">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input v-model="item.value" :placeholder="item.placeholder" @blur="doRefresh" />
              </template>
              <template v-else-if="item.type === 'cascader' && item.key === 'project_product'">
                <a-cascader
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="projectInfo.projectPytest2"
                  value-key="key"
                  allow-clear
                  allow-search
                  @change="onSearchProjectProductChange(item.value)"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'module'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="data.moduleList"
                  value-key="key"
                  allow-clear
                  allow-search
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'file_status'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="enumStore.file_status"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'status'">
                <a-select
                  v-model="item.value"
                  :field-names="fieldNames"
                  :options="enumStore.task_status"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'level'">
                <a-select
                  v-model="item.value"
                  :field-names="fieldNames"
                  :options="enumStore.case_level"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="doRefresh"
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
          <a-space>
            <div>
              <a-button type="primary" size="small" @click="openUpdateModal">更新目录</a-button>
            </div>
            <div>
              <a-button status="warning" size="small" @click="handleClick">设为定时任务</a-button>
            </div>
            <div>
              <a-button size="small" status="danger" @click="onDelete(null)">批量删除</a-button>
            </div>
            <BaseSidePanel
              :visible="data.visible"
              :title="'设为定时任务'"
              @update:visible="
                (val) => {
                  data.visible = val
                }
              "
              @cancel="handleCancel"
            >
              <template #default>
                <div>
                  <a-select
                    v-model="data.value"
                    placeholder="请选择定时任务进行绑定"
                    :options="data.scheduledName"
                    :field-names="fieldNames"
                    value-key="key"
                    allow-clear
                    allow-search
                  />
                </div>
              </template>
              <template #extra-buttons>
                <a-button type="primary" @click="handleOk">确定</a-button>
              </template>
            </BaseSidePanel>
            <ModalDialog
              ref="updateModalRef"
              title="选择项目进行同步"
              @confirm="handleUpdateConfirm"
            >
              <template #content>
                <a-form :model="updateForm">
                  <a-form-item :class="'mango-form-item__require'">
                    <template #label>
                      <span>项目/产品</span>
                    </template>
                    <a-cascader
                      v-model="updateForm.projectId"
                      placeholder="请选择项目/产品"
                      :options="projectInfo.projectPytest2"
                      allow-search
                      allow-clear
                    />
                  </a-form-item>
                </a-form>
              </template>
            </ModalDialog>
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
        :scroll="{ x: 1280 }"
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
              <span
                v-if="record?.project_product?.project_product && record?.project_product?.name"
              >
                {{
                  record.project_product.project_product.project.name +
                  '/' +
                  record.project_product.name
                }}
              </span>
            </template>
            <template v-else-if="item.key === 'module'" #cell="{ record }">
              <span v-if="record?.module?.name">
                <span v-if="record.module.superior_module">
                  {{ record.module.superior_module + '/' }}
                </span>
                {{ record.module.name }}
              </span>
            </template>
            <template v-else-if="item.key === 'case_people'" #cell="{ record }">
              {{ record.case_people?.name }}
            </template>
            <template v-else-if="item.key === 'file_status'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.file_status]" size="small"
                >{{ enumStore.file_status[record.file_status]?.title || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="enumStore.status_colors[record.status]" size="small"
                >{{ enumStore.task_status[record.status]?.title || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'level'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.level]" size="small">
                {{ record.level !== null ? enumStore.case_level[record.level]?.title || '-' : '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { label: '执行', loading: caseRunning, onClick: () => onRun(record) },
                  { label: '文件', onClick: () => onClick(record) },
                  { label: '编辑', onClick: () => onUpdate(record) },
                  { label: '结果', onClick: () => onResult(record) },
                  { label: '删除', danger: true, onClick: () => onDelete(record) },
                ]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
      <BaseSidePanel
        :visible="data.drawerVisible"
        :title="data.isResult ? '查看测试结果' : '编辑代码'"
        :width="1000"
        @update:visible="
          (val) => {
            data.drawerVisible = val
          }
        "
        @cancel="
          () => {
            data.drawerVisible = false
          }
        "
      >
        <template #default>
          <div v-if="!data.isResult">
            <a-tabs
              v-if="data.hasFeatureFile"
              :active-key="data.fileType"
              @change="
                (key) => {
                  data.fileType = key
                  onFileTypeChange()
                }
              "
            >
              <a-tab-pane key="py" title="Python 文件">
                <CodeEditor v-model="data.codeText" placeholder="输入python代码" />
              </a-tab-pane>
              <a-tab-pane key="feature" title="Feature 文件">
                <CodeEditor v-model="data.codeText" placeholder="输入 Gherkin 语法" />
              </a-tab-pane>
            </a-tabs>
            <CodeEditor v-else v-model="data.codeText" placeholder="输入python代码" />
          </div>
          <div v-else>
            <a-collapse
              v-for="item of data?.codeText"
              :bordered="false"
              :key="item?.uuid"
              accordion
              destroy-on-hide
            >
              <a-collapse-item :style="customStyle" :key="item?.uuid">
                <template #header>
                  <div class="custom-header">
                    <span>{{ item?.name }}</span>
                    <span style="width: 20px"></span>
                    <a-tag :color="enumStore.status_colors[item?.status]"
                      >{{ enumStore.task_status[item?.status]?.title || '-' }}
                    </a-tag>
                  </div>
                </template>
                <PytestTestReport :resultData="item" />
              </a-collapse-item>
            </a-collapse>
          </div>
        </template>
        <template #extra-buttons>
          <a-button v-if="!data.isResult" type="primary" @click="drawerOk">保存</a-button>
        </template>
      </BaseSidePanel>
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
          v-for="item of formItems"
          :key="item.key"
        >
          <template v-if="item.type === 'input'">
            <a-input :placeholder="item.placeholder" v-model="item.value" />
          </template>
          <template v-else-if="item.type === 'cascader' && item.key === 'project_product'">
            <a-cascader
              v-model="item.value"
              @change="onPytestProjectName(item.value)"
              :placeholder="item.placeholder"
              :options="projectInfo.projectPytest2"
              allow-search
              allow-clear
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'module'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="data.moduleList"
              value-key="key"
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'file_status'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="enumStore.file_status"
              :field-names="fieldNames"
              value-key="key"
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'level'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="enumStore.case_level"
              :field-names="fieldNames"
              value-key="key"
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'case_people'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="data.userList"
              :field-names="fieldNames"
              value-key="key"
              allow-clear
              allow-search
              @change="doRefresh"
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { FormItem, ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { formItems, tableColumns } from './config'
  import { useEnum } from '@/store/modules/get-enum'
  import {
    deletePytestCase,
    getPytestCase,
    getPytestCaseRead,
    getPytestCaseTest,
    postPytestCaseUpdate,
    postPytestCase,
    postPytestCaseWrite,
    putPytestCase,
  } from '@/api/pytest/case'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import { getUserName } from '@/api/user/user'
  import { useProject } from '@/store/modules/get-project'
  import { postSystemTasksBatchSetCases } from '@/api/system/tasks_details'
  import { getSystemTasksName } from '@/api/system/tasks'
  import useUserStore from '@/store/modules/user'
  import { conditionItems } from '@/views/pytest/case/config'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'

  const projectInfo = useProject()

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const updateModalRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const enumStore = useEnum()
  const userStore = useUserStore()

  const data: any = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
    drawerVisible: false,
    codeText: '',
    moduleList: [],
    scheduledName: [],
    isResult: false,
    visible: false,
    fileType: 'py',
    hasFeatureFile: false,
  })

  const updateForm = reactive({
    projectId: null as number | null,
  })
  const caseRunning = ref(false)
  const pollingTimer = ref<NodeJS.Timeout | null>(null)

  function clearPollingTimer() {
    if (pollingTimer.value) {
      clearInterval(pollingTimer.value)
      pollingTimer.value = null
    }
  }

  const customStyle = reactive({
    borderRadius: '6px',
    marginBottom: '2px',
    border: 'none',
    overflow: 'hidden',
  })
  const handleClick = () => {
    if (selectedRowKeys.value.length === 0) {
      Message.error('请选择要添加定时任务的用例')
      return
    }
    data.visible = true
  }
  const handleOk = () => {
    postSystemTasksBatchSetCases(selectedRowKeys.value, data.value, 2)
      .then((res) => {
        Message.success(res.msg)
        data.visible = false
        doRefresh()
      })
      .catch(console.log)
  }
  const handleCancel = () => {
    data.visible = false
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
      content: '该删除只会删除数据库数据，不会影响git文件！是否要删除此数据？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deletePytestCase(batch ? selectedRowKeys.value : record.id)
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

  function openUpdateModal() {
    updateForm.projectId = null
    updateModalRef.value?.toggle()
  }

  function handleUpdateConfirm() {
    const projectId = Array.isArray(updateForm.projectId)
      ? updateForm.projectId[updateForm.projectId.length - 1]
      : updateForm.projectId

    if (!projectId) {
      Message.error('请选择项目/产品')
      updateModalRef.value?.setConfirmLoading(false)
      return
    }
    Message.loading('文件更新中，请耐心等待10秒左右...')

    postPytestCaseUpdate(projectId)
      .then((res) => {
        updateModalRef.value?.toggle()
        Message.success(res.msg)
        doRefresh()
      })
      .catch((error) => {
        console.log(error)
        Message.error(error?.msg || '同步失败')
      })
      .finally(() => {
        updateModalRef.value?.setConfirmLoading(false)
      })
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(formItems)
      if (data.isAdd) {
        postPytestCase(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      } else {
        value['id'] = data.updateId
        putPytestCase(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch((error) => {
            console.log(error)
          })
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
    if (item.project_product) {
      onPytestProjectName(item.project_product.id)
    }
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = item[it.key]
        if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
        } else {
          it.value = propName
        }
      })
    })
  }

  function doRefresh(projectProductId: number | null = null, bool_ = false) {
    clearPollingTimer()
    const value = getFormItems(conditionItems)
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    if (projectProductId && bool_) {
      value['project_product'] = projectProductId
      data.moduleList = projectInfo.getProjectPytestModule(projectProductId)
    }
    getPytestCase(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
        const hasRunningItem =
          res.data && Array.isArray(res.data) && res.data.some((item: any) => item.status === 3)

        if (hasRunningItem) {
          // 5秒后再次刷新
          pollingTimer.value = setInterval(() => {
            doRefresh(projectProductId, bool_)
          }, 5000)
        }
      })
      .catch(console.log)
  }

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = it.key === 'project_product' || it.key === 'module' ? null : ''
    })
    data.moduleList = []
    doRefresh()
  }

  function onSearchProjectProductChange(projectProductId: any) {
    const moduleItem = conditionItems.find((it) => it.key === 'module')
    if (moduleItem) {
      moduleItem.value = null
    }
    if (projectProductId) {
      data.moduleList = projectInfo.getProjectPytestModule(projectProductId)
    } else {
      data.moduleList = []
    }
    doRefresh(projectProductId, true)
  }

  const onRun = async (param) => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    Message.loading('准备开始执行，执行完成之后，请在右侧按钮结果中查看执行结果~')

    if (caseRunning.value) return
    caseRunning.value = true
    try {
      const res = await getPytestCaseTest(param.id, userStore.selected_environment)
      Message.success(res.msg)
    } catch (e) {
    } finally {
      caseRunning.value = false
      doRefresh()
    }
  }

  function drawerOk() {
    data.drawerVisible = false
    postPytestCaseWrite(data.updateId, data.codeText, data.fileType)
      .then((res) => {
        data.codeText = res.data
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  function onResult(record: any) {
    data.isResult = true
    data.drawerVisible = true
    data.codeText = record.result_data
  }

  function onFileTypeChange() {
    getPytestCaseRead(data.updateId, data.fileType)
      .then((res) => {
        data.codeText = typeof res.data === 'string' ? res.data : JSON.stringify(res.data, null, 2)
      })
      .catch(console.log)
  }

  function onClick(record: any) {
    data.isResult = false
    data.drawerVisible = true
    data.updateId = record.id
    data.fileType = 'py'
    data.hasFeatureFile = !!record.feature_file_path
    getPytestCaseRead(record.id, 'py')
      .then((res) => {
        // 确保传递给CodeMirror的值是字符串类型
        data.codeText = typeof res.data === 'string' ? res.data : JSON.stringify(res.data, null, 2)
      })
      .catch(console.log)
  }

  function onPytestProjectName(projectProductId: any) {
    data.moduleList = projectInfo.getProjectPytestModule(projectProductId)
    formItems.forEach((item: FormItem) => {
      if (item.key === 'module') {
        item.value = ''
      }
    })
  }

  function getNickName() {
    getUserName()
      .then((res) => {
        data.userList = res.data
      })
      .catch(console.log)
  }

  function scheduledName() {
    getSystemTasksName()
      .then((res) => {
        data.scheduledName = res.data
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      getNickName()
      onPytestProjectName(null)
      scheduledName()
    })
  })
  onUnmounted(() => {
    clearPollingTimer()
  })
</script>
<style lang="less" scoped>
  .custom-header {
    display: flex;
    align-items: center;
    gap: 12px; /* 控制标签间距 */
    font-size: 14px;
  }
</style>
