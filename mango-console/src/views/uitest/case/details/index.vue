<template>
  <TableBody ref="tableBody" class="mango-detail-workbench-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">{{ uiCaseDetailTitle }}</div>
          <div class="mango-detail-subtitle">维护用例前后置、步骤编排、断言和执行结果</div>
        </div>
        <a-space class="mango-detail-actions" wrap>
          <a-button size="small" status="success" :loading="caseRunning" @click="onCaseRun">
            执行
          </a-button>
          <a-button size="small" @click="doResetSearch">返回</a-button>
        </a-space>
      </div>
    </template>
    <template #default>
      <div
        class="ui-case-workbench mango-detail-workbench mango-detail-workbench--fill mango-detail-workbench--flex"
      >
        <section class="ui-case-panel">
          <div class="ui-case-panel-head">
            <div>
              <div class="ui-case-panel-title">步骤编排</div>
              <div class="ui-case-panel-subtitle">维护前置参数、用例步骤和后置处理</div>
            </div>
            <a-space wrap>
              <a-button
                size="small"
                type="primary"
                :loading="syncAllLoading"
                @click="addSynchronous"
                >全部同步</a-button
              >
              <a-button size="small" type="primary" @click="addData">增加步骤</a-button>
            </a-space>
          </div>
          <div class="ui-case-panel-body">
            <a-tabs default-active-key="2" @tab-click="(key) => switchType(key)">
              <a-tab-pane key="1" title="用例前置">
                <a-tabs
                  :default-active-key="data.uiSonType"
                  position="left"
                  @tab-click="(key) => switchSonType(key)"
                >
                  <a-tab-pane key="11" title="自定义参数">
                    <KeyValueList
                      :data-list="pageData.record.front_custom"
                      :field-config="[
                        { field: 'key', label: 'Key', placeholder: '请输入key的名称' },
                        { field: 'value', label: 'Value', placeholder: '请输入value的名称' },
                      ]"
                      :on-delete-item="
                        (index) => removeFrontSql(pageData.record.front_custom, index)
                      "
                      :on-save="upDataCase"
                    />
                  </a-tab-pane>
                  <a-tab-pane key="12" title="sql参数">
                    <KeyValueList
                      :data-list="pageData.record.front_sql"
                      :field-config="[
                        { field: 'sql', label: 'Sql语句', placeholder: '请输入sql语句' },
                        sqlDatasourceField,
                        {
                          field: 'key_list',
                          label: 'Key列表',
                          placeholder: '请输入查询结果缓存key',
                        },
                      ]"
                      :on-delete-item="(index) => removeFrontSql(pageData.record.front_sql, index)"
                      :on-save="upDataCase"
                    />
                  </a-tab-pane>
                  <a-tab-pane key="14" title="数据工厂">
                    <DataFactoryCaseConfigPanel
                      ref="dataFactoryPanelRef"
                      :case-id="route.query.case_id as string"
                      :project-product-id="route.query.project_product as string"
                      :source-type="2"
                    />
                  </a-tab-pane>
                </a-tabs>
              </a-tab-pane>

              <a-tab-pane key="2" title="用例步骤">
                <a-table
                  :key="tableKey"
                  :columns="columns"
                  :data="data.data"
                  :loading="stepTableLoading"
                  :draggable="{ type: 'handle', width: 40 }"
                  :pagination="false"
                  :scroll="{ x: 1020 }"
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
                      <template v-if="item.key === 'index'" #cell="{ record }">
                        {{ record.id }}
                      </template>
                      <template v-else-if="item.dataIndex === 'page_step_name'" #cell="{ record }">
                        {{ record.page_step?.name }}
                      </template>
                      <template v-else-if="item.dataIndex === 'status'" #cell="{ record }">
                        <a-tag :color="enumStore.status_colors[record.status]" size="small"
                          >{{ enumStore.task_status[record.status]?.title || '-' }}
                        </a-tag>
                      </template>
                      <template v-else-if="item.dataIndex === 'error_message'" #cell="{ record }">
                        <a-tooltip v-if="record.error_message" :content="record.error_message">
                          <span class="case-error-text">{{ record.error_message }}</span>
                        </a-tooltip>
                        <span v-else class="case-error-empty">-</span>
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
                        <MangoTableActions
                          :actions="[
                            {
                              label: '单步执行',
                              loading: caseRunning,
                              onClick: () => onPageStep(record),
                            },
                            { label: '同步数据', onClick: () => oeFreshSteps(record) },
                            { label: '编辑', onClick: () => onUpdate1(record) },
                            { label: '删除', danger: true, onClick: () => onDelete(record) },
                          ]"
                        />
                      </template>
                    </a-table-column>
                  </template>
                </a-table>
              </a-tab-pane>
              <a-tab-pane key="3" title="用例后置">
                <a-tabs position="left" @tab-click="(key) => switchSonType(key)">
                  <a-tab-pane key="31" title="sql参数">
                    <KeyValueList
                      :data-list="pageData.record.posterior_sql"
                      :field-config="[
                        { field: 'sql', label: 'Sql语句', placeholder: '请输入sql语句' },
                        sqlDatasourceField,
                      ]"
                      :on-delete-item="
                        (index) => removeFrontSql(pageData.record.posterior_sql, index)
                      "
                      :on-save="upDataCase"
                    />
                  </a-tab-pane>
                </a-tabs>
              </a-tab-pane>
            </a-tabs>
          </div>
        </section>
        <section class="ui-case-panel">
          <div class="ui-case-panel-head">
            <div>
              <div class="ui-case-panel-title">执行详情</div>
              <div class="ui-case-panel-subtitle">
                {{ data.selectData?.page_step?.name || '选择左侧步骤后查看执行顺序和结果' }}
              </div>
            </div>
            <a-tag
              v-if="data.selectData?.status !== undefined"
              :color="enumStore.status_colors[data.selectData.status]"
              size="small"
            >
              {{ enumStore.task_status[data.selectData.status]?.title }}
            </a-tag>
          </div>
          <div class="ui-case-panel-body">
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
                            useSelectValue.findItemByValue(item.ope_key)?.label
                          }}</span>
                        </div>
                        <div class="step-element" v-if="item.page_step_details_name">
                          <span class="element-label">元素名称：</span>
                          <span class="element-value">{{ item.page_step_details_name }}</span>
                        </div>
                      </div>

                      <!-- 步骤详情数据 -->
                      <div class="step-details">
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
                        <template
                          v-for="(item1, idx) of item.page_step_details_data"
                          :key="item1.id || `${item.page_step_details_id}-${idx}`"
                        >
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
                          <template v-else-if="item.type === 1">
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
                              <a-button
                                type="primary"
                                class="save-btn"
                                :loading="detailSaving"
                                @click="onUpdate"
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
                <ElementTestReport :result-data="data.selectData?.result_data || {}" />
              </a-tab-pane>
            </a-tabs>
          </div>
        </section>
      </div>
    </template>
  </TableBody>

  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          v-for="item of formItems"
          :key="item.key"
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
          <template v-else-if="item.type === 'cascader' && item.key === 'module'">
            <ProductModuleSelect
              v-model="item.value"
              :project-product-id="pageData.record.project_product?.id || route.query.project_product"
              :placeholder="item.placeholder"
              @change="doUiPageNameAll"
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
  import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'

  import { ModalDialogType } from '@/types/components'
  import { useRoute } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import ModalDialog from '@/components/overlays/ModalDialog.vue'
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
  import { getUiCaseRun, putUiCase } from '@/api/uitest/case'
  import { getUiStepsPageStepsName, getUiStepsTest } from '@/api/uitest/page-steps'
  import { getUiPageName } from '@/api/uitest/page'
  import useUserStore from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import ElementTestReport from '@/components/reports/ElementTestReport.vue'
  import { useSelectValueStore } from '@/store/modules/get-ope-value'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import KeyValueList from '@/components/forms/KeyValueList.vue'
  import DataFactoryCaseConfigPanel from '@/components/DataFactory/CaseConfigPanel.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { getDataFactoryDatasourceAlias } from '@/api/data-factory'

  const userStore = useUserStore()
  const enumStore = useEnum()

  const pageData: any = usePageData()
  const route = useRoute()
  const formModel = ref({})
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const dataFactoryPanelRef = ref<InstanceType<typeof DataFactoryCaseConfigPanel> | null>(null)
  const tableKey = ref(0)
  const data: any = reactive({
    isAdd: true,
    updateId: null,
    pageName: [],
    pageStepsName: [],
    data: [],
    selectData: {},
    actionTitle: '新增',
    uiType: '2',
    uiSonType: '11',
    datasourceAliasOptions: [],
  })
  const useSelectValue = useSelectValueStore()

  const caseRunning = ref(false)
  const stepTableLoading = ref(false)
  const syncAllLoading = ref(false)
  const detailSaving = ref(false)
  const uiCaseDetailTitle = computed(() => {
    const id = pageData.record?.id || route.query.id || '-'
    const name = pageData.record?.name || '-'
    return `界面用例配置 / ${id} / ${name}`
  })
  const pollingTimer = ref<NodeJS.Timeout | null>(null)
  const sqlDatasourceField = computed(() => ({
    field: 'datasource_alias',
    label: '数据源',
    type: 'select',
    placeholder: '单库可不选',
    options: data.datasourceAliasOptions,
  }))

  function clearPollingTimer() {
    if (pollingTimer.value) {
      clearInterval(pollingTimer.value)
      pollingTimer.value = null
    }
  }

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
      pageData.record.front_sql.push({ sql: '', key_list: '', datasource_alias: null })
    } else if (data.uiSonType === '14') {
      dataFactoryPanelRef.value?.open()
    } else if (data.uiSonType === '31') {
      pageData.record.posterior_sql.push({ sql: '', datasource_alias: null })
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
      onBeforeOk: () => {
        return deleteUiCaseStepsDetailed(record.id, record.case.id)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
          .finally(() => {
            doRefresh()
          })
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
      let value = getFormItems(formItems)
      if (data.isAdd) {
        value['case'] = route.query.id
        value['case_cache_data'] = []
        value['case_cache_ass'] = []
        value['case_sort'] = data.data.length
        postUiCaseStepsDetailed(value, route.query.id)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            getUiCaseStepsRefreshCacheData(res.data.id)
              .then((res) => {
                Message.success(res.msg)
                doRefresh()
              })
              .catch(console.log)
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      } else {
        value['id'] = data.updateId
        putUiCaseStepsDetailed(value, route.query.id)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      }
    } else {
      modalDialogRef.value?.setConfirmLoading(false)
    }
  }

  function doResetSearch() {
    window.history.back()
  }

  function doRefresh() {
    clearPollingTimer()
    stepTableLoading.value = true

    getUiCaseStepsDetailed(route.query.id)
      .then((res) => {
        data.data = res.data
        if (data.selectData && res.data) {
          res.data.forEach((item: any) => {
            if (item.id === data.selectData.id) {
              data.selectData = item
            }
          })
        } else if (res.data) {
          data.selectData = res.data[0]
        }

        const hasRunningItem =
          res.data && Array.isArray(res.data) && res.data.some((item: any) => item.status === 3)

        if (hasRunningItem) {
          // 5秒后再次刷新
          pollingTimer.value = setInterval(() => {
            doRefresh()
          }, 5000)
        }
      })
      .catch(console.log)
      .finally(() => {
        stepTableLoading.value = false
      })
  }

  function oeFreshSteps(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否确实从页面步骤详情中同步数据？点击确认后，原始数据会丢失！',
      cancelText: '取消',
      okText: '刷新',
      onBeforeOk: () => {
        return getUiCaseStepsRefreshCacheData(record.id)
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
      onBeforeOk: () => {
        syncAllLoading.value = true
        return getUiCaseStepsRefreshCacheData(null, route.query.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
          .finally(() => {
            syncAllLoading.value = false
          })
      },
    })
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

  function loadDatasourceAliases() {
    getDataFactoryDatasourceAlias({
      project_product: route.query.project_product,
      status: 1,
    })
      .then((res) => {
        data.datasourceAliasOptions = (res.data || []).map((item: any) => ({
          label: item.name,
          value: item.id,
        }))
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
    } catch (e) {
    } finally {
      caseRunning.value = false
      doRefresh()
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
    if (detailSaving.value) return
    detailSaving.value = true
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
      .finally(() => {
        detailSaving.value = false
      })
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
      doRefresh()
    }
  }

  function onModifyStatus(newValue: any, id: number, key: string) {
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
      useSelectValue.getSelectValue()
      loadDatasourceAliases()
    })
  })
  onUnmounted(() => {
    clearPollingTimer()
  })
