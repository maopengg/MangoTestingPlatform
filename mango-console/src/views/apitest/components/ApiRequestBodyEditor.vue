<template>
  <div class="mango-api-body-editor">
    <div class="mango-api-body-editor__toolbar">
      <div class="mango-api-body-editor__field mango-api-body-editor__toolbar-field">
        <span>请求体类型：</span>
        <a-select
          v-model="local.body_type"
          class="mango-api-body-editor__select"
          :options="bodyTypeOptions"
          :disabled="bodyTypeReadonly"
          placeholder="请选择请求体类型"
          @change="handleBodyTypeChange"
        />
      </div>
    </div>

    <div v-if="local.protocol_type === 'sse'" class="mango-api-body-editor__section">
      <div class="mango-api-body-editor__title">SSE配置</div>
      <div class="mango-api-body-editor__sse-form">
        <div class="mango-api-body-editor__field">
          <span>最大读取秒数：</span>
          <a-input-number
            v-model="local.sse_config.max_duration_seconds"
            placeholder="请输入最大读取秒数"
            :min="1"
            @blur="save"
          />
        </div>
        <div class="mango-api-body-editor__field">
          <span>最大事件数：</span>
          <a-input-number
            v-model="local.sse_config.max_event_count"
            placeholder="请输入最大事件数"
            :min="1"
            @blur="save"
          />
        </div>
        <div class="mango-api-body-editor__field">
          <span>结束事件名：</span>
          <a-input
            v-model="local.sse_config.end_event"
            allow-clear
            placeholder="请输入结束事件名"
            @blur="save"
          />
        </div>
        <div class="mango-api-body-editor__field">
          <span>结束JSONPath：</span>
          <a-input
            v-model="local.sse_config.end_jsonpath"
            allow-clear
            placeholder="请输入结束JSONPath"
            @blur="save"
          />
        </div>
      </div>
    </div>

    <div class="mango-api-body-editor__section">
      <div v-if="local.body_type === 'none'" class="mango-api-body-editor__empty">
        当前请求不提交请求体
      </div>

      <template v-else-if="local.body_type === 'json'">
        <div class="mango-api-body-editor__title">JSON请求体</div>
        <a-radio-group
          v-model="local.body_config.source_type"
          type="button"
          @change="handleJsonSourceTypeChange"
        >
          <a-radio value="template">模板文本</a-radio>
          <a-radio value="value">JSON值</a-radio>
        </a-radio-group>
        <a-textarea
          v-if="local.body_config.source_type === 'template'"
          v-model="local.body_config.body_text"
          class="mango-api-body-editor__textarea"
          allow-clear
          :auto-size="{ minRows: 10, maxRows: 18 }"
          placeholder='支持变量模板，例如 {"id": ${{随机数字}}}'
          @blur="save"
        />
        <a-textarea
          v-else
          v-model="jsonValueText"
          class="mango-api-body-editor__textarea"
          allow-clear
          :auto-size="{ minRows: 10, maxRows: 18 }"
          placeholder='请输入合法JSON，例如 {"key": "value"}'
          @blur="save"
        />
      </template>

      <template v-else-if="local.body_type === 'form'">
        <div class="mango-api-body-editor__title">Form字段</div>
        <div
          v-for="(field, index) in local.body_config.fields"
          :key="index"
          class="mango-api-body-editor__row"
        >
          <a-input v-model="field.key" placeholder="key" @blur="save" />
          <a-input v-model="field.value" placeholder="value" @blur="save" />
          <a-button status="danger" @click="removeRow(local.body_config.fields, index)"
            >删除</a-button
          >
        </div>
        <a-button size="small" type="outline" @click="addField">增加字段</a-button>
      </template>

      <template v-else-if="local.body_type === 'raw'">
        <div class="mango-api-body-editor__title">Raw请求体</div>
        <div class="mango-api-body-editor__field mango-api-body-editor__field--full">
          <span>Content-Type：</span>
          <a-input
            v-model="local.body_config.content_type"
            allow-clear
            placeholder="默认 application/json"
            @blur="save"
          />
        </div>
        <a-textarea
          v-model="local.body_config.body_text"
          class="mango-api-body-editor__textarea"
          allow-clear
          :auto-size="{ minRows: 10, maxRows: 18 }"
          placeholder="请输入原始请求体"
          @blur="save"
        />
      </template>

      <template v-else-if="local.body_type === 'multipart'">
        <div class="mango-api-body-editor__title">Multipart普通字段</div>
        <div
          v-for="(field, index) in local.body_config.fields"
          :key="`field-${index}`"
          class="mango-api-body-editor__row"
        >
          <a-input v-model="field.key" placeholder="key" @blur="save" />
          <a-input v-model="field.value" placeholder="value" @blur="save" />
          <a-button status="danger" @click="removeRow(local.body_config.fields, index)"
            >删除</a-button
          >
        </div>
        <a-button size="small" type="outline" @click="addField">增加普通字段</a-button>

        <div class="mango-api-body-editor__title mango-api-body-editor__title--gap">
          Multipart文件字段
        </div>
        <div
          v-for="(file, index) in local.body_config.files"
          :key="`file-${index}`"
          class="mango-api-body-editor__row"
        >
          <a-input v-model="file.key" placeholder="文件字段key" @blur="save" />
          <a-select
            v-model="file.file_id"
            :options="fileOptions"
            :loading="fileLoading"
            placeholder="选择测试文件"
            allow-search
            @change="save"
          />
          <a-input
            v-model="file.file_name"
            allow-clear
            placeholder="发送文件名，可空"
            @blur="save"
          />
          <a-button status="danger" @click="removeRow(local.body_config.files, index)"
            >删除</a-button
          >
        </div>
        <a-button size="small" type="outline" @click="addFile">增加文件字段</a-button>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { Message } from '@arco-design/web-vue'
  import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
  import { getUserFile } from '@/api/system/file_data'

  const props = defineProps<{
    protocolType?: string | null
    bodyType?: string | null
    bodyConfig?: Record<string, any> | null
    sseConfig?: Record<string, any> | null
    projectProductId?: string | number | null
    saving?: boolean
    bodyTypeReadonly?: boolean
  }>()

  const emit = defineEmits<{
    (
      event: 'save',
      value: {
        body_type: string
        body_config: Record<string, any> | null
        sse_config: Record<string, any> | null
      }
    ): void
  }>()

  const bodyTypeOptions = [
    { label: '无请求体', value: 'none' },
    { label: 'JSON', value: 'json' },
    { label: 'Form', value: 'form' },
    { label: 'Raw', value: 'raw' },
    { label: 'Multipart', value: 'multipart' },
  ]

  const local = reactive({
    protocol_type: 'http',
    body_type: 'none',
    body_config: {} as Record<string, any>,
    sse_config: {} as Record<string, any>,
  })
  const fileOptions = ref<Array<{ label: string; value: number }>>([])
  const fileLoading = ref(false)
  const bodyTypeReadonly = computed(() => props.bodyTypeReadonly === true)

  const jsonValueText = computed({
    get() {
      if (typeof local.body_config.body_text === 'string') {
        return local.body_config.body_text
      }
      return JSON.stringify(local.body_config.body ?? {}, null, 2)
    },
    set(value: string) {
      local.body_config.body_text = value
    },
  })

  function defaultBodyConfig(bodyType: string, source?: Record<string, any> | null) {
    const config = source && typeof source === 'object' ? { ...source } : {}
    if (bodyType === 'json') {
      const body = config.body ?? {}
      return {
        source_type: config.source_type || 'template',
        body_text: config.body_text || JSON.stringify(body, null, 2),
        body,
      }
    }
    if (bodyType === 'form') return { fields: Array.isArray(config.fields) ? config.fields : [] }
    if (bodyType === 'raw') {
      return { content_type: config.content_type || 'application/json', body_text: config.body_text || '' }
    }
    if (bodyType === 'multipart') {
      return {
        fields: Array.isArray(config.fields) ? config.fields : [],
        files: Array.isArray(config.files) ? config.files : [],
      }
    }
    return {}
  }

  function syncLocal() {
    local.protocol_type = props.protocolType || 'http'
    local.body_type = props.bodyType || 'none'
    local.body_config = defaultBodyConfig(local.body_type, props.bodyConfig)
    local.sse_config = {
      max_duration_seconds: props.sseConfig?.max_duration_seconds ?? 30,
      max_event_count: props.sseConfig?.max_event_count ?? 100,
      end_event: props.sseConfig?.end_event || '',
      end_jsonpath: props.sseConfig?.end_jsonpath || '',
    }
  }

  function addField() {
    if (!Array.isArray(local.body_config.fields)) local.body_config.fields = []
    local.body_config.fields.push({ key: '', value: '' })
  }

  function addFile() {
    if (!Array.isArray(local.body_config.files)) local.body_config.files = []
    local.body_config.files.push({ key: '', file_id: null, file_name: '' })
  }

  function removeRow(rows: any[], index: number) {
    rows.splice(index, 1)
    save()
  }

  async function handleBodyTypeChange() {
    await nextTick()
    save()
  }

  async function handleJsonSourceTypeChange() {
    await nextTick()
    save()
  }

  async function loadFiles() {
    if (!props.projectProductId) {
      fileOptions.value = []
      return
    }
    fileLoading.value = true
    try {
      const res = await getUserFile({
        project_product: props.projectProductId,
        page: 1,
        pageSize: 10000,
      })
      fileOptions.value = (res.data || []).map((item: any) => ({
        label: `${item.name} / ID:${item.id}`,
        value: item.id,
      }))
    } catch (error) {
      console.log(error)
    } finally {
      fileLoading.value = false
    }
  }

  function buildBodyConfig() {
    if (local.body_type === 'none') return null
    if (local.body_type === 'json') {
      if (local.body_config.source_type === 'value') {
        try {
          return { source_type: 'value', body: JSON.parse(local.body_config.body_text || '{}') }
        } catch (error) {
          Message.error('JSON值必须是合法JSON')
          return false
        }
      }
      return {
        source_type: 'template',
        body_text: local.body_config.body_text || '',
      }
    }
    if (local.body_type === 'multipart') {
      return {
        fields: (local.body_config.fields || []).filter((item: any) => item.key),
        files: (local.body_config.files || []).filter((item: any) => item.key && item.file_id),
      }
    }
    if (local.body_type === 'form') {
      return { fields: (local.body_config.fields || []).filter((item: any) => item.key) }
    }
    if (local.body_type === 'raw') {
      return {
        content_type: local.body_config.content_type || 'application/json',
        body_text: local.body_config.body_text || '',
      }
    }
    return null
  }

  function save() {
    const bodyConfig = buildBodyConfig()
    if (bodyConfig === false) return
    emit('save', {
      body_type: local.body_type,
      body_config: bodyConfig,
      sse_config: local.protocol_type === 'sse' ? local.sse_config : null,
    })
  }

  watch(
    () => [props.protocolType, props.bodyType, props.bodyConfig, props.sseConfig],
    syncLocal,
    { deep: true, immediate: true }
  )
  watch(() => local.body_type, (value) => {
    local.body_config = defaultBodyConfig(value, local.body_config)
  })
  watch(() => props.projectProductId, loadFiles, { immediate: true })

  onMounted(loadFiles)
