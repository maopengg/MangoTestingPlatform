<template>
  <a-modal :width="560" modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    :title="importing ? '导入接口' : editingId === null ? '新增' : '编辑'"
    :on-before-ok="save"
    :closable="!saving"
    :mask-closable="!saving"
    :cancel-button-props="{ disabled: saving }"
    @cancel="close"
  >
    <MangoPanelSpin :loading="detailLoading" class="mango-info-editor-loading mango-simple-form-content">
      <template v-if="loadFailed"><a-button size="small" @click="loadRecord">重新加载</a-button></template>
      <a-form auto-label-width class="mango-simple-form"
        v-else
        :model="draft"
        :disabled="saving || detailLoading"
        layout="horizontal"
      >
        <a-form-item
          v-if="!importing && draft.protocol_type === 'mcp'"
          label="工具名称"
          class="mango-form-item__require mango-simple-form-item"
        >
          <a-input v-model="draft.tool_name" placeholder="MCP 服务提供的工具名称" />
        </a-form-item>
        <a-form-item class="mango-simple-form-item"
          v-for="item of formFields"
          :key="item.key"
          :label="item.label"
          :class="item.required ? 'mango-form-item__require' : 'mango-form-item__no_require'"
        >
          <ProjectProductSelect
            v-if="item.type === 'cascader'"
            v-model="item.value"
            :disabled="saving || detailLoading"
            :placeholder="item.placeholder"
            @change="draft.module = null"
          />
          <ProductModuleSelect
            v-else-if="item.key === 'module'"
            v-model="item.value"
            :disabled="saving || detailLoading"
            :project-product-id="draft.project_product"
            :auto-clear="false"
            :placeholder="item.placeholder"
          />
          <a-select
            v-else-if="item.key === 'method'"
            v-model="item.value"
            :field-names="fieldNames"
            :options="methodOptions"
            :placeholder="item.placeholder"
            allow-clear
            allow-search
          />
          <a-select
            v-else-if="item.key === 'protocol_type'"
            v-model="item.value"
            :options="editingId === null ? apiProtocolCreateOptions : apiProtocolOptions"
            :placeholder="item.placeholder"
            allow-search
            @change="syncProtocol"
          />
          <a-select
            v-else-if="item.key === 'body_type'"
            v-model="item.value"
            :options="item.optionItems"
            :disabled="['mcp', 'grpc', 'websocket'].includes(draft.protocol_type)"
            :placeholder="item.placeholder"
            allow-search
          />
          <a-textarea
            v-else-if="item.key === 'curl_command'"
            v-model="item.value"
            :placeholder="item.placeholder"
            :auto-size="{ minRows: 3, maxRows: 5 }"
            allow-clear
          />
          <a-input v-else v-model="item.value" :placeholder="item.placeholder" />
        </a-form-item>
      </a-form>
    </MangoPanelSpin>
  </a-modal>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, reactive, ref, onBeforeUnmount, onDeactivated } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import { getApiInfo, postApiInfo, putApiInfo, postApiImportUrl } from '@/api/apitest/info'
  import { getOptionId } from '@/utils/business-format'
  import { cloneLosslessJson } from '@/utils/lossless-json'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import {
    apiProtocolCreateOptions,
    apiProtocolOptions,
    createFormItems,
    createImportFormItems,
    protocolMethodValues,
    protocolMethodTitles,
  } from '../config'
  import { createApiInfoDraft, apiInfoPayload, normalizeProtocolType } from '../form'
  import type {
    ApiInfoDraft,
    ApiInfoMetadataRecord,
    ApiEntityId,
    NavigationDefaults,
    McpBinding,
  } from '../types'
  const emit = defineEmits<{ (event: 'saved'): void }>()
  const enumStore = useEnum()
  const visible = ref(false),
    saving = ref(false),
    detailLoading = ref(false),
    loadFailed = ref(false),
    importing = ref(false),
    editingId = ref<ApiEntityId | null>(null)
  const loadingId = computed(() =>
    detailLoading.value && editingId.value !== null ? String(editingId.value) : ''
  )
  const draft = reactive(createApiInfoDraft())
  const regularFields = createFormItems(),
    importFields = createImportFormItems()
  const formFields = computed(() => (importing.value ? importFields : regularFields))
  let session = 0,
    readRequest = 0,
    binding: McpBinding = {}
  for (const item of [...regularFields, ...importFields]) {
    const key = item.key as keyof ApiInfoDraft
    Object.defineProperty(item, 'value', {
      enumerable: true,
      get: () => draft[key],
      set: (value) => Object.assign(draft, { [key]: value }),
    })
  }
  const methodOptions = computed(() => {
    const protocol = normalizeProtocolType(draft.protocol_type),
      target = protocolMethodValues[protocol]
    const options = enumStore.method || []
    if (target !== undefined) {
      const matches = options.filter((item) => Number(item.key) === target)
      return matches.length ? matches : [{ key: target, title: protocolMethodTitles[protocol] }]
    }
    return options.filter((item) => Number(item.key) >= 0 && Number(item.key) <= 6)
  })
  function syncProtocol() {
    const protocol = normalizeProtocolType(draft.protocol_type),
      target = protocolMethodValues[protocol]
    if (target !== undefined) draft.method = target
    else if (
      draft.method == null ||
        !methodOptions.value.some((item) => Number(item.key) === Number(draft.method))
    )
      draft.method = null
    if (protocol === 'websocket') draft.body_type = 'json'
  }
  function close() {
    session++
    readRequest++
    visible.value = false
    detailLoading.value = false
    loadFailed.value = false
  }
  function open(mode: 'create' | 'import', defaults: NavigationDefaults = {}, protocol = 'http') {
    if (saving.value) return
    close()
    binding = {}
    editingId.value = null
    importing.value = mode === 'import'
    const supported = apiProtocolCreateOptions.some((item) => item.value === protocol)
      ? protocol
      : 'http'
    Object.assign(draft, createApiInfoDraft(undefined, defaults, supported))
    syncProtocol()
    visible.value = true
  }
  async function openEdit(id: ApiEntityId) {
    if (saving.value) return
    close()
    binding = {}
    editingId.value = id
    importing.value = false
    visible.value = true
    Object.assign(draft, createApiInfoDraft())
    await loadRecord()
  }
  async function loadRecord() {
    const id = editingId.value
    if (id === null || !visible.value) return
    const token = session,
      request = ++readRequest
    detailLoading.value = true
    loadFailed.value = false
    try {
      const response = await getApiInfo({ id })
      if (token !== session || request !== readRequest) return
      const record: ApiInfoMetadataRecord | undefined = response.data?.[0]
      if (!record) {
        loadFailed.value = true
        return
      }
      binding = cloneLosslessJson(record.mcp_binding || {})
      Object.assign(draft, createApiInfoDraft(record))
      syncProtocol()
    } catch (loadFailure0) {
      if (token === session && request === readRequest) (reportLoadError(loadFailure0, "加载失败，请重试", false), loadFailed.value = true)
    } finally {
      if (token === session && request === readRequest) detailLoading.value = false
    }
  }
  async function save(): Promise<boolean> {
    if (!visible.value || saving.value || detailLoading.value || loadFailed.value) return false
    if (getOptionId(draft.project_product) == null || getOptionId(draft.module) == null) {
      Message.warning('请选择项目/产品和模块')
      return false
    }
    if (!formFields.value.every((item) => !item.validator || item.validator())) return false
    if (!importing.value && draft.protocol_type === 'mcp' && !draft.tool_name.trim()) {
      Message.warning('请填写 MCP 工具名称')
      return false
    }
    const token = session,
      id = editingId.value,
      payload = apiInfoPayload(draft, importing.value, binding),
      isImport = importing.value
    saving.value = true
    try {
      const response = await (isImport
        ? postApiImportUrl(payload)
        : id === null
        ? postApiInfo(payload)
        : putApiInfo({ ...payload, id }))
      if (token !== session) return false
      Message.success(response.msg)
      emit('saved')
      close()
      return true
    } catch {
      return false
    } finally {
      saving.value = false
    }
  }
  onBeforeUnmount(close)
  onDeactivated(close)
  defineExpose({ open, openEdit, close, loadingId })
</script>
<style scoped>
  .mango-info-editor-loading {
    display: block;
    width: 100%;
  }
</style>
