<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    :title="editingId === null ? '新增页面' : '编辑页面'"
    :width="560"
    :on-before-ok="save"
    :closable="!saving"
    :mask-closable="!saving"
    :esc-to-close="!saving"
    :cancel-button-props="{ disabled: saving }"
    unmount-on-close
    @cancel="close"
  >
    <MangoRequestFeedback v-if="error" :message="(error)" />
    <a-form auto-label-width class="mango-simple-form" :model="draft" :disabled="saving" layout="horizontal">
      <a-form-item class="mango-simple-form-item" label="项目/产品" required
        ><ProjectProductSelect
          v-model="draft.project_product"
          placeholder="请选择项目/产品"
          @change="draft.module = null"
      /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="模块名称" required
        ><ProductModuleSelect
          v-model="draft.module"
          :project-product-id="draft.project_product"
          :auto-clear="false"
          :disabled="draft.project_product === null"
          placeholder="请选择测试模块"
      /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="页面名称" required
        ><a-input v-model="draft.name" placeholder="请输入页面名称"
      /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="页面地址" required
        ><a-input v-model="draft.url" placeholder="请输入页面地址"
      /></a-form-item>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
import { requestFailureMessage } from '@/utils/load-error'

  import { reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { postUiPage, putUiPage } from '@/api/uitest/page'
  import { useLiveWorkbenchScope } from '@/hooks/use-live-workbench-scope'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import {
    createPageDraft,
    pagePayload,
    pageResponse,
    readUiPage,
    type PageId,
    type PageDefaults,
    type UiPageRow,
  } from '../page-records'
  const emit = defineEmits<{
    (event: 'saved'): void
    (event: 'busy-change', value: boolean): void
  }>()
  const visible = ref(false),
    saving = ref(false),
    error = ref(''),
    editingId = ref<PageId | null>(null)
  const draft = reactive(createPageDraft())
  let session = 0
  function close() {
    session++
    visible.value = false
    error.value = ''
    editingId.value = null
    Object.assign(draft, createPageDraft())
  }
  const scope = useLiveWorkbenchScope(() => null, { invalidate: close, resume: () => {} })
  function open(record: UiPageRow | null = null, defaults: PageDefaults = {}) {
    if (saving.value || !scope.available()) return
    close()
    const row = record === null ? null : readUiPage(record)
    editingId.value = row?.id ?? null
    Object.assign(draft, createPageDraft(row, defaults))
    visible.value = true
  }
  async function save(): Promise<boolean> {
    if (saving.value || !visible.value || !scope.available()) return false
    let payload: ReturnType<typeof pagePayload>
    try {
      payload = pagePayload(draft, editingId.value)
    } catch (requestFailure) {
      error.value = requestFailureMessage(requestFailure, '请完整填写项目/产品、模块、页面名称和页面地址')
      return false
    }
    const valid = scope.capture(),
      version = session,
      current = () => valid() && version === session && visible.value
    const isAdd = editingId.value === null
    saving.value = true
    emit('busy-change', true)
    error.value = ''
    try {
      pageResponse(await (isAdd ? postUiPage(payload) : putUiPage(payload)))
      if (!current()) return false
      Message.success('保存成功')
      close()
      emit('saved')
      return true
    } catch (requestFailure) {
      if (current()) error.value = requestFailureMessage(requestFailure, '保存失败，草稿已保留，请重试')
      return false
    } finally {
      saving.value = false
      emit('busy-change', false)
    }
  }
  defineExpose({ open, close })
</script>
