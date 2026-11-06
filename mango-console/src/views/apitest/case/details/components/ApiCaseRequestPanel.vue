<!-- eslint-disable vue/no-mutating-props -->
<template>
  <a-tabs :active-key="activeKey" @tab-click="emit('change', String($event))">
    <a-tab-pane key="00" title="请求头">
      <div class="request-header-panel">
        <TipMessage message="场景请求头优先，未配置时使用用例前置；前置函数可修改最终请求头" />
        <a-spin :loading="headersSaving" class="request-panel-spin">
          <div class="mango-case-global-table mango-case-global-table--headers">
            <div class="mango-case-global-table__head"
              ><span></span><span>Key</span><span>Value</span></div
            >
            <a-checkbox-group
              v-model="item.headers"
              class="mango-case-global-table__body"
              direction="vertical"
              :disabled="editLocked || headersSaving"
              @change="saveHeaders"
            >
              <a-checkbox v-for="header of headerOptions" :key="header.id" :value="header.id">
                <span class="mango-case-global-table__row">
                  <span class="mango-case-global-table__cell" :title="header.key">{{
                    header.key
                  }}</span>
                  <span class="mango-case-global-table__cell" :title="header.value">{{
                    header.value
                  }}</span>
                </span>
              </a-checkbox>
            </a-checkbox-group>
          </div>
        </a-spin>
      </div>
    </a-tab-pane>
    <a-tab-pane key="01" title="参数">
      <a-spin :loading="paramsSaving" class="request-panel-spin">
        <div class="m-2">
          <div class="request-editor-actions">
            <a-button
              size="small"
              type="outline"
              :disabled="editLocked || paramsSaving"
              @click="emit('edit-json', 'params', '参数', item)"
              >展开编辑</a-button
            >
          </div>
          <a-textarea
            v-model="item.params"
            allow-clear
            :disabled="editLocked || paramsSaving"
            :auto-size="{ minRows: 6 }"
            placeholder='请输入查询参数，例如：{"key": "value"} 或 case_id=21'
            @blur="saveParams"
          />
        </div>
      </a-spin>
    </a-tab-pane>
    <a-tab-pane key="02" title="请求体">
      <div class="m-2">
        <ApiRequestBodyEditor
          :protocol-type="protocolType"
          :body-type="bodyType"
          :body-config="item.body_config"
          :sse-config="item.sse_config"
          :project-product-id="projectProductId"
          :body-type-readonly="true"
          :readonly="editLocked"
          @save="saveBody"
        />
      </div>
    </a-tab-pane>
  </a-tabs>
</template>

<script setup lang="ts">
  /* eslint-disable vue/no-mutating-props */
  import { ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { useApiCaseParameterSave } from '../composables/useApiCaseAutoSave'
  import TipMessage from '@/components/feedback/TipMessage.vue'
  import ApiRequestBodyEditor from '../../../components/ApiRequestBodyEditor.vue'

  const props = withDefaults(
    defineProps<{
      item: any
      activeKey: string
      editLocked: boolean
      headerOptions?: any[]
      projectProductId?: string | number
      protocolType?: string
      bodyType?: string
    }>(),
    {
      headerOptions: () => [],
      protocolType: 'http',
      bodyType: 'none',
    }
  )
  const emit = defineEmits<{
    (event: 'change', value: string): void
    (event: 'edit-json', field: string, label: string, item: any): void
    (event: 'saving-change', saving: boolean): void
  }>()
  const headersSaving = ref(false)
  const putApiCaseDetailedParameter = useApiCaseParameterSave()
  const paramsSaving = ref(false)

  function setSaving(target: typeof headersSaving, saving: boolean) {
    target.value = saving
    emit('saving-change', saving)
  }

  async function saveHeaders(selectedValues: any) {
    if (props.editLocked || headersSaving.value) return
    const nextHeaders = Array.isArray(selectedValues) ? [...selectedValues] : []
    const persistedHeaders = Array.isArray(props.item.__persistedHeaders)
      ? [...props.item.__persistedHeaders]
      : []
    setSaving(headersSaving, true)
    try {
      const response = await putApiCaseDetailedParameter({
        id: props.item.id,
        headers: nextHeaders,
      })
      props.item.headers = nextHeaders
      props.item.__persistedHeaders = [...nextHeaders]
      if (response) Message.success(response.msg)
    } catch (error: any) {
      props.item.headers = persistedHeaders
      Message.error(error?.msg || '场景请求头保存失败，已恢复上一次配置')
    } finally {
      setSaving(headersSaving, false)
    }
  }

  async function saveParams() {
    if (props.editLocked || paramsSaving.value) return
    setSaving(paramsSaving, true)
    try {
      const response = await putApiCaseDetailedParameter({
        id: props.item.id,
        params: props.item.params === '' ? null : props.item.params,
      })
      if (response) Message.success(response.msg)
    } catch (error: any) {
      Message.error(error?.msg || '查询参数保存失败')
    } finally {
      setSaving(paramsSaving, false)
    }
  }

  async function saveBody(value: any) {
    if (props.editLocked) return
    const protocolExpectation = props.item.body_config?.protocol_expectation
    const bodyConfig = protocolExpectation
      ? { ...(value.body_config || {}), protocol_expectation: protocolExpectation }
      : value.body_config
    props.item.body_config = bodyConfig
    props.item.sse_config = value.sse_config
    try {
      const response = await putApiCaseDetailedParameter({
        id: props.item.id,
        body_config: bodyConfig,
        sse_config: value.sse_config,
      })
      if (response) Message.success(response.msg)
    } catch (error: any) {
      Message.error(error?.msg || '请求体保存失败')
    }
  }
</script>

<style scoped>
  .request-panel-spin {
    display: block;
    width: 100%;
  }
  .request-header-panel {
    display: flex;
    min-width: 0;
    padding: var(--m-page-gap);
    flex-direction: column;
    gap: var(--m-page-gap);
  }
  .request-editor-actions {
    display: flex;
    margin-bottom: var(--m-page-gap);
    justify-content: flex-end;
  }
  .mango-case-global-table__body {
    max-height: 260px;
  }
</style>
