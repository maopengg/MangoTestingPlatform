<template>
  <TableBody plain class="mango-detail-workbench-page" :sticky-horizontal-scroll="false">
    <template #header><TableHeader title="研发协同 / 缺陷管理" /></template>
    <template #default>
      <ProjectProductNavigationWorkbench
        contained-body show-modules :sticky-horizontal-scroll="false"
        :model-value="navigationProjectProduct" :module-value="navigationModule"
        @filter-change="onNavigationFilterChange" @search="search" @reset-search="reset"
      >
        <template #search>
          <a-form :model="filters" layout="inline" @keyup.enter="search">
            <a-form-item label="关键词"><a-input v-model="filters.keyword" allow-clear placeholder="编号或标题" /></a-form-item>
            <a-form-item label="状态"><a-select v-model="filters.status" :options="statusOptions" :field-names="fieldNames" allow-clear /></a-form-item>
            <a-form-item label="严重程度"><a-select v-model="filters.severity" :options="severityOptions" :field-names="fieldNames" allow-clear /></a-form-item>
            <a-form-item label="优先级"><a-select v-model="filters.priority" :options="priorityOptions" :field-names="fieldNames" allow-clear /></a-form-item>
            <a-form-item label="缺陷类型"><a-select v-model="filters.defect_type" :options="typeOptions" :field-names="fieldNames" allow-clear /></a-form-item>
            <a-form-item label="缺陷来源"><a-select v-model="filters.source_type" :options="sourceOptions" :field-names="fieldNames" allow-clear /></a-form-item>
            <a-form-item label="经办人"><a-select v-model="filters.assignee" :options="userOptions" :field-names="fieldNames" allow-search allow-clear /></a-form-item>
            <a-form-item label="报告人"><a-select v-model="filters.reporter" :options="userOptions" :field-names="fieldNames" allow-search allow-clear /></a-form-item>
            <a-form-item label="来源计划"><a-select v-model="filters.source_plan" :options="searchPlanOptions" allow-search allow-clear /></a-form-item>
            <a-form-item label="创建日期"><a-range-picker v-model="filters.create_range" value-format="YYYY-MM-DD" allow-clear /></a-form-item>
            <a-form-item label="更新日期"><a-range-picker v-model="filters.update_range" value-format="YYYY-MM-DD" allow-clear /></a-form-item>
          </a-form>
        </template>
        <template #toolbar>
          <a-space>
            <a-popover trigger="click" position="br">
              <a-button size="small">列设置</a-button>
              <template #content>
                <div class="mango-defect-page__column-settings">
                  <div v-for="(column, index) in configuredColumns" :key="columnKey(column)" class="mango-defect-page__column-setting">
                    <a-checkbox :model-value="column.visible !== false" :disabled="column.slotName === 'actions'" @change="setColumnVisible(index, $event)">{{ column.title }}</a-checkbox>
                    <a-space :size="2"><a-button size="mini" :disabled="index === 0" @click="moveColumn(index, -1)">上移</a-button><a-button size="mini" :disabled="index === configuredColumns.length - 1" @click="moveColumn(index, 1)">下移</a-button></a-space>
                  </div>
                  <a-button size="mini" long @click="resetColumns">恢复默认</a-button>
                </div>
              </template>
            </a-popover>
            <a-button size="small" :loading="loading" @click="loadRows">刷新</a-button>
            <a-button  size="small" type="primary" @click="openEditor()">新建缺陷</a-button>
          </a-space>
        </template>
        <div class="mango-defect-page__stats">
          <span>未关闭 <strong>{{ stats.open_count || 0 }}</strong></span>
          <span>我的待处理 <strong>{{ stats.my_pending_count || 0 }}</strong></span>
          <span>致命/严重 <strong>{{ stats.serious_count || 0 }}</strong></span>
          <span>已解决待验证 <strong>{{ stats.resolved_pending_count || 0 }}</strong></span>
        </div>
        <div class="mango-defect-page__table">
          <a-table class="mango-native-scroll-table" :data="rows" :columns="visibleColumns" :loading="loading" :pagination="false" :scroll="{ x: tableWidth, y: '100%' }" row-key="id">
            <template #defect_no="{ record }"><a-link @click="openEditor(record)">{{ record.defect_no }}</a-link></template>
            <template #status="{ record }">
              <a-select :class="['mango-defect-page__quick-select', enumToneClass('status', record.status)]" :model-value="record.status" :options="statusQuickOptions(record)" :loading="record._saving === 'status'" @change="quickStatus(record, $event)" />
            </template>
            <template #severity="{ record }"><a-select :class="['mango-defect-page__quick-select', enumToneClass('severity', record.severity)]" :model-value="record.severity" :options="enumSelectOptions(severityOptions)" :loading="record._saving === 'severity'" @change="quickUpdate(record, 'severity', $event)" /></template>
            <template #priority="{ record }"><a-select :class="['mango-defect-page__quick-select', enumToneClass('priority', record.priority)]" :model-value="record.priority" :options="enumSelectOptions(priorityOptions)" :loading="record._saving === 'priority'" @change="quickUpdate(record, 'priority', $event)" /></template>
            <template #defect_type="{ record }">{{ enumTitle(typeOptions, record.defect_type) }}</template>
            <template #source_type="{ record }">{{ enumTitle(sourceOptions, record.source_type) }}</template>
            <template #assignee="{ record }"><a-select class="mango-defect-page__quick-select" :model-value="record.assignee?.id" :options="userOptions" :field-names="fieldNames" allow-search allow-clear :loading="record._saving === 'assignee'" @change="quickUpdate(record, 'assignee', $event)" /></template>
            <template #reporter="{ record }">{{ record.reporter?.name || '-' }}</template>
            <template #module="{ record }">{{ formatModulePath(record.module) }}</template>
            <template #project_product="{ record }">{{ formatProjectProductPath(record.project_product) }}</template>
            <template #relations="{ record }">{{ record.relation_count ?? record.relations?.length ?? 0 }}</template>
            <template #actions="{ record }">
              <MangoTableActions :actions="[
    { label: '编辑', onClick: () => openEditor(record) },
    { label: '流转', disabled: !nextStatuses(record).length, onClick: () => openTransition(record) },
    { label: '创建重测计划', disabled: !(record.relation_count ?? record.relations?.length), onClick: () => openRetest(record) },
    { label: '删除', danger: true, onClick: () => removeRow(record) },
]" />
            </template>
          </a-table>
        </div>
        <template #footer><TableFooter :pagination="pagination" /></template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>

  <a-drawer v-model:visible="visible" :title="form.id ? `编辑缺陷 ${form.defect_no}` : '新建缺陷'" width="760px" :ok-loading="saving" @ok="saveRow">
    <a-form :model="form" layout="vertical">
      <a-grid :cols="2" :col-gap="16">
        <a-grid-item :span="2"><div class="mango-section-title">基本信息</div></a-grid-item>
        <a-grid-item v-if="form.id" :span="2">
          <div class="mango-defect-page__readonly-meta">
            <span>状态：{{ enumTitle(statusOptions, form.status) }}</span>
            <span>报告人：{{ form.reporter?.name || '-' }}</span>
            <span>创建：{{ form.create_time || '-' }}</span>
            <span>更新：{{ form.update_time || '-' }}</span>
          </div>
        </a-grid-item>
        <a-grid-item :span="2"><a-form-item label="缺陷标题" required><a-input v-model="form.title" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="项目产品" required><ProjectProductSelect v-model="form.project_product" @change="onFormProductChange" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="模块"><ProductModuleSelect v-model="form.module" :project-product-id="form.project_product" :auto-clear="false" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="缺陷来源" required><a-select v-model="form.source_type" :options="sourceOptions" :field-names="fieldNames" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="缺陷类型" required><a-select v-model="form.defect_type" :options="typeOptions" :field-names="fieldNames" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="严重程度" required><a-select v-model="form.severity" :options="severityOptions" :field-names="fieldNames" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="优先级" required><a-select v-model="form.priority" :options="priorityOptions" :field-names="fieldNames" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="经办人"><a-select v-model="form.assignee" :options="userOptions" :field-names="fieldNames" allow-search allow-clear /></a-form-item></a-grid-item>
        <a-grid-item v-if="form.id"><a-form-item label="解决方式"><span>{{ enumTitle(resolutionOptions, form.resolution) }}</span></a-form-item></a-grid-item>
        <a-grid-item v-if="form.id" :span="2"><a-form-item label="解决说明"><span>{{ form.resolution_note || '-' }}</span></a-form-item></a-grid-item>
        <a-grid-item v-if="form.id" :span="2"><div class="mango-defect-page__readonly-meta"><span>解决时间：{{ form.resolved_at || '-' }}</span><span>关闭时间：{{ form.closed_at || '-' }}</span></div></a-grid-item>
        <a-grid-item :span="2"><div class="mango-section-title">问题内容</div></a-grid-item>
        <a-grid-item :span="2"><a-form-item label="问题描述"><a-textarea v-model="form.description" :auto-size="{ minRows: 2, maxRows: 5 }" /></a-form-item></a-grid-item>
        <a-grid-item :span="2"><a-form-item label="前置条件"><a-textarea v-model="form.precondition" :auto-size="{ minRows: 2, maxRows: 4 }" /></a-form-item></a-grid-item>
        <a-grid-item :span="2">
          <a-form-item label="复现步骤">
            <div class="mango-defect-page__steps">
              <div v-for="(step, index) in form.reproduce_steps" :key="index" class="mango-defect-page__step">
                <span>{{ index + 1 }}</span><a-input v-model="step.action" placeholder="操作" /><a-input v-model="step.expected" placeholder="预期" /><a-input v-model="step.actual" placeholder="实际" />
                <a-button size="mini" status="danger" @click="form.reproduce_steps.splice(index, 1)">删除</a-button>
              </div>
              <a-button size="small" @click="addStep">添加步骤</a-button>
            </div>
          </a-form-item>
        </a-grid-item>
        <a-grid-item :span="2"><a-form-item label="预期结果"><a-textarea v-model="form.expected_result" :auto-size="{ minRows: 2, maxRows: 4 }" /></a-form-item></a-grid-item>
        <a-grid-item :span="2"><a-form-item label="实际结果" required><a-textarea v-model="form.actual_result" :auto-size="{ minRows: 2, maxRows: 5 }" /></a-form-item></a-grid-item>
        <a-grid-item :span="2"><a-form-item label="环境信息"><a-textarea v-model="form.environment" :auto-size="{ minRows: 2, maxRows: 4 }" /></a-form-item></a-grid-item>
        <a-grid-item :span="2">
          <a-form-item label="附件">
            <div class="mango-defect-page__attachments">
              <a-space v-if="form.attachment_file_ids?.length" wrap>
                <a-tag v-for="fileId in form.attachment_file_ids" :key="fileId" closable @close="removeAttachment(fileId)">File #{{ fileId }}</a-tag>
              </a-space>
              <a-upload v-model:file-list="attachmentFileList" multiple :auto-upload="false" @change="onAttachmentChange" />
            </div>
          </a-form-item>
        </a-grid-item>
        <a-grid-item :span="2"><div class="mango-section-title">关联信息</div></a-grid-item>
        <a-grid-item :span="2"><a-form-item label="关联用例库用例"><a-select v-model="form.case_ids" :options="caseOptions" multiple allow-search allow-clear :loading="relationLoading" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="发现于测试计划"><a-select v-model="form.source_plan_id" :options="planOptions" allow-search allow-clear :loading="relationLoading" @change="loadPlanCases" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="关联计划用例"><a-select v-model="form.plan_case_ids" :options="planCaseOptions" multiple allow-search allow-clear :loading="planCaseLoading" /></a-form-item></a-grid-item>
        <a-grid-item v-if="form.relations?.length" :span="2">
          <div class="mango-defect-page__relation-list">
            <div v-for="relation in form.relations" :key="relation.id" class="mango-defect-page__relation-item">
              <div><strong>{{ relation.case_no || '-' }}</strong> {{ relation.case_title || '-' }}</div>
              <small v-if="relation.plan_case">发现于 {{ relation.plan_name || `计划 #${relation.plan_id}` }}，结果 {{ enumTitle(enumStore.functional_test_result || [], relation.result) }}，执行人 {{ relation.executor_name || '-' }}，{{ relation.execute_time || '-' }}</small>
              <small v-else>来自用例库</small>
            </div>
          </div>
        </a-grid-item>
      </a-grid>
    </a-form>
  </a-drawer>

  <a-modal v-model:visible="transitionVisible" title="流转缺陷" width="560px" :ok-loading="transitionSaving" @ok="saveTransition">
    <a-form :model="transitionForm" layout="vertical">
      <a-form-item label="目标状态" required><a-select v-model="transitionForm.status" :options="transitionOptions" /></a-form-item>
      <a-form-item v-if="transitionForm.status === 2" label="经办人" required><a-select v-model="transitionForm.assignee" :options="userOptions" :field-names="fieldNames" allow-search /></a-form-item>
      <template v-if="[3, 4].includes(transitionForm.status)">
        <a-form-item label="解决方式" required><a-select v-model="transitionForm.resolution" :options="resolutionOptions" :field-names="fieldNames" /></a-form-item>
        <a-form-item label="解决说明"><a-textarea v-model="transitionForm.resolution_note" /></a-form-item>
      </template>
    </a-form>
  </a-modal>

  <a-modal v-model:visible="retestVisible" title="创建缺陷验证计划" width="720px" :ok-loading="retestSaving" @ok="createRetestPlan">
    <a-form :model="retestForm" layout="vertical">
      <a-grid :cols="2" :col-gap="16">
        <a-grid-item :span="2"><a-form-item label="计划名称" required><a-input v-model="retestForm.name" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="负责人" required><a-select v-model="retestForm.owner" :options="userOptions" :field-names="fieldNames" allow-search /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="测试环境"><a-input v-model="retestForm.environment" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="构建版本"><a-input v-model="retestForm.build_version" /></a-form-item></a-grid-item>
        <a-grid-item :span="2"><a-alert type="info">将使用缺陷当前关联的用例创建一次新的测试计划，不会修改原计划和历史结果。</a-alert></a-grid-item>
      </a-grid>
    </a-form>
  </a-modal>
