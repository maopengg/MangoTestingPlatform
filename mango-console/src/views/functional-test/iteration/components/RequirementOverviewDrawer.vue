<template>
  <a-drawer
    :visible="visible"
    :width="860"
    unmount-on-close
    @update:visible="emit('update:visible', $event)"
  >
    <template #title>
      {{ suite.requirement?.requirement_key || '需求' }} · {{ suite.requirement_name || suite.requirement?.name || '-' }}
    </template>
    <template #footer>
      <a-space>
        <a-button v-permission="'functional.iteration:edit'" @click="emit('edit-schedule', suite)">编辑排期</a-button>
        <a-button @click="openWorkspace">用例生成工作台</a-button>
        <a-button type="primary" @click="openDetail">查看完整需求</a-button>
      </a-space>
    </template>
    <a-spin class="mango-requirement-overview__spin" :loading="loading">
      <a-tabs v-model:active-key="activeTab">
        <a-tab-pane key="overview" title="概览">
          <a-descriptions :column="2" bordered size="small">
            <a-descriptions-item label="版本">V{{ suite.version_no || '-' }}</a-descriptions-item>
            <a-descriptions-item label="状态">{{ enumTitle(statusOptions, suite.status) }}</a-descriptions-item>
            <a-descriptions-item label="开发负责人">{{ suite.development_owner?.name || '-' }}</a-descriptions-item>
            <a-descriptions-item label="测试负责人">{{ suite.owner?.name || '-' }}</a-descriptions-item>
            <a-descriptions-item label="计划开始">{{ suite.planned_start_date || '-' }}</a-descriptions-item>
            <a-descriptions-item label="计划提测">{{ suite.planned_submit_date || '-' }}</a-descriptions-item>
            <a-descriptions-item label="用例数">{{ suite.case_count || 0 }}</a-descriptions-item>
            <a-descriptions-item label="自动化覆盖">{{ suite.automation_coverage_percent || 0 }}%</a-descriptions-item>
            <a-descriptions-item label="项目产品">{{ suite.project_product?.project?.name || '' }} / {{ suite.project_product?.name || '-' }}</a-descriptions-item>
            <a-descriptions-item label="模块">{{ suite.module?.full_path || suite.module?.name || '-' }}</a-descriptions-item>
          </a-descriptions>
        </a-tab-pane>
        <a-tab-pane key="cases" :title="`来源用例（${cases.length}）`">
          <div class="mango-requirement-overview__toolbar">
            <span>解绑只取消需求来源关系，不会删除用例资产、历史版本、执行快照或缺陷关系。</span>
            <a-button size="small" status="danger" :disabled="!selectedCaseKeys.length" :loading="unlinking" @click="unlinkCases">取消关联</a-button>
          </div>
          <a-table
            :data="cases"
            :columns="caseColumns"
            :pagination="false"
            :scroll="{ x: 720, y: 440 }"
            :row-selection="{ type: 'checkbox', showCheckedAll: true }"
            row-key="id"
            @selection-change="selectedCaseKeys = $event"
          >
            <template #case_priority="{ record }">{{ enumTitle(enumStore.case_level, record.priority) }}</template>
          </a-table>
        </a-tab-pane>
        <a-tab-pane key="plans" :title="`测试计划（${plans.length}）`">
          <div class="mango-requirement-overview__toolbar">
            <span>每个计划仅执行一次，执行结果保存在计划用例快照中。</span>
            <a-button v-permission="'functional.iteration:create'" size="small" type="primary" @click="createPlan">新建测试计划</a-button>
          </div>
          <a-table :data="plans" :columns="planColumns" :pagination="false" :scroll="{ x: 720, y: 440 }">
            <template #plan_name="{ record }"><a-link @click="openPlan(record)">{{ record.name }}</a-link></template>
            <template #plan_status="{ record }"><a-tag size="small">{{ enumTitle(enumStore.functional_test_plan_status, record.status) }}</a-tag></template>
            <template #plan_progress="{ record }">{{ formatRate(record.execution_stats?.progress) }}</template>
          </a-table>
        </a-tab-pane>
        <a-tab-pane key="defects" :title="`缺陷（${defects.length}）`">
          <a-table :data="defects" :columns="defectColumns" :pagination="false" :scroll="{ x: 720, y: 440 }">
            <template #defect_status="{ record }"><a-tag size="small">{{ enumTitle(enumStore.functional_test_defect_status, record.status) }}</a-tag></template>
          </a-table>
        </a-tab-pane>
        <a-tab-pane key="resources" :title="`资料（${resources.length}）`">
          <a-list :data="resources" :bordered="false">
            <template #item="{ item }">
              <a-list-item>{{ item.title || item.context_key }}<template #extra>{{ item.update_time }}</template></a-list-item>
            </template>
          </a-list>
        </a-tab-pane>
      </a-tabs>
    </a-spin>
  </a-drawer>
