<template>
  <div>
    <div id="tableHeaderContainer" class="relative" :style="{ zIndex: 9 }">
      <a-card
        :title="
          '所属页面：' +
          pageEleData.pageName +
          ' | ' +
          '所属项目：' +
          pageEleData.project_name +
          ' (' +
          '共：' +
          pageEleData.totalSize +
          '个元素)'
        "
      >
        <template #extra>
          <a-affix :offsetTop="80">
            <a-space>
              <a-button type="primary" size="small" @click="doAppend">增加</a-button>
              <a-button status="danger" size="small" @click="doResetSearch">返回</a-button>
            </a-space>
          </a-affix>
        </template>
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
                <a-tag color="orangered" size="small" v-if="record.exp === 0">W_XPATH</a-tag>
                <a-tag color="gold" size="small" v-else-if="record.exp === 1">W_ID</a-tag>
                <a-tag color="lime" size="small" v-else-if="record.exp === 3">W_文本</a-tag>
                <a-tag color="green" size="small" v-else-if="record.exp === 4">W_占位符</a-tag>
                <a-tag color="cyan" size="small" v-else-if="record.exp === 5">W_CSS</a-tag>
                <a-tag color="blue" size="small" v-else-if="record.exp === 11">A_DESCRIPTION</a-tag>
                <a-tag color="arcoblue" size="small" v-else-if="record.exp === 12">A_BOUNDS</a-tag>
                <a-tag color="purple" size="small" v-else-if="record.exp === 13">A_百分比坐标点击</a-tag>
              </template>
              <template v-else-if="item.dataIndex === 'actions'" #cell="{ record }">
                <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
                <a-button status="danger" type="text" size="mini" @click="onDelete(record)">删除</a-button>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-card>
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
    </div>
  </div>
</template>
<script lang="ts" setup>
import { nextTick, onMounted, reactive, ref } from 'vue'
import { Message, Modal } from '@arco-design/web-vue'
import { uiUiElement, getUiElementExp } from '@/api/url'
import { deleted, get, post, put } from '@/api/http'
import { FormItem, ModalDialogType } from '@/types/components'
import { useRoute } from 'vue-router'
import { getFormItems } from '@/utils/datacleaning'
import { fieldNames } from '@/setting'

const route = useRoute()
const formModel = ref({})
const modalDialogRef = ref<ModalDialogType | null>(null)
const pageEleData = reactive({
  isAdd: false,
  updateId: 0,
  actionTitle: '添加元素',
  pageName: route.query.name,
  project_name: route.query.project_name,
  eleExp: [],
  totalSize: 0,
  data: []
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
    title: '元素表达式',
    dataIndex: 'loc'
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
    width: 130
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
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '表达式类型',
    key: 'exp',
    value: '',
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
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
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
    value['project'] = route.query.project_id
    value['page'] = route.query.id
    if (pageEleData.isAdd) {
      post({
        url: uiUiElement,
        data: () => {
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
      // pageEleData.data.forEach((i: any) => {
      //   let typeOpe = pageEleData.eleExp.find((obj: any) => obj.key === i.exp)
      //   i.exp = typeOpe.title
      // })
    })
    .catch(console.log)
}

function getEleExp() {
  get({
    url: getUiElementExp,
    data: () => {
      return {
        id: 4
      }
    }
  })
    .then((res) => {
      pageEleData.eleExp = res.data
    })
    .catch(console.log)
}

onMounted(() => {
  nextTick(async () => {
    doRefresh()
    getEleExp()
  })
})
</script>
