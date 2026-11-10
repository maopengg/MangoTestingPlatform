<template>
  <a-modal modal-class="mango-simple-form-modal" v-model:visible="visible" title="设为定时任务" :width="560" :on-before-ok="save" :closable="!saving" :mask-closable="!saving" :cancel-button-props="{ disabled: saving }" @cancel="close">
    <a-alert v-if="error" type="error">{{ error }}</a-alert>
    
    <a-form auto-label-width class="mango-simple-form" :model="draft" :disabled="saving" layout="horizontal">
      <a-form-item class="mango-simple-form-item" label="项目产品" required><ProjectProductSelect v-model="draft.product" placeholder="请选择项目产品" @change="productChanged" /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="模块"><ProductModuleSelect v-model="draft.module" :project-product-id="draft.product" :disabled="caseOptionId(draft.product) === null" :auto-clear="false" :selectable-level="0" show-all-option placeholder="全部模块" @change="loadTasks()" /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="定时任务" required><a-select v-model="draft.task" :disabled="caseOptionId(draft.product) === null" :options="taskOptions" :field-names="fieldNames" :loading="optionsLoading" allow-search allow-clear placeholder="请选择定时任务进行绑定" /></a-form-item>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { fieldNames } from '@/setting'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { getSystemTasksName } from '@/api/system/tasks'
  import { postSystemTasksBatchSetCases } from '@/api/system/tasks_details'
  import { uiCaseAssetObject, requiredUiCaseAssetId, uiCaseAssetResponse } from '@/components/business/ui-case-step-create'
  import { useCaseListScope } from '../composables/useCaseListScope'
  import { caseOptionId, type CaseId, type CaseUserOption } from '../case-list-records'
  const emit = defineEmits<{ (event: 'saved'): void }>()
  const visible = ref(false), saving = ref(false), error = ref(''), optionsLoading = ref(false), optionsError = ref(''), taskOptions = ref<CaseUserOption[]>([])
  const draft = reactive<{ product: CaseId | CaseId[] | null; module: CaseId | null; task: CaseId | null }>({ product: null, module: '__all__', task: null })
  let ids: CaseId[] = [], session = 0, request = 0
  function close() { session++; request++; visible.value = false; optionsLoading.value = false; optionsError.value = ''; error.value = '' }
  const scope = useCaseListScope({ invalidate: close })
  function open(values: readonly CaseId[]) {
    if (saving.value || !scope.available() || !values.length) return
    close(); ids = [...new Set(values.map(requiredUiCaseAssetId))]; taskOptions.value = []; Object.assign(draft, { product: null, module: '__all__', task: null }); visible.value = true
  }
  function productChanged() { draft.module = '__all__'; void loadTasks() }
  async function loadTasks(): Promise<boolean> {
    const product = caseOptionId(draft.product), module = draft.module === '__all__' ? null : caseOptionId(draft.module)
    const sequence = ++request, version = session, valid = scope.capture(), signature = JSON.stringify([draft.product, draft.module])
    const current = () => valid() && visible.value && sequence === request && version === session && signature === JSON.stringify([draft.product, draft.module])
    draft.task = null; taskOptions.value = []; optionsError.value = ''; optionsLoading.value = false
    if (product === null || !current()) return false
    optionsLoading.value = true
    try {
      const values = uiCaseAssetResponse(await getSystemTasksName(product, module, 0))
      if (!current()) return false
      if (!Array.isArray(values)) throw Error('Invalid task options')
      taskOptions.value = values.map(value => { const row = uiCaseAssetObject(value); if (typeof row.title !== 'string') throw Error('Invalid task name'); return { key: requiredUiCaseAssetId(row.key), title: row.title } }); return true
    } catch (loadFailure0) { if (current()) (reportLoadError(loadFailure0, "定时任务加载失败，请重试", false), optionsError.value = '定时任务加载失败，请重试'); return false }
    finally { if (sequence === request) optionsLoading.value = false }
  }
  async function save(): Promise<boolean> {
    if (saving.value || !visible.value || !scope.available()) return false
    if (caseOptionId(draft.product) === null || draft.task === null || !taskOptions.value.some(item => String(item.key) === String(draft.task))) { error.value = '请选择项目产品和有效的定时任务'; return false }
    const valid = scope.capture(), version = session, current = () => valid() && version === session && visible.value, snapshot = [...ids], task = draft.task
    saving.value = true; error.value = ''
    try { uiCaseAssetResponse(await postSystemTasksBatchSetCases(snapshot, task, 0)); if (!current()) return false; Message.success('绑定成功'); emit('saved'); close(); return true }
    catch { if (current()) error.value = '绑定失败，当前选择已保留，请重试'; return false }
    finally { saving.value = false }
  }
  defineExpose({ open, close })
</script>
