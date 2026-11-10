<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    :title="editingId === null ? '新增执行编排' : '编辑执行编排'"
    :width="560"
    :on-before-ok="save"
    :closable="!saving"
    :mask-closable="!saving"
    :cancel-button-props="{ disabled: saving }"
    @cancel="close"
  >
    <a-form auto-label-width class="mango-simple-form" :model="draft" layout="horizontal" :disabled="saving">
      <a-form-item class="mango-simple-form-item"
        v-for="item of formItems"
        :key="item.key"
        v-show="!item.hidden"
        :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
        :label="item.label"
      >
        <template v-if="item.type === 'input'">
          <a-input v-model="item.value" :placeholder="item.placeholder" />
        </template>
        <template v-else-if="item.type === 'cascader' && item.key === 'module'">
          <ProductModuleSelect
            v-model="item.value"
            :project-product-id="projectProductId"
            :placeholder="item.placeholder"
            @change="getModuleApi"
          />
        </template>
        <template v-else-if="item.type === 'select' && item.key === 'api_info'">
          <a-select
            v-model="item.value"
            :field-names="fieldNames"
            :options="apiOptions"
            :loading="optionsLoading"
            :placeholder="item.placeholder"
            allow-clear
            allow-search
            value-key="key"
            @change="loadApiInfoRevisions"
          />
        </template>
        <template v-else-if="item.type === 'select' && item.key === 'pinned_api_info_revision'">
          <a-select
            v-model="item.value"
            :field-names="fieldNames"
            :options="revisionOptions"
            :placeholder="item.placeholder"
            allow-clear
          />
        </template>
      </a-form-item>
      <ApiCaseStepTimingFields v-model="draft.is_recovery" />
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
  import { onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { getApiInfoName } from '@/api/apitest/info'
  import { postApiCaseDetailed, putApiCaseDetailed } from '@/api/apitest/case_detailed'
  import type { ApiCaseStep } from '../types'
  import { createStepFormItems } from '../config'
  import ApiCaseStepTimingFields from './ApiCaseStepTimingFields.vue'
  const props = defineProps<{
    caseId: string | number
    projectProductId: string | number
    editLocked: boolean
    stepCount: number
  }>()
  const emit = defineEmits<{ (event: 'saved'): void }>()
  const visible = ref(false),
    editingId = ref<string | number | null>(null),
    saving = ref(false),
    optionsLoading = ref(false)
  const draft = reactive<{
    module: string | number | null
    api_info: string | number | null
    pinned_api_info_revision: string | number | null
    is_recovery: boolean
  }>({ module: null, api_info: null, pinned_api_info_revision: null, is_recovery: false })
  const formItems = createStepFormItems()
  for (const item of formItems) {
    const key = item.key as keyof typeof draft
    Object.defineProperty(item, 'value', {
      enumerable: true,
      get: () => draft[key],
      set: (value) => Object.assign(draft, { [key]: value }),
    })
  }
  const apiOptions = ref<
    Array<{
      key: number
      title: string
      published_revision_id?: number
      published_version_label?: string
    }>
  >([])
  const revisionOptions = ref<Array<{ key: number; title: string }>>([])
  let optionRequest = 0,
    session = 0
  let executionConfig: Record<string, unknown> = {}
  function close() {
    session++
    optionRequest++
    visible.value = false
    optionsLoading.value = false
  }
  function open(step?: ApiCaseStep) {
    if (saving.value || props.editLocked) return
    close()
    editingId.value = step?.id ?? null
    executionConfig = { ...step?.execution_config }
    const module = step?.api_info.module
    const moduleId = typeof module === 'object' ? module?.id ?? null : module ?? null
    Object.assign(draft, {
      module: moduleId,
      api_info: step?.api_info.id ?? null,
      pinned_api_info_revision: step?.pinned_api_info_revision ?? null,
      is_recovery: Boolean(step?.execution_config?.is_recovery),
    })
    apiOptions.value = step
      ? [{ key: Number(step.api_info.id), title: step.api_info.name || '' }]
      : []
    revisionOptions.value = step?.pinned_api_info_revision
      ? [{ key: Number(step.pinned_api_info_revision), title: '当前绑定版本' }]
      : []
    visible.value = true
    if (moduleId) getModuleApi(moduleId, true)
  }
  function getModuleApi(moduleId: string | number, preserveSelection = false) {
    const apiInfoItem = formItems.find((item) => item.key === 'api_info')
    const revisionItem = formItems.find((item) => item.key === 'pinned_api_info_revision')
    const selectedOptions = preserveSelection ? [...apiOptions.value] : []
    if (!preserveSelection) {
      revisionOptions.value = []
      if (apiInfoItem) apiInfoItem.value = ''
      if (revisionItem) revisionItem.value = ''
      apiOptions.value = []
    }
    const token = ++optionRequest
    if (!moduleId) {
      optionsLoading.value = false
      return
    }
    optionsLoading.value = true
    getApiInfoName(moduleId)
      .then((response) => {
        if (token === optionRequest && visible.value) {
          const options: typeof apiOptions.value = response.data || []
          apiOptions.value = [
            ...options,
            ...selectedOptions.filter(
              (selected) => !options.some((option) => String(option.key) === String(selected.key))
            ),
          ]
        }
      })
      .catch(() => {})
      .finally(() => {
        if (token === optionRequest) optionsLoading.value = false
      })
  }

  function loadApiInfoRevisions(apiInfoId: number | string) {
    const revisionItem = formItems.find((item) => item.key === 'pinned_api_info_revision')
    revisionOptions.value = []
    if (revisionItem) revisionItem.value = ''
    if (!apiInfoId) return
    const selectedApi = apiOptions.value.find((item: any) => String(item.key) === String(apiInfoId))
    if (!selectedApi?.published_revision_id) {
      Message.warning('该接口未发布，不能添加到 Case')
      return
    }
    revisionOptions.value = [
      {
        key: selectedApi.published_revision_id,
        title: selectedApi.published_version_label || '当前发布版本',
      },
    ]
    if (revisionItem) revisionItem.value = selectedApi.published_revision_id
  }

  async function save(): Promise<boolean> {
    if (saving.value || props.editLocked || !props.caseId || !visible.value) return false
    if (!formItems.every((item) => !item.validator || item.validator())) return false
    const token = session,
      caseId = props.caseId,
      id = editingId.value
    const payload = {
      ...getFormItems(formItems),
      case: caseId,
      case_sort: props.stepCount,
      execution_config: { ...executionConfig, is_recovery: draft.is_recovery },
    }
    saving.value = true
    try {
      const response =
        id === null
          ? await postApiCaseDetailed(payload, caseId)
          : await putApiCaseDetailed(
              {
                id,
                api_info: draft.api_info!,
                pinned_api_info_revision: draft.pinned_api_info_revision!,
                execution_config: payload.execution_config,
              },
              caseId
            )
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
  watch(() => [props.caseId, props.projectProductId, props.editLocked], close)
  onBeforeUnmount(close)
  onDeactivated(close)
  defineExpose({ open, close })
</script>
