<template>
  <div>
    <a-card title="用例详情">
      <template #extra>
        <a-affix :offsetTop="80">
          <a-space>
            <a-button type="primary" size="small" @click="doAppend">增加</a-button>
            <a-button type="primary" size="small" @click="doRefresh">刷新页面</a-button>
            <a-button status="success" size="small" @click="onCaseRun">执行</a-button>
            <a-button status="danger" size="small" @click="doResetSearch">返回</a-button>
          </a-space>
        </a-affix>
      </template>
      <div class="container">
        <a-space direction="vertical" style="width: 25%">
          <span>所属项目：{{ pageData.record.project?.name }}</span>
          <span>顶级模块：{{ pageData.record.module_name?.superior_module }}</span>
          <span>所属模块：{{ pageData.record.module_name?.name }}</span>
          <span>用例负责人：{{ pageData.record.case_people?.nickname }}</span>
        </a-space>
        <a-space direction="vertical" style="width: 25%">
          <span>用例ID：{{ pageData.record.id }}</span>
          <span>用例名称：{{ pageData.record.name }}</span>
          <span>测试结果：{{ pageData.record.status === 1 ? '通过' : '失败' }}</span>
        </a-space>
        <a-space direction="vertical" style="width: 50%">
          <span>用例执行顺序：{{ pageData.record.case_flow }}</span>
          <span v-if="uiCaseDetailsData.elementLocator">元素表达式：{{ uiCaseDetailsData.elementLocator }}</span>
        </a-space>
      </div>
    </a-card>
    <a-card>
      <div style="display: flex">
        <div style="width: 50%; margin-right: 10px">
          <a-table
            :columns="columns"
            :data="uiCaseDetailsData.data"
            @change="handleChange"
            :draggable="{ type: 'handle', width: 40 }"
            :pagination="false"
            @row-click="select"
          >
            <template #columns>
              <a-table-column
                v-for="item of columns"
                :key="item.key"
                :align="item.align"
                :title="item.title"
                :width="item.width"
                :data-index="item.dataIndex"
                :fixed="item.fixed"
                :ellipsis="item.ellipsis"
                :tooltip="item.tooltip"
              >
                <template v-if="item.dataIndex === 'page_step_name'" #cell="{ record }">
                  {{ record.page_step?.name }}
                </template>
                <template v-else-if="item.dataIndex === 'status'" #cell="{ record }">
                  <a-tag color="green" size="small" v-if="record.status === 1">通过</a-tag>
                  <a-tag color="red" size="small" v-else-if="record.status === 0">失败</a-tag>
                  <a-tag color="gray" size="small" v-else>未测试</a-tag>
                </template>
                <template v-else-if="item.dataIndex === 'actions'" #cell="{ record }">
                  <a-button type="text" size="mini" @click="onPageStep(record)">调试</a-button>
                  <a-button type="text" size="mini" @click="oeFreshSteps(record)">更新数据</a-button>
                  <a-button status="danger" type="text" size="mini" @click="onDelete(record)">删除</a-button>
                </template>
              </a-table-column>
            </template>
          </a-table>
        </div>
        <div style="width: 50%; margin-left: 10px">
          <a-list :bordered="false">
            <template #header> {{ uiCaseDetailsData.selectData?.page_step?.name }} </template>
            <a-list-item
              v-for="item of uiCaseDetailsData.selectData?.case_data"
              :key="item.page_step_details_id"
              style="padding: 4px 20px"
            >
              <div style="display: flex; flex-direction: column">
                <div style="display: flex; margin-bottom: 2px; margin-top: 2px">
                  <a-space style="width: 40%">
                    <span>元素名称：</span>
                    <span>{{ item.page_step_details_name }}</span>
                  </a-space>
                  <a-space style="width: 30%">
                    <span v-if="item.type === 0">操作：{{ getLabelByValue(uiCaseDetailsData.ope, item.ope_type) }}</span>
                    <span v-if="item.type === 1">断言：{{ getLabelByValue(uiCaseDetailsData.ass, item.ass_type) }}</span>
                  </a-space>
                  <a-space style="width: 30%">
                    <a-button type="text" size="mini" @click="viewElementExpressions(item.page_step_details_id)"
                      >查看元素表达式</a-button
                    >
                  </a-space>
                </div>
                <a-space direction="vertical" style="margin-bottom: 2px; margin-top: 2px">
                  <template v-for="key in Object.keys(item.page_step_details_data)" :key="key">
                    <div style="display: flex">
                      <span style="width: 13%">{{ key + '：' }}</span>
                      <a-textarea
                        v-model="item.page_step_details_data[key]"
                        @blur="onUpdate"
                        :auto-size="{ minRows: 1, maxRows: 5 }"
                        style="width: 90%"
                      />
                    </div>
                  </template>
                </a-space>
              </div>
            </a-list-item>
          </a-list>
        </div>
      </div>
    </a-card>
  </div>

  <ModalDialog ref="modalDialogRef" :title="uiCaseDetailsData.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
          :label="item.label"
          v-for="item of formItems"
          :key="item.key"
        >
          <template v-if="item.type === 'select' && item.key === 'project'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="project.data"
              :field-names="fieldNames"
              @change="doUiModuleNameAll(item.value)"
              value-key="key"
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'module'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="uiCaseDetailsData.moduleName"
              :field-names="fieldNames"
              @change="doUiPageNameAll(item.value)"
              value-key="key"
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'page'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="uiCaseDetailsData.pageName"
              :field-names="fieldNames"
              @change="doUiStepsPageStepsName(item.value)"
              value-key="key"
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'page_step'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="uiCaseDetailsData.pageStepsName"
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
</template>
<script lang="ts" setup>
import { nextTick, onMounted, reactive, ref } from 'vue'
import { Message, Modal } from '@arco-design/web-vue'
import {
  userProjectModuleGetAll,
  uiPageName,
  uiCasePutCaseSort,
  uiCaseStepsDetailed,
  uiCaseStepsRefreshCacheData,
  uiStepsPageStepsName,
  uiCaseRun,
  uiStepsRun,
  uiPageStepsDetailed,
  uiPageStepsDetailedOpe,
  uiPageStepsDetailedAss
} from '@/api/url'
import { deleted, get, post, put } from '@/api/http'
import { FormItem, ModalDialogType } from '@/types/components'
import { useRoute } from 'vue-router'
import { getFormItems } from '@/utils/datacleaning'
import { fieldNames } from '@/setting'
import { useProject } from '@/store/modules/get-project'
import ModalDialog from '@/components/ModalDialog.vue'
import { usePageData } from '@/store/page-data'
import { useTestObj } from '@/store/modules/get-test-obj'
const pageData = usePageData()
const testObj = useTestObj()
const project = useProject()
const route = useRoute()
const formModel = ref({})
const modalDialogRef = ref<ModalDialogType | null>(null)
const uiCaseDetailsData: any = reactive({
  moduleName: [],
  pageName: [],
  pageStepsName: [],
  data: [],
  isAdd: false,
  updateId: 0,
  selectData: {},
  actionTitle: '添加用例步骤',
  elementLocator: null,
  ope: [],
  ass: []
})

