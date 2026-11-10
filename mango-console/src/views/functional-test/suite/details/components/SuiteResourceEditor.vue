<template>
  <a-drawer
    :visible="visible"
    :title="raw ? form.title || '原文' : '上下文资料'"
    :width="760"
    :mask-closable="!saving"
    :esc-to-close="!saving"
    :on-before-cancel="canCancel"
    @update:visible="onVisibleChange"
  >
    <a-alert v-if="saveError" type="error" class="mango-suite-resource__error">
      保存失败，输入及已上传文件已保留，请重试。
    </a-alert>
    <div v-if="raw" class="mango-suite-resource__raw">
      <CodeEditor
        v-model="rawText"
        :readonly="saving"
        :code-style="resourceCodeStyle"
        placeholder="暂无原文内容"
      />
    </div>
    <a-form v-else :model="form" layout="horizontal" :disabled="saving">
      <a-grid :cols="2" :col-gap="16">
        <a-grid-item
          ><a-form-item label="资料分组"
            ><a-select
              v-model="form.context_key"
              :options="groupOptions"
              :field-names="fieldNames"
              disabled /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="资料类型"
            ><a-select
              v-model="form.content_type"
              :options="typeOptions"
              :field-names="fieldNames" /></a-form-item
        ></a-grid-item>
        <a-grid-item :span="2"
          ><a-alert type="info" class="mango-suite-resource__tip"
            >URL
            需后端可访问且无需额外登录。私有链接、文件和图片可手工补充解析文本，便于查阅。</a-alert
          ></a-grid-item
        >
        <a-grid-item :span="2"
          ><a-form-item label="标题" required
            ><a-input v-model="form.title" placeholder="请输入资料标题" /></a-form-item
        ></a-grid-item>
        <a-grid-item v-if="form.content_type === resourceContent.url" :span="2"
          ><a-form-item label="URL 类型"
            ><a-select v-model="form.url_type"
              ><a-option :value="resourceUrl.normal">普通URL</a-option
              ><a-option :value="resourceUrl.feishu" disabled
                >飞书文档（后续开放）</a-option
              ></a-select
            ></a-form-item
          ></a-grid-item
        >
        <a-grid-item v-if="!isFile" :span="2"
          ><a-form-item
            :label="form.content_type === resourceContent.url ? 'URL或链接说明' : '文本内容'"
            ><div class="mango-suite-resource__content"
              ><CodeEditor
                v-model="form.content"
                :readonly="saving"
                :code-style="resourceCodeStyle" /></div></a-form-item
        ></a-grid-item>
        <a-grid-item v-if="isFile" :span="2"
          ><a-form-item label="上传文件">
            <a-upload
              :file-list="fileList"
              :auto-upload="false"
              :limit="1"
              :disabled="saving"
              :accept="form.content_type === resourceContent.image ? 'image/*' : undefined"
              @change="onFileChange"
              :on-before-remove="removeFile"
            />
            <span v-if="form.file_name" class="mango-suite-resource__file"
              >当前文件：{{ form.file_name }}</span
            >
          </a-form-item></a-grid-item
        >
        <a-grid-item v-if="isFile" :span="2"
          ><a-form-item label="文件说明或路径"
            ><a-textarea
              v-model="form.content"
              :auto-size="{ minRows: 3, maxRows: 8 }" /></a-form-item
        ></a-grid-item>
        <a-grid-item :span="2"
          ><a-form-item label="解析文本"
            ><div class="mango-suite-resource__extracted"
              ><CodeEditor
                v-model="form.extracted_text"
                :readonly="saving"
                :code-style="resourceCodeStyle"
                placeholder="可在这里补充文件、图片或 URL 的文本内容。" /></div></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="启用"><a-switch v-model="form.enabled" size="small" /></a-form-item
        ></a-grid-item>
      </a-grid>
    </a-form>
    <template #footer
      ><a-space
        ><a-button size="small" :disabled="saving" @click="cancel">取消</a-button
        ><a-button size="small" type="primary" :loading="saving" @click="save"
          >保存</a-button
        ></a-space
      ></template
    >
  </a-drawer>
