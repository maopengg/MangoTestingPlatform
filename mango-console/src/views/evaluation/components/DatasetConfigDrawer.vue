<template>
  <BaseSidePanel
    v-model:visible="visible"
    title="数据集配置"
    :width="1100"
    :mask-closable="!saving"
  >
    <a-form
      v-if="version"
      :model="config"
      layout="horizontal"
      auto-label-width
      :disabled="readonly || saving"
      :inert="saving"
      class="mango-dataset-flow"
    >
      <section class="mango-dataset-config-section">
        <h3 class="mango-dataset-config-heading">字段配置</h3>
        <section
          v-for="section in fieldSections"
          :key="section.key"
          class="mango-dataset-config-fields"
        >
          <h4 class="mango-dataset-config-subtitle">{{ section.title }}</h4>
          <div class="mango-dataset-config-field-body"
            ><SchemaEditor
              :key="version.id"
              :model-value="config[section.key] || {}"
              :readonly="readonly"
              :disabled="readonly || saving"
              @update:model-value="config[section.key] = $event"
          /></div>
        </section>
      </section>
      <section class="mango-dataset-config-section">
        <div class="mango-dataset-config-toolbar"
          ><h3 class="mango-dataset-config-heading">输入配置</h3
          ><a-space
            ><a-button
              size="small"
              :loading="previewing"
              :disabled="!sampleAvailable"
              @click="preview"
              >预览输入变量</a-button
            ><a-button
              v-if="!readonly"
              size="small"
              @click="config.input_variables.push({ name: '', path: '$' })"
              >添加变量</a-button
            ></a-space
          ></div
        >
        <div class="mango-dataset-config-input-body">
          <a-table
            size="small"
            class="mango-native-scroll-table"
            :columns="variableColumns"
            :data="config.input_variables"
            :pagination="false"
            :scroll="{ x: variableTableWidth, y: 240 }"
          >
            <template #name="{ record }"
              ><span v-if="readonly">{{ record.name }}</span
              ><a-input
                v-else
                v-model="record.name"
                size="small"
                placeholder="如 case_input"
                aria-label="输入变量名称"
            /></template>
            <template #path="{ record }"
              ><span v-if="readonly">{{
                inputFieldOptions.find((item) => item.value === record.path)?.label || record.path
              }}</span
              ><a-select
                v-else
                v-model="record.path"
                size="small"
                :options="inputFieldOptions"
                placeholder="选择输入字段"
                aria-label="输入字段"
                allow-search
            /></template>
            <template #reference="{ record }"
              ><code>{{ reference(record.name) }}</code></template
            >
            <template #actions="{ rowIndex }"
              ><MangoTableActions
                :actions="
                  readonly
                    ? []
                    : [
                        {
                          label: '移除',
                          danger: true,
                          disabled: config.input_variables.length === 1,
                          onClick: () => config.input_variables.splice(rowIndex, 1),
                        },
                      ]
                "
            /></template>
          </a-table>
          <a-alert data-feedback-kind="validation" v-if="previewError" type="error">{{ previewError }}</a-alert>
          <JsonDisplay
            v-if="previewResult !== undefined"
            :data="previewResult"
            :show-drawer-button="false"
          />
          <a-form-item label="条目组织" class="mango-dataset-config-sequence"
            ><span v-if="readonly">{{
              options('evaluation_sequence').find((item) => item.value === config.workflow.sequence)
                ?.label || config.workflow.sequence
            }}</span
            ><a-select
              v-else
              v-model="config.workflow.sequence"
              size="small"
              :options="options('evaluation_sequence')"
          /></a-form-item>
        </div>
      </section>
      <MangoRequestFeedback v-if="error" :message="(error)" />
    </a-form>
    <template #footer-buttons
      ><a-space
        ><a-button v-if="!readonly" type="primary" size="small" :loading="saving" @click="save"
          >保存</a-button
        ><a-button size="small" :disabled="saving" @click="visible = false">{{
          readonly ? '关闭' : '取消'
        }}</a-button></a-space
      ></template
    >
  </BaseSidePanel>
