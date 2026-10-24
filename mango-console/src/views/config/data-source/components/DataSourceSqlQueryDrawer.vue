<template>
  <a-drawer :visible="visible" width="50%" :footer="false" unmount-on-close @update:visible="$emit('update:visible', $event)">
    <template #title>SQL查询 / {{ databaseName }}</template>
    <div class="mango-connection-query">
      <dl class="mango-connection-query-target">
        <dt>连接配置</dt><dd :title="sourceName">{{ sourceName }}</dd>
        <dt>数据库</dt><dd :title="databaseName">{{ databaseName }}</dd>
      </dl>
      <label for="mango-connection-query-sql">查询SQL</label>
      <a-textarea id="mango-connection-query-sql" v-model="statement" :disabled="loading"
        :auto-size="{ minRows: 6, maxRows: 12 }" placeholder="请输入只读SQL，例如：SELECT * FROM table_name LIMIT 20" />
      <div class="mango-connection-query-actions">
        <span class="mango-muted-text">只读查询，SQL必须指定 LIMIT 1～200</span>
        <a-space>
          <a-button size="small" :disabled="loading" @click="clear">清空</a-button>
          <a-button v-permission="'config.datasource:debug'" size="small" type="primary" :loading="loading" @click="query">查询</a-button>
        </a-space>
      </div>
      <div class="mango-connection-query-result">
        <strong>查询结果</strong>
        <a-spin :loading="loading" class="mango-connection-query-spin">
          <JsonDisplay v-if="result !== null" :data="result" :default-expanded="false" :show-drawer-button="false" />
          <div v-else class="mango-empty-state">执行查询后将在这里展示结果</div>
        </a-spin>
      </div>
    </div>
  </a-drawer>
</template>
<script setup lang="ts">
  import { ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import { queryDataSourceDatabase } from '@/api/system/data_source'
  const props = defineProps<{visible: boolean; sourceId: number; sourceName: string; databaseName: string}>()
  defineEmits(['update:visible'])
  const statement = ref('')
  const result = ref<any>(null)
  const loading = ref(false)
  function clear() {statement.value = ''; result.value = null}
  async function query() {
    if (loading.value) return
    if (!statement.value.trim()) {Message.error('请输入查询SQL'); return}
    loading.value = true
    result.value = null
    try {
      const response = await queryDataSourceDatabase({data_source_id: props.sourceId,
        database_name: props.databaseName, sql: statement.value.trim()})
      result.value = response.data
    } catch {
      // 请求层统一显示接口错误，避免重复弹出提示。
    } finally {loading.value = false}
  }
</script>
<style scoped>
  .mango-connection-query {display: flex; flex-direction: column; gap: var(--m-space-md); min-width: 0;}
  .mango-connection-query-target {display: grid; grid-template-columns: auto minmax(0, 1fr); gap: var(--m-space-sm) var(--m-space-md); margin: 0;}
  .mango-connection-query-target dt {color: var(--m-muted);}
  .mango-connection-query-target dd {margin: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;}
  .mango-connection-query-actions {display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: var(--m-space-sm);}
  .mango-connection-query-result {display: flex; flex-direction: column; gap: var(--m-space-sm); min-width: 0;}
  .mango-connection-query-spin {display: block; min-height: 160px;}
</style>
