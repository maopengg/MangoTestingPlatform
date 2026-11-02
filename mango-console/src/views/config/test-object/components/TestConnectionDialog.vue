<template>
  <ModalDialog
    ref="dialog"
    title="测试服务器连通性"
    width="min(560px, calc(100vw - 32px))"
    @confirm="runTest"
    @cancel="reset"
  >
    <template #content>
      <div class="mango-target-probe">
        <p class="mango-target-probe__hint">从平台服务器检测 DNS 与 TCP 端口，不发送业务请求或验证登录态。</p>
        <a-form :model="{ address }" layout="horizontal">
          <a-form-item label="被测地址">
            <a-select v-model="address" :disabled="loading" @change="result = null; error = ''">
              <a-option v-for="option in options" :key="option.value" :value="option.value">
                {{ option.label }} · {{ option.value }}
              </a-option>
            </a-select>
          </a-form-item>
        </a-form>
        <div v-if="result" class="mango-target-probe__result" role="status">
          <a-tag class="mango-target-probe__status" :class="{ 'mango-target-probe__status--success': result.connected }" size="small">{{ result.connected ? '连接成功' : '连接失败' }}</a-tag>
          <span>{{ result.message }}</span>
          <dl>
            <dt>目标端口</dt><dd>{{ result.host }}:{{ result.port }}</dd>
            <dt>解析地址</dt><dd>{{ result.resolved_ips.join('、') || '—' }}</dd>
            <dt>检测耗时</dt><dd>{{ result.elapsed_ms }} ms</dd>
          </dl>
        </div>
        <p v-if="error" class="mango-target-probe__error" role="alert">{{ error }}</p>
      </div>
    </template>
    <template #footer>
        <div class="mango-modal-dialog-footer-actions">
          <a-button size="small" @click="close">关闭</a-button>
          <a-button  type="primary" size="small" :loading="loading" :disabled="!address" @click="runTest">测试</a-button>
        </div>
    </template>
  </ModalDialog>
</template>

<script setup lang="ts">
  import { onBeforeUnmount, ref } from 'vue'
  import ModalDialog from '@/components/overlays/ModalDialog.vue'
  import { testObjectConnection, type TestObjectProbeResult } from '@/api/system/test_object'
  import type { ModalDialogType } from '@/types/components'

  const dialog = ref<ModalDialogType | null>(null)
  const options = ref<Array<{ label: string; value: string }>>([])
  const address = ref('')
  const objectId = ref(0)
  const loading = ref(false)
  const result = ref<TestObjectProbeResult | null>(null)
  const error = ref('')
  let requestVersion = 0

  function reset() {
    requestVersion += 1
    loading.value = false
    result.value = null
    error.value = ''
  }

  function open(record: { id: number; network_test_addresses: Array<{ label: string; value: string }> }) {
    reset()
    objectId.value = record.id
    options.value = record.network_test_addresses || []
    address.value = options.value[0]?.value || ''
    dialog.value?.show()
  }

  function close() {
    reset()
    dialog.value?.close()
  }

  async function runTest() {
    if (loading.value || !address.value) return
    const version = ++requestVersion
    loading.value = true
    result.value = null
    error.value = ''
    try {
      const response = await testObjectConnection(objectId.value, address.value)
      if (version === requestVersion) result.value = response.data as TestObjectProbeResult
    } catch {
      if (version === requestVersion) error.value = '检测请求失败，请检查操作权限或稍后重试。'
    } finally {
      if (version === requestVersion) {
        loading.value = false
        dialog.value?.setConfirmLoading(false)
      }
    }
  }

  onBeforeUnmount(reset)
  defineExpose({ open })
</script>

<style scoped>
  .mango-target-probe { display: grid; gap: var(--m-page-gap); min-width: 0; }
  .mango-target-probe__hint { margin: 0; color: var(--m-muted); }
  .mango-target-probe__result { color: var(--m-text); overflow-wrap: anywhere; }
  .mango-target-probe__result dl { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 8px 12px; }
  .mango-target-probe__result dt { color: var(--m-muted); }
  .mango-target-probe__result dd { margin: 0; }
  .mango-target-probe__error { margin: 0; color: var(--m-danger); }
  .mango-target-probe__status { color: var(--m-danger); background: var(--m-surface); }
  .mango-target-probe__status--success { color: var(--m-success); }
</style>
