<template>
  <a-modal modal-class="mango-simple-form-modal" :visible="visible" title="重置密码" :width="560"
    ok-text="重置并发送" :ok-loading="submitting" :on-before-ok="confirm" @cancel="close" @update:visible="onVisibleChange">
    <a-form class="mango-simple-form" :model="{}" layout="horizontal" auto-label-width>
      <a-form-item class="mango-simple-form-item" label="登录邮箱">
        <a-input :model-value="username" disabled />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="发送方式">
        <span>系统生成随机密码并发送到你的登录邮箱，无需输入原密码。</span>
        <template #extra>重置成功后将退出登录，请使用邮件中的新密码重新登录。</template>
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
  import { onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { resetOwnPassword } from '@/api/user/user'
  import { reportLoadError } from '@/utils/load-error'
  import { successResponse } from '../records'

  const props = defineProps<{ username: string; requiresEmailMigration: boolean; contextVersion: number; isContextCurrent: (version: number) => boolean }>()
  const emit = defineEmits<{ (event: 'reset', version: number): void }>()
  const visible = ref(false), submitting = ref(false)
  let generation = 0, openedContext = 0, disposed = false
  const current = (window: number) => !disposed && visible.value && generation === window && props.isContextCurrent(openedContext)
  function open(): void {
    if (disposed || submitting.value || !props.isContextCurrent(props.contextVersion)) return
    if (props.requiresEmailMigration) {
      Message.warning('请先通过“修改密码”绑定登录邮箱，再重置密码')
      return
    }
    generation++; openedContext = props.contextVersion; visible.value = true
  }
  function close(): void { generation++; visible.value = false }
  function onVisibleChange(value: boolean): void { if (!value) close() }
  async function confirm(): Promise<boolean> {
    if (submitting.value || !current(generation) || props.requiresEmailMigration) return false
    const window = generation, version = openedContext
    submitting.value = true
    try {
      successResponse(await resetOwnPassword())
      if (!current(window)) return false
      close(); emit('reset', version)
      return true
    } catch (error) {
      if (current(window)) reportLoadError(error, '重置密码失败，请重试', false)
      return false
    } finally { submitting.value = false }
  }
  watch(() => props.contextVersion, close, { flush: 'sync' })
  onDeactivated(close)
  onBeforeUnmount(() => { disposed = true; close() })
  defineExpose({ open, close })
</script>
