<template>
  <a-select :model-value="modelValue" :options="options" :loading="loading" :disabled="disabled || productId == null || productId === ''"
    multiple allow-create allow-search allow-clear :max-tag-count="2" placeholder="选填，可输入新标签"
    @update:model-value="changeTags" />
</template>
<script setup lang="ts">
  import { computed, onBeforeUnmount, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { reportLoadError } from '@/utils/load-error'
  import useUserStore from '@/store/modules/user'
  import { normalizeVariableTags, type VariableTagReader } from './variable-tags'
  const props = defineProps<{ modelValue: string[]; productId: string | number | null; read: VariableTagReader; disabled?: boolean }>()
  const emit = defineEmits<{ (event: 'update:modelValue', value: string[]): void }>()
  const names = ref<string[]>([]), loading = ref(false)
  const options = computed(() => [...new Set([...props.modelValue, ...names.value])])
  function changeTags(value: unknown) {
    const tags = normalizeVariableTags(value)
    if (tags.length > 20 || tags.some(tag => tag.length > 32)) {
      Message.warning('最多20个标签，每个最多32个字符'); return
    }
    emit('update:modelValue', tags)
  }
  let sequence = 0
  const user = useUserStore()
  watch(() => [props.productId, user.userId, user.roleId, user.token], async () => {
    const id = props.productId
    const token = ++sequence
    names.value = []; loading.value = false
    if (id == null || id === '') return
    loading.value = true
    try {
      const response = await props.read({ project_product: id, tag_summary: true })
      if (token === sequence) names.value = response.data.items.map(item => item.name)
    } catch (error) { if (token === sequence) reportLoadError(error, '分类选项加载失败', false) }
    finally { if (token === sequence) loading.value = false }
  }, { immediate: true })
  onBeforeUnmount(() => { sequence++ })
</script>
