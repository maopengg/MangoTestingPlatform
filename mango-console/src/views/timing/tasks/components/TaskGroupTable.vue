<template>
  <div class="mango-task-group-table">
    <div v-if="!projectProductId" class="mango-empty-state">请先从左侧导航选择项目 / 产品</div>
    <template v-else>
      <div class="mango-task-group-table__body">
        <a-table
          class="mango-native-scroll-table"
          :data="pagedRows"
          :loading="loading"
          :pagination="false"
          :scroll="{ x: 2500, y: '100%' }"
          row-key="local_key"
        >
          <template #columns>
            <a-table-column title="模块" :width="260" fixed="left">
              <template #cell="{ record }">
                <ProductModuleSelect
                  v-model="record.module_id"
                  :project-product-id="projectProductId"
                  :selectable-level="0"
                  :max-selectable-level="3"
                  :max-display-level="3"
                  :auto-clear="false"
                  check-strictly
                  placeholder="请选择模块"
                  @change="onModuleChange(record)"
                />
              </template>
            </a-table-column>
            <a-table-column title="保存状态" :width="90" fixed="left" align="center">
              <template #cell="{ record }">
                <a-tag size="small" :color="saveStateColor(record)">{{
                  saveStateText(record)
                }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="任务名称" :width="230">
              <template #cell="{ record }">
                <a-input
                  v-model="record.name"
                  placeholder="请输入任务名称"
                  @blur="queueSave(record)"
                />
              </template>
            </a-table-column>
            <a-table-column title="定时策略" :width="230">
              <template #cell="{ record }">
                <a-select
                  v-model="record.timing_strategies"
                  multiple
                  allow-search
                  :max-tag-count="1"
                  :field-names="fieldNames"
                  :options="timingOptions"
                  placeholder="请选择定时策略"
                  @change="queueSave(record)"
                />
              </template>
            </a-table-column>
            <a-table-column title="测试环境" :width="180">
              <template #cell="{ record }">
                <a-select
                  v-model="record.test_envs"
                  multiple
                  allow-search
                  :max-tag-count="1"
                  :field-names="fieldNames"
                  :options="environmentOptions"
                  placeholder="请选择测试环境"
                  @change="onEnvironmentChange(record)"
                />
              </template>
            </a-table-column>
            <a-table-column title="用例类型" :width="180">
              <template #cell="{ record }">
                <a-select
                  v-model="record.case_types"
                  multiple
                  allow-clear
                  :max-tag-count="1"
                  :field-names="fieldNames"
                  :options="caseTypeOptions"
                  placeholder="留空表示全部类型"
                  @change="onCaseTypeChange(record)"
                />
              </template>
            </a-table-column>
            <a-table-column title="执行场景" :width="210">
              <template #cell="{ record }">
                <a-select
                  v-model="record.execution_scenes"
                  multiple
                  allow-clear
                  :max-tag-count="1"
                  :field-names="fieldNames"
                  :options="scenesForEnvironments(record.test_envs)"
                  placeholder="请选择执行场景"
                  @change="queueSave(record)"
                />
              </template>
            </a-table-column>
            <a-table-column title="API 并发" :width="110">
              <template #cell="{ record }">
                <a-input-number
                  v-model="record.api_concurrency_limit"
                  :min="1"
                  allow-clear
                  :disabled="!supportsApi(record)"
                  placeholder="默认"
                  @change="queueSave(record)"
                />
              </template>
            </a-table-column>
            <a-table-column title="负责人" :width="150">
              <template #cell="{ record }">
                <a-select
                  v-model="record.case_people"
                  allow-search
                  :field-names="fieldNames"
                  :options="userOptions"
                  placeholder="请选择负责人"
                  @change="queueSave(record)"
                />
              </template>
            </a-table-column>
            <a-table-column title="启用" :width="72" align="center">
              <template #cell="{ record }"
                ><a-switch v-permission="'timing.tasks:status'"
                  v-model="record.status"
                  :checked-value="1"
                  :unchecked-value="0"
                  @change="queueSave(record)"
              /></template>
            </a-table-column>
            <a-table-column title="发送通知" :width="90" align="center">
              <template #cell="{ record }"
                ><a-switch v-permission="'timing.tasks:status'"
                  v-model="record.is_notice"
                  :checked-value="1"
                  :unchecked-value="0"
                  @change="queueSave(record)"
              /></template>
            </a-table-column>
            <a-table-column title="失败通知" :width="90" align="center">
              <template #cell="{ record }"
                ><a-switch v-permission="'timing.tasks:status'"
                  v-model="record.fail_notice"
                  :checked-value="1"
                  :unchecked-value="0"
                  @change="queueSave(record)"
              /></template>
            </a-table-column>
            <a-table-column title="通知组" :width="160">
              <template #cell="{ record }">
                <a-select
                  v-model="record.notice_group"
                  allow-clear
                  :options="noticeOptions"
                  placeholder="请选择通知组"
                  @change="queueSave(record)"
                />
              </template>
            </a-table-column>
            <a-table-column title="更新人" :width="100" align="center">
              <template #cell="{ record }">{{ record.update_user_name || '-' }}</template>
            </a-table-column>
            <a-table-column title="更新时间" :width="180" align="center">
              <template #cell="{ record }">{{ record.update_time || '-' }}</template>
            </a-table-column>
            <a-table-column title="操作" :width="160" fixed="right" align="center">
              <template #cell="{ record }">
                <MangoTableActions
                  :actions="[
                    { permission: 'timing.tasks:create',
                      label: '复制',
                      disabled: record.saving,
                      onClick: () => copyRow(record),
                    },
                    { permission: 'timing.tasks:delete',
                      label: '删除',
                      danger: true,
                      loading: record.saving,
                      onClick: () => remove(record),
                    },
                  ]"
                />
              </template>
            </a-table-column>
          </template>
        </a-table>
      </div>
      <TableFooter :pagination="pagination" :show-refresh="false" />
    </template>
  </div>
