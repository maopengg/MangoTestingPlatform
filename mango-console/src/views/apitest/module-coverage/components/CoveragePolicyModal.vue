<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    title="编辑覆盖策略"
    :width="560"
    :ok-loading="saving"
    :on-before-ok="save"
    :mask-closable="!saving"
    :closable="!saving"
    :esc-to-close="!saving"
    :cancel-button-props="{ disabled: saving }"
  >
    <a-form auto-label-width class="mango-simple-form" :model="form" layout="horizontal">
      <a-form-item class="mango-simple-form-item" label="当前接口">#{{ form.id }} · {{ form.name }}</a-form-item>
      <a-form-item class="mango-simple-form-item" label="覆盖策略" required>
        <a-select
          v-model="form.policy"
          :options="enumStore.module_coverage_policy"
          :field-names="{ value: 'key', label: 'title' }"
          :disabled="saving"
        />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="处理原因" :required="form.policy !== 'included'">
        <a-textarea
          v-model="form.reason"
          :max-length="2000"
          show-word-limit
          placeholder="暂不处理或排除覆盖时必填，说明依据及后续处理条件"
          :disabled="saving"
        />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="处理说明">{{ coveragePolicyHelp[form.policy] }}</a-form-item>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
  import { reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { updateCoverageInterfacePolicy } from '@/api/apitest/module-coverage'
  import { coveragePolicyHelp } from '../config'
  import { useCoveragePanelScope } from '../composables/useCoveragePanelScope'
  import type { CoverageRecord } from '../types'
  const emit = defineEmits<{ (event: 'saved'): void }>()
  const enumStore = useEnum(),
    visible = ref(false),
    saving = ref(false)
  const form = reactive({ id: 0, name: '', policy: 'included', reason: '' })
  const { begin, current, close } = useCoveragePanelScope(visible, () => {})
  let session = 0
  function open(row: CoverageRecord) {
    if (saving.value) return
    session = begin()
    Object.assign(form, {
      id: row.id,
      name: row.interface_name || row.url || '',
      policy: row.coverage_policy || 'included',
      reason: row.coverage_reason || '',
    })
    visible.value = true
  }
  async function save() {
    if (!visible.value || saving.value) return false
    if (form.policy !== 'included' && !form.reason.trim()) {
      Message.warning('暂不处理或排除覆盖时请填写处理原因')
      return false
    }
    const token = session,
      payload = { id: form.id, policy: form.policy, reason: form.reason.trim() }
    saving.value = true
    try {
      await updateCoverageInterfacePolicy([payload.id], payload.policy, payload.reason)
      if (!current(token)) return false
      Message.success('覆盖策略已更新')
      emit('saved')
      visible.value = false
      return true
    } catch {
      return false
    } finally {
      saving.value = false
    }
  }
  defineExpose({ open, close })
</script>
