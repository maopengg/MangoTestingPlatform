<template>
  <TableBody plain class="mango-detail-workbench-page mango-evaluation-case-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading"
          ><div class="mango-evaluation-case-title"><div class="mango-detail-title" :title="record?.name">{{ record?.name || '测试用例详情' }}</div><a-tag v-if="record" size="small" :color="statusColor(record.status)">{{ enumTitle('evaluation_case_status', record.status) }}</a-tag><a-tag v-if="false" size="small">只读</a-tag></div
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
          <a-button

            size="small"
            :disabled="!record"
            @click="historyVisible = true"
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
          <div v-if="!record && !loading" class="mango-empty-state">Case 不存在或无权查看。</div>
          <template v-else-if="record">
              <div class="mango-evaluation-workspace">
                <section class="mango-evaluation-config-panel" aria-label="用例配置与执行结果">
                  <CaseEditor
                    ref="editor"
                    embedded
                    :case-id="caseId"
                    :initial-record="record"
                    :initial-catalog="graderCatalog"
                    :initial-step="initialStep"
                    @saved="configurationSaved"
                  >
                    <template #results><section class="mango-evaluation-results-panel" aria-label="执行结果"
                  ><ExecutionPanel
                    flat
                    :case-id="caseId"
                    :execution-id="executionId"
                    :grading-preview="gradingPreview"
                    :preview-loading="previewLoading"
                    :grader-catalog="graderCatalog"
                    @preview="preview"
                    :dataset-name="record.dataset_name"
                    :dataset-id="record.dataset_id"
                    @selected="selected"
                /></section></template>
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
      :dataset-name="record?.dataset_name"
      :dataset-id="record?.dataset_id"
      history
  /></EvaluationDrawer>
