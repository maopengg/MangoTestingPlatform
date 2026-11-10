<template>
  <TableBody plain class="mango-detail-workbench-page mango-evaluation-case-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading"
          ><div class="mango-evaluation-case-title"
            ><div class="mango-detail-title" :title="record?.name">{{
              record?.name || '测试用例详情'
            }}</div
            ><a-tag v-if="record" size="small" :color="statusColor(record.status)">{{
              enumTitle('evaluation_case_status', record.status)
            }}</a-tag></div
          ><div class="mango-detail-subtitle mango-evaluation-case-meta"
            >Case #{{ caseId
            }}<template v-if="record?.dataset_name">
              · {{ record.dataset_name
              }}<template v-if="record.dataset_version_no">
                · V{{ record.dataset_version_no }}</template
              ></template
            ><template v-else> · 尚未配置评测数据</template></div
          ></div
        >
        <a-space class="mango-detail-actions" wrap>
          <a-button
            size="small"
            type="primary"
            :loading="Boolean(editor?.saving || editor?.loading)"
            :disabled="loading || executing || !editor"
            :status="editor?.saveError ? 'danger' : undefined"
            :title="editor?.saveError || editor?.saveStatus"
            aria-live="polite"
            @click="saveConfiguration"
            >{{ saveButtonLabel }}</a-button
          >
          <a-button size="small" :disabled="!record" @click="historyVisible = true"
            >历史结果</a-button
          >
          <a-button
            size="small"
            status="success"
            :disabled="record?.status !== 'enabled'"
            :loading="executing"
            @click="execute"
            >执行用例</a-button
          >
          <a-button
            class="mango-back-button"
            size="small"
            @click="router.push('/evaluation/case/index')"
            >返回</a-button
          >
        </a-space>
      </div>
    </template>
    <template #default>
      <div class="mango-case-details mango-detail-workbench">
        <MangoPanelSpin :loading="loading" class="mango-case-details-body">
          <div v-if="!record && !loading" class="mango-empty-state">
            {{ loadError ? '' : 'Case 不存在或无权查看。' }}
            <a-button v-if="loadError" size="small" :loading="loading" @click="load">重试</a-button>
          </div>
          <template v-else-if="record">
            <div class="mango-evaluation-workspace">
              <section class="mango-evaluation-config-panel" aria-label="用例配置与执行结果">
                <CaseEditor
                  ref="editor"
                  embedded
                  :case-id="caseId"
                  :initial-record="record"
                  :initial-catalog="graderCatalog"
                  :catalog-loading="catalogLoading"
                  :catalog-error="catalogError"
                  :initial-step="initialStep"
                  @saved="configurationSaved"
                  @retry-catalog="loadCatalog"
                >
                  <template #results
                    ><section class="mango-evaluation-results-panel" aria-label="执行结果"
                      ><ExecutionPanel
                        flat
                        :case-id="caseId"
                        :execution-id="executionId"
                        :grading-preview="gradingPreview"
                        :preview-loading="previewLoading"
                        :grader-catalog="graderCatalog"
                        @preview="preview"
                        :dataset-name="record.dataset_name ?? undefined"
                        :dataset-id="record.dataset_id ?? undefined"
                        @selected="selected" /></section
                  ></template>
                </CaseEditor>
              </section>
              <CaseInfoPanel :record="record" />
            </div>
          </template>
        </MangoPanelSpin>
      </div>
    </template>
  </TableBody>
  <EvaluationDrawer
    v-model:visible="historyVisible"
    contained
    title="历史执行结果"
    :width="1300"
    :footer="false"
    unmount-on-close
    ><ExecutionPanel
      v-if="historyVisible"
      :case-id="caseId"
      :dataset-name="record?.dataset_name ?? undefined"
      :dataset-id="record?.dataset_id ?? undefined"
      history
  /></EvaluationDrawer>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import EvaluationDrawer from '../../components/EvaluationDrawer.vue'
  import { computed, onActivated, onDeactivated, onBeforeUnmount, ref, watch } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { Message } from '@arco-design/web-vue'
  import useUserStore from '@/store/modules/user'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import { useEvaluationEnums } from '../../components/useEvaluationEnums'
  import {
    getEvaluationCase,
    executeEvaluationCase,
    getCaseGradingPreview,
    getCaseGraderCatalog,
  } from '@/api/evaluation'
  import CaseEditor from '../../components/CaseEditor.vue'
  import ExecutionPanel from '../../components/ExecutionPanel.vue'
  import CaseInfoPanel from '../../components/CaseInfoPanel.vue'
  import type {
    EvaluationCaseRecord,
    GraderCatalogEntry,
    GradingPreview,
    CaseEditorHandle,
  } from '../../types'
  const route = useRoute(),
    router = useRouter(),
    user = useUserStore(),
    pagePath = route.path
  const caseId = computed(() => Number(route.query.id)),
    editor = ref<CaseEditorHandle | null>(null)
  const record = ref<EvaluationCaseRecord | null>(null),
    graderCatalog = ref<GraderCatalogEntry[]>([])
  const loading = ref(false),
    loadError = ref(false),
    catalogLoading = ref(false),
    catalogError = ref(false),
    executing = ref(false),
    previewLoading = ref(false)
  const gradingPreview = ref<GradingPreview>()
  const executionId = ref<number>(),
    historyVisible = ref(false),
    initialStep = ref('data')
  const { title: enumTitle, color: statusColor } = useEvaluationEnums()
  const saveButtonLabel = computed(() => {
    if (editor.value?.loading) return '加载中'
    if (editor.value?.saving) return '保存中'
    if (editor.value?.saveError) return editor.value.ready ? '重试保存' : '重试加载'
    return editor.value?.ready && !editor.value.dirty ? '已保存' : '保存'
  })
  let active = true,
    generation = 0,
    catalogRequest = 0,
    previewRequest = 0,
    environmentVersion = 0,
    previewPending = false
  const executionKeys = new Map<string, string>()
  const isActive = () => active && route.path === pagePath
  const current = (version: number) => isActive() && generation === version
  async function saveConfiguration() {
    if (
      !isActive() ||
      loading.value ||
      executing.value ||
      !editor.value ||
      editor.value.saving ||
      editor.value.loading
    )
      return false
    if (!editor.value.ready) {
      await editor.value.open(caseId.value)
      return false
    }
    return flushConfiguration()
  }
  async function load() {
    if (!isActive() || !Number.isSafeInteger(caseId.value) || caseId.value <= 0) return
    const version = ++generation,
      id = caseId.value
    loading.value = true
    loadError.value = false
    void loadCatalog()
    try {
      const response = await getEvaluationCase(id)
      if (!current(version)) return
      record.value = response.data || null
      return true
    } catch (loadFailure0) {
      if (current(version)) (reportLoadError(loadFailure0, "加载失败，请重试", false), loadError.value = true)
      return false
    } finally {
      if (version === generation) loading.value = false
    }
  }
  async function loadCatalog() {
    if (!isActive()) return false
    const version = generation,
      request = ++catalogRequest
    catalogLoading.value = true
    catalogError.value = false
    try {
      const response = await getCaseGraderCatalog()
      if (!current(version) || request !== catalogRequest) return false
      graderCatalog.value = Array.isArray(response.data) ? response.data : []
      return true
    } catch (loadFailure1) {
      if (current(version) && request === catalogRequest) (reportLoadError(loadFailure1, "加载失败，请重试", false), catalogError.value = true)
      return false
    } finally {
      if (request === catalogRequest) catalogLoading.value = false
    }
  }
  async function flushConfiguration() {
    if (!isActive() || !editor.value) return false
    const version = generation,
      saved = await editor.value.flush()
    if (!current(version)) return false
    if (!saved) Message.warning('配置尚未保存，请先完善配置或重试保存')
    return saved
  }
  function configurationSaved(value?: Partial<EvaluationCaseRecord>) {
    if (!isActive() || !value || !record.value || record.value.id !== value.id) return
    const previous = record.value
    record.value = {
      ...previous,
      config: value.config ?? previous.config,
      dataset_version: value.dataset_version,
      dataset_id: value.dataset_id,
      dataset_name: value.dataset_name,
      dataset_version_no: value.dataset_version_no,
    }
    gradingPreview.value = undefined
    ++previewRequest
    if (!previewPending) previewLoading.value = false
  }
  async function preview() {
    if (!isActive() || previewPending || loading.value) return false
    const version = generation,
      environment = environmentVersion,
      id = caseId.value
    previewPending = true
    previewLoading.value = true
    try {
      if (!(await flushConfiguration()) || !current(version) || environment !== environmentVersion)
        return false
      const ownRequest = ++previewRequest
      const response = await getCaseGradingPreview(id)
      if (current(version) && environment === environmentVersion && ownRequest === previewRequest)
        gradingPreview.value = response.data
      return current(version) && environment === environmentVersion && ownRequest === previewRequest
    } catch {
      return false
    } finally {
      previewPending = false
      previewLoading.value = false
    }
  }
  async function execute() {
    if (!isActive() || executing.value || loading.value || record.value?.status !== 'enabled')
      return false
    if (!user.selected_environment) {
      Message.warning('请先选择顶部测试环境')
      return false
    }
    const environment = user.selected_environment,
      version = generation,
      environmentEpoch = environmentVersion,
      id = caseId.value
    const scope = `${user.userId}:${user.roleId}:${id}:${environment}`
    if (!executionKeys.has(scope)) executionKeys.set(scope, crypto.randomUUID())
    const key = executionKeys.get(scope)!
    executing.value = true
    try {
      if (
        !(await flushConfiguration()) ||
        !current(version) ||
        environmentEpoch !== environmentVersion
      )
        return false
      const response = await executeEvaluationCase(id, { test_env: Number(environment) }, key)
      if (executionKeys.get(scope) === key) executionKeys.delete(scope)
      if (!current(version) || environmentEpoch !== environmentVersion) return false
      executionId.value = response.data.id
      editor.value?.scrollToStep('results')
      Message.success('已提交执行')
      return true
    } catch {
      return false
    } finally {
      executing.value = false
    }
  }
  function selected(id: number) {
    if (isActive()) executionId.value = id
  }
  function invalidate() {
    ++generation
    ++catalogRequest
    ++previewRequest
    loading.value = false
    catalogLoading.value = false
    catalogError.value = false
    previewLoading.value = false
    record.value = null
    graderCatalog.value = []
    gradingPreview.value = undefined
    historyVisible.value = false
    executionId.value = undefined
  }
  function reload() {
    invalidate()
    if (!isActive()) return
    executionId.value = Number(route.query.execution) || undefined
    initialStep.value = executionId.value || route.query.tab === 'results' ? 'results' : 'data'
    historyVisible.value = route.query.tab === 'history'
    void load()
  }
  watch(() => [caseId.value, route.path, user.userId, user.roleId, user.token], reload, {
    immediate: true,
    flush: 'sync',
  })
  watch(
    () => user.selected_environment,
    (_environment, previous) => {
      ++environmentVersion
      ++previewRequest
      previewLoading.value = false
      gradingPreview.value = undefined
      if (!previous) return
      executionId.value = undefined
      historyVisible.value = false
      if (isActive() && route.query.execution)
        void router.replace({ query: { ...route.query, execution: undefined } })
    },
    { flush: 'sync' }
  )
  onDeactivated(() => {
    active = false
    invalidate()
  })
  onActivated(() => {
    if (!active) {
      active = true
      reload()
    }
  })
  onBeforeUnmount(() => {
    active = false
    invalidate()
  })