</template>

<script lang="ts" setup>
  import { ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { useRouter } from 'vue-router'
  import { useEnum } from '@/store/modules/get-enum'
  import {
    getFunctionalContextResource,
    getFunctionalRequirementCases,
    getManualSuite,
    getRelatedFunctionalDefects,
    getRelatedFunctionalPlans,
    unbindFunctionalRequirementCases,
  } from '@/api/functional-test'

  const props = defineProps<{ visible: boolean; suiteId?: number; statusOptions?: any[] }>()
  const emit = defineEmits<{
    (event: 'update:visible', value: boolean): void
    (event: 'edit-schedule', suite: any): void
    (event: 'changed'): void
  }>()
  const router = useRouter()
  const enumStore = useEnum()
  const loading = ref(false)
  const unlinking = ref(false)
  const activeTab = ref('overview')
  const suite = ref<any>({})
  const cases = ref<any[]>([])
  const plans = ref<any[]>([])
  const defects = ref<any[]>([])
  const resources = ref<any[]>([])
  const selectedCaseKeys = ref<number[]>([])
  const caseColumns = [
    { title: '用例编号', dataIndex: 'case_no', width: 130 },
    { title: '用例标题', dataIndex: 'title', ellipsis: true, tooltip: true },
    { title: '优先级', dataIndex: 'priority', slotName: 'case_priority', width: 90 },
    { title: '负责人', dataIndex: 'owner.name', width: 120 },
  ]
  const planColumns = [
    { title: '计划名称', dataIndex: 'name', slotName: 'plan_name' },
    { title: '状态', dataIndex: 'status', slotName: 'plan_status', width: 100 },
    { title: '执行进度', dataIndex: 'execution_stats', slotName: 'plan_progress', width: 110 },
  ]
  const defectColumns = [
    { title: '缺陷编号', dataIndex: 'defect_no', width: 150 },
    { title: '缺陷标题', dataIndex: 'title', ellipsis: true, tooltip: true },
    { title: '状态', dataIndex: 'status', slotName: 'defect_status', width: 100 },
    { title: '负责人', dataIndex: 'assignee.name', width: 110 },
  ]
  const enumTitle = (options: any[] = [], value: any) => options.find((item) => item.key === value)?.title || '-'
  const formatRate = (value: any) => `${Number(value || 0).toFixed(0)}%`

  async function load() {
    if (!props.visible || !props.suiteId) return
    loading.value = true
    selectedCaseKeys.value = []
    try {
      const [suiteRes, caseRes, planRes, defectRes, resourceRes] = await Promise.all([
        getManualSuite({ id: props.suiteId }),
        getFunctionalRequirementCases(Number(props.suiteId)),
        getRelatedFunctionalPlans({ requirement_version_id: props.suiteId }),
        getRelatedFunctionalDefects({ requirement_version_id: props.suiteId }),
        getFunctionalContextResource({ suite: props.suiteId }),
      ])
      suite.value = (suiteRes.data || [])[0] || {}
      cases.value = caseRes.data || []
      plans.value = planRes.data || []
      defects.value = defectRes.data || []
      resources.value = resourceRes.data || []
    } finally { loading.value = false }
  }
  function unlinkCases() {
    Modal.warning({
      title: '确认取消关联',
      content: `将 ${selectedCaseKeys.value.length} 条用例从当前需求中取消关联，用例资产本身仍会保留。`,
      hideCancel: false,
      onOk: async () => {
        unlinking.value = true
        try {
          await unbindFunctionalRequirementCases(Number(props.suiteId), selectedCaseKeys.value)
          Message.success('已取消用例关联')
          emit('changed')
          await load()
        } finally { unlinking.value = false }
      },
    })
  }
  function openWorkspace() { router.push({ path: '/functional-test/suite/details', query: { id: props.suiteId } }) }
  function openDetail() { router.push({ path: '/functional-test/requirement/details', query: { id: props.suiteId } }) }
  function createPlan() { router.push({ path: '/functional-test/plan/index', query: { requirement_version: props.suiteId } }) }
  function openPlan(row: any) { router.push({ path: '/functional-test/plan/details', query: { id: row.id } }) }
  watch(() => [props.visible, props.suiteId], load, { immediate: true })
</script>

<style lang="less" scoped>
  .mango-requirement-overview__spin { display: block; min-height: 360px; }
  .mango-requirement-overview__toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 8px; color: var(--m-text-3); }
</style>
