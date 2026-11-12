<template>
  <TableBody plain class="mango-detail-workbench-page" :sticky-horizontal-scroll="false">
    <template #header><TableHeader title="研发协同 / 迭代管理" /></template>
    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
        :sticky-horizontal-scroll="false"
        :model-value="navigationProjectProduct"
        @filter-change="onNavigationFilterChange"
        @search="autoSearch.run"
        @reset-search="autoSearch.cancel(); reset(); autoSearch.sync()"
      >
        <template #search>
          <a-form :model="filters" layout="inline" @keyup.enter="autoSearch.run">
            <a-form-item label="Sprint"
              ><a-input @blur="autoSearch.schedule" @clear="autoSearch.schedule" @mouseleave="autoSearch.schedule" v-model="filters.name" allow-clear placeholder="编号或名称"
            /></a-form-item>
            <a-form-item label="状态"
              ><a-select @change="autoSearch.schedule"
                v-model="filters.status"
                multiple
                :max-tag-count="1"
                :options="statusOptions"
                :loading="enumsRegion.loading.value"
                :field-names="fieldNames"
                allow-clear
            /></a-form-item>
            <a-form-item label="负责人"
              ><a-select @change="autoSearch.schedule"
                v-model="filters.owner"
                multiple
                :max-tag-count="1"
                :options="userOptions"
                :loading="usersRegion.loading.value"
                :field-names="fieldNames"
                allow-clear
                allow-search
            /></a-form-item>
          </a-form>
        </template>
        <template #toolbar>
          <a-space wrap>
            <a-button size="small" :loading="loading" @click="loadRows">刷新</a-button>
            <a-button size="small" type="primary" @click="openEditor()">新建 Sprint</a-button>
          </a-space>
        </template>
        <div class="mango-iteration-page__table">
          
          
          
          <MangoRequestFeedback v-if="navigationError" :message="&quot;详情页面打开失败，请重新点击排期。&quot;" />
          <a-table
            class="mango-native-scroll-table"
            :data="rows"
            :columns="iterationColumns"
            :loading="loading"
            :pagination="false"
            :scroll="{ x: 1940, y: '100%' }"
            row-key="id"
          >
            <template #iteration_no="{ record }"
              ><a-link :loading="navigatingId === record.id" @click="goDetail(record)">{{
                record.iteration_no
              }}</a-link></template
            >
            <template #status="{ record }"
              ><a-tag :color="enumStore.colors[record.status]">{{
                enumTitle(record.status)
              }}</a-tag></template
            >
            <template #owner="{ record }">{{ record.owner?.name || '-' }}</template>
            <template #project_product="{ record }">{{
              formatProjectProductPath(record.project_product)
            }}</template>
            <template #test_progress="{ record }">
              <div v-if="record.test_metrics.total" class="mango-iteration-page__metric">
                <a-progress
                  :percent="record.test_metrics.progress / 100"
                  size="small"
                  :show-text="false"
                />
                <span
                  >{{ record.test_metrics.executed }}/{{ record.test_metrics.total }}</span
                > </div
              ><span v-else>-</span>
            </template>
            <template #pass_rate="{ record }">{{
              record.test_metrics.total ? formatRate(record.test_metrics.pass_rate) : '-'
            }}</template>
            <template #actions="{ record }">
              <MangoTableActions
                :actions="[
                  {
                    label: '排期',
                    loading: navigatingId === record.id,
                    disabled: isBusy(record.id),
                    onClick: () => goDetail(record),
                  },
                  { label: '编辑', disabled: isBusy(record.id), onClick: () => openEditor(record) },
                  {
                    label: '删除',
                    danger: true,
                    loading: deletingIds.has(record.id),
                    disabled: isBusy(record.id),
                    onClick: () => removeRow(record),
                  },
                ]"
              />
            </template>
          </a-table>
        </div>
        <template #footer><TableFooter :pagination="pagination" /></template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>
  <IterationEditor
    ref="editorRef"
    :context-key="contextKey"
    :users="userOptions"
    :status-options="statusOptions"
    :busy-ids="[...confirmations.keys(), ...deletingIds]"
    :users-loading="usersRegion.loading.value"
    :users-error="usersRegion.error.value"
    :enums-loading="enumsRegion.loading.value"
    :enums-error="enumsRegion.error.value"
    @retry-users="usersRegion.load()"
    @retry-enums="enumsRegion.load()"
    @saved="onSaved"
  />
</template>
<script lang="ts" setup>
  import { useDebouncedSearch } from '@/hooks/useDebouncedSearch'

