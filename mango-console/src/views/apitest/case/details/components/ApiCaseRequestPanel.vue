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
              v-model="draft.headers"
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
            v-model="draft.params"
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
          :body-config="draft.body_config"
          :sse-config="draft.sse_config"
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
  import { useApiCaseScenarioDraft } from '../composables/useApiCaseScenarioDraft'
  import type { ApiCaseScenario, ScenarioPatch } from '../types'
  import { ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { useApiCaseParameterSave } from '../composables/useApiCaseAutoSave'
  import TipMessage from '@/components/feedback/TipMessage.vue'
  import ApiRequestBodyEditor from '../../../components/ApiRequestBodyEditor.vue'

  const props = withDefaults(
    defineProps<{
      item: ApiCaseScenario
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
    (event: 'patch', patch: ScenarioPatch): void
    (event: 'edit-json', field: string, label: string, item: ApiCaseScenario): void
    (event: 'saving-change', saving: boolean): void
  }>()
  const headersSaving = ref(false)
  const persistParameter = useApiCaseParameterSave()
  const { draft, save: putApiCaseDetailedParameter } = useApiCaseScenarioDraft(
    () => props.item,
    (patch) => emit('patch', patch),
    persistParameter,
    () => props.editLocked
  )
  const paramsSaving = ref(false)
  const bodySaving = ref(false)

  function setSaving(target: typeof headersSaving, saving: boolean) {
    target.value = saving
    emit('saving-change', saving)
  }

  async function saveHeaders(selectedValues: any) {
    const scenario = draft.value
    if (props.editLocked || headersSaving.value) return
    const nextHeaders = Array.isArray(selectedValues) ? [...selectedValues] : []
    const persistedHeaders = Array.isArray(scenario.__persistedHeaders)
      ? [...scenario.__persistedHeaders]
      : []
    setSaving(headersSaving, true)
    try {
      const response = await putApiCaseDetailedParameter({
        id: scenario.id,
        headers: nextHeaders,
      })
      scenario.headers = nextHeaders
      scenario.__persistedHeaders = [...nextHeaders]
      if (response) Message.success(response.msg)
    } catch (error: any) {
      scenario.headers = persistedHeaders
      Message.error(error?.msg || '场景请求头保存失败，已恢复上一次配置')
    } finally {
      setSaving(headersSaving, false)
    }
  }

  async function saveParams() {
    const scenario = draft.value
    if (props.editLocked || paramsSaving.value) return
    setSaving(paramsSaving, true)
    try {
      const response = await putApiCaseDetailedParameter({
        id: scenario.id,
        params: scenario.params === '' ? null : scenario.params,
      })
      if (response) Message.success(response.msg)
    } catch (error: any) {
      Message.error(error?.msg || '查询参数保存失败')
    } finally {
      setSaving(paramsSaving, false)
    }
  }

  async function saveBody(value: any) {
    const scenario = draft.value
    if (props.editLocked || bodySaving.value) return
    setSaving(bodySaving, true)
    const protocolExpectation = scenario.body_config?.protocol_expectation
    const bodyConfig = protocolExpectation
      ? { ...(value.body_config || {}), protocol_expectation: protocolExpectation }
      : value.body_config
    scenario.body_config = bodyConfig
    scenario.sse_config = value.sse_config
    try {
      const response = await putApiCaseDetailedParameter({
        id: scenario.id,
        body_config: bodyConfig,
        sse_config: value.sse_config,
      })
      if (response) Message.success(response.msg)
    } catch (error: any) {
      Message.error(error?.msg || '请求体保存失败')
    } finally {
      setSaving(bodySaving, false)
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
