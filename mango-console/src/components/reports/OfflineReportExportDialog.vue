<template>
  <a-modal modal-class="mango-simple-form-modal" :visible="visible" title="导出离线 HTML" :width="560" :footer="false" @cancel="close">
    <div v-if="selectReport" class="mango-offline-export__selection">
      <a-form auto-label-width :model="selectionForm" class="mango-simple-form" layout="horizontal">
        <a-form-item class="mango-simple-form-item" label="执行报告" required>
          <a-select v-model="selectedId" :loading="optionsLoading" :disabled="busy"
            placeholder="请选择已完成的执行报告" allow-search @dropdown-reach-bottom="loadMoreOptions">
            <a-option v-for="item in options" :key="item.id" :value="item.id" :label="optionLabel(item)" />
            <template #footer>
              <div class="mango-offline-export__load-more" role="status">
                <span v-if="optionsLoading">正在加载…</span>
                <a-button v-else-if="optionsError" size="small" @click.stop="retryOptions">重试</a-button>
                <span v-else-if="page * 20 < total">向下滚动加载更多</span>
                <span v-else-if="options.length">已加载全部 {{ total }} 条</span>
              </div>
            </template>
          </a-select>
        </a-form-item>
      </a-form>
      <a-button v-if="optionsError && !options.length" size="small" :loading="optionsLoading" @click="retryOptions">重新加载</a-button>

    </div>
    <a-alert>实时生成 HTML 报告，不会重新执行 Case。</a-alert>
    <p role="status" :class="{ 'mango-offline-export__error': error }">{{ statusText }}</p>
    <div v-if="links" class="mango-offline-export__result">
      <div class="mango-offline-export__links">
        <a :href="links.preview_url" target="_blank" rel="noopener noreferrer">在线预览</a>
        <a :href="links.download_url" target="_blank" rel="noopener noreferrer">下载 HTML</a>
      </div>
      <p class="mango-offline-export__expiry">链接有效至：{{ expiresAtText }}。请勿向无关人员转发。</p>
    </div>
    <div class="mango-offline-export__actions">
      <a-button size="small" @click="close">关闭</a-button>
      <a-button type="primary" size="small" :loading="busy" :disabled="!canGenerate" @click="generate">{{ links || downloaded ? '重新生成' : '生成报告' }}</a-button>
    </div>
  </a-modal>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { downloadOfflineReport, generateOfflineReport, getOfflineReportOptions, offlineReportId, parseOfflineReportLinks, parseOfflineReportOptions } from '@/api/system/offline_report'
  import type { OfflineReportLinks, OfflineReportOption, ReportSource } from '@/api/system/offline_report'
  import { isApiBusinessError } from '@/api/errors'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import usePermissionStore from '@/store/modules/permission'

  const props = defineProps<{ visible: boolean; sourceKind: ReportSource; sourceId: string | number; selectReport?: boolean }>()
  const emit = defineEmits<{ (event: 'update:visible', value: boolean): void }>()
  const enumStore = useEnum(), route = useRoute(), user = useUserStore(), permission = usePermissionStore(), pagePath = route.path
  const downloading = ref(false), busy = ref(false), downloaded = ref(false), error = ref('')
  const links = ref<OfflineReportLinks | null>(null), options = ref<OfflineReportOption[]>([])
  const selectedId = ref<string | number | null>(null), page = ref(0), total = ref(0), optionsLoading = ref(false), optionsError = ref('')
  const selectionForm = computed(() => ({ selectedId: selectedId.value }))
  const expiresAtText = computed(() => links.value ? new Date(links.value.expires_at).toLocaleString('zh-CN', { hour12: false }) : '')
  let mounted = false, active = true, disposed = false, closedUntilReopen = false, session = 0, generation = 0, needsOptions = false
  let controller: AbortController | undefined, optionsController: AbortController | undefined
  const identity = () => JSON.stringify([route.path, route.fullPath, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
  const sourceKey = () => JSON.stringify([identity(), props.sourceKind, props.sourceId, Boolean(props.selectReport)])
  const available = () => mounted && active && !disposed && route.path === pagePath && document.visibilityState === 'visible' && props.visible && !closedUntilReopen
  const validSource = () => ['suite', 'group'].includes(props.sourceKind) && offlineReportId(props.sourceId) !== null
  const targetId = computed(() => offlineReportId(props.selectReport ? selectedId.value : props.sourceId))
  const canGenerate = computed(() => validSource() && targetId.value !== null && (!props.selectReport || options.value.some(item => String(item.id) === String(targetId.value))))
  function enumLabel(value: unknown, key: number | null) {
    if (!Array.isArray(value)) return key === null ? '-' : String(key)
    for (const entry of value) {
      if (!entry || typeof entry !== 'object') continue
      const option = entry as { key?: unknown; title?: unknown }
      if (String(option.key) === String(key) && typeof option.title === 'string') return option.title
    }
    return key === null ? '-' : String(key)
  }
  function optionLabel(item: OfflineReportOption) {
    const timestamp = Number.isFinite(Date.parse(item.started_at)) ? item.started_at.replace('T', ' ').slice(0, 19) : '-'
    return `${enumLabel(enumStore.environment_type, item.test_env)} · ${timestamp} · ${enumLabel(enumStore.task_status, item.status)} · ID ${item.id}`
  }
  function cancelGeneration() {
    generation++
    controller?.abort()
    downloading.value = false
  }
  function cancelRequest() {
    session++
    cancelGeneration()
    optionsController?.abort(); optionsController = undefined; optionsLoading.value = false
  }
  function reset() {
    cancelRequest(); downloaded.value = false; links.value = null; error.value = ''; optionsError.value = ''
    selectedId.value = null; options.value = []; page.value = 0; total.value = 0
    needsOptions = Boolean(props.selectReport)
  }
  function close() { closedUntilReopen = true; reset(); emit('update:visible', false) }
  async function loadOptions(append = false) {
    if (!available() || !props.selectReport || !validSource() || optionsLoading.value || busy.value || (append && page.value * 20 >= total.value)) return
    const request = new AbortController(), key = sourceKey(), currentSession = session
    optionsController = request; optionsLoading.value = true; optionsError.value = ''; needsOptions = false
    if (!append) { selectedId.value = null; options.value = []; page.value = 0; total.value = 0 }
    const nextPage = append ? page.value + 1 : 1, kind = props.sourceKind, id = props.sourceId
    const current = () => available() && !request.signal.aborted && currentSession === session && key === sourceKey()
    try {
      const result = parseOfflineReportOptions(await getOfflineReportOptions(kind, id, nextPage, request.signal))
      if (!current()) return
      const merged = new Map(options.value.map(item => [String(item.id), item]))
      result.items.forEach(item => merged.set(String(item.id), item))
      options.value = [...merged.values()]; total.value = result.count; page.value = nextPage
    } catch (cause: unknown) {
      if (current()) (reportLoadError(cause, "加载失败，请重试", false), optionsError.value = cause instanceof Error ? cause.message : '读取执行报告失败，请重试。')
    } finally {
      if (optionsController === request) { optionsLoading.value = false; optionsController = undefined }
    }
  }
  function loadMoreOptions() { return loadOptions(true) }
  function retryOptions() { return loadOptions(page.value > 0) }
  const statusText = computed(() => error.value || (downloading.value ? '正在生成并上传，请稍候…' : busy.value ? '正在结束上次生成，请稍候…' : links.value ? '报告已生成，可直接预览或下载。' : downloaded.value ? '当前为本地存储，已发起 HTML 下载；在线预览需配置 MinIO/TOS。' : '每次生成均使用最新结果，链接有效期沿用报告配置。'))
  async function generate() {
    const id = targetId.value
    if (!available() || busy.value || !canGenerate.value || id === null) return false
    const request = new AbortController(), key = sourceKey(), currentGeneration = ++generation, currentSession = session, kind = props.sourceKind
    controller = request; busy.value = true; downloading.value = true
    error.value = ''; links.value = null; downloaded.value = false
    const current = () => available() && !request.signal.aborted && currentGeneration === generation && currentSession === session && key === sourceKey() && String(id) === String(targetId.value)
    try {
      try {
        const result = parseOfflineReportLinks(await generateOfflineReport(kind, id, request.signal))
        if (!current()) return false
        links.value = result
      } catch (cause: unknown) {
        if (!current()) return false
        if (!isApiBusinessError(cause) || cause.code !== 40047) throw cause
        await downloadOfflineReport(kind, id, request.signal)
        if (!current()) return false
        downloaded.value = true
      }
      return true
    } catch (cause: unknown) {
      if (current()) error.value = cause instanceof Error ? cause.message : '生成或上传失败，请重试。'
      return false
    } finally {
      if (controller === request) { busy.value = false; downloading.value = false; controller = undefined; resume() }
    }
  }
  function pause() {
    needsOptions = Boolean(props.selectReport && (optionsController || optionsError.value || !options.value.length))
    cancelRequest()
  }
  function resume() { if (available() && needsOptions) void loadOptions(page.value > 0) }
  function visibilityChanged() { if (document.visibilityState === 'visible') resume(); else pause() }
  watch(() => [props.visible, props.sourceKind, props.sourceId, props.selectReport], (value, previous) => {
    if (!props.visible || !previous?.[0]) closedUntilReopen = false
    reset(); resume()
  }, { immediate: true, flush: 'sync' })
  watch(selectedId, () => { cancelGeneration(); downloaded.value = false; links.value = null; error.value = '' }, { flush: 'sync' })
  watch(identity, () => { reset(); if (props.visible) { closedUntilReopen = true; emit('update:visible', false) } }, { flush: 'sync' })
  onMounted(() => { mounted = true; document.addEventListener('visibilitychange', visibilityChanged); resume() })
  onActivated(() => { const wasInactive = !active; active = true; if (wasInactive) resume() })
  onDeactivated(() => { active = false; pause() })
  onBeforeUnmount(() => { disposed = true; cancelRequest(); document.removeEventListener('visibilitychange', visibilityChanged) })
</script>

<style scoped>
  .mango-offline-export__actions { display: flex; justify-content: flex-end; gap: var(--m-space-sm); margin-top: 20px; }
  .mango-offline-export__error { color: var(--m-danger); overflow-wrap: anywhere; }
  .mango-offline-export__selection { margin-bottom: 16px; }
  .mango-offline-export__load-more { padding: 8px 12px; text-align: center; color: var(--m-muted); font-size: 12px; }
  .mango-offline-export__result { margin-top: 12px; }
  .mango-offline-export__links { display: flex; flex-wrap: wrap; gap: var(--m-space-sm); }
  .mango-offline-export__links a { color: var(--m-primary); border: 1px solid var(--m-border); border-radius: var(--m-radius-md); padding: 4px 12px; text-decoration: none; }
  .mango-offline-export__links a:hover { border-color: var(--m-primary); background: var(--m-primary-soft); }
  .mango-offline-export__expiry { color: var(--m-muted); font-size: 12px; overflow-wrap: anywhere; margin-top: 8px; }
</style>
