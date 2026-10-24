<template>
  <div class="case-version-sidebar">
    <div class="version-panel-head">
      <div>
        <strong>版本</strong>
        <small>选择后查看对应配置</small>
      </div>
      <a-space size="mini">
        <a-button size="mini" type="outline" @click="openCompareDrawer" data-testid="qa-views-apitest-case-details-components-apicaseversionpanel-button-版本比对">版本比对</a-button>
      </a-space>
    </div>

    <mango-panel-spin :loading="loading || selectingVersion" class="version-panel-list">
      <div class="version-panel-scroll">
        <button
          type="button"
          class="version-card current-version-card"
          :class="{ active: selectedKey === 'current' }"
          @click="selectCurrent"
        >
          <div class="version-card-head">
            <strong>当前配置</strong>
            <a-tag size="small" color="orange">编辑态</a-tag>
          </div>
          <small>当前工作区，可直接编辑</small>
          <small>确认当前配置后可生成修订，断言为可选配置</small>
        </button>

        <a-popover
          v-for="item in revisions"
          :key="item.id"
          position="right"
          :popup-visible="activePopoverKey === getRevisionPopoverKey(item)"
          content-class="version-detail-popover"
        >
          <button
            type="button"
            class="version-card"
            :class="{ active: selectedKey === `revision-${item.id}` }"
            @click="selectRevision(item)"
            @mouseenter="startVersionPopoverTimer(getRevisionPopoverKey(item))"
            @mousemove="restartVersionPopoverTimer(getRevisionPopoverKey(item))"
            @mouseleave="hideVersionPopover(getRevisionPopoverKey(item))"
          >
            <div class="version-card-head">
              <strong>{{ getApiCaseRevisionLabel(item) }}</strong>
              <a-tag :color="revisionStatus(item).color" size="small">
                {{ revisionStatus(item).text }}
              </a-tag>
            </div>
            <small>{{ getRevisionUserMeta(item) }}</small>
            <small>{{ getRevisionUpdateTimeMeta(item) }}</small>
          </button>
          <template #content>
            <div
              class="version-popover-content"
              @mouseenter="keepVersionPopover(getRevisionPopoverKey(item))"
              @mouseleave="hideVersionPopover(getRevisionPopoverKey(item))"
            >
              <div class="version-popover-title">{{ getApiCaseRevisionLabel(item) }}</div>
              <dl class="version-popover-list">
                <div
                  v-for="popoverItem in getRevisionPopoverItems(item)"
                  :key="popoverItem.label"
                  class="version-popover-row"
                >
                  <dt>{{ popoverItem.label }}</dt>
                  <dd>{{ popoverItem.value }}</dd>
                </div>
              </dl>
            </div>
          </template>
        </a-popover>
      </div>
    </mango-panel-spin>

    <div class="case-version-sidebar-actions">
      <a-button v-permission="'api.case:edit'"
        v-if="selectedKey === 'current' && !prepublishedRevision"
        long
        size="small"
        :loading="creating"
        @click="createRevisionFromCurrent" data-testid="qa-views-apitest-case-details-components-apicaseversionpanel-button-生成修订"
      >
        生成修订
      </a-button>
      <a-button v-permission="'api.case:publish'"
        v-if="
          selectedRevision &&
          selectedRevision.is_active_candidate &&
          !selectedRevision.release?.is_current &&
          !selectedRevision.is_prepublished &&
          !prepublishedRevision
        "
        long
        size="small"
        type="primary"
        :loading="publishing"
        :disabled="!selectedRevision.has_product_owner"
        @click="submitPrepublication"
      >
        提交预发布
      </a-button>
      <a-button v-permission="'api.case:publish'"
        v-if="selectedRevision?.is_prepublished && selectedRevision.is_product_owner"
        long
        size="small"
        type="primary"
        :loading="publishing"
        @click="approvePrepublication"
      >
        通过并发布 {{ nextReleaseLabel }}
      </a-button>
      <a-button v-permission="'api.case:publish'"
        v-if="selectedRevision?.is_prepublished && selectedRevision.is_product_owner"
        long
        size="small"
        :loading="revertingPrepublication"
        @click="revertPrepublication"
      >
        退回未发布
      </a-button>
      <span
        v-if="selectedRevision?.is_prepublished && !selectedRevision.is_product_owner"
        class="prepublication-waiting"
        >等待产品负责人处理</span
      >
      <a-button
        v-if="selectedRevision"
        long
        size="small"
        :loading="checkingOut"
        @click="checkoutSelectedRevision" data-testid="qa-views-apitest-case-details-components-apicaseversionpanel-button-迁出到编辑态"
      >
        迁出到编辑态
      </a-button>
      <a-button v-permission="'api.case:publish'"
        v-if="selectedRevision?.release?.is_current && selectedRevision.is_product_owner"
        long
        size="small"
        status="danger"
        :loading="unpublishing"
        @click="unpublishSelected"
      >
        取消发布
      </a-button>
      <a-button v-permission="'api.case:delete'"
        v-if="selectedRevision && !selectedRevision.release && !selectedRevision.is_prepublished"
        long
        size="small"
        status="danger"
        :loading="deleting"
        @click="deleteSelectedRevision" data-testid="qa-views-apitest-case-details-components-apicaseversionpanel-button-删除修订"
      >
        删除修订
      </a-button>
    </div>
  </div>
  <ApiVersionCompareDrawer
    v-model:visible="compareDrawerVisible"
    left-title="当前编辑态"
    :left-payload="currentPayload || {}"
    :targets="apiCaseCompareTargets"
    :load-target-payload="loadApiCaseCompareTarget"
  />
  <ExecutionResultHistoryDrawer
    v-model:visible="resultHistoryVisible"
    :title="resultHistoryTitle"
    :case-id="caseId"
    :query="resultHistoryQuery"
    @show-trace="(query) => emit('show-trace', query)"
  />
  <CasePublicationReviewModal ref="publicationReviewRef" @published="onReviewPublished" />
