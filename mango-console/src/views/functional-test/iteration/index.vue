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
        @search="search"
        @reset-search="reset"
      >
        <template #search>
          <a-form :model="filters" layout="inline" @keyup.enter="search">
            <a-form-item label="Sprint"><a-input v-model="filters.name" allow-clear placeholder="编号或名称" /></a-form-item>
            <a-form-item label="状态">
              <a-select v-model="filters.status" multiple :max-tag-count="1" :options="statusOptions" :field-names="fieldNames" allow-clear />
            </a-form-item>
            <a-form-item label="负责人">
              <a-select v-model="filters.owner" multiple :max-tag-count="1" :options="userOptions" :field-names="fieldNames" allow-clear allow-search />
            </a-form-item>
          </a-form>
        </template>
        <template #toolbar>
          <a-space>
            <a-button size="small" :loading="loading" @click="loadRows">刷新</a-button>
            <a-button  size="small" type="primary" @click="openEditor()">新建 Sprint</a-button>
          </a-space>
        </template>
        <div class="mango-iteration-page__table">
          <a-table
            class="mango-native-scroll-table"
            :data="rows"
            :columns="iterationColumns"
            :loading="loading"
            :pagination="false"
            :scroll="{ x: 1940, y: '100%' }"
            row-key="id"
          >
            <template #iteration_no="{ record }"><a-link @click="goDetail(record)">{{ record.iteration_no }}</a-link></template>
            <template #status="{ record }"><a-tag>{{ enumTitle(statusOptions, record.status) }}</a-tag></template>
            <template #owner="{ record }">{{ record.owner?.name || '-' }}</template>
            <template #project_product="{ record }">{{ formatProjectProductPath(record.project_product) }}</template>
            <template #test_progress="{ record }">
              <div v-if="record.test_metrics?.total" class="mango-iteration-page__metric">
                <a-progress :percent="Number(record.test_metrics.progress || 0) / 100" size="small" :show-text="false" />
                <span>{{ record.test_metrics.executed || 0 }}/{{ record.test_metrics.total || 0 }}</span>
              </div>
              <span v-else>-</span>
            </template>
            <template #pass_rate="{ record }">{{ record.test_metrics?.total ? formatRate(record.test_metrics.pass_rate) : '-' }}</template>
            <template #actions="{ record }">
              <MangoTableActions :actions="[
    { label: '排期', onClick: () => goDetail(record) },
    { label: '编辑', onClick: () => openEditor(record) },
    { label: '删除', danger: true, onClick: () => removeRow(record) },
]" />
            </template>
          </a-table>
        </div>
        <template #footer><TableFooter :pagination="pagination" /></template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>

  <a-modal v-model:visible="visible" :title="form.id ? '编辑 Sprint' : '新建 Sprint'" width="720px" :ok-loading="saving" @ok="saveRow">
    <a-form :model="form" layout="vertical">
      <a-grid :cols="2" :col-gap="16">
        <a-grid-item><a-form-item label="Sprint 编号" required><a-input v-model="form.iteration_no" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="Sprint 名称" required><a-input v-model="form.name" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="项目产品" required><ProjectProductSelect v-model="form.project_product" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="负责人" required><a-select v-model="form.owner" :options="userOptions" :field-names="fieldNames" allow-search /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="开始日期" required><a-date-picker v-model="form.start_date" value-format="YYYY-MM-DD" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="结束日期" required><a-date-picker v-model="form.end_date" value-format="YYYY-MM-DD" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="状态" required><a-select v-model="form.status" :options="statusOptions" :field-names="fieldNames" /></a-form-item></a-grid-item>
        <a-grid-item :span="2"><a-form-item label="备注"><a-textarea v-model="form.remark" :auto-size="{ minRows: 3, maxRows: 6 }" /></a-form-item></a-grid-item>
      </a-grid>
    </a-form>
  </a-modal>
</template>

