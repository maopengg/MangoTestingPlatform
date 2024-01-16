<template>
  <div>
    <a-card title="页面元素详情">
      <template #extra>
        <a-affix :offsetTop="80">
          <a-space>
            <a-button type="primary" size="small" @click="doAppend">增加</a-button>
            <a-button status="danger" size="small" @click="doResetSearch">返回</a-button>
          </a-space>
        </a-affix>
      </template>
      <div class="container">
        <a-space direction="vertical" style="width: 25%">
          <p>页面ID：{{ pageData.record.id }}</p>
          <span>所属项目：{{ pageData.record.project?.name }}</span>
          <span>顶级模块：{{ pageData.record.module_name?.superior_module }}</span>
          <span>所属模块：{{ pageData.record.module_name?.name }}</span>
        </a-space>
        <a-space direction="vertical" style="width: 25%">
          <span>页面名称：{{ pageData.record.name }}</span>
          <span>页面地址：{{ pageData.record.url }}</span>
          <span>元素个数：{{ pageEleData.totalSize }}</span>
          <span>页面类型：{{ pageData.record.type }}</span>
        </a-space>
      </div>
    </a-card>
    <a-card>
      <a-table :columns="columns" :data="pageEleData.data" :pagination="false" :bordered="false">
        <template #columns>
          <a-table-column
            :key="item.key"
            v-for="item of columns"
            :align="item.align"
            :title="item.title"
            :width="item.width"
            :data-index="item.dataIndex"
            :fixed="item.fixed"
          >
            <template v-if="item.dataIndex === 'exp'" #cell="{ record }">
              <a-tag color="orangered" size="small" v-if="record.exp === 0">XPATH</a-tag>
              <a-tag color="gold" size="small" v-else-if="record.exp === 1">TestID</a-tag>
              <a-tag color="lime" size="small" v-else-if="record.exp === 3">文本</a-tag>
              <a-tag color="green" size="small" v-else-if="record.exp === 4">占位符</a-tag>
              <a-tag color="cyan" size="small" v-else-if="record.exp === 5">标签</a-tag>
              <a-tag color="cyan" size="small" v-else-if="record.exp === 6">标题</a-tag>
              <a-tag color="cyan" size="small" v-else-if="record.exp === 7">ROLE</a-tag>
              <a-tag color="cyan" size="small" v-else-if="record.exp === 8">AIT_TEXT</a-tag>
              <a-tag color="blue" size="small" v-else-if="record.exp === 11">A_DESCRIPTION</a-tag>
              <a-tag color="arcoblue" size="small" v-else-if="record.exp === 12">A_BOUNDS</a-tag>
              <a-tag color="purple" size="small" v-else-if="record.exp === 13">A_百分比坐标点击</a-tag>
            </template>
            <template v-else-if="item.dataIndex === 'is_iframe'" #cell="{ record }">
              <a-switch
                :default-checked="record.is_iframe === 1"
                :beforeChange="(newValue) => onModifyStatus(newValue, record.id)"
              />
            </template>
            <template v-else-if="item.dataIndex === 'actions'" #cell="{ record }">
              <a-button type="text" size="mini" @click="onDebug(record)">调试</a-button>
              <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
              <a-button status="danger" type="text" size="mini" @click="onDelete(record)">删除</a-button>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-card>
  </div>
  <ModalDialog ref="modalDialogRef" :title="pageEleData.actionTitle" @confirm="onDataForm">
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
          <template v-else-if="item.type === 'select'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="pageEleData.eleExp"
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
  <ModalDialog ref="modalDialogRef1" :title="pageEleData.actionTitle" @confirm="onDataForm1">
    <template #content>
      <a-form :model="formModel1">
        <a-form-item
          :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
          :label="item.label"
          v-for="item of formItems1"
          :key="item.key"
        >
          <template v-if="item.type === 'input'">
            <a-input :placeholder="item.placeholder" v-model="item.value" />
          </template>
          <template v-else-if="item.type === 'cascader' && item.key === 'ope_type'">
            <a-space direction="vertical">
              <a-cascader
                v-model="item.value"
                :options="pageEleData.ope"
                :default-value="item.value"
                expand-trigger="hover"
                :placeholder="item.placeholder"
                @change="upDataOpeValue(item.value)"
                value-key="key"
                style="width: 380px"
                allow-search
                allow-clear
                :disabled="pageEleData.isDisabledOpe"
              />
            </a-space>
          </template>
          <template v-else-if="item.type === 'cascader' && item.key === 'ass_type'">
            <a-space direction="vertical">
              <a-cascader
                v-model="item.value"
                :options="pageEleData.ass"
                :default-value="item.value"
                expand-trigger="hover"
                :placeholder="item.placeholder"
                @change="upDataAssValue(item.value)"
                value-key="key"
                style="width: 380px"
                allow-search
                allow-clear
                :disabled="pageEleData.isDisabledAss"
              />
            </a-space>
          </template>
          <template v-else-if="item.type === 'textarea' && item.key === 'ope_value'">
            <a-textarea
              :auto-size="{ minRows: 4, maxRows: 7 }"
              :placeholder="item.placeholder"
              :default-value="item.value"
              v-model="item.value"
              allow-clear
              :disabled="pageEleData.isDisabledOpe"
            />
          </template>
          <template v-else-if="item.type === 'textarea' && item.key === 'ass_value'">
            <a-textarea
              :auto-size="{ minRows: 4, maxRows: 7 }"
              :placeholder="item.placeholder"
              :default-value="item.value"
              v-model="item.value"
              allow-clear
              :disabled="pageEleData.isDisabledAss"
            />
          </template>
          <template v-else-if="item.type === 'radio' && item.key === 'type'">
            <a-radio-group @change="changeStatus" v-model="item.value" :options="pageEleData.plainOptions" />
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
  uiUiElement,
  systemEnumExp,
  uiUiElementPutIsIframe,
  uiPageStepsDetailedOpe,
  uiPageStepsDetailedAss,
  uiUiElementTest
} from '@/api/url'
import { deleted, get, post, put } from '@/api/http'
import { FormItem, ModalDialogType } from '@/types/components'
import { useRoute } from 'vue-router'
import { getFormItems } from '@/utils/datacleaning'
import { fieldNames } from '@/setting'
import { useTestObj } from '@/store/modules/get-test-obj'
import { usePageData } from '@/store/page-data'

