<template>
  <a-form-item label="别名推断参考">
    <a-space direction="vertical" fill>
      <a-select v-model="sourceId" :options="sources" :loading="loading.sources" allow-search allow-clear
        placeholder="选择同类型连接，仅用于 AI 推断" />
      <a-input v-if="[0, 1].includes(sourceType)" v-model="databaseName" placeholder="数据库名称（可选）" />
      <a-space><a-button size="small" :disabled="!sourceId" :loading="loading.suggest" @click="suggest">AI 推断别名</a-button>
        <span v-if="suggestion">{{ suggestion }}</span>
        <a-button v-if="suggestion" size="small" @click="emit('apply', suggestion)">使用此别名</a-button></a-space>
    </a-space>
  </a-form-item>
</template>
<script setup lang="ts">
  import { reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { getSystemDataSource, suggestDataSourceAlias } from '@/api/system/data_source'
  const props = defineProps<{ sourceType: number | null }>()
  const emit = defineEmits<{ (event: 'apply', name: string): void }>()
  const sourceId = ref<number>()
  const databaseName = ref('')
  const suggestion = ref('')
  const sources = ref<any[]>([])
  const loading = reactive({ sources: false, suggest: false })
  let version = 0
  watch(() => props.sourceType, async (type) => {
    const current = ++version
    sourceId.value = undefined
    suggestion.value = ''
    loading.sources = true
    try {
      const res = await getSystemDataSource({ db_type: type, page: 1, pageSize: 999 })
      if (current === version) sources.value = (res.data || []).map((item: any) => ({ value: item.id, label: item.display_name }))
    } finally { if (current === version) loading.sources = false }
  }, { immediate: true })
  async function suggest() {
    loading.suggest = true
    try {
      const res = await suggestDataSourceAlias({ data_source_id: sourceId.value, name: databaseName.value })
      suggestion.value = res.data?.alias || ''
      if (!suggestion.value) Message.warning('未获得可用别名，请手动填写')
    } finally { loading.suggest = false }
  }
</script>
