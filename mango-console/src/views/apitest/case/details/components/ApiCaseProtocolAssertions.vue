<template>
  <div class="mango-protocol-assertions" :aria-busy="saving" @mouseleave="leave">
    <TipMessage message="默认跟随系统；选择自定义后，勾选本场景需要的检查项。" />
    <a-form :model="form" layout="horizontal" auto-label-width>
      <a-form-item label="配置来源">
        <a-select v-model="form.source" :options="sourceOptions" :disabled="editLocked || saving" :loading="saving" @popup-visible-change="popupChange" />
      </a-form-item>
      <a-form-item v-if="form.source === 'custom'" label="协议断言检查项">
        <a-cascader
          v-model="form.checks"
          multiple allow-clear allow-search
          expand-trigger="click"
          :path-mode="false"
          :check-strictly="false"
          :max-tag-count="2"
          :options="checkOptions"
          :disabled="editLocked || saving"
          :loading="saving"
          placeholder="先选择协议类型，再选择默认断言场景"
          @popup-visible-change="popupChange"
        />
      </a-form-item>
      <a-alert v-if="form.source === 'legacy'">当前保留旧场景预期：{{ value?.mode }}，状态码 {{ (value?.status_codes || []).join(',') || '未指定' }}。选择跟随系统或自定义并保存后才会替换，不会自动修改。</a-alert>
    </a-form>
  </div>
</template>
<script setup lang="ts">
  import { computed, reactive, watch, nextTick } from 'vue'
  import { useEnum } from '@/store/modules/get-enum'
  import TipMessage from '@/components/feedback/TipMessage.vue'
  import { buildDefaultAssertionOptions } from '@/views/system/settings/config'
  import { protocolAssertionSourceOptions } from './protocol-assertions'
  import type { ApiProtocolExpectation } from '@/types/api-test/case-parameter'

  const props = defineProps<{scenarioId: number; value?: ApiProtocolExpectation; editLocked: boolean; saving: boolean}>()
  const emit = defineEmits<{(event: 'save', value: ApiProtocolExpectation): void}>()
  const enums = useEnum()
  const checkOptions = computed(() => buildDefaultAssertionOptions(enums.api_default_assertion_check || []))
  const legacy = computed(() => props.value?.inherit_system === undefined && Boolean(props.value?.mode && props.value.mode !== 'auto'))
  const baselineSource = computed(() => legacy.value ? 'legacy' : props.value?.inherit_system === false ? 'custom' : 'system')
  const sourceOptions = computed(() => legacy.value ? [...protocolAssertionSourceOptions, {label: '保留旧场景预期', value: 'legacy'}] : protocolAssertionSourceOptions)
  const form = reactive({source: 'system', checks: [] as string[]})
  let popupOpen = false
  let saveAfterPopup = false
  watch(() => [props.scenarioId, props.value] as const, () => {
    form.source = baselineSource.value
    form.checks = [...(props.value?.checks || [])]
    popupOpen = false
    saveAfterPopup = false
  }, {immediate: true})
  const changed = computed(() => form.source !== baselineSource.value
    || (form.source === 'custom' && JSON.stringify([...form.checks].sort()) !== JSON.stringify([...(props.value?.checks || [])].sort())))
  function save() {
    if (props.editLocked || props.saving || !changed.value || form.source === 'legacy') return
    emit('save', {mode: 'auto', status_codes: [], inherit_system: form.source === 'system', checks: form.source === 'system' ? [] : [...form.checks]})
  }
  function leave() {
    if (popupOpen) { saveAfterPopup = true; return }
    save()
  }
  async function popupChange(visible: boolean) {
    popupOpen = visible
    if (!visible && saveAfterPopup) {
      saveAfterPopup = false
      await nextTick()
      if (!popupOpen) save()
    }
  }
</script>
<style scoped>
  .mango-protocol-assertions { display: flex; flex-direction: column; gap: var(--m-page-gap); padding: var(--m-page-gap); }
  .mango-protocol-assertions :deep(.arco-alert) { margin-bottom: var(--m-page-gap); }
</style>
