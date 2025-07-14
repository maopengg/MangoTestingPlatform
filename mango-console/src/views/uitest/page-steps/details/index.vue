<template>
  <TableBody ref="tableBody">
    <template #header>
      <a-card :bordered="false" style="border-radius: 10px; overflow: hidden" title="页面步骤详情">
        <template #extra>
          <a-space>
            <a-button size="small" type="primary" @click="doAppend">增加</a-button>
            <a-button size="small" status="success" :loading="caseRunning" @click="onRunCase"
              >调试</a-button
            >
            <a-button size="small" status="danger" @click="doResetSearch">返回</a-button>
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
          <a-card :bordered="false" style="border-radius: 10px; overflow: hidden">
            <a-table
              :bordered="false"
              :columns="columns"
              :data="data.dataList"
              :draggable="{ type: 'handle', width: 40 }"
              :pagination="false"
              @change="handleChange"
            >
              <template #columns>
                <a-table-column
                  v-for="item of columns"
                  :key="item.key"
                  :align="item.align"
                  :data-index="item.dataIndex"
                  :ellipsis="item.ellipsis"
                  :fixed="item.fixed"
                  :title="item.title"
                  :tooltip="item.tooltip"
                  :width="item.width"
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
                        ? record.key_list
                        : record.key
                    }}
                  </template>
                  <template v-else-if="item.dataIndex === 'ope_value'" #cell="{ record }">
                    {{
                      (() => {
                        if (record.type === 0 || record.type === 1) {
                          const filteredData = Object.fromEntries(
                            record.ope_value
                              ?.filter((item) => item.d === true)
                              ?.map((item) => [item.f, item.v]) || []
                          )
                          return Object.keys(filteredData).length
                            ? JSON.stringify(filteredData)
                            : ''
                        }
                        return record.type === 2 ? record.sql : record.value
                      })()
                    }}
                  </template>

                  <template v-else-if="item.dataIndex === 'type'" #cell="{ record }">
                    <a-tag :color="enumStore.colors[record.type]" size="small"
                      >{{ enumStore.element_ope[record.type].title }}
                    </a-tag>
                  </template>
                  <template v-else-if="item.dataIndex === 'actions'" #cell="{ record }">
                    <a-button size="mini" type="text" :loading="caseRunning" @click="onTest(record)"
                      >调试</a-button
                    >
                    <a-button size="mini" type="text" @click="onUpdate(record)">编辑</a-button>
                    <a-button size="mini" status="danger" type="text" @click="onDelete(record)"
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
          v-for="item of formItems"
          :key="item.key"
          :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
          <template v-else-if="item.type === 'select' && item.label === '选择元素'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="data.uiPageName"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>

          <template v-else-if="item.type === 'cascader' && item.label === '元素操作'">
            <a-space direction="vertical">
              <a-cascader
                v-model="item.value"
                :default-value="item.value"
                :options="data.ope"
                :placeholder="item.placeholder"
                allow-clear
                allow-search
                expand-trigger="hover"
                style="width: 380px"
                value-key="key"
                @change="upDataOpeValue(data.ope, item.value)"
              />
            </a-space>
          </template>
          <template v-else-if="item.type === 'cascader' && item.label === '断言操作'">
            <a-space direction="vertical">
              <a-cascader
                v-model="item.value"
                :default-value="item.value"
                :options="data.ass"
                :placeholder="item.placeholder"
                allow-clear
                allow-search
                expand-trigger="hover"
                style="width: 380px"
                value-key="key"
                @change="upDataOpeValue(data.ass, item.value)"
              />
            </a-space>
          </template>
          <template
            v-else-if="item.type === 'textarea' && item.key !== 'key_list' && item.key !== 'sql'"
          >
            <a-textarea
              v-model="item.value"
              :auto-size="{ minRows: 4, maxRows: 7 }"
              :default-value="item.value"
              :placeholder="item.placeholder"
              allow-clear
            />
          </template>

          <template v-else-if="item.type === 'radio' && item.key === 'type'">
            <a-select
              v-model="data.type"
              :field-names="fieldNames"
              :options="enumStore.element_ope"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
              @change="changeStatus"
            />
          </template>
          <template v-else-if="item.type === 'textarea' && item.key === 'key_list'">
            <a-textarea
              v-model="item.value"
              :auto-size="{ minRows: 4, maxRows: 7 }"
              :default-value="item.value"
              :placeholder="item.placeholder"
              allow-clear
            />
          </template>

          <template v-else-if="item.type === 'textarea' && item.key === 'sql'">
            <a-textarea
              v-model="item.value"
              :auto-size="{ minRows: 4, maxRows: 7 }"
              :default-value="item.value"
              :placeholder="item.placeholder"
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
  import { columns, formItems } from './config'
  import {
    deleteUiPageStepsDetailed,
    getUiPageStepsDetailed,
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
  import { getSystemCacheDataKeyValue } from '@/api/system/cache_data'

  const enumStore = useEnum()

  const pageData = usePageData()
  const userStore = useUserStore()

  const route = useRoute()
  const formModel = ref({})
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const data: any = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
    dataList: [],
    uiPageName: [],
    type: 0,
    plainOptions: [],
    result_data: {},
    ass: [],
    ope: [],
    opeSelect: [],
  })
  const caseRunning = ref(false)

  function changeStatus(event: number, value: any = null) {
    data.type = event
    for (let i = formItems.length - 1; i >= 0; i--) {
      if (formItems[i].key !== 'type') {
        formItems.splice(i, 1)
      }
    }
    if (event === 0) {
      formItems.push({
        label: '元素操作',
        key: 'ope_key',
        value: value ? value : ref(''),
        type: 'cascader',
        required: true,
        placeholder: '请选择对元素的操作',
        validator: function () {
          if (!this.value && this.value !== 0) {
            Message.error(this.placeholder || '')
            return false
          }
          return true
        },
      })
    } else if (event === 1) {
      formItems.push({
        label: '断言操作',
        key: 'ope_key',
        value: value ? value : ref(''),
        type: 'cascader',
        required: true,
        placeholder: '请选择断言类型',
        validator: function () {
          if (!this.value && this.value !== 0) {
            Message.error(this.placeholder || '')
            return false
          }
          return true
        },
      })
    } else if (event === 2) {
      formItems.push(
        ...[
          {
            label: 'key_list',
            key: 'key_list',
            value: ref(''),
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
            value: ref(''),
            type: 'textarea',
            required: true,
            placeholder: '请输入sql',
            validator: function () {
              if (!this.value && this.value !== 0) {
                Message.error(this.placeholder || '')
                return false
              }
              return true
            },
          },
        ]
      )
    } else {
      formItems.push(
        ...[
          {
            label: 'key',
            key: 'key',
            value: ref(''),
            type: 'input',
            required: true,
            placeholder: '请输入key',
            validator: function () {
              if (!this.value && this.value !== 0) {
                Message.error(this.placeholder || '')
                return false
              }
              return true
            },
          },
          {
            label: 'value',
            key: 'value',
            value: ref(''),
            type: 'input',
            required: true,
            placeholder: '请输入value',
            validator: function () {
              if (!this.value && this.value !== 0) {
                Message.error(this.placeholder || '')
                return false
              }
              return true
            },
          },
        ]
      )
    }
  }

  function doAppend() {
    changeStatus(0)
    data.type = 0
    data.actionTitle = '新增'
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
    if (item.ope_key && item.type === 0) {
      upDataOpeValue(data.ope, item.ope_key)
    } else {
      upDataOpeValue(data.ass, item.ope_key)
    }
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it: any) => {
        let propName: any = item[it.key]
        if (it.key.includes('locating') || it.key.includes('actual')) {
          propName = item.ele_name
        } else if (it.key.includes('ope_value')) {
          if (item.ope_value) {
            item.ope_value.forEach((item1: any) => {
              if (item1.d && it.key.includes(it.key)) {
                propName = item1.v
              }
            })
          }
        } else if (typeof propName === 'undefined') {
          item.ope_value.forEach((item: any) => {
            if (item.f === it.key) {
              propName = item.v
            }
          })
        }
        if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
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
      const extractedValues = []
      for (const key in value) {
        if (key == 'locating' || key == 'actual') {
          value['ele_name'] = value[key]
          extractedValues.push({
            f: key,
            v: '',
            d: false,
          })
          delete value[key]
        } else if (key.includes('-ope_value')) {
          const newKey = key.replace('-ope_value', '')
          if (newKey && data.type === 0) {
            findItemByValue(data.ope, value.ope_key).parameter.forEach((item: any) => {
              if (item.f === newKey) {
                extractedValues.push({
                  f: newKey,
                  v: value[key],
                  d: item.d,
                })
              }
            })
          } else if (newKey && data.type === 1) {
            findItemByValue(data.ass, value.ope_key).parameter.forEach((item: any) => {
              if (item.f === newKey) {
                extractedValues.push({
                  f: newKey,
                  v: value[key],
                  d: item.d,
                })
              }
            })
          }
          delete value[key]
        }
      }
      value['ope_value'] = extractedValues

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

  function upDataOpeValue(selectData: any, value: any) {
    changeStatus(data.type, value)
    const inputItem = findItemByValue(selectData, value)
    if (inputItem && inputItem.parameter) {
      inputItem.parameter.forEach((select: any) => {
        if (
          (select.f === 'actual' || select.f === 'locating') &&
          !formItems.some((item) => item.key === select.f)
        ) {
          formItems.push({
            label: '选择元素',
            key: select.f,
            value: ref(''),
            placeholder: '请选择一个元素',
            required: true,
            type: 'select',
            validator: function () {
              if (!this.value && this.value !== 0) {
                Message.error(this.placeholder || '')
                return false
              }
              return true
            },
          })
        } else if (select.d === true && !formItems.some((item) => item.key === select.f)) {
          formItems.push({
            label: select.f,
            key: `${select.f}-ope_value`,
            value: select.v,
            type: 'textarea',
            required: true,
            placeholder: select.p,
            validator: function () {
              if (!this.value && this.value !== 0) {
                Message.error(this.placeholder || '')
                return false
              }
              return true
            },
          })
        }
      })
    }
  }

  function findItemByValue(data: any, value: string) {
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
  const onRunCase = async () => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (caseRunning.value) return
    caseRunning.value = true
    try {
      const res = await getUiStepsTest(route.query.id, userStore.selected_environment)
      Message.loading(res.msg)
      doRefresh()
    } catch (e) {
    } finally {
      caseRunning.value = false
    }
  }
  const onTest = async (record) => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (caseRunning.value) return
    caseRunning.value = true
    try {
      const res = await getUiPageStepsDetailedTest(record.id, userStore.selected_environment)
      Message.loading(res.msg)
      doRefresh()
    } catch (e) {
    } finally {
      caseRunning.value = false
    }
  }

  function doRefreshSteps(pageStepsId: any) {
    getUiSteps({ id: pageStepsId })
      .then((res) => {
        data.result_data = res.data[0].result_data
      })
      .catch(console.log)
  }

  function getUiRunSortOpe() {
    getSystemCacheDataKeyValue('select_value')
      .then((res) => {
        res.data.forEach((item: any) => {
          if (item.value === 'web') {
            if (route.query.pageType === '0') {
              data.ope.push(...item.children)
            }
          } else if (item.value === 'android') {
            if (route.query.pageType === '1') {
              data.ope.push(...item.children)
            }
          } else if (item.value === 'ass_android') {
            if (route.query.pageType === '1') {
              data.ass.unshift(...item.children)
            }
          } else if (item.value === 'ass_web') {
            if (route.query.pageType === '0') {
              data.ass.unshift(...item.children)
            }
          } else if (item.value.includes('断言')) {
            data.ass.push(item)
          }
        })
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
    getUiRunSortOpe()
  })
</script>
<style scoped>
  .container .a-space span {
    font-size: 14px !important;
    display: block;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
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
