<template>
  <a-drawer
    :visible="visible && !dismissed"
    :width="drawerWidth"
    :footer="false"
    :closable="false"
    unmount-on-close
    class="mango-diagnostic-markdown-drawer"
    @update:visible="updateVisible"
  >
    <template #header>
      <div class="mango-diagnostic-markdown__drawer-header">
        <div class="mango-diagnostic-markdown__title">
          <strong>{{ title || '排查结果' }}</strong>
          <span>由 AI 排查并通过测试平台 MCP 回传</span>
        </div>
        <div class="mango-diagnostic-markdown__drawer-actions">
          <a-button
            v-if="document?.download_url"
            size="small"
            @click="downloadDocument"
          >
            下载 Markdown
          </a-button>
          <a-button
            type="text"
            shape="circle"
            aria-label="关闭排查结果"
            @click="closeDrawer"
          >
            <template #icon><icon-close /></template>
          </a-button>
        </div>
      </div>
    </template>

    <div class="mango-diagnostic-markdown">
      <mango-panel-spin :loading="loading" class="mango-diagnostic-markdown__loading">
        <div v-if="errorText" class="mango-empty-state mango-diagnostic-markdown__empty" role="alert">
          <strong>{{ errorText }}</strong>
          <a-button size="small" :loading="loading" @click="loadDocument">重试</a-button>
        </div>
        <div v-else-if="document" class="mango-diagnostic-markdown__document">
          <div
            class="mango-diagnostic-markdown__reader-layout"
            :class="{ 'mango-diagnostic-markdown__reader-layout--without-outline': !hasOutline }"
          >
            <aside v-if="hasOutline" class="mango-diagnostic-markdown__outline mango-scrollbar">
              <div class="mango-diagnostic-markdown__outline-title">文档大纲</div>
              <MdCatalog
                :editor-id="previewId"
                :scroll-element="scrollElement"
                :theme="markdownTheme"
                :offset-top="16"
                :catalog-max-depth="4"
              />
            </aside>
            <main class="mango-diagnostic-markdown__reader mango-scrollbar">
              <MdPreview
                :id="previewId"
                :model-value="markdownContent"
                :theme="markdownTheme"
                preview-theme="github"
              />
            </main>
          </div>
        </div>
        <div v-else-if="!loading" class="mango-empty-state mango-diagnostic-markdown__empty">
          <div class="mango-diagnostic-markdown__empty-mark">MD</div>
          <strong>尚未上传排查结果</strong>
          <p>
            请使用 <code>mango-scheduled-api-report-maintainer</code> Skill 完成定时任务报告分析，
            再通过测试平台 MCP 上传并绑定排查文档。
          </p>
          <span>Skill 可在测试平台首页下载，上传完成后刷新页面即可查看。</span>
        </div>
      </mango-panel-spin>
    </div>
  </a-drawer>
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message } from '@arco-design/web-vue'
  import { IconClose } from '@arco-design/web-vue/es/icon'
  import { MdCatalog, MdPreview } from 'md-editor-v3'
  import 'md-editor-v3/lib/preview.css'
  import { getSystemTaskDiagnosticMarkdown } from '@/api/system/tasks'
  import { getSystemTestSuiteDiagnosticMarkdown } from '@/api/system/test_suite'
  import useAppConfigStore from '@/store/modules/app-config'
  import { useUserStoreContext } from '@/store/modules/user'
  import { diagnosticTargetId, isMissingDiagnostic, parseDiagnosticDocument, type DiagnosticDocument } from './diagnostic-markdown'

  const props = defineProps<{
    visible: boolean
    targetType: 'scheduled_task' | 'test_report'
    targetId?: number | string | null
    documentAvailable?: boolean
    title?: string
  }>()
  const emit = defineEmits<{ (event: 'update:visible', value: boolean): void }>()

  const loading = ref(false)
  const errorText = ref(''), dismissed = ref(false)
  const document = ref<DiagnosticDocument | null>(null)
  const route = useRoute(), userStore = useUserStoreContext()
  let active = true, disposed = false, version = 0
  let pending: { version: number; promise: Promise<void> } | null = null
  const available = () => !disposed && active && props.visible && !dismissed.value && globalThis.document.visibilityState === 'visible'
  const appStore = useAppConfigStore()
  const drawerWidth = 'min(1280px, calc(100vw - 32px))'
  const previewId = 'mango-diagnostic-markdown-preview'
  const scrollElement = '.mango-diagnostic-markdown__reader'
  const markdownTheme = computed<'light' | 'dark'>(() => (
    appStore.theme === 'dark' ? 'dark' : 'light'
  ))

  const markdownContent = computed(() => {
    const content = String(document.value?.content || '')
    const frontmatter = content.match(/^---\r?\n[\s\S]*?\r?\n---(?:\r?\n)?/)
    return frontmatter ? content.slice(frontmatter[0].length) : content
  })
  const hasOutline = computed(() => /^#{1,4}\s+\S+/m.test(markdownContent.value))

  function closeDrawer() {
    dismissed.value = true
    invalidate()
    emit('update:visible', false)
  }
  function updateVisible(value: boolean) { if (!value) closeDrawer(); else emit('update:visible', true) }
  function invalidate() {
    version += 1
    document.value = null
    errorText.value = ''
    loading.value = false
  }

  function downloadDocument() {
    if (!available()) return
    if (!document.value?.download_url) {
      Message.warning('当前排查文档暂无可用下载地址')
      return
    }
    const anchor = globalThis.document.createElement('a')
    anchor.href = document.value.download_url
    anchor.download = document.value.file_name || 'diagnostic.md'
    anchor.rel = 'noopener noreferrer'
    try {
      globalThis.document.body.appendChild(anchor)
      anchor.click()
    } catch {
      Message.error('排查文档下载失败，请重试')
    } finally { anchor.remove() }
  }

  function loadDocument(): Promise<void> {
    if (!available()) return Promise.resolve()
    const id = diagnosticTargetId(props.targetId), type = props.targetType
    if (id === null) {
      errorText.value = '缺少有效对象 ID，无法读取排查结果'
      return Promise.resolve()
    }
    if (pending?.version === version) return pending.promise
    const currentVersion = version
    const current = () => available() && version === currentVersion
    document.value = null
    errorText.value = ''
    loading.value = true
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return
        const response: unknown = type === 'scheduled_task'
          ? await getSystemTaskDiagnosticMarkdown(id, true)
          : await getSystemTestSuiteDiagnosticMarkdown(id, true)
        if (current()) document.value = parseDiagnosticDocument(response, type, id)
      } catch (error: unknown) {
        if (current() && !isMissingDiagnostic(error)) (reportLoadError(error, "排查结果加载失败，请重试", false), errorText.value = '排查结果加载失败，请重试')
      } finally {
        if (current()) loading.value = false
        if (pending?.version === currentVersion) pending = null
      }
    })
    pending = { version: currentVersion, promise }
    return promise
  }

  function visibilityChanged() {
    if (globalThis.document.visibilityState === 'visible') void loadDocument()
    else invalidate()
  }
  watch([() => props.visible, () => props.targetType, () => diagnosticTargetId(props.targetId), () => props.documentAvailable], (values, previous) => {
    if (values[0] === false || (values[0] === true && previous?.[0] !== true)) dismissed.value = false
    invalidate()
    void loadDocument()
  }, { immediate: true, flush: 'sync' })
  watch(() => [route.fullPath, userStore.userId, userStore.roleId, userStore.token, userStore.selected_environment], closeDrawer, { flush: 'sync' })
  onMounted(() => globalThis.document.addEventListener('visibilitychange', visibilityChanged))
  onDeactivated(() => { active = false; invalidate() })
  onActivated(() => { const resume = !active; active = true; if (resume) void loadDocument() })
  onBeforeUnmount(() => { disposed = true; active = false; invalidate(); globalThis.document.removeEventListener('visibilitychange', visibilityChanged) })
