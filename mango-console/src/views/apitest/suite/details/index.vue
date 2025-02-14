<template>
  <a-card title="组合用例场景">
    <template #extra>
      <a-space>
        <a-button type="primary" status="warning" size="small" @click="doResetSearch"
          >返回
        </a-button>
      </a-space>
    </template>
    <div class="container">
      <div class="left">
        <a-tabs :active-key="data.apiType" @tab-click="(key) => switchType(key)">
          <template #extra>
            <a-space>
              <a-button status="success" size="small" @click="caseRun(null)">全部执行</a-button>
              <a-button type="primary" size="small" @click="addData">增加</a-button>
            </a-space>
          </template>
          <a-tab-pane key="1" title="前置数据">
            <a-tabs
              :default-active-key="data.apiSonType"
              @tab-click="(key) => switchSonType(key)"
              position="left"
            >
              <a-tab-pane key="11" title="自定义变量">
                <a-space direction="vertical">
                  <a-space v-for="(item, index) of pageData.record.front_custom" :key="item.key">
                    <span>key</span>
                    <a-input v-model="item.key" placeholder="请输入key的名称" @blur="upDataCase" />
                    <span>value</span>
                    <a-input
                      v-model="item.value"
                      placeholder="请输入value的名称"
                      @blur="upDataCase"
                    />
                    <a-button
                      type="text"
                      size="small"
                      status="danger"
                      @click="removeFrontSql1(pageData.record.front_custom, index)"
                      >移除
                    </a-button>
                  </a-space>
                </a-space>
              </a-tab-pane>
              <a-tab-pane key="12" title="sql变量">
                <a-space direction="vertical">
                  <a-space v-for="(item, index) of pageData.record.front_sql" :key="item.sql">
                    <span>sql语句</span>
                    <a-input v-model="item.sql" placeholder="请输入sql语句" @blur="upDataCase" />
                    <span>key列表</span>
                    <a-input
                      v-model="item.key_list"
                      placeholder="请输入查询结果缓存key"
                      @blur="upDataCase"
                    />
                    <a-button
                      type="text"
                      size="small"
                      status="danger"
                      @click="removeFrontSql1(pageData.record.front_sql, index)"
                      >移除
                    </a-button>
                  </a-space>
                </a-space>
              </a-tab-pane>
            </a-tabs>
          </a-tab-pane>
          <a-tab-pane key="4" title="参数化List">
            <a-textarea
              placeholder='请输入[[{"key":"value"}],[{"key":"value"}]]格式的数据，list中的每个列表都会执行一次测试套'
              v-model="data.file"
              allow-clear
              :auto-size="{ minRows: 10, maxRows: 50 }"
              @blur="upDataCase"
            />
          </a-tab-pane>
          <a-tab-pane key="2" title="套件步骤">
            <a-table
              :columns="columns"
              :data="data.data"
              :draggable="{ type: 'handle', width: 40 }"
              :pagination="false"
              :bordered="true"
              @row-click="select"
              @change="handleChange"
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
                  <template v-if="item.dataIndex === 'name'" #cell="{ record }">
                    {{ record.api_info.name }}
                  </template>
                  <template v-else-if="item.dataIndex === 'method'" #cell="{ record }">
                    <a-tag :color="enumStore.colors[record.api_info.method]" size="small">{{
                      enumStore.method[record.api_info.method].title
                    }}</a-tag>
                  </template>
                  <template v-else-if="item.dataIndex === 'status'" #cell="{ record }">
                    <a-tag :color="enumStore.status_colors[record.status]" size="small">{{
                      enumStore.task_status[record.status].title
                    }}</a-tag>
                  </template>
                  <template v-else-if="item.dataIndex === 'actions'" #cell="{ record }">
                    <a-button type="text" size="mini" @click="caseRun(record.case_sort)"
                      >执行到此处
                    </a-button>
                    <a-button status="danger" type="text" size="mini" @click="onDelete(record)"
                      >删除
                    </a-button>
                  </template>
                </a-table-column>
              </template>
            </a-table>
          </a-tab-pane>
          <a-tab-pane key="3" title="后置清除">
            <a-tabs
              :default-active-key="data.apiSonType"
              @tab-click="(key) => switchSonType(key)"
              position="left"
            >
              <a-tab-pane key="31" title="sql清除">
                <a-space direction="vertical">
                  <a-space v-for="(item, index) of pageData.record.posterior_sql" :key="item.sql">
                    <span>sql语句</span>
                    <a-input v-model="item.sql" placeholder="请输入sql语句" @blur="upDataCase" />
                    <a-button
                      type="text"
                      size="small"
                      status="danger"
                      @click="removeFrontSql1(pageData.record.posterior_sql, index)"
                      >移除
                    </a-button>
                  </a-space>
                </a-space>
              </a-tab-pane>
            </a-tabs>
          </a-tab-pane>
        </a-tabs>
      </div>
      <div class="right">
        <a-space>
          <span>嘿嘿</span>
        </a-space>
      </div>
    </div>
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
          <template v-else-if="item.type === 'cascader' && item.key === 'module'">
            <a-cascader
              v-model="item.value"
              @change="getModuleCase(item.value)"
              :placeholder="item.placeholder"
              :options="data.productModuleName"
              allow-search
              allow-clear
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'case'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="data.apiCaseList"
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
</template>

