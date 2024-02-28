<template>
  <div>
    <a-card title="页面步骤详情">
      <template #extra>
        <a-affix :offsetTop="80">
          <a-space>
            <a-button type="primary" size="small" @click="doAppend">增加</a-button>
            <a-button status="success" size="small" @click="onRunCase">调试</a-button>
            <a-button status="danger" size="small" @click="doResetSearch">返回</a-button>
          </a-space>
        </a-affix>
      </template>
      <div class="container">
        <a-space direction="vertical" style="width: 25%">
          <span>所属项目：{{ pageData.record.project?.name }}</span>
          <span>顶级模块：{{ pageData.record.module_name?.superior_module }}</span>
          <span>所属模块：{{ pageData.record.module_name?.name }}</span>
          <span>所属页面：{{ pageData.record.page?.name }}</span>
        </a-space>
        <a-space direction="vertical" style="width: 25%">
          <span>步骤ID：{{ pageData.record.id }}</span>
          <span>步骤名称：{{ pageData.record.name }}</span>
          <span>步骤状态：{{ pageData.record.type === 1 ? '通过' : '失败' }}</span>
        </a-space>
        <a-space direction="vertical" style="width: 50%">
          <span>步骤执行顺序：{{ pageData.record.run_flow }}</span>
        </a-space>
      </div>
    </a-card>

    <a-card>
      <a-table
        :columns="columns"
        :data="pageStepsData.data"
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
            :ellipsis="item.ellipsis"
            :tooltip="item.tooltip"
          >
            <template v-if="item.dataIndex === 'page_step'" #cell="{ record }">
              {{ record.page_step.name }}
            </template>
            <template v-else-if="item.dataIndex === 'ele_name_a'" #cell="{ record }">
              {{ record.ele_name_a == null ? '-' : record.ele_name_a.name }}
            </template>
            <!--              <template v-else-if="item.dataIndex === 'ele_name_b'" #cell="{ record }">-->
            <!--                {{ record.ele_name_b == null ? '-' : record.ele_name_b.name }}-->
            <!--              </template>-->
            <template v-else-if="item.dataIndex === 'ope_type'" #cell="{ record }">
              {{
                record.ope_type == null ? '-' : getLabelByValue(pageStepsData.ope, record.ope_type)
              }}
            </template>
            <template v-else-if="item.dataIndex === 'ope_value'" #cell="{ record }">
              {{ record.ope_value == null ? '-' : record.ope_value }}
            </template>
            <template v-else-if="item.dataIndex === 'ass_type'" #cell="{ record }">
              {{
                record.ass_type == null ? '-' : getLabelByValue(pageStepsData.ass, record.ass_type)
              }}
            </template>
            <template v-else-if="item.dataIndex === 'ass_value'" #cell="{ record }">
              {{ record.ass_value == null ? '-' : record.ass_value }}
            </template>
            <template v-else-if="item.dataIndex === 'type'" #cell="{ record }">
              <a-tag color="orangered" size="small" v-if="record.type === 1">断言</a-tag>
              <a-tag color="purple" size="small" v-else-if="record.type === 0">操作</a-tag>
            </template>
            <template v-else-if="item.dataIndex === 'actions'" #cell="{ record }">
              <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
              <a-button status="danger" type="text" size="mini" @click="onDelete(record)"
                >删除</a-button
              >
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-card>
    <ModalDialog ref="modalDialogRef" :title="pageStepsData.actionTitle" @confirm="onDataForm">
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
            <template v-else-if="item.type === 'select' && item.key === 'ele_name_a'">
              <a-select
                v-model="item.value"
                :placeholder="item.placeholder"
                :options="pageStepsData.uiPageName"
                :field-names="fieldNames"
                @change="elementIsLocator"
                value-key="key"
                allow-clear
                allow-search
              />
            </template>
            <!--              <template v-else-if="item.type === 'select' && item.key === 'ele_name_b'">-->
            <!--                <a-select-->
            <!--                  v-model="item.value"-->
            <!--                  :placeholder="item.placeholder"-->
            <!--                  :options="pageStepsData.uiPageName"-->
            <!--                  :field-names="fieldNames"-->
            <!--                  value-key="key"-->
            <!--                  allow-clear-->
            <!--                  allow-search-->
            <!--                />-->
            <!--              </template>-->
            <template v-else-if="item.type === 'cascader' && item.key === 'ope_type'">
              <a-space direction="vertical">
                <a-cascader
                  v-model="item.value"
                  :options="pageStepsData.ope"
                  :default-value="item.value"
                  expand-trigger="hover"
                  :placeholder="item.placeholder"
                  @change="upDataOpeValue(item.value)"
                  value-key="key"
                  style="width: 380px"
                  allow-search
                  allow-clear
                  :disabled="pageStepsData.isDisabledOpe"
                />
              </a-space>
            </template>
            <template v-else-if="item.type === 'cascader' && item.key === 'ass_type'">
              <a-space direction="vertical">
                <a-cascader
                  v-model="item.value"
                  :options="pageStepsData.ass"
                  :default-value="item.value"
                  expand-trigger="hover"
                  :placeholder="item.placeholder"
                  @change="upDataAssValue(item.value)"
                  value-key="key"
                  style="width: 380px"
                  allow-search
                  allow-clear
                  :disabled="pageStepsData.isDisabledAss"
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
                :disabled="pageStepsData.isDisabledOpe"
              />
            </template>
            <template v-else-if="item.type === 'textarea' && item.key === 'ass_value'">
              <a-textarea
                :auto-size="{ minRows: 4, maxRows: 7 }"
                :placeholder="item.placeholder"
                :default-value="item.value"
                v-model="item.value"
                allow-clear
                :disabled="pageStepsData.isDisabledAss"
              />
            </template>
            <template v-else-if="item.type === 'radio' && item.key === 'type'">
              <a-radio-group
                @change="changeStatus"
                v-model="item.value"
                :options="pageStepsData.plainOptions"
              />
            </template>
          </a-form-item>
        </a-form>
      </template>
    </ModalDialog>
  </div>