</template>

<script lang="ts" setup>
  import CasePublicationReviewModal from '@/components/business/CasePublicationReviewModal.vue'
  import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import ApiVersionCompareDrawer from '@/components/business/ApiVersionCompareDrawer.vue'
  import ExecutionResultHistoryDrawer from '@/components/business/ExecutionResultHistoryDrawer.vue'
  import {
    checkoutApiCaseRevision,
    createApiCaseRevision,
    deleteApiCaseRevision,
    getApiCaseRevisionCheckoutImpact,
    getApiCaseRevisionDetail,
    getApiCaseRevisionList,
    revertApiCasePrepublication,
    submitApiCasePrepublication,
    unpublishApiCaseRelease,
  } from '@/api/apitest/case-version'
  import type {
    ApiCaseRevisionCheckoutImpact,
    ApiCaseRevisionDetail,
    ApiCaseRevisionListItem,
  } from '@/types/api-test/case-version'
  import type { ApiVersionCompareTarget } from '@/types/api-test/version-compare'
  import {
    getApiCaseRevisionLabel,
    toApiCaseCurrentExecutionVersion,
    toApiCaseExecutionVersion,
    type ApiCaseExecutionVersion,
  } from '@/utils/api-case-revision'
  import { parseApiCaseRevisionPayload } from '@/types/api-test/case-revision-payload'

  const props = defineProps<{
    caseId: number | string
    currentPayload?: Record<string, any> | null
  }>()
  const emit = defineEmits<{
    (event: 'select', version: ApiCaseExecutionVersion): void
    (event: 'detail', detail: ApiCaseRevisionDetail): void
    (event: 'current'): void
    (event: 'execute', version: ApiCaseExecutionVersion): void
    (event: 'published'): void
    (event: 'show-trace', query: { result_id: number | string }): void
  }>()

  const revisions = ref<ApiCaseRevisionListItem[]>([])
  const selectedKey = ref('current')
  const loading = ref(false)
  const creating = ref(false)
  const publishing = ref(false)
  const publicationReviewRef = ref<InstanceType<typeof CasePublicationReviewModal> | null>(null)
  async function onReviewPublished() {
    await refresh()
    emit('published')
  }
  const revertingPrepublication = ref(false)
  const unpublishing = ref(false)
  const checkingOut = ref(false)
  const deleting = ref(false)
  const selectingVersion = ref(false)
  const compareDrawerVisible = ref(false)
  const resultHistoryVisible = ref(false)
  const activePopoverKey = ref('')
  let selectionToken = 0
  let popoverTimer: ReturnType<typeof setTimeout> | null = null
  let popoverCloseTimer: ReturnType<typeof setTimeout> | null = null

  const selectedRevision = computed(() => {
    if (!selectedKey.value.startsWith('revision-')) return null
    const revisionId = Number(selectedKey.value.replace('revision-', ''))
    return revisions.value.find((item) => item.id === revisionId) || null
  })
  const prepublishedRevision = computed(
    () => revisions.value.find((item) => item.is_prepublished) || null
  )
  const nextReleaseLabel = computed(() => {
    const latestVersionNo = revisions.value.reduce(
      (maximum, item) => Math.max(maximum, item.release?.version_no || 0),
      0
    )
    return `V${latestVersionNo + 1}`
  })
  const apiCaseCompareTargets = computed<ApiVersionCompareTarget[]>(() =>
    revisions.value.map((revision) => ({
      key: `revision-${revision.id}`,
      label: getApiCaseRevisionLabel(revision),
    }))
  )
  const resultHistoryTitle = computed(() => `用例执行历史：${selectedRevision.value ? getApiCaseRevisionLabel(selectedRevision.value) : '当前编辑态'}`)
  const resultHistoryQuery = computed(() => ({
    target_type: 'api_case',
    target_id: props.caseId,
    ...(selectedRevision.value
      ? { revision_id: selectedRevision.value.id }
      : { revision_id_isnull: 1 }),
  }))

  function unwrap<T>(response: any): T {
    return (response?.data ?? response) as T
  }

  function revisionStatus(item: ApiCaseRevisionListItem) {
    if (item.is_prepublished) return { text: '预发布', color: 'orange' }
    if (item.release?.is_current) return { text: '当前发布', color: 'green' }
    if (item.release?.status === 'deprecated') return { text: '已取消发布', color: 'gray' }
    if (item.release) return { text: '历史版本', color: 'gray' }
    if (item.is_active_candidate) return { text: '未发布候选', color: 'orange' }
    return { text: '已替代修订', color: 'gray' }
  }

  async function refresh() {
    if (!props.caseId) return
    loading.value = true
    try {
      revisions.value =
        unwrap<ApiCaseRevisionListItem[]>(await getApiCaseRevisionList(props.caseId)) || []
      if (!selectedKey.value || selectedKey.value === 'current') selectCurrent()
    } finally {
      loading.value = false
    }
  }

  function selectCurrent() {
    selectionToken += 1
    selectedKey.value = 'current'
    selectingVersion.value = false
    emit('select', toApiCaseCurrentExecutionVersion())
    emit('current')
  }

  async function selectRevision(item: ApiCaseRevisionListItem) {
    const token = selectionToken + 1
    selectionToken = token
    selectedKey.value = `revision-${item.id}`
    emit('select', toApiCaseExecutionVersion(item))
    selectingVersion.value = true
    try {
      const detail = unwrap<ApiCaseRevisionDetail>(await getApiCaseRevisionDetail(item.id))
      if (token !== selectionToken || selectedKey.value !== `revision-${item.id}`) return
      emit('detail', detail)
    } finally {
      if (token === selectionToken) {
        selectingVersion.value = false
      }
    }
  }

  async function createRevisionFromCurrent() {
    if (creating.value) return
    creating.value = true
    try {
      const revision = unwrap<ApiCaseRevisionListItem>(
        await createApiCaseRevision({
          case_id: Number(props.caseId),
          summary: '从当前配置生成修订',
        })
      )
      Message.success('已生成修订')
      await refresh()
      const target = revisions.value.find((item) => item.id === revision.id)
      if (target) await selectRevision(target)
    } finally {
      creating.value = false
    }
  }

  function submitPrepublication() {
    if (!selectedRevision.value || publishing.value) return
    const revision = selectedRevision.value
    Modal.confirm({
      title: '提交预发布',
      content: `确认将修订 r${revision.revision_no} 提交审核吗？提交后旧正式版本转为历史版本，用例暂停参与定时执行。`,
      okText: '提交预发布',
      async onBeforeOk() {
        publishing.value = true
        try {
          await submitApiCasePrepublication(Number(props.caseId), revision.id)
          Message.success('已提交预发布')
          await refresh()
          emit('published')
          return true
        } finally {
          publishing.value = false
        }
      },
    })
  }

  function approvePrepublication() {
    const revision = selectedRevision.value
    if (!revision?.is_prepublished || !revision.is_product_owner || publishing.value) return
    void publicationReviewRef.value?.open('api', [Number(props.caseId)])
  }

  function revertPrepublication() {
    const revision = selectedRevision.value
    if (!revision?.is_prepublished || !revision.is_product_owner || revertingPrepublication.value)
      return
    Modal.confirm({
      title: '退回未发布',
      content: `确认将修订 r${revision.revision_no} 退回为未发布修订吗？`,
      okText: '确认退回',
      async onBeforeOk() {
        revertingPrepublication.value = true
        try {
          await revertApiCasePrepublication(Number(props.caseId))
          Message.success('已退回未发布')
          await refresh()
          emit('published')
          return true
        } finally {
          revertingPrepublication.value = false
        }
      },
    })
  }

  function unpublishSelected() {
    const revision = selectedRevision.value
    const release = revision?.release
    if (!revision || !release?.is_current || unpublishing.value) return
    Modal.confirm({
      title: '取消发布用例版本',
      content: `确认取消当前发布版本 ${release.version_label} 吗？取消后，定时任务将不再按已发布版本选中该 Case。`,
      okText: '确认取消',
      okButtonProps: { status: 'danger' },
      async onBeforeOk() {
        unpublishing.value = true
        try {
          await unpublishApiCaseRelease(Number(props.caseId), release.id)
          Message.success('已取消发布')
          await refresh()
          emit('published')
          return true
        } catch {
          return false
        } finally {
          unpublishing.value = false
        }
      },
    })
  }

  async function checkoutSelectedRevision() {
    if (!selectedRevision.value || checkingOut.value) return
    const revision = selectedRevision.value
    checkingOut.value = true
    let impact: ApiCaseRevisionCheckoutImpact
    try {
      impact = unwrap<ApiCaseRevisionCheckoutImpact>(
        await getApiCaseRevisionCheckoutImpact(Number(props.caseId), revision.id)
      )
    } finally {
      checkingOut.value = false
    }
    const blocked = impact.items.filter((item) => item.status === 'blocked')
    if (blocked.length) {
      Message.error(
        `无法迁出：${blocked
          .map((item) => item.api_info_name || `步骤 ${item.step_index}`)
          .join('、')} 缺少可恢复的完整接口快照`
      )
      return
    }
    const restorable = impact.items.filter((item) => item.status === 'restorable')
    Modal.confirm({
      title: '迁出到编辑态',
      content: restorable.length
        ? `发现 ${restorable.length} 个原接口或修订已删除。继续后将从历史快照创建新接口和新修订（使用新 ID），再迁出到编辑态；原历史版本保持不变。`
        : '迁出后将覆盖当前配置，原版本会永久保留，是否继续？',
      okText: restorable.length ? '恢复依赖并迁出' : '确认迁出',
      async onBeforeOk() {
        checkingOut.value = true
        try {
          await checkoutApiCaseRevision(Number(props.caseId), revision.id, restorable.length > 0)
          Message.success('已迁出到编辑态')
          selectedKey.value = 'current'
          await refresh()
          emit('published')
          return true
        } finally {
          checkingOut.value = false
        }
      },
    })
  }

  function deleteSelectedRevision() {
    if (!selectedRevision.value || selectedRevision.value.release || deleting.value) return
    const revision = selectedRevision.value
    Modal.confirm({
      title: '删除未发布修订',
      content: `确认删除修订 r${revision.revision_no} 吗？删除后不可恢复。`,
      okText: '确认删除',
      okButtonProps: { status: 'danger' },
      async onBeforeOk() {
        deleting.value = true
        try {
          await deleteApiCaseRevision(props.caseId, revision.id)
          Message.success('修订已删除')
          selectCurrent()
          await refresh()
          return true
        } catch {
          return false
        } finally {
          deleting.value = false
        }
      },
    })
  }

  function openCompareDrawer() {
    compareDrawerVisible.value = true
  }

  function openResultHistoryDrawer() {
    resultHistoryVisible.value = true
  }

  async function loadApiCaseCompareTarget(target: ApiVersionCompareTarget) {
    if (target.payload) return target.payload
    const revisionId = Number(target.key.replace('revision-', ''))
    const detail = unwrap<ApiCaseRevisionDetail>(await getApiCaseRevisionDetail(revisionId))
    return normalizeApiCaseComparePayload(detail.payload)
  }

  function normalizeApiCaseComparePayload(payload: unknown) {
    const revisionPayload = parseApiCaseRevisionPayload(payload)
    return {
      api_case: pickCaseCompareFields(revisionPayload.api_case, [
        'id',
        'name',
        'front_custom',
        'front_sql',
        'front_headers',
        'front_public',
        'front_auth_config',
        'posterior_sql',
        'parametrize',
      ]),
      api_case_detailed: revisionPayload.api_case_detailed.map((step) => ({
        ...pickCaseCompareFields(step, [
          'id',
          'logical_id',
          'case_sort',
          'execution_config',
          'posterior_sql',
          'api_info_id',
          'api_info_revision_id',
        ]),
        api_case_detailed_parameter: step.api_case_detailed_parameter,
      })),
    }
  }

  function pickCaseCompareFields(payload: Record<string, any>, fields: string[]) {
    return fields.reduce<Record<string, any>>((result, field) => {
      if (field === 'execution_config' && !Object.keys(payload.execution_config || {}).length) return result
      result[field] = payload?.[field]
      return result
    }, {})
  }

  function getRevisionUserMeta(item: ApiCaseRevisionListItem) {
    return `创建/编辑：${item.operator_name || '-'}`
  }

  function getRevisionUpdateTimeMeta(item: ApiCaseRevisionListItem) {
    return `更新时间：${item.create_time || '-'}`
  }

  function getRevisionPopoverKey(item: ApiCaseRevisionListItem) {
    return `revision-${item.id}`
  }

  function getRevisionPopoverItems(item: ApiCaseRevisionListItem) {
    return [
      { label: '类型', value: item.release ? '发布版本' : '修订版本' },
      { label: '状态', value: revisionStatus(item).text },
      { label: '修订ID', value: item.id },
      { label: '修订号', value: item.revision_no },
      { label: '创建/编辑', value: item.operator_name || '-' },
      { label: '更新时间', value: item.create_time || '-' },
      { label: '来源', value: item.summary || '-' },
      { label: '哈希', value: item.checksum || '-' },
    ]
  }

  async function selectPreferredRevision() {
    await refresh()
    const current = revisions.value.find((item) => item.release?.is_current)
    if (prepublishedRevision.value) await selectRevision(prepublishedRevision.value)
    else if (current) await selectRevision(current)
    else selectCurrent()
  }

  function clearVersionPopoverTimer() {
    if (popoverTimer) {
      clearTimeout(popoverTimer)
      popoverTimer = null
    }
  }

  function clearVersionPopoverCloseTimer() {
    if (popoverCloseTimer) {
      clearTimeout(popoverCloseTimer)
      popoverCloseTimer = null
    }
  }

  function startVersionPopoverTimer(key: string) {
    clearVersionPopoverTimer()
    clearVersionPopoverCloseTimer()
    popoverTimer = setTimeout(() => {
      activePopoverKey.value = key
    }, 1000)
  }

  function restartVersionPopoverTimer(key: string) {
    if (activePopoverKey.value === key) return
    startVersionPopoverTimer(key)
  }

  function hideVersionPopover(key: string) {
    clearVersionPopoverTimer()
    clearVersionPopoverCloseTimer()
    popoverCloseTimer = setTimeout(() => {
      if (activePopoverKey.value === key) activePopoverKey.value = ''
    }, 160)
  }

  function keepVersionPopover(key: string) {
    clearVersionPopoverCloseTimer()
    activePopoverKey.value = key
  }

  watch(() => props.caseId, refresh)
  onMounted(refresh)
  onBeforeUnmount(() => {
    clearVersionPopoverTimer()
    clearVersionPopoverCloseTimer()
  })
  defineExpose({ refresh, selectPreferredRevision, openResultHistoryDrawer })