</script>

<style scoped>
  .ui-case-workbench {
    min-height: 0;
  }

  .ui-case-panel {
    display: flex;
    overflow: hidden;
    flex: 1 1 0;
    flex-direction: column;
    min-width: 0;
    min-height: 0;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .ui-case-panel-head {
    display: flex;
    flex: none;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-height: 58px;
    padding: 10px 12px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface);
  }

  .ui-case-panel-title {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }

  .ui-case-panel-subtitle {
    display: -webkit-box;
    overflow: hidden;
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 1;
  }

  .ui-case-panel-body {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: 12px;
  }

  .ui-case-panel-body :deep(.arco-tabs),
  .ui-case-panel-body :deep(.arco-tabs-content),
  .ui-case-panel-body :deep(.arco-tabs-content-list),
  .ui-case-panel-body :deep(.arco-tabs-pane) {
    height: 100%;
    min-height: 0;
  }

  .ui-case-panel-body :deep(.arco-tabs-content) {
    padding-top: 10px;
  }

  .case-error-text {
    display: block;
    overflow: hidden;
    max-width: 100%;
    color: var(--m-danger);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .case-error-empty {
    color: var(--m-muted);
  }

  .step-execution-list .step-header {
    color: var(--m-text);
    font-size: 16px;
    font-weight: 600;
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
    border: 1px solid var(--m-border) !important;
    border-radius: 8px !important;
    margin-bottom: 5px !important;
    background-color: var(--m-surface);
    transition: all 0.2s ease;
  }

  .step-list-item:hover {
    border-color: var(--m-border-strong);
    background-color: var(--m-surface-soft);
    box-shadow: var(--m-shadow);
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
    background-color: var(--m-surface-soft);
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
    color: var(--m-muted);
    margin-right: 4px;
  }

  .operation-value,
  .element-value {
    color: var(--m-text);
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
    color: var(--m-muted);
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
    background-color: color-mix(in srgb, var(--m-warning) 12%, var(--m-surface));
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

  /* 确保KeyValueList中的所有元素都在一行 */
  :deep(.mango-key-value-row) {
    flex-wrap: nowrap;
    align-items: flex-start;
    width: 100%;
    min-width: 0; /* 允许子元素收缩 */
    overflow-x: hidden; /* 防止水平滚动 */
  }

  :deep(.mango-key-value-field) {
    flex: 1;
    min-width: 100px; /* 减小最小宽度 */
    overflow: hidden; /* 防止内容溢出 */
  }

  :deep(.mango-button-container) {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    flex-shrink: 0;
    white-space: nowrap; /* 防止按钮内文字换行 */
    min-width: fit-content; /* 确保按钮容器不会收缩 */
  }

  :deep(.mango-remove-btn) {
    flex-shrink: 0;
    margin-top: 18px;
    min-width: fit-content; /* 确保按钮不会收缩 */
  }

  /* 响应式处理：在小屏幕上允许换行，但保持按钮在同一行 */
  @media (max-width: 1px) {
    :deep(.mango-key-value-row) {
      flex-wrap: wrap;
    }

    :deep(.mango-key-value-field) {
      min-width: 120px;
    }

    :deep(.mango-button-container) {
      width: 100%;
      justify-content: flex-end;
      margin-top: 8px;
    }

    :deep(.mango-remove-btn) {
      margin-top: 0;
      align-self: center;
    }
  }

  .drag-handle {
    cursor: move;
    color: var(--m-muted);
  }

  .drag-handle:hover {
    color: var(--m-primary);
  }
</style>
