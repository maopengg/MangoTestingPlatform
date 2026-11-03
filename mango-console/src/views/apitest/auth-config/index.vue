<template>
  <TableBody ref="tableBody" plain class="mango-api-resource-page mango-detail-workbench-page">
    <template #header>
      <TableHeader title="Token授权管理" />
    </template>

    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
          contained-body
          :model-value="projectProductCondition?.value"
          :reset-key="sidebarResetKey"
          @filter-change="onSidebarFilterChange"
          @search="onSearchRefresh"
          @reset-search="onResetSearch"
        >
          <template #search>
              <ApiResourceSearchFilters
                :items="headerConditionItems"
                :field-names="fieldNames"
                :enum-store="enumStore"
                :user-list="data.userList"
                @search="onSearchRefresh"
                @reset="onResetSearch"
              />
          </template>
          <template #toolbar>
          <div>
            <a-space>
              <a-button  size="small" type="primary" @click="onAdd" data-testid="qa-views-apitest-auth-config-button-新增">新增</a-button>
              <a-button  size="small" status="danger" @click="onDelete(null)" data-testid="qa-views-apitest-auth-config-button-批量删除">批量删除</a-button>
            </a-space></div
          >
          </template>
      <a-table
        class="mango-native-scroll-table"
        :scroll="{ x: tableScrollX, y: '100%' }"
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
            <template v-else-if="item.key === 'test_env'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.test_env]" size="small">
                {{ enumStore.environment_type.find((item) => String(item.key) === String(record.test_env))?.title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'auth_type'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.auth_type]" size="small">
                {{ enumStore.api_auth_type[record.auth_type]?.title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'auth_source'" #cell="{ record }">
              <a-tooltip :content="getAuthSourceText(record)">
                <div class="auth-source-text">
                  {{ getAuthSourceText(record) }}
                </div>
              </a-tooltip>
            </template>
            <template v-else-if="item.key === 'target_address'" #cell="{ record }">
              {{ record.target_address || '默认地址' }}
            </template>
            <template v-else-if="item.key === 'refresh_mode'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.refresh_mode]" size="small">
                {{ enumStore.api_auth_refresh_mode[record.refresh_mode]?.title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'time_task'" #cell="{ record }">
              <a-tooltip :content="getRefreshStrategyText(record)">
                <div class="auth-source-text">
                  {{ getRefreshStrategyText(record) }}
                </div>
              </a-tooltip>
            </template>
            <template v-else-if="item.key === 'last_refresh_status'" #cell="{ record }">
              <a-tag :color="authRefreshStatusColor(record.last_refresh_status)" size="small">
                {{ enumStore.api_auth_refresh_status[record.last_refresh_status]?.title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-switch
                :beforeChange="(newValue) => onModifyStatus(newValue, record.id)"
                :default-checked="record.status === 1"
              />
            </template>
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ formatProjectProductPath(record.project_product) }}
            </template>
            <template v-else-if="item.key === 'update_user'" #cell="{ record }">
              {{ record.update_user?.name || '-' }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
    { label: '查看', onClick: () => onPreview(record) },
    { label: '自定义代码', hidden: record.auth_type !== 1, overflow: true, onClick: () => onViewCustomCode(record) },
    { label: '刷新', onClick: () => onRefresh(record) },
    { label: '编辑', onClick: () => onUpdate(record) },
    { label: '清空', onClick: () => onClear(record) },
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

  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" :width="760" class="mango-auth-modal" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel" layout="horizontal" class="mango-auth-form">
        <section v-for="section of authFormGroups" :key="section.key" class="mango-auth-form-section">
          <header class="mango-section-title mango-auth-form-section__header">
            <h3 class="mango-section-heading">{{ section.title }}</h3>
            <span class="mango-section-description">{{ section.description }}</span>
          </header>
          <div class="mango-auth-form-section__fields">
        <a-form-item
          v-for="item of section.items"
          :key="item.key"
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require',
            { 'mango-auth-form-item--wide': ['name', 'target_address', 'public_variable_ids', 'custom_code', 'notice_group'].includes(item.key) }]"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
          <template v-else-if="item.type === 'number'">
            <a-input-number
              v-model="item.value"
              :min="item.min ?? 0"
              :placeholder="item.placeholder"
            />
          </template>
          <template v-else-if="item.type === 'cascader'">
            <ProjectProductSelect
              v-model="item.value"
              :placeholder="item.placeholder"
              @change="item.key === 'project_product' ? onFormProjectProductChange() : undefined"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'test_env'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :field-names="fieldNames"
              :options="enumStore.environment_type"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
              @change="onAuthVariableContextChange"
            />
          </template>
          <template v-else-if="item.key === 'target_address'">
            <div class="mango-auth-variable-field">
              <a-select v-model="item.value" :options="targetOptions" :loading="targetsLoading"
                :disabled="!projectProductItem?.value || authEnvironment == null || authEnvironment === ''"
                :placeholder="item.placeholder" allow-clear allow-search @clear="item.value = ''" />
              <div class="mango-auth-variable-hint">留空使用被测对象的默认地址，仅在请求地址匹配时加载授权。</div>
            </div>
          </template>
          <template v-else-if="item.key === 'public_variable_ids'">
            <div class="mango-auth-variable-field">
              <a-select
                v-model="item.value"
                :options="publicVariableOptions"
                :loading="publicVariablesLoading"
                :disabled="!projectProductItem?.value || authEnvironment == null || authEnvironment === ''"
                :placeholder="item.placeholder"
                multiple allow-clear allow-search :filter-option="false"
                @search="loadPublicVariableOptions"
              />
              <div class="mango-auth-variable-hint">仅用于准备认证上下文，同 key 覆盖默认值；Case 仍须选择匹配的变量，不会自动切换租户。</div>
            </div>
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'auth_type'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :field-names="fieldNames"
              :options="enumStore.api_auth_type"
              :placeholder="item.placeholder"
              allow-clear
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'api_info'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :options="data.apiInfoList"
              :loading="apiInfoLoading"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'refresh_mode'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :field-names="fieldNames"
              :options="enumStore.api_auth_refresh_mode"
              :placeholder="item.placeholder"
              allow-clear
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'time_task'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :options="data.timeTaskList"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'notice_group'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :options="data.noticeList"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'code'">
            <CodeEditor
              v-model="item.value"
              :line-height="220"
              :placeholder="item.placeholder"
              :code-style="{ width: '100%' }"
            />
          </template>
        </a-form-item>
          </div>
        </section>
      </a-form>
    </template>
  </ModalDialog>

  <BaseSidePanel
    v-model:visible="customCodePanel.visible"
    :title="customCodePanel.title"
    :width="1000"
    :show-footer="false"
  >
    <div v-if="customCodePanel.visible" class="mango-auth-custom-code-panel">
      <CodeEditor
        :model-value="customCodePanel.code"
        language="python"
        readonly
        placeholder="暂无自定义授权代码"
        :code-style="{ height: '100%' }"
      />
      <section class="mango-auth-custom-code-result">
        <div class="mango-auth-custom-code-result-header">
          <span>执行结果</span>
          <a-button

            type="primary"
            size="small"
            :loading="customCodeRunningIds.has(customCodePanel.id)"
            @click="onRunCustomCode"
          >刷新/执行</a-button>
        </div>
        <MangoPanelSpin :loading="customCodeRunningIds.has(customCodePanel.id)" class="mango-auth-custom-code-result-body">
          <a-alert v-if="customCodePanel.error" type="error">{{ customCodePanel.error }}</a-alert>
          <JsonDisplay v-else-if="customCodePanel.result !== null" :data="customCodePanel.result" :show-toolbar="false" />
          <div v-else class="mango-empty-state">点击“刷新/执行”刷新授权，结果将在此展示。</div>
        </MangoPanelSpin>
      </section>
    </div>
  </BaseSidePanel>

  <a-drawer
    v-model:visible="cacheModal.visible"
    title="授权缓存"
    width="50%"
    :footer="false"
    unmount-on-close
  >
    <div class="cache-drawer-body">
      <a-descriptions v-if="cacheModal.data" :column="1" bordered>
        <a-descriptions-item label="授权名称">{{ cacheModal.data.name }}</a-descriptions-item>
        <a-descriptions-item label="过期时间">{{
          cacheModal.data.expires_at || '-'
        }}</a-descriptions-item>
        <a-descriptions-item label="剩余分钟">{{
          cacheModal.data.remaining_minutes ?? '-'
        }}</a-descriptions-item>
        <a-descriptions-item label="最近刷新时间">
          {{ cacheModal.data.last_refresh_time || '-' }}
        </a-descriptions-item>
        <a-descriptions-item label="最近错误">
          {{ cacheModal.data.last_refresh_error || '-' }}
        </a-descriptions-item>
      </a-descriptions>
      <div v-if="cacheModal.data" class="cache-json-section">
        <div class="cache-json-title">缓存数据</div>
        <JsonDisplay :data="cacheModal.data.cache_data || {}" />
      </div>
    </div>
  </a-drawer>
</template>

<script lang="ts" setup>
  import { formatProjectProductPath, getOptionId } from '@/utils/business-format'
  import { AUTH_REFRESH_STATUS_COLORS, getStatusTagColor } from '@/utils/status-color'
  import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { ModalDialogType } from '@/types/components'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import ApiResourceSearchFilters from '@/components/business/ApiResourceSearchFilters.vue'
  import { getApiInfoOptions } from '@/api/apitest/info'
  import { getSystemTimingList } from '@/api/system/time'
  import { getSystemNoticeName } from '@/api/system/notice_group'
  import { getUserName } from '@/api/user/user'
  import { conditionItems, formItems, authFormSections, tableColumns, tableScrollX } from './config'
  import {
    deleteApiAuthConfig,
    getApiAuthConfig,
    getApiAuthPublicVariables,
    getApiAuthTargets,
    getApiAuthConfigCache,
    postApiAuthConfig,
    postApiAuthConfigClear,
    postApiAuthConfigRefresh,
    putApiAuthConfig,
    putApiAuthConfigStatus,
  } from '@/api/apitest/auth-config'
  import { prefillNavigationFormItems, NavigationCreateSource } from '@/utils/navigation-create-defaults'

  const navigationCreateRef = ref<NavigationCreateSource | null>(null)

  const enumStore = useEnum()
  const route = useRoute()
  const authRefreshStatusColor = (value: number) =>
    getStatusTagColor(AUTH_REFRESH_STATUS_COLORS, value)
  const headerConditionItems = computed(() => conditionItems.filter((item) => item.key !== 'project_product'))
  const projectProductCondition = computed(() => conditionItems.find((item) => item.key === 'project_product'))
  const sidebarResetKey = ref(0)

  function onSidebarFilterChange({ projectProduct }: { projectProduct: string | number | null }) {
    if (projectProductCondition.value) projectProductCondition.value.value = projectProduct
    selectedRowKeys.value = []
    pagination.page = 1
    doRefresh(true)
  }
  const userStore = useUserStore()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const { beginRequest, isLatestRequest } = useLatestRequest()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const data = reactive({
    actionTitle: '新增',
    isAdd: false,
    updateId: 0,
    apiInfoList: [] as any[],
    timeTaskList: [] as any[],
    noticeList: [] as any[],
    userList: [] as any[],
  })
  const cacheModal = reactive({
    visible: false,
    data: null as any,
  })
  const publicVariableOptions = ref<Array<{ label: string; value: number }>>([])
  const publicVariablesLoading = ref(false)
  const authEnvironment = computed(() => formItems.find(item => item.key === 'test_env')?.value)
  let publicVariableRequest = 0
  const targetOptions = ref<Array<{ label: string; value: string }>>([])
  const targetsLoading = ref(false)
  const apiInfoLoading = ref(false)
  let apiInfoRequest = 0
  let targetRequest = 0

  async function loadTargetOptions() {
    const request = ++targetRequest
    const product = getOptionId(projectProductItem.value?.value)
    const env = authEnvironment.value
    targetOptions.value = []
    if (!product || env == null || env === '') {
      targetsLoading.value = false
      return
    }
    targetsLoading.value = true
    try {
      const res = await getApiAuthTargets({ project_product: product, test_env: env })
      if (request === targetRequest) targetOptions.value = res.data || []
    } catch {
      if (request === targetRequest) targetOptions.value = []
    } finally {
      if (request === targetRequest) targetsLoading.value = false
    }
  }

  async function loadPublicVariableOptions(keyword = '') {
    const request = ++publicVariableRequest
    const product = projectProductItem.value?.value
    const env = authEnvironment.value
    if (!product || env == null || env === '') {
      publicVariableOptions.value = []
      publicVariablesLoading.value = false
      return
    }
    publicVariablesLoading.value = true
    try {
      const res = await getApiAuthPublicVariables({ project_product: getOptionId(product), test_env: env,
        keyword, page: 1, pageSize: 200 })
      if (request !== publicVariableRequest) return
      const selected = formItems.find(item => item.key === 'public_variable_ids')?.value || []
      const options = publicVariableOptions.value.filter(item => selected.includes(item.value))
      const merged = new Map(options.map(item => [item.value, item]))
      for (const item of res.data || []) merged.set(item.id, { value: item.id, label: `${item.name} / ${item.key} (#${item.id})` })
      publicVariableOptions.value = [...merged.values()]
    } catch {
      if (request === publicVariableRequest) publicVariableOptions.value = []
    } finally {
      if (request === publicVariableRequest) publicVariablesLoading.value = false
    }
  }

  function onAuthVariableContextChange() {
    const target = formItems.find(item => item.key === 'target_address')
    if (target) target.value = ''
    void loadTargetOptions()
    const item = formItems.find(item => item.key === 'public_variable_ids')
    if (item) item.value = []
    publicVariableOptions.value = []
    void loadPublicVariableOptions()
  }
  const customCodePanel = reactive({
    visible: false, title: '自定义代码', code: '', id: 0,
    result: null as Record<string, any> | null, error: '', version: 0,
  })
  const customCodeRunningIds = reactive(new Set<number>())

  function onViewCustomCode(record: any) {
    if (record.auth_type !== 1) return
    customCodePanel.version += 1
    customCodePanel.id = record.id
    customCodePanel.result = null
    customCodePanel.error = ''
    customCodePanel.title = `自定义代码 / ${record.name}`
    customCodePanel.code = record.custom_code || ''
    customCodePanel.visible = true
  }

  async function onRunCustomCode() {
    const { id, version } = customCodePanel
    if (!customCodePanel.visible || !id || customCodeRunningIds.has(id)) return
    customCodeRunningIds.add(id)
    customCodePanel.result = null
    customCodePanel.error = ''
    const isCurrent = () => customCodePanel.visible && customCodePanel.id === id && customCodePanel.version === version
    try {
      const response = await postApiAuthConfigRefresh(id)
      if (isCurrent()) customCodePanel.result = response.data
    } catch (error) {
      if (isCurrent()) customCodePanel.error = error instanceof Error ? error.message : '授权刷新失败，请稍后重试'
    } finally {
      customCodeRunningIds.delete(id)
      void doRefresh()
    }
  }
  const customAuthCodeExample = `def auth(context):
    """
    函数名字，参数都不可以改。
    必须返回 dict。
    dict 的 key 会作为缓存 key，value 会作为缓存值。
    接口执行时可以通过 \${token}、\${tenant_id} 引用。
    """
    # 租户、用户等认证条件从 context.test_data 读取，关联公共变量已提前加载。
    return {"token": "your_token"}`

  const authTypeItem = computed(() => formItems.find((it) => it.key === 'auth_type'))
  const refreshModeItem = computed(() => formItems.find((it) => it.key === 'refresh_mode'))
  const projectProductItem = computed(() => formItems.find((it) => it.key === 'project_product'))
  const isExecutionCheckRefreshMode = computed(() => [0, 2].includes(refreshModeItem.value?.value))
  const visibleFormItems = computed(() => {
    return formItems.filter((it) => {
      if (it.key === 'api_info') {
        return authTypeItem.value?.value === 0
      }
      if (it.key === 'custom_code') {
        return authTypeItem.value?.value === 1
      }
      if (it.key === 'token_ttl') {
        return [0, 2, 4].includes(refreshModeItem.value?.value)
      }
      if (it.key === 'refresh_margin') {
        return isExecutionCheckRefreshMode.value
      }
      if (it.key === 'expire_notice_minutes' || it.key === 'notice_group') {
        return refreshModeItem.value?.value === 4
      }
      if (it.key === 'time_task') {
        return [1, 2].includes(refreshModeItem.value?.value)
      }
      return true
    })
  })
  const authFormGroups = computed(() => {
    const items = new Map(visibleFormItems.value.map(item => [item.key, item]))
    return authFormSections.map(section => ({
      ...section,
      items: section.itemKeys.flatMap(key => {
        const item = items.get(key)
        return item ? [item] : []
      }),
    })).filter(section => section.items.length)
  })

  function onSearchRefresh() {
    pagination.page = 1
    doRefresh(true)
  }

  function doRefresh(showLoading = false) {
    const requestId = beginRequest()
    if (showLoading) {
      table.tableLoading.value = true
    }
    const value = getFormItems(conditionItems)
    clearEmptyFilter(value, 'name')
    clearEmptyFilter(value, 'test_env')
    clearEmptyFilter(value, 'auth_type')
    clearEmptyFilter(value, 'refresh_mode')
    clearEmptyFilter(value, 'last_refresh_status')
    clearEmptyFilter(value, 'update_user')
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    return getApiAuthConfig(value)
      .then((res) => {
        if (!isLatestRequest(requestId)) return
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
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

  function clearEmptyFilter(value: Record<string, any>, key: string) {
    if (value[key] === null || value[key] === '' || value[key] === undefined) {
      delete value[key]
    }
  }

  function refreshTable() {
    selectedRowKeys.value = []
    return doRefresh()
  }

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = it.multiple ? [] : ''
    })
    sidebarResetKey.value += 1
    pagination.page = 1
    doRefresh(true)
  }

  function applyRouteIdFilter(value: unknown) {
    const routeValue = Array.isArray(value) ? value[0] : value
    const idCondition = conditionItems.find((item) => item.key === 'id')
    if (idCondition) idCondition.value = typeof routeValue === 'string' ? routeValue : ''
  }

  function resetFormItems() {
    targetRequest++
    targetOptions.value = []
    targetsLoading.value = false
    publicVariableRequest++
    publicVariableOptions.value = []
    publicVariablesLoading.value = false
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else if (it.key === 'auth_type' || it.key === 'refresh_mode') {
        it.value = 0
      } else if (it.key === 'token_ttl') {
        it.value = 1440
      } else if (it.key === 'refresh_margin') {
        it.value = 10
      } else if (it.key === 'expire_notice_minutes') {
        it.value = 30
      } else if (it.key === 'custom_code') {
        it.value = customAuthCodeExample
      } else {
        it.value = it.multiple ? [] : ''
      }
    })
    const envItem = formItems.find((it) => it.key === 'test_env')
    if (envItem && userStore.selected_environment != null) {
      envItem.value = userStore.selected_environment
    }
    data.apiInfoList = []
    data.noticeList = []
  }

  function onAdd() {
    data.actionTitle = '新增'
    data.isAdd = true
    resetFormItems()
    modalDialogRef.value?.toggle()
    void prefillNavigationFormItems(navigationCreateRef.value, formItems, () => data.isAdd)
      .then(() => {
        if (!data.isAdd) return
        onFormProjectProductChange()
        return loadTargetOptions()
      })
  }

  function fillCustomCodeExample() {
    const customCodeItem = formItems.find((it) => it.key === 'custom_code')
    if (customCodeItem && !customCodeItem.value) {
      customCodeItem.value = customAuthCodeExample
    }
  }

  function onUpdate(item: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = item[it.key]
        if (it.key === 'public_variable_ids' && !Array.isArray(propName)) {
          it.value = []
          return
        }
        if (Array.isArray(propName)) {
          it.value = [...propName]
        } else if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
        } else {
          it.value = propName
        }
      })
      getApiInfoList(item.project_product?.id || item.project_product)
      getNoticeList(item.project_product?.id || item.project_product)
      publicVariableOptions.value = []
      void loadPublicVariableOptions()
      void loadTargetOptions()
    })
  }

  function onFormProjectProductChange() {
    nextTick(() => {
      onAuthVariableContextChange()
      const apiInfoItem = formItems.find((it) => it.key === 'api_info')
      if (apiInfoItem) {
        apiInfoItem.value = ''
      }
      const noticeItem = formItems.find((it) => it.key === 'notice_group')
      if (noticeItem) {
        noticeItem.value = ''
      }
      getApiInfoList(projectProductItem.value?.value)
      getNoticeList(projectProductItem.value?.value)
    })
  }

  function validateVisibleForm() {
    const authType = authTypeItem.value?.value
    const refreshMode = refreshModeItem.value?.value
    if (authType === 0 && !formItems.find((it) => it.key === 'api_info')?.value) {
      Message.error('请选择登录接口')
      return false
    }
    if (authType === 1 && !formItems.find((it) => it.key === 'custom_code')?.value) {
      Message.error('请输入自定义授权代码')
      return false
    }
    if ([1, 2].includes(refreshMode) && !formItems.find((it) => it.key === 'time_task')?.value) {
      Message.error('请选择定时策略')
      return false
    }
    if (refreshMode === 4 && !formItems.find((it) => it.key === 'notice_group')?.value) {
      Message.error('请选择通知组')
      return false
    }
    return visibleFormItems.value.every((it) => (it.validator ? it.validator() : true))
  }

  function normalizeSubmitValue(value: any) {
    value.target_address = value.target_address ?? ''
    value.public_variable_ids = value.public_variable_ids ?? []
    if (value.auth_type === 0) {
      value.custom_code = null
    } else {
      value.api_info = null
    }
    if (![1, 2].includes(value.refresh_mode)) {
      value.time_task = null
    }
    if (value.refresh_mode !== 4) {
      value.notice_group = null
    }
    return value
  }

  function getAuthSourceText(record: any) {
    if (record.auth_type === 0) {
      const apiInfo = record.api_info
      if (!apiInfo) return '-'
      return `ID：${apiInfo.id ?? '-'} / 名称：${apiInfo.name || '-'}`
    }
    if (record.auth_type === 1) {
      return record.custom_code || '-'
    }
    return '-'
  }

  function getRefreshStrategyText(record: any) {
    const tokenStrategy = `有效期${record.token_ttl ?? '-'}分钟，提前${record.refresh_margin ?? '-'}分钟刷新`
    const timeTaskStrategy = record.time_task?.name ? `定时策略：${record.time_task.name}` : '定时策略：-'
    if (record.refresh_mode === 0) {
      return tokenStrategy
    }
    if (record.refresh_mode === 1) {
      return timeTaskStrategy
    }
    if (record.refresh_mode === 2) {
      return `${timeTaskStrategy}；${tokenStrategy}`
    }
    if (record.refresh_mode === 3) {
      return '手动刷新（永久有效）'
    }
    if (record.refresh_mode === 4) {
      const tokenStrategy = `有效期${record.token_ttl ?? '-'}分钟，提前${record.expire_notice_minutes ?? '-'}分钟通知`
      const noticeGroup = record.notice_group?.name ? `通知组：${record.notice_group.name}` : '通知组：-'
      return `${tokenStrategy}；${noticeGroup}`
    }
    return '-'
  }

  function onDataForm() {
    if (!validateVisibleForm()) {
      modalDialogRef.value?.setConfirmLoading(false)
      return
    }
    const value = normalizeSubmitValue(getFormItems(formItems))
    if (data.isAdd) {
      value['status'] = 1
      postApiAuthConfig(value)
        .then((res) => {
          modalDialogRef.value?.toggle()
          Message.success(res.msg)
          refreshTable()
        })
        .catch(console.log)
        .finally(() => modalDialogRef.value?.setConfirmLoading(false))
    } else {
      value['id'] = data.updateId
      putApiAuthConfig(value)
        .then((res) => {
          modalDialogRef.value?.toggle()
          Message.success(res.msg)
          refreshTable()
        })
        .catch(console.log)
        .finally(() => modalDialogRef.value?.setConfirmLoading(false))
    }
  }

  function onDelete(record: any) {
    const batch = record === null
    if (batch && selectedRowKeys.value.length === 0) {
      Message.error('请选择要删除的数据')
      return
    }
    Modal.confirm({
      title: '提示',
      content: '是否要删除此授权配置？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteApiAuthConfig(batch ? selectedRowKeys.value : record.id)
          .then((res) => Message.success(res.msg))
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

  function onPreview(record: any) {
    getApiAuthConfigCache(record.id)
      .then((res) => {
        cacheModal.data = res.data
        cacheModal.visible = true
      })
      .catch(console.log)
  }

  function onRefresh(record: any) {
    postApiAuthConfigRefresh(record.id)
      .then((res) => {
        Message.success(res.msg)
        cacheModal.data = res.data
        cacheModal.visible = true
        doRefresh()
      })
      .catch(console.log)
  }

  function onClear(record: any) {
    postApiAuthConfigClear(record.id)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  const onModifyStatus = async (newValue: boolean, id: number) => {
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value: any = false
          await putApiAuthConfigStatus(id, newValue ? 1 : 0)
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

  async function getApiInfoList(projectProductId?: any) {
    const request = ++apiInfoRequest
    data.apiInfoList = []
    apiInfoLoading.value = false
    if (!projectProductId) {
      return
    }
    apiInfoLoading.value = true
    try {
      const items = await getApiInfoOptions(projectProductId, () => request === apiInfoRequest)
      if (request !== apiInfoRequest) return
      data.apiInfoList = items.map((item: any) => ({
          label: `${item.id} - ${item.name}`,
          value: item.id,
      }))
    } catch (error) {
      console.log(error)
    } finally {
      if (request === apiInfoRequest) apiInfoLoading.value = false
    }
  }

  function getTiming() {
    getSystemTimingList()
      .then((res) => {
        data.timeTaskList = (res.data || []).map((item: any) => ({
          label: item.title,
          value: item.key,
        }))
      })
      .catch(console.log)
  }

  function getNoticeList(projectProductId?: any) {
    if (!projectProductId) {
      data.noticeList = []
      return
    }
    getSystemNoticeName(projectProductId)
      .then((res) => {
        data.noticeList = res.data || []
      })
      .catch(console.log)
  }

  function getNickName() {
    getUserName()
      .then((res) => {
        data.userList = res.data
      })
      .catch(console.log)
  }

  watch(
    () => authTypeItem.value?.value,
    (value) => {
      if (value === 1) {
        fillCustomCodeExample()
      }
    }
  )

  watch(
    () => route.query.id,
    (value) => {
      applyRouteIdFilter(value)
      pagination.page = 1
      doRefresh(true)
    }
  )

  onMounted(() => {
    if (projectProductCondition.value) projectProductCondition.value.value = ''
    applyRouteIdFilter(route.query.id)
    nextTick(() => {
      getTiming()
      doRefresh()
      getNickName()
    })
  })
</script>

<style scoped>
  :global(.mango-auth-modal .mango-scrollbar),
  :global(.mango-auth-modal .mango-modal-dialog__wrap) {
    height: auto;
  }

  .mango-auth-form {
    container-type: inline-size;
  }

  .mango-auth-form-section {
    padding: 14px 0;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-auth-form-section:first-child { padding-top: 0; }
  .mango-auth-form-section:last-child { padding-bottom: 0; border-bottom: 0; }

  .mango-auth-form-section__header {
    align-items: baseline;
    justify-content: flex-start;
    flex-wrap: wrap;
    gap: var(--m-page-gap);
    margin-bottom: 12px;
  }

  .mango-auth-form-section__fields {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px 16px;
  }

  .mango-auth-form-section__fields :deep(.arco-form-item) {
    flex-wrap: nowrap;
    min-width: 0;
    margin-bottom: 0;
  }

  .mango-auth-form-section__fields :deep(.arco-form-item-label-col) {
    flex: 0 0 136px;
    width: 136px;
    max-width: 136px;
    white-space: nowrap;
  }

  .mango-auth-form-section__fields :deep(.arco-form-item-label-col > label) { white-space: nowrap; }

  .mango-auth-form-section__fields :deep(.arco-form-item-wrapper-col) {
    flex: 1 1 0;
    width: 0;
    max-width: none;
    min-width: 0;
  }

  .mango-auth-form-item--wide { grid-column: 1 / -1; }

  @container (max-width: 640px) {
    .mango-auth-form-section__fields { grid-template-columns: minmax(0, 1fr); }
  }

  .mango-auth-variable-field { width: 100%; min-width: 0; }
  .mango-auth-variable-hint { margin-top: 4px; color: var(--m-muted); font-size: 12px; }
  .mango-auth-custom-code-panel {
    display: grid;
    grid-template-rows: minmax(0, 7fr) minmax(0, 3fr);
    gap: var(--m-page-gap);
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .mango-auth-custom-code-result {
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
  }

  .mango-auth-custom-code-result-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--m-page-gap);
    padding-bottom: var(--m-page-gap);
    color: var(--m-text);
    font-weight: 500;
  }

  .mango-auth-custom-code-result-body {
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  .mango-auth-custom-code-result-body :deep(> .mango-panel-spin__content) {
    height: 100%;
    overflow: auto;
  }

  .cache-drawer-body {
    height: 100%;
    overflow: auto;
  }

  .cache-json-section {
    margin-top: 16px;
  }

  .cache-json-title {
    margin-bottom: 8px;
    color: var(--m-text);
    font-weight: 500;
  }

  .auth-source-text {
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
