<template>
  <div v-if="visible" class="mango-module-config-drawer mango-module-config-panel">
    <a-empty v-if="!projectProductId" description="请先从左侧导航选择项目 / 产品" />
    <template v-else>
      <div class="mango-module-config-content">
        <Teleport v-if="filterHost" :to="filterHost">
          <div class="mango-module-config-toolbar">
            <ProductModuleLevelSelect
              class="mango-module-config-module-filter"
              v-model="moduleFilter"
              :project-product-id="projectProductId"
              :auto-clear="false"
            />
            <div class="mango-module-config-filter-row">
              <div class="mango-module-config-filter-field">
                <span>测试环境</span>
                <a-select
                  v-model="environmentFilter"
                  multiple
                  allow-clear
                  :max-tag-count="1"
                  :field-names="fieldNames"
                  :options="environmentOptions"
                  placeholder="请选择测试环境"
                />
              </div>
              <div class="mango-module-config-filter-field">
                <span>用例类型</span>
                <a-select
                  v-model="caseTypeFilter"
                  multiple
                  allow-clear
                  :max-tag-count="1"
                  :field-names="fieldNames"
                  :options="caseTypeOptions"
                  placeholder="请选择用例类型"
                />
              </div>
              <div class="mango-module-config-filter-field">
                <span>执行场景</span>
                <a-select
                  v-model="sceneFilter"
                  multiple
                  allow-clear
                  :max-tag-count="1"
                  :field-names="fieldNames"
                  :options="sceneOptions"
                  placeholder="请选择执行场景"
                />
              </div>
              <div class="mango-module-config-filter-field">
                <span>是否开启</span>
                <a-select
                  v-model="statusFilter"
                  allow-clear
                  :field-names="fieldNames"
                  :options="statusOptions"
                  placeholder="请选择开启状态"
                />
              </div>
              <div class="mango-module-config-filter-field">
                <span>是否通知</span>
                <a-select
                  v-model="noticeFilter"
                  allow-clear
                  :field-names="fieldNames"
                  :options="noticeStatusOptions"
                  placeholder="请选择通知状态"
                />
              </div>
              <div class="mango-module-config-filter-field">
                <span>保存状态</span>
                <a-select
                  v-model="saveStateFilter"
                  allow-clear
                  :field-names="fieldNames"
                  :options="saveStateOptions"
                  placeholder="请选择保存状态"
                />
              </div>
            </div>
          </div>
        </Teleport>
        <div class="mango-module-config-table-region">
          <a-table
            class="mango-native-scroll-table mango-module-config-table"
            :data="pagedRows"
            :loading="loading"
            :pagination="false"
            :scroll="{ x: 2940, y: '100%' }"
            row-key="local_key"
          >
            <template #columns>
              <a-table-column title="一级模块" :width="120" fixed="left">
                <template #cell="{ record }">
                  {{ record.module_level_1 }}
                </template>
              </a-table-column>
              <a-table-column title="二级模块" :width="120" fixed="left">
                <template #cell="{ record }">
                  {{ record.module_level_2 }}
                </template>
              </a-table-column>
              <a-table-column title="三级模块" :width="120" fixed="left">
                <template #cell="{ record }">
                  {{ record.module_level_3 }}
                </template>
              </a-table-column>
              <a-table-column title="保存状态" :width="100" fixed="left" align="center">
                <template #cell="{ record }">
                  <a-tag :color="saveStateColor(record)" size="small">
                    {{ saveStateLabel(record) }}
                  </a-tag>
                </template>
              </a-table-column>
              <a-table-column title="任务名称" :width="240">
                <template #cell="{ record }">
                  <a-input
                    v-model="record.name"
                    :max-length="64"
                    :disabled="isReadOnlyRow(record)"
                    placeholder="请输入任务名称"
                    @blur="scheduleSave(record)"
                  />
                </template>
              </a-table-column>
              <a-table-column title="定时策略" :width="250">
                <template #cell="{ record }">
                  <a-select
                    v-model="record.timing_strategies"
                    multiple
                    allow-search
                    :max-tag-count="1"
                    :field-names="fieldNames"
                    :options="timingOptions"
                    :disabled="isReadOnlyRow(record)"
                    placeholder="请选择定时策略"
                    @change="scheduleSave(record)"
                  />
                </template>
              </a-table-column>
              <a-table-column title="测试环境" :width="190">
                <template #cell="{ record }">
                  <a-select
                    v-model="record.test_envs"
                    multiple
                    allow-clear
                    allow-search
                    :max-tag-count="1"
                    :field-names="fieldNames"
                    :options="environmentOptions"
                    :disabled="isReadOnlyRow(record)"
                    @change="onEnvironmentChange(record)"
                    placeholder="请选择测试环境"
                  />
                </template>
              </a-table-column>
              <a-table-column title="用例类型" :width="190">
                <template #cell="{ record }">
                  <a-select
                    v-model="record.case_types"
                    multiple
                    allow-clear
                    :max-tag-count="1"
                    :field-names="fieldNames"
                    :options="caseTypeOptions"
                    :disabled="isReadOnlyRow(record)"
                    placeholder="留空表示全部类型"
                    @change="onCaseTypeChange(record)"
                  />
                </template>
              </a-table-column>
              <a-table-column title="执行场景" :width="220">
                <template #cell="{ record }">
                  <a-select
                    v-model="record.execution_scenes"
                    multiple
                    allow-clear
                    :max-tag-count="1"
                    :field-names="fieldNames"
                    :options="scenesForEnvironments(record.test_envs)"
                    :disabled="isReadOnlyRow(record)"
                    placeholder="请选择执行场景"
                    @change="scheduleSave(record)"
                  />
                </template>
              </a-table-column>
              <a-table-column title="API 并发" :width="120">
                <template #cell="{ record }">
                  <a-input-number
                    v-model="record.api_concurrency_limit"
                    :min="1"
                    allow-clear
                    :disabled="isReadOnlyRow(record) || !supportsApi(record)"
                    placeholder="默认"
                    @change="scheduleSave(record)"
                  />
                </template>
              </a-table-column>
              <a-table-column title="负责人" :width="170">
                <template #cell="{ record }">
                  <a-select
                    v-model="record.case_people"
                    allow-search
                    :field-names="fieldNames"
                    :options="userOptions"
                    :disabled="isReadOnlyRow(record)"
                    placeholder="请选择负责人"
                    @change="scheduleSave(record)"
                  />
                </template>
              </a-table-column>
              <a-table-column title="启用" :width="80" align="center">
                <template #cell="{ record }"
                  ><a-switch
                    v-model="record.status"
                    :disabled="isReadOnlyRow(record)"
                    :checked-value="1"
                    :unchecked-value="0"
                    @change="scheduleSave(record)"
                /></template>
              </a-table-column>
              <a-table-column title="发送通知" :width="100" align="center">
                <template #cell="{ record }"
                  ><a-switch
                    v-model="record.is_notice"
                    :disabled="isReadOnlyRow(record)"
                    :checked-value="1"
                    :unchecked-value="0"
                    @change="scheduleSave(record)"
                /></template>
              </a-table-column>
              <a-table-column title="仅失败通知" :width="110" align="center">
                <template #cell="{ record }"
                  ><a-switch
                    v-model="record.fail_notice"
                    :disabled="isReadOnlyRow(record) || record.is_notice !== 1"
                    :checked-value="1"
                    :unchecked-value="0"
                    @change="scheduleSave(record)"
                /></template>
              </a-table-column>
              <a-table-column title="通知组" :width="180">
                <template #cell="{ record }">
                  <a-select
                    v-model="record.notice_group"
                    allow-clear
                    :options="noticeOptions"
                    :disabled="isReadOnlyRow(record)"
                    placeholder="请选择通知组"
                    @change="scheduleSave(record)"
                  />
                </template>
              </a-table-column>
              <a-table-column title="更新人" :width="100" align="center">
                <template #cell="{ record }">
                  {{ record.update_user_name || '-' }}
                </template>
              </a-table-column>
              <a-table-column title="更新时间" :width="180" align="center">
                <template #cell="{ record }">
                  {{ record.update_time || '-' }}
                </template>
              </a-table-column>
              <a-table-column title="操作" :width="160" fixed="right" align="center">
                <template #cell="{ record }">
                  <MangoTableActions
                    :actions="[
    {
        label: '新增规则',
        disabled: isReadOnlyRow(record),
        onClick: () => addRule(record), },
    {
        label: '删除',
        danger: true,
        hidden: !record.task_id || isAutomaticallyDeleted(record),
        loading: record.realtime_saving,
        onClick: () => deleteSavedRow(record), },
]"
                  />
                </template>
              </a-table-column>
            </template>
          </a-table>
        </div>
        <TableFooter
          class="mango-module-config-pagination"
          :pagination="pagination"
          :show-refresh="false"
        />
      </div>
    </template>
  </div>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="batchVisible"
    title="批量新增任务组"
    :width="560"
    :mask-closable="false"
    :on-before-ok="confirmBatchCreate"
    :ok-loading="batchSaving"
    unmount-on-close
  >
    <a-form auto-label-width :model="batchForm" class="mango-task-group-batch-form mango-simple-form" layout="horizontal">
      <a-form-item label="模块" required class="mango-task-group-batch-form__wide mango-simple-form-item">
        <a-select
          v-model="batchForm.module_ids"
          multiple
          allow-clear
          allow-search
          :max-tag-count="3"
          :options="moduleOptions"
          placeholder="可选择一级、二级或三级模块"
        />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="定时策略" required>
        <a-select
          v-model="batchForm.timing_strategies"
          multiple
          allow-search
          :max-tag-count="1"
          :field-names="fieldNames"
          :options="timingOptions"
          placeholder="请选择定时策略"
        />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="测试环境" required>
        <a-select
          v-model="batchForm.test_envs"
          multiple
          :max-tag-count="1"
          :field-names="fieldNames"
          :options="environmentOptions"
          placeholder="请选择测试环境"
          @change="clearInvalidBatchScenes"
        />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="用例类型">
        <a-select
          v-model="batchForm.case_types"
          multiple
          allow-clear
          :max-tag-count="1"
          :field-names="fieldNames"
          :options="caseTypeOptions"
          placeholder="留空表示全部类型"
        />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="执行场景" required>
        <a-select
          v-model="batchForm.execution_scenes"
          multiple
          :max-tag-count="1"
          :field-names="fieldNames"
          :options="scenesForEnvironments(batchForm.test_envs)"
          placeholder="请选择执行场景"
        />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="负责人" required>
        <a-select
          v-model="batchForm.case_people"
          allow-search
          :field-names="fieldNames"
          :options="userOptions"
          placeholder="请选择负责人"
        />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="API 并发">
        <a-input-number
          v-model="batchForm.api_concurrency_limit"
          :min="1"
          allow-clear
          placeholder="留空使用平台默认并发"
        />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="通知组">
        <a-select
          v-model="batchForm.notice_group"
          allow-clear
          :options="noticeOptions"
          placeholder="可选"
        />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="任务状态">
        <a-space>
          <span>启用</span>
          <a-switch v-model="batchForm.status" :checked-value="1" :unchecked-value="0" />
          <span>发送通知</span>
          <a-switch v-model="batchForm.is_notice" :checked-value="1" :unchecked-value="0" />
          <span>仅失败通知</span>
          <a-switch v-model="batchForm.fail_notice" :checked-value="1" :unchecked-value="0" />
        </a-space>
      </a-form-item>
    </a-form>
    <a-alert v-if="batchCoveredCount" type="warning">
      创建父级任务组后，将同时删除 {{ batchCoveredCount }} 条已存在的下级任务组。
    </a-alert>
  </a-modal>
