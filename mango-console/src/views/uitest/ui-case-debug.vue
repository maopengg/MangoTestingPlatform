<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader :show-filter="true" title="Ui自动化用例" @search="onSearch" @reset-search="onResetSearch">
            <template #search-content>
              <a-form layout="inline" :model="{}">
                <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
                  <template v-if="item.render">
                    <FormRender :render="item.render" :formItem="item" />
                  </template>
                  <template v-else>
                    <template v-if="item.type === 'input'">
                      <a-input v-model="item.value.value" :placeholder="item.placeholder" />
                    </template>
                    <template v-else-if="item.type === 'select'">
                      <a-select
                        style="width: 150px"
                        v-model="item.value.value"
                        :placeholder="item.placeholder"
                        :options="project.data"
                        :field-names="fieldNames"
                        allow-clear
                        allow-search
                      />
                    </template>
                    <template v-if="item.type === 'date'">
                      <a-date-picker v-model="item.value.value" />
                    </template>
                    <template v-if="item.type === 'time'">
                      <a-time-picker v-model="item.value.value" value-format="HH:mm:ss" />
                    </template>
                    <template v-if="item.type === 'check-group'">
                      <a-checkbox-group v-model="item.value.value">
                        <a-checkbox v-for="it of item.optionItems" :value="it.value" :key="it.value">
                          {{ item.label }}
                        </a-checkbox>
                      </a-checkbox-group>
                    </template>
                  </template>
                </a-form-item>
              </a-form>
            </template>
          </TableHeader>
        </template>

        <template #default>
          <a-tabs @tab-click="(key) => switchType(key)">
            <template #extra>
              <a-space v-if="caseType === '0'">
                <a-button type="primary" size="small" @click="onAddPage">新增</a-button>
                <a-button status="warning" size="small" @click="setCase('调试完成')">调试完成</a-button>
                <a-button status="danger" size="small" @click="onDeleteItems">批量删除</a-button>
              </a-space>
              <a-space v-else-if="caseType === '1'">
                <a-button status="warning" size="small" @click="setCase('调试用例')">设为调试用例</a-button>
                <a-button status="warning" size="small" @click="setCaseGroup('用例组')">设为用例组</a-button>
              </a-space>
              <a-space v-else />
            </template>
            <a-tab-pane key="0" title="调试用例" />
            <a-tab-pane key="1" title="调试完成" />
            <!--            <a-tab-pane key="5" title="已设置定时" />-->
          </a-tabs>
          <a-table
            :bordered="false"
            :row-selection="{ selectedRowKeys, showCheckedAll }"
            :loading="table.tableLoading"
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
                <template v-else-if="item.key === 'team'" #cell="{ record }">
                  {{ record.team.name }}
                </template>
                <template v-else-if="item.key === 'state'" #cell="{ record }">
                  <a-tag color="green" size="small" v-if="record.state === 1">通过</a-tag>
                  <a-tag color="red" size="small" v-else-if="record.state === 2">失败</a-tag>
                  <a-tag color="gray" size="small" v-else>未测试</a-tag>
                </template>
                <template v-else-if="item.key === 'case_type'" #cell="{ record }">
                  <a-tag color="green" size="small" v-if="record.case_type === 0">WEB</a-tag>
                  <a-tag color="arcoblue" size="small" v-else-if="record.case_type === 1">安卓</a-tag>
                  <a-tag color="pinkpurple" size="small" v-else-if="record.case_type === 2">IOS</a-tag>
                  <a-tag color="red" size="small" v-else-if="record.case_type === 3">桌面PC</a-tag>
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <a-space v-if="caseType === '0'">
                    <a-button type="text" size="mini" @click="onRunCase(record)">执行</a-button>
                    <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
                    <a-button type="text" size="mini" @click="onClick(record)">添加步骤</a-button>
                    <a-button status="danger" type="text" size="mini" @click="onDelete(record)">删除</a-button>
                  </a-space>
                  <a-space v-else-if="caseType === '1'">
                    <a-button type="text" size="mini" @click="onRunCase(record)">执行</a-button>
                    <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
                    <!--                    <a-button type="text" size="mini" @click="setCase('用例组')">设为用例组</a-button>-->
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
      <ModalDialog ref="modalDialogRef" :title="actionTitle" @confirm="onDataForm">
        <template #content>
          <a-form :model="formModel">
            <a-form-item
              :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
              :label="item.label"
              v-for="item of formItems"
              :key="item.key"
            >
              <template v-if="item.type === 'input'">
                <a-input :placeholder="item.placeholder" v-model="item.value.value" />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'team'">
                <a-select
                  v-model="item.value.value"
                  :placeholder="item.placeholder"
                  :options="project.data"
                  :field-names="fieldNames"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'case_type'">
                <a-select
                  v-model="item.value.value"
                  :placeholder="item.placeholder"
                  :options="testObjData.platformEnum"
                  :field-names="fieldNames"
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
// import {Search} from '@/components/ListSearch.vue'
import { get, post, put, deleted } from '@/api/http'
import { getPlatformEnum, uiCase, uiCasePutType, UiRun } from '@/api/url'
import { usePagination, useRowKey, useRowSelection, useTable, useTableColumn } from '@/hooks/table'
import { FormItem, ModalDialogType } from '@/types/components'
import { Input, Message, Modal, Notification } from '@arco-design/web-vue'
import { h, onMounted, ref, nextTick, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useProject } from '@/store/modules/get-project'
import { getKeyByTitle, transformData } from '@/utils/datacleaning'
import { fieldNames } from '@/setting'
import { useTestObj } from '@/store/modules/get-test-obj'

