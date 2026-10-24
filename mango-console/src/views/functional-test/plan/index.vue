<template>
  <TableBody plain class="mango-detail-workbench-page" :sticky-horizontal-scroll="false">
    <template #header>
      <TableHeader title="研发协同 / 测试计划" />
    </template>
    <template #default>
      <ProjectProductNavigationWorkbench
        contained-body
        :sticky-horizontal-scroll="false"
        :model-value="navigationProjectProduct"
        @filter-change="onNavigationFilterChange"
        @search="search"
        @reset-search="reset"
      >
        <template #search>
          <a-form :model="filters" layout="inline" @keyup.enter="search">
            <a-form-item label="计划类型">
              <a-select
                v-model="filters.scope_type"
                :options="enumStore.functional_test_plan_scope_type"
                :field-names="fieldNames"
                multiple
                :max-tag-count="1"
                allow-clear
                placeholder="请选择计划类型"
                @change="search"
              />
            </a-form-item>
            <a-form-item label="计划名称">
              <a-input
                v-model="filters.name"
                allow-clear
                placeholder="请输入计划名称"
                @blur="search"
                @clear="search"
              />
            </a-form-item>
            <a-form-item label="状态">
              <a-select
                v-model="filters.status"
                :options="enumStore.functional_test_plan_status"
                :field-names="fieldNames"
                multiple
                :max-tag-count="1"
                allow-clear
                placeholder="请选择状态"
                @change="search"
              />
            </a-form-item>
          </a-form>
        </template>
        <template #toolbar>
          <a-space>
            <a-button size="small" @click="loadPlans">刷新</a-button>
            <a-button v-permission="'functional.plan:create'" size="small" type="primary" @click="openEditor()">新建计划</a-button>
          </a-space>
        </template>
        <div class="mango-plan-page__table">
          <a-table
            class="mango-native-scroll-table"
            :data="rows"
            :columns="planColumns"
            :loading="loading"
            :pagination="false"
            :scroll="{ x: 2140, y: '100%' }"
            row-key="id"
          >
            <template #name="{ record }"
              ><a-link @click="goDetail(record)">{{ record.name }}</a-link></template
            >
            <template #project_product="{ record }">{{
              formatProjectProductPath(record.project_product)
            }}</template>
            <template #scope_type="{ record }">{{
              enumTitle(enumStore.functional_test_plan_scope_type, record.scope_type)
            }}</template>
            <template #scope_ref="{ record }">{{
              record.scope_type === 0
                ? `${record.requirement_version?.requirement_name || record.requirement_version?.requirement?.name || '-'} · V${record.requirement_version?.version_no || '-'}`
                : record.scope_type === 1
                  ? record.iteration?.name || '-'
                  : record.scope_ref || '-'
            }}</template>
            <template #status="{ record }"
              ><a-tag>{{
                enumTitle(enumStore.functional_test_plan_status, record.status)
              }}</a-tag></template
            >
            <template #execution_progress="{ record }">
              <div v-if="record.case_count" class="mango-plan-page__metric">
                <a-progress
                  :percent="Number(record.execution_stats?.progress || 0) / 100"
                  size="small"
                  :show-text="false"
                />
                <span
                  >{{ record.execution_stats?.executed || 0 }}/{{
                    record.execution_stats?.total || 0
                  }}</span
                >
              </div>
              <span v-else>-</span>
            </template>
            <template #pass_rate="{ record }">
              <a-tooltip v-if="record.case_count" :content="resultSummary(record.execution_stats)">
                <span>{{ formatRate(record.execution_stats?.pass_rate) }}</span>
              </a-tooltip>
              <span v-else>-</span>
            </template>
            <template #owner="{ record }">{{ record.owner?.name || '-' }}</template>
            <template #actions="{ record }">
              <MangoTableActions
                :actions="[
                  { permission: 'functional.plan:detail', label: '进入用例', onClick: () => goDetail(record) },
                  { permission: 'functional.plan:edit', label: '编辑', onClick: () => openEditor(record) },
                  { permission: 'functional.plan:delete', label: '删除', danger: true, onClick: () => removePlan(record) },
                ]"
              />
            </template>
          </a-table>
        </div>
        <template #footer><TableFooter :pagination="pagination" /></template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>

  <a-modal
    v-model:visible="visible"
    :title="form.id ? '编辑测试计划' : '新建测试计划'"
    width="720px"
    :ok-loading="saving"
    @ok="savePlan"
  >
    <a-form :model="form" layout="vertical">
      <a-grid :cols="2" :col-gap="16">
        <a-grid-item :span="2"
          ><a-form-item label="计划名称" required><a-input v-model="form.name" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="项目产品" required
            ><ProjectProductSelect
              v-model="form.project_product"
              @change="onFormProductChange" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="计划类型" required
            ><a-select
              v-model="form.scope_type"
              :options="enumStore.functional_test_plan_scope_type"
              :field-names="fieldNames"
              @change="onScopeTypeChange" /></a-form-item
        ></a-grid-item>
        <a-grid-item v-if="form.scope_type === 0"
          ><a-form-item label="关联需求版本" required
            ><a-select
              v-model="form.requirement_version"
              :options="requirementOptions"
              allow-search
              :loading="requirementLoading"
              placeholder="请选择具体需求版本" /></a-form-item
        ></a-grid-item>
        <a-grid-item v-else-if="form.scope_type === 1"
          ><a-form-item label="关联 Sprint" required
            ><a-select
              v-model="form.iteration"
              :options="iterationOptions"
              allow-search
              :loading="iterationLoading"
              placeholder="请选择 Sprint" /></a-form-item
        ></a-grid-item>
        <a-grid-item v-else
          ><a-form-item label="范围标识"
            ><a-input v-model="form.scope_ref" placeholder="例如 v2.8.0 / 核心回归" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="负责人" required
            ><a-select
              v-model="form.owner"
              :options="userOptions"
              :field-names="fieldNames"
              allow-search /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="测试环境"><a-input v-model="form.environment" placeholder="例如 dev / test" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="构建版本"><a-input v-model="form.build_version" placeholder="例如 2.8.0-rc1" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="计划开始"
            ><a-date-picker
              v-model="form.planned_start_time"
              show-time
              value-format="YYYY-MM-DD HH:mm:ss" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="计划结束"
            ><a-date-picker
              v-model="form.planned_end_time"
              show-time
              value-format="YYYY-MM-DD HH:mm:ss" /></a-form-item
        ></a-grid-item>
        <a-grid-item :span="2"
          ><a-form-item label="备注"><a-textarea v-model="form.remark" /></a-form-item
        ></a-grid-item>
      </a-grid>
    </a-form>
  </a-modal>