</script>

<style scoped lang="less">
  :deep(.mango-diagnostic-markdown-drawer .arco-drawer-body) {
    min-height: 0;
    padding: var(--m-page-gap);
    background: var(--m-bg);
  }

  .mango-diagnostic-markdown__title {
    display: flex;
    min-width: 0;
    flex-direction: column;

    strong { color: var(--m-text); font-size: 16px; line-height: 22px; }
    span { color: var(--m-muted); font-size: 11px; font-weight: 400; line-height: 16px; }
  }

  .mango-diagnostic-markdown__drawer-header {
    display: flex;
    width: 100%;
    min-width: 0;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  .mango-diagnostic-markdown__drawer-actions {
    display: flex;
    flex: none;
    align-items: center;
    gap: 8px;
  }

  .mango-diagnostic-markdown,
  .mango-diagnostic-markdown__loading { width: 100%; height: 100%; min-height: 0; }

  :deep(.mango-diagnostic-markdown__loading > .arco-spin),
  :deep(.mango-diagnostic-markdown__loading > .mango-panel-spin__content) {
    width: 100%;
    height: 100%;
  }

  .mango-diagnostic-markdown__empty {
    display: flex;
    min-height: calc(100vh - 96px);
    align-items: center;
    justify-content: center;
    flex-direction: column;
    padding: 32px;
    border: 1px dashed var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    color: var(--m-muted);
    text-align: center;

    strong {
      margin-top: 14px;
      color: var(--m-text);
      font-size: 16px;
      line-height: 24px;
    }

    p {
      max-width: 560px;
      margin: 8px 0 4px;
      color: var(--m-text-2);
      line-height: 22px;
    }

    span { font-size: 12px; line-height: 20px; }

    code {
      padding: 2px 6px;
      border-radius: 3px;
      background: var(--m-fill);
      color: var(--m-primary);
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    }
  }

  .mango-diagnostic-markdown__empty-mark {
    display: inline-flex;
    width: 46px;
    height: 46px;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-fill);
    color: var(--m-primary);
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 1px;
  }

  .mango-diagnostic-markdown__document {
    display: flex;
    height: calc(100vh - 72px);
    min-height: 0;
    flex-direction: column;
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .mango-diagnostic-markdown__reader-layout {
    display: grid;
    min-height: 0;
    flex: 1;
    grid-template-columns: 224px minmax(0, 1fr);
  }

  .mango-diagnostic-markdown__reader-layout--without-outline {
    grid-template-columns: minmax(0, 1fr);
  }

  .mango-diagnostic-markdown__reader {
    position: relative;
    min-width: 0;
    min-height: 0;
    overflow: auto;
    padding: 24px 30px 48px;
    scroll-behavior: smooth;
  }

  .mango-diagnostic-markdown__outline {
    min-width: 0;
    min-height: 0;
    overflow: auto;
    padding: 20px 12px 28px;
    border-right: 1px solid var(--m-border);
    background: var(--m-surface-soft);
  }

  .mango-diagnostic-markdown__outline-title {
    margin-bottom: 8px;
    padding: 0 8px 8px;
    border-bottom: 1px solid var(--m-border);
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
  }

  :deep(.md-editor) {
    --md-color: var(--m-text-2);
    --md-bk-color: transparent;
    --md-bk-color-outstand: var(--m-fill);
    --md-border-color: var(--m-border);
    background: transparent;
  }

  :deep(.md-editor-preview) {
    --md-theme-color: var(--m-text-2);
    --md-theme-heading-color: var(--m-text);
    --md-theme-border-color: var(--m-border);
    --md-theme-bg-color: transparent;
    --md-theme-bg-color-inset: var(--m-fill);
    --md-theme-link-color: var(--m-primary);
    --md-theme-link-hover-color: var(--m-primary-hover);
    color: var(--m-text-2);
    font-size: 14px;
    line-height: 1.75;
    word-break: break-word;
  }

  :deep(.md-editor-preview-wrapper) {
    max-width: 794px;
    margin: 0 auto;
  }

  :deep(.md-editor-preview h1),
  :deep(.md-editor-preview h2),
  :deep(.md-editor-preview h3),
  :deep(.md-editor-preview h4) {
    color: var(--m-text);
    line-height: 1.4;
  }

  :deep(.md-editor-preview h1) {
    margin: 0 0 24px;
    padding-bottom: 14px;
    border-bottom: 1px solid var(--m-border);
    font-size: 28px;
  }

  :deep(.md-editor-preview h2) {
    margin: 32px 0 14px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--m-border);
    font-size: 21px;
  }

  :deep(.md-editor-preview h3) {
    margin: 26px 0 10px;
    padding-left: 10px;
    border-left: 3px solid var(--m-primary);
    font-size: 17px;
  }

  :deep(.md-editor-preview h4) {
    margin: 24px 0 10px;
    padding: 7px 10px;
    border-left: 3px solid var(--m-primary);
    border-radius: 0 var(--m-radius-md) var(--m-radius-md) 0;
    background: var(--m-primary-soft);
    font-size: 15px;
  }
  :deep(.md-editor-preview p) { margin: 10px 0; }
  :deep(.md-editor-preview li + li) { margin-top: 4px; }
  :deep(.md-editor-preview strong) { color: var(--m-text); }

  :deep(.md-editor-preview blockquote) {
    margin: 16px 0;
    padding: 10px 16px;
    border-left-color: var(--m-primary);
    border-radius: 0 var(--m-radius-md) var(--m-radius-md) 0;
    background: var(--m-fill);
  }

  :deep(.md-editor-preview table) {
    width: 100%;
    margin: 18px 0;
  }

  :deep(.md-editor-preview th) {
    background: var(--m-fill);
    color: var(--m-text);
  }

  :deep(.md-editor-preview th),
  :deep(.md-editor-preview td) {
    padding: 9px 12px;
    border-color: var(--m-border);
  }

  :deep(.md-editor-preview tbody tr) { transition: background-color 0.15s ease; }
  :deep(.md-editor-preview tbody tr:hover) { background: var(--m-primary-soft); }

  :deep(.md-editor-preview hr) { margin: 28px 0; }
  :deep(.md-editor-preview img) { border-radius: var(--m-radius-md); }

  :deep(.md-editor-catalog-indicator) { background-color: var(--m-primary); }
  :deep(.md-editor-catalog-active > span),
  :deep(.md-editor-catalog-link span:hover) { color: var(--m-primary); }
  :deep(.md-editor-catalog-link span) { color: var(--m-text-2); font-size: 12px; }

  @media (max-width: 760px) {
    .mango-diagnostic-markdown__reader-layout { grid-template-columns: minmax(0, 1fr); }
    .mango-diagnostic-markdown__outline { display: none; }
    .mango-diagnostic-markdown__reader { padding: 20px 18px 40px; }
  }
</style>