</script>

<style scoped>
  .mango-api-body-editor {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .mango-api-body-editor__row,
  .mango-api-body-editor__grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 180px)) max-content;
    gap: 8px;
    align-items: center;
  }

  .mango-api-body-editor__toolbar {
    display: grid;
    grid-template-columns: minmax(260px, 360px) max-content;
    gap: 8px;
    align-items: center;
  }

  .mango-api-body-editor__toolbar-field {
    min-width: 260px;
  }

  .mango-api-body-editor__row {
    grid-template-columns: minmax(120px, 0.35fr) minmax(180px, 1fr) max-content;
    margin-bottom: 8px;
  }

  .mango-api-body-editor__row:has(.arco-select:nth-child(2)) {
    grid-template-columns: minmax(120px, 0.25fr) minmax(200px, 0.45fr) minmax(160px, 0.3fr) max-content;
  }

  .mango-api-body-editor__sse-form {
    display: grid;
    grid-template-columns: repeat(2, minmax(260px, 1fr));
    gap: 10px 16px;
  }

  .mango-api-body-editor__field {
    display: grid;
    grid-template-columns: 108px minmax(0, 1fr);
    gap: 8px;
    align-items: center;
    min-width: 0;
    color: var(--m-text-2);
    font-size: 13px;
    line-height: 20px;
  }

  .mango-api-body-editor__field > span {
    color: var(--m-muted);
    text-align: right;
    white-space: nowrap;
  }

  .mango-api-body-editor__field--full {
    max-width: 560px;
    margin-bottom: 8px;
  }

  .mango-api-body-editor__section {
    min-width: 0;
  }

  .mango-api-body-editor__title {
    margin-bottom: 8px;
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
  }

  .mango-api-body-editor__title--gap {
    margin-top: 14px;
  }

  .mango-api-body-editor__textarea {
    margin-top: 8px;
  }

  .mango-api-body-editor__empty {
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
    color: var(--m-muted);
    font-size: 13px;
    line-height: 20px;
  }

  @media (max-width: 900px) {
    .mango-api-body-editor__toolbar,
    .mango-api-body-editor__row,
    .mango-api-body-editor__row:has(.arco-select:nth-child(2)),
    .mango-api-body-editor__grid {
      grid-template-columns: 1fr;
    }

    .mango-api-body-editor__sse-form {
      grid-template-columns: 1fr;
    }

    .mango-api-body-editor__field {
      grid-template-columns: 96px minmax(0, 1fr);
    }
  }
</style>
