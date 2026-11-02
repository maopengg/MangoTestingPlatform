<template>
  <aside class="api-info-version-panel">
    <div class="version-panel-head">
      <div>
        <strong>版本</strong>
        <small>选择后查看对应配置</small>
      </div>
      <a-space size="mini">
        <a-button
          size="mini"
          type="outline"
          @click="openCompareDrawer"
          data-testid="qa-views-apitest-info-details-components-apiinfoversionpanel-button-版本比对"
          >版本比对</a-button
        >
      </a-space>
    </div>
    <mango-panel-spin :loading="loading || selecting" class="version-panel-list">
      <div class="version-panel-scroll">
        <button
          type="button"
          class="version-card current-version-card"
          :class="{ active: selectedKey === 'current' }"
          :disabled="selecting"
          @click="selectCurrent"
        >
          <div class="version-card-head">
            <strong>当前配置</strong>
            <a-tag v-if="!currentRelease" size="small" color="orange">尚未发布</a-tag>
            <a-tag v-else-if="hasUnpublishedChanges" size="small" color="orange">
              未发布变更
            </a-tag>
            <a-tag v-else size="small" color="blue">编辑态</a-tag>
          </div>
          <small>{{ currentVersionSummary }}</small>
          <small>调试通过后生成修订</small>
        </button>

        <a-popover
          v-for="revision in revisions"
          :key="revision.id"
          position="right"
          :popup-visible="activePopoverKey === getRevisionPopoverKey(revision)"
          content-class="version-detail-popover"
        >
          <button
            type="button"
            class="version-card"
            :class="{ active: selectedKey === `revision-${revision.id}` }"
            :disabled="selecting"
            @click="selectRevision(revision)"
            @mouseenter="startVersionPopoverTimer(getRevisionPopoverKey(revision))"
            @mousemove="restartVersionPopoverTimer(getRevisionPopoverKey(revision))"
            @mouseleave="hideVersionPopover(getRevisionPopoverKey(revision))"
          >
            <div class="version-card-head">
              <strong>{{ getRevisionTitle(revision) }}</strong>
              <a-tag v-if="revision.release?.is_current" size="small" color="green">当前发布</a-tag>
              <a-tag v-else-if="revision.release" size="small" color="gray">历史版本</a-tag>
              <a-tag v-else size="small" color="orange">未发布修订</a-tag>
            </div>
            <small>{{ getRevisionUserMeta(revision) }}</small>
            <small>{{ getRevisionUpdateTimeMeta(revision) }}</small>
          </button>
          <template #content>
            <div
              class="version-popover-content"
              @mouseenter="keepVersionPopover(getRevisionPopoverKey(revision))"
              @mouseleave="hideVersionPopover(getRevisionPopoverKey(revision))"
            >
              <div class="version-popover-title">{{ getRevisionTitle(revision) }}</div>
              <dl class="version-popover-list">
                <div
                  v-for="item in getRevisionPopoverItems(revision)"
                  :key="item.label"
                  class="version-popover-row"
                >
                  <dt>{{ item.label }}</dt>
                  <dd>{{ item.value }}</dd>
                </div>
              </dl>
            </div>
          </template>
        </a-popover>
      </div>
    </mango-panel-spin>
    <div
      class="version-state-notice"
      :class="{ warning: hasUnpublishedChanges }"
      role="status"
      aria-live="polite"
    >
      <strong>{{ versionStateTitle }}</strong>
      <span>{{ versionStateDescription }}</span>
    </div>
    <div class="api-info-version-actions">
      <a-button
        v-if="selectedKey === 'current'"
        long
        :loading="creatingRevision"
        @click="createRevision"
        data-testid="qa-views-apitest-info-details-components-apiinfoversionpanel-button-生成修订"
      >
        生成修订
      </a-button>
      <a-button
        v-if="selectedRevision && !selectedRevision.release?.is_current"
        long
        type="primary"
        :loading="publishing"
        @click="publishSelected"
      >
        {{ selectedRevision.release ? '设为当前发布' : `发布 ${nextReleaseLabel}` }}
      </a-button>
      <a-button
        v-if="selectedRevision"
        long
        :loading="checkingOut"
        @click="checkoutSelectedRevision"
        data-testid="qa-views-apitest-info-details-components-apiinfoversionpanel-button-迁出到编辑态"
      >
        迁出到编辑态
      </a-button>
      <a-button
        v-if="selectedRevision && !selectedRevision.release"
        long
        status="danger"
        :loading="deletingRevision"
        @click="deleteSelectedRevision"
        data-testid="qa-views-apitest-info-details-components-apiinfoversionpanel-button-删除修订"
      >
        删除修订
      </a-button>
    </div>
  </aside>
  <ApiVersionCompareDrawer
    v-model:visible="compareDrawerVisible"
    left-title="当前编辑态"
    :left-payload="apiInfoCompareLeftPayload"
    :targets="apiInfoCompareTargets"
    :load-target-payload="loadApiInfoCompareTarget"
  />
  <ExecutionResultHistoryDrawer
    v-model:visible="resultHistoryVisible"
    :title="resultHistoryTitle"
    :query="resultHistoryQuery"
  />