</script>

<style scoped>
  .case-version-sidebar {
    display: flex;
    height: 100%;
    min-height: 0;
    overflow: hidden;
    flex-direction: column;
  }
  .version-panel-head {
    display: flex;
    flex-shrink: 0;
    align-items: flex-start;
    justify-content: space-between;
    gap: 8px;
    padding: 12px;
  }
  .version-panel-head strong {
    display: block;
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }
  .version-panel-head small {
    display: block;
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }
  .version-panel-list {
    display: flex;
    flex: 1 1 auto;
    width: 100%;
    min-height: 0;
    overflow: hidden;
  }
  .version-panel-list :deep(> .mango-panel-spin__content) {
    display: flex;
    flex: 1;
    width: 100%;
    min-height: 0;
  }
  .version-panel-scroll {
    display: flex;
    flex: 1;
    width: 100%;
    flex-direction: column;
    gap: 8px;
    min-height: 0;
    box-sizing: border-box;
    padding: 4px 12px 12px;
    overflow-x: hidden;
    overflow-y: auto;
  }
  .version-panel-scroll :deep(.arco-trigger) {
    width: 100%;
  }
  .version-card {
    display: flex;
    flex: none;
    width: 100%;
    margin: 0;
    flex-direction: column;
    gap: 6px;
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
    color: var(--m-text-2);
    text-align: left;
    cursor: pointer;
    transition: border-color 0.2s ease, background 0.2s ease;
  }
  .version-card:hover {
    border-color: color-mix(in srgb, var(--m-primary) 28%, var(--m-border));
    background: var(--m-surface);
  }
  .current-version-card {
    border-color: color-mix(in srgb, var(--m-warning) 18%, var(--m-border));
    background: color-mix(in srgb, var(--m-warning) 5%, var(--m-surface));
  }
  .current-version-card:hover {
    border-color: color-mix(in srgb, var(--m-warning) 32%, var(--m-border));
    background: color-mix(in srgb, var(--m-warning) 8%, var(--m-surface));
  }
  .version-card.active {
    border-color: var(--m-primary);
    background: color-mix(in srgb, var(--m-primary) 10%, var(--m-surface));
    box-shadow: inset 3px 0 0 var(--m-primary);
  }
  .version-card strong,
  .version-card small {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .version-card strong {
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
  }
  .version-card small {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }
  .version-card-head {
    display: flex;
    min-width: 0;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  .version-card-head strong {
    min-width: 0;
  }
  .case-version-sidebar-actions {
    display: flex;
    flex-shrink: 0;
    flex-direction: column;
    gap: 8px;
    padding: 10px;
    border-top: 1px solid var(--m-border);
    background: var(--m-surface);
  }
  .prepublication-waiting {
    padding: 6px 8px;
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
    text-align: center;
  }
  .version-popover-content {
    width: 340px;
    max-height: 360px;
    overflow-y: auto;
  }
  .version-popover-title {
    margin-bottom: 8px;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
  }
  .version-popover-list {
    display: flex;
    margin: 0;
    flex-direction: column;
    gap: 6px;
  }
  .version-popover-row {
    display: grid;
    grid-template-columns: 78px minmax(0, 1fr);
    gap: 10px;
    font-size: 12px;
    line-height: 18px;
  }
  .version-popover-row dt {
    color: var(--m-muted);
  }
  .version-popover-row dd {
    margin: 0;
    color: var(--m-text-2);
    word-break: break-all;
  }
</style>
