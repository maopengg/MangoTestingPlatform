<template>
  <BaseSidePanel
    :visible="visible"
    title="历史资源精确补偿"
    :width="760"
    :show-footer="false"
    @update:visible="close"
  >
    <a-form :model="form" layout="horizontal" auto-label-width :disabled="busy">
      <a-form-item label="补偿原因" required>
        <a-input
          v-model="form.reason"
          :max-length="500"
          placeholder="说明原清理失败及本次处理依据"
        />
      </a-form-item>
      <a-form-item
        label="子记录归属映射（可选）"
        help="只填写映射，归属记录由平台读取原执行证据。留空沿用原规则；不能输入文档ID或租户来强制删除。"
      >
        <a-textarea
          v-model="form.lineage"
          :auto-size="{ minRows: 4, maxRows: 9 }"
          placeholder='例如 {"entity_id":52,"parent_field":"parent_id","tenant_field":"tenant_id","id_field":"id","collection_path":"rounds","document_id_path":"roundId"}'
        />
      </a-form-item>
      <a-space>
        <a-button size="small" :loading="busy" @click="preview">预览精确影响</a-button>
        <a-button
          type="primary"
          status="danger"
          size="small"
          :loading="busy"
          :disabled="!confirmation"
          @click="execute"
          >确认补偿并验证</a-button
        >
      </a-space>
    </a-form>
    <div v-if="confirmation" class="mango-compensation-preview">
      <p
        >只处理原执行的精确资源，不重跑业务创建。原快照保留；文档版本变化将拒绝删除。结果必须完成观察验证。</p
      >
      <JsonDisplay :data="confirmation" />
    </div>
  </BaseSidePanel>
</template>
<script setup lang="ts">
  import { reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import { postDataFactoryExecutionCleanup } from '@/api/data-factory'
  import { useExecutionScope } from '../composables/useExecutionScope'
  import type { JsonValue } from '../types'

  const emit = defineEmits<{ (event: 'completed'): void }>()
  const visible = ref(false),
    busy = ref(false)
  const form = reactive({ reason: '', lineage: '' })
  const confirmation = ref<Record<string, JsonValue> | null>(null)
  let target: { execution_id: number; item_id: number; snapshot_index: number } | null = null
  let generation = 0
  const scope = useExecutionScope(close)
  watch(
    () => [form.reason, form.lineage],
    () => {
      confirmation.value = null
      generation++
    }
  )
  function close() {
    generation++
    visible.value = false
    busy.value = false
    confirmation.value = null
    target = null
  }
  function open(
    executionId: number,
    row: { item_id: number; snapshot_index: number; tenant_lineage?: JsonValue }
  ) {
    close()
    form.reason = ''
    form.lineage = row.tenant_lineage ? JSON.stringify(row.tenant_lineage, null, 2) : ''
    target = { execution_id: executionId, item_id: row.item_id, snapshot_index: row.snapshot_index }
    visible.value = true
  }
  async function send(previewOnly: boolean) {
    if (!target || busy.value || !scope.isActive() || !form.reason.trim()) {
      if (!form.reason.trim()) Message.warning('请填写补偿原因')
      return
    }
    let lineage: unknown = null
    try {
      lineage = form.lineage.trim() ? JSON.parse(form.lineage) : null
    } catch {
      Message.warning('子记录归属映射必须为合法JSON对象')
      return
    }
    const snapshot = { ...target },
      current = ++generation,
      version = scope.snapshot()
    const token = confirmation.value
    if (!previewOnly && !token) return
    busy.value = true
    try {
      const response = await postDataFactoryExecutionCleanup({
        execution_id: snapshot.execution_id,
        compensation: {
          item_id: snapshot.item_id,
          snapshot_index: snapshot.snapshot_index,
          reason: form.reason.trim(),
          tenant_lineage: lineage,
        },
        preview: previewOnly,
        ...(previewOnly
          ? {}
          : { preview_token: token?.preview_token, confirm_text: token?.confirm_text }),
      })
      if (current !== generation || !scope.current(version) || !visible.value) return
      if (previewOnly) confirmation.value = response.data
      else {
        if (response.data?.fail) Message.warning('补偿尚未完成，请查看清理明细和历史记录')
        else Message.success('原执行资源已完成清理验证')
        emit('completed')
        close()
      }
    } catch {
      if (current === generation) confirmation.value = null
    } finally {
      if (current === generation) busy.value = false
    }
  }
  const preview = () => send(true),
    execute = () => send(false)
  defineExpose({ open, close })
</script>
<style scoped>
  .mango-compensation-preview {
    margin-top: var(--m-page-gap);
    color: var(--m-text);
  }
</style>
