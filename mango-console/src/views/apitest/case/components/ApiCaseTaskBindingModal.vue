<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    :width="560"
    :on-before-ok="save"
    :closable="!saving"
    :mask-closable="!saving"
    :cancel-button-props="{ disabled: saving }"
    @cancel="close"
  >
    <template #title>绑定到手动定时任务</template>
    <a-form auto-label-width class="mango-simple-form" :model="draft" :disabled="saving" layout="horizontal">
      <a-form-item class="mango-form-item__require mango-simple-form-item" label="项目产品">
        <ProjectProductSelect
          v-model="draft.projectProduct"
          placeholder="请选择项目产品"
          @change="onScheduledProjectProductChange"
        />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="模块">
        <ProductModuleSelect
          v-model="draft.module"
          :auto-clear="false"
          :disabled="!getOptionId(draft.projectProduct)"
          :project-product-id="draft.projectProduct"
          :selectable-level="0"
          show-all-option
          placeholder="请选择模块分类（可选）"
          @change="onScheduledModuleChange"
        />
      </a-form-item>
      <a-form-item class="mango-form-item__require mango-simple-form-item" label="定时任务">
        <a-select
          v-model="draft.task"
          :disabled="!getOptionId(draft.projectProduct)"
          :field-names="fieldNames"
          :loading="optionsLoading"
          :options="taskOptions"
          allow-clear
          allow-search
          placeholder="请选择手动指定任务进行绑定"
          value-key="key"
          data-testid="qa-views-apitest-case-select-请选择手动指定任务进行绑定"
        />
      </a-form-item>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
  import { reactive, ref, onBeforeUnmount, onDeactivated } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { getOptionId } from '@/utils/business-format'
  import { fieldNames } from '@/setting'
  import { getSystemTasksName } from '@/api/system/tasks'
  import { postSystemTasksBatchSetCaseVersions } from '@/api/system/tasks_details'
  import type { TaskBindingItem, CaseEntityId } from '../types'
  const emit = defineEmits<{ (event: 'saved'): void }>()
  const visible = ref(false),
    saving = ref(false),
    optionsLoading = ref(false)
  const taskOptions = ref<Array<{ key: number; title: string }>>([])
  const draft = reactive<{
    projectProduct: CaseEntityId | CaseEntityId[] | null
    module: CaseEntityId | null
    task: number | null
  }>({ projectProduct: null, module: '__all__', task: null })
  let items: TaskBindingItem[] = [],
    session = 0,
    optionRequest = 0
  function close() {
    session++
    optionRequest++
    visible.value = false
    optionsLoading.value = false
  }
  function open(value: TaskBindingItem[]) {
    if (saving.value) return
    close()
    items = value.map((item) => ({ ...item }))
    taskOptions.value = []
    Object.assign(draft, { projectProduct: null, module: '__all__', task: null })
    visible.value = true
  }
  async function loadTasks() {
    const request = ++optionRequest,
      product = getOptionId(draft.projectProduct)
    draft.task = null
    taskOptions.value = []
    optionsLoading.value = false
    if (!product) return
    optionsLoading.value = true
    try {
      const module = getOptionId(draft.module)
      const response = await getSystemTasksName(
        product,
        module === '__all__' ? null : module,
        1,
        'manual'
      )
      if (request === optionRequest && visible.value) taskOptions.value = response.data || []
    } catch {
      if (request === optionRequest) taskOptions.value = []
    } finally {
      if (request === optionRequest) optionsLoading.value = false
    }
  }
  function onScheduledProjectProductChange() {
    draft.module = '__all__'
    void loadTasks()
  }
  function onScheduledModuleChange() {
    void loadTasks()
  }
  async function save(): Promise<boolean> {
    if (saving.value || !visible.value) return false
    if (!getOptionId(draft.projectProduct)) {
      Message.warning('请选择项目产品')
      return false
    }
    if (!draft.task) {
      Message.warning('请选择定时任务')
      return false
    }
    if (!items.length) return false
    const token = session,
      target = draft.task,
      snapshot = items.map((item) => ({ ...item }))
    saving.value = true
    try {
      const response = await postSystemTasksBatchSetCaseVersions(snapshot, target, 1)
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
  defineExpose({ open, close })
</script>
