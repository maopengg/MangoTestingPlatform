<template>
  <template v-if="[0, 1].includes(sourceType)">
    <a-form-item label="数据库名称">
      <a-select v-model="target.database_name" :options="databases" :loading="loading.databases"
        allow-search allow-create allow-clear placeholder="可留空，或选择 / 输入数据库名称" />
    </a-form-item>
    <a-form-item v-if="sourceType === 1" label="Schema">
      <a-select v-model="target.schema_name" :options="schemas" :loading="loading.schemas"
        allow-search allow-create allow-clear placeholder="可留空，使用连接默认 Schema" />
    </a-form-item>
    <a-form-item v-if="!target.database_name" label="查询说明">
      <span class="mango-muted-text">{{ sourceType === 0 ? '未选默认库，请使用库.表查询。' : '未选库时连接 postgres；schema.表不能跨数据库，请按业务需要选库。' }}</span>
    </a-form-item>
  </template>
  <a-form-item v-if="sourceType === 10" label="Redis DB" required>
    <a-input-number v-model="target.redis_db" :min="0" :precision="0" />
  </a-form-item>
  <a-form-item v-if="sourceId" label="目标验证">
    <a-button size="small" :loading="loading.test" @click="testTarget">测试连接</a-button>
  </a-form-item>
</template>
<script setup lang="ts">
  import { computed, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { getDataSourceDatabases, getDataSourceSchemas } from '@/api/system/data_source'
  import { postDataSourceExecution } from '@/api/data-source-execution'
  type Target = { database_name: string; schema_name: string; redis_db: number | null }
  const props = defineProps<{ sourceId?: number | null; sourceType: number; modelValue: Target }>()
  const emit = defineEmits<{ (event: 'update:modelValue', value: Target): void }>()
  const target = computed({ get: () => props.modelValue, set: value => emit('update:modelValue', value) })
  const loading = reactive({ databases: false, schemas: false, test: false })
  const databases = ref<string[]>([])
  const schemas = ref<string[]>([])
  let databaseVersion = 0
  let schemaVersion = 0
  watch(() => props.sourceId, async (id, previous) => {
    const version = ++databaseVersion
    databases.value = []
    loading.databases = false
    if (previous != null && id !== previous) {
      target.value = { database_name: '', schema_name: '', redis_db: props.sourceType === 10 ? 0 : null }
    }
    if (id && props.sourceType === 10 && target.value.redis_db == null) target.value.redis_db = 0
    if (!id || ![0, 1].includes(props.sourceType)) return
    loading.databases = true
    try {
      const res = await getDataSourceDatabases({ data_source_id: id })
      if (version === databaseVersion) databases.value = (res.data?.items || res.data || []).map((item: any) => item.name)
    } catch { /* 允许手动输入名称，接口已展示错误。 */ }
    finally { if (version === databaseVersion) loading.databases = false }
  }, { immediate: true })
  watch(() => [props.sourceId, target.value.database_name], async ([id, name]) => {
    const version = ++schemaVersion
    schemas.value = []
    loading.schemas = false
    if (!id || props.sourceType !== 1 || !name) return
    loading.schemas = true
    try {
      const res = await getDataSourceSchemas({ data_source_id: id, database_name: name })
      if (version === schemaVersion) schemas.value = (res.data?.items || res.data || []).map((item: any) => typeof item === 'string' ? item : item.name)
    } catch { /* 允许手动输入 Schema。 */ }
    finally { if (version === schemaVersion) loading.schemas = false }
  }, { immediate: true })
  async function testTarget() {
    if (!props.sourceId) return
    loading.test = true
    try {
      const res = await postDataSourceExecution({ action: 'test_connection', data_source_id: props.sourceId,
        target: { ...target.value, database_name: target.value.database_name || '', schema_name: target.value.schema_name || '' } })
      if (res.data?.connected) Message.success('目标连接测试成功')
      else Message.error(res.data?.error || '目标连接测试失败')
    } catch (error: any) { Message.error(error?.msg || error?.message || '目标连接测试失败') }
    finally { loading.test = false }
  }
</script>