const testObj = useTestObj()
const pageData: any = usePageData()

const route = useRoute()
const formModel = ref({})
const formModel1 = ref({})
const modalDialogRef = ref<ModalDialogType | null>(null)
const modalDialogRef1 = ref<ModalDialogType | null>(null)
const pageEleData = reactive({
  id: 0,
  isAdd: false,
  updateId: 0,
  actionTitle: '添加元素',
  eleExp: [],
  totalSize: 0,
  data: [],
  ope: [],
  ass: [],
  isDisabledOpe: false,
  isDisabledAss: true,
  plainOptions: [
    { label: '操作', value: 0 },
    { label: '断言', value: 1 }
  ]
})
const columns = reactive([
  {
    title: '元素名称',
    dataIndex: 'name',
    width: 200
  },
  {
    title: '表达式类型',
    dataIndex: 'exp'
  },
  {
    title: '定位表达式',
    dataIndex: 'loc'
  },
  {
    title: '定位器',
    dataIndex: 'locator'
  },
  {
    title: '是否在iframe中',
    dataIndex: 'is_iframe'
  },
  {
    title: '等待时间',
    dataIndex: 'sleep'
  },
  {
    title: '元素下标',
    dataIndex: 'sub'
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
    label: '元素名称',
    key: 'name',
    value: '',
    placeholder: '请输入元素名称',
    required: true,
    type: 'input',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '表达式类型',
    key: 'exp',
    value: null,
    type: 'select',
    required: true,
    placeholder: '请选择元素表达式类型',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '元素表达式',
    key: 'loc',
    value: '',
    type: 'input',
    required: true,
    placeholder: '请输入元素表达式',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '定位器',
    key: 'locator',
    value: '',
    type: 'input',
    required: false,
    placeholder: '请输入定位器'
  },
  {
    label: '等待时间',
    key: 'sleep',
    value: '',
    type: 'input',
    required: false,
    placeholder: '请输入元素等待时间'
  },
  {
    label: '元素下标',
    key: 'sub',
    value: '',
    type: 'input',
    required: false,
    placeholder: '请输入元素下标'
  }
])
const formItems1: FormItem[] = reactive([
  {
    label: '步骤类型',
    key: 'type',
    value: 0,
    type: 'radio',
    required: true,
    placeholder: '请选择对元素的操作类型',
    validator: function () {
      return true
    }
  },

  {
    label: '元素操作',
    key: 'ope_type',
    value: null,
    type: 'cascader',
    required: false,
    placeholder: '请选择对元素的操作',
    validator: function () {
      return true
    }
  },
  {
    label: '元素操作值',
    key: 'ope_value',
    value: '',
    type: 'textarea',
    required: false,
    placeholder: '请输入对元素的操作内容',
    validator: function () {
      if (this.value !== '') {
        try {
          this.value = JSON.parse(this.value)
        } catch (e) {
          Message.error('元素操作值请输入json数据类型')
          return false
        }
      }
      return true
    }
  },
  {
    label: '断言类型',
    key: 'ass_type',
    value: null,
    type: 'cascader',
    required: false,
    placeholder: '请选择断言类型'
  },
  {
    label: '断言值',
    key: 'ass_value',
    value: '',
    type: 'textarea',
    required: false,
    placeholder: '请输入断言内容',
    validator: function () {
      if (this.value !== '') {
        try {
          this.value = JSON.parse(this.value)
        } catch (e) {
          Message.error('断言值请输入json数据类型')
          return false
        }
      }
      return true
    }
  }
])