const columns = reactive([
  {
    title: '步骤名称',
    dataIndex: 'page_step_name'
  },
  {
    title: '测试结果',
    dataIndex: 'status'
  },
  {
    title: '错误提示',
    dataIndex: 'error_message',
    align: 'left',
    ellipsis: true,
    tooltip: true
  },

  {
    title: '操作',
    dataIndex: 'actions',
    align: 'center',
    width: 200
  }
])

const formItems: FormItem[] = reactive([
  {
    label: '选择项目',
    key: 'project',
    value: '',
    placeholder: '请选择项目',
    required: true,
    type: 'select',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '选择模块',
    key: 'module',
    value: '',
    placeholder: '请选择模块',
    required: true,
    type: 'select',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '选择页面',
    key: 'page',
    value: '',
    placeholder: '请选择测试页面',
    required: true,
    type: 'select',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '页面步骤',
    key: 'page_step',
    value: '',
    type: 'select',
    required: true,
    placeholder: '请输入用例名称',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  }
])

function doAppend() {
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
  Modal.confirm({
    title: '提示',
    content: '是否要删除此页面？',
    cancelText: '取消',
    okText: '删除',
    onOk: () => {
      deleted({
        url: uiCaseStepsDetailed,
        data: () => {
          return {
            id: record.id,
            case: record.case.id
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

const handleChange = (_data: any) => {
  uiCaseDetailsData.data = _data
  let data: any = []
  uiCaseDetailsData.data.forEach((item: any, index: number) => {
    data.push({
      id: item.id,
      case_sort: index
    })
  })
  put({
    url: uiCasePutCaseSort,
    data: () => {
      return {
        case_sort_list: data
      }
    }
  })
    .then((res) => {
      Message.success(res.msg)
    })
    .catch(console.log)
}

function onDataForm() {
  if (formItems.every((it: any) => (it.validator ? it.validator() : true))) {
    modalDialogRef.value?.toggle()
    let value = getFormItems(formItems)
    post({
      url: uiCaseStepsDetailed,
      data: () => {
        value['case'] = route.query.id
        value['case_data'] = []
        value['case_sort'] = uiCaseDetailsData.data.length
        return value
      }
    })
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
        get({
          url: uiCaseStepsRefreshCacheData,
          data: () => {
            return {
              id: res.data.id
            }
          }
        })
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      })
      .catch(console.log)
  }
}

function doResetSearch() {
  window.history.back()
}

function doRefresh() {
  get({
    url: uiCaseStepsDetailed,
    data: () => {
      return {
        case_id: route.query.id
      }
    }
  })
    .then((res) => {
      uiCaseDetailsData.data = res.data
      if (res.data) {
        uiCaseDetailsData.selectData = res.data[0]
      }
    })
    .catch(console.log)
}

function oeFreshSteps(record: any) {
  Modal.confirm({
    title: '提示',
    content: '是否确实要刷新这个用例的步骤数据？刷新会导致丢失原始数据，请先保存原始数据！',
    cancelText: '取消',
    okText: '刷新',
    onOk: () => {
      get({
        url: uiCaseStepsRefreshCacheData,
        data: () => {
          return {
            id: record.id
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

function doUiModuleNameAll(project_id: number) {
  get({
    url: userProjectModuleGetAll,
    data: () => {
      return {
        project_id: project_id
      }
    }
  })
    .then((res) => {
      uiCaseDetailsData.moduleName = res.data
    })
    .catch(console.log)
}

function doUiPageNameAll(project_id: number) {
  get({
    url: uiPageName,
    data: () => {
      return {
        module_name: project_id
      }
    }
  })
    .then((res) => {
      uiCaseDetailsData.pageName = res.data
    })
    .catch(console.log)
}

function doUiStepsPageStepsName(page_id: number) {
  get({
    url: uiStepsPageStepsName,
    data: () => {
      return {
        page_id: page_id
      }
    }
  })
    .then((res) => {
      uiCaseDetailsData.pageStepsName = res.data
    })
    .catch(console.log)
}
function onCaseRun() {
  if (testObj.selectValue == null) {
    Message.error('请先选择用例执行的环境')
    return
  }
  get({
    url: uiCaseRun,
    data: () => {
      return {
        case_id: route.query.id,
        testing_environment: testObj.selectValue
      }
    }
  })
    .then((res) => {
      Message.loading(res.msg)
    })
    .catch(console.log)
}
function select(record: any) {
  uiCaseDetailsData.selectData = record
}
function onUpdate() {
  put({
    url: uiCaseStepsDetailed,
    data: () => {
      return {
        id: uiCaseDetailsData.selectData.id,
        case_data: uiCaseDetailsData.selectData.case_data
      }
    }
  })
    .then((res) => {
      Message.success(res.msg)
      console.log(res.data)
    })
    .catch(console.log)
}
function onPageStep(record: any) {
  if (testObj.selectValue == null) {
    Message.error('请先选择用例执行的环境')
    return
  }
  get({
    url: uiStepsRun,
    data: () => {
      return {
        page_step_id: record.page_step.id,
        case_id: record.id,
        te: testObj.selectValue
      }
    }
  })
    .then((res) => {
      Message.loading(res.msg)
    })
    .catch(console.log)
}
function getLabelByValue(data: any, value: string): string {
  const list = [...data]
  for (const item of list) {
    if (item.children) {
      list.push(...item.children)
    }
  }
  return list.find((item: any) => item.value === value)?.label
}

function viewElementExpressions(id: number) {
  get({
    url: uiPageStepsDetailed,
    data: () => {
      return {
        id: id
      }
    }
  })
    .then((res) => {
      uiCaseDetailsData.elementLocator = res.data[0].ele_name_a.loc
    })
    .catch(console.log)
}
function getUiRunSortOpe() {
  get({
    url: uiPageStepsDetailedOpe,
    data: () => {
      return {
        page_type: route.query.pageType
      }
    }
  })
    .then((res) => {
      uiCaseDetailsData.ope = res.data
    })
    .catch(console.log)
}
function getUiRunSortAss() {
  get({
    url: uiPageStepsDetailedAss,
    data: () => {
      return {
        page_type: route.query.pageType
      }
    }
  })
    .then((res) => {
      uiCaseDetailsData.ass = res.data
    })
    .catch(console.log)
}

onMounted(() => {
  nextTick(async () => {
    doRefresh()
    getUiRunSortOpe()
    getUiRunSortAss()
  })
})
</script>

<style>
.container {
  display: flex; /* 开启flex布局 */
}

.left {
  width: 30%; /* 左边区域占据50%的宽度 */
  margin-right: 10px; /* 设置左边盒子的右边距 */
}

.right {
  width: 70%; /* 右边区域占据50%的宽度 */
  margin-left: 10px; /* 设置右边盒子的左边距 */
}
</style>
