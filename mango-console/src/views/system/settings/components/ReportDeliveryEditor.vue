<template>
  <div class="mango-report-delivery">
    <a-spin :loading="metadataLoading">
      <a-alert v-if="metadataError" type="error">配置选项加载失败，请重新加载此页。</a-alert>
      <template v-else>
        <div v-for="field in REPORT_DELIVERY_FIELDS" :key="field.key" class="mango-system-settings__row">
          <div class="mango-system-settings__label-wrap"><span class="mango-system-settings__label">{{ field.label }}</span></div>
          <div class="mango-system-settings__type"><a-tag v-if="field.type !== 'text'" size="small">普通配置</a-tag></div>
          <div class="mango-system-settings__control">
            <a-switch v-if="field.type === 'switch'"  v-model="draft[field.key]" :loading="loading" :disabled="loading" :aria-label="field.label" size="medium" @change="save" />
            <a-input-number v-else-if="field.type === 'number'"  v-model="draft[field.key]" class="mango-system-settings__input mango-system-settings__input--number" :disabled="loading" :aria-label="field.label" :min="300" :max="604800" :precision="0" size="medium" @blur="save" @press-enter="save" />
            <span v-else>{{ field.text }}</span>
          </div>
        </div>
        <div class="mango-system-settings__row">
          <div class="mango-system-settings__control">
            <a-button  size="small" :loading="sampling" @click="sample">下载 HTML</a-button>
            <span v-if="loading" role="status">正在保存…</span>
          </div>
        </div>
      </template>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
  import { onMounted, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { downloadSampleReport, getReportDeliveryMetadata } from '@/api/system/offline_report'
  import { REPORT_DELIVERY_FIELDS } from '../config'

  const props = defineProps<{ modelValue: Record<string, any>; loading: boolean }>()
  const emit = defineEmits<{ (event: 'update:modelValue', value: Record<string, any>): void; (event: 'save'): void }>()
  const draft = reactive<Record<string, any>>({})
  const defaults = ref<Record<string, any>>({})
  const metadataLoading = ref(true)
  const metadataError = ref(false)
  const sampling = ref(false)
  function syncDraft(value: Record<string, any>) {
    for (const [key, fallback] of Object.entries(defaults.value)) draft[key] = value[key] ?? fallback
  }
  watch(() => props.modelValue, syncDraft)
  onMounted(async () => {
    try {
      const response = await getReportDeliveryMetadata()
      defaults.value = response.data.defaults
      syncDraft(props.modelValue)
    } catch { metadataError.value = true } finally { metadataLoading.value = false }
  })
  function save() {
    if (props.loading || metadataLoading.value || metadataError.value) return
    emit('update:modelValue', { ...draft })
    emit('save')
  }
  async function sample() {
    sampling.value = true
    try { await downloadSampleReport() } catch (error) { Message.error(error instanceof Error ? error.message : '下载失败') }
    finally { sampling.value = false }
  }
</script>

<style scoped>
  .mango-report-delivery { width: 100%; min-width: 0; }
  .mango-report-delivery :deep(.arco-spin) { display: block; width: 100%; }
</style>
