<template>
  <TableBody ref="tableBody" plain class="mango-detail-workbench-page">
    <template #header>
      <TableHeader title="页面步骤" />
    </template>
    <template #default>
      <ProjectProductNavigationWorkbench
        contained-body
        show-modules
        emit-initial-filter
        :model-value="getConditionValue('project_product')"
        :module-value="getConditionValue('module')"
        :reset-key="sidebarResetKey"
        @filter-change="onSidebarFilterChange"
        @search="onSearchRefresh"
        @reset-search="onResetSearch"
      >
        <template #search>
          <a-form :model="{}" layout="inline" @keyup.enter="onSearchRefresh">
                <a-form-item
                  v-for="item of headerConditionItems"
                  :key="item.key"
                  :label="item.label"
                >
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="onSearchRefresh"
                  @clear="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'cascader' && item.key === 'project_product'">
                <ProjectProductSelect
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  @change="onSearchProjectProductChange"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'module'">
                <ProductModuleSelect
                  v-model="item.value"
                  :project-product-id="getConditionValue('project_product')"
                  :placeholder="item.placeholder"
                  :auto-clear="false"
                  @change="onSearchModuleChange"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'page_id'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="data.pageName"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'status'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="enumStore.task_status"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'update_user'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="item.optionItems"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-if="item.type === 'date'">
                <a-date-picker v-model="item.value" />
              </template>
              <template v-if="item.type === 'time'">
                <a-time-picker v-model="item.value" value-format="HH:mm:ss" />
              </template>
              <template v-if="item.type === 'check-group'">
                <a-checkbox-group v-model="item.value">
                  <a-checkbox v-for="it of item.optionItems" :key="it.value" :value="it.value">
                    {{ item.label }}
                  </a-checkbox>
                </a-checkbox-group>
              </template>
            </a-form-item>
          </a-form>
        </template>
        <template #toolbar>
          <a-space>
            <a-button
              size="small"
              type="primary"
              @click="onAdd"
              data-testid="qa-views-uitest-page-steps-button-新增"
            >
              新增
            </a-button>
            <a-button
              size="small"
              status="danger"
              @click="onDelete(null)"
              data-testid="qa-views-uitest-page-steps-button-批量删除"
            >
              批量删除
            </a-button>
          </a-space>
        </template>
      <a-table
        class="mango-native-scroll-table"
        :scroll="{ x: 1180, y: '100%' }"
        :bordered="false"
        :columns="tableColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :row-selection="{ selectedRowKeys, showCheckedAll }"
        :rowKey="rowKey"
        @selection-change="onSelectionChange"
      >
        <template #columns>
          <a-table-column
            v-for="item of tableColumns"
            :key="item.key"
            :align="item.align"
            :data-index="item.key"
            :ellipsis="item.ellipsis"
            :fixed="item.fixed"
            :title="item.title"
            :tooltip="item.tooltip"
            :width="item.width"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'page'" #cell="{ record }">
              {{ record.page.name }}
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="enumStore.status_colors[record.status]" size="small"
                >{{ enumStore.task_status[record.status]?.title || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ formatProjectProductPath(record.project_product) }}
            </template>
            <template v-else-if="item.key === 'module'" #cell="{ record }">
              {{ formatModulePath(record.module) }}
            </template>
            <template v-else-if="item.key === 'update_user'" #cell="{ record }">
              {{ record.update_user?.name || record.update_user?.username || '-' }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
    { label: '调试', loading: caseRunning, onClick: () => onRunCase(record) },
    { label: '步骤', onClick: () => onClick(record) },
    { label: '用例', onClick: () => onShowReferencedCases(record) },
    { label: '编辑', onClick: () => onUpdate(record) },
    { label: '删除', danger: true, onClick: () => onDelete(record) },
]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
      </ProjectProductNavigationWorkbench>
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
          <template v-else-if="item.type === 'cascader'">
            <ProjectProductSelect
              v-model="item.value"
              :placeholder="item.placeholder"
              @change="onFormProjectProductChange"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'module'">
            <ProductModuleSelect
              v-model="item.value"
              :project-product-id="getFormItemValue('project_product')"
              :placeholder="item.placeholder"
              :auto-clear="false"
              @change="onModulePage(item.value, false)"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'page'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :field-names="fieldNames"
              :options="data.pageName"
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

  <BaseSidePanel
    v-model:visible="caseReferencePanel.visible"
    :title="caseReferencePanel.title"
    width="64%"
    @cancel="closeCaseReferencePanel"
  >
    <a-spin class="mango-page-step-reference-loading" :loading="caseReferencePanel.loading">
      <div class="mango-page-step-reference-summary">
        <span>当前步骤被</span>
        <strong>{{ caseReferencePanel.cases.length }}</strong>
        <span>个用例引用</span>
      </div>
      <div
        v-if="!caseReferencePanel.loading && caseReferencePanel.cases.length === 0"
        class="mango-empty-state mango-page-step-reference-empty"
      >
        该步骤暂未被任何用例引用
      </div>
      <a-table
        v-else
        :bordered="false"
        :columns="referencedCaseColumns"
        :data="caseReferencePanel.cases"
        :pagination="false"
        :scroll="{ x: 1100 }"
        row-key="id"
      >
        <template #columns>
          <a-table-column
            v-for="item of referencedCaseColumns"
            :key="item.key"
            :align="item.align"
            :data-index="item.key"
            :ellipsis="item.ellipsis"
            :fixed="item.fixed"
            :title="item.title"
            :tooltip="item.tooltip"
            :width="item.width"
          >
            <template v-if="item.key === 'project_product'" #cell="{ record }">
              {{ formatProjectProductPath(record.project_product) }}
            </template>
            <template v-else-if="item.key === 'module'" #cell="{ record }">
              {{ formatModulePath(record.module) }}
            </template>
            <template v-else-if="item.key === 'case_people'" #cell="{ record }">
              {{ record.case_people?.name || record.case_people?.username || '-' }}
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="enumStore.status_colors[record.status]" size="small">
                {{ enumStore.task_status[record.status]?.title || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[{ label: '步骤', onClick: () => openReferencedCase(record) }]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-spin>
  </BaseSidePanel>

  <BaseSidePanel
    v-model:visible="caseDetailPanel.visible"
    title="界面用例配置"
    width="80%"
    mode="page"
    @cancel="closeCaseDetailPanel"
  >
    <UiCaseDetails
      v-if="caseDetailPanel.visible && caseDetailPanel.caseId"
      :key="caseDetailPanel.caseId"
      embedded
      :case-id="caseDetailPanel.caseId"
      :project-product-id="caseDetailPanel.projectProductId"
      @close="closeCaseDetailPanel"
    />
  </BaseSidePanel>
</template>

<script lang="ts" setup>
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { usePageData } from '@/store/page-data'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import {
    formatProjectProductPath,
    formatModulePath,
    getItemValue,
    setItemValue,
  } from '@/utils/business-format'
  import {
    deleteUiSteps,
    getUiPageStepReferencedCases,
    getUiPageStepsCopy,
    getUiSteps,
    getUiStepsTest,
    postUiSteps,
    putUiSteps,
  } from '@/api/uitest/page-steps'
  import { getUiPageName } from '@/api/uitest/page'
  import { getUserName } from '@/api/user/user'
  import { conditionItems, formItems, referencedCaseColumns, tableColumns } from './config'
  import { setUpdateUserOptions } from '@/utils/update-user'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import UiCaseDetails from '@/views/uitest/case/details/index.vue'

  const enumStore = useEnum()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const { beginRequest, isLatestRequest } = useLatestRequest()
  const rowKey = useRowKey('id')
  const sidebarResetKey = ref(0)
  const headerConditionItems = computed(() =>
    conditionItems.filter((item) => item.key !== 'project_product' && item.key !== 'module')
  )
  const userStore = useUserStore()

  const formModel = ref({})
  const data = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
    pageName: [],
  })
  const caseRunning = ref(false)
  const pollingTimer = ref<NodeJS.Timeout | null>(null)
  const caseReferencePanel = reactive({
    visible: false,
    loading: false,
    title: '引用用例',
    cases: [] as any[],
  })
  const caseDetailPanel = reactive({
    visible: false,
    caseId: '' as string | number,
    projectProductId: '' as string | number,
  })

  async function onShowReferencedCases(record: any) {
    caseReferencePanel.visible = true
    caseReferencePanel.loading = true
    caseReferencePanel.title = `引用用例 · ${record.name || `步骤 ${record.id}`}`
    caseReferencePanel.cases = []
    try {
      const res = await getUiPageStepReferencedCases(record.id)
      caseReferencePanel.cases = Array.isArray(res.data) ? res.data : []
    } catch (error) {
      caseReferencePanel.cases = []
    } finally {
      caseReferencePanel.loading = false
    }
  }

  function closeCaseReferencePanel() {
    caseReferencePanel.visible = false
    closeCaseDetailPanel()
  }

  function openReferencedCase(record: any) {
    caseDetailPanel.caseId = record.id
    caseDetailPanel.projectProductId = record.project_product?.id || ''
    caseDetailPanel.visible = true
  }

  function closeCaseDetailPanel() {
    caseDetailPanel.visible = false
    caseDetailPanel.caseId = ''
    caseDetailPanel.projectProductId = ''
  }

  function clearPollingTimer() {
    if (pollingTimer.value) {
      clearInterval(pollingTimer.value)
      pollingTimer.value = null
    }
  }

  function getConditionValue(key: string) {
    return getItemValue(conditionItems, key)
  }

  function getFormItemValue(key: string) {
    return getItemValue(formItems, key)
  }

  function onSearchProjectProductChange(value: any) {
    setItemValue(conditionItems, 'module', '')
    setItemValue(conditionItems, 'page_id', '')
    data.pageName = []
    doRefresh(value, true, true)
  }

  function onSearchModuleChange(value: any) {
    setItemValue(conditionItems, 'page_id', '')
    onModulePage(value, true)
  }

  function onFormProjectProductChange() {
    setItemValue(formItems, 'module', '')
    setItemValue(formItems, 'page', '')
    data.pageName = []
  }

  function onSearchRefresh() {
    doRefresh(null, false, true)
  }

  function onSidebarFilterChange(filter: { projectProduct: any; module: any }) {
    setItemValue(conditionItems, 'project_product', filter.projectProduct)
    setItemValue(conditionItems, 'module', filter.module)
    setItemValue(conditionItems, 'page_id', '')
    data.pageName = []
    if (filter.module) onModulePage(filter.module, false)
    pagination.page = 1
    selectedRowKeys.value = []
    doRefresh(null, false, true)
  }

  function doRefresh(projectProductId: any = null, bool_ = false, showLoading = false) {
    clearPollingTimer()
    const requestId = beginRequest()
    if (showLoading) {
      table.tableLoading.value = true
    }
    let value = getFormItems(conditionItems)
    if (value.update_user === null || value.update_user === '') {
      delete value.update_user
    }
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    if (projectProductId && bool_) {
      value['project_product'] = projectProductId
    }
    getUiSteps(value)
      .then((res) => {
        if (!isLatestRequest(requestId)) return
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
        const hasRunningItem =
          res.data && Array.isArray(res.data) && res.data.some((item: any) => item.status === 3)

        if (hasRunningItem) {
          // 5秒后再次刷新
          pollingTimer.value = setInterval(() => {
            doRefresh(projectProductId, bool_, false)
          }, 5000)
        }
      })
      .catch((error) => {
        if (isLatestRequest(requestId)) console.log(error)
      })
      .finally(() => {
        if (isLatestRequest(requestId)) {
          table.tableLoading.value = false
        }
      })
  }

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = it.multiple ? [] : ''
    })
    sidebarResetKey.value += 1
    doRefresh(null, false, true)
  }

  function onAdd() {
    data.actionTitle = '新增'
    data.isAdd = true
    modalDialogRef.value?.toggle()
    formItems.forEach((it: any) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = it.multiple ? [] : ''
      }
    })
  }

  function onDelete(record: any) {
    const batch = record === null
    if (batch) {
      if (selectedRowKeys.value.length === 0) {
        Message.error('请选择要删除的数据')
        return
      }
    }
    Modal.confirm({
      title: '提示',
      content: '是否要删除此步骤？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteUiSteps(batch ? selectedRowKeys.value : record.id)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
          .finally(() => {
            doRefresh()
            if (batch) {
              selectedRowKeys.value = []
            }
          })
      },
    })
  }

  function onUpdate(item: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
    onModulePage(item.module.id, false)
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = item[it.key]
        if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
        } else {
          it.value = item.name
        }
      })
    })
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(formItems)
      if (data.isAdd) {
        postUiSteps(value)
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
      } else {
        value['id'] = data.updateId
        value['parent_id'] = data.updateId
        putUiSteps(value)
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

  const onRunCase = async (param) => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (caseRunning.value) return
    caseRunning.value = true
    try {
      const res = await getUiStepsTest(param.id, userStore.selected_environment)
      Message.loading(res.msg)
    } catch (e) {
    } finally {
      caseRunning.value = false
      doRefresh()
    }
  }

  const router = useRouter()

  function onClick(record: any) {
    const pageData = usePageData()
    pageData.setRecord(record)
    router.push({
      path: '/uitest/page/steps/details',
      query: {
        id: parseInt(record.id, 10),
      },
    })
  }

  function onModulePage(moduleId: any, refresh: boolean) {
    if (refresh) {
      doRefresh(null, false, true)
    }
    getUiPageName(moduleId)
      .then((res) => {
        data.pageName = res.data
      })
      .catch(() => {
        data.pageName = []
        setItemValue(formItems, 'page', null)
      })
  }

  function onPageStepsCopy(record: any) {
    getUiPageStepsCopy(record.id)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      getUserName().then((res) => setUpdateUserOptions(conditionItems, res.data || []))
      onModulePage(null, false)
    })
  })
  onUnmounted(() => {
    clearPollingTimer()
  })
</script>

<style scoped>
  .mango-page-step-reference-loading {
    display: block;
    min-height: 240px;
    padding: 0;
  }

  .mango-page-step-reference-summary {
    display: flex;
    align-items: center;
    gap: 4px;
    margin-bottom: 12px;
    color: var(--m-text-2);
  }

  .mango-page-step-reference-summary strong {
    color: var(--m-text);
  }

  .mango-page-step-reference-empty {
    min-height: 200px;
  }
</style>
