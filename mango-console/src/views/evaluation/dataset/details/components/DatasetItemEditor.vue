<template>
  <BaseSidePanel
    v-model:visible="itemEditorVisible"
    :title="itemForm.id ? '编辑评测数据条目' : '新增评测数据条目'"
    width="50%"
    :mask-closable="!itemSaving"
  >
    <a-form
      v-if="itemVersion"
      :model="itemForm"
      layout="horizontal"
      size="small"
      :disabled="itemSaving"
      :inert="itemSaving"
      class="mango-evaluation-item-form"
    >
      <ItemDataSourceEditor
        v-if="itemForm.version_id"
        :key="`${itemForm.version_id}-${itemForm.id || 'new'}`"
        v-model="itemForm.data_source"
        :version-id="itemForm.version_id"
        :disabled="itemSaving"
        class="mango-item-editor-section"
      />
      <ScenarioEditor
        v-model="itemForm.scenario"
        :sequence="itemVersion?.schema_snapshot?.workflow?.sequence || 'independent'"
        :disabled="itemSaving"
        class="mango-item-editor-section"
      />
      <section
        v-for="section in itemDataSections"
        :key="section.key"
        class="mango-item-editor-section"
      >
        <h3 class="mango-item-editor-heading">{{ section.title }}</h3>
        <div class="mango-item-editor-body"
          ><DataFieldsEditor
            :model-value="parseFields(itemForm[section.key])"
            :schema="itemVersion?.schema_snapshot?.[section.schema]"
            :disabled="itemSaving"
            @update:model-value="itemForm[section.key] = JSON.stringify($event)"
        /></div>
      </section>
      <section class="mango-item-editor-section">
        <h3 class="mango-item-editor-heading">评分规则</h3>
        <div class="mango-item-editor-body">
          <div class="mango-evaluation-item-fields">
            <a-form-item label="数据条目权重"
              ><a-input-number v-model="itemForm.weight" :min="0.001" :step="0.1"
            /></a-form-item>
            <a-form-item label="评分模式"
              ><a-select
                v-model="itemForm.grading_config.mode"
                :options="[
                  { label: '继承 Case 默认评分', value: 'inherit' },
                  { label: '替换默认评分', value: 'replace' },
                ]"
                @change="changeItemGradingMode"
            /></a-form-item>
          </div>
          
          <MangoPanelSpin
            v-if="itemForm.grading_config.mode === 'replace'"
            :loading="catalogLoading"
            class="mango-evaluation-grader-loading"
            ><GraderEditor
              v-model="itemForm.grading_config.graders"
              :disabled="itemSaving"
              :catalog="graderCatalog"
              :loading="catalogLoading"
              title="条目专属评分"
              empty-text="替换模式需要至少一个有效评分项；Case 强制项仍会追加"
          /></MangoPanelSpin>
        </div>
      </section>
      <section class="mango-item-editor-section">
        <h3 class="mango-item-editor-heading">其他设置</h3>
        <div class="mango-item-editor-body">
          <div class="mango-evaluation-item-fields">
            <a-form-item label="标签"
              ><a-input
                v-model="itemForm.tags_text"
                placeholder="英文逗号分隔，如：有订单,权限边界"
            /></a-form-item>
            <a-form-item label="优先级"
              ><a-select
                v-model="itemForm.priority"
                :options="
                  itemPriorityOptions.map(({ key, title }) => ({ label: title, value: key }))
                "
            /></a-form-item>
            <a-form-item label="启用"
              ><a-switch v-model="itemForm.enabled" size="small"
            /></a-form-item>
          </div>
        </div>
      </section>
    </a-form>
    <a-alert v-if="saveError" type="error">{{ saveError }}</a-alert>
    <template #footer-buttons
      ><a-space
        ><a-button size="small" type="primary" :loading="itemSaving" @click="saveItem"
          >保存</a-button
        ><a-button size="small" :disabled="itemSaving" @click="itemEditorVisible = false"
          >取消</a-button
        ></a-space
      ></template
    >
  </BaseSidePanel>
