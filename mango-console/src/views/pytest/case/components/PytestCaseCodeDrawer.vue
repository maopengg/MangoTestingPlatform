<template>
  <BaseSidePanel :visible="visible" title="编辑代码" :width="1000" @update:visible="onVisibleChange" @cancel="close">
    <div class="mango-pytest-source-editor">
      <a-tabs :active-key="fileType" @change="changeFile">
        <a-tab-pane key="py" title="Python 文件" data-testid="qa-views-pytest-case-tab-pane-python-文件" />
        <a-tab-pane v-if="hasFeature" key="feature" title="Feature 文件" data-testid="qa-views-pytest-case-tab-pane-feature-文件" />
      </a-tabs>


      <mango-panel-spin :loading="activeFile.loading" class="mango-pytest-source-editor__spin">
        <template v-if="activeFile.failed"></template>
        <CodeEditor v-else-if="activeFile.snapshot" :key="fileType" v-model="activeFile.draft" :readonly="saving || confirmationOpen" :line-actions="fileType === 'py' ? lineActions : []" :placeholder="fileType === 'py' ? '输入python代码' : '输入 Gherkin 语法'" @line-action="runMethod" />
      </mango-panel-spin>
    </div>
    <template #footer-buttons>
      <a-button @click="close">取消</a-button>
      <a-button type="primary" :loading="saving" :disabled="!canSave" data-testid="qa-views-pytest-case-button-保存" @click="requestSave">保存</a-button>
    </template>
  </BaseSidePanel>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, h, onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import { getPytestCaseRead, getPytestCaseMethodNodes, getPytestCaseTest, postPytestCaseWrite } from '@/api/pytest/case'
  import useUserStore from '@/store/modules/user'
  import { batchSuccess } from '../batch-editor'
  import { codeTarget, executionEnvironment, methodNodes, methodTarget, sourceSnapshot, unboundFeature } from '../source'
  import type { CodeTarget, PytestFileType, PytestMethodNode, SourceSnapshot } from '../source'

  interface FileDraft { snapshot: SourceSnapshot | null; draft: string; loading: boolean; failed: boolean }
  const props = withDefaults(defineProps<{ contextKey?: string }>(), { contextKey: '' })
  const emit = defineEmits<{ (event: 'saved', caseId: number): void; (event: 'started', caseId: number): void }>()
  const user = useUserStore(), route = useRoute()
  const visible = ref(false), target = ref<CodeTarget | null>(null), fileType = ref<PytestFileType>('py'), saving = ref(false)
  const emptyFile = (): FileDraft => ({ snapshot: null, draft: '', loading: false, failed: false })
  const files = reactive({ py: emptyFile(), feature: emptyFile() }), featureAbsent = ref(false)
  const nodes = ref<PytestMethodNode[]>([]), methodsLoading = ref(false), methodsFailed = ref(false), running = ref(new Set<string>())
  const confirmationOpen = ref(false)
  let version = 0, methodsVersion = 0, confirmationVersion = 0, active = true, disposed = false
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const reads: Partial<Record<PytestFileType, { current: () => boolean; promise: Promise<boolean> }>> = {}
  let methodsRead: { current: () => boolean; promise: Promise<boolean> } | null = null
  const available = () => !disposed && active && (typeof document === 'undefined' || !document.hidden)
  const current = (window: number) => available() && visible.value && window === version
  const hasFeature = computed(() => !featureAbsent.value && Boolean(target.value?.featurePath || files.feature.snapshot))
  const activeFile = computed(() => files[fileType.value])
  const canSave = computed(() => current(version) && !!activeFile.value.snapshot && !activeFile.value.loading && !activeFile.value.failed && !saving.value && !confirmationOpen.value)
  const runKey = (caseId: number, environment: number, nodeid: string) => JSON.stringify([caseId, environment, nodeid])
  const lineActions = computed(() => nodes.value.filter(node => node.line_number !== null).map(node => ({
    id: node.nodeid, line: node.line_number!, label: `执行 ${node.class_name ? node.class_name + '.' : ''}${node.method_name}`,
    loading: !!target.value && running.value.has(runKey(target.value.id, Number(user.selected_environment), node.nodeid)),
    disabled: !target.value?.executable || saving.value || confirmationOpen.value || activeFile.value.loading || activeFile.value.failed,
    payload: node,
  })))
  function closeConfirmation(): void { confirmationVersion++; confirmation?.close(); confirmation = null; confirmationOpen.value = false }
  function close(): void {
    version++; methodsVersion++; closeConfirmation(); visible.value = false; target.value = null
    Object.assign(files.py, emptyFile()); Object.assign(files.feature, emptyFile()); featureAbsent.value = false; fileType.value = 'py'
    delete reads.py; delete reads.feature; methodsRead = null; nodes.value = []; methodsLoading.value = false; methodsFailed.value = false
  }
  function onVisibleChange(value: boolean): void { if (!value) close() }
  function open(value: unknown): void {
    if (!available() || saving.value) return
    let next: CodeTarget
    try { next = codeTarget(value) } catch { Message.error('用例信息不完整，请重新加载'); return }
    close(); target.value = next; visible.value = true
    void readFile('py'); void readFile('feature'); void loadMethods()
  }
  function readFile(type: PytestFileType): Promise<boolean> {
    if (!current(version) || !target.value || saving.value || confirmationOpen.value) return Promise.resolve(false)
    if (reads[type]?.current()) return reads[type]!.promise
    if (files[type].snapshot) return Promise.resolve(true)
    const window = version, caseId = target.value.id, file = files[type]
    const isCurrent = () => current(window) && reads[type] === job
    const job = { current: isCurrent, promise: Promise.resolve(false) }
    reads[type] = job; file.loading = true; file.failed = false
    job.promise = Promise.resolve().then(async () => {
      try {
        if (!isCurrent()) return false
        const snapshot = sourceSnapshot(await getPytestCaseRead(caseId, type, type === 'feature'))
        if (!isCurrent()) return false
        file.snapshot = snapshot; file.draft = snapshot.content
        if (type === 'feature') featureAbsent.value = false
        return true
      } catch (error) {
        if (isCurrent()) {
          if (type === 'feature' && unboundFeature(error)) { featureAbsent.value = true; if (fileType.value === 'feature') fileType.value = 'py' }
          else (reportLoadError(error, "加载失败，请重试", false), file.failed = true)
        }
        return false
      } finally { if (isCurrent()) { file.loading = false; delete reads[type] } }
    })
    return job.promise
  }
  function loadMethods(): Promise<boolean> {
    if (!current(version) || !target.value || saving.value || confirmationOpen.value) return Promise.resolve(false)
    if (methodsRead?.current()) return methodsRead.promise
    const window = version, request = ++methodsVersion, caseId = target.value.id
    const isCurrent = () => current(window) && request === methodsVersion
    const job = { current: isCurrent, promise: Promise.resolve(false) }
    methodsRead = job; methodsLoading.value = true; methodsFailed.value = false
    job.promise = Promise.resolve().then(async () => {
      try {
        if (!isCurrent()) return false
        const next = methodNodes(await getPytestCaseMethodNodes(caseId))
        if (!isCurrent()) return false
        nodes.value = next; return true
      } catch (loadFailure0) { if (isCurrent()) { nodes.value = []; (reportLoadError(loadFailure0, "加载失败，请重试", false), methodsFailed.value = true) }; return false }
      finally { if (methodsRead === job) { methodsRead = null; methodsLoading.value = false } }
    })
    return job.promise
  }
  function changeFile(value: unknown): void {
    if (!current(version) || saving.value || confirmationOpen.value || (value !== 'py' && value !== 'feature') || (value === 'feature' && !hasFeature.value)) return
    fileType.value = value; void readFile(value)
  }
  function requestSave(): void {
    if (!canSave.value || !target.value || !activeFile.value.snapshot) return
    const window = version, serial = ++confirmationVersion, caseId = target.value.id, type = fileType.value
    const snapshot = { ...activeFile.value.snapshot }, content = activeFile.value.draft
    const other: PytestFileType = type === 'py' ? 'feature' : 'py'
    const otherDirty = files[other].snapshot && files[other].draft !== files[other].snapshot?.content
    confirmationOpen.value = true
    confirmation = Modal.confirm({
      title: '确认保存平台代码', cancelText: '继续编辑', okText: '仍要保存',
      content: () => h('div', [h('div', '请确认已了解以下事项：'), h('ol', [
        h('li', '平台保存只会修改本地仓库工作区；你还需要自行提交并推送到 Git 远端，代码才会作为仓库版本正式生效。'),
        h('li', '建议优先在本地 IDE 或代码仓库中修改并正常提交，不建议长期通过测试平台直接编辑源码。'),
        ...(otherDirty ? [h('li', '本次只保存当前文件，另一个文件未保存的修改不会提交。')] : []),
      ])]),
      onCancel: () => { if (serial === confirmationVersion) closeConfirmation() },
      onClose: () => { if (serial === confirmationVersion) { confirmationOpen.value = false; confirmation = null } },
      onBeforeOk: async () => {
        if (!current(window) || serial !== confirmationVersion || saving.value) return false
        saving.value = true
        try {
          const next = sourceSnapshot(await postPytestCaseWrite(caseId, content, type, snapshot.commitHash ?? undefined, snapshot.contentHash))
          if (!current(window) || serial !== confirmationVersion) return false
          if (next.path !== snapshot.path) throw new Error('保存响应文件不一致')
          close(); Message.success('保存成功；请提交并推送到 Git 远端'); emit('saved', caseId)
          return true
        } catch { if (current(window) && serial === confirmationVersion) Message.error('保存失败，请检查文件版本后重试'); return false }
        finally { saving.value = false }
      },
    })
  }
  async function runMethod(value: unknown): Promise<boolean> {
    if (!current(version) || fileType.value !== 'py' || !target.value || saving.value || confirmationOpen.value || !files.py.snapshot || files.py.failed || methodsLoading.value || methodsFailed.value) return false
    const nodeid = value != null && typeof value === 'object' && 'nodeid' in value ? value.nodeid : null
    const node = nodes.value.find(node => node.nodeid === nodeid)
    if (!node) return false
    if (!target.value.executable) { Message.warning('当前测试文件源码不可用，或资产已停用、归档、忽略，不能执行'); return false }
    let environment: number
    try { environment = executionEnvironment(user.selected_environment) } catch { Message.error('请先选择用例执行的环境'); return false }
    const window = version, caseId = target.value.id, key = runKey(caseId, environment, node.nodeid), payload = methodTarget(node)
    if (running.value.has(key)) return false
    running.value = new Set([...running.value, key])
    try {
      batchSuccess(await getPytestCaseTest(caseId, environment, payload))
      if (!current(window)) return false
      Message.success('准备开始执行，执行完成之后，请在右侧按钮结果中查看执行结果~'); emit('started', caseId)
      return true
    } catch { if (current(window)) Message.error('执行失败，请重试'); return false }
    finally { const next = new Set(running.value); next.delete(key); running.value = next }
  }
  watch(() => [user.userId, user.roleId, user.token, user.selected_environment, route.fullPath, props.contextKey], close, { flush: 'sync' })
  function visibilityChanged(): void { if (typeof document !== 'undefined' && document.hidden) close() }
  onMounted(() => { if (typeof document !== 'undefined') document.addEventListener('visibilitychange', visibilityChanged) })
  onActivated(() => { active = true })
  onDeactivated(() => { active = false; close() })
  onBeforeUnmount(() => { disposed = true; close(); if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', visibilityChanged) })
  defineExpose({ open, close })
</script>

<style scoped lang="less">
  .mango-pytest-source-editor {
    min-width: 0;
    &__status { display: flex; align-items: center; gap: var(--m-page-gap); }
    &__spin {
      width: 100%;
      :deep(> .mango-panel-spin__content) { min-width: 0; width: 100%; }
    }
  }
</style>
