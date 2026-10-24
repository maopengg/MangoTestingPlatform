<template>
  <div class="mango-evaluation-ai-profiles">
    <a-space>
      <a-button v-if="editable" v-permission="'system.settings:edit'" size="small" :disabled="loading" @click="add">新增 AI</a-button>
      <a-button v-if="editable" v-permission="'system.settings:edit'" size="small" type="primary" :loading="loading" @click="save">保存 AI 列表</a-button>
    </a-space>
    <div v-if="!draft.length" class="mango-empty-state">尚未配置效果测评 AI</div>
    <section v-for="(profile, index) in draft" :key="profile.id" class="mango-soft-panel">
      <div class="mango-section-title">
        <strong>{{ profile.name || `AI ${index + 1}` }}</strong>
        <a-space>
          <a-switch v-if="editable" v-permission="'system.settings:edit'" v-model="profile.enabled" size="small" :disabled="loading" />
          <a-button v-if="editable" v-permission="'system.settings:edit'" size="small" type="text" status="danger" :disabled="loading" @click="draft.splice(index, 1)">移除</a-button>
        </a-space>
      </div>
      <a-form :model="profile" layout="horizontal" :disabled="!editable || loading">
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
  import { ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import usePermissionStore from '@/store/modules/permission'
  import { computed } from 'vue'
  const props = defineProps<{ modelValue: any[]; loading?: boolean }>()
  const emit = defineEmits(['update:modelValue', 'save'])
  const permissions = usePermissionStore()
  const editable = computed(() => permissions.hasPermission('system.settings:edit'))
  const draft = ref<any[]>([])
  const providers = [{ value: 'openai_compatible', label: 'OpenAI 兼容' }, { value: 'openai', label: 'OpenAI' }, { value: 'azure_openai', label: 'Azure OpenAI' }]
  watch(() => props.modelValue, value => { draft.value = JSON.parse(JSON.stringify(value || [])) }, { immediate: true, deep: true })
  function add() {
    if (!editable.value || props.loading || draft.value.length >= 50) return
    draft.value.push({ id: crypto.randomUUID(), name: '', provider_type: 'openai_compatible',
      base_url: '', model: '', api_key: '', timeout: 120, enabled: true })
  }
  function save() {
    if (!editable.value || props.loading) return
    if (draft.value.some(row => !row.name.trim() || !row.model.trim() || !row.base_url.trim() || (row.enabled && !row.api_key.trim()))) {
      Message.warning('请填写 AI 名称、模型、服务地址和密钥')
      return
    }
    emit('update:modelValue', JSON.parse(JSON.stringify(draft.value)))
    emit('save')
  }
</script>
<style scoped>
  .mango-evaluation-ai-profiles { display: grid; gap: var(--m-page-gap); min-width: 0; container-type: inline-size; }
  .mango-evaluation-ai-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: var(--m-page-gap); }
  @container (max-width: 650px) { .mango-evaluation-ai-fields { grid-template-columns: minmax(0, 1fr); } }
</style>
