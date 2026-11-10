<template>
  <template v-if="[0, 1].includes(sourceType)">
    <a-form-item label="数据库名称">
      <a-select
        v-model="databaseName"
        :disabled="disabled"
        :options="databases"
        :loading="loading.databases"
        allow-search
        allow-create
        allow-clear
        placeholder="可留空，或选择 / 输入数据库名称"
      />
    </a-form-item>
    <a-form-item v-if="sourceType === 1" label="Schema">
      <a-select
        v-model="schemaName"
        :disabled="disabled"
        :options="schemas"
        :loading="loading.schemas"
        allow-search
        allow-create
        allow-clear
        placeholder="可留空，使用连接默认 Schema"
      />
    </a-form-item>
    <a-form-item v-if="!databaseName" label="查询说明">
      <span class="mango-muted-text">{{
        sourceType === 0
          ? '未选默认库，请使用库.表查询。'
          : '未选库时连接 postgres；schema.表不能跨数据库，请按业务需要选库。'
      }}</span>
    </a-form-item>
  </template>
  <a-form-item v-if="sourceType === 10" label="Redis DB" required>
    <a-input-number v-model="redisDb" :disabled="disabled" :min="0" :precision="0" />
  </a-form-item>
  <a-form-item v-if="sourceId" label="目标验证">
    <a-button size="small" :loading="loading.test" :disabled="disabled" @click="testTarget"
      >测试连接</a-button
    >
  </a-form-item>
</template>
<script setup lang="ts">
  import { computed, onActivated, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import useUserStore from '@/store/modules/user'
  import { getDataSourceDatabases, getDataSourceSchemas } from '@/api/system/data_source'
  import { postDataSourceExecution } from '@/api/data-source-execution'
  type Target = { database_name: string; schema_name: string; redis_db: number | null }
  const props = defineProps<{
    sourceId?: number | null
    sourceType: number
    modelValue: Target
    disabled?: boolean
  }>()
  const emit = defineEmits<{ (event: 'update:modelValue', value: Target): void }>()
  const target = computed({
    get: () => props.modelValue,
    set: (value) => emit('update:modelValue', value),
  })
  const databaseName = computed({
    get: () => props.modelValue.database_name,
    set: (value) => {
      target.value = { ...props.modelValue, database_name: value ?? '' }
    },
  })
  const schemaName = computed({
    get: () => props.modelValue.schema_name,
    set: (value) => {
      target.value = { ...props.modelValue, schema_name: value ?? '' }
    },
  })
  const redisDb = computed({
    get: () => props.modelValue.redis_db,
    set: (value) => {
      target.value = { ...props.modelValue, redis_db: value }
    },
  })
  const loading = reactive({ databases: false, schemas: false, test: false })
  const databases = ref<string[]>([]),
    schemas = ref<string[]>([])
  const user = useUserStore()
  let databaseVersion = 0,
    schemaVersion = 0,
    testVersion = 0,
    active = true
  function names(value: unknown): string[] {
    const items = Array.isArray(value)
      ? value
      : value && typeof value === 'object' && 'items' in value && Array.isArray(value.items)
      ? value.items
      : []
    return items.flatMap((item: unknown) =>
      typeof item === 'string'
        ? [item]
        : item && typeof item === 'object' && 'name' in item && typeof item.name === 'string'
        ? [item.name]
        : []
    )
  }
  function invalidate() {
    ++databaseVersion
    ++schemaVersion
    ++testVersion
    databases.value = []
    schemas.value = []
    loading.databases = false
    loading.schemas = false
    loading.test = false
  }
  async function loadDatabases() {
    const id = props.sourceId,
      version = ++databaseVersion
    databases.value = []
    loading.databases = false
    if (!active || id == null || ![0, 1].includes(props.sourceType)) return
    loading.databases = true
    try {
      const res = await getDataSourceDatabases({ data_source_id: id })
      if (active && version === databaseVersion) databases.value = names(res.data)
    } catch {
    } finally {
      if (version === databaseVersion) loading.databases = false
    }
  }
  async function loadSchemas() {
    const id = props.sourceId,
      name = props.modelValue.database_name,
      version = ++schemaVersion
    schemas.value = []
    loading.schemas = false
    if (!active || id == null || props.sourceType !== 1 || !name) return
    loading.schemas = true
    try {
      const res = await getDataSourceSchemas({ data_source_id: id, database_name: name })
      if (active && version === schemaVersion) schemas.value = names(res.data)
    } catch {
    } finally {
      if (version === schemaVersion) loading.schemas = false
    }
  }
  watch(
    () => [props.sourceId, props.sourceType] as const,
    ([id, type], previous) => {
      invalidate()
      if (previous?.[0] != null && previous[0] !== id)
        target.value = { database_name: '', schema_name: '', redis_db: type === 10 ? 0 : null }
      else if (id != null && type === 10 && props.modelValue.redis_db === null)
        target.value = { ...props.modelValue, redis_db: 0 }
      void loadDatabases()
      void loadSchemas()
    },
    { immediate: true, flush: 'sync' }
  )
  watch(
    () => props.modelValue.database_name,
    () => {
      void loadSchemas()
    },
    { flush: 'sync' }
  )
  watch(
    () => [props.modelValue.database_name, props.modelValue.schema_name, props.modelValue.redis_db],
    () => {
      ++testVersion
      loading.test = false
    },
    { flush: 'sync' }
  )
  watch(
    () => [user.token, user.roleId],
    () => {
      invalidate()
      void loadDatabases()
      void loadSchemas()
    },
    { flush: 'sync' }
  )
  async function testTarget() {
    if (!active || props.disabled || props.sourceId == null || loading.test) return
    const version = ++testVersion,
      payload = {
        action: 'test_connection' as const,
        data_source_id: props.sourceId,
        target: { ...props.modelValue },
      }
    loading.test = true
    try {
      const res = await postDataSourceExecution(payload)
      if (!active || version !== testVersion) return
      if (res.data?.connected) Message.success('目标连接测试成功')
      else Message.error(res.data?.error || '目标连接测试失败')
    } catch (error: unknown) {
      if (active && version === testVersion) {
        const message =
          error && typeof error === 'object' && 'msg' in error && typeof error.msg === 'string'
            ? error.msg
            : error &&
              typeof error === 'object' &&
              'message' in error &&
              typeof error.message === 'string'
            ? error.message
            : '目标连接测试失败'
        Message.error(message)
      }
    } finally {
      if (version === testVersion) loading.test = false
    }
  }
  function deactivate() {
    active = false
    invalidate()
  }
  onDeactivated(deactivate)
  onBeforeUnmount(deactivate)
  onActivated(() => {
    if (!active) {
      active = true
      void loadDatabases()
      void loadSchemas()
    }
  })
</script>
