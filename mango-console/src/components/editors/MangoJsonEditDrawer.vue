<template>
  <a-drawer v-model:visible="localVisible" :title="title" :width="width" unmount-on-close>
    <div class="mango-json-edit-drawer">
      <div v-if="description" class="mango-json-edit-drawer__tip">
        {{ description }}
      </div>
      <MangoJsonEditor
        v-model="localValue"
        :placeholder="placeholder"
        min-height="calc(100vh - 190px)"
      />
    </div>
    <template #footer>
      <div class="mango-json-edit-drawer__footer">
        <a-button size="small" @click="handleCancel" data-testid="qa-components-editors-mangojsoneditdrawer-button-取消">取消</a-button>
        <a-button size="small" type="primary" :loading="props.saving" @click="handleSave" data-testid="qa-components-editors-mangojsoneditdrawer-button-保存"
          >保存</a-button
        >
      </div>
    </template>
  </a-drawer>
</template>

<script lang="ts" setup>
  import { ref, watch } from 'vue'
  import MangoJsonEditor from '@/components/editors/MangoJsonEditor.vue'

  const props = withDefaults(
    defineProps<{
      visible: boolean
      modelValue: string
      title?: string
      description?: string
      placeholder?: string
      width?: string | number
      saving?: boolean
    }>(),
    {
      title: 'JSON 编辑',
      description: '',
      placeholder: '请输入 JSON 内容',
      width: '50%',
      saving: false,
    }
  )

  const emit = defineEmits<{
    (e: 'update:visible', value: boolean): void
    (e: 'update:modelValue', value: string): void
    (e: 'save', value: string): void
    (e: 'cancel'): void
  }>()

  const localVisible = ref(props.visible)
  const localValue = ref(props.modelValue || '')

  watch(
    () => props.visible,
    (value) => {
      localVisible.value = value
      if (value) {
        localValue.value = props.modelValue || ''
      }
    }
  )

  watch(
    () => props.modelValue,
    (value) => {
      if (!localVisible.value) {
        localValue.value = value || ''
      }
    }
  )

  watch(localVisible, (value) => {
    emit('update:visible', value)
  })

  function handleCancel() {
    localVisible.value = false
    emit('cancel')
  }

  function handleSave() {
    emit('update:modelValue', localValue.value)
    emit('save', localValue.value)
  }
</script>

<style scoped>
  .mango-json-edit-drawer {
    display: flex;
    height: 100%;
    min-height: 0;
    flex-direction: column;
  }

  .mango-json-edit-drawer__tip {
    flex-shrink: 0;
    margin-bottom: 10px;
    padding: 8px 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
    color: var(--m-muted);
    font-size: 13px;
    line-height: 20px;
  }

  .mango-json-edit-drawer :deep(.mango-json-editor) {
    flex: 1;
    min-height: 0;
  }

  .mango-json-edit-drawer__footer {
    display: flex;
    justify-content: flex-start;
    gap: 8px;
    width: 100%;
  }
</style>
