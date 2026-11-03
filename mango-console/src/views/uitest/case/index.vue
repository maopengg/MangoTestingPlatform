<template>
  <TableBody ref="tableBody" plain class="mango-detail-workbench-page">
    <template #header>
      <TableHeader title="测试用例" />
    </template>

    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
        :model-value="getConditionValue('project_product')"
        :module-value="getConditionValue('module')"
        :reset-key="sidebarResetKey"
        show-modules
        @filter-change="onNavigationFilterChange"
        @search="onSearchRefresh"
        @reset-search="onResetSearch"
      >
        <template #search>
          <a-form :model="{}" layout="inline" @keyup.enter="onSearchRefresh">
            <a-form-item v-for="item of headerConditionItems" :key="item.key" :label="item.label">
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
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'case_people'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="data.userList"
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
                  :options="data.userList"
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
              <template v-else-if="item.type === 'select' && item.key === 'level'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="enumStore.case_level"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'scenario_layer'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="enumStore.api_case_scenario_layer"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'scenario_type'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="enumStore.api_case_scenario_type"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'scenario_tags'">
                <a-select
                  v-model="item.value"
                  :field-names="fieldNames"
                  :options="enumStore.api_case_scenario_tag"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  multiple
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
        <template #tabs>
          <TableTabs :active-key="activePublicationStatus" @tab-click="switchPublicationTab">
            <a-tab-pane v-for="tab in publicationTabs" :key="tab.key" :title="tab.title" />
            <template #extra>
          <a-space>
            <div>
              <a-button
                size="small"
                status="success"
                :loading="caseRunning"
                @click="onConcurrency('批量执行')" data-testid="qa-views-uitest-case-button-批量执行"
                >批量执行
              </a-button>
            </div>
            <div>
              <a-button  size="small" status="warning" @click="handleClick" data-testid="qa-views-uitest-case-button-设为定时任务">设为定时任务</a-button>
              <a-modal v-model:visible="data.visible" @cancel="handleCancel" @ok="handleOk">
                <template #title> 设为定时任务</template>
                <a-form :model="data">
                  <a-form-item class="mango-form-item__require" label="项目产品">
                    <ProjectProductSelect
                      v-model="data.scheduledProjectProduct"
                      placeholder="请选择项目产品"
                      @change="onScheduledProjectProductChange"
                    />
                  </a-form-item>
                  <a-form-item label="模块">
                    <ProductModuleSelect
                      v-model="data.scheduledModule"
                      :auto-clear="false"
                      :disabled="!getOptionId(data.scheduledProjectProduct)"
                      :project-product-id="data.scheduledProjectProduct"
                      :selectable-level="0"
                      show-all-option
                      placeholder="请选择模块分类（可选）"
                      @change="onScheduledModuleChange"
                    />
                  </a-form-item>
                  <a-form-item class="mango-form-item__require" label="定时任务">
                    <a-select
                      v-model="data.value"
                      :disabled="!getOptionId(data.scheduledProjectProduct)"
                      :field-names="fieldNames"
                      :loading="data.scheduledNameLoading"
                      :options="data.scheduledName"
                      allow-clear
                      allow-search
                      placeholder="请选择定时任务进行绑定"
                      value-key="key"
                      data-testid="qa-views-uitest-case-select-请选择定时任务进行绑定"
                    />
                  </a-form-item>
                </a-form>
              </a-modal>
            </div>
            <div>
              <a-button  size="small" type="primary" @click="onAdd" data-testid="qa-views-uitest-case-button-新增">新增</a-button>
            </div>
            <div>
              <a-button  size="small" status="danger" @click="onDelete(null)" data-testid="qa-views-uitest-case-button-批量删除">批量删除</a-button>
            </div>
          </a-space>
            </template>
          </TableTabs>
        </template>

      <a-table
        class="mango-native-scroll-table"
        :bordered="false"
        :columns="visibleTableColumns"
        :data="batchSelectableDataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :row-selection="{ selectedRowKeys, showCheckedAll }"
        :rowKey="rowKey"
        :scroll="{ x: 2000, y: '100%' }"
        @selection-change="onUiCaseSelectionChange"
      >
        <template #columns>
          <a-table-column
            v-for="item of visibleTableColumns"
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
            <template v-else-if="item.key === 'scenario_type'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.scenario_type]" size="small">
                {{ getEnumTitle(enumStore.api_case_scenario_type, record.scenario_type) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'scenario_layer'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.scenario_layer]" size="small">
                {{ getEnumTitle(enumStore.api_case_scenario_layer, record.scenario_layer) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'scenario_tags'" #cell="{ record }">
              <ExecutionSceneTagGrid
                :values="record.scenario_tags"
                :options="enumStore.api_case_scenario_tag"
                :colors="enumStore.colors"
              />
            </template>
            <template v-else-if="item.key === 'scenario_description'" #cell="{ record }">
              {{ record.scenario_description || '-' }}
            </template>
            <template v-else-if="item.key === 'level'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record?.level]" size="small"
                >{{ record.level !== null ? enumStore.case_level[record.level]?.title || '-' : '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'case_people'" #cell="{ record }">
              {{ record.case_people.name }}
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="enumStore.status_colors[record.status]" size="small"
                >{{ enumStore.task_status[record.status]?.title || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'publication_status'" #cell="{ record }">
              <a-tag :color="record.publication_status === 'published' ? 'green' : record.publication_status === 'prepublished' ? 'orange' : 'gray'" size="small">
                {{ publicationTabs.find((tab) => tab.key === record.publication_status)?.title || '未发布' }}
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
    { label: '执行', loading: caseRunning, onClick: () => onCaseRun(record.id) },
    { label: '步骤', onClick: () => onClick(record) },
    { label: '套件', onClick: () => clickSuite(record) },
    { label: '编辑', onClick: () => onUpdate(record) },
    { label: '复制', onClick: () => caseCody(record) },
    {
        hidden: record.publication_status !== 'unpublished',
        label: '提交预发布',
        loading: publicationActionCaseId === record.id,
        onClick: () => onPublicationChange(record, 'prepublished'),
    },
    {
        hidden: record.publication_status !== 'prepublished' || !record.is_product_owner,
        label: '通过发布',
        loading: publicationActionCaseId === record.id,
        onClick: () => onPublicationChange(record, 'published'),
    },
    {
        hidden: record.publication_status === 'unpublished' || !record.is_product_owner,
        label: '退回未发布', danger: true,
        loading: publicationActionCaseId === record.id,
        onClick: () => onPublicationChange(record, 'unpublished'),
    },
    { label: '删除', danger: true, onClick: () => onDelete(record) },
]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
      <ParametrizeDrawer
        v-model:initial-data="data.row.parametrize"
        show-environment
        :visible="data.drawerVisible"
        @cancel="data.drawerVisible = false"
        @ok="drawerOk"
      />
        <template #footer>
          <TableFooter :pagination="pagination" />
        </template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>
  <CasePublicationReviewModal ref="publicationReviewRef" @published="doRefresh()" />
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
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'case_people'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :field-names="fieldNames"
              :options="data.userList"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'level'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :field-names="fieldNames"
              :options="enumStore.case_level"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'scenario_layer'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :field-names="fieldNames"
              :options="enumStore.api_case_scenario_layer"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'scenario_type'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :field-names="fieldNames"
              :options="enumStore.api_case_scenario_type"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'scenario_tags'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="enumStore.api_case_scenario_tag"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              multiple
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'textarea'">
            <a-textarea
              v-model="item.value"
              :placeholder="item.placeholder"
              :auto-size="{ minRows: 3, maxRows: 5 }"
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import CasePublicationReviewModal from '@/components/business/CasePublicationReviewModal.vue'
  import { usePagination, useRowKey, useTable } from '@/hooks/table'
  import { useProjectLockedRowSelection } from '@/hooks/use-project-locked-row-selection'
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, onMounted, ref, nextTick, reactive, onUnmounted } from 'vue'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { useRoute, useRouter } from 'vue-router'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { usePageData } from '@/store/page-data'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import ExecutionSceneTagGrid from '@/components/display/ExecutionSceneTagGrid.vue'
  import {
    formatProjectProductPath,
    formatModulePath,
    getItemValue,
    getOptionId,
    setItemValue,
  } from '@/utils/business-format'
  import { conditionItems, formItems, tableColumns, publicationTabs } from './config'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import {
    deleteUiCase,
    getUiCase,
    getUiCaseRun,
    postUiCase,
    postUiCaseCopy,
    putUiCase,
    putUiCasePublication,
    postUiRunCaseBatch,
  } from '@/api/uitest/case'
  import { getSystemTasksName } from '@/api/system/tasks'
  import { postSystemTasksBatchSetCases } from '@/api/system/tasks_details'
  import { getUserName } from '@/api/user/user'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { prefillNavigationFormItems, NavigationCreateSource } from '@/utils/navigation-create-defaults'

  const navigationCreateRef = ref<NavigationCreateSource | null>(null)

  const enumStore = useEnum()

  const userStore = useUserStore()
  const router = useRouter()
  const route = useRoute()
  const { beginRequest, isLatestRequest } = useLatestRequest()
  const activePublicationStatus = ref('all')

  function switchPublicationTab(key: string | number) {
    activePublicationStatus.value = String(key)
    pagination.page = 1
    selectedRowKeys.value = []
    doRefresh(null, false, true)
  }

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const publicationReviewRef = ref<InstanceType<typeof CasePublicationReviewModal> | null>(null)
  const table = useTable()
  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const {
    selectedRowKeys,
    showCheckedAll,
    selectableDataList: batchSelectableDataList,
    onSelectionChange: onUiCaseSelectionChange,
    validateSingleProject,
  } = useProjectLockedRowSelection<any>(
    () => table.dataList,
    (row) => row?.project_product?.project
  )
  const sidebarResetKey = ref(0)
  const sidebarModuleIds = ref<Array<string | number>>([])
  const headerConditionItems = computed(() =>
    conditionItems.filter((item) => !['project_product', 'module'].includes(item.key))
  )
  const visibleTableColumns = tableColumns
  const rowKey = useRowKey('id')
  const formModel = ref({})

  const data: any = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
    userList: [],
    moduleList: [],
    systemStatus: [],
    scheduledName: [],
    scheduledNameLoading: false,
    scheduledProjectProduct: null,
    scheduledModule: '__all__',
    value: null,
    visible: false,
    drawerVisible: false,
    row: {},
  })
  const caseRunning = ref(false)
  const publicationActionCaseId = ref<number | null>(null)

  const pollingTimer = ref<NodeJS.Timeout | null>(null)

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
    setItemValue(conditionItems, 'module', null)
    doRefresh(value, true, true)
  }

  function onFormProjectProductChange() {
    setItemValue(formItems, 'module', null)
  }

  function onSearchRefresh() {
    doRefresh(null, false, true)
  }

  function onNavigationFilterChange({
    projectProduct,
    module,
    moduleIds,
  }: {
    projectProduct: any
    module: any
    moduleIds?: Array<string | number>
  }) {
    setItemValue(conditionItems, 'project_product', projectProduct ?? null)
    setItemValue(conditionItems, 'module', module ?? null)
    sidebarModuleIds.value = moduleIds || []
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
    if (activePublicationStatus.value !== 'all') value.publication_status = activePublicationStatus.value
    if (sidebarModuleIds.value.length) value['module__in'] = sidebarModuleIds.value.join(',')
    if (!Array.isArray(value.scenario_tags) || !value.scenario_tags.length) {
      delete value.scenario_tags
    }
    if (value.update_user === null || value.update_user === '') {
      delete value.update_user
    }
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    if (projectProductId && bool_) {
      value['project_product'] = projectProductId
    }
    getUiCase(value)
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
      .catch(console.log)
      .finally(() => {
        if (isLatestRequest(requestId)) table.tableLoading.value = false
      })
  }

  function onResetSearch() {
    pagination.page = 1
    sidebarModuleIds.value = []
    conditionItems.forEach((it) => {
      if (it.key === 'project_product' || it.key === 'module') {
        it.value = null
      } else if (it.reset) {
        it.reset()
      } else {
        it.value = it.multiple ? [] : ''
      }
    })
    sidebarResetKey.value += 1
    doRefresh(null, false, true)
  }

  function getEnumTitle(options: any[] | null, value: any) {
    return options?.find((item: any) => Number(item.key) === Number(value))?.title || '-'
  }

  function onAdd() {
    data.actionTitle = '添加'
    data.isAdd = true
    modalDialogRef.value?.toggle()
    formItems.forEach((it: any) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = it.multiple ? [] : ''
      }
    })
    void prefillNavigationFormItems(navigationCreateRef.value, formItems, () => data.isAdd)
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
      content: '是否要删除此用例？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteUiCase(batch ? selectedRowKeys.value : record.id)
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

  function onPublicationChange(record: any, target: 'prepublished' | 'published' | 'unpublished') {
    if (target === 'published') {
      if (record.publication_status !== 'prepublished') {
        Message.warning('只有预发布状态的用例可以进入发布审核')
        return
      }
      void publicationReviewRef.value?.open('ui', [Number(record.id)])
      return
    }
    if (target !== 'unpublished' && record.status !== 1) {
      Message.warning('用例必须执行通过后才能提交预发布或正式发布')
      return
    }
    const title = target === 'prepublished' ? '提交预发布' : '退回未发布'
    Modal.confirm({
      title,
      content: target === 'prepublished' ? '提交后由项目产品负责人审核，预发布用例不参与定时执行。确认提交吗？'
        : '退回后该用例不再参与定时执行。确认退回吗？',
      cancelText: '取消',
      okText: title,
      okButtonProps: target === 'unpublished' ? { status: 'danger' } : undefined,
      onBeforeOk: async () => {
        publicationActionCaseId.value = record.id
        try {
          const res = await putUiCasePublication(record.id, target)
          Message.success(res.msg)
          doRefresh()
          return true
        } finally {
          publicationActionCaseId.value = null
        }
      },
    })
  }

  function onUpdate(item: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = item[it.key]
        if (it.key === 'scenario_layer' && (propName === undefined || propName === null)) {
          it.value = 0
        } else if (Array.isArray(propName)) {
          it.value = propName
        } else if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
        } else {
          it.value = propName
        }
      })
    })
  }

  const onCaseRun = async (param) => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (caseRunning.value) return
    caseRunning.value = true
    try {
      const res = await getUiCaseRun(param, userStore.selected_environment)
      Message.loading(res.msg)
    } catch (e) {
    } finally {
      caseRunning.value = false
      doRefresh()
    }
  }

  function onConcurrency(name: string) {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (selectedRowKeys.value.length === 0) {
      Message.error('请选择要' + name + '的用例数据')
      return
    }
    if (!validateSingleProject()) return
    Modal.confirm({
      title: '提示',
      content: '确定要' + name + '这些用例吗？批量执行会生成多个浏览器来执行用例',
      cancelText: '取消',
      okText: '执行',
      onBeforeOk: () => {
        return postUiRunCaseBatch(selectedRowKeys.value, userStore.selected_environment)
          .then((res) => {
            Message.success(res.msg)
            selectedRowKeys.value = []
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  const handleClick = () => {
    if (selectedRowKeys.value.length === 0) {
      Message.error('请选择要添加定时任务的用例')
      return
    }
    data.scheduledProjectProduct = null
    data.scheduledModule = '__all__'
    data.scheduledName = []
    data.value = null
    data.visible = true
  }
  const handleOk = () => {
    if (!getOptionId(data.scheduledProjectProduct)) {
      Message.warning('请选择项目产品')
      return
    }
    if (!data.value) {
      Message.warning('请选择定时任务')
      return
    }
    postSystemTasksBatchSetCases(selectedRowKeys.value, data.value, 0)
      .then((res) => {
        Message.success(res.msg)
        data.visible = false
        doRefresh()
      })
      .catch(console.log)
  }
  const handleCancel = () => {
    data.visible = false
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(formItems)
      value['scenario_tags'] = value['scenario_tags'] || []
      if (data.isAdd) {
        value['front_custom'] = []
        value['front_sql'] = []
        value['posterior_sql'] = []
        value['front_public'] = []
        value['front_auth_config'] = []
        value['scenario_layer'] = value['scenario_layer'] ?? 0
        postUiCase(value)
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
        putUiCase(value)
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

  function getNickName() {
    getUserName()
      .then((res) => {
        data.userList = res.data
      })
      .catch(console.log)
  }

  function onClick(record: any) {
    const pageData = usePageData()
    pageData.setRecord(record)
    router.push({
      path: '/uitest/case/details',
      query: {
        id: parseInt(record.id, 10),
      },
    })
  }

  function clickSuite(record: any) {
    data.row = JSON.parse(JSON.stringify(record))

    if (
      !data.row.parametrize ||
      !Array.isArray(data.row.parametrize) ||
      data.row.parametrize.length === 0
    ) {
      data.row.parametrize = [
        {
          name: '',
          parametrize: [{ key: '', value: '', test_envs: [] }],
        },
      ]
    }

    data.drawerVisible = true
  }

  function drawerOk(paramData: any) {
    data.drawerVisible = false

    const hasValidData = paramData.some(
      (suite: any) => suite.name || suite.parametrize.some((param: any) => param.key || param.value)
    )

    let value = {
      id: data.row.id,
      parametrize: hasValidData ? paramData : [],
    }

    putUiCase(value)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function caseCody(record: any) {
    postUiCaseCopy(record.id)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function scheduledName(projectProductId: number | string, moduleId?: number | string | null) {
    data.scheduledNameLoading = true
    getSystemTasksName(projectProductId, moduleId, 0)
      .then((res) => {
        data.scheduledName = res.data
      })
      .catch(console.log)
      .finally(() => {
        data.scheduledNameLoading = false
      })
  }

  function onScheduledProjectProductChange(value: any) {
    const projectProductId = getOptionId(value)
    data.scheduledModule = '__all__'
    data.value = null
    data.scheduledName = []
    if (projectProductId) scheduledName(projectProductId)
  }

  function onScheduledModuleChange(value: any) {
    const projectProductId = getOptionId(data.scheduledProjectProduct)
    const selectedModuleId = getOptionId(value)
    const moduleId = selectedModuleId === '__all__' ? null : selectedModuleId
    data.value = null
    data.scheduledName = []
    if (projectProductId) scheduledName(projectProductId, moduleId)
  }

  onMounted(() => {
    const routeStatus = route.query.publication_status
    if (typeof routeStatus === 'string' && publicationTabs.some((tab) => tab.key === routeStatus)) {
      activePublicationStatus.value = routeStatus
    }
    if (route.query.project_product) {
      setItemValue(conditionItems, 'project_product', Number(route.query.project_product))
    }
    nextTick(async () => {
      await getNickName()
      doRefresh()
    })
  })
  onUnmounted(() => {
    clearPollingTimer()
  })
</script>
