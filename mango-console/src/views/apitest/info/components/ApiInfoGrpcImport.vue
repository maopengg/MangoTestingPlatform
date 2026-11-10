<template>
  <a-modal :width="560" modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    title="导入 gRPC Method"
    :on-before-ok="save"
    :closable="!saving"
    :mask-closable="!saving"
    :cancel-button-props="{ disabled: saving }"
    @cancel="close"
  >
    <div class="mango-grpc-import-tip"
      >导入后为编辑态，调试成功并发布后可绑定 API Case。当前仅支持 Unary RPC，流式 Method
      不可导入执行。</div
    >
    <a-form auto-label-width class="mango-simple-form" :model="draft" :disabled="saving || syncing" layout="horizontal">
      <a-form-item class="mango-simple-form-item" label="项目/产品"
        ><ProjectProductSelect
          v-model="draft.project_product_id"
          :disabled="saving || syncing"
          placeholder="默认使用服务定义中的项目/产品"
          @change="draft.module_id = null"
      /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="模块"
        ><ProductModuleSelect
          v-model="draft.module_id"
          :disabled="saving || syncing"
          :project-product-id="draft.project_product_id"
          :auto-clear="false"
          placeholder="默认使用服务定义中的模块"
      /></a-form-item>
      <a-form-item label="gRPC 服务" class="mango-form-item__require mango-simple-form-item">
        <a-select
          v-model="draft.service_id"
          :options="serviceOptions"
          :loading="servicesLoading"
          placeholder="请选择gRPC服务定义"
          allow-search
          allow-clear
          @change="onServiceChange"
        />
        <a-button v-if="servicesFailed" size="small" @click="loadServices">重试</a-button>
      </a-form-item>
      <a-form-item label="gRPC Method" class="mango-form-item__require mango-simple-form-item">
        <a-space direction="vertical" fill>
          <a-button
            size="small"
            :loading="syncing"
            :disabled="draft.service_id == null || saving"
            @click="syncMethods"
            >同步 Method</a-button
          >
          <a-select
            v-model="draft.method_id"
            :options="methodOptions"
            :loading="methodsLoading"
            :disabled="draft.service_id == null"
            placeholder="请选择要导入的Method"
            allow-search
          />
          <a-button v-if="methodsFailed" size="small" @click="loadMethods">重试读取</a-button>
        </a-space>
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="gRPC 地址"
        ><a-input
          v-model="draft.grpc_target"
          placeholder="可选，例如 127.0.0.1:50051；留空使用测试对象地址"
          allow-clear
      /></a-form-item>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, reactive, ref, onBeforeUnmount, onDeactivated } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import {
    getGrpcServices,
    getGrpcMethods,
    postGrpcMethodSync,
    postGrpcMethodImportApiInfo,
  } from '@/api/apitest/info'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { getOptionId } from '@/utils/business-format'
  import { grpcStreamingLabel } from '../form'
  import type { ApiEntityId, GrpcService, GrpcMethod } from '../types'
  const emit = defineEmits<{ (event: 'saved'): void }>()
  const visible = ref(false),
    saving = ref(false),
    syncing = ref(false),
    servicesLoading = ref(false),
    methodsLoading = ref(false),
    servicesFailed = ref(false),
    methodsFailed = ref(false)
  const services = ref<GrpcService[]>([]),
    methods = ref<GrpcMethod[]>([])
  const draft = reactive<{
    project_product_id: ApiEntityId | ApiEntityId[] | null
    module_id: ApiEntityId | null
    service_id: ApiEntityId | null
    method_id: ApiEntityId | null
    grpc_target: string
  }>({
    project_product_id: null,
    module_id: null,
    service_id: null,
    method_id: null,
    grpc_target: '',
  })
  let session = 0,
    servicesRequest = 0,
    methodsRequest = 0
  const serviceOptions = computed(() =>
    services.value.map((item) => ({
      label: `${item.name || item.service_name || item.id} / ${item.service_name || '-'}`,
      value: item.id,
    }))
  )
  const methodOptions = computed(() =>
    methods.value.map((item) => {
      const streaming = grpcStreamingLabel(item)
      return {
        label: `${item.full_method || item.name || item.id}${
          streaming ? `（${streaming}，暂不支持执行）` : ''
        }${item.imported_api_info_id ? '（已导入）' : ''}`,
        value: item.id,
        disabled: Boolean(streaming || item.imported_api_info_id),
      }
    })
  )
  function close() {
    session++
    servicesRequest++
    methodsRequest++
    visible.value = false
    servicesLoading.value = false
    methodsLoading.value = false
  }
  async function open() {
    if (saving.value || syncing.value) return
    close()
    Object.assign(draft, {
      project_product_id: null,
      module_id: null,
      service_id: null,
      method_id: null,
      grpc_target: '',
    })
    services.value = []
    methods.value = []
    servicesFailed.value = false
    methodsFailed.value = false
    visible.value = true
    await loadServices()
  }
  async function loadServices() {
    const request = ++servicesRequest
    servicesLoading.value = true
    servicesFailed.value = false
    try {
      const response = await getGrpcServices({ page: 1, pageSize: 200 })
      if (request === servicesRequest && visible.value) services.value = response.data || []
    } catch (loadFailure0) {
      if (request === servicesRequest) (reportLoadError(loadFailure0, "加载失败，请重试", false), servicesFailed.value = true)
    } finally {
      if (request === servicesRequest) servicesLoading.value = false
    }
  }
  async function onServiceChange(serviceId: ApiEntityId | null) {
    draft.service_id = serviceId
    const service = services.value.find((item) => String(item.id) === String(serviceId))
    if (service) {
      draft.project_product_id = service.project_product_id ?? draft.project_product_id
      draft.module_id = service.module_id ?? draft.module_id
    }
    draft.method_id = null
    await loadMethods()
  }
  async function loadMethods() {
    const request = ++methodsRequest,
      service = draft.service_id
    methods.value = []
    methodsFailed.value = false
    methodsLoading.value = false
    if (service == null) return
    methodsLoading.value = true
    try {
      const response = await getGrpcMethods({ page: 1, pageSize: 500, service })
      if (request === methodsRequest && visible.value) methods.value = response.data || []
    } catch (loadFailure0) {
      if (request === methodsRequest) (reportLoadError(loadFailure0, "加载失败，请重试", false), methodsFailed.value = true)
    } finally {
      if (request === methodsRequest) methodsLoading.value = false
    }
  }
  async function syncMethods() {
    if (draft.service_id == null || syncing.value || saving.value || !visible.value) return
    const token = session,
      service = draft.service_id
    syncing.value = true
    try {
      await postGrpcMethodSync({ grpc_service_id: service })
      if (token !== session || service !== draft.service_id) return
      Message.success('gRPC Method同步完成')
      draft.method_id = null
      await loadMethods()
    } catch {
      /* 公共请求层反馈错误，允许再次同步。 */
    } finally {
      syncing.value = false
    }
  }
  async function save(): Promise<boolean> {
    if (!visible.value || saving.value || syncing.value || methodsLoading.value) return false
    const method = methods.value.find((item) => String(item.id) === String(draft.method_id))
    if (!method || method.imported_api_info_id || grpcStreamingLabel(method)) {
      Message.warning('请选择未导入且支持执行的 gRPC Method')
      return false
    }
    const token = session,
      payload = {
        grpc_method_id: method.id,
        project_product_id: getOptionId(draft.project_product_id) ?? undefined,
        module_id: getOptionId(draft.module_id) ?? undefined,
        grpc_target: draft.grpc_target.trim() || undefined,
      }
    saving.value = true
    try {
      await postGrpcMethodImportApiInfo(payload)
      if (token !== session) return false
      Message.success('gRPC Method已导入编辑态，请调试成功后再发布')
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
  defineExpose({ open, close })
</script>
<style scoped>
  .mango-grpc-import-tip {
    padding: var(--m-card-padding);
    margin-bottom: var(--m-card-padding);
    background: var(--m-surface-soft);
    color: var(--m-muted);
    border-radius: var(--m-radius-sm);
    font-size: 13px;
    line-height: 1.6;
  }
</style>