</template>
<script setup lang="ts">
  import EvaluationDrawer from '../../components/EvaluationDrawer.vue'
  import { computed, onBeforeUnmount, ref, watch } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { Message } from '@arco-design/web-vue'
  import useUserStore from '@/store/modules/user'
  import usePermissionStore from '@/store/modules/permission'
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
  const route = useRoute(),
    router = useRouter(),
    user = useUserStore(),
    permissions = usePermissionStore()
  const caseId = computed(() => Number(route.query.id)),
    editor = ref<InstanceType<typeof CaseEditor>>()
  const record = ref<any>(),
    graderCatalog = ref<any[]>([]),
    loading = ref(false),
    executing = ref(false),
    previewLoading = ref(false),
    gradingPreview = ref<any>()
  const executionId = ref<number | undefined>(Number(route.query.execution) || undefined)
  const historyVisible = ref(route.query.tab === 'history')
  const initialStep = ref('data')
  const { title: enumTitle, color: statusColor } = useEvaluationEnums()
  const saveButtonLabel = computed(() => {
    if (editor.value?.loading) return '加载中'
    if (editor.value?.saving) return '保存中'
    if (editor.value?.saveError) return editor.value.ready ? '重试保存' : '重试加载'
    return editor.value?.ready && !editor.value.dirty ? '已保存' : '保存'
  })
  async function saveConfiguration() {
    if (loading.value || executing.value || !editor.value || editor.value.saving || editor.value.loading)
    return;
    if (!editor.value.ready) {
      await editor.value.open(caseId.value)
      return
    }
    await flushConfiguration()
  }
  let generation = 0,
    previewRequest = 0
  const executionKeys = new Map<string, string>()
  async function load() {
    const request = ++generation
    loading.value = true
    try {
      const [response, catalog]: any[] = await Promise.allSettled([
        getEvaluationCase(caseId.value),
        getCaseGraderCatalog(),
      ])
      if (request !== generation) return
      if (response.status === 'rejected') throw response.reason
      record.value = response.value.data
      graderCatalog.value =
        catalog.status === 'fulfilled' && Array.isArray(catalog.value.data)
          ? catalog.value.data
          : []
    } finally {
      if (request === generation) loading.value = false
    }
  }
  async function flushConfiguration() {
    if (!editor.value) return true
    const saved = await editor.value.flush()
    if (!saved) Message.warning('配置尚未保存，请先完善配置或重试保存')
    return saved
  }
  function configurationSaved(value: any) {
    if (value && record.value?.id === value.id) {
      Object.assign(record.value, value)
      gradingPreview.value = undefined
      previewRequest += 1
    }
  }
  async function preview() {
    const id = caseId.value
    let request = previewRequest
    previewLoading.value = true
    try {
      if (!(await flushConfiguration()) || caseId.value !== id) return
      request = ++previewRequest
      const response: any = await getCaseGradingPreview(id)
      if (request === previewRequest) gradingPreview.value = response.data
    } finally {
      if (request === previewRequest || caseId.value === id) previewLoading.value = false
    }
  }
  async function execute() {
    if (!user.selected_environment) {
      Message.warning('请先选择顶部测试环境')
      return
    }
    if (executing.value) return
    const environment = user.selected_environment
    const scope = `${caseId.value}:${environment}`,
      id = caseId.value
    if (!executionKeys.has(scope)) executionKeys.set(scope, crypto.randomUUID())
    executing.value = true
    try {
      if (!(await flushConfiguration())) return
      if (caseId.value !== id || user.selected_environment !== environment) return
      const response: any = await executeEvaluationCase(
        id,
        { test_env: Number(environment) },
        executionKeys.get(scope)!
      )
      executionKeys.delete(scope)
      if (caseId.value === id && user.selected_environment === environment) {
        executionId.value = response.data.id
        editor.value?.scrollToStep?.('results')
        Message.success('已提交执行')
      }
    } finally {
      executing.value = false
    }
  }
  function selected(id: number) {
    executionId.value = id
  }
  watch([caseId, () => true], () => {
    generation += 1;
    previewRequest += 1;
    record.value = undefined;
    gradingPreview.value = undefined;
    loading.value = false;
    previewLoading.value = false;
    executionId.value = Number(route.query.execution) || undefined;
    initialStep.value = executionId.value || route.query.tab === 'results' ? 'results' : 'data';
    historyVisible.value =
        route.query.tab === 'history';
    if (caseId.value > 0)
        load();
}, { immediate: true })
  watch(
    () => user.selected_environment,
    (_environment, previous) => {
      if (!previous) return
      executionId.value = undefined
      router.replace({ query: { ...route.query, execution: undefined } })
    }
  )
  onBeforeUnmount(() => {
    generation += 1
    previewRequest += 1
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
  .mango-evaluation-case-page :deep(> .mango-table-body__header) { padding-inline: var(--m-page-gap); }
  .mango-evaluation-case-page :deep(> .mango-table-body__header > .mango-detail-toolbar) { padding: var(--m-card-padding) 0; }
  .mango-evaluation-case-page :deep(> .mango-table-body__content) {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    padding: 0 var(--m-page-gap) var(--m-page-gap);
  }
  .mango-case-details-body :deep(> .mango-panel-spin__content) { display: flex; flex-direction: column; height: 100%; min-height: 0; }
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
    .mango-evaluation-workspace { grid-template-columns: minmax(0, 1fr) 300px; }
  }
  @container (max-width: 800px) {
    .mango-evaluation-workspace { grid-template-columns: minmax(0, 1fr); grid-template-rows: minmax(0, 1fr) minmax(0, 200px); }
  }
  .mango-evaluation-config-panel,
  .mango-evaluation-results-panel {
    min-width: 0;
    container-type: inline-size;
  }
  .mango-evaluation-config-panel { flex: 1; min-height: 0; }
  .mango-evaluation-case-title {
    display: flex;
    align-items: center;
    gap: var(--m-space-sm);
    min-width: 0;
  }
  .mango-evaluation-case-title :deep(.arco-tag) { flex-shrink: 0; }
  .mango-evaluation-case-meta {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-evaluation-case-page :deep(.mango-detail-toolbar) { flex-wrap: wrap; }
  .mango-evaluation-case-page :deep(.mango-detail-heading) { flex: 1; }
  .mango-evaluation-case-page :deep(.mango-detail-actions) { margin-left: auto; }
</style>
