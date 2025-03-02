<template>
  <TableBody ref="tableBody">
    <template #header>
      <a-card title="页面步骤详情" style="border-radius: 10px; overflow: hidden" :bordered="false">
        <template #extra>
          <a-space>
            <a-button type="primary" size="small" @click="doAppend">增加</a-button>
            <a-button status="success" size="small" @click="onRunCase">调试</a-button>
            <a-button status="danger" size="small" @click="doResetSearch">返回</a-button>
          </a-space>
        </template>
        <div class="container">
          <a-space direction="vertical" style="width: 25%">
            <span>所属项目：{{ pageData.record.project_product?.project?.name }}</span>
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
    </template>
    <template #default>
      <div class="box">
        <div class="left">
          <a-card style="border-radius: 10px; overflow: hidden" :bordered="false">
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
                    {{ record.page_step?.name }}
                  </template>
                  <template v-else-if="item.dataIndex === 'ele_name'" #cell="{ record }">
                    {{ record.ele_name ? record.ele_name.name : '-' }}
                  </template>
                  <template v-else-if="item.dataIndex === 'ope_key'" #cell="{ record }">
                    {{
                      record.type === 0
                        ? getLabelByValue(data.ope, record.ope_key)
                        : record.type === 1
                        ? getLabelByValue(data.ass, record.ope_key)
                        : record.type === 2
                        ? record.key
                        : record.key_list
                    }}
                  </template>
                  <template v-else-if="item.dataIndex === 'ope_value'" #cell="{ record }">
                    {{
                      record.ope_value ? record.ope_value : record.value ? record.value : record.sql
                    }}
                  </template>

                  <template v-else-if="item.dataIndex === 'type'" #cell="{ record }">
                    <a-tag :color="enumStore.colors[record.type]" size="small"
                      >{{ enumStore.element_ope[record.type].title }}
                    </a-tag>
                  </template>
                  <template v-else-if="item.dataIndex === 'actions'" #cell="{ record }">
                    <a-button type="text" size="mini" @click="onTest(record)">调试</a-button>
                    <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
                    <a-button status="danger" type="text" size="mini" @click="onDelete(record)"
                      >删除
                    </a-button>
                  </template>
                </a-table-column>
              </template>
            </a-table>
          </a-card>
        </div>
        <div class="right">
          <ElementTestReport :result-data="data.result_data" />
        </div>
      </div>
    </template>
  </TableBody>
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

          <template v-else-if="item.type === 'cascader' && item.label === '元素操作'">
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
          <template v-else-if="item.type === 'cascader' && item.label === '断言操作'">
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

          <template v-else-if="item.type === 'radio' && item.key === 'type'">
            <a-select
              v-model="data.type"
              :placeholder="item.placeholder"
              :options="enumStore.element_ope"
              :field-names="fieldNames"
              @change="changeStatus"
              value-key="key"
              allow-clear
              allow-search
            />
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
</template>
<script lang="ts" setup>
  import { nextTick, onMounted, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'

  import { ModalDialogType } from '@/types/components'
  import { useRoute } from 'vue-router'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { usePageData } from '@/store/page-data'
  import { assForm, columns, customForm, eleForm, formItems, Item, sqlForm } from './config'
  import {
    deleteUiPageStepsDetailed,
    getUiPageStepsDetailed,
    getUiPageStepsDetailedAss,
    getUiPageStepsDetailedOpe,
    getUiPageStepsDetailedTest,
    postUiPageStepsDetailed,
    putUiPagePutStepSort,
    putUiPageStepsDetailed,
  } from '@/api/uitest/page-steps-detailed'
  import { getUiSteps, getUiStepsTest } from '@/api/uitest/page-steps'
  import { getUiUiElementName } from '@/api/uitest/element'
  import useUserStore from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import ElementTestReport from '@/components/ElementTestReport.vue'

  const enumStore = useEnum()

  const pageData = usePageData()
  const userStore = useUserStore()

  const route = useRoute()
  const formModel = ref({})
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const data: any = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '添加测试对象',
    dataList: [],
    uiPageName: [],
    type: 0,
    plainOptions: [],
    result_data: {},
    ass: [],
    ope: [],
  })

  function changeStatus(event: number) {
    data.type = event
    for (let i = formItems.length - 1; i >= 0; i--) {
      if (formItems[i].key !== 'type') {
        formItems.splice(i, 1)
      }
    }
    if (event === 0) {
      if (
        !formItems.some(
          (item) =>
            item.key === 'ele_name' ||
            formItems.some((item) => item.key === 'ope_key' && item.label == '元素操作')
        )
      ) {
        formItems.push(...eleForm)
      }
    } else if (event === 1) {
      if (!formItems.some((item) => item.key === 'ope_key' && item.label == '断言操作')) {
        formItems.push(...assForm)
      }
    } else if (event === 2) {
      if (
        !formItems.some((item) => item.key === 'sql') ||
        !formItems.some((item) => item.key === 'key_list')
      ) {
        formItems.push(...sqlForm)
      }
    } else {
      if (
        !formItems.some((item) => item.key === 'key') ||
        !formItems.some((item) => item.key === 'value')
      ) {
        formItems.push(...customForm)
      }
    }
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
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function onUpdate(item: any) {
    data.type = item.type
    changeStatus(item.type)
    if (item.ope_key && item.type === 0) {
      upDataOpeValue(item.ope_key)
    }

    if (item.ope_key && item.type === 1) {
      upDataAssValue(item.ope_key)
    }
    data.actionTitle = '编辑详细步骤'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it: any) => {
        const propName = item[it.key]
        if (typeof propName === 'object' && propName !== null) {
          if (it.key === 'ope_value' || it.key === 'key_list') {
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
        postUiPageStepsDetailed(value, route.query.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      } else {
        value['id'] = data.updateId
        putUiPageStepsDetailed(value, route.query.id)
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
    getUiPageStepsDetailed(route.query.id)
      .then((res) => {
        data.dataList = res.data
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
      if (!formItems.some((item) => item.key === 'ope_value')) {
        formItems.push({
          label: '断言值',
          key: 'ope_value',
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
      } else {
        const existingItem = formItems.find((item: any) => item.key === 'ope_value')
        if (existingItem) {
          existingItem.value = JSON.stringify(parameter)
        }
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
      } else {
        const existingItem = formItems.find((item: any) => item.key === 'ope_value')
        if (existingItem) {
          existingItem.value = JSON.stringify(parameter)
        }
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
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    getUiStepsTest(route.query.id, userStore.selected_environment)
      .then((res) => {
        Message.loading(res.msg)
      })
      .catch(console.log)
  }

  function onTest(record: any) {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    getUiPageStepsDetailedTest(record.id, userStore.selected_environment)
      .then((res) => {
        Message.loading(res.msg)
      })
      .catch(console.log)
  }

  function doRefreshSteps(pageStepsId: any) {
    getUiSteps({ id: pageStepsId })
      .then((res) => {
        data.result_data = res.data[0].result_data
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

  function getLabelByValue(opeData: any, value: string): string {
    const list = [...opeData]
    for (const item of list) {
      if (item.children) {
        list.push(...item.children)
      }
    }
    return list.find((item: any) => item.value === value)?.label
  }

  onMounted(() => {
    doRefresh()
    doRefreshSteps(pageData.record.id)
    getEleName()
    getUiRunSortAss()
    getUiRunSortOpe()
  })
</script>
<style>
  .container {
    display: grid;
    grid-template-columns: 60% 40%; /* 左侧60%，右侧40% */
    gap: 10px; /* 添加间距 */
  }

  .box {
    width: 100%;
    margin: 0 auto;
    padding: 5px;
    box-sizing: border-box;
    display: flex;
  }

  .left {
    flex: 6;
    padding: 5px;
  }

  .right {
    flex: 4;
    padding: 5px;
    max-width: 60%;
  }
</style>
