<template>
  <a-modal
    v-model:visible="visible"
    :title="editingId === null ? '新增测试对象' : '编辑测试对象'"
    :width="760"
    :on-before-ok="save"
    :ok-loading="saving"
    :closable="!saving"
    :mask-closable="!saving"
    :esc-to-close="!saving"
    :cancel-button-props="{ disabled: saving }"
    unmount-on-close
    @cancel="close"
  >
    <a-form :model="draft" :disabled="saving" layout="horizontal" class="mango-target-editor">
      <section class="mango-target-editor__section">
        <header class="mango-target-editor__heading">
          <strong>基础信息</strong>
          <span>设置所属项目产品、环境及自动化类型</span>
        </header>
        <div class="mango-target-editor__grid">
          <a-form-item label="项目/产品" class="mango-form-item__require">
            <ProjectProductSelect
              v-model="draft.project_product"
              :disabled="saving"
              placeholder="请选择项目名称"
            />
          </a-form-item>
          <a-form-item label="环境名称" class="mango-form-item__require">
            <a-input v-model="draft.name" placeholder="请输入环境名称" />
          </a-form-item>
          <a-form-item label="被测环境" class="mango-form-item__require">
            <a-select
              v-model="draft.environment"
              :options="enumStore.environment_type"
              :field-names="fieldNames"
              placeholder="请选择被测环境"
              allow-clear
              allow-search
            />
          </a-form-item>
          <a-form-item label="自动化类型" class="mango-form-item__require">
            <a-select
              v-model="draft.auto_type"
              :options="enumStore.auto_type"
              :field-names="fieldNames"
              placeholder="请选择产品的端类型"
              allow-clear
              allow-search
            />
          </a-form-item>
        </div>
      </section>
      <section class="mango-target-editor__section">
        <header class="mango-target-editor__heading">
          <strong>被测对象</strong>
          <span>配置默认地址，按缓存中的条件值匹配不同地址</span>
        </header>
        <template v-if="draft.legacyMode">
          <a-form-item label="历史地址">
            <a-input v-model="draft.legacyValue" placeholder="域名/包名/路径" />
          </a-form-item>
          <a-form-item label="地址配置">
            <a-button size="small" :disabled="saving" @click="useNewTargetConfig"
              >切换为变量映射配置</a-button
            >
          </a-form-item>
        </template>
        <TestTargetEditor v-else v-model="draft.targetConfig" :disabled="saving" />
      </section>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
  import { reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { postUserTestObject, putUserTestObject } from '@/api/system/test_object'
  import { useEnum } from '@/store/modules/get-enum'
  import { fieldNames } from '@/setting'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import TestTargetEditor from './TestTargetEditor.vue'
  import {
    createTargetDraft,
    targetPayload,
    validateTargetDraft,
    switchTargetConfig,
  } from '../form'
  import { useTestObjectScope } from '../composables/useTestObjectScope'
  import type { TargetId, TestObjectRecord } from '../types'
  const emit = defineEmits<{
    (event: 'saved'): void
    (event: 'saving-change', id: number | null, pending: boolean): void
  }>()
  const enumStore = useEnum()
  const visible = ref(false),
    saving = ref(false),
    editingId = ref<number | null>(null)
  const draft = reactive(createTargetDraft())
  let session = 0
  const scope = useTestObjectScope(close)
  function open(record?: TestObjectRecord, product: TargetId | null = null) {
    if (saving.value || !scope.isActive()) return
    ++session
    editingId.value = record?.id ?? null
    Object.assign(draft, createTargetDraft(record, product))
    visible.value = true
  }
  function close() {
    ++session
    visible.value = false
    editingId.value = null
    Object.assign(draft, createTargetDraft())
  }
  function useNewTargetConfig() {
    if (!saving.value) switchTargetConfig(draft)
  }
  async function save(): Promise<boolean> {
    if (!visible.value || saving.value || !scope.isActive()) return false
    const error = validateTargetDraft(draft)
    if (error) {
      Message.error(error)
      return false
    }
    const id = editingId.value,
      current = session,
      version = scope.snapshot()
    const payload = id === null ? targetPayload(draft) : { ...targetPayload(draft), id }
    saving.value = true
    emit('saving-change', id, true)
    try {
      const response = await (id === null
        ? postUserTestObject(payload)
        : putUserTestObject(payload))
      if (current !== session || !scope.current(version)) return false
      Message.success(response.msg)
      emit('saved')
      close()
      return true
    } catch {
      return false
    } finally {
      saving.value = false
      emit('saving-change', id, false)
    }
  }
  defineExpose({ open, close })
</script>
<style scoped>
  .mango-target-editor {
    padding: 0 4px;
  }
  .mango-target-editor__section {
    padding: 20px 0 4px;
    border-bottom: 1px solid var(--m-border);
  }
  .mango-target-editor__section:first-child {
    padding-top: 4px;
  }
  .mango-target-editor__section:last-child {
    border-bottom: 0;
  }
  .mango-target-editor__heading {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 8px 12px;
    margin-bottom: 20px;
  }
  .mango-target-editor__heading strong {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
  }
  .mango-target-editor__heading span {
    color: var(--m-muted);
    font-size: 13px;
  }
  .mango-target-editor__grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: 24px;
  }
  .mango-target-editor :deep(.arco-form-item) {
    margin-bottom: 16px;
  }
  .mango-target-editor :deep(.arco-form-item-label-col) {
    width: 112px !important;
    max-width: 112px !important;
    flex: 0 0 112px !important;
    padding-right: 12px;
  }
  .mango-target-editor :deep(.arco-form-item-wrapper-col) {
    min-width: 0;
    max-width: none !important;
    flex: 1 1 0 !important;
  }
  .mango-target-editor :deep(.arco-form-item-content-flex) {
    width: 100%;
  }
  @media (max-width: 760px) {
    .mango-target-editor__grid {
      grid-template-columns: minmax(0, 1fr);
    }
  }
</style>
