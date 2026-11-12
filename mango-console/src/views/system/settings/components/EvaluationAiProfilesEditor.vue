<template>
  <div class="mango-evaluation-ai-profiles">
    <a-space>
      <a-button size="small" :disabled="loading || Boolean(modelError) || draft.length >= 50" @click="add">新增 AI</a-button>
      <a-button size="small" type="primary" :disabled="Boolean(modelError)" :loading="loading" @click="save">保存 AI 列表</a-button>
    </a-space>
    <a-alert data-feedback-kind="validation" v-if="modelError" type="error">{{ modelError }}</a-alert>
    <div v-else-if="!draft.length" class="mango-empty-state">尚未配置效果测评 AI</div>
    <section v-for="(profile, index) in draft" :key="profile.id" class="mango-soft-panel">
      <div class="mango-section-title">
        <strong>{{ profile.name || `AI ${index + 1}` }}</strong>
        <a-space>
          <a-switch v-model="profile.enabled" size="small" :disabled="loading" />
          <a-button size="small" type="text" status="danger" :disabled="loading" @click="remove(index)">移除</a-button>
        </a-space>
      </div>
      <a-form :model="profile" layout="horizontal" :disabled="loading">
        <div class="mango-evaluation-ai-fields">
          <a-form-item label="名称" required><a-input v-model="profile.name" :max-length="100" /></a-form-item>
          <a-form-item label="模型" required><a-input v-model="profile.model" placeholder="填写模型名称" /></a-form-item>
          <a-form-item label="服务地址" required><a-input v-model="profile.base_url" placeholder="https://example.com/v1" /></a-form-item>
          <a-form-item label="API Key" required><a-input-password v-model="profile.api_key" placeholder="已保存的 Key 无需重新输入" /></a-form-item>
          <a-form-item label="协议"><a-select v-model="profile.provider_type" :options="providers" /></a-form-item>
          <a-form-item label="超时（秒）"><a-input-number v-model="profile.timeout" :min="1" :max="3600" /></a-form-item>
        </div>
      </a-form>
    </section>
  </div>
</template>
<script setup lang="ts">
  import { ref, toRaw, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { EVALUATION_AI_PROVIDER_OPTIONS as providers } from '../config'
  import { createEvaluationAiProfile, copyEvaluationAiProfiles, evaluationAiProfilePayload } from '../evaluation-profiles'
  import type { EvaluationAiProfile } from '../evaluation-profiles'
  const props = defineProps<{ modelValue: unknown; loading?: boolean }>()
  const emit = defineEmits<{ (event: 'update:modelValue', value: EvaluationAiProfile[]): void; (event: 'save'): void }>()
  const draft = ref<EvaluationAiProfile[]>([]), modelError = ref('')
  let lastEmission: EvaluationAiProfile[] | null = null
  watch(() => props.modelValue, value => {
    if (lastEmission !== null && toRaw(value) === lastEmission) return
    try { draft.value = copyEvaluationAiProfiles(value); modelError.value = '' }
    catch { draft.value = []; modelError.value = 'AI列表配置格式异常，请重新读取系统配置' }
  }, { immediate: true })
  function add() {
    if (props.loading || modelError.value || draft.value.length >= 50) return
    draft.value.push(createEvaluationAiProfile(crypto.randomUUID()))
  }
  function remove(index: number) {
    if (props.loading || modelError.value || !Number.isInteger(index) || index < 0 || index >= draft.value.length) return
    draft.value.splice(index, 1)
  }
  function save() {
    if (props.loading || modelError.value) return
    try {
      const payload = evaluationAiProfilePayload(draft.value)
      lastEmission = payload; emit('update:modelValue', payload); emit('save')
    } catch (error) { Message.warning(error instanceof Error ? error.message : '请检查 AI 配置') }
  }
</script>
<style scoped>
  .mango-evaluation-ai-profiles { display: grid; gap: var(--m-page-gap); min-width: 0; container-type: inline-size; }
  .mango-evaluation-ai-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: var(--m-page-gap); }
  @container (max-width: 650px) { .mango-evaluation-ai-fields { grid-template-columns: minmax(0, 1fr); } }
</style>