</template>

<script lang="ts" setup>
  import { computed, onMounted, reactive, ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { useRoute, useRouter } from 'vue-router'
  import TableBody from '@/components/table/TableBody.vue'
  import TableHeader from '@/components/table/TableHeader.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import { usePagination } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'
  import { getUserName } from '@/api/user/user'
  import { postUserFile } from '@/api/system/file_data'
  import { formatModulePath, formatProjectProductPath } from '@/utils/business-format'
  import {
    createFunctionalDefectRetestPlan, deleteFunctionalDefect, getFunctionalDefectDetail, getFunctionalDefectStats,
    getFunctionalDefects, getFunctionalPlanCases, getFunctionalPlans,
    getManualCase, postFunctionalDefect, putFunctionalDefect, transitionFunctionalDefect,
  } from '@/api/functional-test'
  import { defectColumns, defectStatusTransitions, emptyDefect } from './config'

  const enumStore = useEnum()
  const route = useRoute()
  const router = useRouter()
  const fieldNames = { value: 'key', label: 'title' }
  const rows = ref<any[]>([])
  const userOptions = ref<any[]>([])
  const caseOptions = ref<any[]>([])
  const planOptions = ref<any[]>([])
  const planCaseOptions = ref<any[]>([])
  const planCaseRows = ref<any[]>([])
  const libraryCaseRows = ref<any[]>([])
  const searchPlanOptions = ref<any[]>([])
  const stats = reactive<any>({})
  const COLUMN_STORAGE_KEY = 'mango-functional-defect-columns'
  const configuredColumns = ref<any[]>([])
  const attachmentFileList = ref<any[]>([])
  const loading = ref(false), saving = ref(false), relationLoading = ref(false), planCaseLoading = ref(false)
  const visible = ref(false), transitionVisible = ref(false), transitionSaving = ref(false)
  const retestVisible = ref(false), retestSaving = ref(false)
  const navigationProjectProduct = ref<any>(), navigationModule = ref<any>()
  const form = reactive<any>(emptyDefect())
  const transitionForm = reactive<any>({ id: undefined, status: undefined, assignee: undefined, resolution: undefined, resolution_note: '' })
  const retestForm = reactive<any>({ id: undefined, name: '', owner: undefined, environment: '', build_version: '' })
  const filters = reactive<any>({
    project_product: undefined, module: undefined, keyword: '', status: undefined,
    severity: undefined, priority: undefined, defect_type: undefined, source_type: undefined,
    assignee: undefined, reporter: undefined, source_plan: undefined,
    create_range: [], update_range: [],
  })
  const sourceOptions = computed(() => (enumStore as any).functional_test_defect_source || [])
  const typeOptions = computed(() => (enumStore as any).functional_test_defect_type || [])
  const severityOptions = computed(() => (enumStore as any).functional_test_defect_severity || [])
  const priorityOptions = computed(() => (enumStore as any).functional_test_defect_priority || [])
  const statusOptions = computed(() => (enumStore as any).functional_test_defect_status || [])
  const resolutionOptions = computed(() => (enumStore as any).functional_test_defect_resolution || [])
  const visibleColumns = computed(() => configuredColumns.value.filter((item) => item.visible !== false))
  const tableWidth = computed(() => visibleColumns.value.reduce((total, item) => total + Number(item.width || 140), 0))
  const transitionOptions = computed(() => nextStatuses(transitionForm).map((value) => ({ value, label: enumTitle(statusOptions.value, value) })))
  const pagination = usePagination(loadRows, () => loading)
  const normalize = (value: any) => (Array.isArray(value) ? value[value.length - 1] : value)
  const enumTitle = (options: any[], value: any) => options.find((item) => item.key === value)?.title || '-'
  const enumSelectOptions = (options: any[]) => options.map((item) => ({ value: item.key, label: item.title }))
  function enumToneClass(kind: string, value: number) {
    if (kind === 'status') return `is-status-${value}`
    if (kind === 'severity') return `is-severity-${value}`
    return `is-priority-${value}`
  }
  async function refreshStats() {
    const res = await getFunctionalDefectStats({
      project_product: normalize(filters.project_product),
      module: normalize(filters.module),
    })
    Object.assign(stats, res.data || {})
  }

  async function loadRows() {
    loading.value = true
    try {
      const query: any = { page: pagination.page, pageSize: pagination.pageSize }
      Object.entries(filters).forEach(([key, value]) => {
        if (['create_range', 'update_range'].includes(key)) return
        const normalized = ['project_product', 'module'].includes(key) ? normalize(value) : value
        if (normalized !== '' && normalized !== undefined && normalized !== null) query[key] = normalized
      })
      if (filters.update_range?.length === 2) {
        query.update_time_start = filters.update_range[0]
        query.update_time_end = filters.update_range[1]
      }
      if (filters.create_range?.length === 2) {
        query.create_time_start = filters.create_range[0]
        query.create_time_end = filters.create_range[1]
      }
      const [res, statsRes] = await Promise.all([
        getFunctionalDefects(query),
        getFunctionalDefectStats({ project_product: normalize(filters.project_product), module: normalize(filters.module) }),
      ])
      rows.value = res.data || []; pagination.total = res.totalSize || 0
      Object.assign(stats, statsRes.data || {})
    } finally { loading.value = false }
  }
  function search() { pagination.page = 1; loadRows() }
  function reset() {
    Object.assign(filters, {
      keyword: '', status: undefined, severity: undefined, priority: undefined,
      defect_type: undefined, source_type: undefined, assignee: undefined,
      reporter: undefined, source_plan: undefined, create_range: [], update_range: [],
    })
    search()
  }
  const columnKey = (column: any) => String(column.dataIndex || column.slotName)
  function restoreColumns() {
    let saved: any[] = []
    try { saved = JSON.parse(localStorage.getItem(COLUMN_STORAGE_KEY) || '[]') } catch { saved = [] }
    const byKey = new Map(defectColumns.map((item: any) => [columnKey(item), { ...item }]))
    const restored = saved.map((item: any) => {
      const base = byKey.get(item.key)
      if (!base) return undefined
      byKey.delete(item.key)
      return { ...base, visible: item.visible !== false }
    }).filter(Boolean)
    configuredColumns.value = [...restored, ...byKey.values()]
  }
  function setColumnVisible(index: number, value: boolean) { configuredColumns.value[index].visible = value }
  function moveColumn(index: number, offset: number) {
    const target = index + offset
    if (target < 0 || target >= configuredColumns.value.length) return
    const next = [...configuredColumns.value]
    ;[next[index], next[target]] = [next[target], next[index]]
    configuredColumns.value = next
  }
  function resetColumns() { configuredColumns.value = defectColumns.map((item: any) => ({ ...item })) }
  watch(configuredColumns, (value) => localStorage.setItem(COLUMN_STORAGE_KEY, JSON.stringify(
    value.map((item) => ({ key: columnKey(item), visible: item.visible !== false })),
  )), { deep: true })
  async function loadSearchPlans() {
    const query: any = { page: 1, pageSize: 500 }
    const product = normalize(filters.project_product)
    if (product) query.project_product = product
    const res = await getFunctionalPlans(query)
    searchPlanOptions.value = (res.data || []).map((item: any) => ({ value: item.id, label: item.name }))
  }
  function onNavigationFilterChange(filter: any) {
    navigationProjectProduct.value = filter.projectProduct || undefined
    navigationModule.value = filter.module || undefined
    filters.project_product = navigationProjectProduct.value
    filters.module = navigationModule.value
    filters.source_plan = undefined
    loadSearchPlans()
    search()
  }
  async function loadRelations() {
    const product = normalize(form.project_product); caseOptions.value = []; planOptions.value = []; planCaseOptions.value = []
    if (!product) return
    relationLoading.value = true
    try {
      const [casesRes, plansRes] = await Promise.all([getManualCase({ project_product: product, page: 1, pageSize: 500 }), getFunctionalPlans({ project_product: product, page: 1, pageSize: 500 })])
      libraryCaseRows.value = casesRes.data || []
      caseOptions.value = libraryCaseRows.value.map((item: any) => ({ value: item.id, label: `${item.case_no} ${item.title}` }))
      planOptions.value = (plansRes.data || []).map((item: any) => ({
        value: item.id, label: item.name, environment: item.environment || '',
      }))
    } finally { relationLoading.value = false }
  }
  async function loadPlanCases() {
    form.plan_case_ids = []
    planCaseOptions.value = []
    planCaseRows.value = []
    if (!form.source_plan_id) return
    planCaseLoading.value = true
    try {
      const res = await getFunctionalPlanCases(form.source_plan_id)
      planCaseRows.value = res.data || []
      planCaseOptions.value = planCaseRows.value.map((item: any) => ({ value: item.id, label: `${item.case_no} ${item.title}` }))
    } finally { planCaseLoading.value = false }
  }
  async function onFormProductChange() { form.module = undefined; form.case_ids = []; form.source_plan_id = undefined; form.plan_case_ids = []; await loadRelations() }
  async function openEditor(row?: any) {
    const relations = row?.relations || []
    Object.assign(form, emptyDefect(), row ? { ...row, project_product: row.project_product?.id, module: row.module?.id, assignee: row.assignee?.id, case_ids: relations.filter((item: any) => item.case).map((item: any) => item.case), plan_case_ids: relations.filter((item: any) => item.plan_case).map((item: any) => item.plan_case), source_plan_id: relations.find((item: any) => item.plan_id)?.plan_id } : {})
    await loadRelations()
    attachmentFileList.value = []
    if (form.source_plan_id) { const selected = [...form.plan_case_ids]; await loadPlanCases(); form.plan_case_ids = selected }
    visible.value = true
  }
  async function openEditorFromPlan() {
    const productId = Number(route.query.project_product)
    const requirementVersion = Number(route.query.requirement_version)
    const planId = Number(route.query.plan_id)
    const planCaseIds = String(route.query.plan_case_ids || route.query.plan_case_id || '').split(',').map(Number).filter(Boolean)
    const caseIds = String(route.query.case_ids || '').split(',').map(Number).filter(Boolean)
    if (!productId || (!requirementVersion && !caseIds.length && (!planId || !planCaseIds.length))) return
    Object.assign(form, emptyDefect(), {
      project_product: productId,
      requirement_version: requirementVersion || undefined,
      source_type: caseIds.length ? 1 : 0,
      source_plan_id: planId || undefined,
      case_ids: caseIds,
    })
    await loadRelations()
    if (planId && planCaseIds.length) {
      await loadPlanCases()
      form.plan_case_ids = planCaseIds
      const first = planCaseRows.value.find((item: any) => item.id === planCaseIds[0])
      if (first) fillFromCase(first, true)
    } else if (caseIds.length) {
      const first = libraryCaseRows.value.find((item: any) => item.id === caseIds[0])
      if (first) fillFromCase(first, false)
    }
    visible.value = true
  }
  async function openRouteDefect() {
    const defectId = Number(route.query.defect_id)
    if (!defectId) return false
    const res = await getFunctionalDefectDetail(defectId)
    await openEditor(res.data)
    return true
  }
  function fillFromCase(item: any, fromPlan: boolean) {
    form.module = item.module_id || item.module?.id || form.module
    form.title = form.title || `[缺陷] ${item.title || item.case_no || ''}`
    form.precondition = form.precondition || item.precondition || ''
    form.reproduce_steps = (item.test_steps || []).map((step: any, index: number) => ({
      sort: index + 1,
      action: step.action || '',
      expected: step.expected || '',
      actual: '',
    }))
    form.expected_result = form.expected_result || item.expected_result || ''
    if (fromPlan) {
      form.actual_result = form.actual_result || item.actual_result || ''
      const plan = planOptions.value.find((option: any) => option.value === form.source_plan_id)
      form.environment = form.environment || plan?.environment || ''
    }
  }
  function addStep() { form.reproduce_steps.push({ sort: form.reproduce_steps.length + 1, action: '', expected: '', actual: '' }) }
  function onAttachmentChange(fileList: any[]) { attachmentFileList.value = fileList }
  function removeAttachment(fileId: number) {
    form.attachment_file_ids = (form.attachment_file_ids || []).filter((item: number) => item !== fileId)
  }
  async function uploadAttachments() {
    const pendingFiles = attachmentFileList.value.map((item: any) => item.file).filter(Boolean)
    if (!pendingFiles.length) return
    const productId = normalize(form.project_product)
    const uploaded = await Promise.all(pendingFiles.map(async (file: File) => {
      const data = new FormData()
      data.append('test_file', file)
      data.append('type', '0')
      data.append('name', `${Date.now()}-${file.name}`)
      if (productId) data.append('project_product', String(productId))
      return (await postUserFile(data)).data?.id
    }))
    form.attachment_file_ids = [...new Set([...(form.attachment_file_ids || []), ...uploaded.filter(Boolean)])]
    attachmentFileList.value = []
  }
  async function saveRow() {
    if (!form.title || !normalize(form.project_product) || !form.actual_result) { Message.warning('请填写必填字段'); return false }
    saving.value = true
    try {
      await uploadAttachments()
      const payload: any = { ...form, project_product: normalize(form.project_product), module: normalize(form.module), reproduce_steps: form.reproduce_steps.map((item: any, index: number) => ({ ...item, sort: index + 1 })) }
      delete payload.source_plan_id; delete payload.relations; delete payload.reporter; delete payload.update_user
      const res = form.id ? await putFunctionalDefect(payload) : await postFunctionalDefect(payload)
      const saved = res.data || {}
      const index = rows.value.findIndex((item: any) => item.id === saved.id)
      if (index >= 0) rows.value[index] = saved
      else { rows.value.unshift(saved); pagination.total += 1 }
      visible.value = false; Message.success('保存成功')
      await refreshStats()
      return true
    } finally { saving.value = false }
  }
  function nextStatuses(row: any) { return defectStatusTransitions[Number(row.currentStatus ?? row.status)] || [] }
  function openTransition(row: any) { Object.assign(transitionForm, { id: row.id, currentStatus: row.status, status: undefined, assignee: row.assignee?.id, resolution: row.resolution, resolution_note: row.resolution_note || '' }); transitionVisible.value = true }
  async function saveTransition() {
    if (transitionForm.status === undefined) { Message.warning('请选择目标状态'); return false }
    transitionSaving.value = true
    try {
      const res = await transitionFunctionalDefect({ ...transitionForm })
      patchRow(res.data)
      transitionVisible.value = false
      Message.success('状态已更新')
      await refreshStats()
      return true
    } finally { transitionSaving.value = false }
  }
  function patchRow(saved: any) {
    if (!saved?.id) return
    const index = rows.value.findIndex((item: any) => item.id === saved.id)
    if (index >= 0) rows.value[index] = { ...rows.value[index], ...saved, _saving: undefined }
  }
  async function quickUpdate(row: any, field: string, value: any) {
    const oldValue = field === 'assignee' ? row.assignee?.id : row[field]
    row._saving = field
    try {
      const res = await putFunctionalDefect({ id: row.id, [field]: value })
      patchRow(res.data)
      await refreshStats()
    } catch (error) {
      if (field === 'assignee') row.assignee = userOptions.value.find((item: any) => item.key === oldValue)
      else row[field] = oldValue
      throw error
    } finally { row._saving = undefined }
  }
  function statusQuickOptions(row: any) {
    const allowed = new Set([Number(row.status), ...nextStatuses(row)])
    return enumSelectOptions(statusOptions.value).filter((item: any) => allowed.has(Number(item.value)))
  }
  async function quickStatus(row: any, value: any) {
    const target = Number(value)
    if (target === Number(row.status)) return
    if ([2, 3, 4].includes(target)) {
      openTransition(row)
      transitionForm.status = target
      return
    }
    row._saving = 'status'
    try {
      patchRow((await transitionFunctionalDefect({ id: row.id, status: target })).data)
      await refreshStats()
    }
    finally { row._saving = undefined }
  }
  function openRetest(row: any) {
    Object.assign(retestForm, {
      id: row.id,
      name: `${row.defect_no} 缺陷验证`,
      owner: row.assignee?.id,
      environment: row.environment || '',
      build_version: '',
    })
    retestVisible.value = true
  }
  async function createRetestPlan() {
    if (!retestForm.name || !retestForm.owner) { Message.warning('请填写计划名称和负责人'); return false }
    retestSaving.value = true
    try {
      const res = await createFunctionalDefectRetestPlan({ ...retestForm })
      retestVisible.value = false
      Message.success('重测计划已创建')
      await router.push({ path: '/functional-test/plan/details', query: { id: res.data?.id } })
      return true
    } finally { retestSaving.value = false }
  }
  function removeRow(row: any) { Modal.warning({ title: '删除缺陷', content: `确认删除「${row.defect_no} ${row.title}」？`, hideCancel: false, onBeforeOk: async () => { await deleteFunctionalDefect(row.id); await loadRows() } }) }
  onMounted(async () => {
    restoreColumns()
    await enumStore.getEnum()
    userOptions.value = (await getUserName()).data || []
    await loadSearchPlans()
    await loadRows()
    if (!(await openRouteDefect())) await openEditorFromPlan()
  })
</script>

<style lang="less" scoped>
  .mango-defect-page__table { display: flex; flex: 1; min-width: 0; min-height: 0; flex-direction: column; overflow: hidden; }
  .mango-defect-page__stats { display: flex; flex: none; align-items: center; gap: 24px; min-height: 36px; padding: 0 12px; border: 1px solid var(--m-border); border-radius: var(--m-radius-md); background: var(--m-surface); color: var(--m-muted); }
  .mango-defect-page__stats strong { margin-left: 4px; color: var(--m-text); font-weight: 600; }
  .mango-defect-page__quick-select { width: 100%; }
  .mango-defect-page__quick-select :deep(.arco-select-view) { border-color: transparent; border-radius: var(--m-radius-md); }
  .mango-defect-page__quick-select.is-status-3 :deep(.arco-select-view),
  .mango-defect-page__quick-select.is-status-4 :deep(.arco-select-view) { background: color-mix(in srgb, var(--m-success) 12%, var(--m-surface)); }
  .mango-defect-page__quick-select.is-status-2 :deep(.arco-select-view),
  .mango-defect-page__quick-select.is-severity-1 :deep(.arco-select-view),
  .mango-defect-page__quick-select.is-priority-1 :deep(.arco-select-view) { background: color-mix(in srgb, var(--m-warning) 12%, var(--m-surface)); }
  .mango-defect-page__quick-select.is-status-5 :deep(.arco-select-view),
  .mango-defect-page__quick-select.is-severity-0 :deep(.arco-select-view),
  .mango-defect-page__quick-select.is-priority-0 :deep(.arco-select-view) { background: color-mix(in srgb, var(--m-danger) 12%, var(--m-surface)); }
  .mango-defect-page__quick-select.is-status-0 :deep(.arco-select-view),
  .mango-defect-page__quick-select.is-priority-2 :deep(.arco-select-view) { background: var(--m-primary-soft); }
  .mango-defect-page__steps { display: flex; flex-direction: column; gap: 8px; }
  .mango-defect-page__attachments { display: flex; flex-direction: column; gap: 8px; }
  .mango-defect-page__readonly-meta { display: flex; flex-wrap: wrap; gap: 8px 20px; padding: 8px 12px; border-radius: var(--m-radius-md); background: var(--m-surface-soft); color: var(--m-muted); }
  .mango-defect-page__relation-list { display: flex; flex-direction: column; gap: 8px; }
  .mango-defect-page__relation-item { padding: 8px 12px; border: 1px solid var(--m-border); border-radius: var(--m-radius-md); background: var(--m-surface-soft); }
  .mango-defect-page__relation-item small { display: block; margin-top: 4px; color: var(--m-muted); }
  .mango-defect-page__step { display: grid; grid-template-columns: 28px 1fr 1fr 1fr auto; align-items: center; gap: 8px; }
  .mango-defect-page__step > span { color: var(--m-muted); text-align: center; }
  .mango-defect-page__column-settings { display: flex; width: 280px; max-height: 420px; flex-direction: column; gap: 6px; overflow: auto; }
  .mango-defect-page__column-setting { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
</style>