const project = useProject()
const conditionItems: Array<FormItem> = [
  {
    key: 'name',
    label: '用例名称',
    type: 'input',
    placeholder: '请输入用例名称',
    value: ref(''),
    reset: function () {
      this.value.value = ''
    },
    render: (formItem: FormItem) => {
      return h(Input, {
        placeholder: '请输入用例名称',
        modelValue: formItem.value.value,
        'onUpdate:modelValue': (value) => {
          formItem.value.value = value
        }
      })
    }
  },
  {
    key: 'caseid',
    label: '用例ID',
    type: 'input',
    placeholder: '请输入用例ID',
    value: ref(''),
    reset: function () {
      this.value.value = ''
    },
    render: (formItem: FormItem) => {
      return h(Input, {
        placeholder: '请输入用例ID',
        modelValue: formItem.value.value,
        'onUpdate:modelValue': (value) => {
          formItem.value.value = value
        }
      })
    }
  },
  {
    key: 'team',
    label: '筛选项目组',
    value: ref(),
    type: 'select',
    placeholder: '请选择项目',
    optionItems: [],
    reset: function () {
      this.value.value = undefined
    }
  }
]
conditionItems[2].optionItems = project.data

const formItems = [
  {
    label: '项目组名称',
    key: 'team',
    value: ref(''),
    placeholder: '请选择项目名称',
    required: true,
    type: 'select',
    validator: function () {
      if (!this.value.value && this.value.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '用例客户端',
    key: 'case_type',
    value: ref(''),
    placeholder: '请选择用例类型',
    required: true,
    type: 'select',
    validator: function () {
      if (!this.value.value && this.value.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '用例名称',
    key: 'name',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入页面名称',
    validator: function () {
      if (!this.value.value && this.value.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  }
] as FormItem[]

const actionTitle = ref('添加页面')
const modalDialogRef = ref<ModalDialogType | null>(null)
const pagination = usePagination(doRefresh)
const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
const table = useTable()
const rowKey = useRowKey('id')
const testObj = useTestObj()

const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '项目组',
    key: 'team',
    dataIndex: 'team',
    width: 100
  },
  {
    title: '用例名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 230
  },
  {
    title: '客户端',
    key: 'case_type',
    dataIndex: 'case_type',
    align: 'left'
  },
  {
    title: '用例执行顺序',
    key: 'run_flow',
    dataIndex: 'run_flow',
    align: 'left'
  },
  {
    title: '状态',
    key: 'state',
    dataIndex: 'state'
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 200
  }
])
const caseType: any = ref('0')

function switchType(key: any) {
  caseType.value = key
  doRefresh()
}

const formModel = ref({})

function doRefresh() {
  get({
    url: uiCase,
    data: () => {
      return {
        page: pagination.page,
        pageSize: pagination.pageSize,
        type: caseType.value
      }
    }
  })
    .then((res) => {
      table.handleSuccess(res)
      pagination.setTotalSize((res as any).totalSize)
    })
    .catch(console.log)
}

function onSearch() {
  let data: { [key: string]: string } = {}
  conditionItems.forEach((it) => {
    if (it.value.value) {
      data[it.key] = it.value.value
    }
  })
  console.log(data)
  if (JSON.stringify(data) === '{}') {
    doRefresh()
  } else if (data.project) {
    get({
      url: uiCase,
      data: () => {
        return {
          page: pagination.page,
          pageSize: pagination.pageSize,
          project: data.project,
          type: caseType.value
        }
      }
    })
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize(res.totalSize || 10)
        Message.success(res.msg)
      })
      .catch(console.log)
  } else if (data) {
    get({
      url: uiCase,
      data: () => {
        return {
          id: data.caseid,
          name: data.name,
          type: caseType.value
        }
      }
    })
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize(res.totalSize || 10)
        Message.success(res.msg)
      })
      .catch(console.log)
  }
}

function onResetSearch() {
  conditionItems.forEach((it) => {
    it.reset ? it.reset() : (it.value.value = '')
  })
}

const addUpdate = ref(0)
const updateId: any = ref('')

