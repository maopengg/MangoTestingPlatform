<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader
            :show-filter="true"
            title="测试用例"
            @search="doRefresh"
            @reset-search="onResetSearch"
          >
            <template #search-content>
              <a-form layout="inline" :model="{}" @keyup.enter="doRefresh">
                <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
                  <template v-if="item.type === 'input'">
                    <a-input
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      @blur="doRefresh"
                    />
                  </template>
                  <template v-else-if="item.type === 'select' && item.key === 'project_product'">
                    <a-select
                      style="width: 140px"
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      :options="projectInfo.projectProductList"
                      :field-names="fieldNames"
                      value-key="key"
                      allow-clear
                      allow-search
                      @change="doRefresh(item.value, true)"
                    />
                  </template>
                  <template v-else-if="item.type === 'select' && item.key === 'module'">
                    <a-select
                      style="width: 140px"
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      :options="productModule.data"
                      :field-names="fieldNames"
                      value-key="key"
                      allow-clear
                      allow-search
                      @change="doRefresh"
                    />
                  </template>
                  <template v-else-if="item.type === 'select' && item.key === 'case_people'">
                    <a-select
                      style="width: 140px"
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
                  <template v-else-if="item.type === 'select' && item.key === 'status'">
                    <a-select
                      style="width: 140px"
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      :options="status.data"
                      :field-names="fieldNames"
                      value-key="key"
                      allow-clear
                      allow-search
                      @change="doRefresh"
                    />
                  </template>
                  <template v-if="item.type === 'date'">
                    <a-date-picker v-model="item.value" />
                  </template>
                  <template v-if="item.type === 'time'">
                    <a-time-picker v-model="item.value" value-format="HH:mm:ss" />
                  </template>
                  <template v-if="item.type === 'check-group'">
                    <a-checkbox-group v-model="item.value">
                      <a-checkbox v-for="it of item.optionItems" :value="it.value" :key="it.value">
                        {{ item.label }}
                      </a-checkbox>
                    </a-checkbox-group>
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
                  <a-button status="success" size="small" @click="onCaseBatchRun"
                    >批量执行</a-button
                  >
                </div>
                <div>
                  <a-button status="warning" size="small" @click="handleClick"
                    >设为定时任务</a-button
                  >
                  <a-modal v-model:visible="data.visible" @ok="handleOk" @cancel="handleCancel">
                    <template #title> 设为定时任务 </template>
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
                  </a-modal>
                </div>
                <div>
                  <a-button type="primary" size="small" @click="onAddPage">新增</a-button>
                </div>
                <div>
                  <a-button status="danger" size="small" @click="onDeleteItems">批量删除</a-button>
                </div>
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
                <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                  {{ record.project_product?.project?.name + '/' + record.project_product?.name }}
                </template>
                <template v-else-if="item.key === 'module'" #cell="{ record }">
                  {{ record.module?.superior_module ? record.module?.superior_module + '/' : ''
                  }}{{ record.module?.name }}
                </template>
                <template v-else-if="item.key === 'case_people'" #cell="{ record }">
                  {{ record.case_people?.nickname }}
                </template>
                <template v-else-if="item.key === 'level'" #cell="{ record }">
                  <a-tag color="orange" size="small">
                    {{
                      record.level !== null ? data.enumCaseLevel[record.level].title : '-'
                    }}</a-tag
                  >
                </template>
                <template v-else-if="item.key === 'status'" #cell="{ record }">
                  <a-tag color="green" size="small" v-if="record.status === 1">通过</a-tag>
                  <a-tag color="red" size="small" v-else-if="record.status === 0">失败</a-tag>
                  <a-tag color="gray" size="small" v-else>未测试</a-tag>
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <a-space>
                    <a-button type="text" size="mini" @click="caseRun(record)">执行</a-button>
                    <a-button type="text" size="mini" @click="onStep(record)">步骤</a-button>
                    <a-dropdown trigger="hover">
                      <a-button type="text" size="mini">···</a-button>
                      <template #content>
                        <a-doption>
                          <a-button type="text" size="mini" @click="onUpdate(record)"
                            >编辑</a-button
                          >
                        </a-doption>
                        <a-doption>
                          <a-button type="text" size="mini" @click="pageStepsCody(record)"
                            >复制</a-button
                          >
                        </a-doption>
                        <a-doption>
                          <a-button
                            status="danger"
                            type="text"
                            size="mini"
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
              v-for="item of formItems"
              :key="item.key"
            >
              <template v-if="item.type === 'input'">
                <a-input :placeholder="item.placeholder" v-model="item.value" />
              </template>
              <template v-else-if="item.type === 'cascader'">
                <a-cascader
                  v-model="item.value"
                  @change="onModuleSelect(item.value)"
                  :placeholder="item.placeholder"
                  :options="projectInfo.projectProduct"
                  allow-search
                  allow-clear
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'module'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="productModule.data"
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
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'level'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="data.enumCaseLevel"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
      </ModalDialog>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { FormItem, ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, ref, nextTick, reactive } from 'vue'
  import { useProject } from '@/store/modules/get-project'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { useRouter } from 'vue-router'
  import { useTestObj } from '@/store/modules/get-test-obj'
  import { useProductModule } from '@/store/modules/project_module'
  import { usePageData } from '@/store/page-data'
  import { tableColumns, formItems, conditionItems } from './config'
  import {
    deleteApiCase,
    getApiCase,
    getApiCaseRun,
    postApiCase,
    postApiCaseBatchRun,
    postApiCaseCody,
    putApiCase,
  } from '@/api/apitest'
  import { getUserNickname } from '@/api/user'
  import {
    getSystemEnumCaseLevel,
    getSystemScheduledName,
    postSystemTasksBatchSetCases,
  } from '@/api/system'
  import { useStatus } from '@/store/modules/status'

  const productModule = useProductModule()
  const status = useStatus()

  const router = useRouter()
  const projectInfo = useProject()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const testObj = useTestObj()

  const data = reactive({
    actionTitle: '添加接口',
    isAdd: false,
    updateId: 0,
    userList: [],
    scheduledName: [],
    enumCaseLevel: [],
    value: null,
    visible: false,
  })

  function doRefresh(projectProductId: number | null = null, bool_ = false) {
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
      })
      .catch(console.log)
  }

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = ''
    })
  }

  function onAddPage() {
    data.actionTitle = '添加公共参数'
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

  function onDelete(data: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此用例？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteApiCase(data.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }
  function onDeleteItems() {
    if (selectedRowKeys.value.length === 0) {
      Message.error('请选择要删除的数据')
      return
    }
    Modal.confirm({
      title: '提示',
      content: '确定要删除此数据吗？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteApiCase(selectedRowKeys.value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }
  function onUpdate(item: any) {
    data.actionTitle = '编辑用例'
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
      modalDialogRef.value?.toggle()
      let value = getFormItems(formItems)
      if (data.isAdd) {
        value['front_custom'] = []
        value['front_sql'] = []
        value['posterior_sql'] = []
        postApiCase(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      } else {
        value['id'] = data.updateId
        putApiCase(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      }
    }
  }

  function getNickName() {
    getUserNickname()
      .then((res) => {
        data.userList = res.data
      })
      .catch(console.log)
  }

  function caseRun(record: any) {
    if (testObj.selectValue == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    Message.loading('正在执行用例请稍后~')
    getApiCaseRun(record.id, testObj.selectValue, null)
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
    doRefresh()
  }
  function onCaseBatchRun() {
    if (testObj.selectValue == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (selectedRowKeys.value.length === 0) {
      Message.error('请选择要执行的用例')
      return
    }
    Message.loading('正在执行用例请稍后~')
    postApiCaseBatchRun(selectedRowKeys.value, testObj.selectValue)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
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
    postSystemTasksBatchSetCases(selectedRowKeys.value, data.value)
      .then((res) => {
        Message.success(res.msg)
        data.visible = false
      })
      .catch(console.log)
  }
  const handleCancel = () => {
    data.visible = false
  }
  function scheduledName() {
    getSystemScheduledName(1)
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

  function enumCaseLevel() {
    getSystemEnumCaseLevel()
      .then((res) => {
        data.enumCaseLevel = res.data
      })
      .catch(console.log)
  }
  onMounted(() => {
    nextTick(async () => {
      getNickName()
      scheduledName()
      await enumCaseLevel()
      await doRefresh()
      productModule.getProjectModule(null)
    })
  })
</script>
