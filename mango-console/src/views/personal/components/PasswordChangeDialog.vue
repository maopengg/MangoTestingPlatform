<template>
  <a-modal modal-class="mango-simple-form-modal" :visible="visible" title="修改密码" :width="560" :ok-loading="submitting" :on-before-ok="confirm" @cancel="close" @update:visible="onVisibleChange">
    <a-form class="mango-simple-form" ref="formRef" :model="draft" layout="horizontal" auto-label-width :disabled="submitting">
      <a-form-item v-for="field of visibleFields" :key="field.key" :field="field.key" :label="field.label" class="mango-form-item__require mango-simple-form-item" :rules="[{ required: true, message: field.placeholder }]">
        <a-input v-if="field.key === 'email'" v-model="draft.email" :placeholder="field.placeholder" allow-clear />
        <a-input-password v-else v-model="draft[field.key]" :placeholder="field.placeholder" allow-clear />
        <template v-if="field.key === 'email' || field.key === 'new_password'" #extra>
          <span v-if="field.key === 'email'">修改成功后，原账号将停用，请使用该邮箱登录。</span>
          <span v-else>至少8位，并包含大写字母、小写字母、数字和特殊字符。</span>
        </template>
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
  import { computed, nextTick, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message, type FormInstance } from '@arco-design/web-vue'
  import { postUserPassword } from '@/api/user/user'
  import { passwordFields } from '../config'
  import { passwordDraft, passwordPayload, successResponse } from '../records'

  const props = defineProps<{ userId: number; requiresEmailMigration: boolean; contextVersion: number; isContextCurrent: (version: number) => boolean }>()
  const emit = defineEmits<{ (event: 'changed', version: number): void }>()
  const visible = ref(false), submitting = ref(false), formRef = ref<FormInstance | null>(null)
  const draft = reactive(passwordDraft())
  const visibleFields = computed(() => passwordFields.filter(field => field.key !== 'email' || props.requiresEmailMigration))
  let generation = 0, openedContext = 0, disposed = false
  const current = (window: number) => !disposed && visible.value && generation === window && props.isContextCurrent(openedContext)
  function open(): void {
    if (disposed || submitting.value || !props.isContextCurrent(props.contextVersion)) return
    const window = ++generation
    openedContext = props.contextVersion
    Object.assign(draft, passwordDraft())
    visible.value = true
    void nextTick(() => { if (current(window)) formRef.value?.clearValidate() })
  }
  function close(): void { generation++; visible.value = false; Object.assign(draft, passwordDraft()) }
  function onVisibleChange(value: boolean): void { if (!value) close() }
  async function confirm(): Promise<boolean> {
    if (submitting.value || !current(generation) || !formRef.value) return false
    const window = generation, version = openedContext
    submitting.value = true
    try {
      let payload: ReturnType<typeof passwordPayload>
      try { payload = passwordPayload(draft, props.userId, props.requiresEmailMigration) }
      catch (error) { Message.warning(error instanceof Error ? error.message : '请检查密码输入'); return false }
      const errors = await formRef.value.validate()
      if (errors || !current(window)) return false
      successResponse(await postUserPassword(payload))
      if (!current(window)) return false
      close()
      emit('changed', version)
      return true
    } catch {
      if (current(window)) Message.error('密码修改失败，请重试')
      return false
    } finally { submitting.value = false }
  }
  watch(() => props.contextVersion, close, { flush: 'sync' })
  onDeactivated(close)
  onBeforeUnmount(() => { disposed = true; close() })
  defineExpose({ open, close })
</script>