function doAppend() {
  pageEleData.actionTitle = '添加元素'
  pageEleData.isAdd = true
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
        url: uiUiElement,
        data: () => {
          return {
            id: '[' + record.id + ']'
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

function onUpdate(record: any) {
  pageEleData.actionTitle = '编辑添加元素'
  pageEleData.isAdd = false
  pageEleData.updateId = record.id
  modalDialogRef.value?.toggle()
  nextTick(() => {
    formItems.forEach((it) => {
      const propName = record[it.key]
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
    value['page'] = route.query.id
    if (pageEleData.isAdd) {
      post({
        url: uiUiElement,
        data: () => {
          value['is_iframe'] = 0
          return value
        }
      })
        .then((res) => {
          Message.success(res.msg)
          doRefresh()
        })
        .catch(console.log)
    } else {
      put({
        url: uiUiElement,
        data: () => {
          value['id'] = pageEleData.updateId
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
}

function doResetSearch() {
  // console.log('点击了', route)
  // const { getVisitedRoutes, removeVisitedRoute } = useVisitedRouteStore()
  // getVisitedRoutes.forEach((item: any) => {
  //   console.log(route.path)
  //   console.log(item['fullPath'])
  //   if (route.path === item['fullPath']) {
  //     console.log(item)
  //     removeVisitedRoute(item)
  //   }
  // })
  window.history.back()
}

function doRefresh() {
  get({
    url: uiUiElement,
    data: () => {
      return {
        page_id: route.query.id
      }
    }
  })
    .then((res) => {
      pageEleData.data = res.data
      pageEleData.totalSize = res.totalSize
    })
    .catch(console.log)
}

function getEleExp() {
  get({
    url: systemEnumExp,
    data: () => {
      return {}
    }
  })
    .then((res) => {
      pageEleData.eleExp = res.data
    })
    .catch(console.log)
}

const onModifyStatus = async (newValue: boolean, id: number) => {
  return new Promise<any>((resolve, reject) => {
    setTimeout(async () => {
      try {
        let value: any = false
        await put({
          url: uiUiElementPutIsIframe,
          data: () => {
            return {
              id: id,
              is_iframe: newValue ? 1 : 0
            }
          }
        })
          .then((res) => {
            Message.success(res.msg)
            value = res.code === 200
          })
          .catch(reject)
        resolve(value)
      } catch (error) {
        reject(error)
      }
    }, 300)
  })
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
      pageEleData.ope = res.data
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
      pageEleData.ass = res.data
    })
    .catch(console.log)
}

function changeStatus(event: number) {
  pageEleData.isDisabledOpe = event == 1
  pageEleData.isDisabledAss = event == 0
  formItems1.forEach((item) => {
    item.value = null
  })
  formItems1[0].value = event
}

function onDataForm1() {
  if (formItems1.every((it) => (it.validator ? it.validator() : true))) {
    modalDialogRef1.value?.toggle()
    let value = getFormItems(formItems1)
    value['testing_environment'] = testObj.selectValue
    value['id'] = pageEleData.id
    value['page_id'] = pageData.record.id
    value['project_id'] = pageData.record.project.id
    post({
      url: uiUiElementTest,
      data: () => {
        return value
      }
    })
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }
}

interface Item {
  value: string
  label: string
  parameter?: {
    [key: string]: any
  }
  children?: Item[]
}

function upDataAssValue(value: any) {
  const inputItem = findItemByValue(pageEleData.ass, value)
  if (inputItem) {
    const parameter: any = inputItem.parameter
    Object.keys(parameter).forEach((key) => {
      parameter[key] = ''
    })
    formItems1.forEach((item: any) => {
      if (item.key === 'ass_value') {
        item.value = JSON.stringify(parameter)
      }
    })
  }
}

function findItemByValue(data: Item[], value: string): Item | undefined {
  for (let i = 0; i < data.length; i++) {
    const item = data[i]
    if (item.value === value) {
      return item
    }
    if (item.children) {
      const childItem = findItemByValue(item.children, value)
      if (childItem) {
        return childItem
      }
    }
  }
  return undefined
}

function upDataOpeValue(value: string) {
  const inputItem = findItemByValue(pageEleData.ope, value)
  if (inputItem) {
    const parameter: any = inputItem.parameter
    Object.keys(parameter).forEach((key) => {
      parameter[key] = ''
    })
    formItems1.forEach((item: any) => {
      if (item.key === 'ope_value') {
        item.value = JSON.stringify(parameter)
      }
    })
  }
}

function onDebug(record: any) {
  if (!testObj.selectValue) {
    Message.error('请先选择测试环境')
    return
  }
  pageEleData.actionTitle = `对元素：${record.name} 进行操作或断言`
  pageEleData.id = record.id
  modalDialogRef1.value?.toggle()
  nextTick(() => {
    formItems1.forEach((it) => {
      const propName = record[it.key]
      if (typeof propName === 'object' && propName !== null) {
        it.value = propName.id
      } else {
        it.value = propName
      }
    })
  })
}

onMounted(() => {
  nextTick(async () => {
    doRefresh()
    getEleExp()
    getUiRunSortOpe()
    getUiRunSortAss()
  })
})
</script>
