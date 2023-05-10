<template>
  <div>
    <div id="tableHeaderContainer" class="relative" :style="{ zIndex: 9 }">
      <a-card :title="'所属页面：' + uiElementData.pageName + ' | ' + '所属项目组：' + uiElementData.team_name">
        <template #extra>
          <a-affix :offsetTop="80">
            <a-space>
              <a-button type="primary" size="small" @click="doAppend">增加</a-button>
              <a-button status="danger" size="small" @click="doResetSearch">返回</a-button>
            </a-space>
          </a-affix>
        </template>
        <a-table :columns="columns" :data="uiElementData.data" :pagination="false" :bordered="false">
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
              <template v-if="item.dataIndex === 'actions'" #cell="{ record }">
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
              <template v-else-if="item.type === 'select'">
                <a-select
                  v-model="item.value.value"
                  :placeholder="item.placeholder"
                  :options="uiElementData.eleExp"
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
import { nextTick, onMounted, reactive, ref } from 'vue'
import { Message, Modal } from '@arco-design/web-vue'
import { uiUiElement, getUiElementExp } from '@/api/url'
import { deleted, get, post, put } from '@/api/http'
import { FormItem, ModalDialogType } from '@/types/components'
import { useRoute } from 'vue-router'
import { getKeyByTitle, transformData } from '@/utils/datacleaning'
import { fieldNames } from '@/setting'

const route = useRoute()

const columns = reactive([
  {
    title: '元素名称',
    dataIndex: 'name',
    width: 150
  },
  {
    title: '表达式类型',
    dataIndex: 'exp',
    width: 150
  },
  {
    title: '元素表达式',
    dataIndex: 'loc'
  },
  {
    title: '等待时间',
    dataIndex: 'sleep',
    width: 150
  },
  {
    title: '元素下标',
    dataIndex: 'sub',
    width: 150
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
const updateId: any = ref('')
const formItems = [
  {
    label: '元素名称',
    key: 'name',
    value: ref(''),
    placeholder: '请输入元素名称',
    required: true,
    type: 'input',
    validator: function () {
      if (!this.value.value && this.value.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '表达式类型',
    key: 'exp',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请选择元素表达式类型',
    validator: function () {
      if (!this.value.value && this.value.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '元素表达式',
    key: 'loc',
    value: ref(),
    type: 'input',
    required: true,
    placeholder: '请输入元素表达式',
    validator: function () {
      if (!this.value.value && this.value.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '等待时间',
    key: 'sleep',
    value: ref(''),
    type: 'input',
    required: false,
    placeholder: '请输入元素等待时间'
  },
  {
    label: '元素下标',
    key: 'sub',
    value: ref(''),
    type: 'input',
    required: false,
    placeholder: '请输入元素下标'
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
        url: uiUiElement,
        data: () => {
          return {
            id: '[' + record.id + ']'
          }
        }
      })
        .then((res) => {
          Message.success(res.msg)
          getUiElement()
        })
        .catch(console.log)
    }
  })
}

function onUpdate(record: any) {
  actionTitle.value = '编辑元素'
  modalDialogRef.value?.toggle()
  addUpdate.value = 0
  updateId.value = record.id
  nextTick(() => {
    formItems.forEach((it) => {
      const key = it.key
      const propName = record[key]
      if (typeof propName === 'object' && propName !== null) {
        it.value.value = propName.name
      } else {
        it.value.value = propName
      }
    })
  })
}

function onDataForm() {
  if (formItems.every((it) => (it.validator ? it.validator() : true))) {
    modalDialogRef.value?.toggle()
    let value = transformData(formItems)
    if (addUpdate.value === 1) {
      post({
        url: uiUiElement,
        data: () => {
          return {
            team: route.query.team_id,
            page: route.query.id,
            name: value.name,
            exp: value.exp,
            loc: value.loc,
            sleep: value.sleep,
            sub: value.sub
          }
        }
      })
        .then((res) => {
          Message.success(res.msg)
          getUiElement()
        })
        .catch(console.log)
    } else if (addUpdate.value === 0) {
      let exp = getKeyByTitle(uiElementData.eleExp, value.exp)

      value['id'] = updateId.value
      updateId.value = 0
      put({
        url: uiUiElement,
        data: () => {
          return {
            team: route.query.team_id,
            page: route.query.id,
            name: value.name,
            exp: exp,
            loc: value.loc,
            sleep: value.sleep,
            sub: value.sub,
            id: value.id
          }
        }
      })
        .then((res) => {
          Message.success(res.msg)
          getUiElement()
        })
        .catch(console.log)
    }
  }
}

function doResetSearch() {
  window.history.back()
}

const uiElementData: any = reactive({
  pageName: route.query.name,
  team_name: route.query.team_name,
  eleExp: []
})

function getUiElement() {
  get({
    url: uiUiElement,
    data: () => {
      return {
        page_id: route.query.id
      }
    }
  })
    .then((res) => {
      uiElementData.data = res.data
      uiElementData.data.forEach((i: any) => {
        let typeOpe = uiElementData.eleExp.find((obj: any) => obj.key === i.exp)
        i.exp = typeOpe.title
      })
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
      uiElementData.eleExp = res.data
    })
    .catch(console.log)
}

onMounted(() => {
  nextTick(async () => {
    getUiElement()
    getEleExp()
  })
})
</script>
