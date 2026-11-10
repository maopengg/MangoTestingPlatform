<template>
  <a-modal modal-class="mango-simple-form-modal" :visible="visible" title="新建性能场景" :width="560" :unmount-on-close="true" :ok-loading="submitting" :on-before-ok="confirm" @cancel="close" @update:visible="onVisibleChange">

      <a-form class="mango-simple-form" ref="formRef" :model="draft" layout="horizontal" auto-label-width :disabled="submitting">
        <a-grid class="mango-simple-form-fields" :cols="2" :col-gap="12" :row-gap="4">
          <a-grid-item class="mango-simple-form-fields"
            ><a-form-item
              field="name"
              label="场景名称"
              class="mango-draft-item__require mango-simple-form-item"
              :rules="[{ required: true, message: '请输入场景名称' }]"
              ><a-input
                v-model="draft.name"
                placeholder="请输入便于识别的场景名称"
                :max-length="128" /></a-form-item
          ></a-grid-item>
          <a-grid-item class="mango-simple-form-fields"
            ><a-form-item
              field="project_product"
              label="项目产品"
              class="mango-draft-item__require mango-simple-form-item"
              :rules="[{ required: true, message: '请选择项目产品' }]"
              ><ProjectProductSelect v-model="draft.project_product" @change="draft.module = null" /></a-form-item
          ></a-grid-item>
          <a-grid-item class="mango-simple-form-fields"
            ><a-form-item
              field="module"
              label="产品模块"
              class="mango-draft-item__require mango-simple-form-item"
              :rules="[{ required: true, message: '请选择产品模块' }]"
              ><ProductModuleSelect
                v-model="draft.module"
                :project-product-id="selectionId(draft.project_product)" /></a-form-item
          ></a-grid-item>
          <a-grid-item class="mango-simple-form-fields"
            ><a-form-item
              field="engine"
              label="执行引擎"
              class="mango-draft-item__require mango-simple-form-item"
              :rules="[{ required: true, message: '请选择执行引擎' }]"
              ><a-select v-model="draft.engine" :options="engineOptions" placeholder="请选择执行引擎" /></a-form-item
          ></a-grid-item>
          <a-grid-item class="mango-simple-form-fields"
            ><a-form-item
              field="load_type"
              label="负载模型"
              class="mango-draft-item__require mango-simple-form-item"
              :rules="[{ required: true, message: '请选择负载模型' }]"
              ><a-select
                v-model="draft.load_type"
                :options="loadTypeOptions"
                placeholder="请选择负载模型" /></a-form-item
          ></a-grid-item>
          <a-grid-item class="mango-simple-form-fields"
            ><a-form-item
              field="default_executor_count"
              label="执行器数"
              class="mango-draft-item__require mango-simple-form-item"
              :rules="[{ required: true, message: '请输入执行器数量' }]"
              ><a-input-number
                v-model="draft.default_executor_count"
                :min="1"
                :max="100"
                placeholder="请输入 1-100" /></a-form-item
          ></a-grid-item>
          <a-grid-item class="mango-simple-form-fields" :span="2"
            ><a-form-item class="mango-simple-form-item" field="description" label="说明"
              ><a-textarea
                v-model="draft.description"
                placeholder="可填写测试目标、业务范围或注意事项"
                :max-length="1000"
                show-word-limit
                :auto-size="{ minRows: 2, maxRows: 4 }" /></a-form-item
          ></a-grid-item>
        </a-grid>
      </a-form>
    
  </a-modal>
</template>

<script setup lang="ts">
  import { nextTick, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from 'vue'
  import type { FormInstance } from '@arco-design/web-vue'
  import { Message } from '@arco-design/web-vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import type { NavigationCreateSelection } from '@/utils/navigation-create-defaults'
  import { createPerfScenario } from '@/api/perf'
  import { engineOptions, loadTypeOptions } from '../config'
  import { createScenarioDraft, createdScenarioId, scenarioCreatePayload, selectionId } from '../create'

  const props = defineProps<{ contextVersion: number; isContextCurrent: (version: number) => boolean }>()
  const emit = defineEmits<{ (event: 'created', id: number, contextVersion: number): void }>()
  const visible = ref(false), submitting = ref(false)
  const draft = reactive(createScenarioDraft())
  const formRef = ref<FormInstance | null>(null)
  let generation = 0, openedVersion = 0, disposed = false
  const current = (window: number) => !disposed && visible.value && generation === window &&
    props.isContextCurrent(openedVersion) && (typeof document === 'undefined' || document.visibilityState !== 'hidden')

  async function open(selection?: NavigationCreateSelection): Promise<boolean> {
    if (disposed || !props.isContextCurrent(props.contextVersion)) return false
    const window = ++generation
    openedVersion = props.contextVersion
    Object.assign(draft, createScenarioDraft(selection), { module: null })
    visible.value = true
    await nextTick()
    if (!current(window)) return false
    if (selectionId(draft.project_product) === selectionId(selection?.projectProduct) && !draft.module)
      draft.module = selectionId(selection?.module)
    formRef.value?.clearValidate()
    return true
  }
  function close(): void { generation++; visible.value = false }
  function onVisibleChange(value: boolean): void { if (!value) close() }
  async function confirm(): Promise<boolean> {
    if (submitting.value || !current(generation) || !formRef.value) return false
    const window = generation, version = openedVersion
    submitting.value = true
    try {
      let payload: Record<string, unknown>
      try { payload = scenarioCreatePayload(draft) }
      catch (error) { Message.warning(error instanceof Error ? error.message : '请检查场景配置'); return false }
      const errors = await formRef.value.validate()
      if (errors || !current(window)) return false
      const response = await createPerfScenario(payload)
      if (!current(window)) return false
      const id = createdScenarioId(response)
      Message.success('场景已创建')
      close()
      emit('created', id, version)
      return true
    } catch {
      if (current(window)) Message.error('创建场景失败，请重试')
      return false
    } finally { submitting.value = false }
  }
  function visibilityChanged(): void { if (document.visibilityState === 'hidden') close() }
  watch(() => props.contextVersion, close, { flush: 'sync' })
  onMounted(() => { if (typeof document !== 'undefined') document.addEventListener('visibilitychange', visibilityChanged) })
  onDeactivated(close)
  onBeforeUnmount(() => {
    disposed = true
    close()
    if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', visibilityChanged)
  })
  defineExpose({ open, close })
</script>

