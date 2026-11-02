<template>
  <TableBody plain class="mango-grader-page">
    <template #header
      ><TableHeader title="评测中心 / 评分器" @search="load" @reset-search="reset"
        ><template #search-content
          ><a-form :model="filters" layout="inline" @keyup.enter="load"
            ><a-form-item label="评分器名称"
              ><a-input
                v-model="filters.search"
                placeholder="搜索评分器名称"
                allow-clear /></a-form-item
            ><a-form-item label="类别"
              ><a-select
                v-model="filters.categories"
                :options="categoryOptions"
                placeholder="选择评分类别"
                multiple
                :max-tag-count="1"
                allow-clear /></a-form-item></a-form></template></TableHeader
    ></template>
    <template #default>
      <a-alert v-if="loadError" type="error" class="mango-grader-error"
        >目录加载失败，请重试。<template #action
          ><a-button size="small" :loading="loading" @click="load">重试</a-button></template
        ></a-alert
      >
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
          <a-link v-if="true" @click="show(record)">{{ record.name }}</a-link>
          <span v-else>{{ record.name }}</span>
        </template>
        <template #description="{ record }"
          ><span class="mango-grader-catalog-description">{{
            record.description || '暂无适用说明'
          }}</span></template
        >
        <template #version="{ record }">{{ formatVersion(record.grader_version) }}</template>
        <template #category="{ record }"
          ><a-tag size="small" :color="getEnumTagColor(categoryEnumOptions, record.category, enumStore.colors)">{{
            categoryOptions.find((item) => item.value === record.category)?.label || record.category || '—'
          }}</a-tag></template
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
        >{{ detailError ? '评分器详情加载失败，请重试。' : '暂无评分器详情'
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
  import EvaluationDrawer from '../components/EvaluationDrawer.vue'
  import { computed, onMounted, reactive, ref } from 'vue'
  import { getGraderCatalog, getGrader } from '@/api/evaluation'
  import GraderDetail from './GraderDetail.vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import { graderColumns, categoryOptions, categoryEnumOptions, GRADER_SCROLL_X } from './config'
  import { useEnum } from '@/store/modules/get-enum'
  import { getEnumTagColor } from '@/utils/business-format'
  import { formatVersion } from '../components/presentation'

  const enumStore = useEnum()
  const selectedGrader = ref<any>(),
    loadError = ref(false),
    detailError = ref(false)
  const rows = ref<any[]>([]),
    loading = ref(false),
    detail = ref<any>(),
    visible = ref(false),
    detailLoading = ref(false)
  const filters = reactive({ search: '', categories: [] as string[] })
  const pagination = reactive({
    page: 1,
    pageSize: 20,
    pageCount: 0,
    pageSizes: [20, 50],
    showSizePicker: true,
    onChange: () => undefined,
  })
  const displayedRows = computed(() =>
    rows.value.slice(
      (pagination.page - 1) * pagination.pageSize,
      pagination.page * pagination.pageSize
    )
  )
  let requestId = 0,
    detailRequest = 0
  async function load() {
    const request = ++requestId
    loading.value = true
    loadError.value = false
    try {
      const response: any = await getGraderCatalog({
        search: filters.search || undefined,
        category__in: filters.categories.length ? filters.categories.join(',') : undefined,
      })
      if (request === requestId) {
        rows.value = response.data?.items || []
        pagination.pageCount = rows.value.length
        pagination.page = 1
      }
    } catch {
      if (request === requestId) loadError.value = true
    } finally {
      if (request === requestId) loading.value = false
    }
  }
  function reset() {
    filters.search = ''
    filters.categories = []
    load()
  }
  async function show(row: any) {

    const request = ++detailRequest
    selectedGrader.value = row
    detail.value = undefined
    detailError.value = false
    visible.value = true
    detailLoading.value = true
    try {
      const response: any = await getGrader(row.grader_key, row.grader_version)
      if (request === detailRequest) detail.value = response.data
    } catch {
      if (request === detailRequest) detailError.value = true
    } finally {
      if (request === detailRequest) detailLoading.value = false
    }
  }
  onMounted(load)
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
