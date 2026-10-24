<template>
  <BaseSidePanel :visible="visible" title="发布审核" :width="1200" :mask-closable="!publishing"
    :closable="!publishing" :esc-to-close="!publishing" @update:visible="onReviewVisibilityChange" @cancel="close">
    <div class="mango-publication-review">
      <TableHeader class="mango-publication-review__toolbar" :title="`共 ${rows.length} 条 · 已勾选 ${selectedIds.length} 条`" :show-search-actions="false">
        <template #header-extra>
          <a-button size="small" :disabled="publishing || !selectedIds.length" @click="selectRows([])">清空勾选</a-button>
        </template>
      </TableHeader>
      <div class="mango-publication-review__table">
      <a-table class="mango-native-scroll-table" row-key="id" :data="displayRows" :columns="reviewColumns" :loading="loading" size="small"
        :pagination="false" :scroll="{ x: 1280, y: '100%' }" :bordered="false"
        :row-selection="{ selectedRowKeys: selectedIds, showCheckedAll: true, onlyCurrent: false }"
        @selection-change="selectRows">
        <template #execution_configuration_title>
          <CaseExecutionConfigurationTitle prepublished />
        </template>
        <template #case="{ record }">
          <strong>#{{ record.id }} {{ record.name || (record.error ? '加载失败' : '加载中') }}</strong>
          <div class="mango-publication-review__muted" :title="`${record.product || ''} / ${record.module || ''}`">{{ record.product }} / {{ record.module }}</div>
        </template>
        <template #result="{ record }">
          <a-tag :color="enumStore.status_colors?.[record.status]" size="small">{{ enumTitle(enumStore.task_status, record.status) }}</a-tag>
        </template>
        <template #scenes="{ record }">
          <ExecutionSceneTagGrid :values="record.scenario_tags" :options="enumStore.api_case_scenario_tag" :colors="enumStore.colors" />
        </template>
        <template #execution_configuration="{ record }">
          <a-button v-if="record.sql_count > 0 || record.factory_count > 0" type="text" size="mini"
            :disabled="!canViewDetails || !Array.isArray(record.configuration_details)"
            @click="openConfiguration(record)">
            <CaseExecutionConfigurationTags :sql-count="record.sql_count" :factory-count="record.factory_count" />
          </a-button>
          <CaseExecutionConfigurationTags v-else :sql-count="record.sql_count" :factory-count="record.factory_count" />
        </template>
        <template #requirements="{ record }">
          <ul class="mango-publication-review__requirements">
            <li v-for="requirement in reviewRequirements(record.scenario_tags)" :key="requirement">
              <span v-for="(part, index) in reviewRequirementParts(requirement)" :key="index"
                :class="{ 'mango-publication-review__emphasis': part.emphasis }">{{ part.text }}</span>
            </li>
          </ul>
          <div v-if="record.published" class="mango-publication-review__success">已发布</div>
          <div v-else-if="record.error" class="mango-publication-review__danger">{{ record.error }}</div>
          <template v-else>
            <div v-for="reason in record.eligibility_reasons" :key="reason" class="mango-publication-review__danger">{{ reason }}</div>
          </template>
        </template>
        <template #actions="{ record }">
          <MangoTableActions :actions="[{ label: '查看详情', permission: `${domain}.case:detail`, disabled: !record.name, onClick: () => openCaseDetail(record.id) }]" />
        </template>
        <template #review="{ record }">
          <a-switch :model-value="record.reviewConfirmed === true" :disabled="record.disabled"
            :aria-label="`确认已审核用例 ${record.id}`" @change="setRowReview(record.id, $event)" />
        </template>
      </a-table>
      </div>
    </div>
    <template #footer-buttons>
      <div class="mango-publication-review__footer">
        <a-checkbox v-model="acknowledged" :disabled="loading || publishing || !allSelectedReviewed">我已核对勾选用例符合审核要求，确认发布</a-checkbox>
        <a-space wrap>
          <a-button size="small" :disabled="publishing" @click="close">取消</a-button>
          <a-button v-permission="permissionKey" size="small" type="primary" :loading="publishing"
            :disabled="loading || !canPublish || !acknowledged || !allSelectedReviewed" @click="publishSelected">确认发布 {{ selectedIds.length }} 条</a-button>
        </a-space>
      </div>
    </template>
  </BaseSidePanel>
  <ApiCaseConfigurationDrawer ref="configurationDrawerRef" />
  <BaseSidePanel :visible="detailVisible" title="用例详情" width="calc(92vw - 150px)" mode="page"
    @update:visible="detailVisible = $event" @cancel="detailVisible = false">
    <div class="mango-publication-review__detail-page">
      <component :is="detailComponents[domain]" v-if="detailVisible && detailCaseId && canViewDetails"
        :key="`${domain}-${detailCaseId}`" embedded :case-id="detailCaseId" @close="detailVisible = false" />
    </div>
  </BaseSidePanel>
</template>

