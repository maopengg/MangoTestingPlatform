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
          <span>所属项目：{{ pageData.record.project_product?.project?.name }}</span>
          <span>顶级模块：{{ pageData.record.module?.superior_module }}</span>
          <span>所属模块：{{ pageData.record.module?.name }}</span>
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
        :data="data.dataList"
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
            <template v-else-if="item.dataIndex === 'ele_name'" #cell="{ record }">
              {{ record.ele_name == null ? '-' : record.ele_name.name }}
            </template>
            <template v-else-if="item.dataIndex === 'ope_type'" #cell="{ record }">
              {{ record.ope_type == null ? '-' : getLabelByValue(data.ope, record.ope_type) }}
            </template>
            <template v-else-if="item.dataIndex === 'ope_value'" #cell="{ record }">
              {{ record.ope_value == null ? '-' : record.ope_value }}
            </template>
            <template v-else-if="item.dataIndex === 'ass_type'" #cell="{ record }">
              {{ record.ass_type == null ? '-' : getLabelByValue(data.ass, record.ass_type) }}
            </template>
            <template v-else-if="item.dataIndex === 'ass_value'" #cell="{ record }">
              {{ record.ass_value == null ? '-' : record.ass_value }}
            </template>
            <template v-else-if="item.dataIndex === 'key_list'" #cell="{ record }">
              {{ record.key_list }}
            </template>
            <template v-else-if="item.dataIndex === 'type'" #cell="{ record }">
              <a-tag color="orangered" size="small" v-if="record.type === 1">断言</a-tag>
              <a-tag color="orange" size="small" v-else-if="record.type === 0">操作</a-tag>
              <a-tag color="blue" size="small" v-else-if="record.type === 2">SQL</a-tag>
              <a-tag color="blue" size="small" v-else-if="record.type === 3">参数</a-tag>
            </template>
            <template v-else-if="item.dataIndex === 'actions'" #cell="{ record }">
              <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
              <a-button status="danger" type="text" size="mini" @click="onDelete(record)">删除 </a-button>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-card>
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
            <template v-else-if="item.type === 'select' && item.key === 'ele_name'">
              <a-select
                v-model="item.value"
                :placeholder="item.placeholder"
                :options="data.uiPageName"
                :field-names="fieldNames"
                value-key="key"
                allow-clear
                allow-search
              />
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
              />
            </template>
            <template v-else-if="item.type === 'textarea' && item.key === 'ass_value'">
              <a-textarea
                :auto-size="{ minRows: 4, maxRows: 7 }"
                :placeholder="item.placeholder"
                :default-value="item.value"
                v-model="item.value"
                allow-clear
              />
            </template>
            <template v-else-if="item.type === 'radio' && item.key === 'type'">
              <a-radio-group @change="changeStatus" v-model="data.type" :options="data.plainOptions" />
            </template>
            <template v-else-if="item.type === 'textarea' && item.key === 'key_list'">
              <a-textarea
                :auto-size="{ minRows: 4, maxRows: 7 }"
                :placeholder="item.placeholder"
                :default-value="item.value"
                v-model="item.value"
                allow-clear
              />
            </template>

            <template v-else-if="item.type === 'textarea' && item.key === 'sql'">
              <a-textarea
                :auto-size="{ minRows: 4, maxRows: 7 }"
                :placeholder="item.placeholder"
                :default-value="item.value"
                v-model="item.value"
                allow-clear
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

  import { ModalDialogType } from '@/types/components'
  import { useRoute } from 'vue-router'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { usePageData } from '@/store/page-data'
  import { useTestObj } from '@/store/modules/get-test-obj'
  import { columns, formItems, Item } from './config'
  import {
    deleteUiPageStepsDetailed,
    getUiPageStepsDetailed,
    getUiPageStepsDetailedAss,
    getUiPageStepsDetailedOpe,
    getUiStepsRun,
    getUiUiElementName,
    postUiPageStepsDetailed,
    putUiPagePutStepSort,
    putUiPageStepsDetailed,
  } from '@/api/uitest'
  import { getSystemEnumUiElementOperation } from '@/api/system'
  const pageData = usePageData()
  const testObj = useTestObj()

  const route = useRoute()
  const formModel = ref({})
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const data = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '添加测试对象',
    ass: [],
    ope: [],
    dataList: [],
    uiPageName: [],
    type: 0,
    plainOptions: [],
  })

  function changeStatus(event: number) {
    data.type = event
    for (let i = formItems.length - 1; i >= 0; i--) {
      if (formItems[i].key !== 'type') {
        formItems.splice(i, 1)
      }
    }
    if (event === 0) {
      if (!formItems.some((item) => item.key === 'ele_name' || formItems.some((item) => item.key === 'ope_type'))) {
        formItems.push(
          {
            label: '元素操作',
            key: 'ope_type',
            value: '',
            type: 'cascader',
            required: true,
            placeholder: '请选择对元素的操作',
            validator: function () {
              return true
            },
          },
          {
            label: '选择元素',
            key: 'ele_name',
            value: '',
            placeholder: '请选择locating',
            required: false,
            type: 'select',
            validator: function () {
              return true
            },
          }
        )
      }
    } else if (event === 1) {
      if (!formItems.some((item) => item.key === 'ass_type')) {
        formItems.push(
          {
            label: '断言类型',
            key: 'ass_type',
            value: '',
            type: 'cascader',
            required: true,
            placeholder: '请选择断言类型',
            validator: function () {
              return true
            },
          },
          {
            label: '选择元素',
            key: 'ele_name',
            value: '',
            placeholder: '请选择locating',
            required: false,
            type: 'select',
            validator: function () {
              return true
            },
          }
        )
      }
    } else if (event === 2) {
      if (!formItems.some((item) => item.key === 'sql') || !formItems.some((item) => item.key === 'key_list')) {
        formItems.push(
          {
            label: 'key_list',
            key: 'key_list',
            value: '',
            type: 'textarea',
            required: true,
            placeholder: '请输入sql查询结果的key_list',
            validator: function () {
              if (this.value !== '') {
                try {
                  this.value = JSON.parse(this.value)
                } catch (e) {
                  Message.error('key_list值请输入json数据类型')
                  return false
                }
              }
              return true
            },
          },
          {
            label: 'sql语句',
            key: 'sql',
            value: '',
            type: 'textarea',
            required: true,
            placeholder: '请输入sql',
            validator: function () {
              return true
            },
          }
        )
      }
    } else {
      if (!formItems.some((item) => item.key === 'key') || !formItems.some((item) => item.key === 'value')) {
        formItems.push(
          {
            label: 'key',
            key: 'key',
            value: '',
            type: 'input',
            required: true,
            placeholder: '请输入key',
            validator: function () {
              return true
            },
          },
          {
            label: 'value',
            key: 'value',
            value: '',
            type: 'input',
            required: true,
            placeholder: '请输入value',
            validator: function () {
              return true
            },
          }
        )
      }
    }
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
    changeStatus(0)
    data.type = 0
    data.actionTitle = '添加详细步骤'
    data.isAdd = true
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
      content: '是否要删除此步骤详情？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteUiPageStepsDetailed(record.id, record.page_step.id)
          .then((res) => {
            Message.success(res.msg)
            getUiRunSort()
          })
          .catch(console.log)
      },
    })
  }

  function onUpdate(item: any) {
    data.type = item.type
    changeStatus(item.type)
    if (item.ope_type) {
      upDataOpeValue(item.ope_type)
    }

    if (item.ass_type) {
      upDataAssValue(item.ass_type)
    }
    data.actionTitle = '编辑详细步骤'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it: any) => {
        const propName = item[it.key]
        if (typeof propName === 'object' && propName !== null) {
          if (it.key === 'ope_value' || it.key === 'ass_value' || it.key === 'key_list') {
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
    data.dataList = _data
    let data1: any = []
    data.dataList.forEach((item: any, index) => {
      data1.push({
        id: item.id,
        step_sort: index,
      })
    })
    putUiPagePutStepSort(data1)
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
      value['type'] = data.type
      if (data.isAdd) {
        value['step_sort'] = data.dataList.length
        postUiPageStepsDetailed(value)
          .then((res) => {
            Message.success(res.msg)
            getUiRunSort()
          })
          .catch(console.log)
      } else {
        value['id'] = data.updateId
        putUiPageStepsDetailed(value)
          .then((res) => {
            Message.success(res.msg)
            getUiRunSort()
          })
          .catch(console.log)
      }
    }
  }

  function doResetSearch() {
    window.history.back()
  }

  function getUiRunSort() {
    getUiPageStepsDetailed(route.query.id)
      .then((res) => {
        data.dataList = res.data
      })
      .catch(console.log)
  }

  function getUiRunSortAss() {
    getUiPageStepsDetailedAss(route.query.pageType)
      .then((res) => {
        data.ass = res.data
      })
      .catch(console.log)
  }

  function getUiRunSortOpe() {
    getUiPageStepsDetailedOpe(route.query.pageType)
      .then((res) => {
        data.ope = res.data
      })
      .catch(console.log)
  }

  function getEleName() {
    getUiUiElementName(route.query.pageId)
      .then((res) => {
        data.uiPageName = res.data
      })
      .catch(console.log)
  }

  function upDataAssValue(value: any) {
    const inputItem = findItemByValue(data.ass, value)
    if (inputItem) {
      const parameter: any = inputItem.parameter
      Object.keys(parameter).forEach((key) => {
        parameter[key] = ''
      })
      if (!formItems.some((item) => item.key === 'ass_value')) {
        formItems.push({
          label: '断言值',
          key: 'ass_value',
          value: JSON.stringify(parameter),
          type: 'textarea',
          required: true,
          placeholder: '请输入断言内容',
          validator: function () {
            if (this.value !== '') {
              try {
                this.value = JSON.parse(this.value)
              } catch (e) {
                Message.error(this.placeholder || '')
                return false
              }
            }
            return true
          },
        })
      }
    }
  }

  function upDataOpeValue(value: any) {
    const inputItem = findItemByValue(data.ope, value)
    if (inputItem) {
      const parameter: any = inputItem.parameter
      Object.keys(parameter).forEach((key) => {
        parameter[key] = ''
      })
      if (!formItems.some((item) => item.key === 'ope_value')) {
        formItems.push({
          label: '元素操作值',
          key: 'ope_value',
          value: JSON.stringify(parameter),
          type: 'textarea',
          required: true,
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
        })
      }
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

  function onRunCase() {
    if (testObj.selectValue == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    getUiStepsRun(route.query.id, testObj.selectValue)
      .then((res) => {
        Message.loading(res.msg)
      })
      .catch(console.log)
  }

  function enumUiElementOperation() {
    getSystemEnumUiElementOperation()
      .then((res) => {
        data.plainOptions = res.data
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      await getUiRunSortAss()
      await getUiRunSortOpe()
      await getEleName()
      getUiRunSort()
      enumUiElementOperation()
    })
  })
</script>
