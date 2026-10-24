<template>
  <TableBody plain class="mango-detail-workbench-page">
    <template #header><TableHeader title="评测中心 / 测试用例" /></template>
    <template #default>
      <ProjectProductNavigationWorkbench contained-body show-modules :model-value="filters.project_product" :module-value="filters.module" :reset-key="resetKey" @filter-change="sidebarChanged" @search="search" @reset-search="reset">
        <template #search><a-form :model="filters" layout="inline" @keyup.enter="search">
          <a-form-item label="用例名称"><a-input v-model="filters.name" allow-clear placeholder="搜索用例" /></a-form-item>
          <a-form-item label="状态"><a-select v-model="filters.status" :options="caseStatusOptions" multiple :max-tag-count="1" allow-clear /></a-form-item>
          <a-form-item label="目标类型"><a-select v-model="filters.target_type" :options="targetTypeOptions" multiple :max-tag-count="1" allow-clear /></a-form-item>
        </a-form></template>
        <template #toolbar><a-button v-permission="'evaluation.case:create'" type="primary" size="small" @click="editor?.open(undefined, filters.project_product, filters.module)">新建用例</a-button></template>
        <a-table class="mango-native-scroll-table" :columns="caseColumns" :data="rows" :loading="loading" :pagination="false" :scroll="{ x: CASE_SCROLL_X, y: '100%' }" row-key="id" size="small">
          <template #columns><a-table-column v-for="column in caseColumns" :key="column.key" v-bind="column"><template #cell="{ record }">
            <span v-if="column.key === 'index'">{{ record.id }}</span>
            <span v-else-if="column.key === 'dataset_version_no'">{{ formatVersion(record.dataset_version_no) }}</span>
            <a-link v-else-if="column.key === 'name' && permissions.hasPermission('evaluation.case:detail')" @click="details(record)">{{ record.name }}</a-link>
            <span v-else-if="column.key === 'description'">{{ record.description || '-' }}</span>
            <span v-else-if="column.key === 'project_product'">{{ formatProjectProductPath(record.project_product) }}</span>
            <span v-else-if="column.key === 'module'">{{ formatModulePath(record.module) }}</span>
            <a-tag v-else-if="column.key === 'latest'" size="small" :color="statusColor(record.latest_result?.status)">{{ record.latest_result?.status ? enumTitle('evaluation_execution_status', record.latest_result.status) : '尚未执行' }}</a-tag>
            <a-tag v-else-if="column.key === 'target_type'" size="small" :color="getEnumTagColor(enumStore.evaluation_target_type, record.target_type, enumStore.colors)">{{ record.target_type ? enumTitle('evaluation_target_type', record.target_type) : '待配置' }}</a-tag>
            <span v-else-if="column.key === 'score'">{{ record.latest_result?.average_score ?? '-' }}</span>
            <span v-else-if="column.key === 'valid_rate'">{{ record.latest_result?.valid_rate == null ? '-' : `${(record.latest_result.valid_rate * 100).toFixed(1)}%` }}</span>
            <span v-else-if="column.key === 'finished_at'">{{ record.latest_result?.finished_at || '-' }}</span>
            <template v-else-if="column.key === 'status'">
              <a-switch v-if="permissions.hasPermission('evaluation.case:status')" size="small" :model-value="record.status === 'enabled'" :before-change="() => toggleStatus(record)" />
              <a-tag v-else size="small" :color="statusColor(record.status)">{{ enumTitle('evaluation_case_status', record.status) }}</a-tag>
            </template>
            <MangoTableActions v-else-if="column.key === 'actions'" :actions="[
              { label: '执行', permission: 'evaluation.case:execute', disabled: record.status !== 'enabled', loading: executing.has(record.id), onClick: () => execute(record) },
              { label: '详情', permission: 'evaluation.case:detail', onClick: () => details(record) },
              { label: '历史结果', permission: 'evaluation.case:detail', onClick: () => details(record, true) },
              { label: '编辑信息', permission: 'evaluation.case:edit', onClick: () => editor?.open(record.id) },
              { label: '复制', permission: 'evaluation.case:copy', loading: copying === record.id, onClick: () => copy(record) },
              { label: '删除', permission: 'evaluation.case:delete', danger: true, onClick: () => remove(record) },
            ]" />
            <span v-else>{{ record[column.dataIndex as string] ?? '-' }}</span>
          </template></a-table-column></template>
        </a-table>
        <template #footer><TableFooter :pagination="pagination" /></template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>
  <CaseEditor ref="editor" @saved="load" />
