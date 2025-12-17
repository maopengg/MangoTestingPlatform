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
              <template v-else-if="item.type === 'select' && item.key === 'module'">
                <a-select
                  v-model="item.value"
                  :field-names="fieldNames"
                  :options="productModule.data"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  style="width: 140px"
                  value-key="key"
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'case_people'">
                <a-select
                  v-model="item.value"
                  :field-names="fieldNames"
                  :options="data.userList"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  style="width: 140px"
                  value-key="key"
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
                  style="width: 140px"
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
                  style="width: 150px"
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
              <a-button size="small" status="success" :loading="caseRunning" @click="onCaseBatchRun"
                >批量执行
              </a-button>
            </div>
            <div>
              <a-button size="small" status="warning" @click="handleClick">设为定时任务</a-button>
              <a-modal v-model:visible="data.visible" @cancel="handleCancel" @ok="handleOk">
                <template #title> 设为定时任务</template>
                <div>
                  <a-select
                    v-model="data.value"
                    :field-names="fieldNames"
                    :options="data.scheduledName"
                    allow-clear
                    allow-search
                    placeholder="请选择定时任务进行绑定"
                    value-key="key"
                  />
                </div>
              </a-modal>
            </div>
            <div>
              <a-button size="small" type="primary" @click="onAdd">新增</a-button>
            </div>
            <div>
              <a-button size="small" status="danger" @click="onDelete(null)">批量删除</a-button>
            </div>
          </a-space>
        </template>
      </a-tabs>
      <a-table
        :bordered="false"
        :columns="tableColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :row-selection="{ selectedRowKeys, showCheckedAll }"
        :rowKey="rowKey"
        @selection-change="onSelectionChange"
      >
        <template #columns>
          <a-table-column
            v-for="item of tableColumns"
            :key="item.key"
            :align="item.align"
            :data-index="item.key"
            :ellipsis="item.ellipsis"
            :fixed="item.fixed"
            :title="item.title"
            :tooltip="item.tooltip"
            :width="item.width"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ record?.project_product?.project?.name + '/' + record?.project_product?.name }}
            </template>
            <template v-else-if="item.key === 'module'" #cell="{ record }">
              {{ record?.module?.superior_module ? record?.module?.superior_module + '/' : ''
              }}{{ record?.module?.name }}
            </template>
            <template v-else-if="item.key === 'case_people'" #cell="{ record }">
              {{ record.case_people?.name }}
            </template>
            <template v-else-if="item.key === 'level'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.level]" size="small">
                {{ record.level !== null ? enumStore.case_level[record.level].title : '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="enumStore.status_colors[record.status]" size="small"
                >{{ enumStore.task_status[record.status].title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-space>
                <a-button
                  size="mini"
                  type="text"
                  class="custom-mini-btn"
                  :loading="caseRunning"
                  @click="caseRun(record)"
                  >执行
                </a-button>
                <a-button size="mini" type="text" class="custom-mini-btn" @click="onStep(record)"
                  >步骤
                </a-button>
                <a-button
                  size="mini"
                  type="text"
                  class="custom-mini-btn"
                  @click="clickSuite(record)"
                  >套件
                </a-button>
                <a-dropdown trigger="hover">
                  <a-button size="mini" type="text">···</a-button>
                  <template #content>
                    <a-doption>
                      <a-button
                        size="mini"
                        type="text"
                        class="custom-mini-btn"
                        @click="onUpdate(record)"
                        >编辑
                      </a-button>
                    </a-doption>
                    <a-doption>
                      <a-button
                        size="mini"
                        type="text"
                        class="custom-mini-btn"
                        @click="pageStepsCody(record)"
                        >复制
                      </a-button>
                    </a-doption>
                    <a-doption>
                      <a-button
                        size="mini"
                        status="danger"
                        class="custom-mini-btn"
                        type="text"
                        @click="onDelete(record)"
                        >删除
                      </a-button>
                    </a-doption>
                  </template>
                </a-dropdown>
              </a-space>
            </template>
          </a-table-column>
        </template>
      </a-table>
      <ParametrizeDrawer
        v-model:initial-data="data.row.parametrize"
        :visible="data.drawerVisible"
        @cancel="data.drawerVisible = false"
        @ok="drawerOk"
      />
    </template>
    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>
  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          v-for="item of formItems"
          :key="item.key"
          :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
          <template v-else-if="item.type === 'cascader'">
            <a-cascader
              v-model="item.value"
              :options="projectInfo.projectProduct"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              @change="onModuleSelect(item.value)"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'module'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="productModule.data"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'case_people'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="data.userList"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
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
  import { onMounted, ref, nextTick, reactive, onUnmounted } from 'vue'
  import { useProject } from '@/store/modules/get-project'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { useRouter } from 'vue-router'
  import { useProductModule } from '@/store/modules/project_module'
  import { usePageData } from '@/store/page-data'
  import { tableColumns, formItems, conditionItems } from './config'

  import { getUserName } from '@/api/user/user'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import {
    getApiCase,
    deleteApiCase,
    postApiCase,
    postApiCaseCody,
    getApiCaseRun,
    postApiCaseBatchRun,
    putApiCase,
  } from '@/api/apitest/case'
  import { postSystemTasksBatchSetCases } from '@/api/system/tasks_details'
  import { getSystemTasksName } from '@/api/system/tasks'

  const productModule = useProductModule()

  const router = useRouter()
  const projectInfo = useProject()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const enumStore = useEnum()
  const userStore = useUserStore()

  const data: any = reactive({
    actionTitle: '新增',
    isAdd: false,
    updateId: 0,
    userList: [],
    scheduledName: [],
    value: null,
    visible: false,
    drawerVisible: false,
    row: {},
  })
  const caseRunning = ref(false)
  const pollingTimer = ref<NodeJS.Timeout | null>(null)

  function clearPollingTimer() {
    if (pollingTimer.value) {
      clearInterval(pollingTimer.value)
      pollingTimer.value = null
    }
  }

  function doRefresh(projectProductId: number | null = null, bool_ = false) {
    clearPollingTimer()
    let value = getFormItems(conditionItems)
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    if (projectProductId && bool_) {
      value['project_product'] = projectProductId
      productModule.getProjectModule(projectProductId)
    }
    getApiCase(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
        const hasRunningItem =
          res.data && Array.isArray(res.data) && res.data.some((item: any) => item.status === 3)

        if (hasRunningItem) {
          // 5秒后再次刷新
          pollingTimer.value = setInterval(() => {
            doRefresh()
          }, 5000)
        }
      })
      .catch(console.log)
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
      content: '是否要删除此用例？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteApiCase(batch ? selectedRowKeys.value : record.id)
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

  function onUpdate(item: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    productModule.getProjectModule(item.project_product.id)
    modalDialogRef.value?.toggle()
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

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(formItems)
      if (data.isAdd) {
        value['front_custom'] = []
        value['front_sql'] = []
        value['posterior_sql'] = []
        value['front_headers'] = []
        postApiCase(value)
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
        putApiCase(value)
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

  function clickSuite(record: any) {
    data.drawerVisible = true
    data.row = record
  }

  function drawerOk(paramData: any) {
    data.drawerVisible = false

    const hasValidData = paramData.some(
      (suite: any) => suite.name || suite.parametrize.some((param: any) => param.key || param.value)
    )

    let value = {
      id: data.row.id,
      parametrize: hasValidData ? paramData : [],
    }
    putApiCase(value)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function getNickName() {
    getUserName()
      .then((res) => {
        data.userList = res.data
      })
      .catch(console.log)
  }

  const caseRun = async (param) => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (caseRunning.value) return
    caseRunning.value = true

    const timeoutId = setTimeout(() => {
      Message.info('测试用例异步执行中，请稍后刷新页面查看该用例的测试结果~')
      caseRunning.value = false
    }, 15000)

    try {
      const res = await getApiCaseRun(param.id, userStore.selected_environment, null)
      clearTimeout(timeoutId)
      Message.success(res.msg)
      doRefresh()
      caseRunning.value = false
    } catch (e) {
      clearTimeout(timeoutId)
      caseRunning.value = false
    }
  }

  const onCaseBatchRun = async () => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (selectedRowKeys.value.length === 0) {
      Message.error('请选择要执行的用例')
      return
    }
    if (caseRunning.value) return
    caseRunning.value = true
    try {
      const res = await postApiCaseBatchRun(selectedRowKeys.value, userStore.selected_environment)
      Message.success(res.msg)
    } catch (e) {
    } finally {
      caseRunning.value = false
      doRefresh()
    }
  }

  function onStep(record: any) {
    const pageData = usePageData()
    pageData.setRecord(record)
    router.push({
      path: '/apitest/case/details',
      query: {
        case_id: record.id,
        project_product: record.project_product.id,
      },
    })
  }

  function pageStepsCody(record: any) {
    postApiCaseCody(record.id)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  const handleClick = () => {
    if (selectedRowKeys.value.length === 0) {
      Message.error('请选择要添加定时任务的用例')
      return
    }
    data.visible = true
  }
  const handleOk = () => {
    postSystemTasksBatchSetCases(selectedRowKeys.value, data.value, 1)
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

  function scheduledName() {
    getSystemTasksName()
      .then((res) => {
        data.scheduledName = res.data
      })
      .catch(console.log)
  }

  function onModuleSelect(projectProductId: number) {
    productModule.getProjectModule(projectProductId)
    formItems.forEach((item: FormItem) => {
      if (item.key === 'module') {
        item.value = ''
      }
    })
  }

  onMounted(() => {
    nextTick(async () => {
      getNickName()
      scheduledName()
      await doRefresh()
      productModule.getProjectModule(null)
    })
  })
  onUnmounted(() => {
    clearPollingTimer()
  })
</script>
