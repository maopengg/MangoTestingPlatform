<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    :title="editingId === null ? '添加' : '编辑'"
    :width="560"
    :on-before-ok="save"
    :closable="!saving"
    :mask-closable="!saving"
    :esc-to-close="!saving"
    :cancel-button-props="{ disabled: saving }"
    unmount-on-close
    @cancel="close"
  >
    <a-form auto-label-width class="mango-simple-form" :model="draft" :disabled="saving" layout="horizontal">
      <a-form-item class="mango-simple-form-item"
        v-for="item of noticeFields"
        :key="item.key"
        :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
        :label="item.label"
      >
        <template v-if="item.type === 'input'">
          <a-input v-model="draft[item.key]" :placeholder="item.placeholder" />
        </template>
        <template v-else-if="item.type === 'textarea'">
          <a-textarea
            v-model="draft[item.key]"
            :auto-size="{ minRows: 2, maxRows: 3 }"
            :placeholder="item.placeholder"
          />
        </template>
        <template v-else-if="item.type === 'input-tag'">
          <a-input-tag v-model="draft[item.key]" :placeholder="item.placeholder" allow-clear />
        </template>
      </a-form-item>
    </a-form> </a-modal
></template>
<script setup lang="ts">
  import { reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { postSystemNotice, putSystemNotice } from '@/api/system/notice_group'
  import { noticeFields } from '../config'
  import { createNoticeDraft, noticePayload } from '../form'
  import { useNoticeScope } from '../composables/useNoticeScope'
  import type { NoticeRecord } from '../types'
  const props = defineProps<{ projectId: number | null }>()
  const emit = defineEmits<{
    (event: 'saved'): void
    (event: 'saving-change', id: number | null, pending: boolean): void
  }>()
  const visible = ref(false),
    saving = ref(false),
    editingId = ref<number | null>(null)
  const draft = reactive(createNoticeDraft())
  let session = 0
  const scope = useNoticeScope(() => [props.projectId], close)
  function open(record?: NoticeRecord) {
    if (saving.value || !scope.isActive() || props.projectId === null) return
    ++session
    editingId.value = record?.id ?? null
    Object.assign(draft, createNoticeDraft(record))
    visible.value = true
  }
  function close() {
    ++session
    visible.value = false
  }
  async function save(): Promise<boolean> {
    if (!visible.value || saving.value || !scope.isActive() || props.projectId === null)
      return false
    if (!draft.name) {
      Message.error('请输入通知组名称')
      return false
    }
    const current = session,
      version = scope.snapshot(),
      id = editingId.value,
      payload =
        id === null
          ? { ...noticePayload(draft), project: props.projectId }
          : { ...noticePayload(draft), id }
    saving.value = true
    emit('saving-change', id, true)
    try {
      const response = await (id === null ? postSystemNotice(payload) : putSystemNotice(payload))
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
