<template>
  <a-modal v-model:visible="visible" modal-class="mango-simple-form-modal" title="批量设置分类" :width="560"
    :on-before-ok="save" :ok-loading="saving" :mask-closable="!saving" :closable="!saving" :cancel-button-props="{ disabled: saving }" @cancel="close">
    <a-form :model="draft" auto-label-width class="mango-simple-form" layout="horizontal">
      <a-form-item label="已选变量" class="mango-simple-form-item">{{ ids.length }} 条</a-form-item>
      <a-form-item label="操作" class="mango-simple-form-item"><a-select v-model="draft.operation" :options="variableTagOperations" :disabled="saving" /></a-form-item>
      <a-form-item label="分类标签" class="mango-simple-form-item">
        <a-select v-model="draft.tags" :options="options" multiple allow-create allow-search allow-clear :disabled="saving" placeholder="输入或选择标签" />
      </a-form-item>
      <a-form-item v-if="draft.operation === 2" class="mango-simple-form-item"><span>将替换原标签；留空表示清空分类。</span></a-form-item>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
  import { onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { putApiPublic } from '@/api/apitest/public'
  import { putUiPublic } from '@/api/uitest/public'
  import { normalizeVariableTags, variableTagOperations } from './variable-tags'
  import useUserStore from '@/store/modules/user'
  const props = defineProps<{ kind: 'api' | 'ui'; contextKey: string; options: string[] }>()
  const emit = defineEmits<{ (event: 'saved'): void }>()
  const visible = ref(false), saving = ref(false), ids = ref<Array<string | number>>([])
  const draft = reactive({ operation: 0, tags: [] as string[] })
  let version = 0
  const user = useUserStore()
  function close() { version++; visible.value = false }
  function open(values: Array<string | number>) {
    if (saving.value) return
    if (!values.length) { Message.warning('请选择变量'); return }
    if (values.length > 200) { Message.warning('每次最多设置200条变量'); return }
    version++; ids.value = [...values]; draft.operation = 0; draft.tags = []; visible.value = true
  }
  async function save() {
    if (saving.value || !visible.value) return false
    const tags = normalizeVariableTags(draft.tags)
    if (tags.length > 20 || tags.some(tag => tag.length > 32)) { Message.error('最多20个标签，每个最多32个字符'); return false }
    if (draft.operation !== 2 && !tags.length) { Message.warning('请选择需要操作的标签'); return false }
    const token = version, payload = { ids: [...ids.value], tags, tag_operation: draft.operation }
    saving.value = true
    try {
      await (props.kind === 'api' ? putApiPublic(payload) : putUiPublic(payload))
      if (token !== version) return false
      Message.success('分类已更新'); emit('saved'); close(); return true
    } catch { return false }
    finally { saving.value = false }
  }
  watch(() => props.contextKey, close)
  watch(() => [user.userId, user.roleId, user.token], close, { flush: 'sync' })
  onDeactivated(close); onBeforeUnmount(close)
  defineExpose({ open, close })
</script>
