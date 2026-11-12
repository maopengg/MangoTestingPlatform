<template>
  <a-modal modal-class="mango-simple-form-modal" v-model:visible="visible" title="测试服务器连通性" :width="560" @cancel="close">
    <div class="mango-target-probe">
      <p class="mango-target-probe__hint"
        >从平台服务器检测 DNS 与 TCP 端口，不发送业务请求或验证登录态。</p
      >
      <a-form auto-label-width
        :model="{ address }"
        layout="horizontal"
        size="small"
        class="mango-target-probe__form mango-simple-form"
      >
        <a-form-item class="mango-simple-form-item" label="被测地址">
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
      <MangoRequestFeedback v-if="error" :message="(error)" />
    </div>
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
  </a-modal>
</template>

<script setup lang="ts">
import { requestFailureMessage } from '@/utils/load-error'

  import { ref } from 'vue'
  import { testObjectConnection, type TestObjectProbeResult } from '@/api/system/test_object'
  import { useTestObjectScope } from '../composables/useTestObjectScope'
  import type { ProbeAddress, TestObjectRecord } from '../types'
  const emit = defineEmits<{ (event: 'testing-change', id: number, pending: boolean): void }>()
  const visible = ref(false)
  const options = ref<ProbeAddress[]>([])
  const address = ref('')
  const objectId = ref<number | null>(null)
  const loading = ref(false)
  const result = ref<TestObjectProbeResult | null>(null)
  const error = ref('')
  let requestVersion = 0
  const scope = useTestObjectScope(close)
  function clearResult() {
    ++requestVersion
    result.value = null
    error.value = ''
  }
  function open(record: TestObjectRecord) {
    if (loading.value || !scope.isActive()) return
    close()
    objectId.value = record.id
    options.value = (record.network_test_addresses || []).map((option) => ({
      label: option.label,
      value: option.value,
    }))
    address.value = options.value[0]?.value || ''
    visible.value = true
  }
  function close() {
    clearResult()
    visible.value = false
    objectId.value = null
    address.value = ''
    options.value = []
  }
  async function runTest() {
    if (
      !visible.value ||
      loading.value ||
      objectId.value === null ||
      !address.value ||
      !scope.isActive()
    )
      return
    const id = objectId.value,
      selectedAddress = address.value,
      version = ++requestVersion,
      context = scope.snapshot()
    loading.value = true
    result.value = null
    error.value = ''
    emit('testing-change', id, true)
    try {
      const response = await testObjectConnection(id, selectedAddress)
      if (version === requestVersion && scope.current(context) && address.value === selectedAddress)
        result.value = response.data
    } catch (requestFailure) {
      if (version === requestVersion && scope.current(context))
        error.value = requestFailureMessage(requestFailure, '检测请求失败，请检查操作权限或稍后重试。')
    } finally {
      loading.value = false
      emit('testing-change', id, false)
    }
  }
  defineExpose({ open, close })
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