<script setup lang="ts">
  import { computed, defineAsyncComponent, h, ref } from 'vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import TableHeader from '@/components/table/TableHeader.vue'
  import ExecutionSceneTagGrid from '@/components/display/ExecutionSceneTagGrid.vue'
  import CaseExecutionConfigurationTags from '@/components/display/CaseExecutionConfigurationTags.vue'
  import CaseExecutionConfigurationTitle from '@/components/display/CaseExecutionConfigurationTitle.vue'
  import ApiCaseConfigurationDrawer from '@/views/apitest/case/components/ApiCaseConfigurationDrawer.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import { requiresCaseReview, reviewRequirementParts, reviewRequirements } from '@/utils/case-publication-review'
  import { Message } from '@arco-design/web-vue'
  import { get } from '@/api/http'
  import { approveApiCasePrepublication } from '@/api/apitest/case-version'
  import { putUiCasePublication } from '@/api/uitest/case'
  import { putPytestCasePublication } from '@/api/pytest/case'
  import { useEnum } from '@/store/modules/get-enum'
  import usePermissionStore from '@/store/modules/permission'

  type Domain = 'api' | 'ui' | 'pytest'
  type Review = { id: number; name?: string; disabled?: boolean; error?: string; published?: boolean;
    eligibility_reasons?: string[]; [key: string]: any }
  const emit = defineEmits<{ (event: 'published', ids: number[]): void }>()
  const enumStore = useEnum()
  const permissions = usePermissionStore()
  const configurationDrawerRef = ref<InstanceType<typeof ApiCaseConfigurationDrawer> | null>(null)
  const detailVisible = ref(false)
  const detailCaseId = ref<number | null>(null)
  const canViewDetails = computed(() => permissions.hasPermission(`${domain.value}.case:detail`))
  const lazyDetail = (loader: () => Promise<any>) => defineAsyncComponent({
    loader,
    delay: 0,
    loadingComponent: { render: () => h(MangoPanelSpin, { loading: true, class: 'mango-publication-review__detail-loading' },
      () => h('span', '正在加载用例详情…')) },
    errorComponent: { render: () => h('div', { class: 'mango-empty-state' }, '用例详情加载失败，请关闭后重试。') },
  })
  const detailComponents = {
    api: lazyDetail(() => import('@/views/apitest/case/details/index.vue')),
    ui: lazyDetail(() => import('@/views/uitest/case/details/index.vue')),
    pytest: lazyDetail(() => import('@/views/pytest/case/index.vue')),
  }
  const domain = ref<Domain>('api')
  const visible = ref(false)
  const loading = ref(false)
  const publishing = ref(false)
  const acknowledged = ref(false)
  const ids = ref<number[]>([])
  const rows = ref<Review[]>([])
  const selectedIds = ref<Array<string | number>>([])
  let requestVersion = 0
  const permissionKey = computed(() => `${domain.value}.case:publish`)
  const canPublish = computed(() => permissions.hasPermission(permissionKey.value))
  const allSelectedReviewed = computed(() => selectedIds.value.length > 0 && selectedIds.value.every(
    (id) => rows.value.find((row) => row.id === Number(id))?.reviewConfirmed === true,
  ))
  const displayRows = computed(() => rows.value.map((row) => ({ ...row,
    disabled: loading.value || publishing.value || !canPublish.value || Boolean(row.error || row.published || row.eligibility_reasons?.length) })))
  const reviewColumns = [
    { title: '用例', slotName: 'case', width: 240, ellipsis: true, tooltip: true },
    { title: '负责人', dataIndex: 'owner', width: 80, ellipsis: true, tooltip: true },
    { title: '执行结果', slotName: 'result', width: 80, align: 'center' as const },
    { title: '执行场景', slotName: 'scenes', width: 160, ellipsis: true, tooltip: true },
    { title: '执行配置', titleSlotName: 'execution_configuration_title', slotName: 'execution_configuration', width: 180, align: 'left' as const },
    { title: '审核要求', slotName: 'requirements' },
    { title: '审核确认', slotName: 'review', width: 100, align: 'center' as const },
    { title: '操作', slotName: 'actions', width: 160, fixed: 'right' as const, align: 'center' as const },
  ]
  const enumTitle = (options: any[], value: unknown) => options?.find((item) => String(item.key) === String(value))?.title || String(value ?? '-')

  async function open(type: Domain, caseIds: number[]) {
    if (publishing.value) return
    domain.value = type
    detailVisible.value = false
    ids.value = [...new Set(caseIds.map(Number).filter((id) => Number.isSafeInteger(id) && id > 0))]
    visible.value = true
    await reload()
  }

  function close() {
    if (publishing.value) return
    requestVersion += 1
    visible.value = false
    detailVisible.value = false
    loading.value = false
    selectedIds.value = []
    acknowledged.value = false
  }

  function onReviewVisibilityChange(nextVisible: boolean) {
    if (!nextVisible) close()
  }

  async function reload() {
    if (publishing.value) return
    const version = ++requestVersion
    loading.value = true
    selectedIds.value = []
    acknowledged.value = false
    rows.value = ids.value.map((id) => ({ id }))
    const type = domain.value
    let cursor = 0
    const worker = async () => {
      while (cursor < ids.value.length && version === requestVersion) {
        const index = cursor++
        const id = ids.value[index]
        try {
          const res = await get({ url: type === 'api' ? '/api/case/prepublication/review' : `/${type}/case/publication/review`,
            data: () => ({ case_id: id }), silentError: true })
          if (!res.data || Number(res.data.id) !== id || !Array.isArray(res.data.eligibility_reasons)) throw new Error('Invalid review summary')
          if (version === requestVersion) rows.value[index] = {
            ...res.data, id, reviewConfirmed: !requiresCaseReview(res.data.scenario_tags),
            eligibility_reasons: [...res.data.eligibility_reasons,
              ...(res.data.publication_status === 'prepublished' ? [] : ['当前不是预发布状态，不能发布'])],
          }
        } catch {
          if (version === requestVersion) rows.value[index] = { id, error: '审核摘要加载失败，不能发布。请重新检查。' }
        }
      }
    }
    try { await Promise.all(Array.from({ length: Math.min(3, ids.value.length) }, worker)) }
    finally { if (version === requestVersion) loading.value = false }
  }

  function selectRows(keys: Array<string | number>) {
    const eligible = new Set(displayRows.value.filter((row) => !row.disabled).map((row) => row.id))
    selectedIds.value = keys.filter((key) => eligible.has(Number(key)))
    acknowledged.value = false
  }

  function setRowReview(id: number, confirmed: string | number | boolean) {
    if (loading.value || publishing.value || !canPublish.value) return
    const row = rows.value.find((item) => item.id === id)
    if (!row || row.error || row.published || row.eligibility_reasons?.length) return
    row.reviewConfirmed = confirmed === true
    acknowledged.value = false
  }

  function openCaseDetail(id: number) {
    if (!permissions.hasPermission(`${domain.value}.case:detail`)) return
    detailCaseId.value = id
    detailVisible.value = true
    acknowledged.value = false
  }

  function openConfiguration(row: Review) {
    if (!permissions.hasPermission(`${domain.value}.case:detail`) || !Array.isArray(row.configuration_details)) return
    configurationDrawerRef.value?.openSnapshot({
      id: row.id, name: row.name || '', sql_count: row.sql_count, data_factory_count: row.factory_count,
      publication_status: row.publication_status, revision_id: row.revision_id,
      has_sql: row.sql_count > 0, has_data_factory: row.factory_count > 0, items: row.configuration_details,
    }, `${domain.value}.case:detail`)
  }

  async function publishSelected() {
    if (loading.value || publishing.value || !acknowledged.value || !canPublish.value) return
    const eligible = new Set(displayRows.value.filter((row) => !row.disabled).map((row) => row.id))
    const selected = selectedIds.value.map(Number).filter((id) => eligible.has(id))
    if (!selected.length || selected.some((id) => rows.value.find((row) => row.id === id)?.reviewConfirmed !== true)) return
    const type = domain.value
    publishing.value = true
    const succeeded: number[] = []
    try {
      for (const id of selected) {
        if (!permissions.hasPermission(`${type}.case:publish`)) break
        const row = rows.value.find((item) => item.id === id)!
        try {
          if (type === 'api') await approveApiCasePrepublication(id)
          else if (type === 'ui') await putUiCasePublication(id, 'published')
          else await putPytestCasePublication(id, 'published')
          row.published = true
          succeeded.push(id)
        } catch { row.error = '发布失败，状态或配置可能已变化。请重新检查。' }
      }
      selectedIds.value = []
      acknowledged.value = false
      if (succeeded.length) { Message.success(`已发布 ${succeeded.length} 条`); emit('published', succeeded) }
      if (rows.value.every((row) => row.published)) visible.value = false
    } finally { publishing.value = false }
  }
  defineExpose({ open })
</script>

<style scoped>
  .mango-publication-review { display: flex; flex-direction: column; height: 100%; min-height: 0; gap: var(--m-page-gap); min-width: 0; overflow: hidden; }
  .mango-publication-review__toolbar { flex: none; }
  .mango-publication-review__table { flex: 1; min-height: 0; min-width: 0; overflow: hidden; }
  .mango-publication-review__footer { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; }
  .mango-publication-review__muted { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .mango-publication-review :deep(.arco-table-cell) { overflow-wrap: anywhere; }
  .mango-publication-review__muted { color: var(--m-text-2); }
  .mango-publication-review__danger { color: var(--m-danger); }
  .mango-publication-review__success { color: var(--m-success); }
  .mango-publication-review__requirements { margin: 0; padding-left: 18px; white-space: normal; line-height: 1.6; }
  .mango-publication-review__emphasis { color: var(--m-danger); font-weight: 600; }
  .mango-publication-review__detail-page { height: 100%; min-height: 0; }
  .mango-publication-review__detail-page :deep(.mango-detail-workbench-page) { height: 100%; min-height: 0; }
  .mango-publication-review__detail-loading { width: 100%; min-height: 160px; }
</style>
