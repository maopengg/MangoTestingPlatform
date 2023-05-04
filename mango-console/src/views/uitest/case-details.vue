<template>
  <div>
    <div id="tableHeaderContainer" class="relative" :style="{ zIndex: 9 }">
      <a-card :title="'用例：' + uiRunSortData.caseName + ' | ' + '所属项目组：' + route.query.team">
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
          :draggable="{}"
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

              <template v-else-if="item.type === 'select' && item.key === 'el_page'">
                <a-select v-model="item.value.value" :placeholder="item.placeholder" @change="getEleName" allow-clear>
                  <a-option
                    v-for="optionItem of uiRunSortData.pageName"
                    :value="optionItem.label"
                    :key="optionItem.value"
                    :label="optionItem.label"
                  />
                </a-select>
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'el_name'">
                <a-select v-model="item.value.value" :placeholder="item.placeholder" allow-clear>
                  <a-option
                    v-for="optionItem of uiRunSortData.eleName"
                    :value="optionItem.label"
                    :key="optionItem.value"
                    :label="optionItem.label"
                  />
                </a-select>
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'ope_type'">
                <a-select v-model="item.value.value" :placeholder="item.placeholder" allow-clear>
                  <a-option
                    v-for="optionItem of uiRunSortData.ope"
                    :value="optionItem.label"
                    :key="optionItem.value"
                    :label="optionItem.label"
                  />
                </a-select>
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'ass_type'">
                <a-select v-model="item.value.value" :placeholder="item.placeholder" allow-clear>
                  <a-option
                    v-for="optionItem of uiRunSortData.ass"
                    :value="optionItem.label"
                    :key="optionItem.value"
                    :label="optionItem.label"
                  />
                </a-select>
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
import { getExpValue, transformData } from '@/utils/datacleaning'

const route = useRoute()

const columns = reactive([
  {
    title: '页面名称',
    dataIndex: 'el_page'
  },
  {
    title: '页面元素',
    dataIndex: 'el_name'
  },
  {
    title: '操作类型',
    dataIndex: 'ope_type'
  },
  {
    title: '元素操作值',
    dataIndex: 'ope_value'
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
    type: 'select'
  },
  {
    label: '元素名称',
    key: 'el_name',
    value: ref(''),
    placeholder: '请选择元素页面',
    required: false,
    type: 'select'
  },
  {
    label: '操作类型',
    key: 'ope_type',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请选择对元素的操作类型'
  },
  {
    label: '元素操作值',
    key: 'ope_value',
    value: ref(''),
    type: 'input',
    required: false,
    placeholder: '请输入对元素的操作内容'
  },
  {
    label: '断言类型',
    key: 'ass_type',
    value: ref(''),
    type: 'select',
    required: false,
    placeholder: '请选择断言类型'
  },
  {
    label: '断言值',
    key: 'ass_value',
    value: ref(''),
    type: 'input',
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
  addUpdate.value = 0
  updateId.value = item.id
  nextTick(() => {
    formItems.forEach((it) => {
      const key = it.key
      console.log(item[key].name)

      const propName = item[key]
      if (propName || propName === null) {
        it.value.value = propName
      }
    })
  })
}

const handleChange = (_data: any) => {
  uiRunSortData.data = _data
}

function onDataForm() {
  if (formItems.every((it) => (it.validator ? it.validator() : true))) {
    modalDialogRef.value?.toggle()
    let value = transformData(formItems)
    let opeValue = getExpValue(value.ope_type, uiRunSortData.ope)
    let assValue = getExpValue(value.ass_type, uiRunSortData.ass)
    if (addUpdate.value === 1) {
      addUpdate.value = 0
      post({
        url: uiRunSort,
        data: () => {
          return {
            case: route.query.name,
            run_sort: uiRunSortData.data.length,
            team: route.query.team,
            el_name: value.el_name,
            el_page: value.el_page,
            ope_type: opeValue,
            ass_type: assValue,
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
      addUpdate.value = 0
      value['id'] = updateId.value
      updateId.value = 0
      put({
        url: uiRunSort,
        data: () => {
          return {
            id: value.id,
            case: route.query.name,
            run_sort: uiRunSortData.data.length,
            team: route.query.team,
            el_name: value.el_name,
            el_page: value.el_page,
            ope_type: opeValue,
            ass_type: assValue,
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
      uiRunSortData.data.forEach((i: any) => {
        let typeOpe = uiRunSortData.ope.find((obj: any) => obj.value === i.ope_type)
        let decOpe = typeOpe.label
        i.ope_type = decOpe
        let typeAss = uiRunSortData.ass.find((obj: any) => obj.value === i.ass_type)
        let decAss = typeAss.label
        i.ass_type = decAss
      })
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

function getEleName() {
  get({
    url: uiUiElementName,
    data: () => {
      return {
        name: formItems[0].value.value
      }
    }
  })
    .then((res) => {
      uiRunSortData.eleName = res.data
    })
    .catch(console.log)
}

onMounted(() => {
  nextTick(async () => {
    await getUiRunSortAss()
    await getUiRunSortOpe()
    getUiRunSort()
    getPageName()
  })
})
</script>