</template>

<script lang="ts" setup>
  import { computed, ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { usePagination } from '@/hooks/table'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import { getSystemTimingList } from '@/api/system/time'
  import { getSystemNoticeName } from '@/api/system/notice_group'
  import { getUserName } from '@/api/user/user'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import {
    deleteSystemTaskGroup,
    getSystemTaskModuleConfig,
    postSystemTaskGroups,
    putSystemTaskGroup,
  } from '@/api/system/tasks'

  const props = defineProps<{ projectProductId: number | null; filters: Record<string, any> }>()
  const enumStore = useEnum()
  const loading = ref(false)
  const rows = ref<any[]>([])
  const modules = ref<any[]>([])
  const timingOptions = ref<any[]>([])
  const userOptions = ref<any[]>([])
  const noticeOptions = ref<any[]>([])
  const timers = new Map<string, ReturnType<typeof setTimeout>>()
  let draftSeed = 0
  const pagination = usePagination(() => undefined, ref(false))
  const productionScenes = [
    'stability_monitoring',
    'production_inspection',
    'production_regression',
  ]
  const environmentOptions = computed(() => enumStore.environment_type || [])
  const caseTypeOptions = computed(() =>
    (enumStore.test_case_type || []).map((item: any) => ({
      ...item,
      disabled: [3, 4].includes(Number(item.key)),
    }))
  )
  const sceneOptions = computed(() =>
    (enumStore.automation_execution_scene || []).filter(
      (item: any) =>
        ![
          'unclassified',
          'effectiveness_test',
          'temporary_validation',
          'performance_test',
        ].includes(String(item.key))
    )
  )
  const filteredRows = computed(() =>
    rows.value.filter((row) => {
      if (!row.task_id) return true
      const filter = props.filters
      const navigationModuleIds = (filter.navigation_module_ids || []).map(Number)
      if (
        navigationModuleIds.length &&
        !navigationModuleIds.includes(Number(row.module_id)) &&
        !navigationModuleIds.some((moduleId: number) => ancestorIds(moduleId).has(row.module_id))
      )
        return false
      if (filter.test_envs?.length && !intersects(row.test_envs, filter.test_envs)) return false
      if (
        filter.case_types?.length &&
        row.case_types?.length &&
        !intersects(row.case_types, filter.case_types)
      )
        return false
      if (
        filter.execution_scenes?.length &&
        !intersects(row.execution_scenes, filter.execution_scenes)
      )
        return false
      if (
        filter.status !== undefined &&
        filter.status !== null &&
        Number(row.status) !== Number(filter.status)
      )
        return false
      if (
        filter.is_notice !== undefined &&
        filter.is_notice !== null &&
        Number(row.is_notice) !== Number(filter.is_notice)
      )
        return false
      if (filter.save_state && saveState(row) !== filter.save_state) return false
      return true
    })
  )
  const pagedRows = computed(() => {
    const start = (pagination.page - 1) * pagination.pageSize
    return filteredRows.value.slice(start, start + pagination.pageSize)
  })

  watch(
    () => props.projectProductId,
    (id) => {
      if (id) void load()
      else rows.value = []
    },
    { immediate: true }
  )
  watch(
    () => props.filters,
    () => {
      pagination.page = 1
    },
    { deep: true }
  )
  watch(
    () => filteredRows.value.length,
    (total) => pagination.setTotalSize(total),
    { immediate: true }
  )

  function createDraft(module: any) {
    return {
      task_id: null,
      local_key: `draft-${++draftSeed}`,
      project_product_id: props.projectProductId,
      module_id: module.id,
      module: {
        id: module.id,
        name: module.name,
        full_path: module.full_path,
        parent_id: module.parent_id,
        level: module.level,
      },
      name: '',
      timing_strategies: [] as number[],
      test_envs: [] as number[],
      case_types: [] as number[],
      execution_scenes: [] as string[],
      api_concurrency_limit: null,
      case_people: null,
      status: 1,
      is_notice: 0,
      fail_notice: 0,
      notice_group: null,
      update_user_name: '',
      update_time: '',
      saving: false,
      save_error: false,
      saved_signature: null,
    }
  }
  function normalizeArray(value: any[]) {
    return [...new Set((value || []).map((item: any) => item?.id ?? item?.key ?? item))]
  }
  function signature(row: any) {
    return JSON.stringify({
      name: row.name,
      module_id: Number(row.module_id),
      timing_strategies: normalizeArray(row.timing_strategies).sort(),
      test_envs: normalizeArray(row.test_envs).sort(),
      case_types: normalizeArray(row.case_types).sort(),
      execution_scenes: normalizeArray(row.execution_scenes).sort(),
      api_concurrency_limit: row.api_concurrency_limit ?? null,
      case_people: row.case_people?.id ?? row.case_people,
      status: Number(row.status),
      is_notice: Number(row.is_notice),
      fail_notice: Number(row.fail_notice),
      notice_group: row.notice_group?.id ?? row.notice_group,
    })
  }
  function moduleById(id: number) {
    return modules.value.find((item) => Number(item.id) === Number(id))
  }
  function ancestorIds(id: number) {
    const result = new Set<number>()
    let current = moduleById(id)
    while (current?.parent_id) {
      result.add(Number(current.parent_id))
      current = moduleById(current.parent_id)
    }
    return result
  }
  function intersects(left: any[], right: any[]) {
    const values = new Set(normalizeArray(left).map(String))
    return normalizeArray(right).some((item) => values.has(String(item)))
  }
  function normalizeRow(item: any) {
    const row = {
      ...item,
      local_key: item.local_key || `task-${item.task_id}`,
      timing_strategies: normalizeArray(item.timing_strategies),
      test_envs: normalizeArray(item.test_envs).map(Number),
      case_types: normalizeArray(item.case_types).map(Number),
      execution_scenes: normalizeArray(item.execution_scenes).map(String),
      case_people: item.case_people?.id ?? item.case_people,
      notice_group: item.notice_group?.id ?? item.notice_group,
      saving: false,
      save_error: false,
    }
    return { ...row, saved_signature: signature(row) }
  }
  async function load() {
    if (!props.projectProductId) return
    const drafts = rows.value.filter(
      (row) => !row.task_id && Number(row.project_product_id) === Number(props.projectProductId)
    )
    loading.value = true
    try {
      await enumStore.getEnum()
      const [matrix, timing, users, notices] = await Promise.all([
        getSystemTaskModuleConfig(props.projectProductId),
        getSystemTimingList(),
        getUserName(),
        getSystemNoticeName(props.projectProductId),
      ])
      modules.value = matrix.data?.modules || []
      const savedRows = (matrix.data?.items || [])
        .filter((item: any) => item.task_id)
        .map(normalizeRow)
        .sort((a: any, b: any) =>
          String(a.module?.full_path).localeCompare(String(b.module?.full_path), 'zh-CN', {
            numeric: true,
          })
        )
      rows.value = [...drafts, ...savedRows]
      timingOptions.value = timing.data || []
      userOptions.value = users.data || []
      noticeOptions.value = notices.data || []
    } finally {
      loading.value = false
    }
  }
  function saveState(row: any) {
    if (row.saving) return 'saving'
    if (row.save_error) return 'error'
    return row.saved_signature === signature(row) ? 'saved' : 'unsaved'
  }
  function saveStateText(row: any) {
    return { saving: '保存中', error: '保存失败', saved: '已保存', unsaved: '未保存' }[
      saveState(row)
    ]
  }
  function saveStateColor(row: any) {
    return { saving: 'blue', error: 'red', saved: 'green', unsaved: 'orange' }[saveState(row)]
  }
  function missing(row: any) {
    const result = []
    if (!row.module_id) result.push('模块')
    if (!row.name?.trim()) result.push('任务名称')
    if (!row.timing_strategies?.length) result.push('定时策略')
    if (!row.test_envs?.length) result.push('测试环境')
    if (!row.execution_scenes?.length) result.push('执行场景')
    if (!row.case_people) result.push('负责人')
    return result
  }
  function queueSave(row: any) {
    if (!row.task_id && missing(row).length) return
    const key = String(row.local_key)
    const old = timers.get(key)
    if (old) clearTimeout(old)
    timers.set(
      key,
      setTimeout(() => {
        timers.delete(key)
        void save(row)
      }, 350)
    )
  }
  async function save(row: any) {
    if (row.saving || row.saved_signature === signature(row)) return
    const fields = missing(row)
    if (fields.length) {
      if (row.task_id) Message.error(`请先补全：${fields.join('、')}`)
      return
    }
    if (!row.task_id) {
      await createRow(row)
      return
    }
    const expected = signature(row)
    row.saving = true
    row.save_error = false
    try {
      const response = await putSystemTaskGroup(row.task_id, JSON.parse(JSON.stringify(row)))
      row.saved_signature = expected
      row.update_user_name = response.data?.item?.update_user_name || row.update_user_name
      row.update_time = response.data?.item?.update_time || row.update_time
      if (response.data?.delete_count) {
        Message.success(`保存成功，并移除 ${response.data.delete_count} 条下级任务组`)
        await load()
      }
    } catch (error) {
      row.save_error = true
      console.log(error)
    } finally {
      row.saving = false
      if (row.saved_signature !== signature(row) && !row.save_error) queueSave(row)
    }
  }
  async function createRow(row: any) {
    if (!props.projectProductId || row.saving) return
    row.saving = true
    row.save_error = false
    try {
      const response = await postSystemTaskGroups(props.projectProductId, [
        JSON.parse(JSON.stringify(row)),
      ])
      const created = response.data?.items?.[0]
      if (!created) throw new Error('任务组创建接口未返回任务数据')
      const localKey = row.local_key
      Object.assign(row, normalizeRow(created), { local_key: localKey })
      Message.success('任务组创建成功')
      if (response.data?.delete_count) {
        Message.success(`已同时移除 ${response.data.delete_count} 条下级任务组`)
        await load()
      }
    } catch (error) {
      row.save_error = true
      console.log(error)
    } finally {
      row.saving = false
    }
  }
  function scenesForEnvironments(values: number[]) {
    const envs = normalizeArray(values).map(Number)
    if (!envs.length) return sceneOptions.value
    const hasProd = envs.includes(2)
    const hasOther = envs.some((item) => item !== 2)
    if (hasProd && hasOther) return sceneOptions.value
    return sceneOptions.value.filter((item: any) => {
      const scene = String(item.key)
      if (hasProd) return productionScenes.includes(scene)
      return scene !== 'stability_monitoring'
    })
  }
  function onEnvironmentChange(row: any) {
    const allowed = new Set(
      scenesForEnvironments(row.test_envs).map((item: any) => String(item.key))
    )
    row.execution_scenes = row.execution_scenes.filter((item: any) => allowed.has(String(item)))
    queueSave(row)
  }
  function supportsApi(row: any) {
    return !row.case_types?.length || row.case_types.map(Number).includes(1)
  }
  function onCaseTypeChange(row: any) {
    if (!supportsApi(row)) row.api_concurrency_limit = null
    queueSave(row)
  }
  function onModuleChange(row: any) {
    const module = moduleById(row.module_id)
    row.module = module
      ? {
          id: module.id,
          name: module.name,
          full_path: module.full_path,
          parent_id: module.parent_id,
          level: module.level,
        }
      : null
    queueSave(row)
  }
  function copyRow(row: any) {
    const module = moduleById(row.module_id)
    if (!module) {
      Message.error('当前任务缺少可复制的模块')
      return
    }
    const draft = createDraft(module)
    const originalName = row.name?.trim() || `模块全量/${module.full_path}`
    Object.assign(draft, {
      name: `${originalName}-副本`.slice(0, 64),
      timing_strategies: normalizeArray(row.timing_strategies).map(Number),
      test_envs: normalizeArray(row.test_envs).map(Number),
      case_types: normalizeArray(row.case_types).map(Number),
      execution_scenes: normalizeArray(row.execution_scenes).map(String),
      api_concurrency_limit: row.api_concurrency_limit ?? null,
      case_people: row.case_people?.id ?? row.case_people ?? null,
      status: Number(row.status),
      is_notice: Number(row.is_notice),
      fail_notice: Number(row.fail_notice),
      notice_group: row.notice_group?.id ?? row.notice_group ?? null,
    })
    rows.value = [draft, ...rows.value]
    pagination.page = 1
    Message.success('已复制为未保存任务组，请调整配置后保存')
  }
  function expandModules() {
    if (!props.projectProductId) return
    const selectedModuleId = Number(props.filters.navigation_module_id || 0)
    const candidates = selectedModuleId
      ? modules.value.filter(
          (module) =>
            Number(module.id) === selectedModuleId || ancestorIds(module.id).has(selectedModuleId)
        )
      : modules.value
    const existingModuleIds = new Set(
      rows.value.map((row) => Number(row.module_id)).filter((id) => Number.isInteger(id) && id > 0)
    )
    const drafts = candidates
      .filter((module) => !existingModuleIds.has(Number(module.id)))
      .map(createDraft)
    if (!drafts.length) {
      Message.info('当前范围内的模块均已有定时任务')
      return
    }
    rows.value = [...drafts, ...rows.value]
    pagination.page = 1
    const skippedCount = candidates.length - drafts.length
    Message.success(
      `已展开 ${drafts.length} 个未保存任务组${
        skippedCount ? `，跳过 ${skippedCount} 个已有任务模块` : ''
      }`
    )
  }
  function remove(row: any) {
    if (!row.task_id) {
      const key = String(row.local_key)
      const timer = timers.get(key)
      if (timer) clearTimeout(timer)
      timers.delete(key)
      rows.value = rows.value.filter((item) => item.local_key !== row.local_key)
      return
    }
    Modal.confirm({
      title: '删除任务组',
      content: `确认删除“${row.name}”吗？`,
      okText: '删除',
      cancelText: '取消',
      onBeforeOk: async () => {
        try {
          const response = await deleteSystemTaskGroup(row.task_id)
          Message.success(response.msg)
          await load()
          return true
        } catch (error) {
          console.log(error)
          return false
        }
      },
    })
  }
  function applyFilters() {
    pagination.page = 1
  }
  defineExpose({ applyFilters, expandModules, load })
</script>

<style scoped>
  .mango-task-group-table {
    display: flex;
    min-height: 0;
    height: 100%;
    flex-direction: column;
  }
  .mango-task-group-table__body {
    flex: 1 1 0;
    min-height: 0;
    overflow: hidden;
  }
  .mango-task-group-table__body :deep(.arco-table) {
    height: 100%;
  }
  .mango-task-group-table__body :deep(.arco-select-view-multiple) {
    min-height: 32px;
    height: 32px;
    max-height: 32px;
    overflow: hidden;
  }
</style>