import { requestFailureMessage } from '@/utils/load-error'

  import {
    computed,
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    onMounted,
    reactive,
    ref,
    watch,
  } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { useRoute, useRouter } from 'vue-router'
  import TableBody from '@/components/table/TableBody.vue'
  import TableHeader from '@/components/table/TableHeader.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import { usePagination } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { getUserName } from '@/api/user/user'
  import { formatProjectProductPath } from '@/utils/business-format'
  import { deleteFunctionalIteration, getFunctionalIterations } from '@/api/functional-test'
  import type { NavigationCreateSource } from '@/utils/navigation-create-defaults'
  import IterationEditor from './components/IterationEditor.vue'
  import { iterationColumns } from './config'
  import { iterationList, iterationObject } from './presentation'
  import { iterationSelectionId, parseIterationRow } from './list-form'
  import { useIterationRegion } from './composables/useIterationRegion'
  import type { IterationEditorHandle, IterationOption, IterationRow } from './types'

  const navigationCreateRef = ref<NavigationCreateSource | null>(null)
  const editorRef = ref<IterationEditorHandle | null>(null)
  const router = useRouter(),
    route = useRoute(),
    user = useUserStore(),
    enumStore = useEnum()
  const fieldNames = { value: 'key', label: 'title' }
  const navigationProjectProduct = ref<number | null>(null)
  const filters = reactive({
    name: '',
    status: [] as Array<number | string>,
    owner: [] as Array<number | string>,
  })
  const appliedQuery = ref<Record<string, unknown>>({})
  const identityKey = computed(() =>
    JSON.stringify([user.userId, user.roleId, user.token, user.selected_environment])
  )
  const contextKey = computed(() => JSON.stringify([route.fullPath, identityKey.value]))
  let previousIdentity = identityKey.value
  let active = true,
    mounted = false,
    generation = 0
  const available = () => active && route.path === '/functional-test/iteration/index'
  function region<T>(initial: () => T, read: () => Promise<T>) {
    return useIterationRegion(initial, read, () => generation, available)
  }
  const rowsRegion = region(
    () => ({ rows: [] as IterationRow[], total: 0 }),
    async () => {
      const response = await getFunctionalIterations({
        ...appliedQuery.value,
        page: pagination.page,
        pageSize: pagination.pageSize,
      })
      const rows = iterationList(response.data).map(parseIterationRow)
      if (
        typeof response.totalSize !== 'number' ||
        !Number.isSafeInteger(response.totalSize) ||
        response.totalSize < 0
      )
        throw Error('分页总数无效')
      return { rows, total: response.totalSize }
    }
  )
  const usersRegion = region(
    (): IterationOption[] => [],
    async () =>
      iterationList((await getUserName()).data).map((value) => {
        const item = iterationObject(value)
        if (
          (typeof item.key !== 'string' && typeof item.key !== 'number') ||
          typeof item.title !== 'string'
        )
          throw Error('用户选项格式错误')
        return { key: item.key, title: item.title }
      })
  )
  const enumsRegion = region(
    () => false,
    async () => {
      await enumStore.getEnum()
      return true
    }
  )
  const rows = computed(() => rowsRegion.data.value.rows),
    loading = rowsRegion.loading,
    userOptions = usersRegion.data
  const statusOptions = computed(() =>
    enumsRegion.data.value ? enumStore.functional_test_iteration_status : []
  )
  const pagination = usePagination(loadRows, loading)
  const enumTitle = (value: number) =>
    statusOptions.value.find((item) => Number(item.key) === value)?.title || '-'
  const formatRate = (value: number) => `${value.toFixed(2).replace(/\.00$/, '')}%`
  async function loadRows() {
    if (!available()) {
      loading.value = false
      return false
    }
    const loaded = await rowsRegion.load()
    if (loaded) pagination.setTotalSize(rowsRegion.data.value.total)
    return loaded
  }
  function search() {
    const query: Record<string, unknown> = {}
    if (navigationProjectProduct.value !== null)
      query.project_product = navigationProjectProduct.value
    if (filters.name !== '') query.name = filters.name
    for (const key of ['status', 'owner'] as const)
      if (filters[key].length) query[`${key}__in`] = filters[key].join(',')
    appliedQuery.value = query
    pagination.page = 1
    return loadRows()
  }
  function reset() {
    Object.assign(filters, { name: '', status: [], owner: [] })
    return search()
  }
  function onNavigationFilterChange(filter: { projectProduct: string | number | null }) {
    navigationProjectProduct.value = iterationSelectionId(filter.projectProduct)
    return search()
  }
  const deletingIds = reactive(new Set<number>())
  const confirmations = reactive(new Map<number, ReturnType<typeof Modal.warning>>())
  const navigatingId = ref<number | null>(null),
    navigationError = ref(false)
  const isBusy = (id: number) =>
    deletingIds.has(id) || confirmations.has(id) || !!editorRef.value?.isSaving(id)
  const owned = (row: IterationRow) => available() && rows.value.includes(row)
  function openEditor(record: IterationRow | null = null) {
    if (!available() || (record && (!owned(record) || isBusy(record.id)))) return
    const productId = iterationSelectionId(
      navigationCreateRef.value?.getCreateDefaults().projectProduct
    )
    editorRef.value?.open(record, productId)
  }
  function onSaved() {
    if (!available()) return
    rowsRegion.invalidate()
    void loadRows()
  }
  function removeRow(row: IterationRow) {
    if (!owned(row) || isBusy(row.id)) return
    const id = row.id,
      version = generation,
      name = row.name
    const current = () => available() && generation === version
    const release = () => confirmations.delete(id)
    const dialog = Modal.warning({
      title: '删除 Sprint',
      content: `确认删除「${name}」？`,
      hideCancel: false,
      onCancel: release,
      onBeforeOk: async () => {
        if (!current() || deletingIds.has(id)) return false
        deletingIds.add(id)
        try {
          await deleteFunctionalIteration(id)
          if (!current()) return false
          rowsRegion.invalidate()
          const displayed = rows.value.some((item) => item.id === id)
          rowsRegion.data.value = {
            rows: rows.value.filter((item) => item.id !== id),
            total: Math.max(0, rowsRegion.data.value.total - (displayed ? 1 : 0)),
          }
          pagination.setTotalSize(rowsRegion.data.value.total)
          if (!rows.value.length && pagination.page > 1) --pagination.page
          Message.success('删除成功')
          release()
          void loadRows()
          return true
        } catch {
          if (current()) Message.error('删除失败，请重试')
          return false
        } finally {
          deletingIds.delete(id)
        }
      },
    })
    confirmations.set(id, dialog)
  }
  async function goDetail(row: IterationRow) {
    if (!owned(row) || isBusy(row.id) || navigatingId.value !== null) return
    const version = generation
    navigatingId.value = row.id
    navigationError.value = false
    try {
      const failure = await router.push({
        path: '/functional-test/iteration/details',
        query: { id: row.id },
      })
      if (failure && available() && generation === version) navigationError.value = true
    } catch (requestFailure) {
      if (available() && generation === version) navigationError.value = requestFailureMessage(requestFailure, true, "详情页面打开失败，请重新点击排期。")
    } finally {
      navigatingId.value = null
    }
  }
  function invalidate() {
    ++generation
    for (const region of [rowsRegion, usersRegion, enumsRegion]) region.invalidate(true)
    pagination.setTotalSize(0)
    for (const dialog of confirmations.values()) dialog.close()
    confirmations.clear()
    navigationError.value = false
  }
  function loadAll() {
    return Promise.allSettled([loadRows(), usersRegion.load(), enumsRegion.load()])
  }
  watch(
    contextKey,
    () => {
      invalidate()
      if (identityKey.value !== previousIdentity) {
        previousIdentity = identityKey.value
        Object.assign(filters, { name: '', status: [], owner: [] })
        navigationProjectProduct.value = null
        appliedQuery.value = {}
      }
      pagination.page = 1
      if (mounted && available()) void loadAll()
    },
    { flush: 'sync' }
  )
  onMounted(() => {
    mounted = true
    void loadAll()
  })
  onDeactivated(() => {
    active = false
    invalidate()
  })
  onActivated(() => {
    if (active) return
    active = true
    if (mounted) void loadAll()
  })
  onBeforeUnmount(() => {
    active = false
    mounted = false
    invalidate()
  })

  const autoSearch = useDebouncedSearch(search, () => filters)
</script>
<style lang="less" scoped>
  .mango-iteration-page__table {
    display: flex;
    flex: 1;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
    gap: var(--m-page-gap);
    overflow: hidden;
  }
  .mango-iteration-page__metric {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .mango-iteration-page__metric :deep(.arco-progress) {
    min-width: 86px;
    flex: 1;
  }
  .mango-iteration-page__metric span {
    flex: none;
    color: var(--m-muted);
  }
</style>
