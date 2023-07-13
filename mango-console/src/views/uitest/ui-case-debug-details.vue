<template>
  <div>
    <div id="tableHeaderContainer" class="relative" :style="{ zIndex: 9 }">
      <a-card :title="'用例：' + uiRunSortData.caseName + ' | ' + '所属项目：' + route.query.project_name">
        <template #extra>
          <a-affix :offsetTop="80">
            <a-space>
              <a-button type="primary" status="warning" size="small" @click="doSave">保存</a-button>
              <a-button type="primary" size="small" @click="doAppend">增加</a-button>
              <a-button status="danger" size="small" @click="doResetSearch">返回</a-button>
            </a-space>
          </a-affix>
        </template>
        <a-table
          :columns="columns"
          :data="uiRunSortData.data"
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
              <template v-if="item.dataIndex === 'el_page'" #cell="{ record }">
                {{ record.el_page.name }}
              </template>
              <template v-else-if="item.dataIndex === 'el_name'" #cell="{ record }">
                {{ record.el_name == null ? '-' : record.el_name.name }}
              </template>
              <template v-else-if="item.dataIndex === 'el_name_b'" #cell="{ record }">
                {{ record.el_name_b == null ? '-' : record.el_name_b.name }}
              </template>
              <template v-else-if="item.dataIndex === 'actions'" #cell="{ record }">
                <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
                <a-button status="danger" type="text" size="mini" @click="onDelete(record)">删除</a-button>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-card>
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
              <template v-if="item.type === 'select' && item.key === 'el_page'">
                <a-select
                  v-model="item.value.value"
                  :placeholder="item.placeholder"
                  :options="uiRunSortData.pageName"
                  :field-names="fieldNames"
                  @change="getEleName(item.value.value)"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'el_name'">
                <a-select
                  v-model="item.value.value"
                  :placeholder="item.placeholder"
                  :options="uiRunSortData.eleName"
                  :field-names="fieldNames"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'el_name_b'">
                <a-select
                  v-model="item.value.value"
                  :placeholder="item.placeholder"
                  :options="uiRunSortData.eleName"
                  :field-names="fieldNames"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'cascader' && item.key === 'ope_type'">
                <a-space direction="vertical">
                  <a-cascader
                    :options="uiRunSortData.ope"
                    :default-value="item.value"
                    expand-trigger="hover"
                    :placeholder="item.placeholder"
                    @change="upDataOpeValue(item.value.value)"
                    style="width: 380px"
                    allow-search
                    allow-clear
                  />
                </a-space>
              </template>
              <template v-else-if="item.type === 'cascader' && item.key === 'ass_type'">
                <a-space direction="vertical">
                  <a-cascader
                    :options="uiRunSortData.ass"
                    :default-value="item.value"
                    expand-trigger="hover"
                    :placeholder="item.placeholder"
                    @change="upDataAssValue(item.value.value)"
                    style="width: 380px"
                    allow-search
                    allow-clear
                  />
                </a-space>
              </template>
              <template v-else-if="item.type === 'textarea' && item.key === 'ope_value'">
                <a-textarea
                  :auto-size="{ minRows: 4, maxRows: 7 }"
                  :placeholder="item.placeholder"
                  :default-value="item.value.value"
                  v-model="item.value.value"
                  allow-clear
                />
              </template>
              <template v-else-if="item.type === 'textarea' && item.key === 'ass_value'">
                <a-textarea
                  :auto-size="{ minRows: 4, maxRows: 7 }"
                  :placeholder="item.placeholder"
                  :default-value="item.value.value"
                  v-model="item.value.value"
                  allow-clear
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

import { uiRunSort, uiRunSortAss, uiRunSortOpe, uiPageName, uiUiElementName } from '@/api/url'
import { deleted, get, post, put } from '@/api/http'
import { FormItem, ModalDialogType } from '@/types/components'
import { useRoute } from 'vue-router'
import { getKeyByTitle, transformData } from '@/utils/datacleaning'
import { fieldNames } from '@/setting'