</template>
<script setup lang="ts">
  import {
    computed,
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    reactive,
    ref,
    shallowRef,
    watch,
  } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import type { FileItem } from '@arco-design/web-vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import {
    postFunctionalContextResource,
    putFunctionalContextResource,
  } from '@/api/functional-test'
  import { postUserFile } from '@/api/system/file_data'
  import { resourceContent, resourceUrl, resourceCodeStyle } from '../config'
  import { createResourceForm, resourceDraft, resourceId, objectValue } from '../resource-form'
  import type { SuiteResource, SuiteResourceForm, UploadedResourceFile } from '../resource-form'

  const props = defineProps<{
    suiteId: number | null
    productId: number | null
    contextKey: string
    available: boolean
    groupOptions: Array<{ key: number | string; title: string }>
    typeOptions: Array<{ key: number | string; title: string }>
  }>()
  const emit = defineEmits<{
    (event: 'changed', suiteId: number): void
    (event: 'busy', value: boolean): void
  }>()
  const fieldNames = { value: 'key', label: 'title' }
  const visible = ref(false),
    raw = ref(false),
    saving = ref(false),
    saveError = ref(false)
  const rawText = ref('')
  const form: SuiteResourceForm = reactive(createResourceForm())
  const fileList = ref<FileItem[]>([])
  const selectedFile = shallowRef<File | null>(null)
  const isFile = computed(
    () => form.content_type === resourceContent.file || form.content_type === resourceContent.image
  )
  let active = true,
    generation = 0
  let subject: { suiteId: number; productId: number | null; contextKey: string } | null = null
  let uploaded: { source: File; metadata: UploadedResourceFile } | null = null
  const current = (version: number) =>
    active &&
    visible.value &&
    props.available &&
    version === generation &&
    subject?.suiteId === props.suiteId &&
    subject?.productId === props.productId &&
    subject?.contextKey === props.contextKey
  const canCancel = () => !saving.value
  function reset() {
    ++generation
    visible.value = false
    subject = null
    uploaded = null
    selectedFile.value = null
    fileList.value = []
    saveError.value = false
    rawText.value = ''
    Object.assign(form, createResourceForm())
  }
  function cancel() {
    if (canCancel()) reset()
  }
  function onVisibleChange(value: boolean) {
    if (!value) cancel()
  }
  function open(contextKey: number, title: string, record?: SuiteResource, rawMode = false) {
    if (
      !active ||
      saving.value ||
      !props.available ||
      !resourceId(props.suiteId) ||
      contextKey === 6 ||
      !Number.isInteger(contextKey)
    )
      return
    if (record && (resourceId(record.suite) !== props.suiteId || !resourceId(record.id))) return
    if (rawMode && !record) return
    reset()
    subject = { suiteId: props.suiteId!, productId: props.productId, contextKey: props.contextKey }
    Object.assign(
      form,
      record ? resourceDraft(record) : createResourceForm(subject.suiteId, contextKey, title)
    )
    raw.value = rawMode
    rawText.value = form.content_type === resourceContent.text ? form.content : form.extracted_text
    visible.value = true
  }
  function onFileChange(list: FileItem[], item: FileItem) {
    if (saving.value) return
    fileList.value = list.slice(-1)
    const file = item?.file || fileList.value[0]?.file || null
    if (file !== selectedFile.value) uploaded = null
    selectedFile.value = file
  }
  async function removeFile() {
    if (saving.value) return false
    selectedFile.value = null
    fileList.value = []
    uploaded = null
    return true
  }
  async function save() {
    if (saving.value || !subject || !current(generation)) return false
    if (!raw.value && !form.title.trim()) {
      Message.error('请输入资料标题')
      return false
    }
    if (!raw.value && form.url_type === resourceUrl.feishu) {
      Message.error('飞书文档后续开放，请先选择普通URL')
      return false
    }
    const version = generation,
      target = { ...subject },
      draft = { ...form },
      rawMode = raw.value,
      text = rawText.value
    const source = isFile.value && !rawMode ? selectedFile.value : null
    const payload = rawMode
      ? {
          id: draft.id,
          suite: target.suiteId,
          ...(draft.content_type === resourceContent.text
            ? { content: text }
            : { extracted_text: text }),
        }
      : {
          ...draft,
          suite: target.suiteId,
          url_type:
            draft.content_type === resourceContent.url ? draft.url_type : resourceUrl.normal,
        }
    saving.value = true
    emit('busy', true)
    saveError.value = false
    try {
      if (source) {
        if (uploaded?.source !== source) {
          const data = new FormData()
          data.append('test_file', source)
          data.append('type', '0')
          data.append('name', `${Date.now()}-${source.name}`)
          if (target.productId !== null) data.append('project_product', String(target.productId))
          const response = await postUserFile(data)
          if (!current(version)) return false
          const file = objectValue(response.data),
            id = resourceId(file.id)
          if (!id) throw new Error('Invalid file response')
          uploaded = {
            source,
            metadata: {
              file: id,
              file_name: source.name,
              file_path:
                typeof file.test_file === 'string'
                  ? file.test_file
                  : typeof file.file_path === 'string'
                  ? file.file_path
                  : '',
              mime_type: source.type,
              file_size: source.size,
              parse_status: 0,
            },
          }
        }
        Object.assign(payload, uploaded.metadata)
      }
      if (!current(version)) return false
      const { id, ...createPayload } = payload
      const response = await (draft.id
        ? putFunctionalContextResource(payload)
        : postFunctionalContextResource(createPayload))
      if (!current(version)) return false
      const saved = objectValue(response.data)
      if (
        !resourceId(saved.id) ||
        (draft.id !== null && resourceId(saved.id) !== draft.id) ||
        resourceId(saved.suite) !== target.suiteId
      )
        throw new Error('Invalid resource response')
      Message.success(rawMode ? '原文已保存' : '资料已保存')
      reset()
      emit('changed', target.suiteId)
      return true
    } catch {
      if (current(version)) saveError.value = true
      return false
    } finally {
      // Context invalidation hides the editor but the physical write must settle before reopening.
      saving.value = false
      emit('busy', false)
    }
  }
  watch(() => [props.contextKey, props.suiteId, props.productId, props.available], reset, {
    flush: 'sync',
  })
  onDeactivated(() => {
    active = false
    reset()
  })
  onActivated(() => {
    active = true
  })
  onBeforeUnmount(() => {
    active = false
    reset()
  })
  defineExpose({ open })
</script>
<style scoped>
  .mango-suite-resource__error,
  .mango-suite-resource__tip {
    margin-bottom: var(--m-page-gap);
  }
  .mango-suite-resource__file {
    color: var(--m-muted);
    overflow-wrap: anywhere;
  }
  .mango-suite-resource__content {
    width: 100%;
    height: 260px;
  }
  .mango-suite-resource__extracted {
    width: 100%;
    height: 180px;
  }
  .mango-suite-resource__raw {
    height: calc(100% - var(--m-page-gap));
    min-height: 260px;
  }
</style>
