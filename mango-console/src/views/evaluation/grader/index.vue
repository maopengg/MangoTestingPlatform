<template>
  <TableBody plain class="mango-grader-page">
    <template #header
      ><TableHeader title="评测中心 / 评分器" @search="autoSearch.run" @reset-search="autoSearch.cancel(); reset(); autoSearch.sync()"
        ><template #search-content
          ><a-form :model="filters" layout="inline" @keyup.enter="autoSearch.run"
            ><a-form-item label="评分器名称"
              ><a-input @blur="autoSearch.schedule" @clear="autoSearch.schedule" @mouseleave="autoSearch.schedule"
                v-model="filters.search"
                placeholder="搜索评分器名称"
                allow-clear /></a-form-item
            ><a-form-item label="类别"
              ><a-select @change="autoSearch.schedule"
                v-model="filters.categories"
                :options="categoryOptions"
                placeholder="选择评分类别"
                multiple
                :max-tag-count="1"
                allow-clear /></a-form-item></a-form></template></TableHeader
    ></template>
    <template #default>
      <template v-if="loadError"><a-button size="small" :loading="loading" @click="load">重新加载</a-button></template>
      <a-table
        class="mango-grader-catalog-table"
        :columns="graderColumns"
        :data="displayedRows"
        :loading="loading"
        :pagination="false"
        :scroll="{ x: GRADER_SCROLL_X }"
        size="small"
        row-key="grader_key"
      >
        <template #name="{ record }">
          <a-link @click="show(record)">{{ record.name }}</a-link>
        </template>
        <template #description="{ record }"
          ><span class="mango-grader-catalog-description">{{
            record.description || '暂无适用说明'
          }}</span></template
        >
        <template #version="{ record }">{{ formatVersion(record.grader_version) }}</template>
        <template #category="{ record }"
          ><a-tag
            size="small"
            :color="getEnumTagColor(categoryEnumOptions, record.category, enumStore.colors)"
            >{{
              categoryOptions.find((item) => item.value === record.category)?.label ||
              record.category ||
              '—'
            }}</a-tag
          ></template
        >
        <template #actions="{ record }"
          ><MangoTableActions
            :actions="[
              {
                label: '详情',
                onClick: () => show(record),
              },
            ]"
        /></template>
      </a-table>
    </template>
    <template #footer><TableFooter :pagination="pagination" /></template>
  </TableBody>
  <EvaluationDrawer
    v-model:visible="visible"
    :width="900"
    contained
    :footer="false"
    :title="detail?.name || '评分器说明'"
    unmount-on-close
  >
    <MangoPanelSpin :loading="detailLoading" class="mango-grader-detail">
      <GraderDetail v-if="detail" :detail="detail" />
      <div v-else-if="!detailLoading" class="mango-empty-state"
        >{{ detailError ? '' : '暂无评分器详情'
        }}<a-button
          v-if="detailError && selectedGrader"
          size="small"
          :loading="detailLoading"
          @click="show(selectedGrader)"
          >重试</a-button
        ></div
      >
    </MangoPanelSpin>
  </EvaluationDrawer>
</template>
<script setup lang="ts">
  import { useDebouncedSearch } from '@/hooks/useDebouncedSearch'

import { reportLoadError } from '@/utils/load-error'

  import EvaluationDrawer from '../components/EvaluationDrawer.vue'
  import { computed, reactive, ref } from 'vue'
  import { getGraderCatalog } from '@/api/evaluation'
  import useUserStore from '@/store/modules/user'
  import GraderDetail from './GraderDetail.vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import { graderColumns, categoryOptions, categoryEnumOptions, GRADER_SCROLL_X } from './config'
  import { useEnum } from '@/store/modules/get-enum'
  import { getEnumTagColor } from '@/utils/business-format'
  import { formatVersion } from '../components/presentation'
  import { useEvaluationScope } from '../composables/useEvaluationScope'
  import { useGraderDetail } from './composables/useGraderDetail'
  import { createGraderFilters, graderQuery } from './catalog'
  import type { GraderCatalogEntry } from '../types'

  const enumStore = useEnum(),
    user = useUserStore()
  const rows = ref<GraderCatalogEntry[]>([]),
    loading = ref(false),
    loadError = ref(false)
  const filters = reactive(createGraderFilters())
  const {
    selectedGrader,
    detail,
    visible,
    detailLoading,
    detailError,
    show: readDetail,
    close: closeDetail,
  } = useGraderDetail()
  const pagination = reactive({
    page: 1,
    pageSize: 20,
    pageCount: 0,
    pageSizes: [20, 50],
    showSizePicker: true,
    onChange: clampPage,
  })
  const displayedRows = computed(() =>
    rows.value.slice(
      (pagination.page - 1) * pagination.pageSize,
      pagination.page * pagination.pageSize
    )
  )
  let requestId = 0
  const identity = () => JSON.stringify([user.userId, user.roleId, user.token])
  let loadedIdentity = identity()
  function invalidate() {
    ++requestId
    closeDetail()
    rows.value = []
    loading.value = false
    loadError.value = false
    pagination.pageCount = 0
    if (loadedIdentity !== identity()) {
      loadedIdentity = identity()
      Object.assign(filters, createGraderFilters())
      pagination.page = 1
    }
  }
  const scope = useEvaluationScope(
    () => [],
    invalidate,
    () => {
      void load()
    }
  )
  function clampPage() {
    pagination.page = Math.max(
      1,
      Math.min(pagination.page, Math.ceil(rows.value.length / pagination.pageSize))
    )
  }
  async function load() {
    if (!scope.isActive()) return false
    const request = ++requestId,
      current = scope.snapshot(),
      query = graderQuery(filters)
    loading.value = true
    loadError.value = false
    try {
      const response: { data: { items?: GraderCatalogEntry[] } } = await getGraderCatalog(query)
      if (request !== requestId || !scope.current(current)) return false
      rows.value = response.data?.items || []
      pagination.pageCount = rows.value.length
      clampPage()
      return true
    } catch (loadFailure0) {
      if (request === requestId && scope.current(current)) (reportLoadError(loadFailure0, "加载失败，请重试", false), loadError.value = true)
      return false
    } finally {
      if (request === requestId && scope.current(current)) loading.value = false
    }
  }
  function onSearch() {
    pagination.page = 1
    return load()
  }
  function reset() {
    Object.assign(filters, createGraderFilters())
    return onSearch()
  }
  function show(row: Pick<GraderCatalogEntry, 'grader_key' | 'grader_version'>) {
    if (!scope.isActive()) return Promise.resolve(false)
    return readDetail(row)
  }
  scope.start()

  const autoSearch = useDebouncedSearch(onSearch, () => filters)
</script>

<style scoped>
  .mango-grader-catalog-description {
    white-space: nowrap;
  }
  .mango-grader-error {
    margin-bottom: var(--m-page-gap);
  }
  .mango-grader-detail {
    width: 100%;
    flex: 1;
    height: 100%;
    min-height: 0;
  }
  .mango-grader-detail :deep(> .mango-panel-spin__content) {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
  }
</style>
