<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    title="上传文件"
    :width="560"
    :on-before-ok="upload"
    ok-text="上传"
    :closable="!uploading"
    :mask-closable="!uploading"
    :esc-to-close="!uploading"
    :cancel-button-props="{ disabled: uploading }"
    unmount-on-close
    @cancel="close"
  >
    <a-form auto-label-width class="mango-simple-form" :model="draft" layout="horizontal" :disabled="uploading">
      <a-form-item class="mango-simple-form-item" label="文件" required>
        <a-upload
          :file-list="fileList"
          :auto-upload="false"
          :limit="1"
          :disabled="uploading"
          :on-before-remove="removeFile"
          @change="changeFile"
        />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="项目/产品" required>
        <ProjectProductSelect
          v-model="draft.project_product"
          :disabled="uploading"
          placeholder="请选择项目产品"
        />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="允许下载">
        <a-switch v-model="draft.allow_download" :disabled="uploading" />
      </a-form-item>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
  import { computed, reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import type { FileItem } from '@arco-design/web-vue/es/upload/interfaces'
  import { postUserFile } from '@/api/system/file_data'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import { createFileDraft, createUploadPayload, productId } from '../file'
  import { useTestFileScope } from '../composables/useTestFileScope'
  const emit = defineEmits<{
    (event: 'saved'): void
    (event: 'uploading-change', pending: boolean): void
  }>()
  const visible = ref(false),
    uploading = ref(false),
    fileList = ref<FileItem[]>([])
  const selectedFile = computed(() => fileList.value[0]?.file ?? null)
  const draft = reactive(createFileDraft())
  let session = 0
  const scope = useTestFileScope(close)
  function open(product: string | number | null = null) {
    if (uploading.value || !scope.isActive()) return
    close()
    draft.project_product = product
    visible.value = true
  }
  function close() {
    ++session
    visible.value = false
    fileList.value = []
    Object.assign(draft, createFileDraft())
  }
  function changeFile(files: FileItem[]) {
    if (!uploading.value) fileList.value = files.slice(-1)
  }
  function removeFile(): boolean {
    if (uploading.value) return false
    fileList.value = []
    return true
  }
  async function upload(): Promise<boolean> {
    if (!visible.value || uploading.value || !scope.isActive()) return false
    if (!selectedFile.value) {
      Message.error('请选择上传文件')
      return false
    }
    if (productId(draft.project_product) === null) {
      Message.error('请选择项目产品')
      return false
    }
    const payload = createUploadPayload(selectedFile.value, draft),
      current = session,
      version = scope.snapshot()
    uploading.value = true
    emit('uploading-change', true)
    try {
      const response = await postUserFile(payload)
      if (current !== session || !scope.current(version)) return false
      Message.success(response.msg)
      emit('saved')
      close()
      return true
    } catch {
      return false
    } finally {
      uploading.value = false
      emit('uploading-change', false)
    }
  }
  defineExpose({ open, close })
</script>