</template>
<script setup lang="ts">
  import { onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import { createEvaluationDatasetItem, updateEvaluationDatasetItem } from '@/api/evaluation'
  import { cloneLosslessJson } from '@/utils/lossless-json'
  import DataFieldsEditor from '../../../components/DataFieldsEditor.vue'
  import GraderEditor from '../../../components/GraderEditor.vue'
  import ScenarioEditor from '../../../components/ScenarioEditor.vue'
  import ItemDataSourceEditor from '../../../components/ItemDataSourceEditor.vue'
  import type { GraderCatalogEntry } from '../../../types'
  import type { DatasetItem, DatasetVersion } from '../../types'
  import { itemDataSourceError } from '../../workflow'
  import { createItemForm, itemPayload } from '../form'
  import { itemEditorSections, itemPriorityOptions } from '../config'

  const props = withDefaults(
    defineProps<{
      contextKey: number
      graderCatalog: GraderCatalogEntry[]
      catalogLoading?: boolean
      catalogError?: string
    }>(),
    { catalogLoading: false, catalogError: '' }
  )
  const emit = defineEmits<{
    (event: 'saved', versionId: number): void
    (event: 'load-catalog'): void
  }>()
  const itemForm = reactive(createItemForm()),
    itemVersion = ref<DatasetVersion | null>(null)
  const itemEditorVisible = ref(false),
    itemSaving = ref(false),
    saveError = ref('')
  const itemDataSections = itemEditorSections
  let generation = 0
  const parseFields = (text: string): unknown => {
    try {
      return JSON.parse(text || '{}')
    } catch {
      return {}
    }
  }
  function close() {
    ++generation
    itemEditorVisible.value = false
    itemVersion.value = null
    saveError.value = ''
    Object.assign(itemForm, createItemForm())
  }
  function open(version: DatasetVersion, record?: DatasetItem) {
    if (itemSaving.value || version.status !== 'draft') return
    ++generation
    itemVersion.value = cloneLosslessJson(version)
    Object.assign(itemForm, createItemForm(version.id, record))
    saveError.value = ''
    itemEditorVisible.value = true
    if (itemForm.grading_config.mode === 'replace') emit('load-catalog')
  }
  function changeItemGradingMode() {
    if (itemSaving.value) return
    itemForm.grading_config.graders = []
    if (itemForm.grading_config.mode === 'replace') emit('load-catalog')
  }
  async function saveItem() {
    if (
      itemSaving.value ||
      !itemEditorVisible.value ||
      !itemVersion.value ||
      itemVersion.value.status !== 'draft' ||
      !itemForm.version_id
    )
      return false
    saveError.value = itemDataSourceError(itemForm.data_source)
    if (saveError.value) return false
    const current = generation,
      versionId = itemForm.version_id
    itemSaving.value = true
    try {
      const payload = itemPayload(itemForm)
      if (payload.id) await updateEvaluationDatasetItem(payload)
      else await createEvaluationDatasetItem(versionId, payload)
      if (current !== generation || !itemEditorVisible.value) return false
      itemEditorVisible.value = false
      emit('saved', versionId)
      return true
    } catch (error) {
      if (current === generation && itemEditorVisible.value)
        saveError.value =
          error instanceof SyntaxError
            ? '数据条目 JSON 格式不正确'
            : '数据条目保存失败，草稿已保留，请重试'
      return false
    } finally {
      itemSaving.value = false
    }
  }
  watch(
    itemEditorVisible,
    (value) => {
      if (!value) close()
    },
    { flush: 'sync' }
  )
  watch(() => props.contextKey, close, { flush: 'sync' })
  onDeactivated(close)
  onBeforeUnmount(close)
  defineExpose({ open, close })
</script>
<style scoped lang="less">
  .mango-evaluation-item-form {
    container-type: inline-size;
    display: flex;
    flex-direction: column;
    gap: 12px;
    min-width: 0;
  }
  .mango-evaluation-item-form :deep(.arco-form-item-label-col) {
    flex: 0 0 112px;
    max-width: 112px;
  }
  .mango-evaluation-item-form :deep(.arco-form-item-wrapper-col) {
    flex: 1;
    min-width: 0;
    max-width: none;
  }
  .mango-evaluation-item-form :deep(.arco-form-item) {
    margin-bottom: 12px;
  }
  .mango-item-editor-section {
    min-width: 0;
  }
  .mango-item-editor-body {
    padding-inline-start: 16px;
    min-width: 0;
  }
  .mango-item-editor-section + .mango-item-editor-section {
    padding-top: 12px;
    border-top: 1px solid var(--m-border);
  }
  .mango-item-editor-heading,
  .mango-evaluation-item-form :deep(.mango-item-source > h3) {
    margin: 0 0 8px;
    font-size: 15px;
    font-weight: 600;
    line-height: 24px;
    color: var(--m-text);
  }
  .mango-item-editor-subheading {
    margin: var(--m-page-gap) 0;
    font-size: 13px;
    font-weight: 500;
    color: var(--m-text-2);
  }
  .mango-evaluation-item-fields {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: var(--m-page-gap);
  }
  .mango-evaluation-item-fields :deep(.arco-input-number) {
    width: 100%;
  }
  .mango-evaluation-grader-loading {
    width: 100%;
    margin-bottom: var(--m-page-gap);
  }
  @container (max-width: 600px) {
    .mango-evaluation-item-fields {
      grid-template-columns: minmax(0, 1fr);
    }
  }
</style>
