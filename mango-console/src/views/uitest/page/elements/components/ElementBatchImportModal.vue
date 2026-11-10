<template>
  <a-modal :visible="visible" title="批量增加页面元素" :width="560" :footer="false" @update:visible="emit('update:visible', $event)">
    <div class="mango-element-import">
      <div v-if="error" class="mango-element-import__error" role="alert">{{ error }}</div>
      <section class="mango-soft-panel mango-element-import__row">
        <div><strong>下载模板</strong><span>按模板格式填写页面元素。</span></div>
        <a-button size="small" :loading="downloading" @click="downloadTemplate">下载模板</a-button>
      </section>
      <section class="mango-soft-panel mango-element-import__row">
        <div><strong>上传模板</strong><span>{{ selectedFile?.name || '支持 Excel 格式' }}</span></div>
        <a-upload accept=".xlsx,.xls" :show-file-list="false" :auto-upload="false" :disabled="uploading" @before-upload="upload">
          <template #upload-button><a-button size="small" type="primary" :loading="uploading">上传模板</a-button></template>
        </a-upload>
        <a-button v-if="error && selectedFile" size="small" :loading="uploading" @click="upload(selectedFile)">重试</a-button>
      </section>
    </div>
  </a-modal>
</template>
<script setup lang="ts">
  import { ref, shallowRef, watch } from 'vue'
  import { getUiElementUpload } from '@/api/uitest/element'
  import { useLiveWorkbenchScope } from '@/hooks/use-live-workbench-scope'
  import { elementResponse } from '../element-records'
  import { liveId, liveError, type LiveId } from '@/components/business/ui-live-workbench'
  const props = defineProps<{ visible: boolean; pageId: LiveId | null }>()
  const emit = defineEmits<{ (event: 'update:visible', visible: boolean): void; (event: 'saved'): void }>()
  const uploading = ref(false), downloading = ref(false), error = ref(''), selectedFile = shallowRef<File | null>(null)
  let windowVersion = 0
  watch(() => props.visible, () => { windowVersion++; error.value = ''; selectedFile.value = null }, { flush: 'sync' })
  const scope = useLiveWorkbenchScope(() => props.pageId, { invalidate() { windowVersion++; error.value = ''; selectedFile.value = null; emit('update:visible', false) }, resume() {} })
  async function upload(file: File) {
    const pageId = liveId(props.pageId), current = scope.capture(), version = windowVersion
    if (!current() || !props.visible || uploading.value || pageId === null) return false
    const body = new FormData(); body.append('file', file); body.append('page_id', String(pageId)); body.append('name', file.name)
    selectedFile.value = file; uploading.value = true; error.value = ''
    try {
      const response: unknown = await getUiElementUpload(body); elementResponse(response)
      if (!current()) return false
      emit('saved')
      if (props.visible && version === windowVersion) emit('update:visible', false)
    } catch (reason) { if (current() && props.visible && version === windowVersion) error.value = liveError(reason, '导入失败，请重试') }
    finally { uploading.value = false }
    return false
  }
  async function downloadTemplate() {
    if (!scope.available() || downloading.value) return
    const current = scope.capture(), version = windowVersion
    downloading.value = true; error.value = ''
    let url = ''
    try {
      const filename = '元素批量上传模版.xlsx', response = await fetch(`/api/download?file_name=${encodeURIComponent(filename)}`, { credentials: 'same-origin' })
      if (!response.ok || response.headers?.get('content-type')?.includes('application/json')) throw Error('模板下载失败，请重试')
      const blob = await response.blob()
      if (!current() || !props.visible || version !== windowVersion) return
      url = URL.createObjectURL(blob)
      const link = document.createElement('a'); link.href = url; link.download = filename
      document.body.appendChild(link); link.click(); link.remove()
    } catch (reason) { if (current() && version === windowVersion) error.value = liveError(reason, '模板下载失败，请重试') }
    finally { if (url) URL.revokeObjectURL(url); downloading.value = false }
  }
</script>
<style scoped>
  .mango-element-import { display: flex; flex-direction: column; gap: var(--m-page-gap); }
  .mango-element-import__row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px; }
  .mango-element-import__row > div { min-width: 0; display: flex; flex-direction: column; gap: 4px; overflow-wrap: anywhere; }
  .mango-element-import__row span { color: var(--m-muted); }
  .mango-element-import__error { color: var(--m-danger); }
</style>
