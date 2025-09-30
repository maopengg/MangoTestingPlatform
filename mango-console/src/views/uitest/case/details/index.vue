<template>
  <TableBody ref="tableBody">
    <template #header>
      <a-card :bordered="false" title="用例详情">
        <template #extra>
          <a-space>
            <a-button size="small" status="success" :loading="caseRunning" @click="onCaseRun"
              >执行
            </a-button>
            <a-button size="small" status="danger" @click="doResetSearch">返回</a-button>
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
            <span>测试结果：{{ enumStore.task_status[pageData.record.status].title }}</span>
          </a-space>
          <a-space direction="vertical" style="width: 50%">
            <span>用例执行顺序：{{ pageData.record.case_flow }}</span>
          </a-space>
        </div>
      </a-card>
    </template>
    <template #default>
      <a-card :bordered="false">
        <div class="main_box">
          <div class="left">
            <a-tabs default-active-key="2" @tab-click="(key) => switchType(key)">
              <template #extra>
                <a-space>
                  <div>
                    <a-button size="small" type="primary" @click="addSynchronous"
                      >全部同步
                    </a-button>
                  </div>
                  <div>
                    <a-button size="small" type="primary" @click="addData">增加步骤</a-button>
                  </div>
                </a-space>
              </template>
              <a-tab-pane key="1" title="前置数据">
                <a-tabs
                  :default-active-key="data.uiSonType"
                  position="left"
                  @tab-click="(key) => switchSonType(key)"
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
                          size="small"
                          status="danger"
                          type="text"
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
                          size="small"
                          status="danger"
                          type="text"
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
                  :key="tableKey"
                  :columns="columns"
                  :data="data.data"
                  :draggable="{ type: 'handle', width: 40 }"
                  :pagination="false"
                  @change="handleChange"
                  @row-click="select"
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
                      <template v-if="item.dataIndex === 'page_step_name'" #cell="{ record }">
                        {{ record.page_step?.name }}
                      </template>
                      <template v-else-if="item.dataIndex === 'status'" #cell="{ record }">
                        <a-tag :color="enumStore.status_colors[record.status]" size="small"
                          >{{ enumStore.task_status[record.status].title }}
                        </a-tag>
                      </template>
                      <template v-else-if="item.key === 'switch_step_open_url'" #cell="{ record }">
                        <a-switch
                          :beforeChange="
                            (newValue) => onModifyStatus(newValue, record.id, item.key)
                          "
                          :default-checked="record.switch_step_open_url === 1"
                        />
                      </template>
                      <template v-else-if="item.dataIndex === 'actions'" #cell="{ record }">
                        <a-button
                          size="mini"
                          type="text"
                          class="custom-mini-btn"
                          :loading="caseRunning"
                          @click="onPageStep(record)"
                          >单步执行
                        </a-button>
                        <a-dropdown trigger="hover">
                          <a-button size="mini" type="text">···</a-button>
                          <template #content>
                            <a-doption>
                              <a-button
                                size="mini"
                                type="text"
                                class="custom-mini-btn"
                                @click="oeFreshSteps(record)"
                                >同步数据
                              </a-button>
                            </a-doption>
                            <a-doption>
                              <a-button
                                size="mini"
                                type="text"
                                class="custom-mini-btn"
                                @click="onUpdate1(record)"
                                >编辑
                              </a-button>
                            </a-doption>
                            <a-doption>
                              <a-button
                                size="mini"
                                status="danger"
                                type="text"
                                class="custom-mini-btn"
                                @click="onDelete(record)"
                                >删除
                              </a-button>
                            </a-doption>
                          </template>
                        </a-dropdown>
                      </template>
                    </a-table-column>
                  </template>
                </a-table>
              </a-tab-pane>
              <a-tab-pane key="3" title="后置清除">
                <a-tabs
                  :default-active-key="data.uiSonType"
                  position="left"
                  @tab-click="(key) => switchSonType(key)"
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
                          size="small"
                          status="danger"
                          type="text"
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
              <a-tab-pane key="1" title="预估步骤执行顺序">
                <a-list :bordered="false" :split="false" class="step-execution-list">
                  <template #header>
                    <div class="step-header">{{ data.selectData?.page_step?.name }}</div>
                  </template>
                  <a-list-item
                    v-for="item of data.selectData?.case_data"
                    :key="item.page_step_details_id"
                    class="step-list-item"
                  >
                    <div class="step-container">
                      <!-- 步骤信息行 -->
                      <div class="step-info-row">
                        <div class="step-type">
                          <span>步骤类型：{{ enumStore.element_ope[item.type]?.title }}</span>
                        </div>
                        <div v-if="item.ope_key">
                          <span class="operation-label">执行方法：</span>
                          <span class="operation-value">{{
                            useSelectValue.findItemByValue(item.ope_key).label
                          }}</span>
                        </div>
                        <div class="step-element" v-if="item.page_step_details_name">
                          <span class="element-label">元素名称：</span>
                          <span class="element-value">{{ item.page_step_details_name }}</span>
                        </div>
                      </div>

                      <!-- 步骤详情数据 -->
                      <div class="step-details">
                        <template
                          v-for="item1 of item.page_step_details_data"
                          :key="item1.id || Math.random()"
                        >
                          <!-- 条件判断值 -->
                          <div v-if="item.condition_value" class="condition-input">
                            <span class="input-label">条件判断值：</span>
                            <a-textarea
                              v-model="item.condition_value.expect"
                              :auto-size="{ minRows: 1, maxRows: 5 }"
                              class="custom-textarea"
                              @blur="onUpdate"
                            />
                          </div>

                          <!-- 操作类型 (type === 0) -->
                          <template v-if="item.type === 0">
                            <div v-if="item1.d" class="operation-input">
                              <span class="input-label">{{ item1.n }}：</span>
                              <a-textarea
                                v-model="item1.v"
                                :auto-size="{ minRows: 1, maxRows: 5 }"
                                class="custom-textarea"
                                @blur="onUpdate"
                              />
                            </div>
                          </template>

                          <!-- 断言类型 (type === 1) -->
                          <template v-if="item.type === 1">
                            <div v-if="item1.f !== 'actual'" class="assertion-input">
                              <span class="input-label">{{ item1.n }}：</span>
                              <a-textarea
                                v-model="item1.v"
                                :auto-size="{ minRows: 1, maxRows: 5 }"
                                class="custom-textarea"
                                @blur="onUpdate"
                              />
                            </div>
                          </template>

                          <!-- 自定义参数类型 (type === 3) -->
                          <template v-else-if="item.type === 3">
                            <div class="custom-param-input">
                              <div class="param-row">
                                <span class="input-label">key：</span>
                                <a-textarea
                                  v-model="item1.key"
                                  :auto-size="{ minRows: 1, maxRows: 5 }"
                                  class="custom-textarea"
                                  @blur="onUpdate"
                                />
                              </div>
                              <div class="param-row">
                                <span class="input-label">value：</span>
                                <a-textarea
                                  v-model="item1.value"
                                  :auto-size="{ minRows: 1, maxRows: 5 }"
                                  class="custom-textarea"
                                  @blur="onUpdate"
                                />
                              </div>
                            </div>
                          </template>

                          <!-- SQL类型 (type === 2) -->
                          <template v-else-if="item.type === 2">
                            <div class="sql-input">
                              <div class="sql-row">
                                <span class="input-label">key_list：</span>
                                <a-textarea
                                  v-model="item1.key_list"
                                  :auto-size="{ minRows: 1, maxRows: 5 }"
                                  class="custom-textarea"
                                  @blur="onUpdate"
                                />
                              </div>
                              <div class="sql-row">
                                <span class="input-label">sql：</span>
                                <a-textarea
                                  v-model="item1.sql"
                                  :auto-size="{ minRows: 1, maxRows: 5 }"
                                  class="custom-textarea sql-textarea"
                                  @blur="onUpdate"
                                />
                              </div>
                            </div>
                          </template>

                          <!-- Python代码类型 (type === 5) -->
                          <template v-else-if="item.type === 5">
                            <div class="python-code">
                              <CodeEditor
                                v-model="item1.func"
                                placeholder="请输入python代码"
                                class="code-editor"
                              />
                              <a-button type="primary" class="save-btn" @click="onUpdate"
                                >保存
                              </a-button>
                            </div>
                          </template>

                          <!-- 条件判断类型 (type === 4) -->
                          <template v-else-if="item.type === 4">
                            <!-- 条件判断暂无内容 -->
                          </template>
                        </template>
                      </div>
                    </div>
                  </a-list-item>
                </a-list>
              </a-tab-pane>
              <a-tab-pane key="2" title="测试结果">
                <ElementTestReport :result-data="data.selectData?.result_data" />
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
          v-for="item of formItems"
          :key="item.key"
          :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
          <template v-else-if="item.type === 'cascader' && item.key === 'module'">
            <a-cascader
              v-model="item.value"
              :options="data.productModuleName"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              @change="doUiPageNameAll(item.value)"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'page'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="data.pageName"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
              @change="doUiStepsPageStepsName(item.value)"
            />
          </template>
          <template v-else-if="item.type === 'switch' && item.key === 'switch_step_open_url'">
            <a-switch v-model="item.value" :checked-value="1" :unchecked-value="0" />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'page_step'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="data.pageStepsName"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
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
  import { useSelectValueStore } from '@/store/modules/get-ope-value'
  import CodeEditor from '@/components/CodeEditor.vue'

  const userStore = useUserStore()
  const enumStore = useEnum()

  const pageData: any = usePageData()
  const route = useRoute()
  const formModel = ref({})
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const tableKey = ref(0)
  const data: any = reactive({
    isAdd: true,
    updateId: null,
    productModuleName: [],
    pageName: [],
    pageStepsName: [],
    data: [],
    selectData: {},
    actionTitle: '新增',
    uiType: '2',
    uiSonType: '11',
  })
  const useSelectValue = useSelectValueStore()

  const caseRunning = ref(false)

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
    data.isAdd = true

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
        tableKey.value++
      })
      .catch(console.log)
  }

  function onDataForm() {
    if (formItems.every((it: any) => (it.validator ? it.validator() : true))) {
      modalDialogRef.value?.toggle()
      let value = getFormItems(formItems)
      if (data.isAdd) {
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
      } else {
        value['id'] = data.updateId
        putUiCaseStepsDetailed(value, route.query.id)
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
      content: '是否确实从页面步骤详情中同步数据？点击确认后，原始数据会丢失！',
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

  function addSynchronous() {
    Modal.confirm({
      title: '提示',
      content: '是否确实从页面步骤详情中同步数据？点击确认后，原始数据会丢失！',
      cancelText: '取消',
      okText: '同步',
      onOk: () => {
        getUiCaseStepsRefreshCacheData(null, route.query.id)
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

  const onCaseRun = async () => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (caseRunning.value) return
    caseRunning.value = true
    try {
      const res = await getUiCaseRun(route.query.id, userStore.selected_environment)
      Message.loading(res.msg)
      doRefresh()
    } catch (e) {
    } finally {
      caseRunning.value = false
    }
  }

  function select(record: any) {
    data.selectData = record
  }

  function onUpdate1(item: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = item[it.key]
        if (it.key === 'module') {
          it.value = item.page_step.module
          doUiPageNameAll(item.page_step.module)
        } else if (it.key === 'page') {
          it.value = item.page_step.page
          doUiStepsPageStepsName(item.page_step.page)
        } else if (it.key === 'page_step') {
          it.value = item.page_step.id
        } else {
          it.value = propName
        }
      })
    })
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

  const onPageStep = async (record) => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (caseRunning.value) return
    caseRunning.value = true
    try {
      const res = await getUiStepsTest(record.page_step.id, userStore.selected_environment)
      Message.loading(res.msg)
    } catch (e) {
    } finally {
      caseRunning.value = false
    }
  }

  const onModifyStatus = async (newValue: any, id: number, key: string) => {
    let obj: any = {
      id: id,
    }
    if (key) {
      obj[key] = newValue ? 1 : 0
    }
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value: any = false
          await putUiCaseStepsDetailed(obj, route.query.id)
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
  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      onProductModuleName()
      useSelectValue.getSelectValue()
    })
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

  .main_box {
    width: 100%;
    margin: 0 auto;
    padding: 5px;
    box-sizing: border-box;
    display: flex;

    .left {
      padding: 5px;
      width: 50%;
    }

    .right {
      padding: 5px;
      width: 50%;
    }
  }

  /* 步骤执行列表样式 */
  .step-execution-list {
    .step-header {
      font-size: 16px;
      font-weight: 600;
      color: #1d2129;
    }
  }

  /* 强制覆盖 Arco Design 组件的边框样式 */
  .step-execution-list :deep(.arco-list-split .arco-list-header) {
    border-bottom: none !important;
  }

  .step-execution-list :deep(.arco-list-split .arco-list-item) {
    border-bottom: none !important;
  }

  /* 如果上面还不够，用更强的选择器 */
  :deep(.arco-list.arco-list-split .arco-list-header) {
    border-bottom: none !important;
  }

  :deep(.arco-list.arco-list-split .arco-list-item) {
    border-bottom: none !important;
  }

  .step-list-item {
    padding: 8px 8px !important;
    border: 1px solid #e5e6eb !important;
    border-radius: 8px !important;
    margin-bottom: 5px !important;
    background-color: #ffffff;
    transition: all 0.2s ease;

    &:hover {
      background-color: #f7f8fa;
      border-color: #c9cdd4;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
  }

  .step-container {
    width: 100%;
  }

  /* 步骤信息行 */
  .step-info-row {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 8px;
    background-color: #f2f3f5;
    border-radius: 6px;
    flex-wrap: wrap;
  }

  /* 步骤类型标签 */
  .step-type {
    min-width: 120px;
  }

  .step-element {
    display: flex;
    align-items: center;
    min-width: 120px;
  }

  .operation-label,
  .element-label {
    font-weight: 500;
    color: #4e5969;
    margin-right: 4px;
  }

  .operation-value,
  .element-value {
    color: #1d2129;
    font-weight: 500;
  }

  /* 步骤详情区域 */
  .step-details {
    margin-top: 8px;
  }

  /* 输入框样式 */
  .input-label {
    display: inline-block;
    min-width: 80px;
    font-weight: 500;
    color: #4e5969;
    margin-right: 8px;
  }

  .custom-textarea {
    flex: 1;
    min-width: 200px;
  }

  /* 条件判断输入 */
  .condition-input {
    display: flex;
    align-items: flex-start;
    margin-bottom: 12px;
    padding: 8px;
    background-color: #fff7e6;
    border-radius: 4px;
  }

  /* 操作输入 */
  .operation-input {
    display: flex;
    align-items: center;
    margin-bottom: 8px;
  }

  /* 断言输入 */
  .assertion-input {
    display: flex;
    align-items: center;
    margin-bottom: 8px;
  }

  /* 自定义参数输入 */
  .custom-param-input {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .param-row {
    display: flex;
    align-items: center;
  }

  /* SQL输入 */
  .sql-input {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .sql-row {
    display: flex;
    align-items: center;
  }

  .sql-textarea {
    min-width: 300px;
  }

  /* Python代码编辑器 */
  .python-code {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .code-editor {
    height: 360px;
    width: 100%;
    max-width: 700px;
  }

  .save-btn {
    align-self: flex-start;
  }
</style>