function onAddPage() {
  actionTitle.value = '添加页面'
  modalDialogRef.value?.toggle()
  addUpdate.value = 1
  formItems.forEach((it) => {
    if (it.reset) {
      it.reset()
    } else {
      it.value.value = ''
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
        url: uiCase,
        data: () => {
          return {
            id: '[' + data.id + ']'
          }
        }
      })
        .then((res) => {
          Message.success(res.msg)
          doRefresh()
        })
        .catch(console.log)
    }
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
      deleted({
        url: uiCase,
        data: () => {
          return {
            id: JSON.stringify(selectedRowKeys.value)
          }
        }
      })
        .then((res) => {
          Message.success(res.msg)
          selectedRowKeys.value = []
          doRefresh()
        })
        .catch(console.log)
    }
  })
}

function onUpdate(item: any) {
  actionTitle.value = '编辑页面'
  modalDialogRef.value?.toggle()
  addUpdate.value = 0
  updateId.value = item.id
  nextTick(() => {
    formItems.forEach((it) => {
      const key = it.key
      const propName = item[key]
      if (typeof propName === 'object' && propName !== null) {
        it.value.value = propName.name
      } else {
        it.value.value = propName
      }
    })
  })
}

function setCase(name: string) {
  if (selectedRowKeys.value.length === 0) {
    Message.error('请选择要设为' + name + '的数据')
    return
  }
  let type = 0
  if (name === '调试完成') {
    type = 1
  } else if (name === '用例组') {
    type = 5
    //   用例组需要单独设置一个字段来表示
  }
  Modal.confirm({
    title: '提示',
    content: '确定要把这些设为' + name + '的吗？',
    cancelText: '取消',
    okText: '确定',
    onOk: () => {
      put({
        url: uiCasePutType,
        data: () => {
          return {
            id: JSON.stringify(selectedRowKeys.value),
            type: type,
            name: name
          }
        }
      })
        .then((res) => {
          Message.success(res.msg)
          selectedRowKeys.value = []
          doRefresh()
        })
        .catch(console.log)
    }
  })
}

function onDataForm() {
  if (formItems.every((it) => (it.validator ? it.validator() : true))) {
    modalDialogRef.value?.toggle()
    let value = transformData(formItems)
    if (addUpdate.value === 1) {
      // let case_type = getKeyByTitle(testObjData.platformEnum, value.case_type)

      addUpdate.value = 0
      post({
        url: uiCase,
        data: () => {
          return {
            team: value.team,
            name: value.name,
            case_type: value.case_type,
            type: 0
          }
        }
      })
        .then((res) => {
          Message.success(res.msg)
          doRefresh()
        })
        .catch(console.log)
    } else if (addUpdate.value === 0) {
      let teamId = value.team
      if (typeof value.team === 'string') {
        teamId = getKeyByTitle(project.data, value.team)
      }
      addUpdate.value = 0
      value['id'] = updateId.value
      updateId.value = 0
      put({
        url: uiCase,
        data: () => {
          return {
            id: value.id,
            team: teamId,
            name: value.name,
            type: 0,
            state: 0
          }
        }
      })
        .then((res) => {
          Message.success(res.msg)
          doRefresh()
        })
        .catch(console.log)
    }
  }
}

function onRunCase(record: any) {
  if (testObj.te == null) {
    Message.error('请先选择用例执行的环境')
    return
  }
  // Message.info('测试用例正在执行，请稍后')
  get({
    url: UiRun,
    data: () => {
      return {
        case_id: record.id,
        te: testObj.te
      }
    }
  })
    .then((res) => {
      Notification.success(res.msg)
    })
    .catch(console.log)
}

const router = useRouter()

function onClick(record: any) {
  let caseId = parseInt(record.id, 10)
  router.push({
    path: '/uitest/details',
    query: {
      id: caseId,
      name: record.name,
      team_name: record.team.name,
      team_id: record.team.id,
      type: parseInt(record.type)
    }
  })
}

const testObjData = reactive({
  platformEnum: []
})

function getPlatform() {
  get({
    url: getPlatformEnum,
    data: () => {
      return {}
    }
  })
    .then((res) => {
      testObjData.platformEnum = res.data
    })
    .catch(console.log)
}

function setCaseGroup() {
  Message.info('进入到设置用例组页面')
}

onMounted(() => {
  nextTick(async () => {
    doRefresh()
    getPlatform()
  })
})
</script>

<style lang="less" scoped>
.avatar-container {
  position: relative;
  width: 30px;
  height: 30px;
  margin: 0 auto;
  vertical-align: middle;

  .avatar {
    width: 100%;
    height: 100%;
    border-radius: 50%;
  }

  .avatar-vip {
    border: 2px solid #cece1e;
  }

  .vip {
    position: absolute;
    top: 0;
    right: -9px;
    width: 15px;
    transform: rotate(60deg);
  }
}

.gender-container {
  .gender-icon {
    width: 20px;
  }
}
</style>