</template>

<script lang="ts" setup>
  import { computed, ref, watch } from 'vue'
  import { usePagination } from '@/hooks/table'
  import { Message, Modal } from '@arco-design/web-vue'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import {
    deleteSystemTaskGroup,
    getSystemTaskModuleConfig,
    postSystemTaskGroups,
    putSystemTaskGroup,
  } from '@/api/system/tasks'
  import { getSystemTimingList } from '@/api/system/time'
  import { getSystemNoticeName } from '@/api/system/notice_group'
  import { getUserName } from '@/api/user/user'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import ProductModuleLevelSelect from '@/components/business/ProductModuleLevelSelect.vue'

  const props = defineProps<{
    visible: boolean
    projectProductId: number | null
    navigationModuleId?: number | string | null
    filterHost?: HTMLElement | null
    embedded?: boolean
  }>()
  const emit = defineEmits<{
    (event: 'saved'): void
  }>()
  const enumStore = useEnum()
  const loading = ref(false)
  const rows = ref<any[]>([])
  const moduleOptions = ref<any[]>([])
  const timingOptions = ref<any[]>([])
  const userOptions = ref<any[]>([])
  const noticeOptions = ref<any[]>([])
  const moduleFilter = ref<number | undefined>()
  const environmentFilter = ref<number[]>([])
  const caseTypeFilter = ref<number[]>([])
  const sceneFilter = ref<string[]>([])
  const statusFilter = ref<number | undefined>()
  const noticeFilter = ref<number | undefined>()
  const saveStateFilter = ref<string | undefined>()
  const batchVisible = ref(false)
  const batchSaving = ref(false)
  const batchForm = ref(defaultBatchForm())
  const paginationLoading = ref(false)
  const pagination = usePagination(() => {
    paginationLoading.value = false
  }, paginationLoading)
  let rowSeed = 0
  const rowSaveTimers = new Map<string, ReturnType<typeof setTimeout>>()

  const productionScenes = [
    'stability_monitoring',
    'production_inspection',
    'production_regression',
  ]
  const statusOptions = [
    { key: 1, title: '已开启' },
    { key: 0, title: '已关闭' },
  ]
  const noticeStatusOptions = [
    { key: 1, title: '通知' },
    { key: 0, title: '不通知' },
  ]
  const saveStateOptions = [
    { key: 'saved', title: '已保存' },
    { key: 'unsaved', title: '未保存' },
    { key: 'deleted', title: '已删除' },
    { key: 'covered', title: '已覆盖' },
    { key: 'unconfigured', title: '未配置' },
  ]
  const sceneOptions = computed(() =>
    (enumStore.automation_execution_scene || []).filter(
      (item: any) => !['unclassified', 'effectiveness_test'].includes(String(item.key))
    )
  )
  const environmentOptions = computed(() => enumStore.environment_type || [])
  const caseTypeOptions = computed(() =>
    (enumStore.test_case_type || []).map((item: any) => ({
      ...item,
      disabled: [3, 4].includes(Number(item.key)),
    }))
  )
  const batchCoveredCount = computed(() => {
    const selected = new Set(normalizeNumberArray(batchForm.value.module_ids))
    return rows.value.filter(
      (item) =>
        item.task_id && [...ancestorIds(item.module_id)].some((moduleId) => selected.has(moduleId))
    ).length
  })
  const filteredRows = computed(() =>
    rows.value.filter(
      (item) =>
        matchesModuleFilter(item.module_id) &&
        (!environmentFilter.value.length ||
          hasNumberIntersection(item.test_envs, environmentFilter.value)) &&
        (!caseTypeFilter.value.length ||
          !item.case_types?.length ||
          hasNumberIntersection(item.case_types, caseTypeFilter.value)) &&
        (!sceneFilter.value.length || hasIntersection(item.execution_scenes, sceneFilter.value)) &&
        (statusFilter.value == null ||
          (isConfiguredRow(item) && Number(item.status) === Number(statusFilter.value))) &&
        (noticeFilter.value == null ||
          (isConfiguredRow(item) && Number(item.is_notice) === Number(noticeFilter.value))) &&
        (saveStateFilter.value == null || rowSaveState(item) === saveStateFilter.value)
    )
  )
  const pagedRows = computed(() => {
    const start = (pagination.page - 1) * pagination.pageSize
    return filteredRows.value.slice(start, start + pagination.pageSize)
  })

  watch(
    () => props.visible,
    (visible) => {
      if (visible && props.projectProductId) load()
    }
  )
  watch(
    () => props.navigationModuleId,
    (moduleId) => {
      moduleFilter.value = moduleId == null || moduleId === '' ? undefined : Number(moduleId)
    },
    { immediate: true }
  )
  watch(
    [
      moduleFilter,
      environmentFilter,
      caseTypeFilter,
      sceneFilter,
      statusFilter,
      noticeFilter,
      saveStateFilter,
    ],
    () => {
      pagination.page = 1
    }
  )
  watch(
    () => filteredRows.value.length,
    (total) => {
      pagination.setTotalSize(total)
      const lastPage = Math.max(1, Math.ceil(total / pagination.pageSize))
      if (pagination.page > lastPage) pagination.page = lastPage
    }
  )
  watch(
    () => pagination.pageSize,
    () => {
      const lastPage = Math.max(1, Math.ceil(filteredRows.value.length / pagination.pageSize))
      if (pagination.page > lastPage) pagination.page = lastPage
    }
  )

  function normalize(item: any = {}) {
    const placeholder = item.placeholder === true
    const modulePath = modulePathForId(item.module_id)
    const moduleFullPath =
      item.module_full_path || modulePath.map((module) => module.name).join('/')
    const record = {
      task_id: item.task_id || null,
      local_key: item.task_id ? `task-${item.task_id}` : `new-${++rowSeed}`,
      placeholder,
      pending_delete: false,
      name:
        item.name !== undefined
          ? item.name
          : moduleFullPath
          ? `模块全量/${moduleFullPath}`.slice(0, 64)
          : '',
      module_id: item.module_id ?? null,
      module_full_path: moduleFullPath,
      module_level_1: modulePath[0]?.name || '',
      module_level_2: modulePath[1]?.name || '',
      module_level_3: modulePath[2]?.name || '',
      test_envs: normalizeNumberArray(
        item.test_envs ?? (item.test_env == null ? [] : [item.test_env])
      ),
      case_types: normalizeNumberArray(
        item.case_types ?? (item.case_type == null ? [] : [item.case_type])
      ),
      execution_scenes: normalizeStringArray(
        item.execution_scenes ?? (item.execution_scene ? [item.execution_scene] : [])
      ),
      timing_strategies: item.timing_strategies || [],
      api_concurrency_limit: item.api_concurrency_limit ?? null,
      case_people: item.case_people ?? null,
      is_notice: item.is_notice || 0,
      notice_group: item.notice_group || null,
      fail_notice: item.fail_notice || 0,
      status: item.status ?? (placeholder ? 0 : 1),
      update_user_name: item.update_user_name || '',
      update_time: item.update_time || '',
    }
    return {
      ...record,
      saved_signature: record.task_id ? rowSignature(record) : null,
    }
  }

  function defaultBatchForm() {
    return {
      module_ids: [] as number[],
      timing_strategies: [] as number[],
      test_envs: [] as number[],
      case_types: [] as number[],
      execution_scenes: [] as string[],
      api_concurrency_limit: null as number | null,
      case_people: null as number | null,
      status: 1,
      is_notice: 0,
      notice_group: null as number | null,
      fail_notice: 0,
    }
  }

  function comparableValue(value: any) {
    if (value && typeof value === 'object') {
      return value.id ?? value.value ?? value.key ?? ''
    }
    return value ?? ''
  }

  function comparableArray(value: any) {
    if (!Array.isArray(value)) return []
    return [...new Set(value.map(comparableValue).map(String))].sort()
  }

  function rowSignature(item: any) {
    return JSON.stringify({
      name: item.name ?? '',
      module_id: comparableValue(item.module_id),
      timing_strategies: comparableArray(item.timing_strategies),
      test_envs: comparableArray(item.test_envs),
      case_types: comparableArray(item.case_types),
      execution_scenes: comparableArray(item.execution_scenes),
      api_concurrency_limit: item.api_concurrency_limit ?? null,
      case_people: comparableValue(item.case_people),
      status: Number(item.status),
      is_notice: Number(item.is_notice),
      fail_notice: Number(item.fail_notice),
      notice_group: comparableValue(item.notice_group),
    })
  }

  function isRowSaved(item: any) {
    return Boolean(item.task_id && item.saved_signature === rowSignature(item))
  }

  function rowSaveState(item: any) {
    if (item.realtime_saving) return 'saving'
    if (isDeletedRow(item)) return 'deleted'
    if (isCoveredRow(item)) return 'covered'
    if (isRowSaved(item)) return 'saved'
    return isConfiguredRow(item) ? 'unsaved' : 'unconfigured'
  }

  function saveStateLabel(item: any) {
    if (rowSaveState(item) === 'saving') return '保存中'
    if (rowSaveState(item) === 'deleted') return '已删除'
    if (rowSaveState(item) === 'covered') return '已覆盖'
    if (rowSaveState(item) === 'saved') return '已保存'
    if (rowSaveState(item) === 'unsaved') return '未保存'
    return '未配置'
  }

  function saveStateColor(item: any) {
    if (rowSaveState(item) === 'saving') return 'blue'
    if (rowSaveState(item) === 'deleted') return 'red'
    if (rowSaveState(item) === 'covered') return 'blue'
    if (rowSaveState(item) === 'saved') return 'green'
    if (rowSaveState(item) === 'unsaved') return 'orange'
    return 'gray'
  }

  function isConfiguredRow(item: any) {
    return Boolean(item.task_id)
  }

  async function load() {
    if (!props.projectProductId) return
    loading.value = true
    pagination.page = 1
    try {
      await enumStore.getEnum()
      const [matrix, timing, users, notices] = await Promise.all([
        getSystemTaskModuleConfig(props.projectProductId),
        getSystemTimingList(),
        getUserName(),
        getSystemNoticeName(props.projectProductId),
      ])
      moduleOptions.value = (matrix.data?.modules || [])
        .map((item: any) => ({
          label: item.full_path,
          name: item.name,
          value: item.id,
          parent_id: item.parent_id,
          level: item.level,
        }))
        .sort((left: any, right: any) =>
          String(left.label).localeCompare(String(right.label), 'zh-CN', {
            numeric: true,
            sensitivity: 'base',
          })
        )
      const moduleOrder = new Map(
        moduleOptions.value.map((module, index) => [Number(module.value), index])
      )
      rows.value = (matrix.data?.items || [])
        .map((item: any) => normalize(item))
        .sort(
          (left: any, right: any) =>
            (moduleOrder.get(Number(left.module_id)) ?? Number.MAX_SAFE_INTEGER) -
            (moduleOrder.get(Number(right.module_id)) ?? Number.MAX_SAFE_INTEGER)
        )
      timingOptions.value = timing.data || []
      userOptions.value = users.data || []
      noticeOptions.value = notices.data || []
    } finally {
      loading.value = false
    }
  }

  function moduleById(id: number) {
    return moduleOptions.value.find((item) => Number(item.value) === Number(id))
  }
  function ancestorIds(id: number) {
    const result = new Set<number>()
    let current = moduleById(id)
    while (current?.parent_id != null) {
      result.add(Number(current.parent_id))
      current = moduleById(current.parent_id)
    }
    return result
  }
  function modulePathForId(id: number | null) {
    if (id == null) return []
    const path = []
    let current = moduleById(id)
    while (current) {
      path.unshift(current)
      current = current.parent_id == null ? null : moduleById(current.parent_id)
    }
    return path
  }
  function configuredModuleIds() {
    return new Set(
      rows.value
        .filter(
          (item) =>
            isConfiguredRow(item) &&
            !item.pending_delete &&
            !missingRequiredFields(item).length &&
            item.module_id
        )
        .map((item) => Number(item.module_id))
    )
  }
  function hasConfiguredAncestor(record: any) {
    const configured = configuredModuleIds()
    return [...ancestorIds(record.module_id)].some((id) => configured.has(id))
  }
  function isCoveredByConfiguredAncestor(record: any) {
    return hasConfiguredAncestor(record)
  }
  function isAutomaticallyDeleted(record: any) {
    return Boolean(record.task_id && isCoveredByConfiguredAncestor(record))
  }
  function isDeletedRow(record: any) {
    return Boolean(record.pending_delete || isAutomaticallyDeleted(record))
  }
  function isCoveredRow(record: any) {
    return Boolean(!record.task_id && isCoveredByConfiguredAncestor(record))
  }
  function isReadOnlyRow(record: any) {
    return isDeletedRow(record) || isCoveredRow(record)
  }
  function matchesModuleFilter(moduleId: number) {
    if (moduleFilter.value == null) return true
    const targetId = Number(moduleFilter.value)
    return Number(moduleId) === targetId || ancestorIds(moduleId).has(targetId)
  }
  function normalizeNumberArray(value: any): number[] {
    if (!Array.isArray(value)) return []
    return [...new Set(value.map(Number).filter(Number.isInteger))]
  }

  function normalizeStringArray(value: any): string[] {
    if (!Array.isArray(value)) return []
    return [...new Set(value.map(String).filter(Boolean))]
  }

  function hasIntersection(left: any[], right: any[]) {
    const values = new Set(left || [])
    return (right || []).some((item) => values.has(item))
  }

  function hasNumberIntersection(left: any[], right: any[]) {
    return hasIntersection(normalizeNumberArray(left), normalizeNumberArray(right))
  }

  function scenesForEnvironments(environments: number[]) {
    const values = normalizeNumberArray(environments)
    if (!values.length) return sceneOptions.value
    const hasProduction = values.includes(2)
    const hasNonProduction = values.some((value) => value !== 2)
    if (hasProduction && hasNonProduction) return sceneOptions.value
    return sceneOptions.value.filter((item: any) => {
      const scene = String(item.key)
      if (hasProduction) return productionScenes.includes(scene)
      return scene !== 'stability_monitoring'
    })
  }
  function clearInvalidScene(record: any) {
    const allowed = new Set(
      scenesForEnvironments(record.test_envs).map((item: any) => String(item.key))
    )
    record.execution_scenes = normalizeStringArray(record.execution_scenes).filter((scene) =>
      allowed.has(scene)
    )
  }
  function clearInvalidBatchScenes() {
    const allowed = new Set(
      scenesForEnvironments(batchForm.value.test_envs).map((item: any) => String(item.key))
    )
    batchForm.value.execution_scenes = batchForm.value.execution_scenes.filter((scene) =>
      allowed.has(scene)
    )
  }
  function openBatchCreate() {
    batchForm.value = defaultBatchForm()
    batchVisible.value = true
  }
  defineExpose({ applyFilters, openBatchCreate, resetFilters })
  async function doBatchCreate() {
    if (!props.projectProductId || batchSaving.value) return false
    const form = batchForm.value
    if (
      !form.module_ids.length ||
      !form.timing_strategies.length ||
      !form.test_envs.length ||
      !form.execution_scenes.length ||
      !form.case_people
    ) {
      Message.error('请完整选择模块、定时策略、测试环境、执行场景和负责人')
      return false
    }
    const selectedIds = new Set(normalizeNumberArray(form.module_ids))
    const effectiveIds = [...selectedIds].filter(
      (moduleId) => ![...ancestorIds(moduleId)].some((parentId) => selectedIds.has(parentId))
    )
    const payload = effectiveIds.map((moduleId) => {
      const module = moduleById(moduleId)
      return {
        ...form,
        module_id: moduleId,
        name: `模块全量/${module?.label || moduleId}`.slice(0, 64),
      }
    })
    batchSaving.value = true
    try {
      const response = await postSystemTaskGroups(props.projectProductId, payload)
      Message.success(
        `已创建 ${response.data?.create_count || payload.length} 条任务组` +
          (response.data?.delete_count ? `，并删除 ${response.data.delete_count} 条下级任务组` : '')
      )
      batchVisible.value = false
      await load()
      emit('saved')
      return true
    } finally {
      batchSaving.value = false
    }
  }
  function confirmBatchCreate() {
    return doBatchCreate()
  }
  function supportsApi(record: any) {
    const caseTypes = normalizeNumberArray(record.case_types)
    return !caseTypes.length || caseTypes.includes(1)
  }
  function clearUnavailableApiConcurrency(record: any) {
    if (!supportsApi(record)) record.api_concurrency_limit = null
  }
  function onEnvironmentChange(record: any) {
    clearInvalidScene(record)
    scheduleSave(record)
  }
  function onCaseTypeChange(record: any) {
    clearUnavailableApiConcurrency(record)
    scheduleSave(record)
  }
  function scheduleSave(record: any) {
    if (!record.task_id || isReadOnlyRow(record)) return
    if (record.realtime_saving) {
      record.realtime_save_pending = true
      return
    }
    const currentTimer = rowSaveTimers.get(record.local_key)
    if (currentTimer) clearTimeout(currentTimer)
    rowSaveTimers.set(
      record.local_key,
      setTimeout(() => {
        rowSaveTimers.delete(record.local_key)
        void saveExistingRow(record)
      }, 350)
    )
  }
  async function saveExistingRow(record: any) {
    if (!record.task_id || record.saved_signature === rowSignature(record)) return
    if (record.realtime_saving) {
      record.realtime_save_pending = true
      return
    }
    const missing = missingRequiredFields(record)
    if (missing.length) {
      Message.error(`请先补全：${missing.join('、')}`)
      return
    }
    const payload = JSON.parse(JSON.stringify(record))
    const payloadSignature = rowSignature(payload)
    let reloaded = false
    record.realtime_saving = true
    record.realtime_save_pending = false
    try {
      const response = await putSystemTaskGroup(record.task_id, payload)
      record.update_user_name = response.data?.item?.update_user_name || record.update_user_name
      record.update_time = response.data?.item?.update_time || record.update_time
      record.saved_signature = payloadSignature
      emit('saved')
      if (Number(response.data?.delete_count || 0) > 0) {
        Message.success(`保存成功，并移除 ${response.data.delete_count} 条下级任务组`)
        await load()
        reloaded = true
        return
      }
    } catch (error) {
      await load()
      reloaded = true
      console.log(error)
    } finally {
      record.realtime_saving = false
      if (
        !reloaded &&
        (record.realtime_save_pending || record.saved_signature !== rowSignature(record))
      ) {
        record.realtime_save_pending = false
        scheduleSave(record)
      }
    }
  }
  function addRule(record: any) {
    batchForm.value = {
      ...defaultBatchForm(),
      module_ids: [Number(record.module_id)],
    }
    batchVisible.value = true
  }
  function deleteSavedRow(record: any) {
    if (!record.task_id) return
    Modal.confirm({
      title: '删除任务组',
      content: `确认删除“${record.name || record.module_full_path}”吗？`,
      okText: '删除',
      cancelText: '取消',
      onBeforeOk: async () => {
        record.realtime_saving = true
        try {
          const response = await deleteSystemTaskGroup(record.task_id)
          Message.success(response.msg)
          await load()
          emit('saved')
          return true
        } catch (error) {
          console.log(error)
          return false
        } finally {
          record.realtime_saving = false
        }
      },
    })
  }
  function resetFilters() {
    moduleFilter.value = undefined
    environmentFilter.value = []
    caseTypeFilter.value = []
    sceneFilter.value = []
    statusFilter.value = undefined
    noticeFilter.value = undefined
    saveStateFilter.value = undefined
    pagination.page = 1
  }
  function applyFilters() {
    pagination.page = 1
  }
  function missingRequiredFields(item: any) {
    const fields = []
    if (!item.name?.trim()) fields.push('任务名称')
    if (!item.module_id) fields.push('模块')
    if (!item.timing_strategies?.length) fields.push('定时策略')
    if (!item.test_envs?.length) fields.push('测试环境')
    if (!item.execution_scenes?.length) fields.push('执行场景')
    if (!item.case_people) fields.push('负责人')
    return fields
  }
