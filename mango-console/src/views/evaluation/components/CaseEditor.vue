<template>
  <component
    :is="embedded ? 'section' : ModalDialog"
    ref="dialog"
    v-bind="embedded ? {} : { title: form.id ? '编辑测试用例' : '新建测试用例', width: '560px' }"
    class="mango-case-editor"
    :class="{ 'mango-case-editor--embedded': embedded }"
    @confirm="save"
    @cancel="cancel"
  >
    <template #[contentSlot]>
      <MangoPanelSpin :loading="loading" class="mango-case-editor-spin">
        <component
          v-if="ready"
          :is="embedded ? 'div' : 'a-form'"
          class="mango-case-editor-form"
          v-bind="embedded ? {} : { model: form, disabled: !canEdit, layout: 'horizontal', autoLabelWidth: true }"
        >
          <MangoStepCards ref="stepCards" v-if="embedded" :steps="visibleConfigSteps" label="用例配置步骤" layout="workspace" :initial-step="initialStep">
            <template #data>
              <a-form class="mango-case-config-form" :model="form" :disabled="!canEdit" layout="horizontal">
              <div class="mango-case-field-grid">
                <div
                  ><a-form-item label="数据集" required
                    ><a-select
                      v-model="form.dataset_id"
                      :options="datasetOptions"
                      :loading="datasetsLoading"
                      allow-search
                      :filter-option="false"
                      @search="loadDatasets"
                      @change="datasetChanged" /></a-form-item
                ></div>
                <div
                  ><a-form-item label="发布版本" required
                    ><a-select
                      v-model="form.dataset_version"
                      :options="versionOptions"
                      :loading="versionsLoading" @change="versionChanged" /></a-form-item
                ></div>
                <div class="mango-case-field-grid__wide"
                  ><a-form-item label="条目选择"
                    ><a-space wrap>
                      <span>{{ selectionSummary }}</span>
                      <a-button v-permission="canEdit ? 'evaluation.case:edit' : 'evaluation.case:detail'" size="small" :disabled="!form.dataset_version" @click="itemSelection?.open()">{{ canEdit ? '配置条目' : '查看条目' }}</a-button>
                    </a-space></a-form-item
                ></div>
              </div>
              <a-form-item label="输入变量">
                <div class="mango-evaluation-input-binding">
                  <div v-for="variable in datasetInputVariables" :key="variable.name"><code>{{ inputReference(variable.name) }}</code><span class="mango-muted-text"> ← {{ variable.path === '$' ? '完整输入' : variable.path }}</span></div>
                </div>
              </a-form-item>
              </a-form>
            </template>
            <template #target>
              <a-form class="mango-case-config-form" :model="form" :disabled="!canEdit" layout="horizontal">
              <div class="mango-case-field-grid">
                <div
                  ><a-form-item label="目标类型" required
                    ><a-select
                      v-model="config.target.type"
                      :options="targetTypeOptions"
                      @change="targetChanged" /></a-form-item
                ></div>
                <div v-if="config.target.type === 'api_info'">
                  <a-form-item label="接口模块" required>
                    <ProductModuleSelect v-model="targetModule" :project-product-id="leafId(form.project_product)"
                      :selectable-level="0" check-strictly @change="targetModuleChanged" />
                  </a-form-item>
                </div>
                <div v-if="config.target.type === 'api_info'" :span="2">
                  <a-form-item label="被测接口" required>
                    <a-select v-model="config.target.ref_id" :options="interfaceOptions" :loading="interfacesLoading"
                      :disabled="!targetModule" allow-search :filter-option="false" placeholder="选择已发布的 HTTP / SSE 接口"
                      @search="searchInterfaces" @change="interfaceChanged" @dropdown-reach-bottom="loadMoreInterfaces"
                      @popup-visible-change="visible => visible && loadInterfaces()" />
                  </a-form-item>
                  <a-alert v-if="interfacesError" type="error">{{ interfacesError }}
                    <a-button size="small" :loading="interfacesLoading" @click="loadInterfaces()">重试加载</a-button>
                  </a-alert>
                </div>
              </div>
              <a-form-item v-if="config.target.type === 'script'" class="mango-case-code-field" label="Python 脚本" required>
                <div class="mango-case-python-editor">
                  <CodeEditor v-model="config.target.parameters.code" language="python" :readonly="!canEdit"
                    placeholder="定义 main(input, context)，返回 JSON 对象" />
                </div>
              </a-form-item>
              <p v-if="config.target.type === 'script'" class="mango-answering-hint">
                使用 {{ inputVariableReference }} 获取条目完整输入，返回 JSON 对象；不提供标准答案。
              </p>

              <ExtractionEditor v-model="config.mapping.output" :disabled="!canEdit" @validity-change="extractionErrors.output = $event" />
              </a-form>
            </template>
            <template #answering-actions>
              <a-button size="small" :disabled="!config.answering" @click="advancedSection = 'answering'">字段设置</a-button>
            </template>
            <template #answering>
              <a-form class="mango-case-config-form" :model="form" :disabled="!canEdit" layout="horizontal">
              <a-form-item label="回答 AI">
                <a-select v-model="answerProfile" :options="answerAiOptions" :loading="aiLoading" :disabled="!canEdit" allow-clear placeholder="留空则不生成回答" />
              </a-form-item>
              <p class="mango-answering-hint">留空则跳过本步骤；选择回答 AI 后，根据问题和召回内容生成回答，不向回答模型提供标准答案。</p>
              </a-form>
            </template>
            <template #grading-actions>
              <a-button size="small" @click="advancedSection = 'grading'"
                >强制评分与质量门禁</a-button
              >
            </template>
            <template #grading>
              <a-form class="mango-case-config-form" :model="form" :disabled="!canEdit" layout="horizontal">
              <div class="mango-case-ai-fields">
                <a-form-item label="评分 AI">
                  <a-select v-model="config.ai.judge_profile_id" :options="aiOptions" :loading="aiLoading" :disabled="!canEdit" allow-clear placeholder="AI 评分时选择" />
                </a-form-item>
                <a-form-item label="总结 AI">
                  <a-select v-model="config.ai.summary_profile_id" :options="aiOptions" :loading="aiLoading" :disabled="!canEdit" allow-clear placeholder="总结本次结果（可选）" />
                </a-form-item>
              </div>
              <a-alert v-if="aiError" type="warning">{{ aiError }}</a-alert>
              <GraderEditor
                v-model="config.grading.default_graders"
                :catalog="catalog"
                :disabled="!canEdit"
                title="默认评分项"
              />
              </a-form>
            </template>
            <template #policy>
              <a-form class="mango-case-config-form" :model="form" :disabled="!canEdit" layout="horizontal">
              <div class="mango-case-field-grid">
                <div
                  ><a-form-item label="最低有效率"
                    ><a-input-number
                      :model-value="config.grading.aggregation.min_valid_rate == null ? undefined : config.grading.aggregation.min_valid_rate * 100"
                      :min="0.01" :max="100" :precision="2"
                      @change="config.grading.aggregation.min_valid_rate = $event == null ? null : $event / 100"
                    ><template #suffix>%</template></a-input-number></a-form-item
                ></div>
                <div
                  ><a-form-item label="最低通过率"
                    ><a-input-number
                      :model-value="config.grading.aggregation.min_effect_pass_rate == null ? undefined : config.grading.aggregation.min_effect_pass_rate * 100"
                      :min="0" :max="100" :precision="2"
                      @change="config.grading.aggregation.min_effect_pass_rate = $event == null ? null : $event / 100"
                    ><template #suffix>%</template></a-input-number></a-form-item
                ></div>
                <div
                  ><a-form-item label="作答超时（秒）"
                    ><a-input-number
                      v-model="config.execution.item_timeout_seconds"
                      :min="1"
                      :max="3600"
                      :precision="0" /></a-form-item
                ></div>
                <div
                  ><a-form-item label="调用异常重试"
                    ><a-input-number
                      v-model="config.execution.retry_count"
                      :min="0"
                      :max="3"
                      :precision="0" /></a-form-item
                ></div>
                <div><a-form-item label="高级设置"><a-button size="small" @click="advancedSection = 'execution'">重复执行与提前停止</a-button></a-form-item></div>
              </div>
              </a-form>
            </template>
            <template #results><slot name="results" /></template>
          </MangoStepCards>
          <template v-else>
            <a-form-item label="用例名称" required
              ><a-input v-model="form.name" :max-length="128"
            /></a-form-item>
            <a-form-item label="项目产品" required
              ><ProjectProductSelect
                v-model="form.project_product"
                :disabled="Boolean(form.id)"
                @change="productChanged"
            /></a-form-item>
            <a-form-item label="模块"
              ><ProductModuleSelect
                v-model="form.module"
                :project-product-id="leafId(form.project_product)"
            /></a-form-item>
            <a-form-item label="场景描述"
              ><a-textarea v-model="form.description" placeholder="Given 前置条件或测试数据&#10;When 调用接口或脚本&#10;Then 预期行为与验证目标" :auto-size="{ minRows: 3, maxRows: 6 }"
            /></a-form-item>
          </template>
        </component>
      </MangoPanelSpin>
    </template>
  </component>
  <ItemSelectionDrawer ref="itemSelection" :version-id="form.dataset_version" :model-value="config.data_selection" :disabled="!canEdit" :save-selection="saveItemSelection" />
  <EvaluationDrawer
    v-model:visible="advancedVisible"
    :title="advancedTitle"
    :width="advancedSection === 'grading' ? 900 : 560"
    :footer="false"
    unmount-on-close
  >
    <a-form v-if="advancedSection === 'answering' && config.answering" :model="config.answering" :disabled="!canEdit" layout="horizontal" auto-label-width>
      <a-form-item label="问题字段"><a-input v-model="config.answering.question_path" /></a-form-item>
      <a-form-item label="回答 Token 上限"><a-input-number v-model="config.answering.max_tokens" :min="100" :max="8000" /></a-form-item>
    </a-form>
    <a-form v-else-if="advancedSection === 'execution'" :model="config.execution" :disabled="!canEdit" layout="horizontal" auto-label-width>
      <a-form-item label="重复执行次数"><a-input-number v-model="config.execution.repeat_count" :min="1" :max="10" :precision="0" /></a-form-item>
      <a-form-item label="硬门禁失败停止"><a-switch v-model="config.execution.stop_on_critical_failure" size="small" /></a-form-item>
      <a-form-item label="完整配置"><a-button size="small" @click="jsonSection = 'all'">编辑完整 JSON</a-button></a-form-item>
      <p class="mango-answering-hint">重复结果分别计入统计，并展示均值和波动。回答不正确不会自动重试；评分 AI 超时使用所选 AI 的配置。</p>
    </a-form>
    <div v-else-if="advancedSection === 'grading'" class="mango-case-advanced-grading">
      <GraderEditor
        v-model="config.grading.required_graders"
        :catalog="catalog"
        :disabled="!canEdit"
        title="强制评分项"
        empty-text="未配置强制评分项，条目可继承或替换默认评分"
      />
      <QualityGateEditor v-model="config.grading.quality_gates" :graders="[...config.grading.default_graders, ...config.grading.required_graders]" :catalog="catalog" :disabled="!canEdit" />
    </div>
  </EvaluationDrawer>
  <MangoJsonEditDrawer
    :visible="Boolean(jsonSection)"
    :model-value="jsonValue"
    title="Case 完整配置"
    @update:visible="
      (value) => {
        if (!value) jsonSection = ''
      }
    "
    @save="saveJson"
  />
