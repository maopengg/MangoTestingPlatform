<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    :title="editingId === null ? '新增' : '编辑'"
    :width="560"
    :on-before-ok="save"
    :closable="!saving"
    :mask-closable="!saving"
    :cancel-button-props="{ disabled: saving }"
    @cancel="close"
  >
    <a-form auto-label-width class="mango-simple-form" :model="draft" :disabled="saving" layout="horizontal">
      <a-form-item class="mango-simple-form-item"
        v-for="item of formItems"
        :key="item.key"
        :label="item.label"
        :class="item.required ? 'mango-form-item__require' : 'mango-form-item__no_require'"
      >
        <ProjectProductSelect
          v-if="item.type === 'cascader'"
          v-model="item.value"
          :disabled="saving"
          :placeholder="item.placeholder"
        />
        <a-textarea
          v-else-if="item.type === 'textarea'"
          v-model="item.value"
          :auto-size="{ minRows: 3, maxRows: 5 }"
          :placeholder="item.placeholder"
        />
        <a-input
          v-else
          v-model="item.value"
          :max-length="item.maxLength"
          :placeholder="item.placeholder"
        />
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
  import { onBeforeUnmount, onDeactivated, reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import { postApiHeaders, putApiHeaders } from '@/api/apitest/headers'
  import { createFormItems } from '../config'
  import { createHeaderDraft, headerPayload } from '../form'
  import type { HeaderDraft, HeaderEntityId, HeaderRecord } from '../types'

  const emit = defineEmits<{ (event: 'saved'): void }>()
  const visible = ref(false)
  const saving = ref(false)
  const editingId = ref<number | null>(null)
  const draft = reactive(createHeaderDraft())
  const formItems = createFormItems()
  let session = 0

  for (const item of formItems) {
    const key = item.key as keyof HeaderDraft
    Object.defineProperty(item, 'value', {
      enumerable: true,
      get: () => draft[key],
      set: (value) => Object.assign(draft, { [key]: value }),
    })
  }

  function open(record?: HeaderRecord, product: HeaderEntityId | null = null) {
    if (saving.value) return
    session++
    editingId.value = record?.id ?? null
    Object.assign(draft, createHeaderDraft(record, product))
    visible.value = true
  }

  function close() {
    session++
    visible.value = false
  }

  async function save(): Promise<boolean> {
    if (
      saving.value ||
      !visible.value ||
      !formItems.every((item) => !item.validator || item.validator())
    )
      return false
    const token = session,
      id = editingId.value,
      payload = headerPayload(draft)
    saving.value = true
    try {
      const response = await (id === null
        ? postApiHeaders(payload)
        : putApiHeaders({ ...payload, id }))
      if (token !== session) return false
      Message.success(response.msg)
      emit('saved')
      close()
      return true
    } catch {
      return false
    } finally {
      saving.value = false
    }
  }

  onBeforeUnmount(close)
  onDeactivated(close)
  defineExpose({ open, close })
</script>
