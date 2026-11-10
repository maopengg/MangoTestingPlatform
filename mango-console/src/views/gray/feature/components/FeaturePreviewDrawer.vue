<template>
  <a-drawer
    :visible="visible"
    :title="title"
    :width="1000"
    :on-before-cancel="canCancel"
    :mask-closable="!busy"
    :esc-to-close="!busy"
    unmount-on-close
    @update:visible="onVisibleChange"
  >
    <div class="mango-feature-preview">
      <a-alert v-if="saveError" type="error"
        >保存失败或结果未确认，草稿已保留，请核对后重试。</a-alert
      >
      <a-alert v-if="executeError" type="error"
        >执行失败或结果未确认，请先在执行记录核对，再重新预览。</a-alert
      >
      
      <section class="mango-feature-preview__config">
        <div class="mango-feature-preview__heading"
          ><strong>灰度配置</strong
          ><a-space>
            <a-button
              size="small"
              :disabled="busy"
              @click="addPath"
              data-testid="qa-views-gray-feature-button-新增路径"
              >新增路径</a-button
            >
            <a-button
              size="small"
              type="primary"
              :loading="saving"
              :disabled="executing"
              @click="save"
              data-testid="qa-views-gray-feature-button-保存配置"
              >保存配置</a-button
            >
          </a-space></div
        >
        <a-form :model="draft" layout="horizontal" :disabled="busy">
          <a-form-item v-if="record?.config_type === 1" label="路径配置">
            <div class="mango-feature-preview__paths">
              <div
                v-for="(item, index) in draft.paths"
                :key="index"
                class="mango-feature-preview__path"
              >
                <a-cascader
                  v-model="item.path"
                  :options="pathOptions"
                  allow-clear
                  allow-search
                  check-strictly
                  path-mode
                  placeholder="请选择路径"
                  data-testid="qa-views-gray-feature-cascader-请选择路径"
                />
                <a-select
                  v-model="item.value_type"
                  :options="grayValueTypeOptions"
                  placeholder="值类型"
                  data-testid="qa-views-gray-feature-select-值类型"
                />
                <a-input
                  v-model="item.original_value"
                  allow-clear
                  placeholder="原值，可选"
                  data-testid="qa-views-gray-feature-input-原值-可选"
                />
                <a-input
                  :model-value="inputValue(item.value)"
                  allow-clear
                  placeholder="替换值，如 ${{tenant_id}}"
                  data-testid="qa-views-gray-feature-input-替换值-如-tenant_id"
                  @update:model-value="item.value = $event"
                />
                <a-button
                  size="mini"
                  status="danger"
                  :disabled="busy"
                  @click="removePath(index)"
                  data-testid="qa-views-gray-feature-button-删除"
                  >删除</a-button
                >
              </div>
            </div>
          </a-form-item>
        </a-form>
      </section>
      <a-form :model="variables" layout="inline" :disabled="busy">
        <a-form-item v-if="needsVariables" label="变量来源"
          ><a-select
            v-model="variables.source"
            :options="variableSourceOptions"
            placeholder="请选择变量来源"
            data-testid="qa-views-gray-feature-select-请选择变量来源"
        /></a-form-item>
        <a-form-item v-if="needsVariables" label="变量环境"
          ><a-select
            v-model="variables.environment"
            :options="environmentOptions"
            :loading="enumLoading"
            :field-names="{ value: 'key', label: 'title' }"
            allow-search
            placeholder="请选择变量环境"
            data-testid="qa-views-gray-feature-select-请选择变量环境"
        /></a-form-item>
        <a-form-item
          ><a-button
            size="small"
            type="primary"
            :loading="loading"
            :disabled="busy"
            @click="generate"
            data-testid="qa-views-gray-feature-button-重新预览"
            >重新预览</a-button
          ></a-form-item
        >
      </a-form>
      
      <MangoPanelSpin :loading="loading" class="mango-feature-preview__output">
        <section
          ><strong>原文</strong
          ><div class="mango-feature-preview__code"
            ><CodeEditor
              v-model="beforeText"
              readonly
              placeholder="暂无原文"
              :code-style="{ height: '100%' }" /></div
        ></section>
        <section
          ><strong>修改后</strong
          ><div class="mango-feature-preview__code"
            ><CodeEditor
              v-model="afterText"
              readonly
              placeholder="暂无修改内容"
              :code-style="{ height: '100%' }" /></div
        ></section>
      </MangoPanelSpin>
    </div>
    <template #footer
      ><a-space>
        <a-button
          :disabled="busy"
          @click="onVisibleChange(false)"
          data-testid="qa-views-gray-feature-button-关闭"
          >关闭</a-button
        >
        <a-button
          type="primary"
          status="success"
          :disabled="!canExecute || saving"
          :loading="executing"
          @click="execute"
          data-testid="qa-views-gray-feature-button-执行"
          >执行</a-button
        >
      </a-space></template
    >
  </a-drawer>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { postGrayFeatureExecute, postGrayFeaturePreview, putGrayFeature } from '@/api/gray'
  import { grayValueTypeOptions, variableSourceOptions } from '../config'
  import { contextOf, idOf, object, type ContextSource } from '../editor-form'
  import type { FeatureRow } from '../records'
  import {
    COMMON_ENV,
    environment,
    hasVariables,
    inputValue,
    normalizePaths,
    pathDrafts,
    previewResult,
    type PathDraft,
    type PathOption,
  } from '../preview'

  const props = defineProps<{
    contextKey: ContextSource
    blocked: boolean
    reloadList: () => Promise<boolean>
  }>()
  const emit = defineEmits<{
    (event: 'visible', value: boolean): void
    (event: 'busy', value: boolean): void
  }>()
  const contextKey = computed(() => contextOf(props.contextKey))
  const enumStore = useEnum(),
    visible = ref(false),
    record = ref<FeatureRow | null>(null)
  const draft = reactive<{ paths: PathDraft[] }>({ paths: [] })
  const variables = reactive<{ source: string; environment: string | number | null }>({
    source: 'api',
    environment: COMMON_ENV,
  })
  const loading = ref(false),
    saving = ref(false),
    executing = ref(false),
    busy = computed(() => saving.value || executing.value)
  const previewError = ref(false),
    saveError = ref(false),
    executeError = ref(false),
    enumError = ref(false),
    enumLoading = ref(false)
  const beforeText = ref(''),
    afterText = ref(''),
    filePath = ref(''),
    pathOptions = ref<PathOption[]>([]),
    acceptedFingerprint = ref<string | null>(null)
  let active = true,
    generation = 0,
    requestSequence = 0,
    enumSequence = 0
  const title = computed(
    () => `${record.value?.name || '-'} 预执行预览${filePath.value ? ` / ${filePath.value}` : ''}`
  )
  const needsVariables = computed(() => hasVariables(draft.paths))
  const environmentOptions = computed(() => [
    { key: COMMON_ENV, title: '环境通用' },
    ...(Array.isArray(enumStore.environment_type) ? enumStore.environment_type : []),
  ])
  const fingerprint = computed(() =>
    JSON.stringify([draft.paths, variables.source, variables.environment])
  )
  const canExecute = computed(
    () =>
      visible.value &&
      !loading.value &&
      acceptedFingerprint.value !== null &&
      acceptedFingerprint.value === fingerprint.value
  )
  function payload() {
    return {
      feature_id: record.value?.id,
      target_value: '',
      action: 'enable',
      variable_source: needsVariables.value ? variables.source : '',
      variable_test_env: needsVariables.value ? environment(variables.environment) : null,
      path_config: normalizePaths(draft.paths),
    }
  }
  function invalidatePreview() {
    ++requestSequence
    loading.value = false
    acceptedFingerprint.value = null
    beforeText.value = ''
    afterText.value = ''
    previewError.value = false
  }
  function reset() {
    ++generation
    ++enumSequence
    invalidatePreview()
    visible.value = false
    record.value = null
    draft.paths = []
    pathOptions.value = []
    filePath.value = ''
    saveError.value = false
    executeError.value = false
    enumError.value = false
    enumLoading.value = false
  }
  function canCancel() {
    return !busy.value
  }
  function onVisibleChange(value: boolean) {
    if (!value && !busy.value) reset()
  }
  function open(source: FeatureRow) {
    if (!active || props.blocked || busy.value || !idOf(source.id)) return
    reset()
    record.value = JSON.parse(JSON.stringify(source)) as FeatureRow
    draft.paths = pathDrafts(record.value.path_config)
    filePath.value =
      source.yaml_file?.file_path || source.datasource_alias?.name || source.database?.name || ''
    variables.source = 'api'
    variables.environment =
      enumStore.environment_type?.find((item) =>
        [item.title, item.key].some((value) => {
          const text = String(value ?? '').toLowerCase()
          return text.includes('测试') || text === 'test' || text === '2'
        })
      )?.key ?? COMMON_ENV
    visible.value = true
    void loadEnums()
    void generate()
  }
  async function loadEnums() {
    if (!active || !visible.value || busy.value) return
    const sequence = ++enumSequence,
      version = generation
    enumLoading.value = true
    enumError.value = false
    const current = () =>
      active && visible.value && version === generation && sequence === enumSequence
    try {
      await enumStore.getEnum()
      if (current()) enumError.value = false
    } catch (loadFailure0) {
      if (current()) (reportLoadError(loadFailure0, "加载失败，请重试", false), enumError.value = true)
    } finally {
      if (current()) enumLoading.value = false
    }
  }
  async function generate() {
    const source = record.value
    if (!active || !visible.value || props.blocked || busy.value || !source) return
    if (needsVariables.value && !variables.source) {
      Message.warning('请选择变量来源')
      return
    }
    invalidatePreview()
    const sequence = ++requestSequence,
      version = generation,
      signature = fingerprint.value,
      context = contextKey.value,
      request = payload()
    const current = () =>
      active &&
      visible.value &&
      version === generation &&
      context === contextKey.value &&
      sequence === requestSequence &&
      signature === fingerprint.value
    loading.value = true
    try {
      const result = previewResult(await postGrayFeaturePreview(request), source)
      if (!current()) return
      beforeText.value = result.before
      afterText.value = result.after
      if (result.filePath) filePath.value = result.filePath
      pathOptions.value = result.paths
      acceptedFingerprint.value = signature
    } catch (loadFailure1) {
      if (current()) (reportLoadError(loadFailure1, "加载失败，请重试", false), previewError.value = true)
    } finally {
      if (current()) loading.value = false
    }
  }
  async function refresh(current: () => boolean) {
    try {
      const loaded = await props.reloadList()
      if (current() && !loaded) Message.error('操作已完成，列表读取失败，请重试查询')
    } catch {
      if (current()) Message.error('操作已完成，列表读取失败，请重试查询')
    }
  }
  async function save() {
    const source = record.value
    if (!active || !visible.value || props.blocked || busy.value || !source) return
    const version = generation,
      context = contextKey.value,
      paths = normalizePaths(draft.paths)
    const current = () => active && version === generation && context === contextKey.value
    invalidatePreview()
    saving.value = true
    saveError.value = false
    let applied = false
    try {
      const response = await putGrayFeature({ id: source.id, path_config: paths })
      if (!current()) return
      const row = object(response.data)
      if (
        response.code !== 200 ||
        idOf(row.id) !== source.id ||
        idOf(row.project_product) !== idOf(source.project_product) ||
        idOf(row.module) !== idOf(source.module) ||
        row.config_type !== source.config_type ||
        !Array.isArray(row.path_config) ||
        JSON.stringify(normalizePaths(row.path_config)) !== JSON.stringify(paths)
      )
        throw Error('Invalid path configuration acknowledgment')
      record.value = { ...source, path_config: row.path_config }
      draft.paths = pathDrafts(row.path_config)
      applied = true
      Message.success('灰度配置已保存')
      await refresh(current)
    } catch {
      if (current()) saveError.value = true
    } finally {
      saving.value = false
    }
    if (applied && current() && visible.value) await generate()
  }
  async function execute() {
    if (
      !active ||
      !visible.value ||
      props.blocked ||
      busy.value ||
      !canExecute.value ||
      !record.value
    )
      return
    const version = generation,
      context = contextKey.value,
      request = payload()
    const current = () => active && version === generation && context === contextKey.value
    executing.value = true
    executeError.value = false
    try {
      const response = await postGrayFeatureExecute(request)
      if (!current()) return
      const row = object(response.data)
      if (
        response.code !== 200 ||
        !idOf(row.execution_log_id) ||
        typeof row.status !== 'number' ||
        ![0, 1, 2, 3, 4].includes(row.status)
      )
        throw Error('Invalid execution acknowledgment')
      if (row.status === 1) Message.success('执行成功')
      else Message.error('执行失败，请在执行记录中查看详情')
      visible.value = false
      invalidatePreview()
      await refresh(current)
    } catch {
      if (current()) {
        executeError.value = true
        invalidatePreview()
      }
    } finally {
      executing.value = false
    }
  }
  function addPath() {
    if (!busy.value)
      draft.paths.push({ path: [], value_type: 'number', original_value: '', value: '' })
  }
  function removePath(index: number) {
    if (!busy.value) draft.paths.splice(index, 1)
  }
  watch(fingerprint, invalidatePreview, { flush: 'sync' })
  watch(contextKey, reset, { flush: 'sync' })
  watch(visible, (value) => emit('visible', value), { flush: 'sync' })
  watch(busy, (value) => emit('busy', value), { flush: 'sync' })
  onDeactivated(() => {
    active = false
    reset()
  })
  onActivated(() => {
    active = true
  })
  onBeforeUnmount(() => {
    active = false
    reset()
  })
  defineExpose({ open })
</script>

<style scoped lang="less">
  .mango-feature-preview {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
    min-width: 0;
    color: var(--m-text-2);
  }
  .mango-feature-preview__config {
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
  }
  .mango-feature-preview__heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 8px;
  }
  .mango-feature-preview__paths {
    display: flex;
    flex-direction: column;
    gap: 8px;
    width: 100%;
    min-width: 0;
  }
  .mango-feature-preview__path {
    display: grid;
    grid-template-columns: minmax(150px, 1.2fr) 90px minmax(100px, 1fr) minmax(120px, 1fr) max-content;
    gap: 8px;
    align-items: center;
  }
  .mango-feature-preview__output :deep(> .mango-panel-spin__content) {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
  }
  .mango-feature-preview__code {
    height: clamp(180px, 30vh, 360px);
    margin-top: 8px;
    min-width: 0;
    overflow: hidden;
  }
</style>
