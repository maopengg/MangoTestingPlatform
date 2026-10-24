<template>
  <div class="mango-api-body-editor">
    <div class="mango-api-body-editor__header">
      <div class="mango-api-body-editor__heading">
        <div class="mango-api-body-editor__heading-row">
          <div class="mango-api-body-editor__heading-title">请求体配置</div>
          <a-tag size="small" color="arcoblue">
            {{ String(local.protocol_type || 'http').toUpperCase() }}
          </a-tag>
        </div>
        <div class="mango-api-body-editor__heading-subtitle">
          选择请求体类型，并维护本次请求实际发送的数据内容
        </div>
      </div>
      <div class="mango-api-body-editor__type-field">
        <span>请求体类型</span>
        <a-select
          v-model="local.body_type"
          class="mango-api-body-editor__select"
          :options="bodyTypeOptions"
          :disabled="
            readonly || bodyTypeReadonly || ['grpc', 'websocket'].includes(local.protocol_type)
          "
          placeholder="请选择请求体类型"
          @change="handleBodyTypeChange" data-testid="qa-views-apitest-components-apirequestbodyeditor-select-请选择请求体类型"
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
            :disabled="readonly"
            @blur="save" data-testid="qa-views-apitest-components-apirequestbodyeditor-input-number-请输入最大读取秒数"
          />
        </div>
        <div class="mango-api-body-editor__field">
          <span>最大事件数：</span>
          <a-input-number
            v-model="local.sse_config.max_event_count"
            placeholder="请输入最大事件数"
            :min="1"
            :disabled="readonly"
            @blur="save" data-testid="qa-views-apitest-components-apirequestbodyeditor-input-number-请输入最大事件数"
          />
        </div>
        <div class="mango-api-body-editor__field">
          <span>结束事件名：</span>
          <a-input
            v-model="local.sse_config.end_event"
            allow-clear
            :disabled="readonly"
            placeholder="请输入结束事件名"
            @blur="save" data-testid="qa-views-apitest-components-apirequestbodyeditor-input-请输入结束事件名"
          />
        </div>
        <div class="mango-api-body-editor__field">
          <span>结束JSONPath：</span>
          <a-input
            v-model="local.sse_config.end_jsonpath"
            allow-clear
            :disabled="readonly"
            placeholder="请输入结束JSONPath"
            @blur="save" data-testid="qa-views-apitest-components-apirequestbodyeditor-input-请输入结束jsonpath"
          />
        </div>
      </div>
    </div>

    <div v-if="local.protocol_type === 'websocket'" class="mango-api-body-editor__section">
      <div class="mango-api-body-editor__title">WebSocket连接配置</div>
      <div class="mango-api-body-editor__sse-form">
        <div class="mango-api-body-editor__field">
          <span>连接超时：</span>
          <a-input-number
            v-model="local.body_config.connect.connect_timeout_seconds"
            :min="1"
            :disabled="readonly"
            placeholder="默认10秒"
            @blur="save" data-testid="qa-views-apitest-components-apirequestbodyeditor-input-number-默认10秒"
          />
        </div>
        <div class="mango-api-body-editor__field">
          <span>欢迎消息：</span>
          <a-switch
            v-model="local.body_config.connect.read_greeting"
            :disabled="readonly"
            @change="save"
          />
        </div>
        <div class="mango-api-body-editor__field">
          <span>Ping间隔：</span>
          <a-input-number
            v-model="local.body_config.connect.ping_interval_seconds"
            :min="1"
            :disabled="readonly"
            placeholder="留空则默认"
            @blur="save" data-testid="qa-views-apitest-components-apirequestbodyeditor-input-number-留空则默认"
          />
        </div>
        <div class="mango-api-body-editor__field">
          <span>Ping超时：</span>
          <a-input-number
            v-model="local.body_config.connect.ping_timeout_seconds"
            :min="1"
            :disabled="readonly"
            placeholder="留空则默认"
            @blur="save" data-testid="qa-views-apitest-components-apirequestbodyeditor-input-number-留空则默认-2"
          />
        </div>
      </div>

      <div class="mango-api-body-editor__title mango-api-body-editor__title--gap">
        WebSocket消息脚本
      </div>
      <div
        v-for="(message, index) in local.body_config.messages"
        :key="index"
        class="mango-api-body-editor__ws-message"
      >
        <div class="mango-api-body-editor__ws-row">
          <a-input
            v-model="message.name"
            :disabled="readonly"
            placeholder="步骤名称"
            @blur="save" data-testid="qa-views-apitest-components-apirequestbodyeditor-input-步骤名称"
          />
          <a-select
            v-model="message.direction"
            :disabled="readonly"
            :options="wsDirectionOptions"
            placeholder="方向"
            @change="() => handleWsDirectionChange(message)" data-testid="qa-views-apitest-components-apirequestbodyeditor-select-方向"
          />
          <a-select
            v-if="message.direction === 'send'"
            v-model="message.message_type"
            :disabled="readonly"
            :options="wsMessageTypeOptions"
            placeholder="消息类型"
            @change="save" data-testid="qa-views-apitest-components-apirequestbodyeditor-select-消息类型"
          />
          <a-input-number
            v-else-if="message.direction === 'sleep'"
            v-model="message.seconds"
            :min="1"
            :disabled="readonly"
            placeholder="等待秒数"
            @blur="save" data-testid="qa-views-apitest-components-apirequestbodyeditor-input-number-等待秒数"
          />
          <a-input-number
            v-else
            v-model="message.timeout_seconds"
            :min="1"
            :disabled="readonly"
            placeholder="超时秒数"
            @blur="save" data-testid="qa-views-apitest-components-apirequestbodyeditor-input-number-超时秒数"
          />
          <a-button status="danger" :disabled="readonly" @click="removeWsMessage(index)" data-testid="qa-views-apitest-components-apirequestbodyeditor-button-删除"
            >删除</a-button
          >
        </div>
        <a-textarea
          v-if="message.direction === 'send'"
          v-model="message.payload_text"
          class="mango-api-body-editor__textarea"
          allow-clear
          :disabled="readonly"
          :auto-size="{ minRows: 4, maxRows: 10 }"
          :placeholder="
            message.message_type === 'binary'
              ? '请输入base64内容'
              : '请输入发送消息，JSON类型支持变量模板'
          "
          @blur="save"
        />
        <div
          v-else-if="message.direction === 'receive'"
          class="mango-api-body-editor__ws-condition"
        >
          <div class="mango-api-body-editor__field">
            <span>最大消息数：</span>
            <a-input-number
              v-model="message.max_message_count"
              :min="1"
              :disabled="readonly"
              placeholder="默认1"
              @blur="save" data-testid="qa-views-apitest-components-apirequestbodyeditor-input-number-默认1"
            />
          </div>
          <div class="mango-api-body-editor__field">
            <span>停止类型：</span>
            <a-select
              v-model="message.until.type"
              :disabled="readonly"
              :options="wsUntilTypeOptions"
              allow-clear
              placeholder="收到消息即停止"
              @change="save" data-testid="qa-views-apitest-components-apirequestbodyeditor-select-收到消息即停止"
            />
          </div>
          <div class="mango-api-body-editor__field">
            <span>表达式：</span>
            <a-input
              v-model="message.until.expression"
              :disabled="readonly"
              allow-clear
              placeholder="JSONPath或正则表达式"
              @blur="save" data-testid="qa-views-apitest-components-apirequestbodyeditor-input-jsonpath或正则表达式"
            />
          </div>
          <div class="mango-api-body-editor__field">
            <span>预期值：</span>
            <a-input
              v-model="message.until.expect"
              :disabled="readonly"
              allow-clear
              placeholder="可为空"
              @blur="save" data-testid="qa-views-apitest-components-apirequestbodyeditor-input-可为空"
            />
          </div>
        </div>
      </div>
      <a-space>
        <a-button size="small" type="outline" :disabled="readonly" @click="addWsMessage('send')" data-testid="qa-views-apitest-components-apirequestbodyeditor-button-新增发送"
          >新增发送</a-button
        >
        <a-button size="small" type="outline" :disabled="readonly" @click="addWsMessage('receive')" data-testid="qa-views-apitest-components-apirequestbodyeditor-button-新增接收"
          >新增接收</a-button
        >
        <a-button size="small" type="outline" :disabled="readonly" @click="addWsMessage('sleep')" data-testid="qa-views-apitest-components-apirequestbodyeditor-button-新增等待"
          >新增等待</a-button
        >
        <a-button size="small" type="outline" :disabled="readonly" @click="addWsMessage('ping')" data-testid="qa-views-apitest-components-apirequestbodyeditor-button-新增ping"
          >新增Ping</a-button
        >
      </a-space>
    </div>

    <div class="mango-api-body-editor__section mango-api-body-editor__content-section">
      <div v-if="local.protocol_type === 'websocket'" class="mango-api-body-editor__empty">
        WebSocket消息脚本会作为本协议的请求配置保存。
      </div>
      <div v-else-if="local.body_type === 'none'" class="mango-api-body-editor__empty">
        当前请求不提交请求体
      </div>

      <template v-else-if="local.body_type === 'json'">
        <div v-if="local.protocol_type === 'grpc'" class="mango-api-body-editor__notice">
          <div class="mango-api-body-editor__notice-title">gRPC Message 请求体</div>
          <div>
            页面使用 JSON 维护请求 Message，执行时会按 proto/descriptor 转成 Protobuf
            二进制发送；响应也会转成 JSON 用于展示、提取和断言。
          </div>
          <div>
            当前仅支持 Unary RPC。Server Streaming、Client Streaming、Bidirectional Streaming
            暂不执行。
          </div>
        </div>
        <div class="mango-api-body-editor__content-head">
          <div>
            <div class="mango-api-body-editor__title">
              {{ local.protocol_type === 'grpc' ? 'gRPC Message' : 'JSON 请求体' }}
            </div>
            <div class="mango-api-body-editor__content-subtitle">
              {{
                local.body_config.source_type === 'template'
                  ? '支持变量表达式；JSON 值草稿会独立保留'
                  : '保存前校验 JSON 格式；模板文本草稿会独立保留'
              }}
            </div>
          </div>
          <a-radio-group
            v-model="local.body_config.source_type"
            type="button"
            :disabled="readonly"
            @change="handleJsonSourceTypeChange"
          >
            <a-radio value="template" data-testid="qa-views-apitest-components-apirequestbodyeditor-radio-模板文本">模板文本</a-radio>
            <a-radio value="value" data-testid="qa-views-apitest-components-apirequestbodyeditor-radio-json-值">JSON 值</a-radio>
          </a-radio-group>
        </div>
        <a-textarea
          v-if="local.body_config.source_type === 'template'"
          v-model="local.body_config.body_text"
          class="mango-api-body-editor__textarea"
          allow-clear
          :disabled="readonly"
          :auto-size="{ minRows: 10, maxRows: 18 }"
          :placeholder="
            local.protocol_type === 'grpc'
              ? '请输入请求 Message 模板，例如 {&quot;id&quot;: ${{user_id}}}'
              : '支持变量模板，例如 {&quot;id&quot;: ${{随机数字}}}'
          "
          @blur="save"
        />
        <a-textarea
          v-else
          v-model="jsonValueText"
          class="mango-api-body-editor__textarea"
          allow-clear
          :disabled="readonly"
          :auto-size="{ minRows: 10, maxRows: 18 }"
          :placeholder="
            local.protocol_type === 'grpc'
              ? '请输入合法 JSON 对象，字段名建议使用 proto 中的原始字段名'
              : '请输入合法JSON，例如 {&quot;key&quot;: &quot;value&quot;}'
          "
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
          <a-input v-model="field.key" :disabled="readonly" placeholder="key" @blur="save" data-testid="qa-views-apitest-components-apirequestbodyeditor-input-key" />
          <a-input v-model="field.value" :disabled="readonly" placeholder="value" @blur="save" data-testid="qa-views-apitest-components-apirequestbodyeditor-input-value" />
          <a-button
            status="danger"
            :disabled="readonly"
            @click="removeRow(local.body_config.fields, index)" data-testid="qa-views-apitest-components-apirequestbodyeditor-button-删除-2"
            >删除</a-button
          >
        </div>
        <a-button size="small" type="outline" :disabled="readonly" @click="addField" data-testid="qa-views-apitest-components-apirequestbodyeditor-button-增加字段"
          >增加字段</a-button
        >
      </template>

      <template v-else-if="local.body_type === 'raw'">
        <div class="mango-api-body-editor__title">Raw请求体</div>
        <div class="mango-api-body-editor__field mango-api-body-editor__field--full">
          <span>Content-Type：</span>
          <a-input
            v-model="local.body_config.content_type"
            allow-clear
            :disabled="readonly"
            placeholder="默认 application/json"
            @blur="save" data-testid="qa-views-apitest-components-apirequestbodyeditor-input-默认-application-json"
          />
        </div>
        <a-textarea
          v-model="local.body_config.body_text"
          class="mango-api-body-editor__textarea"
          allow-clear
          :disabled="readonly"
          :auto-size="{ minRows: 10, maxRows: 18 }"
          placeholder="请输入原始请求体"
          @blur="save" data-testid="qa-views-apitest-components-apirequestbodyeditor-textarea-请输入原始请求体"
        />
      </template>

      <template v-else-if="local.body_type === 'multipart'">
        <div class="mango-api-body-editor__title">Multipart普通字段</div>
        <div
          v-for="(field, index) in local.body_config.fields"
          :key="`field-${index}`"
          class="mango-api-body-editor__row"
        >
          <a-input v-model="field.key" :disabled="readonly" placeholder="key" @blur="save" data-testid="qa-views-apitest-components-apirequestbodyeditor-input-key-2" />
          <a-input v-model="field.value" :disabled="readonly" placeholder="value" @blur="save" data-testid="qa-views-apitest-components-apirequestbodyeditor-input-value-2" />
          <a-button
            status="danger"
            :disabled="readonly"
            @click="removeRow(local.body_config.fields, index)" data-testid="qa-views-apitest-components-apirequestbodyeditor-button-删除-3"
            >删除</a-button
          >
        </div>
        <a-button size="small" type="outline" :disabled="readonly" @click="addField" data-testid="qa-views-apitest-components-apirequestbodyeditor-button-增加普通字段"
          >增加普通字段</a-button
        >

        <div class="mango-api-body-editor__title mango-api-body-editor__title--gap">
          Multipart文件字段
        </div>
        <div
          v-for="(file, index) in local.body_config.files"
          :key="`file-${index}`"
          class="mango-api-body-editor__row mango-api-body-editor__file-row"
        >
          <a-input v-model="file.key" placeholder="文件字段key" @blur="saveCompletedFile(file)" data-testid="qa-views-apitest-components-apirequestbodyeditor-input-文件字段key" />
          <a-cascader
            v-model="file.file_path"
            :options="fileCascaderOptions"
            :loading="fileLoading"
            :disabled="readonly"
            placeholder="选择项目/产品/文件"
            allow-search
            allow-clear
            @change="(value) => handleFileChange(file, value)" data-testid="qa-views-apitest-components-apirequestbodyeditor-cascader-选择项目-产品-文件"
          />
          <a-button
            status="danger"
            :disabled="readonly"
            @click="removeRow(local.body_config.files, index)" data-testid="qa-views-apitest-components-apirequestbodyeditor-button-删除-4"
            >删除</a-button
          >
        </div>
        <a-button size="small" type="outline" :disabled="readonly" @click="addFile" data-testid="qa-views-apitest-components-apirequestbodyeditor-button-增加文件字段"
          >增加文件字段</a-button
        >
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { Message } from '@arco-design/web-vue'
  import { computed, nextTick, reactive, ref, watch } from 'vue'
  import { getUserFile } from '@/api/system/file_data'
  import { useProject } from '@/store/modules/get-project'
  import { parseLosslessJson, stringifyLosslessJson } from '@/utils/lossless-json'

  const props = defineProps<{
    protocolType?: string | null
    bodyType?: string | null
    bodyConfig?: Record<string, any> | null
    sseConfig?: Record<string, any> | null
    projectProductId?: string | number | null
    saving?: boolean
    bodyTypeReadonly?: boolean
    readonly?: boolean
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
  const wsDirectionOptions = [
    { label: '发送', value: 'send' },
    { label: '接收', value: 'receive' },
    { label: '等待', value: 'sleep' },
    { label: 'Ping', value: 'ping' },
  ]
  const wsMessageTypeOptions = [
    { label: 'JSON', value: 'json' },
    { label: '文本', value: 'text' },
    { label: '二进制(base64)', value: 'binary' },
  ]
  const wsUntilTypeOptions = [
    { label: 'JSONPath', value: 'jsonpath' },
    { label: '正则', value: 'regex' },
    { label: '文本包含', value: 'contains' },
    { label: '文本等于', value: 'text' },
  ]

  const local = reactive({
    protocol_type: 'http',
    body_type: 'none',
    body_config: {} as Record<string, any>,
    sse_config: {} as Record<string, any>,
  })
  const projectInfo = useProject()
  const fileOptions = ref<any[]>([])
  const fileLoading = ref(false)
  const fileResourcesLoaded = ref(false)
  const syncingFromProps = ref(false)
  const lastEmittedPayload = ref('')
  const jsonValueText = ref('{}')
  const bodyTypeReadonly = computed(() => props.bodyTypeReadonly === true)
  const readonly = computed(() => props.readonly === true)
  const fileCascaderOptions = computed(() => buildFileCascaderOptions())

  function defaultBodyConfig(bodyType: string, source?: Record<string, any> | null) {
    const config = source && typeof source === 'object' ? { ...source } : {}
    if (local.protocol_type === 'websocket') return defaultWebSocketConfig(config)
    if (bodyType === 'json') {
      const sourceType =
        config.source_type ||
        (Object.prototype.hasOwnProperty.call(config, 'body') ? 'value' : 'template')
      const body = config.body ?? {}
      return {
        source_type: sourceType,
        body_text: config.body_text || '',
        body,
        grpc_config: config.grpc_config,
      }
    }
    if (bodyType === 'form') return { fields: Array.isArray(config.fields) ? config.fields : [] }
    if (bodyType === 'raw') {
      return {
        content_type: config.content_type || 'application/json',
        body_text: config.body_text || '',
      }
    }
    if (bodyType === 'multipart') {
      const files = Array.isArray(config.files) ? config.files : []
      return {
        fields: Array.isArray(config.fields) ? config.fields : [],
        files: files.length ? files.map(normalizeFileRow) : [defaultFileRow()],
      }
    }
    return {}
  }

  function defaultWebSocketConfig(source?: Record<string, any> | null) {
    const config = source && typeof source === 'object' ? { ...source } : {}
    const messages = Array.isArray(config.messages) ? config.messages : []
    return {
      mode: config.mode || 'script',
      connect: {
        connect_timeout_seconds: config.connect?.connect_timeout_seconds ?? 10,
        read_greeting: Boolean(config.connect?.read_greeting),
        greeting_timeout_seconds: config.connect?.greeting_timeout_seconds ?? 5,
        ping_interval_seconds: config.connect?.ping_interval_seconds ?? null,
        ping_timeout_seconds: config.connect?.ping_timeout_seconds ?? null,
      },
      messages: messages.length
        ? messages.map(normalizeWsMessage)
        : [defaultWsMessage('send'), defaultWsMessage('receive')],
      close: {
        enabled: config.close?.enabled ?? true,
        code: config.close?.code ?? 1000,
        reason: config.close?.reason || 'case finished',
      },
    }
  }

  function defaultWsMessage(direction = 'send') {
    return normalizeWsMessage({ direction })
  }

  function normalizeWsMessage(message: Record<string, any>) {
    const direction = message.direction || 'send'
    const payload = message.payload ?? {}
    return {
      ...message,
      name: message.name || '',
      direction,
      message_type: message.message_type || 'json',
      payload_text:
        typeof message.payload_text === 'string'
          ? message.payload_text
          : typeof payload === 'string'
          ? payload
          : stringifyLosslessJson(payload, 2),
      timeout_seconds: message.timeout_seconds ?? 10,
      max_message_count: message.max_message_count ?? 1,
      seconds: message.seconds ?? 1,
      until: {
        type: message.until?.type || '',
        expression: message.until?.expression || '',
        method: message.until?.method || 'equals',
        expect: message.until?.expect || '',
      },
    }
  }

  function defaultFileRow() {
    return normalizeFileRow({ key: '', file_id: null, file_name: '' })
  }

  function normalizeFileRow(file: Record<string, any>) {
    return {
      ...file,
      project_product: file.project_product || '',
      file_path: file.file_path || (file.file_id ? `file:${file.file_id}` : ''),
    }
  }

  function syncLocal() {
    syncingFromProps.value = true
    try {
      local.protocol_type = props.protocolType || 'http'
      local.body_type = local.protocol_type === 'grpc' ? 'json' : props.bodyType || 'none'
      local.body_config = defaultBodyConfig(local.body_type, props.bodyConfig)
      jsonValueText.value = stringifyLosslessJson(local.body_config.body ?? {}, 2)
      local.sse_config = {
        max_duration_seconds: props.sseConfig?.max_duration_seconds ?? 30,
        max_event_count: props.sseConfig?.max_event_count ?? 100,
        end_event: props.sseConfig?.end_event || '',
        end_jsonpath: props.sseConfig?.end_jsonpath || '',
      }
    } finally {
      nextTick(() => {
        syncingFromProps.value = false
      })
    }
  }

  function addField() {
    if (readonly.value) return
    if (!Array.isArray(local.body_config.fields)) local.body_config.fields = []
    local.body_config.fields.push({ key: '', value: '' })
  }

  function addFile() {
    if (readonly.value) return
    if (!Array.isArray(local.body_config.files)) local.body_config.files = []
    local.body_config.files.push(defaultFileRow())
  }

  function addWsMessage(direction: string) {
    if (readonly.value) return
    if (!Array.isArray(local.body_config.messages)) local.body_config.messages = []
    local.body_config.messages.push(defaultWsMessage(direction))
    save()
  }

  function removeWsMessage(index: number) {
    if (readonly.value) return
    local.body_config.messages.splice(index, 1)
    save()
  }

  function handleWsDirectionChange(message: any) {
    if (readonly.value) return
    Object.assign(message, normalizeWsMessage(message))
    save()
  }

  function removeRow(rows: any[], index: number) {
    if (readonly.value) return
    rows.splice(index, 1)
    if (rows === local.body_config.files && rows.length === 0) {
      rows.push(defaultFileRow())
    }
    save()
  }

  async function handleBodyTypeChange() {
    if (readonly.value) return
    await nextTick()
    save()
  }

  async function handleJsonSourceTypeChange() {
    if (readonly.value) return
    await nextTick()
    save()
  }

  async function loadFileResources() {
    if (fileResourcesLoaded.value || fileLoading.value) return
    fileLoading.value = true
    try {
      await projectInfo.projectProductName()
      const res = await getUserFile({
        page: 1,
        pageSize: 10000,
      })
      fileOptions.value = Array.isArray(res.data) ? res.data : []
      fileResourcesLoaded.value = true
    } catch (error) {
      console.log(error)
    } finally {
      fileLoading.value = false
    }
  }

  function buildFileCascaderOptions() {
    const options = (projectInfo.projectProduct || []).map((project: any) => ({
      ...project,
      value: `project:${project.value}`,
      children: (project.children || []).map((product: any) => ({
        ...product,
        value: `project_product:${product.value}`,
        raw_product_id: product.value,
        children: [],
      })),
    }))
    const productMap = new Map<string, any>()
    options.forEach((project: any) => {
      ;(project.children || []).forEach((product: any) => {
        productMap.set(String(product.raw_product_id), product)
      })
    })
    fileOptions.value.forEach((item: any) => {
      const productId = getFileProjectProductId(item)
      const product = productMap.get(String(productId))
      if (!product) return
      product.children.push({
        label: `${item.name} / ID:${item.id}`,
        value: `file:${item.id}`,
        raw_file_id: item.id,
        raw_file_name: item.name,
        raw_product_id: productId,
        isLeaf: true,
      })
    })
    options.forEach((project: any) => {
      project.children = (project.children || []).map((product: any) => ({
        ...product,
        disabled: !product.children.length,
      }))
    })
    return options
  }

  function getFileProjectProductId(item: any) {
    return item?.project_product?.id ?? item?.project_product_id ?? item?.project_product ?? ''
  }

  function findFileOption(value: any, options = fileCascaderOptions.value): any {
    for (const item of options || []) {
      if (item.value === value) return item
      const matched = findFileOption(value, item.children || [])
      if (matched) return matched
    }
    return null
  }

  function parseFileId(value: any) {
    const leafValue = Array.isArray(value) ? value[value.length - 1] : value
    if (typeof leafValue !== 'string' || !leafValue.startsWith('file:')) return null
    const fileId = Number(leafValue.replace('file:', ''))
    return Number.isNaN(fileId) ? null : fileId
  }

  function handleFileChange(file: any, value: any) {
    if (readonly.value) return
    const leafValue = Array.isArray(value) ? value[value.length - 1] : value
    const selected = findFileOption(leafValue)
    const fileId = selected?.raw_file_id ?? parseFileId(value)
    if (!fileId) {
      handleFileClear(file)
      return
    }
    file.file_id = fileId
    file.file_name = selected?.raw_file_name || file.file_name || ''
    file.project_product = selected?.raw_product_id || file.project_product || ''
    file.file_path = `file:${fileId}`
    save()
  }

  function handleFileClear(file: any) {
    if (readonly.value) return
    file.file_id = null
    file.file_name = ''
    file.project_product = ''
    file.file_path = ''
    save()
  }

  function saveCompletedFile(file: any) {
    if (readonly.value) return
    if (file.key && file.file_id) {
      save()
    }
  }

  function buildBodyConfig() {
    if (local.protocol_type === 'websocket') {
      return buildWebSocketConfig()
    }
    if (local.body_type === 'none') return null
    if (local.body_type === 'json') {
      const extraConfig =
        local.protocol_type === 'grpc' && local.body_config.grpc_config
          ? { grpc_config: local.body_config.grpc_config }
          : {}
      if (local.body_config.source_type === 'value') {
        try {
          const body = parseLosslessJson(jsonValueText.value || '{}')
          local.body_config.body = body
          return {
            source_type: 'value',
            body,
            body_text: local.body_config.body_text || '',
            ...extraConfig,
          }
        } catch (error) {
          Message.error('JSON值必须是合法JSON')
          return false
        }
      }
      return {
        source_type: 'template',
        body_text: local.body_config.body_text || '',
        body: local.body_config.body ?? {},
        ...extraConfig,
      }
    }
    if (local.body_type === 'multipart') {
      return {
        fields: (local.body_config.fields || []).filter((item: any) => item.key),
        files: (local.body_config.files || [])
          .filter((item: any) => item.key && item.file_id)
          .map((item: any) => ({
            key: item.key,
            file_id: item.file_id,
            file_name: item.file_name || undefined,
            project_product: item.project_product || undefined,
          })),
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

  function buildWebSocketConfig() {
    const messages = (local.body_config.messages || []).map((message: any) => {
      const direction = message.direction || 'send'
      const result: any = {
        name: message.name || undefined,
        direction,
      }
      if (direction === 'send') {
        result.message_type = message.message_type || 'json'
        if (result.message_type === 'json') {
          try {
            result.payload = parseLosslessJson(message.payload_text || '{}')
          } catch (error) {
            result.payload = message.payload_text || ''
          }
        } else {
          result.payload = message.payload_text || ''
        }
      } else if (direction === 'receive') {
        result.timeout_seconds = message.timeout_seconds || 10
        result.max_message_count = message.max_message_count || 1
        if (message.until?.type) {
          result.until = {
            type: message.until.type,
            expression: message.until.expression || '',
            method: message.until.method || 'equals',
            expect: message.until.expect || '',
          }
        }
      } else if (direction === 'sleep') {
        result.seconds = message.seconds || 1
      } else if (direction === 'ping') {
        result.payload = message.payload_text || ''
      }
      return result
    })
    return {
      mode: 'script',
      connect: { ...local.body_config.connect },
      messages,
      close: { ...local.body_config.close },
    }
  }

  function save() {
    if (readonly.value || syncingFromProps.value) return
    const bodyConfig = buildBodyConfig()
    if (bodyConfig === false) return
    const payload = {
      body_type: local.body_type,
      body_config: bodyConfig,
      sse_config: local.protocol_type === 'sse' ? local.sse_config : null,
    }
    const payloadText = stringifyLosslessJson(payload)
    if (payloadText === lastEmittedPayload.value) return
    lastEmittedPayload.value = payloadText
    emit('save', payload)
  }

  watch(() => [props.protocolType, props.bodyType, props.bodyConfig, props.sseConfig], syncLocal, {
    deep: true,
    immediate: true,
  })
  watch(
    () => local.body_type,
    (value) => {
      if (value === 'multipart') {
        void loadFileResources()
      }
      if (syncingFromProps.value) return
      local.body_config = defaultBodyConfig(value, local.body_config)
      if (value === 'json') {
        jsonValueText.value = stringifyLosslessJson(local.body_config.body ?? {}, 2)
      }
    },
    { immediate: true }
  )

  watch(
    () => props.protocolType,
    (value) => {
      if (syncingFromProps.value) return
      local.protocol_type = value || 'http'
      if (['grpc', 'websocket'].includes(local.protocol_type) && local.body_type !== 'json') {
        local.body_type = 'json'
        local.body_config = defaultBodyConfig('json', local.body_config)
        save()
      } else if (local.protocol_type === 'websocket') {
        local.body_config = defaultWebSocketConfig(local.body_config)
        save()
      }
    }
  )
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

  .mango-api-body-editor__header {
    display: flex;
    min-width: 0;
    padding: 6px 10px;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }

  .mango-api-body-editor__heading {
    min-width: 0;
    flex: 1;
  }

  .mango-api-body-editor__heading-row {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 8px;
  }

  .mango-api-body-editor__heading-title {
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 20px;
  }

  .mango-api-body-editor__heading-subtitle,
  .mango-api-body-editor__content-subtitle {
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-api-body-editor__heading-subtitle {
    margin-top: 0;
    line-height: 16px;
  }

  .mango-api-body-editor__content-subtitle {
    margin-top: 2px;
    line-height: 18px;
  }

  .mango-api-body-editor__type-field {
    display: grid;
    width: min(320px, 42%);
    min-width: 260px;
    flex: none;
    grid-template-columns: 76px minmax(0, 1fr);
    align-items: center;
    gap: 8px;
  }

  .mango-api-body-editor__type-field > span {
    color: var(--m-muted);
    font-size: 13px;
    line-height: 20px;
    text-align: right;
    white-space: nowrap;
  }

  .mango-api-body-editor__row {
    grid-template-columns: minmax(120px, 0.35fr) minmax(180px, 1fr) max-content;
    margin-bottom: 8px;
  }

  .mango-api-body-editor__row:has(.arco-select:nth-child(2)) {
    grid-template-columns: minmax(120px, 0.25fr) minmax(200px, 0.45fr) minmax(160px, 0.3fr) max-content;
  }

  .mango-api-body-editor__file-row {
    grid-template-columns: minmax(120px, 0.25fr) minmax(320px, 0.9fr) max-content;
  }

  .mango-api-body-editor__ws-message {
    padding: 10px;
    margin-bottom: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }

  .mango-api-body-editor__ws-row {
    display: grid;
    grid-template-columns: minmax(140px, 1fr) 110px 150px max-content;
    gap: 8px;
    align-items: center;
  }

  .mango-api-body-editor__ws-condition {
    display: grid;
    grid-template-columns: repeat(2, minmax(260px, 1fr));
    gap: 10px 16px;
    margin-top: 8px;
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

  .mango-api-body-editor__content-section {
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .mango-api-body-editor__content-head {
    display: flex;
    min-width: 0;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 10px;
  }

  .mango-api-body-editor__content-head > div:first-child {
    min-width: 0;
    flex: 1;
  }

  .mango-api-body-editor__content-head .mango-api-body-editor__title {
    margin-bottom: 0;
    font-size: 14px;
    line-height: 22px;
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
    margin-top: 10px;
  }

  .mango-api-body-editor__content-head + .mango-api-body-editor__textarea {
    margin-top: 0;
  }

  .mango-api-body-editor__textarea :deep(textarea) {
    font-size: 13px;
    line-height: 1.65;
    tab-size: 2;
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

  .mango-api-body-editor__notice {
    display: grid;
    gap: 4px;
    padding: 10px 12px;
    margin-bottom: 10px;
    border: 1px solid var(--m-color-primary-light-3);
    border-radius: var(--m-radius-sm);
    background: var(--m-color-primary-light-1);
    color: var(--m-text-2);
    font-size: 13px;
    line-height: 20px;
  }

  .mango-api-body-editor__notice-title {
    color: var(--m-text);
    font-weight: 600;
  }

  @media (max-width: 900px) {
    .mango-api-body-editor__row,
    .mango-api-body-editor__row:has(.arco-select:nth-child(2)),
    .mango-api-body-editor__ws-row,
    .mango-api-body-editor__ws-condition,
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

  @media (max-width: 720px) {
    .mango-api-body-editor__header,
    .mango-api-body-editor__content-head {
      align-items: stretch;
      flex-direction: column;
      gap: 10px;
    }

    .mango-api-body-editor__type-field {
      width: 100%;
      min-width: 0;
      grid-template-columns: 76px minmax(0, 1fr);
    }

    .mango-api-body-editor__content-head :deep(.arco-radio-group) {
      align-self: flex-start;
    }
  }
</style>
