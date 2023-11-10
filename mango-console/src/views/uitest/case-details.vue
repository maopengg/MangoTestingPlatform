<template>
  <div>
    <div id="tableHeaderContainer" class="relative" :style="{ zIndex: 9 }">
      <a-card :title="'用例步骤 用例：' + uiCaseDetailsData.caseName + ' | ' + '所属项目：' + route.query.project_name">
        <template #extra>
          <a-affix :offsetTop="80">
            <a-space>
              <a-button type="primary" status="warning" size="small" @click="doSave">保存</a-button>
              <a-button type="primary" size="small" @click="doAppend">增加步骤</a-button>
              <a-button status="danger" size="small" @click="doResetSearch">返回</a-button>
            </a-space>
          </a-affix>
        </template>
        <a-table
          :columns="columns"
          :data="uiCaseDetailsData.data"
          @change="handleChange"
          :draggable="{ type: 'handle', width: 40 }"
          :pagination="false"
          :bordered="false"
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
            >
              <template v-if="item.dataIndex === 'page_step_name'" #cell="{ record }">
                {{ record.page_step.name }}
              </template>
              <template v-else-if="item.dataIndex === 'case_cache_data'" #cell="{ record }">
                {{ record.case_cache_data }}
              </template>
              <template v-else-if="item.dataIndex === 'case_cache_ass'" #cell="{ record }">
                {{ record.case_cache_ass }}
              </template>
              <template v-else-if="item.dataIndex === 'actions'" #cell="{ record }">
                <a-button type="text" size="mini" @click="onUpdate(record)">编辑变量</a-button>
                <a-button type="text" size="mini" @click="oeFreshSteps(record)">刷新</a-button>
                <a-button status="danger" type="text" size="mini" @click="onDelete(record)">删除</a-button>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-card>
      <ModalDialog ref="modalDialogRef" :title="uiCaseDetailsData.actionTitle" @confirm="onDataForm">
        <template #content>
          <a-form :model="formModel">
            <a-form-item
              :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
              :label="item.label"
              v-for="item of formItems"
              :key="item.key"
            >
              <template v-if="item.type === 'textarea'">
                <a-textarea :placeholder="item.placeholder" :auto-size="true" v-model="item.value" />
              </template>
            </a-form-item>
          </a-form>
        </template>
      </ModalDialog>
      <ModalDialog ref="modalDialogRef1" :title="uiCaseDetailsData.actionTitle1" @confirm="onDataForm1">
        <template #content>
          <a-form :model="formModel">
            <a-form-item
              :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
              :label="item.label"
              v-for="item of formItems1"
              :key="item.key"
            >
              <template v-if="item.type === 'select' && item.key === 'project'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="project.data"
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
    </div>
  </div>
</template>
<script lang="ts" setup>
import { nextTick, onMounted, reactive, ref } from 'vue'
import { Message, Modal } from '@arco-design/web-vue'
import { uiCaseStepsDetailed, uiCaseStepsRefreshCacheData, uiPageNameProject, uiStepsPageStepsName } from '@/api/url'
import { deleted, get, post, put } from '@/api/http'
import { FormItem, ModalDialogType } from '@/types/components'
import { useRoute } from 'vue-router'
import { getFormItems } from '@/utils/datacleaning'
import { fieldNames } from '@/setting'
import { useProject } from '@/store/modules/get-project'
import ModalDialog from '@/components/ModalDialog.vue'

const project = useProject()
const route = useRoute()
const formModel = ref({})
const modalDialogRef = ref<ModalDialogType | null>(null)
const modalDialogRef1 = ref<ModalDialogType | null>(null)
const uiCaseDetailsData = reactive({
  caseName: route.query.name,
  pageName: [],
  pageStepsName: [],
  data: [],
  isAdd: false,
  updateId: 0,
  actionTitle: '添加元素',
  actionTitle1: '添加用例步骤'
})

const columns = reactive([
  {
    title: '步骤名称',
    dataIndex: 'page_step_name',
    width: 140
  },
  {
    title: '步骤执行顺序',
    dataIndex: 'case_sort',
    width: 80
  },
  {
    title: '用例数据',
    dataIndex: 'case_cache_data'
  },
  {
    title: '用例断言',
    dataIndex: 'case_cache_ass'
  },
  {
    title: '操作',
    dataIndex: 'actions',
    align: 'center',
    width: 200
  }
])

let formItems: FormItem[] = reactive([
  {
    label: '用例数据',
    key: 'case_cache_data',
    value: '',
    placeholder: '请输入字段需要的value值',
    required: true,
    type: 'textarea',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '用例断言',
    key: 'case_cache_ass',
    value: '',
    placeholder: '请输入字段需要的value值',
    required: true,
    type: 'textarea',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  }
])
const formItems1: FormItem[] = reactive([
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
    label: '选择页面',
    key: 'page',
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
  uiCaseDetailsData.actionTitle1 = '添加用例步骤'
  modalDialogRef1.value?.toggle()
  formItems1.forEach((it) => {
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

function onUpdate(item: any) {
  uiCaseDetailsData.actionTitle = '编辑步骤数据'
  modalDialogRef.value?.toggle()
  uiCaseDetailsData.isAdd = false
  uiCaseDetailsData.updateId = item.id
  nextTick(() => {
    formItems.forEach((it: any) => {
      const propName = item[it.key]
      if (typeof propName === 'object' && propName !== null) {
        it.value = JSON.stringify(propName, null, '\t')
      } else {
        it.value = propName
      }
    })
  })
}

const handleChange = (_data: any) => {
  Message.info('测试拖动成功')
}

function onDataForm() {
  if (formItems.every((it) => (it.validator ? it.validator() : true))) {
    modalDialogRef.value?.toggle()
    let value = getFormItems(formItems)

    put({
      url: uiCaseStepsDetailed,
      data: () => {
        value['id'] = uiCaseDetailsData.updateId
        return value
      }
    })
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }
}
function onDataForm1() {
  if (formItems1.every((it: any) => (it.validator ? it.validator() : true))) {
    modalDialogRef1.value?.toggle()
    let value = getFormItems(formItems1)
    post({
      url: uiCaseStepsDetailed,
      data: () => {
        value['case'] = route.query.id
        value['case_cache_data'] = '[]'
        value['case_cache_ass'] = '[]'
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
function doSave() {
  Message.success('调用了保存')
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

function doUiPageNameAll(project_id: number) {
  get({
    url: uiPageNameProject,
    data: () => {
      return {
        project_id: project_id
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

onMounted(() => {
  nextTick(async () => {
    doRefresh()
  })
})
</script>