</template>

<script lang="ts" setup>
  import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import ApiVersionCompareDrawer from '@/components/business/ApiVersionCompareDrawer.vue'
  import ExecutionResultHistoryDrawer from '@/components/business/ExecutionResultHistoryDrawer.vue'
  import type { ApiVersionCompareTarget } from '@/types/api-test/version-compare'
  import {
    checkoutApiInfoRevision,
    createApiInfoRevision,
    deleteApiInfoRevision,
    getApiInfoRevisionDetail,
    getApiInfoRevisionList,
    publishApiInfoRevision,
  } from '@/api/apitest/info-version'
  import type { ApiInfoRevisionListItem } from '@/types/api-test/info-version'
  import { parseApiInfoRevisionPayload } from '@/types/api-test/info-revision-payload'

  const props = defineProps<{
    apiInfoId: number | string
    currentPayload?: Record<string, any> | null
  }>()
  const emit = defineEmits<{
    (
      event: 'select',
      value: { kind: 'current' | 'revision'; id: number; label: string; payload: any }
    ): void
  }>()

  const revisions = ref<ApiInfoRevisionListItem[]>([])
  const selectedKey = ref('current')
  const loading = ref(false)
  const selecting = ref(false)
  const creatingRevision = ref(false)
  const checkingOut = ref(false)
  const publishing = ref(false)
  const deletingRevision = ref(false)
  const compareDrawerVisible = ref(false)
  const resultHistoryVisible = ref(false)
  const publishedRevisionPayload = ref<Record<string, unknown> | null>(null)
  const publishedRevisionPayloadLoaded = ref(false)
  const activePopoverKey = ref('')
  let popoverTimer: ReturnType<typeof setTimeout> | null = null
  let popoverCloseTimer: ReturnType<typeof setTimeout> | null = null
  let selectRequestSeq = 0

  const selectedRevision = computed(() => {
    if (!selectedKey.value.startsWith('revision-')) return null
    const revisionId = Number(selectedKey.value.replace('revision-', ''))
    return revisions.value.find((item) => item.id === revisionId) || null
  })
  const currentRelease = computed(() => revisions.value.find((item) => item.release?.is_current))
  const hasUnpublishedChanges = computed(() => {
    if (!currentRelease.value) return true
    if (!publishedRevisionPayloadLoaded.value || !publishedRevisionPayload.value) return false
    return (
      stableSerialize(pickApiInfoEditablePayload(props.currentPayload)) !==
      stableSerialize(publishedRevisionPayload.value)
    )
  })
  const currentVersionSummary = computed(() => {
    if (!currentRelease.value) return '当前配置尚未形成正式版本'
    if (hasUnpublishedChanges.value) {
      return `与 ${getRevisionTitle(currentRelease.value)} 不一致`
    }
    return `与 ${getRevisionTitle(currentRelease.value)} 一致`
  })
  const versionStateTitle = computed(() => {
    if (!currentRelease.value) return '当前接口尚未发布'
    return hasUnpublishedChanges.value ? '当前修改尚未发布' : '当前编辑态与发布版本一致'
  })
  const versionStateDescription = computed(() => {
    if (!currentRelease.value) return '生成修订并发布后，才能作为正式版本供用例选择。'
    if (hasUnpublishedChanges.value) {
      return '需生成修订并发布新版本；已有用例仍使用原接口版本。'
    }
    return '后续修改只保存到编辑态，不会直接覆盖已发布版本。'
  })
  const nextReleaseLabel = computed(() => {
    const latestVersionNo = revisions.value.reduce(
      (maximum, item) => Math.max(maximum, item.release?.version_no || 0),
      0
    )
    return `V${latestVersionNo + 1}`
  })
  const apiInfoCompareLeftPayload = computed(() => pickApiInfoEditablePayload(props.currentPayload))
  const apiInfoCompareTargets = computed<ApiVersionCompareTarget[]>(() =>
    revisions.value.map((revision) => ({
      key: `revision-${revision.id}`,
      label: getRevisionTitle(revision),
    }))
  )
  const resultHistoryTitle = computed(
    () =>
      `接口执行历史：${
        selectedRevision.value ? getRevisionTitle(selectedRevision.value) : '当前编辑态'
      }`
  )
  const resultHistoryQuery = computed(() => ({
    target_type: 'api_info',
    target_id: props.apiInfoId,
    ...(selectedRevision.value
      ? { revision_id: selectedRevision.value.id }
      : { revision_id_isnull: 1 }),
  }))

  const apiInfoEditableFields = [
    'url',
    'method',
    'protocol_type',
    'headers',
    'params',
    'is_text_params',
    'body_type',
    'body_config',
    'sse_config',
    'mcp_config',
    'posterior_json_path',
    'posterior_re',
    'posterior_func',
    'status',
  ]

  function unwrap<T>(response: any): T {
    return (response?.data ?? response) as T
  }

  function pickApiInfoEditablePayload(payload: any) {
    if (!payload) return {}
    return apiInfoEditableFields.reduce<Record<string, unknown>>((result, field) => {
      result[field] = payload[field]
      return result
    }, {})
  }

  function stableSerialize(value: unknown): string {
    if (Array.isArray(value)) {
      return JSON.stringify(value.map((item) => stableValue(item))) || ''
    }
    return JSON.stringify(stableValue(value)) || ''
  }

  function stableValue(value: unknown): unknown {
    if (Array.isArray(value)) return value.map((item) => stableValue(item))
    if (value && typeof value === 'object') {
      return Object.keys(value as Record<string, unknown>)
        .sort()
        .reduce<Record<string, unknown>>((result, key) => {
          result[key] = stableValue((value as Record<string, unknown>)[key])
          return result
        }, {})
    }
    return value
  }

  function selectCurrent() {
    selectRequestSeq += 1
    selectedKey.value = 'current'
    emit('select', {
      kind: 'current',
      id: Number(props.apiInfoId),
      label: '当前编辑态',
      payload: props.currentPayload || {},
    })
  }

  async function selectRevision(revision: ApiInfoRevisionListItem) {
    if (selecting.value) return
    const requestSeq = ++selectRequestSeq
    selectedKey.value = `revision-${revision.id}`
    selecting.value = true
    try {
      const detail = unwrap<any>(await getApiInfoRevisionDetail(revision.id))
      if (requestSeq !== selectRequestSeq || selectedKey.value !== `revision-${revision.id}`) return
      emit('select', {
        kind: 'revision',
        id: revision.id,
        label: getRevisionTitle(revision),
        payload: parseApiInfoRevisionPayload(detail.payload).api_info,
      })
    } finally {
      if (requestSeq === selectRequestSeq) selecting.value = false
    }
  }

  async function refresh() {
    if (!props.apiInfoId) return
    loading.value = true
    try {
      revisions.value =
        unwrap<ApiInfoRevisionListItem[]>(await getApiInfoRevisionList(props.apiInfoId)) || []
      await loadPublishedRevisionPayload()
      if (!selectedKey.value || selectedKey.value === 'current') selectCurrent()
    } finally {
      loading.value = false
    }
  }

  async function loadPublishedRevisionPayload() {
    publishedRevisionPayload.value = null
    publishedRevisionPayloadLoaded.value = false
    const revision = currentRelease.value
    if (!revision) {
      publishedRevisionPayloadLoaded.value = true
      return
    }
    try {
      const detail = unwrap<any>(await getApiInfoRevisionDetail(revision.id))
      publishedRevisionPayload.value = pickApiInfoEditablePayload(
        parseApiInfoRevisionPayload(detail.payload).api_info
      )
    } finally {
      publishedRevisionPayloadLoaded.value = true
    }
  }

  async function createRevision() {
    if (creatingRevision.value) return
    creatingRevision.value = true
    try {
      const revision = unwrap<ApiInfoRevisionListItem>(
        await createApiInfoRevision(props.apiInfoId, '从当前配置生成修订')
      )
      Message.success('已从当前编辑态生成修订，尚未发布')
      await refresh()
      const target = revisions.value.find((item) => item.id === revision.id)
      if (target) await selectRevision(target)
    } finally {
      creatingRevision.value = false
    }
  }

  function publishSelected() {
    if (!selectedRevision.value || publishing.value) return
    const revision = selectedRevision.value
    Modal.confirm({
      title: '发布接口版本',
      content: revision.release
        ? '确认将该版本设为当前发布吗？已有用例不会自动切换到该版本。'
        : '确认发布该修订为正式版本吗？已有用例不会自动切换到新版本。',
      okText: '确认发布',
      async onBeforeOk() {
        publishing.value = true
        try {
          await publishApiInfoRevision(props.apiInfoId, revision.id)
          Message.success('已发布；已有用例版本未变')
          await refresh()
          return true
        } finally {
          publishing.value = false
        }
      },
    })
  }

  function checkoutSelectedRevision() {
    if (!selectedRevision.value || checkingOut.value) return
    const revision = selectedRevision.value
    Modal.confirm({
      title: '迁出到编辑态',
      content: '迁出后将覆盖当前配置，原版本会保留，是否继续？',
      okText: '确认迁出',
      async onBeforeOk() {
        checkingOut.value = true
        try {
          await checkoutApiInfoRevision(props.apiInfoId, revision.id)
          Message.success('已迁出到编辑态')
          selectedKey.value = 'current'
          await refresh()
          return true
        } finally {
          checkingOut.value = false
        }
      },
    })
  }

  function deleteSelectedRevision() {
    if (!selectedRevision.value || selectedRevision.value.release || deletingRevision.value) return
    const revision = selectedRevision.value
    Modal.confirm({
      title: '删除未发布修订',
      content: `确认删除修订 r${revision.revision_no} 吗？删除后不可恢复。`,
      okText: '确认删除',
      okButtonProps: { status: 'danger' },
      async onBeforeOk() {
        deletingRevision.value = true
        try {
          await deleteApiInfoRevision(props.apiInfoId, revision.id)
          Message.success('修订已删除')
          selectCurrent()
          await refresh()
          return true
        } catch {
          return false
        } finally {
          deletingRevision.value = false
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

  async function loadApiInfoCompareTarget(target: ApiVersionCompareTarget) {
    if (target.payload) return target.payload
    const revisionId = Number(target.key.replace('revision-', ''))
    const detail = unwrap<any>(await getApiInfoRevisionDetail(revisionId))
    return pickApiInfoEditablePayload(parseApiInfoRevisionPayload(detail.payload).api_info)
  }

  function getRevisionTitle(revision: ApiInfoRevisionListItem) {
    return revision.release?.version_label || `修订 r${revision.revision_no}`
  }

  function getRevisionUserMeta(revision: ApiInfoRevisionListItem) {
    return `创建/编辑：${revision.operator_name || '-'}`
  }

  function getRevisionUpdateTimeMeta(revision: ApiInfoRevisionListItem) {
    return `更新时间：${revision.create_time || '-'}`
  }

  function getRevisionPopoverKey(revision: ApiInfoRevisionListItem) {
    return `revision-${revision.id}`
  }

  function getRevisionPopoverItems(revision: ApiInfoRevisionListItem) {
    return [
      { label: '类型', value: revision.release ? '发布版本' : '修订版本' },
      {
        label: '状态',
        value: revision.release?.is_current ? '当前发布' : revision.release ? '历史版本' : '未发布',
      },
      { label: '修订ID', value: revision.id },
      { label: '修订号', value: revision.revision_no },
      { label: '创建/编辑', value: revision.operator_name || '-' },
      { label: '更新时间', value: revision.create_time || '-' },
      { label: '来源', value: revision.summary || '-' },
      { label: '哈希', value: revision.checksum || '-' },
    ]
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

  watch(() => props.apiInfoId, refresh)
  onMounted(refresh)
  onBeforeUnmount(() => {
    clearVersionPopoverTimer()
    clearVersionPopoverCloseTimer()
  })
  defineExpose({ refresh, openResultHistoryDrawer })
</script>

<style scoped>
  .api-info-version-panel {
    display: flex;
    height: 100%;
    min-height: 0;
    overflow: hidden;
    flex-direction: column;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
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
    height: 100%;
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
  .version-card:disabled {
    cursor: wait;
    opacity: 0.72;
  }
  .version-card:disabled:hover {
    border-color: var(--m-border);
    background: var(--m-surface-soft);
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
  .api-info-version-actions {
    display: flex;
    flex-shrink: 0;
    flex-direction: column;
    gap: 8px;
    padding: 10px;
    border-top: 1px solid var(--m-border);
    background: var(--m-surface);
  }
  .version-state-notice {
    display: flex;
    flex-shrink: 0;
    margin: 0 10px 10px;
    flex-direction: column;
    gap: 2px;
    padding: 8px 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }
  .version-state-notice.warning {
    border-color: color-mix(in srgb, var(--m-warning) 28%, var(--m-border));
    background: color-mix(in srgb, var(--m-warning) 7%, var(--m-surface));
  }
  .version-state-notice strong {
    color: var(--m-text);
    font-size: 12px;
    font-weight: 600;
    line-height: 18px;
  }
  .version-state-notice span {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
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
