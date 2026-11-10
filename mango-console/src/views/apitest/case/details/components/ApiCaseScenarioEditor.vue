<template>
  <a-modal
    v-model:visible="visible"
    :title="title"
    :width="560"
    :on-before-ok="save"
    :closable="!saving"
    :mask-closable="!saving"
    :cancel-button-props="{ disabled: saving }"
    @cancel="close"
  >
    <a-form auto-label-width class="mango-simple-form" :model="draft" layout="horizontal">
      <a-form-item class="mango-simple-form-item"
        v-for="item of basicFormItems"
        v-show="isParameterFormItemVisible(item)"
        :key="item.key"
        :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
        :label="item.label"
      >
        <template v-if="item.type === 'input'">
          <a-input v-model="item.value" :placeholder="item.placeholder" />
        </template>
        <template v-else-if="item.type === 'select'">
          <div class="scenario-protocol-expectation-control">
            <a-select v-model="item.value" :options="item.optionItems" />
            <span class="scenario-allow-failure-control__hint">{{ item.placeholder }}</span>
          </div>
        </template>
        <template v-else-if="item.type === 'switch'">
          <div class="scenario-allow-failure-control">
            <a-switch v-model="item.value" />
            <span class="scenario-allow-failure-control__hint">{{ item.placeholder }}</span>
          </div>
        </template>
      </a-form-item>
      <a-collapse v-if="supportsHttpExpectation" v-model:active-key="advancedKeys" :bordered="false" class="mango-scenario-advanced">
        <a-collapse-item key="protocol" :header="draft.protocol_expectation_mode === 'auto' ? '高级配置（可选）' : '高级配置（已自定义）'">
          <a-form-item
            v-for="item of protocolFormItems"
            v-show="isParameterFormItemVisible(item)"
            :key="item.key"
            class="mango-simple-form-item"
            :class="item.required ? 'mango-form-item__require' : 'mango-form-item__no_require'"
            :label="item.label"
          >
            <div v-if="item.type === 'select'" class="scenario-protocol-expectation-control">
              <a-select v-model="item.value" :options="item.optionItems" />
              <span class="scenario-protocol-expectation-control__hint">{{ item.placeholder }}</span>
            </div>
            <a-input v-else v-model="item.value" :placeholder="item.placeholder" />
          </a-form-item>
        </a-collapse-item>
      </a-collapse>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
  import { computed, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { getFormItems } from '@/utils/datacleaning'
  import {
    postApiCaseDetailedParameter,
    postApiCaseDetailedParameterCopy,
    putApiCaseDetailedParameter,
  } from '@/api/apitest/case-detailed-parameter'
  import { createScenarioFormItems } from '../config'
  import { scenarioFormValues, scenarioSubmitPayload } from '../scenario-form'
  import type { ApiCaseStep, ApiCaseScenario, ScenarioEditorMode } from '../types'
  const props = defineProps<{ caseId: string | number; editLocked: boolean }>()
  const emit = defineEmits<{ (event: 'saved', stepId: string | number): void }>()
  const visible = ref(false)
  const saving = ref(false)
  const mode = ref<ScenarioEditorMode>('create')
  const selectedStep = ref<ApiCaseStep | null>(null)
  const editingId = ref<number | null>(null)
  const draft = reactive(scenarioFormValues())
  const formParameterItems = createScenarioFormItems()
  const basicFormItems = formParameterItems.filter(item => !String(item.key).startsWith('protocol_expectation_'))
  const protocolFormItems = formParameterItems.filter(item => String(item.key).startsWith('protocol_expectation_'))
  const advancedKeys = ref<string[]>([])
  const supportsHttpExpectation = computed(() => !['mcp', 'grpc', 'websocket'].includes(
    String(selectedStep.value?.api_info?.protocol_type || 'http').toLowerCase()
  ))
  for (const item of formParameterItems) {
    const key = item.key as keyof typeof draft
    Object.defineProperty(item, 'value', {
      enumerable: true,
      get: () => draft[key],
      set: (value) => Object.assign(draft, { [key]: value }),
    })
  }
  const title = computed(() =>
    mode.value === 'copy'
      ? '复制接口场景'
      : mode.value === 'edit'
      ? '编辑接口场景名称'
      : '增加接口场景'
  )
  let session = 0
  function close() {
    session++
    visible.value = false
  }
  function open(
    step: ApiCaseStep,
    action: ScenarioEditorMode = 'create',
    scenario?: ApiCaseScenario
  ) {
    if (saving.value || props.editLocked || !step?.api_info) return
    session++
    mode.value = action
    selectedStep.value = step
    editingId.value = scenario ? Number(scenario.id) : null
    Object.assign(draft, scenarioFormValues(scenario))
    advancedKeys.value = draft.protocol_expectation_mode === 'auto' ? [] : ['protocol']
    visible.value = true
  }
  function isParameterFormItemVisible(item: { key: string | number }) {
    const protocol = String(selectedStep.value?.api_info?.protocol_type || 'http').toLowerCase()
    if (['mcp', 'grpc', 'websocket'].includes(protocol))
      return !String(item.key).startsWith('protocol_expectation_')
    return item.key !== 'protocol_expectation_codes' || draft.protocol_expectation_mode === 'codes'
  }
  async function save(): Promise<boolean> {
    const step = selectedStep.value
    if (saving.value || props.editLocked || !visible.value || !step) return false
    if (
      !formParameterItems
        .filter(isParameterFormItemVisible)
        .every((item) => !item.validator || item.validator())
    )
      return false
    if (mode.value !== 'create' && editingId.value === null) return false
    const token = session
    const payload = scenarioSubmitPayload(
      getFormItems(formParameterItems),
      step,
      mode.value,
      editingId.value
    )
    saving.value = true
    try {
      const response = await (mode.value === 'copy'
        ? postApiCaseDetailedParameterCopy({ ...payload, id: Number(editingId.value) })
        : mode.value === 'create'
        ? postApiCaseDetailedParameter(payload)
        : putApiCaseDetailedParameter(payload))
      if (token !== session) return false
      Message.success(response.msg)
      emit('saved', step.id)
      close()
      return true
    } catch {
      return false
    } finally {
      saving.value = false
    }
  }
  watch(() => [props.caseId, props.editLocked], close)
  onBeforeUnmount(close)
  onDeactivated(close)
  defineExpose({ open, close })
</script>

<style scoped>
  .scenario-allow-failure-control {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .scenario-protocol-expectation-control {
    display: flex;
    width: 100%;
    flex-direction: column;
    gap: 6px;
  }

  .scenario-protocol-expectation-control__hint {
    color: var(--m-muted);
    font-size: 12px;
  }

  .scenario-allow-failure-control__hint {
    color: var(--m-warning);
  }
  .mango-scenario-advanced {
    width: 100%;
  }
</style>