<script lang="ts" setup>
  import { computed, onMounted, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { useRouter } from 'vue-router'
  import TableBody from '@/components/table/TableBody.vue'
  import TableHeader from '@/components/table/TableHeader.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import { usePagination } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'
  import { getUserName } from '@/api/user/user'
  import { formatProjectProductPath } from '@/utils/business-format'
  import {
    deleteFunctionalIteration,
    getFunctionalIterations,
    postFunctionalIteration,
    putFunctionalIteration,
  } from '@/api/functional-test'
  import { emptyIteration, iterationColumns } from './config'
  import { prefillNavigationModel, NavigationCreateSource } from '@/utils/navigation-create-defaults'

  const navigationCreateRef = ref<NavigationCreateSource | null>(null)

  const router = useRouter()
  const enumStore = useEnum()
  const fieldNames = { value: 'key', label: 'title' }
  const rows = ref<any[]>([])
  const userOptions = ref<any[]>([])
  const loading = ref(false)
  const saving = ref(false)
  const visible = ref(false)
  const navigationProjectProduct = ref<number>()
  const form = reactive<any>(emptyIteration())
  const filters = reactive<any>({ project_product: undefined, name: '', status: [], owner: [] })
  const statusOptions = computed(() => (enumStore as any).functional_test_iteration_status || [])
  const pagination = usePagination(loadRows, () => loading)
  const normalize = (value: any) => (Array.isArray(value) ? value[value.length - 1] : value)
  const enumTitle = (options: any[], value: any) => options.find((item) => item.key === value)?.title || '-'
  const formatRate = (value: any) => `${Number(value || 0).toFixed(2).replace(/\.00$/, '')}%`

  async function loadRows() {
    loading.value = true
    try {
      const query: any = { page: pagination.page, pageSize: pagination.pageSize }
      Object.entries(filters).forEach(([key, value]) => {
        const normalized = key === 'project_product' ? normalize(value) : value
        if (Array.isArray(normalized)) {
          if (normalized.length) query[`${key}__in`] = normalized.join(',')
          return
        }
        if (normalized !== '' && normalized !== undefined && normalized !== null) query[key] = normalized
      })
      const res = await getFunctionalIterations(query)
      rows.value = res.data || []
      pagination.total = res.totalSize || 0
    } finally { loading.value = false }
  }
  function search() { pagination.page = 1; loadRows() }
  function reset() { Object.assign(filters, { name: '', status: [], owner: [] }); search() }
  function onNavigationFilterChange(filter: { projectProduct: any }) {
    navigationProjectProduct.value = filter.projectProduct || undefined
    filters.project_product = navigationProjectProduct.value
    search()
  }
  async function openEditor(row?: any) {
    Object.assign(form, emptyIteration(), row ? {
      ...row,
      project_product: row.project_product?.id,
      owner: row.owner?.id,
    } : {})
    if (!row) await prefillNavigationModel(navigationCreateRef.value, form)
    visible.value = true
  }
  async function saveRow() {
    if (!form.iteration_no || !form.name || !normalize(form.project_product) || !form.owner || !form.start_date || !form.end_date) {
      Message.warning('请填写必填字段')
      return false
    }
    saving.value = true
    try {
      const payload = { ...form, project_product: normalize(form.project_product) }
      if (form.id) await putFunctionalIteration(payload)
      else await postFunctionalIteration(payload)
      visible.value = false
      Message.success('保存成功')
      await loadRows()
      return true
    } finally { saving.value = false }
  }
  function removeRow(row: any) {
    Modal.warning({
      title: '删除 Sprint', content: `确认删除「${row.name}」？`, hideCancel: false,
      onBeforeOk: async () => { await deleteFunctionalIteration(row.id); await loadRows() },
    })
  }
  function goDetail(row: any) { router.push({ path: '/functional-test/iteration/details', query: { id: row.id } }) }

  onMounted(async () => {
    await enumStore.getEnum()
    userOptions.value = (await getUserName()).data || []
    await loadRows()
  })
</script>

<style lang="less" scoped>
  .mango-iteration-page__table { display: flex; flex: 1; min-width: 0; min-height: 0; flex-direction: column; overflow: hidden; }
  .mango-iteration-page__metric { display: flex; align-items: center; gap: 8px; }
  .mango-iteration-page__metric :deep(.arco-progress) { min-width: 86px; flex: 1; }
  .mango-iteration-page__metric span { flex: none; color: var(--m-muted); }
</style>