</script>

<style scoped>
  :global(.mango-module-config-drawer .arco-drawer-body) {
    min-height: 0;
    overflow: hidden;
  }
  .mango-module-config-panel {
    display: flex;
    height: 100%;
    min-height: 0;
    flex-direction: column;
    overflow: hidden;
  }
  .mango-module-config-content {
    display: flex;
    flex: 1 1 0;
    min-height: 0;
    flex-direction: column;
    overflow: hidden;
  }
  .mango-module-config-toolbar {
    display: flex;
    width: 100%;
    align-items: flex-end;
    gap: 8px;
    flex: 0 0 auto;
    overflow-x: auto;
    overflow-y: hidden;
  }
  .mango-module-config-module-filter {
    flex: 1 0 500px;
    min-width: 500px;
  }
  .mango-module-config-filter-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 0 0 auto;
    flex-wrap: nowrap;
  }
  .mango-module-config-filter-field {
    display: flex;
    flex: 0 0 auto;
    align-items: center;
    gap: 8px;
  }
  .mango-module-config-filter-field > span {
    flex: 0 0 auto;
    color: var(--m-text-2);
    white-space: nowrap;
  }
  .mango-module-config-filter-row :deep(.arco-select) {
    width: 148px;
    flex: 0 0 148px;
  }
  .mango-module-config-table-region {
    flex: 1 1 0;
    min-height: 0;
    overflow: hidden;
  }
  .mango-module-config-table {
    height: 100%;
  }
  .mango-module-config-table :deep(.arco-select-view-multiple) {
    height: 32px;
    min-height: 32px;
    max-height: 32px;
    align-items: center;
    overflow: hidden;
  }
  .mango-module-config-table :deep(.arco-select-view-inner.arco-select-view-nowrap) {
    min-width: 0;
    flex-wrap: nowrap;
    align-items: center;
    overflow: hidden;
  }
  .mango-module-config-table :deep(.arco-select-view-tag) {
    min-width: 0;
    flex: 0 1 auto;
    overflow: hidden;
    white-space: nowrap;
  }
  .mango-module-config-table :deep(.arco-select-view-has-tag .arco-select-view-input) {
    width: 0;
    min-width: 0;
    flex: 0 0 0;
  }
  .mango-module-config-pagination {
    flex: 0 0 auto;
    margin-top: var(--m-page-gap);
  }
  .mango-task-group-batch-form {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0 var(--m-page-gap);
  }
  .mango-task-group-batch-form__wide {
    grid-column: 1 / -1;
  }
</style>
