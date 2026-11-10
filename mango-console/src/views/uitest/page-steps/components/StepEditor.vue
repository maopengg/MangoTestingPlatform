<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    :title="editingId === null ? '新增页面步骤' : '编辑页面步骤'"
    :width="560"
    :on-before-ok="save"
    :closable="!saving"
    :mask-closable="!saving"
    :esc-to-close="!saving"
    :cancel-button-props="{ disabled: saving }"
    unmount-on-close
    @cancel="close"
  >
    <a-alert v-if="error" type="error">{{ error }}</a-alert>
    
    <a-form auto-label-width class="mango-simple-form" :model="draft" :disabled="saving" layout="horizontal">
      <a-form-item class="mango-simple-form-item" label="项目/产品" required
        ><ProjectProductSelect
          v-model="draft.project_product"
          placeholder="请选择项目/产品"
          @change="changeProduct"
      /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="模块名称" required
        ><ProductModuleSelect
          v-model="draft.module"
          :project-product-id="draft.project_product"
          :auto-clear="false"
          :disabled="draft.project_product === null"
          placeholder="请选择模块"
          @change="changeModule"
      /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="所属页面" required
        ><a-select
          v-model="draft.page"
          :options="pageOptions"
          :field-names="fieldNames"
          :loading="pagesLoading"
          :disabled="draft.module === null || pagesLoading"
          placeholder="请选择所属页面"
          allow-clear
          allow-search
      /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="步骤名称" required
        ><a-input v-model="draft.name" placeholder="请输入步骤名称"
      /></a-form-item>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { postUiSteps, putUiSteps } from '@/api/uitest/page-steps'
  import { getUiPageName } from '@/api/uitest/page'
  import { fieldNames } from '@/setting'
  import { useLiveWorkbenchScope } from '@/hooks/use-live-workbench-scope'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import {
    createStepDraft,
    readStepListRow,
    readStepOptions,
    stepListPayload,
    stepListResponse,
    stepOptionId,
    type StepDefaults,
    type StepListId,
    type StepListRow,
    type StepOption,
  } from '../step-list-records'
  const emit = defineEmits<{
    (event: 'saved'): void
    (event: 'reconcile'): void
    (event: 'busy-change', value: boolean): void
  }>()
  const visible = ref(false),
    saving = ref(false),
    editingId = ref<StepListId | null>(null),
    error = ref('')
  const draft = reactive(createStepDraft())
  const pageOptions = ref<StepOption[]>([]),
    pagesLoading = ref(false),
    pagesError = ref('')
  let session = 0,
    pageSequence = 0
  function close() {
    session++
    pageSequence++
    visible.value = false
    editingId.value = null
    Object.assign(draft, createStepDraft())
    pageOptions.value = []
    pagesLoading.value = false
    pagesError.value = error.value = ''
  }
  const scope = useLiveWorkbenchScope(() => null, { invalidate: close, resume: () => {} })
  async function loadPages() {
    const module = stepOptionId(draft.module),
      product = stepOptionId(draft.project_product)
    const valid = scope.capture(),
      version = session,
      request = ++pageSequence
    const current = () =>
      valid() && visible.value && version === session && request === pageSequence
    if (!current()) return
    pageOptions.value = []
    pagesError.value = ''
    if (module === null || product === null) {
      pagesLoading.value = false
      return
    }
    pagesLoading.value = true
    try {
      const options = readStepOptions(await getUiPageName(module, product))
      if (current()) pageOptions.value = options
    } catch (loadFailure0) {
      if (current()) (reportLoadError(loadFailure0, "所属页面加载失败，请重试", false), pagesError.value = '所属页面加载失败，请重试')
    } finally {
      if (current()) pagesLoading.value = false
    }
  }
  function changeProduct() {
    draft.module = null
    draft.page = null
    void loadPages()
  }
  function changeModule() {
    draft.page = null
    void loadPages()
  }
  function open(value: StepListRow | null = null, defaults: StepDefaults = {}) {
    if (saving.value || !scope.available()) return
    close()
    const row = value === null ? null : readStepListRow(value)
    editingId.value = row?.id ?? null
    Object.assign(draft, createStepDraft(row, defaults))
    visible.value = true
    // Keep the selected label visible while its independent options are loading.
    void loadPages()
    if (row?.page) pageOptions.value = [{ key: row.page.id, title: row.page.name }]
  }
  async function save(): Promise<boolean> {
    if (saving.value || !visible.value || !scope.available()) return false
    let payload: ReturnType<typeof stepListPayload>
    try {
      payload = stepListPayload(draft, editingId.value)
    } catch {
      error.value = '请完整填写项目/产品、模块、所属页面和步骤名称'
      return false
    }
    const valid = scope.capture(),
      version = session,
      add = editingId.value === null
    const current = () => valid() && version === session && visible.value
    saving.value = true
    error.value = ''
    emit('busy-change', true)
    try {
      stepListResponse(await (add ? postUiSteps(payload) : putUiSteps(payload)))
      if (!current()) {
        if (scope.available()) emit('reconcile')
        return false
      }
      Message.success('保存成功')
      close()
      emit('saved')
      return true
    } catch {
      if (current()) error.value = '保存失败，草稿已保留，请重试'
      return false
    } finally {
      saving.value = false
      emit('busy-change', false)
    }
  }
  defineExpose({ open, close })
</script>
