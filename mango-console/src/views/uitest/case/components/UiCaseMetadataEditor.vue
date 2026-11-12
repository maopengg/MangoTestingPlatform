<template>
  <a-modal modal-class="mango-simple-form-modal" v-model:visible="visible" :title="editingId === null ? '新增用例' : '编辑用例'" :width="560" :on-before-ok="save" :closable="!saving" :mask-closable="!saving" :cancel-button-props="{ disabled: saving }" @cancel="close">
    <MangoRequestFeedback v-if="error" :message="(error)" />
    
    
    <a-form auto-label-width :model="draft" :disabled="saving" layout="horizontal" class="mango-ui-case-metadata-form mango-simple-form">
      <a-form-item class="mango-simple-form-item" label="项目/产品" required><ProjectProductSelect v-model="draft.project_product" placeholder="请选择项目产品" @change="draft.module = null" /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="模块" required><ProductModuleSelect v-model="draft.module" :project-product-id="draft.project_product" :auto-clear="false" placeholder="请选择模块" /></a-form-item>
      <a-form-item label="用例名称" required class="mango-ui-case-metadata-form__wide mango-simple-form-item"><a-input v-model="draft.name" placeholder="请输入用例名称" /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="优先级" required><a-select v-model="draft.level" :options="enumStore.case_level" :loading="enumsLoading" :field-names="fieldNames" placeholder="请选择优先级" /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="负责人" required><a-select v-model="draft.case_people" :options="userOptions" :loading="usersLoading" :field-names="fieldNames" allow-search placeholder="请选择负责人" /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="测试层级" required><a-select v-model="draft.scenario_layer" :options="enumStore.api_case_scenario_layer" :loading="enumsLoading" :field-names="fieldNames" /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="验证类型" required><a-select v-model="draft.scenario_type" :options="enumStore.api_case_scenario_type" :loading="enumsLoading" :field-names="fieldNames" /></a-form-item>
      <a-form-item label="执行场景" class="mango-ui-case-metadata-form__wide mango-simple-form-item"><a-select v-model="draft.scenario_tags" multiple allow-clear allow-search :options="enumStore.api_case_scenario_tag" :loading="enumsLoading" :field-names="fieldNames" placeholder="请选择执行场景" /></a-form-item>
      <a-form-item label="场景描述" class="mango-ui-case-metadata-form__wide mango-simple-form-item"><a-textarea v-model="draft.scenario_description" :auto-size="{ minRows: 3, maxRows: 5 }" placeholder="Given 前置条件&#10;When 用户执行某个行为&#10;Then 应得到某个结果" /></a-form-item>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
import { requestFailureMessage } from '@/utils/load-error'

  import { reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import { postUiCase, putUiCase } from '@/api/uitest/case'
  import { uiCaseAssetResponse } from '@/components/business/ui-case-step-create'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { useCaseListScope } from '../composables/useCaseListScope'
  import { createMetadataDraft, caseMetadataPayload, type UiCaseRow, type CaseId, type CaseUserOption } from '../case-list-records'
  withDefaults(defineProps<{ userOptions: CaseUserOption[]; usersLoading: boolean; usersError: string; enumsLoading?: boolean; enumsError?: string }>(), { enumsLoading: false, enumsError: '' })
  const emit = defineEmits<{ (event: 'saved'): void; (event: 'retry-users'): void; (event: 'retry-enums'): void }>()
  const enumStore = useEnum(), visible = ref(false), saving = ref(false), error = ref(''), editingId = ref<CaseId | null>(null)
  const draft = reactive(createMetadataDraft())
  let session = 0
  function close() { session++; visible.value = false; error.value = '' }
  const scope = useCaseListScope({ invalidate: close })
  function open(record: UiCaseRow | null = null, defaults: Parameters<typeof createMetadataDraft>[1] = {}) {
    if (saving.value || !scope.available()) return
    close(); editingId.value = record?.id ?? null; Object.assign(draft, createMetadataDraft(record, defaults)); visible.value = true
  }
  async function save(): Promise<boolean> {
    if (saving.value || !visible.value || !scope.available()) return false
    const valid = scope.capture(), version = session, id = editingId.value, current = () => valid() && version === session && visible.value
    let payload: ReturnType<typeof caseMetadataPayload>
    try { payload = caseMetadataPayload(draft, id) } catch (requestFailure) { error.value = requestFailureMessage(requestFailure, '请完整填写项目产品、模块、名称、优先级和负责人'); return false }
    saving.value = true; error.value = ''
    try {
      uiCaseAssetResponse(await (id === null ? postUiCase(payload) : putUiCase(payload)))
      if (!current()) return false
      Message.success('保存成功'); emit('saved'); close(); return true
    } catch (requestFailure) { if (current()) error.value = requestFailureMessage(requestFailure, '保存失败，草稿已保留，请重试'); return false }
    finally { saving.value = false }
  }
  defineExpose({ open, close })
</script>
<style scoped>
  .mango-ui-case-metadata-form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 16px; }
  .mango-ui-case-metadata-form__wide { grid-column: 1 / -1; }
</style>
