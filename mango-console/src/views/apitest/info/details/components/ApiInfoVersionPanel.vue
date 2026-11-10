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
          :disabled="selecting || busy"
          @click="selectedKey !== 'current' && selectCurrent()"
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
            :disabled="selecting || busy"
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
        :disabled="busy"
        :loading="creatingRevision"
        @click="createRevision"
        data-testid="qa-views-apitest-info-details-components-apiinfoversionpanel-button-生成修订"
      >
        生成修订
      </a-button>
      <a-button
        v-if="selectedRevision && !selectedRevision.release?.is_current"
        long
        :disabled="busy"
        type="primary"
        :loading="publishing"
        @click="publishSelected"
      >
        {{ selectedRevision.release ? '设为当前发布' : `发布 ${nextReleaseLabel}` }}
      </a-button>
      <a-button
        v-if="selectedRevision"
        long
        :disabled="busy"
        :loading="checkingOut"
        @click="checkoutSelectedRevision"
        data-testid="qa-views-apitest-info-details-components-apiinfoversionpanel-button-迁出到编辑态"
      >
        迁出到编辑态
      </a-button>
      <a-button
        v-if="selectedRevision && !selectedRevision.release"
        long
        :disabled="busy"
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
    :key="`compare-${windowSession}`"
    v-model:visible="compareDrawerVisible"
    left-title="当前编辑态"
    :left-payload="apiInfoCompareLeftPayload"
    :targets="apiInfoCompareTargets"
    :load-target-payload="loadApiInfoCompareTarget"
  />
  <ExecutionResultHistoryDrawer
    :key="`history-${windowSession}`"
    v-model:visible="resultHistoryVisible"
    :title="resultHistoryTitle"
    :query="resultHistoryQuery"
  />
</template>

