<template>
  <TableBody plain class="mango-detail-workbench-page">
    <template #header>
      <TableHeader title="UI授权管理" />
    </template>

    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
        :model-value="query.project_product"
        :reset-key="sidebarResetKey"
        @filter-change="onNavigationFilterChange"
        @search="onSearchRefresh"
        @reset-search="onReset"
      >
        <template #search>
          <ApiResourceSearchFilters
            :items="conditionItems"
            :field-names="fieldNames"
            :enum-store="enumStore"
            :user-list="userOptions"
            :option-overrides="{
              auth_type: enumStore.ui_auth_type,
              refresh_mode: enumStore.ui_auth_refresh_mode,
              last_refresh_status: enumStore.ui_auth_refresh_status,
            }"
            @search="onSearchRefresh"
            @reset="onReset"
          />
        </template>
        <template #toolbar>
        <a-button  size="small" type="primary" @click="onAdd" data-testid="qa-views-uitest-auth-config-button-新增">新增</a-button>
        </template>
      <a-table
        class="mango-native-scroll-table"
        :bordered="false"
        :columns="columns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :scroll="{ x: tableScrollX, y: '100%' }"
        row-key="id"
      >
        <template #columns>
          <a-table-column v-for="item in columns" :key="item.key" v-bind="item">
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'test_env'" #cell="{ record }">
              <a-tag
                v-if="record.test_env !== null && record.test_env !== undefined"
                :color="enumStore.colors[record.test_env]"
                size="small"
              >
                {{ enumStore.environment_type.find((item) => String(item.key) === String(record.test_env))?.title || `环境${record.test_env}` }}
              </a-tag>
              <span v-else>-</span>
            </template>
            <template v-else-if="item.key === 'auth_type'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.auth_type]" size="small">
                {{ enumStore.ui_auth_type[record.auth_type]?.title || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'auth_config'" #cell="{ record }">
              <a-tooltip :content="getAuthConfigText(record)">
                <div class="mango-auth-table-summary">
                  {{ getAuthConfigText(record) }}
                </div>
              </a-tooltip>
            </template>
            <template v-else-if="item.key === 'refresh_mode'" #cell="{ record }">
              <span v-if="record.auth_type === 3">-</span>
              <a-tag v-else :color="enumStore.colors[record.refresh_mode]" size="small">
                {{ enumStore.ui_auth_refresh_mode[record.refresh_mode]?.title || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'refresh_strategy'" #cell="{ record }">
              <a-tooltip :content="getRefreshStrategyText(record)">
                <div class="mango-auth-table-summary">
                  {{ getRefreshStrategyText(record) }}
                </div>
              </a-tooltip>
            </template>
            <template v-else-if="item.key === 'token_ttl'" #cell="{ record }">
              {{ record.auth_type === 3 ? '-' : record.token_ttl ?? '-' }}
            </template>
            <template v-else-if="item.key === 'expires_at'" #cell="{ record }">
              {{ record.auth_type === 3 ? '-' : record.expires_at || '-' }}
            </template>
            <template v-else-if="item.key === 'last_refresh_status'" #cell="{ record }">
              <span v-if="record.auth_type === 3">-</span>
              <a-tooltip v-else :content="record.last_refresh_error || ''">
                <a-tag
                  :color="record.refreshing ? 'blue' : authRefreshStatusColor(record.last_refresh_status)"
                  size="small"
                >
                  {{
                    record.refreshing
                      ? '刷新中'
                      : enumStore.ui_auth_refresh_status[record.last_refresh_status]?.title || '-'
                  }}
                </a-tag>
              </a-tooltip>
            </template>
            <template v-else-if="item.key === 'last_refresh_time'" #cell="{ record }">
              {{ record.auth_type === 3 ? '-' : record.last_refresh_time || '-' }}
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-switch
                :before-change="(checked) => onStatusChange(record.id, checked ? 1 : 0)"
                :default-checked="record.status === 1"
                size="small"
              />
            </template>
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ formatProjectProductPath(record.project_product) }}
            </template>
            <template v-else-if="item.key === 'update_user'" #cell="{ record }">
              {{ record.update_user?.name || record.update_user?.username || '-' }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="getAuthActions(record)"
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

  <ModalDialog ref="modalDialogRef" :title="formTitle" @confirm="onSubmit">
    <template #content>
      <a-form ref="formRef" :model="form">
        <a-form-item label="项目/产品" class="mango-form-item__require">
          <ProjectProductSelect v-model="form.project_product" @change="onFormProjectProductChange" />
        </a-form-item>
        <a-form-item
          class="mango-form-item__require"
          field="test_env"
          label="被测环境"
          :rules="[{ required: true, message: '请选择被测环境' }]"
        >
          <a-select
            v-model="form.test_env"
            :field-names="fieldNames"
            :options="environmentOptions"
            allow-clear
            placeholder="请选择被测环境"
            value-key="key" data-testid="qa-views-uitest-auth-config-select-请选择绑定环境"
          />
        </a-form-item>
        <a-form-item label="授权名称" class="mango-form-item__require">
          <a-input v-model="form.name" placeholder="请输入授权名称" data-testid="qa-views-uitest-auth-config-input-请输入授权名称-2" />
        </a-form-item>
        <a-form-item label="授权方式" class="mango-form-item__require">
          <a-select
            v-model="form.auth_type"
            :field-names="fieldNames"
            :options="enabledAuthTypeOptions"
            placeholder="请选择授权方式"
            value-key="key" data-testid="qa-views-uitest-auth-config-select-请选择授权方式-2"
          />
        </a-form-item>
        <a-form-item v-if="form.auth_type === 3" label="页面步骤" class="mango-form-item__require">
          <a-select
            v-model="form.page_step"
            :options="pageStepOptions"
            allow-clear
            allow-search
            placeholder="请选择登录页面步骤" data-testid="qa-views-uitest-auth-config-select-请选择登录页面步骤"
          />
        </a-form-item>
        <a-form-item v-if="form.auth_type === 2" label="登录接口" class="mango-form-item__require">
          <a-select
            v-model="form.api_info"
            :options="apiInfoOptions"
            allow-clear
            allow-search
            placeholder="请选择接口转入的登录接口" data-testid="qa-views-uitest-auth-config-select-请选择接口转入的登录接口"
          />
        </a-form-item>
        <a-form-item v-if="form.auth_type === 0" label="手动缓存 JSON">
          <a-textarea v-model="manualConfigText" :auto-size="{ minRows: 5, maxRows: 10 }" />
        </a-form-item>
        <a-form-item v-if="form.auth_type === 1" label="自动授权配置 JSON">
          <a-textarea v-model="autoConfigText" :auto-size="{ minRows: 5, maxRows: 10 }" />
        </a-form-item>
        <a-form-item v-if="form.auth_type === 2" label="接口转入配置 JSON">
          <a-textarea v-model="apiConfigText" :auto-size="{ minRows: 5, maxRows: 10 }" />
        </a-form-item>
        <a-form-item v-if="form.auth_type !== 3" label="刷新方式">
          <a-select
            v-model="form.refresh_mode"
            :field-names="fieldNames"
            :options="refreshModeOptions"
            value-key="key"
          />
        </a-form-item>
        <a-form-item v-if="form.auth_type === 2 && form.refresh_mode === 1" label="定时策略" class="mango-form-item__require">
          <a-select
            v-model="form.time_task"
            :options="timeTaskOptions"
            allow-clear
            allow-search
            placeholder="请选择定时策略" data-testid="qa-views-uitest-auth-config-select-请选择定时策略"
          />
        </a-form-item>
        <a-form-item v-if="form.auth_type !== 3 && form.refresh_mode === 2" label="通知组" class="mango-form-item__require">
          <a-select
            v-model="form.notice_group"
            :options="noticeOptions"
            allow-clear
            allow-search
            placeholder="请选择到期提醒通知组" data-testid="qa-views-uitest-auth-config-select-请选择到期提醒通知组"
          />
        </a-form-item>
        <a-form-item v-if="form.auth_type !== 3" label="有效期(分钟)">
          <a-input-number v-model="form.token_ttl" :min="1" />
        </a-form-item>
        <a-form-item
          v-if="form.auth_type !== 3 && form.refresh_mode === 2"
          field="expire_notice_minutes"
          label="提前提醒(分钟)"
          :rules="[{ type: 'number', min: 10, message: '提前提醒时间不能少于10分钟' }]"
        >
          <a-input-number v-model="form.expire_notice_minutes" :min="10" />
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>

  <a-modal v-model:visible="cacheModal.visible" title="授权缓存" :footer="false" width="720px">
    <pre class="mango-auth-cache">{{ cacheModal.text }}</pre>
  </a-modal>
</template>

<script setup lang="ts">
  import { computed, onMounted, reactive, ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import TableBody from '@/components/table/TableBody.vue'
  import TableHeader from '@/components/table/TableHeader.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import ModalDialog from '@/components/overlays/ModalDialog.vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import ApiResourceSearchFilters from '@/components/business/ApiResourceSearchFilters.vue'
  import { usePagination, useTable } from '@/hooks/table'
  import { ModalDialogType } from '@/types/components'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import { formatProjectProductPath, getOptionId } from '@/utils/business-format'
  import { AUTH_REFRESH_STATUS_COLORS, getStatusTagColor } from '@/utils/status-color'
  import { conditionItems, tableColumns, tableScrollX } from './config'
  import { getFormItems } from '@/utils/datacleaning'
  import { getUiSteps } from '@/api/uitest/page-steps'
  import { getApiInfo } from '@/api/apitest/info'
  import { getSystemTimingList } from '@/api/system/time'
  import { getSystemNoticeName } from '@/api/system/notice_group'
  import { getUserName } from '@/api/user/user'
  import { getExecutorTask } from '@/api/system/executor-task'
  import {
    clearExecutorTaskObservation,
    loadExecutorTaskObservation,
    saveExecutorTaskObservation,
  } from '@/utils/executor-task-observer.mjs'
  import {
    deleteUiAuthConfig,
    getUiAuthConfig,
    getUiAuthConfigCache,
    postUiAuthConfig,
    postUiAuthConfigAutoCapture,
    postUiAuthConfigAutoStart,
    postUiAuthConfigClear,
    postUiAuthConfigRefresh,
    putUiAuthConfig,
    putUiAuthConfigStatus,
  } from '@/api/uitest/auth-config'
  import type { UiAuthCacheConfig, UiAuthConfigPayload } from '@/types/ui-test/case'
  import { prefillNavigationModel, NavigationCreateSource } from '@/utils/navigation-create-defaults'

  const navigationCreateRef = ref<NavigationCreateSource | null>(null)

  type AuthTableAction = {
    label: string
    onClick: () => void
    danger?: boolean
    loading?: boolean
    disabled?: boolean
  }

  const enumStore = useEnum()
  const authRefreshStatusColor = (value: number) =>
    getStatusTagColor(AUTH_REFRESH_STATUS_COLORS, value)
  const table = useTable()
  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const formRef = ref<any>(null)
  const formTitle = ref('新增授权')
  const editingId = ref<number | null>(null)
  const manualConfigText = ref('{"cookies":[],"local_storage":[],"session_storage":[],"headers":{}}')
  const autoConfigText = ref('{"url":"","cookie_domains":[],"local_storage_keys":[],"session_storage_keys":[],"headers":{},"timeout":300}')
  const apiConfigText = ref('{"api_info":null,"token_path":"$.response.json.data.token","cookie_mapping":{},"local_storage_mapping":[],"session_storage_mapping":[],"header_mapping":{}}')
  const pageStepOptions = ref<any[]>([])
  const apiInfoOptions = ref<any[]>([])
  const timeTaskOptions = ref<any[]>([])
  const noticeOptions = ref<any[]>([])
  const userOptions = ref<any[]>([])
  const sidebarResetKey = ref(0)
  const query = reactive({ project_product: '' })
  const form = reactive<any>({
    project_product: '',
    test_env: '',
    name: '',
    auth_type: 0,
    status: 1,
    page_step: null,
    api_info: null,
    time_task: null,
    notice_group: null,
    refresh_mode: 0,
    token_ttl: 1440,
    expire_notice_minutes: 30,
  })
  const cacheModal = reactive({ visible: false, text: '' })
  const authTaskLoading = reactive<Record<string, boolean>>({})
  const columns = tableColumns
  const environmentOptions = computed(() => enumStore.environment_type)
  const enabledAuthTypeOptions = computed(() =>
    (enumStore.ui_auth_type || []).filter((item: any) => item.key !== 4)
  )
  const refreshModeOptions = computed(() =>
    (enumStore.ui_auth_refresh_mode || []).filter((item: any) => {
      if (form.auth_type === 2) return true
      return item.key !== 1
    })
  )

  function onSearchRefresh() {
    pagination.page = 1
    doRefresh(true)
  }

  function onNavigationFilterChange({ projectProduct }: { projectProduct: any }) {
    query.project_product = projectProduct ?? ''
    pagination.page = 1
    doRefresh(true)
  }

  async function doRefresh(showLoading = false) {
    if (showLoading) {
      table.tableLoading.value = true
    }
    try {
      const res = await getUiAuthConfig({
        page: pagination.page,
        pageSize: pagination.pageSize,
        ...normalizeQuery(),
      })
      table.handleSuccess(res)
      pagination.setTotalSize(res.totalSize || 0)
    } finally {
      if (showLoading) {
        table.tableLoading.value = false
      }
    }
  }

  function onReset() {
    query.project_product = ''
    conditionItems.forEach(item => { item.value = item.multiple ? [] : '' })
    pagination.page = 1
    sidebarResetKey.value += 1
    doRefresh()
  }

  function normalizeQuery() {
    const value: Record<string, any> = {
      ...getFormItems(conditionItems),
      project_product: getOptionId(query.project_product),
    }
    Object.keys(value).forEach(key => clearEmptyFilter(value, key))
    return value
  }

  function clearEmptyFilter(value: Record<string, any>, key: string) {
    if (value[key] === null || value[key] === '' || value[key] === undefined) {
      delete value[key]
    }
  }

  function getAuthConfigText(record: any) {
    if (record.auth_type === 0) {
      const config = record.manual_config || {}
      return [
        `Cookie ${arrayLength(config.cookies)}`,
        `本地存储 ${arrayLength(config.local_storage)}`,
        `会话存储 ${arrayLength(config.session_storage)}`,
        `请求头 ${objectSize(config.headers)}`,
      ].join('；')
    }
    if (record.auth_type === 1) {
      const config = record.auto_auth_config || {}
      const details = [
        config.url || '使用授权环境地址',
        `超时 ${config.timeout ?? 300}秒`,
        `Cookie域 ${arrayLength(config.cookie_domains)}`,
        `本地存储键 ${arrayLength(config.local_storage_keys)}`,
        `会话存储键 ${arrayLength(config.session_storage_keys)}`,
        `请求头 ${objectSize(config.headers)}`,
      ]
      return details.join('；')
    }
    if (record.auth_type === 2) {
      const config = record.api_config || {}
      const apiInfoId = config.api_info || config.api_info_id
      return [
        `登录接口 ${apiInfoId ? `#${apiInfoId}` : '-'}`,
        `Token路径 ${config.token_path || '-'}`,
        `Cookie映射 ${objectSize(config.cookie_mapping)}`,
        `本地存储映射 ${arrayLength(config.local_storage_mapping)}`,
        `会话存储映射 ${arrayLength(config.session_storage_mapping)}`,
        `请求头映射 ${objectSize(config.header_mapping)}`,
      ].join('；')
    }
    if (record.auth_type === 3) {
      return record.page_step
        ? `${record.page_step.name || '页面步骤'}（#${record.page_step.id}）`
        : '-'
    }
    return record.custom_code ? '已配置自定义代码' : '-'
  }

  function getRefreshStrategyText(record: any) {
    if (record.auth_type === 3) return '-'
    if (record.refresh_mode === 0) return '手动触发'
    if (record.refresh_mode === 1) {
      return record.time_task?.name
        ? `定时策略：${record.time_task.name}`
        : '未配置定时策略'
    }
    if (record.refresh_mode === 2) {
      const noticeGroup = record.notice_group?.name || '未配置通知组'
      return `提前 ${record.expire_notice_minutes ?? '-'} 分钟；通知组：${noticeGroup}`
    }
    return '-'
  }

  function arrayLength(value: unknown) {
    return Array.isArray(value) ? value.length : 0
  }

  function objectSize(value: unknown) {
    return value && typeof value === 'object' && !Array.isArray(value)
      ? Object.keys(value as Record<string, unknown>).length
      : 0
  }

  function onAdd() {
    editingId.value = null
    formTitle.value = '新增授权'
    Object.assign(form, {
      project_product: '',
      test_env: '',
      name: '',
      auth_type: 0,
      status: 1,
      page_step: null,
      api_info: null,
      time_task: null,
      notice_group: null,
      refresh_mode: 0,
      token_ttl: 1440,
      expire_notice_minutes: 30,
    })
    resetJsonEditors()
    void prefillNavigationModel(navigationCreateRef.value, form, () => editingId.value === null)
      .then(() => { if (editingId.value === null) onFormProjectProductChange() })
    modalDialogRef.value?.toggle()
  }

  function onEdit(record: any) {
    editingId.value = record.id
    formTitle.value = '编辑授权'
    const apiConfig = record.api_config || {}
    Object.assign(form, {
      ...record,
      project_product: record.project_product?.id,
      page_step: record.page_step?.id,
      api_info: apiConfig.api_info || apiConfig.api_info_id || null,
      time_task: record.time_task?.id || null,
      notice_group: record.notice_group?.id || null,
    })
    manualConfigText.value = JSON.stringify(record.manual_config || {}, null, 2)
    autoConfigText.value = JSON.stringify(record.auto_auth_config || {}, null, 2)
    apiConfigText.value = JSON.stringify(apiConfig, null, 2)
    loadRelatedOptions(record.project_product?.id)
    modalDialogRef.value?.toggle()
  }

  async function onSubmit() {
    const errors = await formRef.value?.validate()
    if (errors) {
      modalDialogRef.value?.setConfirmLoading(false)
      return
    }
    try {
      const projectProductId = getOptionId(form.project_product)
      const parsedApiConfig = parseJson<Record<string, unknown>>(apiConfigText.value)
      const apiConfig = {
        ...parsedApiConfig,
        api_info: form.api_info || parsedApiConfig.api_info || null,
      }
      const payload: UiAuthConfigPayload = {
        project_product: projectProductId,
        test_env: form.test_env,
        name: form.name,
        auth_type: form.auth_type,
        status: form.status,
        refresh_mode: form.auth_type === 3 ? 0 : form.refresh_mode,
        token_ttl: form.token_ttl,
        expire_notice_minutes: form.expire_notice_minutes,
        page_step: form.auth_type === 3 ? form.page_step : null,
        time_task: form.auth_type === 2 && form.refresh_mode === 1 ? form.time_task : null,
        notice_group: form.auth_type !== 3 && form.refresh_mode === 2 ? form.notice_group : null,
        custom_code: '',
        manual_config: parseJson<UiAuthCacheConfig>(manualConfigText.value),
        auto_auth_config: parseJson<Record<string, unknown>>(autoConfigText.value),
        api_config: apiConfig,
      }
      editingId.value ? await putUiAuthConfig({ ...payload, id: editingId.value }) : await postUiAuthConfig(payload)
      Message.success('保存成功')
      modalDialogRef.value?.toggle()
      await doRefresh()
    } finally {
      modalDialogRef.value?.setConfirmLoading(false)
    }
  }

  function parseJson<T = Record<string, unknown>>(value: string): T {
    try {
      return JSON.parse(value || '{}') as T
    } catch {
      Message.error('JSON格式不正确')
      throw new Error('JSON格式不正确')
    }
  }

  async function onStatusChange(id: number, status: number) {
    await putUiAuthConfigStatus(id, status)
    Message.success('状态已更新')
    return true
  }

  async function onRefresh(record: any) {
    await postUiAuthConfigRefresh(record.id)
    Message.success('缓存已更新')
    await doRefresh()
  }

  async function onAutoStart(record: any) {
    const key = authTaskKey(record.id, 'start')
    if (authTaskLoading[key]) return
    authTaskLoading[key] = true
    try {
      const response = await postUiAuthConfigAutoStart(record.id)
      const taskId = getTaskId(response)
      saveExecutorTaskObservation('ui-auth-start', record.id, {
        taskId,
        businessType: 'u_auth_auto',
      })
      await waitExecutorTask(taskId, 2 * 60 * 1000, 'ui-auth-start', record.id)
      Message.success('自动授权浏览器已打开，请完成登录后点击“完成登录”')
    } finally {
      authTaskLoading[key] = false
    }
  }

  async function onAutoCapture(record: any) {
    const key = authTaskKey(record.id, 'capture')
    if (authTaskLoading[key]) return
    authTaskLoading[key] = true
    try {
      const response = await postUiAuthConfigAutoCapture(record.id)
      const taskId = getTaskId(response)
      saveExecutorTaskObservation('ui-auth-capture', record.id, {
        taskId,
        businessType: 'u_auth_auto_capture',
      })
      await waitExecutorTask(taskId, 15 * 60 * 1000, 'ui-auth-capture', record.id)
      Message.success('授权缓存已提取并保存')
      await doRefresh()
    } finally {
      authTaskLoading[key] = false
    }
  }

  function authTaskKey(id: number, action: 'start' | 'capture') {
    return `${id}:${action}`
  }

  function isAuthTaskLoading(id: number, action: 'start' | 'capture') {
    return Boolean(authTaskLoading[authTaskKey(id, action)])
  }

  function getAuthActions(record: any): AuthTableAction[] {
    return [
      {  label: '缓存', onClick: () => onCache(record) },
      {
        label: '刷新',
        onClick: () => onRefresh(record),
        disabled: [1, 3].includes(record.auth_type),
      },
      {
        label: '自动授权',
        onClick: () => onAutoStart(record),
        disabled: record.auth_type !== 1,
        loading: isAuthTaskLoading(record.id, 'start'),
      },
      {
        label: '完成登录',
        onClick: () => onAutoCapture(record),
        disabled: record.auth_type !== 1,
        loading: isAuthTaskLoading(record.id, 'capture'),
      },
      {  label: '编辑', onClick: () => onEdit(record) },
      {  label: '清空', danger: true, onClick: () => onClear(record) },
      {  label: '删除', danger: true, onClick: () => onDelete(record) },
    ]
  }

  function getTaskId(response: any): number {
    const taskId = Number(response?.data?.task_id ?? response?.task_id)
    if (!Number.isFinite(taskId) || taskId <= 0) {
      throw new Error('服务端未返回有效的执行器任务ID')
    }
    return taskId
  }

  async function waitExecutorTask(
    taskId: number,
    timeoutMs: number,
    observationScope = '',
    businessId: number | string = ''
  ) {
    const startedAt = Date.now()
    while (Date.now() - startedAt < timeoutMs) {
      const response = await getExecutorTask(taskId)
      const task = response?.data || response
      if (task?.terminal) {
        if (observationScope) {
          clearExecutorTaskObservation(observationScope, businessId, taskId)
        }
        if (task.status === 'success') return task
        throw new Error(task.error_message || `执行器任务未完成（${task.status || '未知状态'}）`)
      }
      await new Promise((resolve) => window.setTimeout(resolve, 1000))
    }
    throw new Error('等待执行器任务结果超时，可稍后刷新查看授权缓存')
  }

  function resumeAuthTasks() {
    for (const record of table.dataList) {
      for (const action of ['start', 'capture'] as const) {
        const scope = action === 'start' ? 'ui-auth-start' : 'ui-auth-capture'
        const observation = loadExecutorTaskObservation(scope, record.id)
        if (!observation?.taskId) continue
        const key = authTaskKey(record.id, action)
        authTaskLoading[key] = true
        void waitExecutorTask(
          Number(observation.taskId),
          action === 'start' ? 2 * 60 * 1000 : 15 * 60 * 1000,
          scope,
          record.id
        )
          .then(async () => {
            Message.success(action === 'start' ? '自动授权浏览器已打开' : '授权缓存已提取并保存')
            if (action === 'capture') await doRefresh()
          })
          .catch((error) => Message.error(error?.message || '自动授权任务执行失败'))
          .finally(() => {
            authTaskLoading[key] = false
          })
      }
    }
  }

  async function onClear(record: any) {
    await postUiAuthConfigClear(record.id)
    Message.success('缓存已清空')
    await doRefresh()
  }

  async function onCache(record: any) {
    const res = await getUiAuthConfigCache(record.id)
    cacheModal.text = JSON.stringify(res.data, null, 2)
    cacheModal.visible = true
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '删除授权',
      content: '是否要删除此 UI 授权配置？',
      onOk: async () => {
        await deleteUiAuthConfig(record.id)
        Message.success('删除成功')
        await doRefresh()
      },
    })
  }

  function onFormProjectProductChange() {
    form.page_step = null
    form.api_info = null
    form.notice_group = null
    loadRelatedOptions(form.project_product)
  }

  async function loadPageSteps(projectProductValue: any = form.project_product) {
    const res = await getUiSteps({ page: 1, pageSize: 500, project_product: getOptionId(projectProductValue) || undefined })
    pageStepOptions.value = (res.data || []).map((item: any) => ({ label: item.name, value: item.id }))
  }

  async function loadApiInfoList(projectProductId: any) {
    apiInfoOptions.value = []
    if (!projectProductId) return
    const res = await getApiInfo({ page: 1, pageSize: 500, project_product: projectProductId })
    apiInfoOptions.value = (res.data || []).map((item: any) => ({
      label: `${item.name}${item.url ? ` / ${item.url}` : ''}`,
      value: item.id,
    }))
  }

  async function loadNoticeList(projectProductId: any) {
    noticeOptions.value = []
    if (!projectProductId) return
    const res = await getSystemNoticeName(projectProductId)
    noticeOptions.value = res.data || []
  }

  async function loadTimeTaskList() {
    const res = await getSystemTimingList()
    timeTaskOptions.value = res.data || []
  }

  function loadRelatedOptions(projectProductValue: any) {
    const projectProductId = getOptionId(projectProductValue)
    loadPageSteps(projectProductId)
    loadApiInfoList(projectProductId)
    loadNoticeList(projectProductId)
  }

  function resetJsonEditors() {
    manualConfigText.value = '{"cookies":[],"local_storage":[],"session_storage":[],"headers":{}}'
    autoConfigText.value = '{"url":"","cookie_domains":[],"local_storage_keys":[],"session_storage_keys":[],"headers":{},"timeout":300}'
    apiConfigText.value = '{"api_info":null,"token_path":"$.response.json.data.token","cookie_mapping":{},"local_storage_mapping":[],"session_storage_mapping":[],"header_mapping":{}}'
  }

  onMounted(async () => {
    await doRefresh()
    resumeAuthTasks()
    getUserName().then((res) => (userOptions.value = res.data || []))
    loadPageSteps()
    loadTimeTaskList()
  })

  watch(
    () => form.auth_type,
    (authType) => {
      if (authType === 3) {
        form.refresh_mode = 0
        form.time_task = null
        form.notice_group = null
      } else if (authType !== 2 && form.refresh_mode === 1) {
        form.refresh_mode = 0
        form.time_task = null
      }
    }
  )

  watch(
    () => form.refresh_mode,
    (refreshMode) => {
      if (refreshMode !== 1) form.time_task = null
      if (refreshMode !== 2) form.notice_group = null
    }
  )
</script>

<style scoped>
  .mango-auth-toolbar {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 8px;
  }

  .mango-auth-cache {
    max-height: 520px;
    overflow: auto;
    padding: 8px;
    color: var(--m-text);
    background: var(--m-surface-soft);
    border-radius: var(--m-radius-sm);
  }

  .mango-auth-table-summary {
    overflow: hidden;
    color: var(--m-text-2);
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
