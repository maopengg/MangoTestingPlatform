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
          <span>所属项目：{{ pageData.record.project_product?.project?.name }}</span>
          <span>顶级模块：{{ pageData.record.module?.superior_module }}</span>
          <span>所属模块：{{ pageData.record.module?.name }}</span>
        </a-space>
        <a-space direction="vertical" style="width: 75%">
          <span>页面名称：{{ pageData.record.name }}</span>
          <span>页面地址：{{ pageData.record.url }}</span>
          <span>元素个数：{{ data.totalSize }}</span>
          <span>页面类型：{{ pageData.record.type }}</span>
        </a-space>
      </div>
    </a-card>
    <a-card>
      <a-table :columns="columns" :data="data.data" :pagination="false" :bordered="false">
        <template #columns>
          <a-table-column
            :key="item.key"
            v-for="item of columns"
            :align="item.align"
            :title="item.title"
            :width="item.width"
            :data-index="item.dataIndex"
            :fixed="item.fixed"
            :ellipsis="item.ellipsis"
            :tooltip="item.tooltip"
          >
            <template v-if="item.dataIndex === 'exp'" #cell="{ record }">
              <a-tag color="orangered" size="small" v-if="record.exp === 0">XPATH</a-tag>
              <a-tag color="gold" size="small" v-else-if="record.exp === 1">TestID</a-tag>
              <a-tag color="arcoblue" size="small" v-else-if="record.exp === 2">定位器</a-tag>
              <a-tag color="lime" size="small" v-else-if="record.exp === 3">文本</a-tag>
              <a-tag color="green" size="small" v-else-if="record.exp === 4">占位符</a-tag>
              <a-tag color="cyan" size="small" v-else-if="record.exp === 5">标签</a-tag>
              <a-tag color="cyan" size="small" v-else-if="record.exp === 6">标题</a-tag>
              <a-tag color="cyan" size="small" v-else-if="record.exp === 7">ROLE</a-tag>
              <a-tag color="cyan" size="small" v-else-if="record.exp === 8">AIT_TEXT</a-tag>
              <a-tag color="cyan" size="small" v-else-if="record.exp === 9">CSS</a-tag>
              <a-tag color="blue" size="small" v-else-if="record.exp === 11">A_DESCRIPTION</a-tag>
              <a-tag color="arcoblue" size="small" v-else-if="record.exp === 12">A_BOUNDS</a-tag>
              <a-tag color="arcoblue" size="small" v-else-if="record.exp === 14">resourceId</a-tag>
              <a-tag color="purple" size="small" v-else-if="record.exp === 13"
                >A_百分比坐标点击</a-tag
              >
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
              <a-button status="danger" type="text" size="mini" @click="onDelete(record)"
                >删除</a-button
              >
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-card>
  </div>
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
          <template v-else-if="item.type === 'select'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="data.eleExp"
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
  <ModalDialog ref="modalDialogRef1" :title="data.actionTitle" @confirm="onDataForm1">
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
                :options="data.ope"
                :default-value="item.value"
                expand-trigger="hover"
                :placeholder="item.placeholder"
                @change="upDataOpeValue(item.value)"
                value-key="key"
                style="width: 380px"
                allow-search
                allow-clear
                :disabled="data.isDisabledOpe"
              />
            </a-space>
          </template>
          <template v-else-if="item.type === 'cascader' && item.key === 'ass_type'">
            <a-space direction="vertical">
              <a-cascader
                v-model="item.value"
                :options="data.ass"
                :default-value="item.value"
                expand-trigger="hover"
                :placeholder="item.placeholder"
                @change="upDataAssValue(item.value)"
                value-key="key"
                style="width: 380px"
                allow-search
                allow-clear
                :disabled="data.isDisabledAss"
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
              :disabled="data.isDisabledOpe"
            />
          </template>
          <template v-else-if="item.type === 'textarea' && item.key === 'ass_value'">
            <a-textarea
              :auto-size="{ minRows: 4, maxRows: 7 }"
              :placeholder="item.placeholder"
              :default-value="item.value"
              v-model="item.value"
              allow-clear
              :disabled="data.isDisabledAss"
            />
          </template>
          <template v-else-if="item.type === 'radio' && item.key === 'type'">
            <a-radio-group
              @change="changeStatus"
              v-model="item.value"
              :options="data.plainOptions"
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
    uiUiElement,
    uiUiElementPutIsIframe,
    uiPageStepsDetailedAss,
    uiUiElementTest,
  } from '@/api/url'
  import { formItems1, columns, formItems } from './config'

  import { deleted, get, post, put } from '@/api/http'
  import { ModalDialogType } from '@/types/components'
  import { useRoute } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { useTestObj } from '@/store/modules/get-test-obj'
  import { usePageData } from '@/store/page-data'
  import { getUiElement, getUiPageStepsDetailedOpe } from '@/api/uitest'
  import { getSystemEnumExp } from '@/api/system'

  const testObj = useTestObj()
  const pageData: any = usePageData()

  const route = useRoute()
  const formModel = ref({})
  const formModel1 = ref({})
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const modalDialogRef1 = ref<ModalDialogType | null>(null)
  const data: any = reactive({
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
      { label: '断言', value: 1 },
    ],
  })

  function doAppend() {
    data.actionTitle = '添加元素'
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

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此元素？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleted({
          url: uiUiElement,
          data: () => {
            return {
              id: '[' + record.id + ']',
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

  function onUpdate(record: any) {
    data.actionTitle = '编辑添加元素'
    data.isAdd = false
    data.updateId = record.id
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
      if (data.isAdd) {
        post({
          url: uiUiElement,
          data: () => {
            value['is_iframe'] = 0
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
          url: uiUiElement,
          data: () => {
            value['id'] = data.updateId
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

  function doResetSearch() {
    window.history.back()
  }

  function doRefresh() {
    getUiElement(route.query.id)
      .then((res) => {
        data.data = res.data
        data.totalSize = res.totalSize
      })
      .catch(console.log)
  }

  function getEleExp() {
    getSystemEnumExp()
      .then((result) => {
        data.eleExp = result
      })
      .catch((error) => {
        console.error(error)
      })
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
                is_iframe: newValue ? 1 : 0,
              }
            },
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
    getUiPageStepsDetailedOpe(route.query.pageType)
      .then((res) => {
        data.ope = res.data
      })
      .catch(console.log)
  }

  function getUiRunSortAss() {
    get({
      url: uiPageStepsDetailedAss,
      data: () => {
        return {
          page_type: route.query.pageType,
        }
      },
    })
      .then((res) => {
        data.ass = res.data
      })
      .catch(console.log)
  }

  function changeStatus(event: number) {
    data.isDisabledOpe = event == 1
    data.isDisabledAss = event == 0
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
      value['id'] = data.id
      value['page_id'] = pageData.record.id
      value['project_id'] = pageData.record.project.id
      post({
        url: uiUiElementTest,
        data: () => {
          return value
        },
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
    const inputItem = findItemByValue(data.ass, value)
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
    const inputItem = findItemByValue(data.ope, value)
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
    data.actionTitle = `对元素：${record.name} 进行操作或断言`
    data.id = record.id
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