<script setup lang="ts">
  import { computed, onBeforeUnmount, onDeactivated, onActivated, ref, watch } from 'vue'
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

  import {
    cloneLosslessJson,
    isLosslessJsonNumber,
    stringifyLosslessJson,
  } from '@/utils/lossless-json'
  import { apiInfoEditableFields } from '../config'
  import type { ApiInfoRecord, ApiVersionSelection } from '../types'
  import type { ApiInfoRevisionDetail } from '@/types/api-test/info-version'

  const props = defineProps<{
    apiInfoId: number | string
    currentPayload?: Partial<ApiInfoRecord> | null
    beforeAction?: () => Promise<unknown>
  }>()
  const emit = defineEmits<{
    (event: 'select', value: ApiVersionSelection): void
    (event: 'checkout'): void
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
    if (!publishedRevisionPayloadLoaded.value) return '发布快照暂不可用'
    if (hasUnpublishedChanges.value) {
      return `与 ${getRevisionTitle(currentRelease.value)} 不一致`
    }
    return `与 ${getRevisionTitle(currentRelease.value)} 一致`
  })
  const versionStateTitle = computed(() => {
    if (!currentRelease.value) return '当前接口尚未发布'
    if (!publishedRevisionPayloadLoaded.value) return '发布快照暂不可用'
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

  function stableSerialize(value: unknown): string {
    if (Array.isArray(value)) {
      return stringifyLosslessJson(value.map((item) => stableValue(item))) || ''
    }
    return stringifyLosslessJson(stableValue(value)) || ''
  }

  function stableValue(value: unknown): unknown {
    if (isLosslessJsonNumber(value)) return value
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

  let active = true,
    generation = 0,
    listRequest = 0,
    publishedRequest = 0
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const windowSession = ref(0)
  const busy = computed(
    () => creatingRevision.value || checkingOut.value || publishing.value || deletingRevision.value
  )
  function current(token: number) {
    return active && generation === token
  }
  function pickApiInfoEditablePayload(payload: Partial<ApiInfoRecord> | null | undefined) {
    return Object.fromEntries(
      Object.entries(payload || {}).filter(([key]) => apiInfoEditableFields.includes(key))
    )
  }
  function unwrap<T>(response: { data?: T } | T): T {
    return ((response as { data?: T })?.data ?? response) as T
  }
  function selectCurrent() {
    if (!active) return
    selectRequestSeq++
    selecting.value = false
    selectedKey.value = 'current'
    emit('select', {
      kind: 'current',
      id: Number(props.apiInfoId),
      label: '当前编辑态',
      payload: cloneLosslessJson(props.currentPayload || {}),
    })
  }
  async function selectRevision(revision: ApiInfoRevisionListItem) {
    if (selecting.value || busy.value || !active) return
    const token = generation,
      request = ++selectRequestSeq,
      previous = selectedKey.value
    selectedKey.value = `revision-${revision.id}`
    selecting.value = true
    try {
      try { await props.beforeAction?.() } catch { /* 只读查看不被之前的保存失败阻止。 */ }
      if (!current(token) || request !== selectRequestSeq) return
      const detail = unwrap<ApiInfoRevisionDetail>(await getApiInfoRevisionDetail(revision.id))
      if (!current(token) || request !== selectRequestSeq) return
      emit('select', {
        kind: 'revision',
        id: revision.id,
        label: getRevisionTitle(revision),
        payload: cloneLosslessJson(parseApiInfoRevisionPayload(detail.payload).api_info),
      })
    } catch {
      if (current(token) && request === selectRequestSeq) selectedKey.value = previous
    } finally {
      if (current(token) && request === selectRequestSeq) selecting.value = false
    }
  }
  async function refresh() {
    if (!props.apiInfoId || !active) return
    const token = generation,
      request = ++listRequest,
      target = props.apiInfoId
    loading.value = true
    try {
      const rows = unwrap<ApiInfoRevisionListItem[]>(await getApiInfoRevisionList(target)) || []
      if (!current(token) || request !== listRequest) return
      revisions.value = rows
      await loadPublishedRevisionPayload()
      if (!current(token) || request !== listRequest) return
      if (!selectedKey.value || selectedKey.value === 'current' || !selectedRevision.value)
        selectCurrent()
    } catch {
      /* 公共请求层反馈错误，保留版本列表。 */
    } finally {
      if (current(token) && request === listRequest) loading.value = false
    }
  }
  async function loadPublishedRevisionPayload() {
    const token = generation,
      request = ++publishedRequest,
      revision = currentRelease.value
    publishedRevisionPayload.value = null
    publishedRevisionPayloadLoaded.value = false
    if (!revision) {
      publishedRevisionPayloadLoaded.value = true
      return
    }
    try {
      const detail = unwrap<ApiInfoRevisionDetail>(await getApiInfoRevisionDetail(revision.id))
      if (!current(token) || request !== publishedRequest) return
      publishedRevisionPayload.value = pickApiInfoEditablePayload(
        parseApiInfoRevisionPayload(detail.payload).api_info
      )
      publishedRevisionPayloadLoaded.value = true
    } catch {
      /* 快照不可用时不声称编辑态与发布版本一致。 */
    }
  }
  async function createRevision() {
    if (busy.value || !active) return
    const token = generation,
      target = props.apiInfoId
    creatingRevision.value = true
    try {
      await props.beforeAction?.()
      if (!current(token)) return
      const revision = unwrap<ApiInfoRevisionListItem>(
        await createApiInfoRevision(target, '从当前配置生成修订')
      )
      if (!current(token)) return
      Message.success('已从当前编辑态生成修订，尚未发布')
      await refresh()
      if (!current(token)) return
      const row = revisions.value.find((item) => item.id === revision.id)
      creatingRevision.value = false
      if (row) await selectRevision(row)
    } catch {
      /* 公共请求层反馈错误，可重新生成修订。 */
    } finally {
      creatingRevision.value = false
    }
  }
  function confirmRevision(action: 'publish' | 'checkout' | 'delete') {
    const revision = selectedRevision.value
    if (
      !revision ||
      busy.value ||
      confirmation ||
      !active ||
      (action === 'delete' && revision.release)
    )
      return
    const token = generation,
      target = props.apiInfoId,
      revisionId = revision.id
    const pending =
      action === 'publish' ? publishing : action === 'checkout' ? checkingOut : deletingRevision
    const config =
      action === 'publish'
        ? {
            title: '发布接口版本',
            content: revision.release
              ? '确认将该版本设为当前发布吗？已有用例不会自动切换到该版本。'
              : '确认发布该修订为正式版本吗？已有用例不会自动切换到新版本。',
            okText: '确认发布',
          }
        : action === 'checkout'
        ? {
            title: '迁出到编辑态',
            content: '迁出后将覆盖当前配置，原版本会保留，是否继续？',
            okText: '确认迁出',
          }
        : {
            title: '删除未发布修订',
            content: `确认删除修订 r${revision.revision_no} 吗？删除后不可恢复。`,
            okText: '确认删除',
          }
    const modal = Modal.confirm({
      ...config,
      okButtonProps: action === 'delete' ? { status: 'danger' } : undefined,
      async onBeforeOk() {
        if (!current(token) || busy.value) return false
        pending.value = true
        try {
          await props.beforeAction?.()
          if (!current(token)) return false
          if (action === 'publish') await publishApiInfoRevision(target, revisionId)
          else if (action === 'checkout') await checkoutApiInfoRevision(target, revisionId)
          else await deleteApiInfoRevision(target, revisionId)
          if (!current(token)) return true
          Message.success(
            action === 'publish'
              ? '已发布；已有用例版本未变'
              : action === 'checkout'
              ? '已迁出到编辑态'
              : '修订已删除'
          )
          if (action === 'checkout') {
            emit('checkout')
            return true
          }
          if (action === 'delete') selectedKey.value = 'current'
          await refresh()
          return true
        } catch {
          return false
        } finally {
          pending.value = false
        }
      },
      onClose() {
        if (confirmation === modal) confirmation = null
      },
    })
    confirmation = modal
  }
  function publishSelected() {
    confirmRevision('publish')
  }
  function checkoutSelectedRevision() {
    confirmRevision('checkout')
  }
  function deleteSelectedRevision() {
    confirmRevision('delete')
  }
  function openCompareDrawer() {
    compareDrawerVisible.value = true
  }
  function openResultHistoryDrawer() {
    resultHistoryVisible.value = true
  }
  async function loadApiInfoCompareTarget(target: ApiVersionCompareTarget) {
    if (target.payload) return target.payload
    const token = generation,
      revisionId = Number(target.key.replace('revision-', ''))
    const detail = unwrap<ApiInfoRevisionDetail>(await getApiInfoRevisionDetail(revisionId))
    if (!current(token)) return {}
    return pickApiInfoEditablePayload(parseApiInfoRevisionPayload(detail.payload).api_info)
  }
  function close() {
    active = false
    generation++
    listRequest++
    publishedRequest++
    selectRequestSeq++
    loading.value = false
    selecting.value = false
    compareDrawerVisible.value = false
    resultHistoryVisible.value = false
    windowSession.value++
    confirmation?.close()
    confirmation = null
    clearVersionPopoverTimer()
    clearVersionPopoverCloseTimer()
    activePopoverKey.value = ''
  }
  watch(
    selectedKey,
    () => {
      compareDrawerVisible.value = false
      resultHistoryVisible.value = false
    },
    { flush: 'sync' }
  )
  watch(
    [compareDrawerVisible, resultHistoryVisible],
    ([compare, history], [oldCompare, oldHistory]) => {
      if ((oldCompare && !compare) || (oldHistory && !history)) windowSession.value++
    }
  )
  watch(
    () => props.apiInfoId,
    () => {
      close()
      active = true
      revisions.value = []
      selectedKey.value = 'current'
      publishedRevisionPayload.value = null
      publishedRevisionPayloadLoaded.value = false
      void refresh()
    },
    { immediate: true }
  )
  onBeforeUnmount(close)
  onDeactivated(close)
  onActivated(() => {
    if (!active) {
      active = true
      void refresh()
    }
  })
  defineExpose({ refresh, openResultHistoryDrawer, close })
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
