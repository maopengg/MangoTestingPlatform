<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    title="编辑"
    :width="560"
    :on-before-ok="save"
    :closable="!saving"
    :mask-closable="!saving"
    :esc-to-close="!saving"
    :cancel-button-props="{ disabled: saving }"
    unmount-on-close
    @cancel="close"
  >
    <a-form auto-label-width class="mango-simple-form" :model="draft" layout="horizontal" :disabled="saving">
      <a-form-item label="项目/产品" class="mango-form-item__require mango-simple-form-item">
        <ProjectProductSelect
          v-model="draft.project_product"
          :disabled="saving"
          placeholder="请选择项目产品"
        />
      </a-form-item>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
  import { reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { putUserFile } from '@/api/system/file_data'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import { createFileDraft, productId } from '../file'
  import { useTestFileScope } from '../composables/useTestFileScope'
  import type { TestFileRecord } from '../types'
  const emit = defineEmits<{
    (event: 'saved'): void
    (event: 'saving-change', id: number, pending: boolean): void
  }>()
  const visible = ref(false),
    saving = ref(false),
    editingId = ref<number | null>(null)
  const draft = reactive(createFileDraft())
  let session = 0
  const scope = useTestFileScope(close)
  function open(record: TestFileRecord) {
    if (saving.value || !scope.isActive()) return
    ++session
    editingId.value = record.id
    Object.assign(draft, createFileDraft(record))
    visible.value = true
  }
  function close() {
    ++session
    visible.value = false
    editingId.value = null
    Object.assign(draft, createFileDraft())
  }
  async function save(): Promise<boolean> {
    if (!visible.value || saving.value || editingId.value === null || !scope.isActive())
      return false
    const product = productId(draft.project_product)
    if (product === null) {
      Message.error('请选择项目产品')
      return false
    }
    const id = editingId.value,
      current = session,
      version = scope.snapshot()
    const payload = { id, project_product: product }
    saving.value = true
    emit('saving-change', id, true)
    try {
      const response = await putUserFile(payload)
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