</template>
<script lang="ts" setup>
  import { nextTick, onMounted, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'

  import {
    uiPageStepsDetailed,
    uiPageStepsDetailedAss,
    uiPageStepsDetailedOpe,
    uiPagePutStepSort,
    uiUiElementName,
    uiStepsRun,
    uiElementIsLocator,
  } from '@/api/url'
  import { deleted, get, post, put } from '@/api/http'
  import { ModalDialogType } from '@/types/components'
  import { useRoute } from 'vue-router'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { usePageData } from '@/store/page-data'
  import { useTestObj } from '@/store/modules/get-test-obj'
  const pageData = usePageData()
  const testObj = useTestObj()

  const route = useRoute()
  const formModel = ref({})
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pageStepsData = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '添加测试对象',
    eleName: [],
    ass: [],
    ope: [],
    data: [],
    uiPageName: [],
    isDisabledOpe: false,
    isDisabledAss: true,
    value: 0,
    plainOptions: [
      { label: '操作', value: 0 },
      { label: '断言', value: 1 },
    ],
  })
  const columns = reactive([
    {
      title: '元素名称',
      dataIndex: 'ele_name_a',
      width: 150,
    },
    // {
    //   title: '页面元素B',
    //   dataIndex: 'ele_name_b'
    // },
    {
      title: '步骤类型',
      dataIndex: 'type',
      width: 90,
    },
    {
      title: '元素操作类型',
      dataIndex: 'ope_type',
      width: 150,
    },
    {
      title: '元素操作值',
      dataIndex: 'ope_value',
      ellipsis: true,
      tooltip: true,
    },

    {
      title: '断言类型',
      dataIndex: 'ass_type',
      width: 150,
    },
    {
      title: '断言操作值',
      dataIndex: 'ass_value',
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '操作',
      dataIndex: 'actions',
      align: 'center',
      width: 130,
    },
  ])

  const formItems = reactive([
    {
      label: '步骤类型',
      key: 'type',
      value: 0,
      type: 'radio',
      required: true,
      placeholder: '请选择对元素的操作类型',
      validator: function () {
        return true
      },
    },
    {
      label: '元素名称',
      key: 'ele_name_a',
      value: null,
      placeholder: '请选择locating',
      required: false,
      type: 'select',
      validator: function () {
        return true
      },
    },
    // {
    //   label: '元素B',
    //   key: 'ele_name_b',
    //   value: null,
    //   placeholder: '请在元素操作值有第二个locating再选择',
    //   required: false,
    //   type: 'select'
    // },
    {
      label: '元素操作',
      key: 'ope_type',
      value: null,
      type: 'cascader',
      required: false,
      placeholder: '请选择对元素的操作',
      validator: function () {
        return true
      },
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
      },
    },
    {
      label: '断言类型',
      key: 'ass_type',
      value: null,
      type: 'cascader',
      required: false,
      placeholder: '请选择断言类型',
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
      },
    },
  ])

  function changeStatus(event: number) {
    pageStepsData.isDisabledOpe = event == 1
    pageStepsData.isDisabledAss = event == 0
    formItems.forEach((item) => {
      item.value = null
    })
    formItems[0].value = event
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

  function doAppend() {
    pageStepsData.isDisabledOpe = false
    pageStepsData.isDisabledAss = true
    pageStepsData.actionTitle = '添加详细步骤'
    pageStepsData.isAdd = true
    modalDialogRef.value?.toggle()
    formItems.forEach((it: any) => {
      if (it.reset) {
        it.reset()
      } else {
        if (it.key === 'type') {
          it.value = 0
        } else {
          it.value = ''
        }
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
          url: uiPageStepsDetailed,
          data: () => {
            return {
              id: record.id,
              parent_id: record.page_step.id,
            }
          },
        })
          .then((res) => {
            Message.success(res.msg)
            getUiRunSort()
          })
          .catch(console.log)
      },
    })
  }

  function onUpdate(item: any) {
    if (item.type === 0) {
      pageStepsData.isDisabledOpe = false
      pageStepsData.isDisabledAss = true
    } else if (item.type === 1) {
      pageStepsData.isDisabledOpe = true
      pageStepsData.isDisabledAss = false
    }
    pageStepsData.actionTitle = '编辑详细步骤'
    pageStepsData.isAdd = false
    pageStepsData.updateId = item.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it: any) => {
        const propName = item[it.key]
        if (typeof propName === 'object' && propName !== null) {
          if (it.key === 'ope_value' || it.key === 'ass_value') {
            it.value = JSON.stringify(propName)
          } else {
            it.value = propName.id
          }
        } else {
          it.value = propName
        }
      })
    })
  }

  const handleChange = (_data: any) => {
    pageStepsData.data = _data
    let data: any = []
    pageStepsData.data.forEach((item: any, index) => {
      data.push({
        id: item.id,
        step_sort: index,
      })
    })
    put({
      url: uiPagePutStepSort,
      data: () => {
        return {
          step_sort_list: data,
        }
      },
    })
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      modalDialogRef.value?.toggle()
      let value = getFormItems(formItems)
      value['page_step'] = route.query.id
      if (pageStepsData.isAdd) {
        post({
          url: uiPageStepsDetailed,
          data: () => {
            value['step_sort'] = pageStepsData.data.length
            return value
          },
        })
          .then((res) => {
            Message.success(res.msg)
            getUiRunSort()
          })
          .catch(console.log)
      } else {
        put({
          url: uiPageStepsDetailed,
          data: () => {
            value['id'] = pageStepsData.updateId
            return value
          },
        })
          .then((res) => {
            Message.success(res.msg)
            getUiRunSort()
          })
          .catch(console.log)
      }
    }
    pageStepsData.eleName = []
    pageStepsData.plainOptions = [
      { label: '操作', value: 0 },
      { label: '断言', value: 1 },
    ]
  }

  function doResetSearch() {
    window.history.back()
  }

  function getUiRunSort() {
    get({
      url: uiPageStepsDetailed,
      data: () => {
        return {
          page_step_id: route.query.id,
        }
      },
    })
      .then((res) => {
        pageStepsData.data = res.data
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
        pageStepsData.ass = res.data
      })
      .catch(console.log)
  }

  function getUiRunSortOpe() {
    get({
      url: uiPageStepsDetailedOpe,
      data: () => {
        return {
          page_type: route.query.pageType,
        }
      },
    })
      .then((res) => {
        pageStepsData.ope = res.data
      })
      .catch(console.log)
  }

  function getEleName() {
    get({
      url: uiUiElementName,
      data: () => {
        return {
          id: route.query.pageId,
        }
      },
    })
      .then((res) => {
        pageStepsData.uiPageName = res.data
      })
      .catch(console.log)
  }

  function upDataAssValue(value: any) {
    const inputItem = findItemByValue(pageStepsData.ass, value)
    if (inputItem) {
      const parameter: any = inputItem.parameter
      Object.keys(parameter).forEach((key) => {
        parameter[key] = ''
      })
      formItems.forEach((item: any) => {
        if (item.key === 'ass_value') {
          item.value = JSON.stringify(parameter)
        }
      })
    }
  }

  function upDataOpeValue(value: any) {
    const inputItem = findItemByValue(pageStepsData.ope, value)
    if (inputItem) {
      const parameter: any = inputItem.parameter
      Object.keys(parameter).forEach((key) => {
        parameter[key] = ''
      })
      formItems.forEach((item: any) => {
        if (item.key === 'ope_value') {
          item.value = JSON.stringify(parameter)
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
  function onRunCase() {
    if (testObj.selectValue == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    get({
      url: uiStepsRun,
      data: () => {
        return {
          page_step_id: route.query.id,
          te: testObj.selectValue,
        }
      },
    })
      .then((res) => {
        Message.loading(res.msg)
      })
      .catch(console.log)
  }
  function elementIsLocator(key: number) {
    console.log(key)
    get({
      url: uiElementIsLocator,
      data: () => {
        return {
          element_id: key,
        }
      },
    })
      .then((res) => {
        if (res.data === '1') {
          formItems.forEach((item: any) => {
            if (item.key === 'ope_value') {
              let data = JSON.parse(item.value)
              data['element_locator'] = ''
              item.value = JSON.stringify(data)
            }
          })
        }
      })
      .catch(console.log)
  }
  onMounted(() => {
    nextTick(async () => {
      await getUiRunSortAss()
      await getUiRunSortOpe()
      await getEleName()
      getUiRunSort()
    })
  })
</script>