</template>
<script setup lang="ts">
  import { requestFailureMessage, reportLoadError } from '@/utils/load-error'
  import { computed, onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import SchemaEditor from './SchemaEditor.vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import { useRoute } from 'vue-router'
  import useUserStore from '@/store/modules/user'
  import { cloneLosslessJson } from '@/utils/lossless-json'
  import { updateDatasetVersion, previewDatasetInputs } from '@/api/evaluation'
  import { inputVariableColumns, datasetConfigurationError } from '../dataset/workflow'
  import { createDatasetConfiguration, datasetInputFields } from '../dataset/configuration'
  import type { DatasetConfiguration, DatasetVersion } from '../dataset/types'
  import { useEvaluationEnums } from './useEvaluationEnums'
  const emit = defineEmits<{ (event: 'saved', value: DatasetVersion): void }>()
  const user = useUserStore(),
    route = useRoute()
  const { options } = useEvaluationEnums()
  const visible = ref(false),
    version = ref<DatasetVersion | null>(null)
  const config = ref<DatasetConfiguration>(createDatasetConfiguration())
  const sample = ref<unknown>(),
    previewResult = ref<unknown>()
  const saving = ref(false),
    previewing = ref(false),
    error = ref(''),
    previewError = ref('')
  const fieldSections = [
    { key: 'input_schema', title: '输入' },
    { key: 'expected_schema', title: '期望输出' },
    { key: 'context_schema', title: '评分依据' },
  ] as const
  let generation = 0
  const readonly = computed(() => version.value?.status !== 'draft')
  const sampleAvailable = computed(() => sample.value !== undefined)
  const reference = (name: string) => '${{' + name + '}}'
  const variableColumns = computed(() =>
    inputVariableColumns.filter((column) => {
      if (column.slotName === 'actions') return !readonly.value
      if (column.slotName === 'path')
        return (
          config.value.input_variables.length > 1 ||
          config.value.input_variables.some((item) => item.path !== '$')
        )
      return true
    })
  )
  const variableTableWidth = computed(() =>
    variableColumns.value.reduce((width, column) => width + column.width, 0)
  )
  const inputFieldOptions = computed(() => datasetInputFields(config.value, sample.value))
  let previewRequest = 0
  function invalidatePreview() {
    ++previewRequest
    previewResult.value = undefined
    previewError.value = ''
    previewing.value = false
  }
  function close() {
    ++generation
    invalidatePreview()
    visible.value = false
    version.value = null
    sample.value = undefined
    config.value = createDatasetConfiguration()
    error.value = ''
  }
  function open(record: DatasetVersion, input?: unknown) {
    if (saving.value) return
    generation++
    version.value = cloneLosslessJson(record)
    sample.value = cloneLosslessJson(input)
    invalidatePreview()
    error.value = ''
    config.value = createDatasetConfiguration(record.schema_snapshot)
    visible.value = true
  }
  async function preview() {
    if (
      !visible.value ||
      !version.value ||
      !sampleAvailable.value ||
      previewing.value ||
      saving.value
    )
      return
    const validation = datasetConfigurationError(config.value)
    if (validation) {
      previewError.value = validation
      return
    }
    const current = generation,
      request = ++previewRequest,
      id = version.value.id
    const payload = cloneLosslessJson({
      input_variables: config.value.input_variables,
      input_data: sample.value,
    })
    previewing.value = true
    previewError.value = ''
    try {
      const response: { data: unknown } = await previewDatasetInputs(id, payload)
      if (visible.value && current === generation && request === previewRequest)
        previewResult.value = response.data
    } catch (loadFailure0) {
      if (current === generation && request === previewRequest)
        void (reportLoadError(loadFailure0, '输入变量预览失败，请重试'), previewError.value = '')
    } finally {
      if (current === generation && request === previewRequest) previewing.value = false
    }
  }
  async function save() {
    if (!visible.value || !version.value || readonly.value || saving.value) return false
    error.value = datasetConfigurationError(config.value)
    if (error.value) return false
    const id = version.value.id,
      current = generation
    const schema = cloneLosslessJson(config.value)
    schema.workflow = { ...schema.workflow, preparation: 'none', steps: [], bindings: [] }
    saving.value = true
    try {
      const response: { data: DatasetVersion } = await updateDatasetVersion(id, {
        schema_snapshot: schema,
      })
      if (!visible.value || current !== generation) return false
      emit('saved', response.data)
      visible.value = false
      Message.success('数据集配置已保存')
      return true
    } catch (requestFailure) {
      if (visible.value && current === generation)
        error.value = requestFailureMessage(requestFailure, '数据集配置保存失败，草稿已保留，请重试')
      return false
    } finally {
      saving.value = false
    }
  }
  watch(
    () => JSON.stringify([config.value.input_variables, config.value.input_schema, sample.value]),
    invalidatePreview,
    { flush: 'sync' }
  )
  watch(
    visible,
    (value) => {
      if (!value) close()
    },
    { flush: 'sync' }
  )
  watch(() => [route.path, route.query.id, user.userId, user.roleId, user.token], close, {
    flush: 'sync',
  })
  onDeactivated(close)
  onBeforeUnmount(close)
  defineExpose({ open, close })
</script>
<style scoped>
  .mango-dataset-flow {
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }
  .mango-dataset-config-heading {
    margin: 0;
    font-size: 15px;
    line-height: 24px;
    font-weight: 600;
    color: var(--m-text);
  }
  .mango-dataset-config-subtitle {
    margin: 0 0 var(--m-page-gap);
    font-size: 13px;
    line-height: 20px;
    font-weight: 500;
    color: var(--m-text-2);
  }
  .mango-dataset-config-section + .mango-dataset-config-section {
    padding-top: 16px;
    border-top: 1px solid var(--m-border);
  }
  .mango-dataset-config-fields {
    margin-top: 12px;
    padding-inline-start: 16px;
    min-width: 0;
  }
  .mango-dataset-config-field-body,
  .mango-dataset-config-input-body {
    padding-inline-start: 16px;
    min-width: 0;
  }
  .mango-dataset-config-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: var(--m-page-gap);
    margin-bottom: 12px;
  }
  .mango-dataset-config-sequence {
    margin-top: 12px;
    margin-bottom: 0;
    max-width: 420px;
  }
  .mango-dataset-flow code {
    overflow-wrap: anywhere;
  }
</style>