</template>

<script lang="ts" setup>
  import { onMounted, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { useRoute, useRouter } from 'vue-router'
  import TableBody from '@/components/table/TableBody.vue'
  import TableHeader from '@/components/table/TableHeader.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { usePagination } from '@/hooks/table'
  import { getUserName } from '@/api/user/user'
  import { formatProjectProductPath } from '@/utils/business-format'
  import {
    deleteFunctionalPlan,
    getFunctionalPlans,
    getFunctionalRequirements,
    getFunctionalIterations,
    postFunctionalPlan,
    putFunctionalPlan,
  } from '@/api/functional-test'
  import { emptyPlan, planColumns } from './config'

  const router = useRouter()
  const route = useRoute()
  const enumStore = useEnum()
  const fieldNames = { value: 'key', label: 'title' }
  const rows = ref<any[]>([])
  const loading = ref(false)
  const saving = ref(false)
  const visible = ref(false)
  const form = reactive<any>(emptyPlan())
  const filters = reactive<any>({
    project_product: undefined,
    scope_type: [],
    name: '',
    status: [],
  })
  const navigationProjectProduct = ref<number>()
  const userOptions = ref<any[]>([])
  const requirementOptions = ref<any[]>([])
  const requirementLoading = ref(false)
  const iterationOptions = ref<any[]>([])
  const iterationLoading = ref(false)
  const pagination = usePagination(loadPlans, () => loading)
  const normalize = (value: any) => (Array.isArray(value) ? value[value.length - 1] : value)
  const enumTitle = (options: any[], value: any) =>
    options.find((item) => item.key === value)?.title || '-'

  async function loadPlans() {
    loading.value = true
    try {
      const query: any = { page: pagination.page, pageSize: pagination.pageSize }
      Object.entries(filters).forEach(([key, value]) => {
        const normalized = key === 'project_product' ? normalize(value) : value
        if (Array.isArray(normalized)) {
          if (normalized.length) query[`${key}__in`] = normalized.join(',')
          return
        }
        if (normalized !== '' && normalized !== undefined && normalized !== null)
          query[key] = normalized
      })
      const res = await getFunctionalPlans(query)
      rows.value = res.data || []
      pagination.total = res.totalSize || 0
    } finally {
      loading.value = false
    }
  }
  function search() {
    pagination.page = 1
    loadPlans()
  }
  function reset() {
    Object.assign(filters, { scope_type: [], name: '', status: [] })
    search()
  }
  function onNavigationFilterChange(filter: { projectProduct: any }) {
    navigationProjectProduct.value = filter.projectProduct || undefined
    filters.project_product = navigationProjectProduct.value
    search()
  }
  async function loadRequirements() {
    const projectProduct = normalize(form.project_product)
    requirementOptions.value = []
    if (!projectProduct) return
    requirementLoading.value = true
    try {
      const res = await getFunctionalRequirements({
        project_product: projectProduct,
        page: 1,
        pageSize: 500,
      })
      requirementOptions.value = (res.data || []).map((item: any) => ({
        label: `${item.name} · V${item.version_no || '-'}`,
        value: item.id,
      }))
    } finally {
      requirementLoading.value = false
    }
  }
  async function loadIterations() {
    const projectProduct = normalize(form.project_product)
    iterationOptions.value = []
    if (!projectProduct) return
    iterationLoading.value = true
    try {
      const res = await getFunctionalIterations({ project_product: projectProduct, page: 1, pageSize: 500 })
      iterationOptions.value = (res.data || []).map((item: any) => ({ label: `${item.iteration_no} ${item.name}`, value: item.id }))
    } finally { iterationLoading.value = false }
  }
  async function onFormProductChange() {
    form.requirement_version = undefined
    form.iteration = undefined
    await Promise.all([loadRequirements(), loadIterations()])
  }
  function onScopeTypeChange() {
    form.scope_ref = ''
    if (form.scope_type !== 0) form.requirement_version = undefined
    if (form.scope_type !== 1) form.iteration = undefined
  }
  async function openEditor(row?: any) {
    Object.assign(
      form,
      emptyPlan(),
      row
        ? {
            ...row,
            project_product: row.project_product?.id,
            owner: row.owner?.id,
            requirement_version: row.requirement_version?.id || row.requirement_version,
            iteration: row.iteration?.id || row.iteration,
          }
        : {}
    )
    await Promise.all([loadRequirements(), loadIterations()])
    visible.value = true
  }
  async function savePlan() {
    if (
      !form.name ||
      !normalize(form.project_product) ||
      !form.owner ||
      (form.scope_type === 0 && !form.requirement_version) ||
      (form.scope_type === 1 && !form.iteration)
    ) {
      Message.warning('请填写必填字段')
      return false
    }
    saving.value = true
    try {
      const payload = { ...form, project_product: normalize(form.project_product) }
      if (form.scope_type !== 0) payload.requirement_version = null
      if (form.scope_type !== 1) payload.iteration = null
      if (form.id) await putFunctionalPlan(payload)
      else await postFunctionalPlan(payload)
      visible.value = false
      Message.success('保存成功')
      await loadPlans()
      return true
    } finally {
      saving.value = false
    }
  }
  function removePlan(row: any) {
    Modal.warning({
      title: '删除测试计划',
      content: `确认删除「${row.name}」及其计划用例和执行结果？`,
      hideCancel: false,
      onBeforeOk: async () => {
        await deleteFunctionalPlan(row.id)
        await loadPlans()
      },
    })
  }
  function goDetail(row: any) {
    router.push({ path: '/functional-test/plan/details', query: { id: row.id } })
  }
  async function openRouteCreate() {
    if (route.query.create !== '1') return
    Object.assign(form, emptyPlan(), {
      project_product: Number(route.query.project_product) || undefined,
      scope_type: 0,
      requirement_version: Number(route.query.requirement_version) || undefined,
    })
    await Promise.all([loadRequirements(), loadIterations()])
    visible.value = true
  }
  function formatRate(value: any) {
    return `${Number(value || 0)
      .toFixed(2)
      .replace(/\.00$/, '')}%`
  }
  function resultSummary(stats: any) {
    return `通过 ${stats?.passed || 0}，失败 ${stats?.failed || 0}，阻塞 ${
      stats?.blocked || 0
    }，跳过 ${stats?.skipped || 0}`
  }
  onMounted(async () => {
    await enumStore.getEnum()
    userOptions.value = (await getUserName()).data || []
    await loadPlans()
    await openRouteCreate()
  })
</script>

<style lang="less" scoped>
  .mango-plan-page__table {
    display: flex;
    flex: 1;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
    overflow: hidden;
  }
  .mango-plan-page__metric {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .mango-plan-page__metric :deep(.arco-progress) {
    min-width: 92px;
    flex: 1;
  }
  .mango-plan-page__metric span {
    flex: none;
    color: var(--m-text-3);
  }
</style>
