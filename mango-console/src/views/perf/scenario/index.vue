<template>
  <TableBody
    plain
    class="mango-detail-workbench-page mango-perf-page mango-perf-navigation-page"
    :sticky-horizontal-scroll="false"
  >
    <template #header><TableHeader title="性能测试 / 性能场景" /></template>
    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
        show-modules
        :model-value="filters.project_product"
        :module-value="filters.module"
        :reset-key="resetKey"
        @filter-change="onNavigation"
        @search="search"
        @reset-search="resetSearch"
      >
        <template #search>
          <a-form :model="filters" layout="inline" @keyup.enter="search">
            <a-form-item label="场景名称"
              ><a-input
                v-model="filters.name"
                allow-clear
                placeholder="请输入场景名称"
                @clear="search"
                @blur="search"
            /></a-form-item>
            <a-form-item label="负载模型"
              ><a-select
                v-model="filters.load_type"
                multiple
                :max-tag-count="1"
                :options="loadTypeOptions"
                allow-clear
                placeholder="请选择负载模型"
                @change="search"
            /></a-form-item>
          </a-form>
        </template>
        <template #toolbar
          ><a-button  type="primary" size="small" @click="openCreate">新建场景</a-button></template
        >
        <a-table
          class="mango-native-scroll-table"
          :columns="scenarioColumns"
          :data="rows"
          :loading="loading"
          :pagination="false"
          :scroll="{ x: scenarioScrollX, y: '100%' }"
          row-key="id"
        >
          <template #columns>
            <a-table-column v-for="column in scenarioColumns" :key="column.key" v-bind="column">
              <template v-if="column.key === 'index'" #cell="{ record }">{{ record.id }}</template>
              <template v-else-if="column.key === 'name'" #cell="{ record }"
                ><a-link @click="goDetail(record)">{{ record.name }}</a-link></template
              >
              <template v-else-if="column.key === 'project_product'" #cell="{ record }">{{
                formatProjectProductPath(record.project_product)
              }}</template>
              <template v-else-if="column.key === 'module'" #cell="{ record }">{{
                record.module_full_path || formatModulePath(record.module)
              }}</template>
              <template v-else-if="column.key === 'load_type'" #cell="{ record }">{{
                loadTitle(record.load_type)
              }}</template>
              <template v-else-if="column.key === 'load_target'" #cell="{ record }">{{
                loadTarget(record)
              }}</template>
              <template v-else-if="column.key === 'duration_seconds'" #cell="{ record }"
                >{{ record.duration_seconds || 0 }} 秒</template
              >
              <template v-else-if="column.key === 'status'" #cell="{ record }"
                ><a-switch
                  :model-value="record.status"
                  :loading="changingIds.has(record.id)"
                  :disabled="changingIds.has(record.id) || deletingIds.has(record.id)"
                  :checked-value="1"
                  :unchecked-value="0"
                  :before-change="(value) => toggleStatus(record, value)"
              /></template>
              <template v-else-if="column.key === 'actions'" #cell="{ record }">
                <MangoTableActions
                  :actions="[
    {
        label: '执行',
        onClick: () => execute(record), },
    { label: '配置', onClick: () => goDetail(record) },
    { label: '删除', danger: true, loading: deletingIds.has(record.id), disabled: changingIds.has(record.id), onClick: () => remove(record) },
]"
                />
              </template>
            </a-table-column>
          </template>
        </a-table>
        <template #footer><TableFooter :pagination="pagination" /></template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>

  <ScenarioCreateDialog ref="createDialogRef" :context-version="createContextVersion"
    :is-context-current="isCreateContextCurrent" @created="onCreated" />
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { Message, Modal } from '@arco-design/web-vue'
  import { onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import ScenarioCreateDialog from './components/ScenarioCreateDialog.vue'
  import useUserStore from '@/store/modules/user'
  import { usePagination } from '@/hooks/table'
  import { formatModulePath, formatProjectProductPath } from '@/utils/business-format'
  import { deletePerfScenario, getPerfScenarios, updatePerfScenario } from '@/api/perf'
  import { loadTypeOptions, scenarioColumns, scenarioScrollX } from './config'
  import { selectionId } from './create'
  import { copyScenarioFilters, createScenarioFilters, readScenarioRows, scenarioQuery, scenarioSuccess } from './list'
  import type { ScenarioRow } from './list'
  import type { NavigationCreateSource } from '@/utils/navigation-create-defaults'

  const route = useRoute(), router = useRouter(), user = useUserStore()
  const navigationCreateRef = ref<NavigationCreateSource | null>(null)
  const createDialogRef = ref<InstanceType<typeof ScenarioCreateDialog> | null>(null)
  const rows = ref<ScenarioRow[]>([]), loading = ref(false), failed = ref(false), resetKey = ref(0)
  const filters = reactive(createScenarioFilters()), appliedFilters = ref(createScenarioFilters())
  const changingIds = reactive(new Set<number>()), deletingIds = reactive(new Set<number>())
  const pagination = usePagination(() => load(), () => loading)
  const createContextVersion = ref(0)
  let active = true, disposed = false, mounted = false, needsRead = true, readVersion = 0, queryVersion = 0
  let pending: { key: string; isCurrent: () => boolean; promise: Promise<boolean> } | null = null
  let deleteDialog: ReturnType<typeof Modal.confirm> | null = null
  let deleteGeneration = 0
  const available = () => !disposed && active && route.path === '/perf/scenario/index' &&
    (typeof document === 'undefined' || document.visibilityState !== 'hidden')
  function isCreateContextCurrent(version: number): boolean { return available() && version === createContextVersion.value }
  function closeCreate(): void { createContextVersion.value++; createDialogRef.value?.close() }
  function closeDelete(): void { deleteGeneration++; deleteDialog?.close(); deleteDialog = null }
  function invalidateRead(): void { readVersion++; pending = null; loading.value = false }
  function suspend(clear: boolean): void {
    closeCreate(); closeDelete(); invalidateRead(); needsRead = true
    if (clear) { rows.value = []; pagination.setTotalSize(0); failed.value = false }
  }
  function resume(): void {
    if (!mounted || !available() || loading.value || !needsRead) return
    void load()
  }
  function loadTitle(value: string) { return loadTypeOptions.find(item => item.value === value)?.label || value }
  function loadTarget(record: ScenarioRow) {
    if (record.load_type === 'concurrency') return `${record.target_users ?? 0} 用户`
    return `${record.target_rate ?? 0} 请求/${record.rate_time_unit === 'minute' ? '分钟' : '秒'}`
  }
  function query() { return scenarioQuery(appliedFilters.value, pagination.page, pagination.pageSize) }
  function load(): Promise<boolean> {
    if (!available()) { loading.value = false; return Promise.resolve(false) }
    const params = query(), key = JSON.stringify(params), context = createContextVersion.value
    if (pending?.key === key && pending.isCurrent()) return pending.promise
    const request = ++readVersion
    const isCurrent = () => available() && context === createContextVersion.value && request === readVersion
    const job = { key, isCurrent, promise: Promise.resolve(false) }
    pending = job
    loading.value = true
    failed.value = false
    needsRead = true
    job.promise = Promise.resolve().then(async () => {
      try {
        if (!isCurrent()) return false
        const response = await getPerfScenarios(params)
        if (!isCurrent()) return false
        const result = readScenarioRows(response)
        const lastPage = Math.max(1, Math.ceil(result.total / Number(params.pageSize)))
        if (Number(params.page) > lastPage) { pagination.page = lastPage; return load() }
        rows.value = result.rows
        pagination.setTotalSize(result.total)
        needsRead = false
        return true
      } catch (loadFailure0) {
        if (isCurrent()) (reportLoadError(loadFailure0, "加载失败，请重试", false), failed.value = true)
        return false
      } finally {
        if (pending === job) { pending = null; loading.value = false }
      }
    })
    return job.promise
  }
  function search(): Promise<boolean> {
    const next = copyScenarioFilters(filters)
    pagination.page = 1
    if (JSON.stringify(next) !== JSON.stringify(appliedFilters.value)) appliedFilters.value = next
    return load()
  }
  function onNavigation(value: { projectProduct: unknown; module: unknown }): Promise<boolean> {
    filters.project_product = selectionId(value.projectProduct)
    filters.module = selectionId(value.module)
    return search()
  }
  function resetSearch(): Promise<boolean> {
    Object.assign(filters, createScenarioFilters())
    resetKey.value++
    return search()
  }
  async function openCreate(): Promise<void> {
    if (available()) await createDialogRef.value?.open(navigationCreateRef.value?.getCreateDefaults())
  }
  function onCreated(id: number, version: number): void {
    if (isCreateContextCurrent(version)) router.push({ path: '/perf/scenario/details', query: { id } })
  }
  function currentRow(record: ScenarioRow): boolean { return available() && rows.value.some(row => row.id === record.id) }
  function goDetail(record: ScenarioRow): void {
    if (currentRow(record)) router.push({ path: '/perf/scenario/details', query: { id: record.id } })
  }
  function execute(record: ScenarioRow): void {
    if (currentRow(record)) router.push({ path: '/perf/scenario/details', query: { id: record.id, execute: '1' } })
  }
  async function toggleStatus(record: ScenarioRow, value: unknown): Promise<boolean> {
    if (!currentRow(record) || (value !== 0 && value !== 1) || changingIds.has(record.id) || deletingIds.has(record.id)) return false
    const id = record.id, context = createContextVersion.value, selection = queryVersion
    const isCurrent = () => isCreateContextCurrent(context) && queryVersion === selection
    changingIds.add(id)
    try {
      const response = scenarioSuccess(await updatePerfScenario({ id, status: value }))
      const result = response.data
      if (!result || typeof result !== 'object' || Array.isArray(result)) throw new Error('场景更新响应格式不正确')
      const saved = result as Record<string, unknown>
      if (saved.id !== id || saved.status !== value) throw new Error('场景更新响应与提交不一致')
      if (!isCurrent()) return false
      const row = rows.value.find(item => item.id === id)
      if (row) row.status = value
      invalidateRead()
      await load()
      return true
    } catch {
      if (isCurrent()) Message.error('状态修改失败，请重试')
      return false
    } finally { changingIds.delete(id) }
  }
  function remove(record: ScenarioRow): void {
    if (!currentRow(record) || deletingIds.has(record.id) || changingIds.has(record.id)) return
    closeDelete()
    const window = deleteGeneration, context = createContextVersion.value, selection = queryVersion, id = record.id
    const isCurrent = () => window === deleteGeneration && isCreateContextCurrent(context) && queryVersion === selection
    deleteDialog = Modal.confirm({
      title: '删除性能场景', content: `确认删除“${record.name}”吗？`,
      okText: '删除', cancelText: '取消', okButtonProps: { status: 'danger' },
      onBeforeOk: async () => {
        if (!isCurrent() || deletingIds.has(id) || changingIds.has(id)) return false
        deletingIds.add(id)
        try {
          scenarioSuccess(await deletePerfScenario(id))
          if (!isCurrent()) return false
          Message.success('删除成功')
          invalidateRead()
          await load()
          return true
        } catch {
          if (isCurrent()) Message.error('删除失败，请重试')
          return false
        } finally { deletingIds.delete(id) }
      },
    })
  }
  function visibilityChanged(): void { if (document.visibilityState === 'hidden') suspend(false); else resume() }
  watch(() => [pagination.page, pagination.pageSize, appliedFilters.value], () => {
    queryVersion++; closeDelete(); invalidateRead(); needsRead = true
  }, { flush: 'sync' })
  watch(() => [user.userId, user.roleId, user.token, user.selected_environment], () => {
    suspend(true)
    Object.assign(filters, createScenarioFilters())
    appliedFilters.value = createScenarioFilters()
    pagination.page = 1
    resetKey.value++
    void Promise.resolve().then(resume)
  }, { flush: 'sync' })
  watch(() => route.path, () => { suspend(false); void Promise.resolve().then(resume) }, { flush: 'sync' })
  onMounted(() => {
    mounted = true
    if (typeof document !== 'undefined') document.addEventListener('visibilitychange', visibilityChanged)
    resume()
  })
  onDeactivated(() => { active = false; suspend(false) })
  onActivated(() => { active = true; resume() })
  onBeforeUnmount(() => {
    disposed = true; active = false; suspend(true)
    if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', visibilityChanged)
  })
</script>
