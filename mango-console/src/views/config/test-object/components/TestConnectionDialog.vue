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
        <p class="mango-target-probe__hint"
          >从平台服务器检测 DNS 与 TCP 端口，不发送业务请求或验证登录态。</p
        >
        <a-form
          :model="{ address }"
          layout="horizontal"
          size="small"
          class="mango-target-probe__form"
        >
          <a-form-item label="被测地址">
            <a-select
              v-model="address"
              :disabled="loading"
              placeholder="请选择被测地址"
              @change="clearResult"
            >
              <a-option
                v-for="option in options"
                :key="option.value"
                :value="option.value"
                :label="option.label"
              >
                {{ option.label }} · {{ option.value }}
              </a-option>
            </a-select>
          </a-form-item>
        </a-form>
        <p v-if="address" class="mango-target-probe__address">{{ address }}</p>
        <div v-if="result" class="mango-target-probe__result" role="status">
          <a-alert
            :type="result.connected ? 'success' : 'error'"
            :title="result.connected ? '连接成功' : '连接失败'"
            class="mango-target-probe__summary"
          >
            {{ result.message }}
          </a-alert>
          <dl class="mango-target-probe__details">
            <dt>检测目标</dt><dd>{{ result.host }}:{{ result.port }}</dd> <dt>解析地址</dt
            ><dd>{{ result.resolved_ips.join('、') || '—' }}</dd> <dt>检测耗时</dt
            ><dd>{{ result.elapsed_ms }} ms</dd>
          </dl>
        </div>
        <a-alert v-if="error" type="error" role="alert">{{ error }}</a-alert>
      </div>
    </template>
    <template #footer>
      <a-space class="mango-modal-dialog-footer-actions">
        <a-button size="small" @click="close">关闭</a-button>
        <a-button
          type="primary"
          size="small"
          :loading="loading"
          :disabled="!address"
          @click="runTest"
          >测试</a-button
        >
      </a-space>
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

  function clearResult() {
    result.value = null
    error.value = ''
  }

  function reset() {
    requestVersion += 1
    loading.value = false
    result.value = null
    error.value = ''
  }

  function open(record: {
    id: number
    network_test_addresses: Array<{ label: string; value: string }>
  }) {
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
  .mango-target-probe {
    display: grid;
    gap: var(--m-space-lg);
    min-width: 0;
    font-size: var(--m-font-body);
    line-height: 1.6;
  }
  .mango-target-probe__hint {
    margin: 0;
    color: var(--m-text-2);
    font-size: var(--m-font-caption);
  }
  .mango-target-probe__form :deep(.arco-form-item) {
    margin-bottom: 0;
  }
  .mango-target-probe__address {
    margin: calc(-1 * var(--m-space-sm)) 0 0;
    padding: var(--m-space-sm) var(--m-card-padding);
    background: var(--m-surface-soft);
    border-radius: var(--m-radius-sm);
    color: var(--m-text-2);
    font-size: var(--m-font-caption);
    overflow-wrap: anywhere;
  }
  .mango-target-probe__result {
    display: grid;
    gap: var(--m-space-lg);
    min-width: 0;
    color: var(--m-text);
    overflow-wrap: anywhere;
  }
  .mango-target-probe__summary {
    align-items: flex-start;
  }
  .mango-target-probe__summary :deep(.arco-alert-title) {
    font-size: var(--m-font-body);
    font-weight: 600;
  }
  .mango-target-probe__details {
    display: grid;
    grid-template-columns: 72px minmax(0, 1fr);
    gap: var(--m-space-md) var(--m-space-lg);
    margin: 0;
    padding-top: var(--m-space-md);
    border-top: 1px solid var(--m-border);
  }
  .mango-target-probe__details dt {
    color: var(--m-text-2);
  }
  .mango-target-probe__details dd {
    margin: 0;
    min-width: 0;
    font-variant-numeric: tabular-nums;
  }
</style>