</script>
<style scoped>
  .mango-case-details {
    min-width: 0;
    min-height: 0;
    flex: 1;
    display: flex;
    flex-direction: column;
    container-type: inline-size;
  }
  .mango-case-details-body {
    width: 100%;
    flex: 1;
    min-height: 0;
  }
  .mango-evaluation-case-page :deep(> .mango-table-body__header) {
    padding-inline: var(--m-page-gap);
  }
  .mango-evaluation-case-page :deep(> .mango-table-body__header > .mango-detail-toolbar) {
    padding: var(--m-card-padding) 0;
  }
  .mango-evaluation-case-page :deep(> .mango-table-body__content) {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    padding: 0 var(--m-page-gap) var(--m-page-gap);
  }
  .mango-case-details-body :deep(> .mango-panel-spin__content) {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
  }
  .mango-evaluation-workspace {
    min-width: 0;
    flex: 1;
    display: grid;
    grid-template-columns: minmax(0, 1fr) 360px;
    grid-template-rows: minmax(0, 1fr);
    gap: var(--m-page-gap);
    min-height: 0;
  }
  @container (max-width: 1200px) {
    .mango-evaluation-workspace {
      grid-template-columns: minmax(0, 1fr) 300px;
    }
  }
  @container (max-width: 800px) {
    .mango-evaluation-workspace {
      grid-template-columns: minmax(0, 1fr);
      grid-template-rows: minmax(0, 1fr) minmax(0, 200px);
    }
  }
  .mango-evaluation-config-panel,
  .mango-evaluation-results-panel {
    min-width: 0;
    container-type: inline-size;
  }
  .mango-evaluation-config-panel {
    flex: 1;
    min-height: 0;
  }
  .mango-evaluation-case-title {
    display: flex;
    align-items: center;
    gap: var(--m-space-sm);
    min-width: 0;
  }
  .mango-evaluation-case-title :deep(.arco-tag) {
    flex-shrink: 0;
  }
  .mango-evaluation-case-meta {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-evaluation-case-page :deep(.mango-detail-toolbar) {
    flex-wrap: wrap;
  }
  .mango-evaluation-case-page :deep(.mango-detail-heading) {
    flex: 1;
  }
  .mango-evaluation-case-page :deep(.mango-detail-actions) {
    margin-left: auto;
  }
</style>
