<template>
  <TableBody ref="tableBody">
    <template #header>
      <a-card title="用例详情" :bordered="false">
        <template #extra>
          <a-space>
            <a-button type="primary" size="small" @click="doRefresh" disabled>刷新页面</a-button>
            <a-button status="success" size="small" @click="onCaseRun">执行</a-button>
            <a-button status="danger" size="small" @click="doResetSearch">返回</a-button>
          </a-space>
        </template>
        <div class="container">
          <a-space direction="vertical" style="width: 25%">
            <span>所属项目：{{ pageData.record.project_product?.project?.name }}</span>
            <span>顶级模块：{{ pageData.record.module?.superior_module }}</span>
            <span>所属模块：{{ pageData.record.module?.name }}</span>
            <span>用例负责人：{{ pageData.record.case_people?.name }}</span>
          </a-space>
          <a-space direction="vertical" style="width: 25%">
            <span>用例ID：{{ pageData.record.id }}</span>
            <span>用例名称：{{ pageData.record.name }}</span>
            <span
              >测试结果：{{
                pageData.record.status === 1
                  ? '通过'
                  : pageData.record.status === 0
                  ? '失败'
                  : '未测试'
              }}</span
            >
          </a-space>
          <a-space direction="vertical" style="width: 50%">
            <span>用例执行顺序：{{ pageData.record.case_flow }}</span>
          </a-space>
        </div>
      </a-card>
    </template>
    <template #default>
      <a-card :bordered="false">
        <div class="box">
          <div class="left">
            <a-tabs default-active-key="2" @tab-click="(key) => switchType(key)">
              <template #extra>
                <a-space>
                  <a-button type="primary" size="small" @click="addData">增加</a-button>
                </a-space>
              </template>
              <a-tab-pane key="1" title="前置数据">
                <a-tabs
                  :default-active-key="data.uiSonType"
                  @tab-click="(key) => switchSonType(key)"
                  position="left"
                >
                  <a-tab-pane key="11" title="自定义变量">
                    <a-space direction="vertical">
                      <a-space
                        v-for="(item, index) of pageData.record.front_custom"
                        :key="item.key"
                      >
                        <span>key</span>
                        <a-input
                          v-model="item.key"
                          placeholder="请输入key的名称"
                          @blur="upDataCase"
                        />
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
                          @click="removeFrontSql(pageData.record.front_custom, index)"
                          >移除
                        </a-button>
                      </a-space>
                    </a-space>
                  </a-tab-pane>
                  <a-tab-pane key="12" title="sql变量">
                    <a-space direction="vertical">
                      <a-space v-for="(item, index) of pageData.record.front_sql" :key="item.sql">
                        <span>sql语句</span>
                        <a-input
                          v-model="item.sql"
                          placeholder="请输入sql语句"
                          @blur="upDataCase"
                        />
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
                          @click="removeFrontSql(pageData.record.front_sql, index)"
                          >移除
                        </a-button>
                      </a-space>
                    </a-space>
                  </a-tab-pane>
                </a-tabs>
              </a-tab-pane>

              <a-tab-pane key="2" title="用例步骤">
                <a-table
                  :columns="columns"
                  :data="data.data"
                  @change="handleChange"
                  :draggable="{ type: 'handle', width: 40 }"
                  :pagination="false"
                  @row-click="select"
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
                      <template v-if="item.dataIndex === 'page_step_name'" #cell="{ record }">
                        {{ record.page_step?.name }}
                      </template>
                      <template v-else-if="item.dataIndex === 'status'" #cell="{ record }">
                        <a-tag :color="enumStore.status_colors[record.status]" size="small"
                          >{{ enumStore.task_status[record.status].title }}
                        </a-tag>
                      </template>
                      <template v-else-if="item.dataIndex === 'actions'" #cell="{ record }">
                        <a-button type="text" size="mini" @click="onPageStep(record)"
                          >单步执行
                        </a-button>
                        <a-button type="text" size="mini" @click="oeFreshSteps(record)"
                          >更新数据
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
                  :default-active-key="data.uiSonType"
                  @tab-click="(key) => switchSonType(key)"
                  position="left"
                >
                  <a-tab-pane key="31" title="sql清除">
                    <a-space direction="vertical">
                      <a-space
                        v-for="(item, index) of pageData.record.posterior_sql"
                        :key="item.sql"
                      >
                        <span>sql语句</span>
                        <a-input
                          v-model="item.sql"
                          placeholder="请输入sql语句"
                          @blur="upDataCase"
                        />
                        <a-button
                          type="text"
                          size="small"
                          status="danger"
                          @click="removeFrontSql(pageData.record.posterior_sql, index)"
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
            <a-tabs default-active-key="1">
              <a-tab-pane key="1" title="步骤数据">
                <a-list :bordered="false">
                  <template #header> {{ data.selectData?.page_step?.name }}</template>
                  <a-list-item
                    v-for="item of data.selectData?.case_data"
                    :key="item.page_step_details_id"
                    style="padding: 4px 20px"
                  >
                    <div style="display: flex; flex-direction: column">
                      <div style="display: flex; margin-bottom: 2px; margin-top: 2px">
                        <a-space style="width: 40%">
                          <span v-if="item.page_step_details_name">元素名称：</span>
                          <span v-if="item.page_step_details_name">{{
                            item.page_step_details_name
                          }}</span>
                        </a-space>
                        <a-space style="width: 30%">
                          <span v-if="item.type === 0"
                            >类型：操作->{{ getLabelByValue(data.ope, item.ope_key) }}</span
                          >
                          <span v-if="item.type === 1"
                            >类型：断言->{{ getLabelByValue(data.ass, item.ope_key) }}</span
                          >
                          <span v-if="item.type === 2">类型：SQL</span>
                          <span v-if="item.type === 3">类型：自定义参数</span>
                        </a-space>
                      </div>
                      <a-space direction="vertical" style="margin-bottom: 2px; margin-top: 2px">
                        <template
                          v-for="key in Object.keys(item.page_step_details_data)"
                          :key="key"
                        >
                          <div style="display: flex; align-items: center; margin-bottom: 12px">
                            <span
                              style="
                                width: 120px;
                                flex-shrink: 0;
                                font-size: 14px;
                                color: #333;
                                font-weight: 500;
                              "
                            >
                              {{ key + '：' }}
                            </span>
                            <a-textarea
                              v-model="item.page_step_details_data[key]"
                              @blur="onUpdate"
                              :auto-size="{ minRows: 1, maxRows: 5 }"
                              style="flex: 1; margin-left: 12px"
                            />
                          </div>
                        </template>
                      </a-space>
                    </div>
                  </a-list-item>
                </a-list>
              </a-tab-pane>
              <a-tab-pane key="2" title="测试结果">
                <ElementTestReport :result-data="data.selectData.result_data" />
              </a-tab-pane>
            </a-tabs>
          </div>
        </div>
      </a-card>
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
          <template v-if="item.type === 'cascader' && item.key === 'module'">
            <a-cascader
              v-model="item.value"
              @change="doUiPageNameAll(item.value)"
              :placeholder="item.placeholder"
              :options="data.productModuleName"
              allow-search
              allow-clear
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'page'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="data.pageName"
              :field-names="fieldNames"
              @change="doUiStepsPageStepsName(item.value)"
              value-key="key"
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'page_step'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="data.pageStepsName"
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
  import { nextTick, onMounted, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'

  import { ModalDialogType } from '@/types/components'
  import { useRoute } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import ModalDialog from '@/components/ModalDialog.vue'
  import { usePageData } from '@/store/page-data'
  import { columns, formItems } from './config'
  import {
    deleteUiCaseStepsDetailed,
    getUiCaseStepsDetailed,
    getUiCaseStepsRefreshCacheData,
    postUiCaseStepsDetailed,
    putUiCasePutCaseSort,
    putUiCaseStepsDetailed,
  } from '@/api/uitest/case-steps-detailed'
  import { getUserProductAllModuleName } from '@/api/system/product'
  import { getUiCaseRun, putUiCase } from '@/api/uitest/case'
  import { getUiStepsPageStepsName, getUiStepsTest } from '@/api/uitest/page-steps'
  import { getUiPageName } from '@/api/uitest/page'
  import useUserStore from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import ElementTestReport from '@/components/ElementTestReport.vue'
  import {
    getUiPageStepsDetailedAss,
    getUiPageStepsDetailedOpe,
  } from '@/api/uitest/page-steps-detailed'

  const userStore = useUserStore()
  const enumStore = useEnum()

  const pageData: any = usePageData()
  const route = useRoute()
  const formModel = ref({})
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const data: any = reactive({
    productModuleName: [],
    pageName: [],
    pageStepsName: [],
    data: [],
    selectData: {},
    actionTitle: '添加用例步骤',
    uiType: '2',
    uiSonType: '11',
    ass: [],
    ope: [],
  })

  function switchType(key: any) {
    if (key === '1') {
      data.uiSonType = '11'
    } else if (key === '3') {
      data.uiSonType = '31'
    }
    data.uiType = key
  }

  function switchSonType(key: any) {
    data.uiSonType = key
  }

  function addData() {
    if (data.uiType == '2') {
      doAppend()
      return
    }
    if (data.uiSonType === '11') {
      pageData.record.front_custom.push({ key: '', value: '' })
    } else if (data.uiSonType === '12') {
      pageData.record.front_sql.push({ sql: '', key_list: '' })
    } else if (data.uiSonType === '31') {
      pageData.record.posterior_sql.push({ sql: '' })
    }
  }

  function removeFrontSql(item: any, index: number) {
    item.splice(index, 1)
    upDataCase()
  }

  function upDataCase() {
    putUiCase({
      id: pageData.record.id,
      name: pageData.record.name,
      posterior_sql: pageData.record.posterior_sql,
      front_sql: pageData.record.front_sql,
      front_custom: pageData.record.front_custom,
    })
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function doAppend() {
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
      content: '是否要删除此步骤？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteUiCaseStepsDetailed(record.id, record.case.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  const handleChange = (_data: any) => {
    data.data = _data
    let data1: any = []
    data.data.forEach((item: any, index: number) => {
      data1.push({
        id: item.id,
        case_sort: index,
      })
    })
    putUiCasePutCaseSort(data1)
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  function onDataForm() {
    if (formItems.every((it: any) => (it.validator ? it.validator() : true))) {
      modalDialogRef.value?.toggle()
      let value = getFormItems(formItems)
      value['case'] = route.query.id
      value['case_cache_data'] = []
      value['case_cache_ass'] = []
      value['case_sort'] = data.data.length
      postUiCaseStepsDetailed(value, route.query.id)
        .then((res) => {
          Message.success(res.msg)
          getUiCaseStepsRefreshCacheData(res.data.id)
            .then((res) => {
              Message.success(res.msg)
              doRefresh()
            })
            .catch(console.log)
        })
        .catch(console.log)
    }
  }

  function doResetSearch() {
    window.history.back()
  }

  function doRefresh() {
    getUiCaseStepsDetailed(route.query.id)
      .then((res) => {
        data.data = res.data
        if (res.data) {
          data.selectData = res.data[0]
        }
      })
      .catch(console.log)
  }

  function oeFreshSteps(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否确实要刷新这个用例的步骤数据？刷新会导致丢失原始数据，请先保存原始数据！',
      cancelText: '取消',
      okText: '刷新',
      onOk: () => {
        getUiCaseStepsRefreshCacheData(record.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function onProductModuleName() {
    getUserProductAllModuleName(pageData.record.project_product?.project?.id)
      .then((res) => {
        data.productModuleName = res.data
      })
      .catch(console.log)
  }

  function doUiPageNameAll(moduleId: number) {
    getUiPageName(moduleId)
      .then((res) => {
        data.pageName = res.data
      })
      .catch(console.log)
  }

  function doUiStepsPageStepsName(pageId: number) {
    getUiStepsPageStepsName(pageId)
      .then((res) => {
        data.pageStepsName = res.data
      })
      .catch(console.log)
  }

  function onCaseRun() {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    getUiCaseRun(route.query.id, userStore.selected_environment)
      .then((res) => {
        Message.loading(res.msg)
      })
      .catch(console.log)
  }

  function select(record: any) {
    data.selectData = record
  }

  function onUpdate() {
    putUiCaseStepsDetailed(
      {
        id: data.selectData.id,
        case_data: data.selectData.case_data,
      },
      route.query.id
    )
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  function onPageStep(record: any) {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    getUiStepsTest(record.page_step.id, userStore.selected_environment)
      .then((res) => {
        Message.loading(res.msg)
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

  function getUiRunSortAss() {
    getUiPageStepsDetailedAss(null)
      .then((res) => {
        data.ass = res.data
      })
      .catch(console.log)
  }

  function getUiRunSortOpe() {
    getUiPageStepsDetailedOpe(null)
      .then((res) => {
        data.ope = res.data
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      onProductModuleName()
      getUiRunSortAss()
      getUiRunSortOpe()
    })
  })
</script>

<style>
  .container {
    display: flex;
  }

  .box {
    width: 100%;
    margin: 0 auto;
    padding: 5px;
    box-sizing: border-box;
    display: flex;
  }

  .left {
    flex: 5;
    padding: 5px;
  }

  .right {
    flex: 5;
    padding: 5px;
    max-width: 60%;
  }
</style>
