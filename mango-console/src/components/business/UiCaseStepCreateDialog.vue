<template>
  <ModalDialog
    ref="dialogRef"
    title="新增执行编排"
    @confirm="submit"
    @cancel="reset"
  >
    <template #content>
      <a-form :model="form" layout="horizontal" class="mango-ui-case-step-create-form">
        <a-form-item required label="项目/产品">
          <a-cascader
            v-model="form.projectProduct"
            :loading="loading.products"
            :options="options.products"
            placeholder="请选择项目/产品"
            allow-search
            expand-trigger="hover"
            path-mode
            @change="onProductChange" data-testid="qa-components-business-uicasestepcreatedialog-cascader-请选择项目-产品"
          />
        </a-form-item>
        <a-form-item required label="模块">
          <a-select
            v-model="form.module"
            :disabled="!productId"
            :loading="loading.modules"
            :options="options.modules"
            placeholder="请选择模块"
            allow-search
            @change="onModuleChange" data-testid="qa-components-business-uicasestepcreatedialog-select-请选择模块"
          />
        </a-form-item>
        <a-form-item required label="页面/步骤">
          <a-cascader
            v-model="form.pageStep"
            :disabled="!form.module"
            :loading="loading.steps"
            :options="pageStepOptions"
            placeholder="请选择页面及页面步骤"
            allow-search
            expand-trigger="hover"
            path-mode
          />
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import { computed, reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import ModalDialog from '@/components/overlays/ModalDialog.vue'
  import {
    getUiPageStepAssetModules,
    getUiPageStepAssetProducts,
    getUiPageStepAssetSteps,
  } from '@/api/uitest/page-steps'
  import {
    getUiCaseStepsRefreshCacheData,
    postUiCaseStepsDetailed,
  } from '@/api/uitest/case-steps-detailed'

  const props = defineProps<{
    caseId: string | number
    caseStepCount: number
  }>()

  const emit = defineEmits<{
    (event: 'created'): void
  }>()

  const dialogRef = ref<{
    show: () => Promise<boolean>
    close: () => Promise<boolean>
    setConfirmLoading: (loading: boolean) => void
  } | null>(null)
  const form = reactive({
    projectProduct: [] as Array<string | number>,
    module: '' as string | number,
    pageStep: [] as Array<string | number>,
  })
  const loading = reactive({
    products: false,
    modules: false,
    steps: false,
  })
  const options = reactive({
    products: [] as any[],
    modules: [] as any[],
    steps: [] as any[],
  })

  const productId = computed(() => {
    const values = Array.isArray(form.projectProduct) ? form.projectProduct : []
    return values[values.length - 1] || ''
  })

  const pageStepOptions = computed(() => {
    const pageMap = new Map<string, any>()
    options.steps.forEach((step: any) => {
      const pageKey = `page:${step.page_id}`
      if (!pageMap.has(pageKey)) {
        pageMap.set(pageKey, {
          label: step.page_name,
          value: pageKey,
          children: [],
        })
      }
      pageMap.get(pageKey).children.push({
        label: step.step_name,
        value: step.step_id,
      })
    })
    return Array.from(pageMap.values())
  })

  async function open() {
    reset()
    await dialogRef.value?.show()
    await loadProducts()
  }

  function reset() {
    form.projectProduct = []
    form.module = ''
    form.pageStep = []
    options.modules = []
    options.steps = []
  }

  async function loadProducts() {
    loading.products = true
    try {
      const res = await getUiPageStepAssetProducts()
      options.products = Array.isArray(res.data) ? res.data : []
    } catch (error) {
      console.log(error)
      options.products = []
    } finally {
      loading.products = false
    }
  }

  async function onProductChange() {
    form.module = ''
    form.pageStep = []
    options.modules = []
    options.steps = []
    if (!productId.value || String(productId.value).startsWith('project:')) return
    loading.modules = true
    try {
      const res = await getUiPageStepAssetModules(productId.value)
      options.modules = Array.isArray(res.data) ? res.data : []
    } catch (error) {
      console.log(error)
    } finally {
      loading.modules = false
    }
  }

  async function onModuleChange() {
    form.pageStep = []
    options.steps = []
    if (!productId.value || !form.module) return
    loading.steps = true
    try {
      const res = await getUiPageStepAssetSteps(productId.value, form.module)
      options.steps = Array.isArray(res.data) ? res.data : []
    } catch (error) {
      console.log(error)
    } finally {
      loading.steps = false
    }
  }

  async function submit() {
    const pageStepId = form.pageStep[form.pageStep.length - 1]
    const selectedStep = options.steps.find(
      (item: any) => String(item.step_id) === String(pageStepId)
    )
    if (!productId.value) {
      Message.error('请选择项目/产品')
      dialogRef.value?.setConfirmLoading(false)
      return
    }
    if (!form.module) {
      Message.error('请选择模块')
      dialogRef.value?.setConfirmLoading(false)
      return
    }
    if (!selectedStep) {
      Message.error('请选择页面及页面步骤')
      dialogRef.value?.setConfirmLoading(false)
      return
    }
    try {
      const res = await postUiCaseStepsDetailed(
        {
          case: props.caseId,
          module: selectedStep.module_id,
          page: selectedStep.page_id,
          page_step: selectedStep.step_id,
          case_cache_data: [],
          case_cache_ass: [],
          case_sort: props.caseStepCount,
        },
        props.caseId
      )
      if (res.data?.id) {
        await getUiCaseStepsRefreshCacheData(res.data.id)
      }
      Message.success(res.msg || '页面步骤添加成功')
      await dialogRef.value?.close()
      emit('created')
    } catch (error) {
      console.log(error)
    } finally {
      dialogRef.value?.setConfirmLoading(false)
    }
  }

  defineExpose({ open })
</script>

<style scoped>
  .mango-ui-case-step-create-form {
    padding: 8px 12px 0;
  }

  .mango-ui-case-step-create-form :deep(.arco-form-item) {
    margin-bottom: 16px;
  }
</style>