</template>
<script setup lang="ts">
  import { computed, onMounted, reactive, ref, watch } from 'vue'
  import { useRouter } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import { formatModulePath, formatProjectProductPath, getEnumTagColor } from '@/utils/business-format'
  import { useEnum } from '@/store/modules/get-enum'
  import usePermissionStore from '@/store/modules/permission'
  import useUserStore from '@/store/modules/user'
  import { getEvaluationCases, updateEvaluationCase, deleteEvaluationCase, copyEvaluationCase, executeEvaluationCase } from '@/api/evaluation'
  import CaseEditor from '../components/CaseEditor.vue'
  import { caseColumns, CASE_SCROLL_X } from './config'
  import { useEvaluationEnums } from '../components/useEvaluationEnums'
  import { formatVersion } from '../components/presentation'
  const { title: enumTitle, color: statusColor, options: enumOptions } = useEvaluationEnums()
  const enumStore = useEnum()
  const caseStatusOptions = computed(() => enumOptions('evaluation_case_status')), targetTypeOptions = computed(() => enumOptions('evaluation_target_type'))
  const permissions = usePermissionStore(), user = useUserStore(), router = useRouter()
  const editor = ref<InstanceType<typeof CaseEditor>>()
  const rows = ref<any[]>([]), loading = ref(false), resetKey = ref(0), copying = ref<number>()
  const executing = reactive(new Set<number>()), keys = new Map<string, string>()
  const filters = reactive<any>({ name: '', status: [], target_type: [], project_product: null, module: null })
  const moduleIds = ref<Array<string | number>>([])
  const pagination = reactive({ page: 1, pageSize: 10, pageCount: 0, pageSizes: [10, 20, 50], showSizePicker: true, onChange: () => load() })
  let requestId = 0
  async function load() {
    const request = ++requestId
    loading.value = true
    try {
      const response: any = await getEvaluationCases({ page: pagination.page, pageSize: pagination.pageSize, name: filters.name || undefined,
        status__in: filters.status.length ? filters.status.join(',') : undefined, target_type__in: filters.target_type.length ? filters.target_type.join(',') : undefined,
        project_product: filters.project_product || undefined, module__in: moduleIds.value.length ? moduleIds.value.join(',') : undefined,
        module: moduleIds.value.length ? undefined : filters.module || undefined, test_env: user.selected_environment || undefined })
      if (request !== requestId) return
      rows.value = (response.data?.items || []).map((item: any) => ({ ...item, project_product: item.project_product_data, module: item.module_data })); pagination.pageCount = response.data?.count || 0
    } finally { if (request === requestId) loading.value = false }
  }
  function search() { pagination.page = 1; load() }
  function sidebarChanged(filter: any) { filters.project_product = filter.projectProduct; filters.module = filter.module; moduleIds.value = filter.moduleIds || []; search() }
  function reset() { Object.assign(filters, { name: '', status: [], target_type: [], project_product: null, module: null }); moduleIds.value = []; resetKey.value += 1; search() }
  function details(record: any, history = false, execution?: number) { router.push({ path: '/evaluation/case/details', query: { id: record.id, ...(history ? { tab: 'history' } : {}), ...(execution ? { execution } : {}) } }) }
  async function toggleStatus(record: any) {
    if (!permissions.hasPermission('evaluation.case:status')) return false
    await updateEvaluationCase({ id: record.id, status: record.status === 'enabled' ? 'draft' : 'enabled' }); await load(); return true
  }
  async function execute(record: any) {
    if (!user.selected_environment) { Message.warning('请先选择顶部测试环境'); return }
    if (executing.has(record.id)) return
    const scope = `${record.id}:${user.selected_environment}`
    if (!keys.has(scope)) keys.set(scope, crypto.randomUUID())
    executing.add(record.id)
    try {
      const response: any = await executeEvaluationCase(record.id, { test_env: Number(user.selected_environment) }, keys.get(scope)!)
      keys.delete(scope); Message.success('Case 已提交执行')
      if (permissions.hasPermission('evaluation.case:detail')) details(record, false, response.data.id)
      else await load()
    } finally { executing.delete(record.id) }
  }
  async function copy(record: any) { copying.value = record.id; try { await copyEvaluationCase(record.id); Message.success('已复制为草稿'); await load() } finally { copying.value = undefined } }
  function remove(record: any) { Modal.warning({ title: '删除 Case', content: `确定删除“${record.name}”？存在执行历史的 Case 受删除保护。`, hideCancel: false, onOk: async () => { await deleteEvaluationCase(record.id); await load() } }) }
  watch(() => user.selected_environment, search)
  onMounted(load)
</script>
