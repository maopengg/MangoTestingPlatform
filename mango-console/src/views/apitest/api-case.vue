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
                      @change="doRefresh"
                    />
                  </template>
                  <template v-else-if="item.type === 'select' && item.key === 'module_name'">
                    <a-select
                      style="width: 150px"
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      :options="apiCaseData.moduleList"
                      :field-names="fieldNames"
                      value-key="key"
                      allow-clear
                      allow-search
                      @change="doRefresh"
                    />
                  </template>
                  <template v-else-if="item.type === 'select' && item.key === 'case_people'">
                    <a-select
                      style="width: 150px"
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      :options="apiCaseData.userList"
                      :field-names="fieldNames"
                      value-key="key"
                      allow-clear
                      allow-search
                      @change="doRefresh"
                    />
                  </template>
                  <template v-else-if="item.type === 'select' && item.key === 'status'">
                    <a-select
                      style="width: 150px"
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      :options="apiCaseData.systemStatus"
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
                  <a-modal
                    v-model:visible="apiCaseData.visible"
                    @ok="handleOk"
                    @cancel="handleCancel"
                  >
                    <template #title> 设为定时任务 </template>
                    <div>
                      <a-select
                        v-model="apiCaseData.value"
                        placeholder="请选择定时任务进行绑定"
                        :options="apiCaseData.scheduledName"
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
              >
                <template v-if="item.key === 'index'" #cell="{ record }">
                  {{ record.id }}
                </template>
                <template v-else-if="item.key === 'project'" #cell="{ record }">
                  {{ record.project?.name }}
                </template>
                <template v-else-if="item.key === 'module_name'" #cell="{ record }">
                  {{
                    record.module_name?.superior_module
                      ? record.module_name?.superior_module + '/'
                      : ''
                  }}{{ record.module_name?.name }}
                </template>
                <template v-else-if="item.key === 'case_people'" #cell="{ record }">
                  {{ record.case_people?.nickname }}
                </template>
                <template v-else-if="item.key === 'level'" #cell="{ record }">
                  <a-tag color="orange" size="small">
                    {{
                      record.level !== null ? apiCaseData.enumCaseLevel[record.level].title : '-'
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
      <ModalDialog ref="modalDialogRef" :title="apiCaseData.actionTitle" @confirm="onDataForm">
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
              <template v-else-if="item.type === 'select' && item.key === 'project'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="project.data"
                  :field-names="fieldNames"
                  @change="getProjectModule(item.value)"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'module_name'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="apiCaseData.moduleList"
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
                  :options="apiCaseData.userList"
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
                  :options="apiCaseData.enumCaseLevel"
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
  import { get, post, put, deleted } from '@/api/http'
  import {
    apiCase,
    apiCaseCody,
    apiCaseRun,
    userNickname,
    userModuleGetAll,
    systemEnumStatus,
    systemTasksBatchSetCases,
    systemScheduledName,
    systemEnumCaseLevel,
    apiCaseBatchRun,
  } from '@/api/url'
  import {
    usePagination,
    useRowKey,
    useRowSelection,
    useTable,
    useTableColumn,
  } from '@/hooks/table'
  import { FormItem, ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, ref, nextTick, reactive } from 'vue'
  import { useProject } from '@/store/modules/get-project'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { useRouter } from 'vue-router'
  import { useTestObj } from '@/store/modules/get-test-obj'
  import { useProjectModule } from '@/store/modules/project_module'
  import { usePageData } from '@/store/page-data'

  const projectModule = useProjectModule()

  const router = useRouter()
  const project = useProject()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const testObj = useTestObj()

  const apiCaseData = reactive({
    actionTitle: '添加接口',
    isAdd: false,
    updateId: 0,
    userList: [],
    systemStatus: [],
    moduleList: projectModule.data,
    scheduledName: [],
    enumCaseLevel: [],
    value: null,
    visible: false,
  })
  const conditionItems: Array<FormItem> = reactive([
    {
      key: 'id',
      label: 'ID',
      type: 'input',
      placeholder: '请输入用例ID',
      value: '',
      reset: function () {
        this.value = ''
      },
    },
    {
      key: 'name',
      label: '用例名称',
      type: 'input',
      placeholder: '请输入用例名称',
      value: '',
      reset: function () {
        this.value = ''
      },
    },
    {
      key: 'module_name',
      label: '模块',
      value: '',
      type: 'select',
      placeholder: '请先选择项目',
      optionItems: apiCaseData.moduleList,
      reset: function () {},
    },
    {
      key: 'case_people',
      label: '用例负责人',
      value: '',
      type: 'select',
      placeholder: '请选择用例负责人',
      optionItems: apiCaseData.moduleList,
      reset: function () {},
    },
    {
      key: 'status',
      label: '测试结果',
      value: '',
      type: 'select',
      placeholder: '请选择测试结果',
      optionItems: apiCaseData.moduleList,
      reset: function () {},
    },
  ])
  const formItems: FormItem[] = reactive([
    {
      label: '项目名称',
      key: 'project',
      value: '',
      placeholder: '请选择项目名称',
      required: true,
      type: 'select',
      validator: function () {
        if (!this.value && this.value !== '0') {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '模块',
      key: 'module_name',
      value: '',
      placeholder: '请选择测试模块',
      required: true,
      type: 'select',
      validator: function () {
        if (!this.value) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '用例名称',
      key: 'name',
      value: '',
      type: 'input',
      required: true,
      placeholder: '请输入用例名称',
      validator: function () {
        if (!this.value) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '用例级别',
      key: 'level',
      value: '',
      type: 'select',
      required: true,
      placeholder: '请设置用例级别',
      validator: function () {
        if (!this.value && this.value !== 0) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '用例负责人',
      key: 'case_people',
      value: '',
      type: 'select',
      required: true,
      placeholder: '请设置用例负责人',
      validator: function () {
        if (!this.value) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
  ])

  const tableColumns = useTableColumn([
    table.indexColumn,
    {
      title: '项目',
      key: 'project',
      dataIndex: 'project',
      width: 110,
    },
    {
      title: '模块',
      key: 'module_name',
      dataIndex: 'module_name',
      width: 160,
    },
    {
      title: '用例名称',
      key: 'name',
      dataIndex: 'name',
      align: 'left',
      width: 250,
    },
    {
      title: '用例顺序',
      key: 'case_flow',
      align: 'left',
    },
    {
      title: '级别',
      key: 'level',
      dataIndex: 'level',
    },
    {
      title: '负责人',
      key: 'case_people',
      dataIndex: 'case_people',
      width: 80,
    },
    {
      title: '状态',
      key: 'status',
      dataIndex: 'status',
    },
    {
      title: '操作',
      key: 'actions',
      dataIndex: 'actions',
      fixed: 'right',
      width: 60,
    },
  ])

  function doRefresh() {
    get({
      url: apiCase,
      data: () => {
        let value = getFormItems(conditionItems)
        value['page'] = pagination.page
        value['pageSize'] = pagination.pageSize
        return value
      },
    })
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
    apiCaseData.actionTitle = '添加公共参数'
    apiCaseData.isAdd = true
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
      content: '是否要删除此页面？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleted({
          url: apiCase,
          data: () => {
            return {
              id: '[' + data.id + ']',
            }
          },
        })
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function onUpdate(item: any) {
    apiCaseData.actionTitle = '编辑用例'
    apiCaseData.isAdd = false
    apiCaseData.updateId = item.id
    getProjectModule(item.project.id)
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

  function getProjectModule(projectId: number) {
    doRefresh()
    get({
      url: userModuleGetAll,
      data: () => {
        return {
          project_id: projectId,
        }
      },
    })
      .then((res) => {
        apiCaseData.moduleList = res.data
      })
      .catch(console.log)
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      modalDialogRef.value?.toggle()
      let value = getFormItems(formItems)
      if (apiCaseData.isAdd) {
        value['front_custom'] = []
        value['front_sql'] = []
        value['posterior_sql'] = []
        post({
          url: apiCase,
          data: () => {
            return value
          },
        })
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      } else {
        put({
          url: apiCase,
          data: () => {
            value['id'] = apiCaseData.updateId
            return value
          },
        })
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      }
    }
  }

  function getNickName() {
    get({
      url: userNickname,
      data: () => {
        return {}
      },
    })
      .then((res) => {
        apiCaseData.userList = res.data
      })
      .catch(console.log)
  }

  function caseRun(record: any) {
    if (testObj.selectValue == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    Message.loading('正在执行用例请稍后~')
    get({
      url: apiCaseRun,
      data: () => {
        return {
          case_id: record.id,
          test_obj_id: testObj.selectValue,
          case_sort: null,
        }
      },
    })
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
      Message.error('请选择要' + name + '的用例数据')
      return
    }
    Message.loading('正在执行用例请稍后~')
    post({
      url: apiCaseBatchRun,
      data: () => {
        return {
          case_id_list: selectedRowKeys.value,
          test_obj_id: testObj.selectValue,
        }
      },
    })
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
      path: '/apitest/details',
      query: {
        case_id: record.id,
        project: record.project.id,
        test_suite_id: record.test_suite_id,
      },
    })
  }

  function pageStepsCody(record: any) {
    post({
      url: apiCaseCody,
      data: () => {
        return {
          case_id: record.id,
        }
      },
    })
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
    apiCaseData.visible = true
  }
  const handleOk = () => {
    post({
      url: systemTasksBatchSetCases,
      data: () => {
        return {
          case_id_list: JSON.stringify(selectedRowKeys.value),
          scheduled_tasks_id: apiCaseData.value,
        }
      },
    })
      .then((res) => {
        Message.success(res.msg)
        apiCaseData.visible = false
      })
      .catch(console.log)
  }
  const handleCancel = () => {
    apiCaseData.visible = false
  }
  function scheduledName() {
    get({
      url: systemScheduledName,
      data: () => {
        return {
          case_type: 1,
        }
      },
    })
      .then((res) => {
        apiCaseData.scheduledName = res.data
      })
      .catch(console.log)
  }
  function status() {
    get({
      url: systemEnumStatus,
      data: () => {
        return {}
      },
    })
      .then((res) => {
        apiCaseData.systemStatus = res.data
      })
      .catch(console.log)
  }
  function enumCaseLevel() {
    get({
      url: systemEnumCaseLevel,
      data: () => {
        return {}
      },
    })
      .then((res) => {
        apiCaseData.enumCaseLevel = res.data
      })
      .catch(console.log)
  }
  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      getNickName()
      status()
      scheduledName()
      enumCaseLevel()
    })
  })
</script>