<script lang="ts" setup>
  import { reactive, nextTick, onMounted, ref } from 'vue'
  import { useRoute } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'
  import { ModalDialogType } from '@/types/components'
  import { fieldNames } from '@/setting'
  import { Message, Modal } from '@arco-design/web-vue'
  import { usePageData } from '@/store/page-data'
  import { formatJson, formatJsonObj, strJson } from '@/utils/tools'
  import { formItems, columns } from './config'
  import { putApiCase, getApiCaseRun, getApiCaseName } from '@/api/apitest/case'
  import {
    getApiCaseSuiteDetailed,
    putApiCaseSuiteDetailed,
    deleteApiCaseSuiteDetailed,
    postApiCaseSuiteDetailed,
    putApiPutCaseSuiteSort,
  } from '@/api/apitest/case-suite-detailed'
  import { getApiInfoName } from '@/api/apitest/info'
  import { getUserProductAllModuleName } from '@/api/system/product'
  import useUserStore from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'

  const userStore = useUserStore()

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const formModel = ref({})
  const pageData: any = usePageData()
  const enumStore = useEnum()

  const route = useRoute()
  const data: any = reactive({
    actionTitle: '新增用例步骤',
    request: {
      headers: null,
      params: null,
      data: null,
      json: null,
      file: null,
    },
    result_data: {},
    selectDataObj: {},
    data: [],
    productModuleName: [],
    apiCaseList: [],
    ass: [],
    caseHeadersList: [],
    caseDetailsHeadersList: [],
    apiType: '2',
    apiSonType: '0',
    caseDetailsTypeKey: '0',
    tabsKey: '10',
  })

  function switchType(key: any) {
    if (key === '1') {
      data.apiSonType = '11'
    } else if (key === '3') {
      data.apiSonType = '31'
    }
    data.apiType = key
  }

  function switchApiInfoType(key: any) {
    data.caseDetailsTypeKey = key
    if (key === '0') {
      if (data.request.params) {
        data.tabsKey = '01'
      } else if (data.request.data) {
        data.tabsKey = '02'
      } else if (data.request.json) {
        data.tabsKey = '03'
      } else if (data.request.file) {
        data.tabsKey = '04'
      } else {
        data.tabsKey = '00'
      }
    } else if (key === '1') {
      data.tabsKey = '10'
    } else if (key === '2') {
      data.tabsKey = '23'
    } else if (key === '3') {
      data.tabsKey = '30'
    } else if (key === '4') {
      data.tabsKey = '40'
    } else if (key === '5') {
      console.log(key)
      data.tabsKey = '50'
    }
  }

  function switchSonType(key: any) {
    data.apiSonType = key
  }

  function addData() {
    if (data.apiType == '2') {
      addApiInfo()
      return
    }
    if (data.apiSonType === '11') {
      pageData.record.front_custom.push({ key: '', value: '' })
    } else if (data.apiSonType === '12') {
      pageData.record.front_sql.push({ sql: '', key_list: '' })
    } else if (data.apiSonType === '31') {
      pageData.record.posterior_sql.push({ sql: '' })
    }
  }

  function removeFrontSql1(item: any, index: number) {
    item.splice(index, 1)

    upDataCase()
  }

  function upDataCase() {
    putApiCase({
      id: pageData.record.id,
      name: pageData.record.name,
      posterior_sql: pageData.record.posterior_sql,
      front_sql: pageData.record.front_sql,
      front_custom: pageData.record.front_custom,
      front_headers: pageData.record.front_headers,
    })
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function doRefresh() {
    data.caseHeadersList = pageData.record.front_headers
    getApiCaseSuiteDetailed(route.query.case_id)
      .then((res) => {
        data.data = res.data
        if (res.data.length !== 0) {
          select(res.data[0])
        }
      })
      .catch(console.log)
  }

  function caseRun(case_sort: number | null) {
    Message.loading('用例开始执行中~')
    getApiCaseRun(route.query.case_id, userStore.selected_environment, case_sort)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function onProductModuleName() {
    getUserProductAllModuleName(pageData.record.project_product?.project?.id)
      .then((res) => {
        data.productModuleName = res.data
      })
      .catch(console.log)
  }

  function getModuleCase(moduleId: number) {
    getApiCaseName(moduleId)
      .then((res) => {
        data.apiCaseList = res.data
      })
      .catch(console.log)
  }

  const handleChange = (_data: any) => {
    data.data = _data
    let data1: any = []
    data.data.forEach((item: any, index: any) => {
      data1.push({
        id: item.id,
        case_sort: index,
      })
    })
    putApiPutCaseSuiteSort(data1)
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      modalDialogRef.value?.toggle()
      let value = getFormItems(formItems)
      value['case'] = route.query.case_id
      value['case_sort'] = data.data.length
      value['front_sql'] = []
      value['ass_sql'] = []
      value['ass_response_value'] = []
      value['posterior_sql'] = []
      value['posterior_response'] = []
      postApiCaseSuiteDetailed(value, route.query.case_id)
        .then((res) => {
          Message.success(res.msg)
          doRefresh()
        })
        .catch(console.log)
    }
  }

  function onDelete(data: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此接口？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteApiCaseSuiteDetailed(data.id, route.query.case_id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function addApiInfo() {
    data.actionTitle = '添加接口到用例'
    modalDialogRef.value?.toggle()
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = ''
      }
    })
  }

  function doResetSearch() {
    window.history.back()
  }

  function select(record: any) {
    data.selectDataObj = record
    console.log(data.selectDataObj)
    data.result_data = record.result_data

    data.request.header = record.header
    data.request.data = formatJson(record.data)
    data.request.params = formatJson(record.params)
    data.request.json = formatJson(record.json)
    data.request.file = formatJson(record.file)
    switchApiInfoType(data.caseDetailsTypeKey)
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      onProductModuleName()
    })
  })
</script>

<style>
  .container {
    display: flex; /* 开启flex布局 */
  }

  .left {
    width: 40%; /* 左边区域占据50%的宽度 */
    margin-right: 10px; /* 设置左边盒子的右边距 */
  }

  .right {
    width: 60%; /* 右边区域占据50%的宽度 */
    margin-left: 10px; /* 设置右边盒子的左边距 */
  }
</style>
