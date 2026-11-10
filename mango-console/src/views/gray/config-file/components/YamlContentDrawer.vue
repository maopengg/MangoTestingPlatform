<template>
  <BaseSidePanel
    :visible="visible"
    :title="target?.title || '配置内容'"
    :width="1000"
    cancel-button-text="关闭"
    @update:visible="onVisibleChange"
    @cancel="closeDrawer"
  >
    <MangoPanelSpin :loading="loading" class="mango-gray-content">
      <div class="mango-gray-content__path" :title="filePath">{{ filePath || '-' }}</div>
      <template v-if="error"></template>
      <CodeEditor
        v-else
        v-model="content"
        readonly
        placeholder="暂无配置内容"
        :code-style="{ height: '100%' }"
        class="mango-gray-content__editor"
      />
    </MangoPanelSpin>
    <template #footer-buttons>
      <a-button @click="closeDrawer">关闭</a-button>
    </template>
  </BaseSidePanel>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { onActivated, onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import { getGrayYamlFileContent } from '@/api/gray'
  import { object, selectionId } from '../forms'
  import type { ContentTarget } from '../content'

  const props = defineProps<{ contextKey: string }>()
  const visible = ref(false)
  const target = ref<ContentTarget | null>(null)
  const content = ref('')
  const filePath = ref('')
  const loading = ref(false)
  const error = ref('')
  let active = true,
    generation = 0,
    sequence = 0

  function closeDrawer() {
    generation++
    sequence++
    visible.value = false
    target.value = null
    content.value = ''
    filePath.value = ''
    loading.value = false
    error.value = ''
  }

  function open(source: ContentTarget) {
    if (
      !active ||
      !selectionId(source.yamlId) ||
      !selectionId(source.bindingId) ||
      !selectionId(source.repositoryId)
    )
      return
    closeDrawer()
    target.value = {
      yamlId: source.yamlId,
      bindingId: source.bindingId,
      repositoryId: source.repositoryId,
      title: source.title,
      filePath: source.filePath,
    }
    filePath.value = source.filePath
    visible.value = true
    void loadContent()
  }

  async function loadContent() {
    if (!active || !visible.value || !target.value) return
    const source = { ...target.value },
      currentGeneration = generation,
      request = ++sequence,
      context = props.contextKey
    const current = () =>
      active &&
      visible.value &&
      generation === currentGeneration &&
      request === sequence &&
      props.contextKey === context
    loading.value = true
    error.value = ''
    content.value = ''
    try {
      const response = await getGrayYamlFileContent({
        id: source.yamlId,
        binding_id: source.bindingId,
      })
      if (!current()) return
      const row = object(response.data)
      if (
        response.code !== 200 ||
        selectionId(row.yaml_file_id) !== source.yamlId ||
        selectionId(row.binding_id) !== source.bindingId ||
        selectionId(row.repository_id) !== source.repositoryId ||
        typeof row.file_path !== 'string' ||
        typeof row.content !== 'string'
      )
        throw Error('Invalid content response')
      filePath.value = row.file_path
      content.value = row.content
    } catch (loadFailure0) {
      if (current()) (reportLoadError(loadFailure0, "配置内容读取失败，请重试", false), error.value = '配置内容读取失败，请重试')
    } finally {
      if (current()) loading.value = false
    }
  }

  function onVisibleChange(value: boolean) {
    if (!value) closeDrawer()
  }

  watch(() => props.contextKey, closeDrawer, { flush: 'sync' })
  onDeactivated(() => {
    active = false
    closeDrawer()
  })
  onActivated(() => {
    active = true
  })
  onBeforeUnmount(() => {
    active = false
    closeDrawer()
  })
  defineExpose({ open })
</script>

<style scoped lang="less">
  .mango-gray-content {
    width: 100%;
    height: 100%;
    min-width: 0;
    min-height: 0;
  }
  .mango-gray-content :deep(> .mango-panel-spin__content) {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
    min-height: 0;
    height: 100%;
  }
  .mango-gray-content__path {
    flex: none;
    overflow: hidden;
    padding: var(--m-page-gap);
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
    color: var(--m-text-2);
    font-size: 13px;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-gray-content__editor {
    flex: 1 1 auto;
    min-height: 0;
    overflow: hidden;
  }
</style>
