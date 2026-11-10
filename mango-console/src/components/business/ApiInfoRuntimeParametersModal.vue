<template>
  <ModalDialog modal-class="mango-simple-form-modal" ref="modal" class="mango-runtime-parameters-dialog" title="填写运行变量" :width="560" confirm-text="执行"
    @confirm="confirm" @cancel="finish(null)">
    <template #content>
      <div class="mango-runtime-parameters">
        <div class="mango-runtime-parameters__hint">全部选填，仅本次运行生效；留空沿用原有替换逻辑，不修改接口和全局变量。</div>
        <a-form auto-label-width class="mango-runtime-parameters__form mango-simple-form" :model="{}" layout="horizontal"
          :label-col-props="{ span: 9 }" :wrapper-col-props="{ span: 15 }">
          <a-form-item class="mango-simple-form-item" v-for="row in rows" :key="row.name">
            <template #label>
              <span class="mango-runtime-parameters__label" :title="formatVariable(row.name)">{{ formatVariable(row.name) }}</span>
            </template>
            <a-textarea v-model="row.value" :aria-label="formatVariable(row.name)" placeholder="选填，输入本次运行值"
              :auto-size="{ minRows: 1, maxRows: 4 }" allow-clear />
          </a-form-item>
        </a-form>
      </div>
    </template>
  </ModalDialog>
</template>

<script setup lang="ts">
  import { onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
  import ModalDialog from '@/components/overlays/ModalDialog.vue'
  import { getApiInfoExecutionParameters } from '@/api/apitest/info'

  type Target = { id: number | string; revision_id?: number; release_id?: number }
  const modal = ref<InstanceType<typeof ModalDialog> | null>(null)
  const rows = ref<Array<{ name: string; value: string }>>([])
  let pending: ((value: Record<string, unknown> | null) => void) | null = null
  let requestVersion = 0

  function formatVariable(name: string) {
    return '${{' + name + '}}'
  }
  function finish(values: Record<string, unknown> | null) {
    const resolve = pending
    pending = null
    void modal.value?.close()
    rows.value = []
    resolve?.(values)
  }
  function confirm() {
    finish(Object.fromEntries(rows.value.filter(row => row.value !== '').map(row => [row.name, row.value])))
  }
  async function prepare(targets: Target[]): Promise<Record<string, unknown> | null> {
    finish(null)
    const version = ++requestVersion
    const snapshot = targets.map(target => ({ ...target }))
    const variables = new Set<string>()
    for (let index = 0; index < snapshot.length; index += 3) {
      const responses = await Promise.all(snapshot.slice(index, index + 3).map(target => getApiInfoExecutionParameters(target)))
      if (version !== requestVersion) return null
      for (const response of responses) {
        for (const name of response.data.variables) variables.add(name)
      }
    }
    if (!variables.size) return {}
    rows.value = Array.from(variables, name => ({ name, value: '' }))
    return new Promise(resolve => {
      pending = resolve
      void modal.value?.show()
    })
  }
  function cancel() { requestVersion++; finish(null) }
  onBeforeUnmount(cancel)
  onDeactivated(cancel)
  watch(() => modal.value?.showModal, shown => { if (shown === false && pending) finish(null) })
  defineExpose({ prepare, cancel })
</script>

<style scoped>
  .mango-runtime-parameters { display: flex; flex-direction: column; gap: 16px; }
  .mango-runtime-parameters__hint { color: var(--m-muted); font-size: 12px; line-height: 1.6; }
  .mango-runtime-parameters__form :deep(.arco-form-item) { margin-bottom: 12px; }
  .mango-runtime-parameters__form :deep(.arco-form-item:last-child) { margin-bottom: 0; }
  .mango-runtime-parameters__form :deep(.arco-form-item-label-col) { min-width: 0; text-align: left; }
  .mango-runtime-parameters__form :deep(.arco-form-item-label) { justify-content: flex-start; }
  .mango-runtime-parameters__form :deep(.arco-form-item-wrapper-col) { min-width: 0; }
  .mango-runtime-parameters__label {
    display: block;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-family: var(--m-font-mono, monospace);
    font-size: 12px;
  }
</style>

<style>
  .mango-runtime-parameters-dialog .mango-scrollbar,
  .mango-runtime-parameters-dialog .mango-scrollbar__wrap { height: auto; }
  .mango-runtime-parameters-dialog .mango-modal-dialog__wrap { max-height: 55vh; }
</style>