const route = useRoute()

const columns = reactive([
  {
    title: '页面名称',
    dataIndex: 'el_page'
  },

  {
    title: '操作类型',
    dataIndex: 'ope_type'
  },
  {
    title: '页面元素A',
    dataIndex: 'el_name'
  },
  {
    title: '页面元素B-未测试',
    dataIndex: 'el_name_b'
  },
  {
    title: '元素操作值',
    dataIndex: 'ope_value'
  },
  {
    title: '输入值key',
    dataIndex: 'ope_value_key'
  },
  {
    title: '断言类型',
    dataIndex: 'ass_type'
  },
  {
    title: '断言操作值',
    dataIndex: 'ass_value'
  },
  {
    title: '操作',
    dataIndex: 'actions',
    align: 'center',
    width: 130
  }
])
const formModel = ref({})
const actionTitle = ref('添加元素')
const modalDialogRef = ref<ModalDialogType | null>(null)
const addUpdate = ref(0)
const updateId = ref(0)
const formItems = [
  {
    label: '页面名称',
    key: 'el_page',
    value: ref(''),
    placeholder: '请选择元素页面',
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
    label: '操作类型',
    key: 'ope_type',
    value: ref(''),
    type: 'cascader',
    required: true,
    placeholder: '请选择对元素的操作类型',
    validator: function () {
      if (!this.value.value && this.value.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '元素A',
    key: 'el_name',
    value: ref(''),
    placeholder: '请选择locating',
    required: false,
    type: 'select'
  },
  {
    label: '元素B',
    key: 'el_name_b',
    value: ref(''),
    placeholder: '请在元素操作值有第二个locating再选择',
    required: false,
    type: 'select'
  },
  {
    label: '元素操作值',
    key: 'ope_value',
    value: ref(''),
    type: 'textarea',
    required: true,
    placeholder: '请输入对元素的操作内容',
    validator: function () {
      if (!this.value.value && this.value.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '元素操作值',
    key: 'ope_value_key',
    value: ref(''),
    type: 'input',
    required: false,
    placeholder: '如果后续需要使用，请输入key'
  },
  {
    label: '断言类型',
    key: 'ass_type',
    value: ref(''),
    type: 'cascader',
    required: false,
    placeholder: '请选择断言类型'
  },
  {
    label: '断言值',
    key: 'ass_value',
    value: ref(''),
    type: 'textarea',
    required: false,
    placeholder: '请输入断言内容'
  }
] as FormItem[]

function doAppend() {
  actionTitle.value = '添加元素'
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

function onDelete(record: any) {
  Modal.confirm({
    title: '提示',
    content: '是否要删除此页面？',
    cancelText: '取消',
    okText: '删除',
    onOk: () => {
      deleted({
        url: uiRunSort,
        data: () => {
          return {
            id: record.id
          }
        }
      })
        .then((res) => {
          Message.success(res.msg)
          getUiRunSort()
        })
        .catch(console.log)
    }
  })
}

function onUpdate(item: any) {
  actionTitle.value = '编辑元素'
  modalDialogRef.value?.toggle()
  getEleName(item.el_name.page.id)
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

const handleChange = (_data: any) => {
  uiRunSortData.data = _data
  Message.info('测试拖动成功')
}

function onDataForm() {
  if (formItems.every((it) => (it.validator ? it.validator() : true))) {
    modalDialogRef.value?.toggle()
    console.log(formItems)
    let value = transformData(formItems)
    console.log(value)
    if (addUpdate.value === 1) {
      addUpdate.value = 0
      post({
        url: uiRunSort,
        data: () => {
          return {
            case: route.query.id,
            run_sort: uiRunSortData.data.length,
            project: route.query.project_id,
            el_name: value.el_name,
            el_name_b: value.el_name_b,
            el_page: value.el_page,
            ope_type: value.ope_type,
            ass_type: value.ass_type,
            ope_value: value.ope_value,
            ass_value: value.ass_value
          }
        }
      })
        .then((res) => {
          Message.success(res.msg)
          getUiRunSort()
        })
        .catch(console.log)
    } else if (addUpdate.value === 0) {
      let pageName = value.el_page
      if (typeof pageName === 'string') {
        pageName = getKeyByTitle(uiRunSortData.pageName, pageName)
      }
      let ele = value.el_name
      if (typeof ele === 'string') {
        ele = getKeyByTitle(uiRunSortData.eleName, ele)
      }
      let ele1 = value.el_name_b
      if (typeof ele === 'string') {
        ele = getKeyByTitle(uiRunSortData.eleName, ele)
      }
      addUpdate.value = 0
      value['id'] = updateId.value
      updateId.value = 0
      put({
        url: uiRunSort,
        data: () => {
          return {
            id: value.id,
            case: route.query.id,
            el_name: ele,
            el_name_b: ele1,
            el_page: pageName,
            ope_type: value.ope_type,
            ass_type: value.ass_type,
            ope_value: value.ope_value,
            ass_value: value.ass_value
          }
        }
      })
        .then((res) => {
          Message.success(res.msg)
          getUiRunSort()
        })
        .catch(console.log)
    }
  }
  uiRunSortData.eleName = []
}

function doSave() {
  Message.success('调用了保存')
}

function doResetSearch() {
  window.history.back()
}

const uiRunSortData: any = reactive({
  caseName: route.query.name,
  pageName: [],
  eleName: [],
  ass: [],
  ope: [],
  data: []
})

function getUiRunSort() {
  get({
    url: uiRunSort,
    data: () => {
      return {
        case_id: route.query.id
      }
    }
  })
    .then((res) => {
      uiRunSortData.data = res.data
      // const arrOpe = uiRunSortData.ope.map((item: any) => item.title)
      // const arrAss = uiRunSortData.ass.map((item: any) => item.title)
      // uiRunSortData.data.forEach((i: any) => {
      //   i.ope_type = arrOpe[i.ope_type]
      //   i.ass_type = arrAss[i.ass_type]
      // })
    })
    .catch(console.log)
}

function getUiRunSortAss() {
  get({
    url: uiRunSortAss
  })
    .then((res) => {
      uiRunSortData.ass = res.data
    })
    .catch(console.log)
}

function getUiRunSortOpe() {
  get({
    url: uiRunSortOpe
  })
    .then((res) => {
      uiRunSortData.ope = res.data
    })
    .catch(console.log)
}

function getPageName() {
  get({
    url: uiPageName
  })
    .then((res) => {
      uiRunSortData.pageName = res.data
    })
    .catch(console.log)
}

function getEleName(pageId: any) {
  get({
    url: uiUiElementName,
    data: () => {
      return {
        id: pageId
      }
    }
  })
    .then((res) => {
      uiRunSortData.eleName = res.data
    })
    .catch(console.log)
}

function upDataAssValue(value: string) {
  const inputItem = findItemByValue(uiRunSortData.ass, value)
  if (inputItem) {
    const parameter: any = inputItem.parameter
    Object.keys(parameter).forEach((key) => {
      parameter[key] = ''
    })
    formItems.forEach((item: any) => {
      if (item.key === 'ass_value') {
        item.value.value = JSON.stringify(parameter)
      }
    })
  }
}

function upDataOpeValue(value: string) {
  const inputItem = findItemByValue(uiRunSortData.ope, value)
  if (inputItem) {
    const parameter: any = inputItem.parameter
    Object.keys(parameter).forEach((key) => {
      parameter[key] = ''
    })
    formItems.forEach((item: any) => {
      if (item.key === 'ope_value') {
        item.value.value = JSON.stringify(parameter)
      }
    })
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

onMounted(() => {
  nextTick(async () => {
    await getUiRunSortAss()
    await getUiRunSortOpe()
    await getPageName()
    getUiRunSort()
  })
})
</script>