</template>
<script setup lang="ts">
  import EvaluationDrawer from './EvaluationDrawer.vue'
  import { computed, onBeforeUnmount, reactive, ref, useSlots, watch } from 'vue'
  import { onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router'
  import { Message } from '@arco-design/web-vue'
  import {
    getEvaluationCase,
    getEvaluationAiProfiles,
    getEvaluationInterfaces,
    createEvaluationCase,
    updateEvaluationCase,
    getEvaluationDatasets,
    getDatasetVersions,
    getCaseGraderCatalog,
  } from '@/api/evaluation'
  import ModalDialog from '@/components/overlays/ModalDialog.vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import MangoStepCards from '@/components/forms/MangoStepCards.vue'
  import MangoJsonEditDrawer from '@/components/editors/MangoJsonEditDrawer.vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import usePermissionStore from '@/store/modules/permission'
  import type { ModalDialogType } from '@/types/components'
  import GraderEditor from './GraderEditor.vue'
  import ExtractionEditor from './ExtractionEditor.vue'
  import ItemSelectionDrawer from './ItemSelectionDrawer.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import QualityGateEditor from './QualityGateEditor.vue'
  import { configSteps, defaultCaseConfig, pythonTargetTemplate, normalizeCaseInput, qualityGateError } from '../case/config'
  import { useEvaluationEnums } from './useEvaluationEnums'
  const { options: enumOptions } = useEvaluationEnums()
  const targetTypeOptions = computed(() => enumOptions('evaluation_target_type').filter(item => ['api_info', 'script'].includes(String(item.value))))
  const props = withDefaults(
    defineProps<{
      embedded?: boolean
      caseId?: number
      initialRecord?: any
      initialCatalog?: any[]
      initialStep?: string
    }>(),
    { embedded: false }
  )
  const emit = defineEmits<{ (event: 'saved', payload?: any): void }>()
  const slots = useSlots()
  const stepCards = ref<InstanceType<typeof MangoStepCards>>()
  function scrollToStep(key: string) { stepCards.value?.scrollToStep(key) }
  const contentSlot = computed(() => (props.embedded ? 'default' : 'content'))
  const advancedSection = ref('')
  const advancedVisible = computed({
    get: () => Boolean(advancedSection.value),
    set: (value) => {
      if (!value) advancedSection.value = ''
    },
  })
  const advancedTitles: Record<string, string> = {
    answering: '回答生成设置',
    execution: '高级运行设置',
    grading: '强制评分与质量门禁',
  }
  const advancedTitle = computed(() => advancedTitles[advancedSection.value] || '高级配置')
  const permissions = usePermissionStore(),
    dialog = ref<ModalDialogType | null>(null)
  const form = reactive<any>({}),
    config = ref<any>(defaultCaseConfig()),
    catalog = ref<any[]>([])
  const extractionErrors = reactive({ output: '' })
  const itemSelection = ref<InstanceType<typeof ItemSelectionDrawer>>()
  const selectionSummary = computed(() => {
    const { item_ids, exclude } = config.value.data_selection
    return item_ids.length ? `${exclude ? '排除' : '选择'} ${item_ids.length} 条` : '全部启用条目'
  })
  async function saveItemSelection(value: { exclude: boolean; item_ids: number[] }) {
    if (!canEdit.value || !ready.value || loading.value) return false
    const previous = config.value.data_selection, version = form.dataset_version, current = generation
    config.value.data_selection = { ...previous, ...value }
    if (await flush()) return true
    if (current !== generation || version !== form.dataset_version) return false
    config.value.data_selection = previous
    clearTimer()
    return false
  }
  const visibleConfigSteps = computed(() => [
    ...configSteps,
    ...(slots.results ? [{ key: 'results', title: '执行结果' }] : []),
  ])
  const datasetInputVariables = computed(() => versions.value.find(item => item.id === form.dataset_version)?.schema_snapshot?.input_variables || [{ name: 'case_input', path: '$' }])
  const inputReference = (name: string) => '${{' + name + '}}'
  const inputVariableReference = computed(() => datasetInputVariables.value.map((item: any) => '${{' + item.name + '}}').join('、'))
  const aiLoading = ref(false), aiProfiles = ref<any[]>([]), aiError = ref('')
  const aiOptions = computed(() => {
    const options = aiProfiles.value.map(item => ({ value: item.id,
      label: `${item.name}${item.model ? ` · ${item.model}` : ''}${item.enabled ? '' : `（${item.disabled_reason || '已停用'}）`}`, disabled: !item.enabled }))
    const missing = new Set(Object.values(config.value.ai || {}).filter(value => value && !aiProfiles.value.some(item => item.id === value)))
    return [...options, ...Array.from(missing).map(value => ({ value, label: '当前 AI 不可用，请重新选择', disabled: true }))]
  })
  const datasets = ref<any[]>([]),
    versions = ref<any[]>([])
  const targetModule = ref<number | null>(null), interfaces = ref<any[]>([]), interfacesLoading = ref(false), interfacesError = ref('')
  const interfaceOptions = computed(() => interfaces.value.map(item => ({
    value: item.id, label: `${item.name} · ${String(item.protocol_type).toUpperCase()}${item.published ? '' : '（未发布）'}`, disabled: !item.published,
  })))
  let interfaceRequest = 0, interfacePage = 1, interfaceCount = 0, interfaceLoaded = 0, interfaceSearch = ''
  const loading = ref(false),
    ready = ref(false),
    datasetsLoading = ref(false),
    versionsLoading = ref(false),
    saving = ref(false)
  const jsonSection = ref(''),
    baseline = ref(''),
    saveError = ref('')
  const canEdit = computed(() =>
    permissions.hasPermission(form.id ? 'evaluation.case:edit' : 'evaluation.case:create')
  )
  const defaultAnswerProfile = '__platform_default__'
  const answerAiOptions = computed(() => [{ value: defaultAnswerProfile, label: '平台默认回答 AI' }, ...aiOptions.value])
  const answerProfile = computed({
    get: () => config.value.answering ? config.value.ai.answer_profile_id || defaultAnswerProfile : undefined,
    set: (value: string | undefined) => {
      if (!canEdit.value) return
      config.value.answering = value ? config.value.answering || { question_path: 'query', max_tokens: 800 } : null
      config.value.ai.answer_profile_id = value && value !== defaultAnswerProfile ? value : null
    },
  })
  let generation = 0,
    datasetRequest = 0,
    versionRequest = 0
  let timer: ReturnType<typeof setTimeout> | undefined, activeSave: Promise<boolean> | undefined
  const leafId = (value: any) => (Array.isArray(value) ? value[value.length - 1] : value)
  const rows = (response: any) =>
    Array.isArray(response.data) ? response.data : response.data?.items || []
  const datasetOptions = computed(() =>
    datasets.value.map((item) => ({ label: item.name, value: item.id }))
  )
  const versionOptions = computed(() =>
    versions.value
      .filter((item) => item.status === 'published')
      .map((item) => ({ label: `V${item.version_no} ${item.version_label || ''}`, value: item.id }))
  )
  const jsonValue = computed(() => JSON.stringify(config.value, null, 2))
  function clearTimer() {
    if (timer) clearTimeout(timer)
    timer = undefined
  }
  function cancel() {
    extractionErrors.output = ''
    clearTimer()
    activeSave = undefined
    saving.value = false
    generation += 1
    datasetRequest += 1
    versionRequest += 1
    interfaceRequest += 1
    ready.value = false
    jsonSection.value = ''
  }
  async function open(id?: number, product?: any, module?: any) {
    if (saving.value && !props.embedded) return
    const current = ++generation
    extractionErrors.output = ''
    interfaceRequest += 1
    interfacesLoading.value = false
    interfacesError.value = ''
    clearTimer()
    activeSave = undefined
    saving.value = false
    ready.value = false
    loading.value = true
    saveError.value = ''
    advancedSection.value = ''
    if (!props.embedded) dialog.value?.show()
    try {
      const [recordResponse, catalogResponse]: any[] = await Promise.all([
        props.embedded && props.initialRecord?.id === id
          ? Promise.resolve({ data: props.initialRecord })
          : id
          ? getEvaluationCase(id)
          : Promise.resolve({ data: null }),
        props.embedded
          ? props.initialCatalog
            ? Promise.resolve({ data: props.initialCatalog })
            : getCaseGraderCatalog()
          : Promise.resolve({ data: [] }),
      ])
      if (current !== generation) return
      const record = recordResponse.data
      if (
        props.embedded &&
        record &&
        Object.keys(record.config || {}).length &&
        (record.config?.schema_version !== 1 || !record.config?.grading || !record.config?.target)
      )
        throw new Error('当前页面不支持该 Case 配置版本')
      Object.assign(form, {
        id,
        name: record?.name || '',
        description: record?.description || '',
        project_product: record?.project_product || product,
        module: record?.module || module,
        dataset_id: record?.dataset_id,
        dataset_version: record?.dataset_version,
        status: record?.status || 'draft',
      })
      config.value = JSON.parse(
        JSON.stringify(
          record?.config && Object.keys(record.config).length ? normalizeCaseInput(record.config) : defaultCaseConfig()
        )
      )
      targetModule.value = null
      config.value.ai ||= { judge_profile_id: null, summary_profile_id: null, answer_profile_id: null }
      interfaces.value = []
      if (props.embedded && config.value.target.type === 'api_info' && config.value.target.ref_id) {
        if (canEdit.value) {
          try {
            const selected: any = await getEvaluationInterfaces(id!, { selected_id: config.value.target.ref_id })
            if (current !== generation) return
            interfaces.value = rows(selected)
            targetModule.value = interfaces.value[0]?.module_id || null
          } catch {
            if (current === generation) interfacesError.value = '接口信息加载失败，请确认接口执行权限后重试'
          }
        } else {
          interfaces.value = [{ id: config.value.target.ref_id, name: `已配置接口 #${config.value.target.ref_id}`, protocol_type: 'HTTP/SSE', published: true }]
        }
      }
      catalog.value = rows(catalogResponse)
      config.value.ai ||= { judge_profile_id: null, summary_profile_id: null, answer_profile_id: null }
      aiProfiles.value = []
      aiError.value = ''
      if (id) {
        aiLoading.value = true
        try {
          const response: any = await getEvaluationAiProfiles(id)
          if (current === generation) aiProfiles.value = rows(response)
        } catch {
          if (current === generation) aiError.value = 'AI 列表加载失败，请检查效果测评 AI 配置后重新打开用例'
        } finally { if (current === generation) aiLoading.value = false }
      }
      if (props.embedded && canEdit.value) await Promise.all([loadDatasets(), loadVersions()])
      else {
        datasets.value = record ? [{ id: record.dataset_id, name: record.dataset_name }] : []
        versions.value = record
          ? [
              {
                id: record.dataset_version,
                version_no: record.dataset_version_no,
                status: 'published',
                schema_snapshot: { input_variables: record.dataset_input_variables, workflow: record.dataset_workflow_summary },
              },
            ]
          : []
      }
      if (current === generation) {
        baseline.value = JSON.stringify(buildPayload())
        ready.value = true
      }
    } catch (error: any) {
      if (current === generation) {
        saveError.value = 'Case 配置加载失败'
        Message.error(error?.message || saveError.value)
        if (!props.embedded) dialog.value?.close()
      }
    } finally {
      if (current === generation) loading.value = false
    }
  }
  async function loadDatasets(search = '') {
    const request = ++datasetRequest
    datasets.value = []
    datasetsLoading.value = true
    try {
      const response: any = await getEvaluationDatasets({
        name: search || undefined,
        page: 1,
        pageSize: 100,
      })
      if (request === datasetRequest) datasets.value = rows(response)
    } finally {
      if (request === datasetRequest) datasetsLoading.value = false
    }
  }
  async function loadVersions() {
    const request = ++versionRequest
    versions.value = []
    if (!form.dataset_id) {
      versionsLoading.value = false
      return
    }
    versionsLoading.value = true
    try {
      let page = 1,
        count = 0,
        fetched: any[] = []
      do {
        const response: any = await getDatasetVersions(form.dataset_id, { page, pageSize: 100 })
        if (request !== versionRequest) return
        const batch = rows(response)
        fetched.push(...batch)
        count = response.data?.count ?? response.totalSize ?? fetched.length
        page += 1
        if (!batch.length) break
      } while (fetched.length < count)
      if (request === versionRequest) versions.value = fetched
    } finally {
      if (request === versionRequest) versionsLoading.value = false
    }
  }
  function productChanged() {
    form.module = null
  }
  function datasetChanged() {
    form.dataset_version = null
    config.value.data_selection.item_ids = []
    loadVersions()
  }
  function versionChanged() {
    config.value.data_selection.item_ids = []
  }
  function targetChanged() {
    config.value.target.ref_id = null
    config.value.target.version_ref = null
    config.value.target.parameters = config.value.target.type === 'script' ? { code: pythonTargetTemplate } : {}
    targetModule.value = null
    interfaces.value = []
    interfaceRequest += 1
    interfacesLoading.value = false
    interfacesError.value = ''
  }
  function interfaceChanged() { config.value.target.version_ref = null }
  function targetModuleChanged() {
    config.value.target.ref_id = null
    config.value.target.version_ref = null
    interfaces.value = []
    searchInterfaces('')
  }
  function searchInterfaces(search = '') { interfaceSearch = search; return loadInterfaces() }
  function loadMoreInterfaces() {
    if (!interfacesLoading.value && interfaceLoaded < interfaceCount) loadInterfaces(interfacePage + 1)
  }
  async function loadInterfaces(page = 1) {
    const request = ++interfaceRequest, current = generation
    interfacesError.value = ''
    if ((!targetModule.value && !config.value.target.ref_id) || config.value.target.type !== 'api_info') { interfacesLoading.value = false; return }
    interfacesLoading.value = true
    try {
      const selection = targetModule.value ? { module_id: targetModule.value, search: interfaceSearch, page, pageSize: 50 } : { selected_id: config.value.target.ref_id }
      const response: any = await getEvaluationInterfaces(form.id, selection)
      if (request !== interfaceRequest || current !== generation) return
      const selected = interfaces.value.filter(item => item.id === config.value.target.ref_id)
      const all = [...(page === 1 ? selected : interfaces.value), ...rows(response)]
      interfaces.value = [...new Map(all.map(item => [item.id, item])).values()]
      interfacePage = page
      interfaceCount = response.data.count
      interfaceLoaded = (page - 1) * 50 + rows(response).length
      if (!targetModule.value) targetModule.value = rows(response)[0]?.module_id || null
    } catch {
      if (request === interfaceRequest && current === generation) interfacesError.value = '接口加载失败，请重试'
    } finally {
      if (request === interfaceRequest && current === generation) interfacesLoading.value = false
    }
  }
  function saveJson(text: string) {
    if (!canEdit.value) return
    try {
      const value = JSON.parse(text)
      if (
        value.schema_version !== 1 ||
        !value.grading ||
        !value.execution ||
        !value.mapping ||
        !value.data_selection ||
        !value.target
      )
        throw new Error('缺少 Case 必要配置')
      config.value = normalizeCaseInput(value)
      config.value.ai ||= { judge_profile_id: null, summary_profile_id: null, answer_profile_id: null }
      extractionErrors.output = ''
      jsonSection.value = ''
    } catch (error: any) {
      Message.warning(error.message || '配置 JSON 不合法')
    }
  }
  function buildPayload() {
    const snapshot = JSON.parse(JSON.stringify(config.value))
    if (props.embedded)
      return { id: form.id, dataset_version: form.dataset_version || null, config: snapshot }
    return {
      id: form.id,
      name: form.name?.trim() || '',
      description: form.description,
      project_product: leafId(form.project_product),
      module: leafId(form.module) || null,
    }
  }
  const dirty = computed(() => ready.value && (JSON.stringify(buildPayload()) !== baseline.value || Boolean(extractionErrors.output)))
  const saveStatus = computed(() =>
    loading.value
      ? '加载中…'
      : !canEdit.value
      ? '只读'
      : saving.value
      ? '保存中…'
      : saveError.value || (dirty.value ? '待保存' : '已保存')
  )
  function validationError(value: ReturnType<typeof buildPayload>) {
    if (!props.embedded)
      return !value.name || !value.project_product ? '请填写用例名称和项目产品' : ''
    if (extractionErrors.output) return extractionErrors.output
    const gateError = qualityGateError(value.config!.grading.quality_gates || [])
    if (gateError) return gateError
    const aggregation = value.config!.grading.aggregation
    if (!Number.isFinite(aggregation.min_valid_rate) || aggregation.min_valid_rate <= 0 || aggregation.min_valid_rate > 1) return '最低有效率必须大于 0% 且不超过 100%'
    if (!Number.isFinite(aggregation.min_effect_pass_rate) || aggregation.min_effect_pass_rate < 0 || aggregation.min_effect_pass_rate > 1) return '最低通过率必须在 0%～100% 之间'
    const target = value.config!.target
    if (!['api_info', 'script'].includes(target.type)) return '请选择接口管理或 Python 脚本'
    if (target.type === 'api_info' && !target.ref_id) return '请选择接口模块和已发布接口'
    if (target.type === 'script' && !target.parameters.code?.trim()) return '请填写 Python 脚本'
    return ''
  }
  async function flush(): Promise<boolean> {
    clearTimer()
    if (activeSave) {
      const succeeded = await activeSave
      return succeeded ? flush() : false
    }
    if (!ready.value || loading.value) return false
    if (!dirty.value) return true
    if (!canEdit.value) return false
    const value = buildPayload(),
      current = generation,
      error = validationError(value)
    if (error) {
      saveError.value = error
      return false
    }
    saving.value = true
    saveError.value = ''
    const task = (async () => {
      try {
        await updateEvaluationCase(value)
        if (current !== generation) return false
        baseline.value = JSON.stringify(value)
        emit('saved', {
          ...value,
          dataset_name: datasets.value.find((item) => item.id === form.dataset_id)?.name,
          dataset_id: form.dataset_id,
          dataset_version_no: versions.value.find((item) => item.id === value.dataset_version)
            ?.version_no,
        })
        return true
      } catch {
        if (current === generation) saveError.value = '保存失败，修改仍保留，请重试'
        return false
      } finally {
        if (current === generation) saving.value = false
      }
    })()
    activeSave = task
    const succeeded = await task
    if (activeSave === task) activeSave = undefined
    return succeeded && dirty.value ? flush() : succeeded
  }
  async function save() {
    if (props.embedded || form.id) {
      const succeeded = await flush()
      if (succeeded && !props.embedded) dialog.value?.close()
      if (!props.embedded) dialog.value?.setConfirmLoading(false)
      return
    }
    try {
      if (!ready.value || loading.value || saving.value || !canEdit.value) return
      const value = buildPayload(),
        error = validationError(value)
      if (error) {
        Message.warning(error)
        return
      }
      saving.value = true
      await createEvaluationCase(value)
      emit('saved')
      dialog.value?.close()
    } finally {
      saving.value = false
      dialog.value?.setConfirmLoading(false)
    }
  }
  watch(
    [form, config, extractionErrors],
    () => {
      if (!props.embedded || !ready.value || loading.value || !canEdit.value) return
      clearTimer()
      saveError.value = ''
      if (dirty.value)
        timer = setTimeout(() => {
          flush()
        }, 600)
    },
    { deep: true }
  )
  function beforeUnload(event: BeforeUnloadEvent) {
    if (props.embedded && canEdit.value && dirty.value) {
      event.preventDefault()
      event.returnValue = ''
    }
  }
  if (props.embedded) {
    watch(
      () => props.caseId,
      (id) => {
        if (id) open(id)
      },
      { immediate: true }
    )
    onBeforeRouteLeave(async () => !canEdit.value || !dirty.value || (await flush()))
    onBeforeRouteUpdate(async () => !canEdit.value || !dirty.value || (await flush()))
    if (typeof window !== 'undefined') window.addEventListener('beforeunload', beforeUnload)
  }
  onBeforeUnmount(() => {
    cancel()
    if (typeof window !== 'undefined') window.removeEventListener('beforeunload', beforeUnload)
  })
  defineExpose({ open, flush, saving, dirty, ready, loading, saveError, saveStatus, scrollToStep })
</script>
<style scoped>
  .mango-case-editor {
    min-width: 0;
    container-type: inline-size;
  }
  .mango-case-editor--embedded { display: flex; flex-direction: column; height: 100%; min-height: 0; }
  .mango-case-editor--embedded > .mango-case-editor-spin { flex: 1; min-height: 0; }
  .mango-case-editor--embedded > .mango-case-editor-spin :deep(> .mango-panel-spin__content) { display: flex; flex-direction: column; height: 100%; min-height: 0; }
  .mango-case-editor--embedded :deep(.mango-panel-spin__content > .mango-case-editor-form) { flex: 1; min-height: 0; }
  .mango-case-ai-fields {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 440px));
    column-gap: var(--m-space-lg);
    margin-bottom: var(--m-page-gap);
  }
  .mango-case-ai-fields :deep(.arco-form-item) {
    min-width: 0;
    margin-bottom: 0;
  }
  @container (max-width: 620px) {
    .mango-case-ai-fields {
      grid-template-columns: minmax(0, 1fr);
      row-gap: 12px;
    }
  }
  .mango-case-editor-spin {
    width: 100%;
    min-height: 180px;
  }
  .mango-case-field-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 440px));
    column-gap: var(--m-space-lg);
  }
  .mango-case-field-grid > div {
    min-width: 0;
  }
  .mango-case-field-grid__wide {
    grid-column: 1 / -1;
  }
  .mango-case-editor :deep(.arco-input-number) {
    width: 100%;
  }
  @container (max-width: 920px) {
    .mango-case-field-grid,
    .mango-case-ai-fields {
      grid-template-columns: minmax(0, 440px);
    }
  }
  .mango-case-advanced-grading {
    display: grid;
    gap: var(--m-page-gap);
    min-width: 0;
  }
  .mango-answering-hint {
    margin-left: var(--m-page-gap);
    color: var(--m-muted);
    font-size: var(--m-font-caption);
    line-height: 1.6;
  }
  .mango-evaluation-input-binding { display: grid; gap: var(--m-page-gap); width: 100%; min-width: 0; }
  .mango-case-config-form > :deep(.arco-form-item) { max-width: 440px; }
  .mango-case-config-form :deep(.arco-form-item-label-col) { flex: 0 0 120px; max-width: 120px; padding-right: var(--m-space-sm); }
  .mango-case-config-form :deep(.arco-form-item-wrapper-col) { flex: 1; min-width: 0; max-width: none; }
  .mango-case-config-form :deep(.arco-input-number) { max-width: 160px; }
  .mango-case-config-form > :deep(.mango-case-code-field) { max-width: none; }
  .mango-case-python-editor {
    width: 100%;
    min-width: 0;
  }
  .mango-case-python-editor :deep(.cm-editor) {
    width: 100%;
  }
  .mango-case-python-editor :deep(.cm-scroller) {
    min-height: 180px;
    max-height: 360px;
    overflow: auto;
  }
</style>
