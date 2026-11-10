<template>
  <a-modal
    v-model:visible="visible"
    title="批量导入"
    :width="560"
    :on-before-ok="save"
    :closable="!saving"
    :mask-closable="!saving"
    :cancel-button-props="{ disabled: saving }"
    @cancel="close"
  >
    <a-space direction="vertical" fill>
      <a-button size="small" :loading="downloading" :disabled="saving" @click="downloadTemplate"
        >下载模板</a-button
      >
      <a-space wrap
        ><a-button size="small" type="primary" :disabled="saving" @click="fileInput?.click()"
          >选择文件</a-button
        ><span class="mango-import-filename" :title="selectedFile?.name">{{
          selectedFile?.name || '请选择 .xlsx 或 .xls 文件'
        }}</span></a-space
      >
      <input
        ref="fileInput"
        type="file"
        accept=".xlsx,.xls"
        class="mango-import-input"
        :disabled="saving"
        @change="selectFile"
      />
    </a-space>
  </a-modal>
</template>
<script setup lang="ts">
  import { ref, onBeforeUnmount, onDeactivated } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { postApiUploadApi } from '@/api/apitest/info'
  import { importTemplateFileName } from '../config'
  const emit = defineEmits<{ (event: 'saved'): void }>()
  const visible = ref(false),
    saving = ref(false),
    downloading = ref(false)
  const fileInput = ref<HTMLInputElement | null>(null),
    selectedFile = ref<File | null>(null)
  let session = 0
  function clearFile() {
    selectedFile.value = null
    if (fileInput.value) fileInput.value.value = ''
  }
  function close() {
    session++
    visible.value = false
  }
  function open() {
    if (saving.value) return
    close()
    clearFile()
    visible.value = true
  }
  function selectFile(event: Event) {
    if (saving.value) return
    const file = (event.target as HTMLInputElement).files?.[0]
    if (file && !/\.(xlsx|xls)$/i.test(file.name)) {
      Message.warning('请选择 .xlsx 或 .xls 文件')
      clearFile()
      return
    }
    selectedFile.value = file ?? null
  }
  async function save(): Promise<boolean> {
    if (!visible.value || saving.value) return false
    if (!selectedFile.value) {
      Message.warning('请先选择要上传的文件')
      return false
    }
    const token = session,
      file = selectedFile.value
    saving.value = true
    try {
      const response = await postApiUploadApi(file)
      if (token !== session) return false
      Message.success(response.msg)
      emit('saved')
      clearFile()
      close()
      return true
    } catch {
      return false
    } finally {
      saving.value = false
    }
  }
  async function downloadTemplate() {
    if (downloading.value) return
    const token = session
    downloading.value = true
    let objectUrl: string | null = null
    try {
      const response = await fetch(
        `/api/download?file_name=${encodeURIComponent(importTemplateFileName)}`
      )
      if (!response.ok || response.headers.get('content-type')?.includes('application/json'))
        throw Error()
      const blob = await response.blob()
      if (token !== session || !visible.value) return
      objectUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = objectUrl
      link.download = importTemplateFileName
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch {
      if (token === session && visible.value) Message.error('模板下载失败，请重试')
    } finally {
      if (objectUrl) URL.revokeObjectURL(objectUrl)
      downloading.value = false
    }
  }
  onBeforeUnmount(close)
  onDeactivated(close)
  defineExpose({ open, close })
</script>
<style scoped>
  .mango-import-input {
    display: none;
  }
  .mango-import-filename {
    display: inline-block;
    max-width: 320px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    vertical-align: middle;
    color: var(--m-text-2);
  }
</style>
