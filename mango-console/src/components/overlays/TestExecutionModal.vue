<template>
  <ModalDialog modal-class="mango-simple-form-modal" ref="modalRef" :title="title" :width="560" @confirm="onConfirm" @cancel="onCancel">
    <template #content>
      <slot name="summary" />
      <a-form auto-label-width layout="horizontal" class="mango-simple-form" :model="form">
        <a-form-item class="mango-form-item__require mango-simple-form-item" label="任务名称">
          <a-input
            v-model="form.executionName"
            :disabled="!nameEditable || submitting"
            :max-length="128"
            :placeholder="namePlaceholder"
            show-word-limit
          />
        </a-form-item>
        <a-form-item class="mango-simple-form-item"
          :class="
            environmentSelectable ? 'mango-form-item__require' : 'mango-form-item__no_require'
          "
          label="测试环境"
        >
          <a-select
            v-if="environmentSelectable && environmentMultiple"
            v-model="form.testEnvs"
            :disabled="submitting"
            :field-names="fieldNames"
            :options="enumStore.environment_type"
            :placeholder="environmentPlaceholder"
            allow-search
            multiple
          />
          <a-select
            v-else-if="environmentSelectable"
            v-model="form.testEnv"
            :disabled="submitting"
            :field-names="fieldNames"
            :options="enumStore.environment_type"
            :placeholder="environmentPlaceholder"
            allow-search
          />
          <div v-else class="mango-execution-environments">
            <a-tag
              v-for="testEnv in form.testEnvs"
              :key="testEnv"
              :color="environmentColor(testEnv)"
              size="small"
            >
              {{ environmentName(testEnv) }}
            </a-tag>
            <span v-if="!form.testEnvs.length" class="mango-execution-environments__empty">
              未配置测试环境
            </span>
          </div>
          <template v-if="!environmentSelectable || environmentHint" #extra>
            {{ environmentHint || '每个测试环境将分别创建一份测试报告' }}
          </template>
        </a-form-item>
        <a-form-item v-if="versionSelectable" class="mango-form-item__require mango-simple-form-item" label="执行版本">
          <a-select v-model="form.executionVersion" :disabled="submitting" class="full-width">
            <a-option
              value="editing"
              data-testid="qa-components-overlays-testexecutionmodal-option-当前编辑态"
              >当前编辑态</a-option
            >
            <a-option
              value="prepublished"
              data-testid="qa-components-overlays-testexecutionmodal-option-预发布"
              >预发布（待审核修订）</a-option
            >
            <a-option
              value="published"
              data-testid="qa-components-overlays-testexecutionmodal-option-当前已发布"
              >当前已发布</a-option
            >
          </a-select>
          <template #extra> 编辑态执行当前配置；预发布固定待审核修订；已发布执行当前正式版本，不跨版本回退 </template>
        </a-form-item>
        <a-form-item class="mango-form-item__no_require mango-simple-form-item" label="API并发">
          <a-input-number
            v-model="form.apiConcurrencyLimit"
            :disabled="submitting"
            :min="1"
            :max="platformLimit"
            :precision="0"
            :step="1"
            allow-clear
            class="full-width"
            :placeholder="concurrencyPlaceholder"
          />
          <template #extra>
            {{ concurrencyHint }}；当前平台最大执行容量：{{ platformLimit }}
          </template>
        </a-form-item>
      </a-form>
    </template>
    <template v-if="$slots.footer" #footer>
      <slot name="footer" :confirm="onConfirm" />
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import { computed, onDeactivated, reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import ModalDialog from '@/components/overlays/ModalDialog.vue'

  interface TestExecutionConfig {
    executionName: string
    testEnv: number | null
    testEnvs?: number[]
    apiConcurrencyLimit: number | null
    executionVersion?: 'editing' | 'prepublished' | 'published'
  }

  const props = withDefaults(
    defineProps<{
      title?: string
      width?: string | number
      nameEditable?: boolean
      namePlaceholder?: string
      environmentPlaceholder?: string
      concurrencyPlaceholder?: string
      concurrencyHint?: string
      platformLimit: number
      versionSelectable?: boolean
      environmentSelectable?: boolean
      environmentMultiple?: boolean
      environmentHint?: string
    }>(),
    {
      title: '执行配置',
      nameEditable: false,
      namePlaceholder: '请输入本次执行的任务名称',
      environmentPlaceholder: '请选择本次执行的测试环境',
      concurrencyPlaceholder: '留空则使用平台最大执行容量',
      concurrencyHint: '留空则使用平台最大执行容量',
      versionSelectable: false,
      environmentSelectable: true,
      environmentMultiple: false,
      environmentHint: '',
    }
  )

  const emit = defineEmits<{
    (event: 'confirm', value: TestExecutionConfig): void
    (event: 'cancel'): void
  }>()

  const enumStore = useEnum()
  const submitting = ref(false)
  function environmentId(value: unknown): number | null {
    if (typeof value !== 'number' && !(typeof value === 'string' && /^\d+$/.test(value))) return null
    const id = Number(value)
    return Number.isSafeInteger(id) && id >= 0 ? id : null
  }
  const environments = computed(() => (Array.isArray(enumStore.environment_type) ? enumStore.environment_type : []).flatMap((entry: unknown) => {
    if (!entry || typeof entry !== 'object') return []
    const row = entry as { key?: unknown; title?: unknown }, id = environmentId(row.key)
    return id === null ? [] : [{ id, title: typeof row.title === 'string' ? row.title : `环境 ${id}` }]
  }))
  const modalRef = ref<InstanceType<typeof ModalDialog> | null>(null)
  const createForm = (): TestExecutionConfig & { testEnvs: number[] } => ({
    executionName: '',
    testEnv: null,
    testEnvs: [],
    apiConcurrencyLimit: null,
    executionVersion: 'editing',
  })
  const form = reactive(createForm())

  function show(value: TestExecutionConfig) {
    if (submitting.value) return Promise.resolve(false)
    Object.assign(form, createForm())
    form.executionName = typeof value.executionName === 'string' ? value.executionName : ''
    form.testEnv = environmentId(value.testEnv)
    form.testEnvs = Array.isArray(value.testEnvs) ? [...new Set(value.testEnvs.map(environmentId).filter((id): id is number => id !== null))] : []
    form.apiConcurrencyLimit = value.apiConcurrencyLimit
    form.executionVersion = value.executionVersion || 'editing'
    return modalRef.value?.show()
  }

  function close() {
    submitting.value = false
    Object.assign(form, createForm())
    return modalRef.value?.close()
  }

  function setConfirmLoading(loading: boolean) {
    submitting.value = loading
    modalRef.value?.setConfirmLoading(loading)
  }

  function onConfirm() {
    if (submitting.value) return
    if (!Number.isInteger(props.platformLimit) || props.platformLimit < 1) {
      Message.error('当前执行容量无效，请重新打开执行配置')
      setConfirmLoading(false)
      return
    }
    const executionName = form.executionName.trim()
    if (!executionName) {
      Message.error('请输入本次执行的任务名称')
      setConfirmLoading(false)
      return
    }
    if (props.environmentSelectable) {
      const selectedTestEnvs = props.environmentMultiple ? form.testEnvs : [form.testEnv]
      const validTestEnvs =
        selectedTestEnvs.length > 0 &&
        selectedTestEnvs.every(value => environmentId(value) !== null && environments.value.some(item => item.id === environmentId(value)))
      if (!validTestEnvs) {
        Message.error('请选择本次执行的测试环境')
        setConfirmLoading(false)
        return
      }
    } else if (!form.testEnvs.length) {
      Message.error('当前定时任务未配置测试环境')
      setConfirmLoading(false)
      return
    }
    const concurrency =
      form.apiConcurrencyLimit === null || form.apiConcurrencyLimit === undefined
        ? null
        : Number(form.apiConcurrencyLimit)
    if (
      concurrency !== null &&
      (!Number.isInteger(concurrency) || concurrency < 1 || concurrency > props.platformLimit)
    ) {
      Message.error(`API并发必须在 1 到 ${props.platformLimit} 之间`)
      setConfirmLoading(false)
      return
    }
    if (props.versionSelectable && !['editing', 'prepublished', 'published'].includes(form.executionVersion || '')) {
      Message.error('请选择执行版本')
      setConfirmLoading(false)
      return
    }
    setConfirmLoading(true)
    emit('confirm', {
      executionName,
      testEnv:
        props.environmentSelectable && !props.environmentMultiple ? Number(form.testEnv) : null,
      testEnvs:
        props.environmentSelectable && props.environmentMultiple
          ? form.testEnvs.map(Number)
          : [...form.testEnvs],
      apiConcurrencyLimit: concurrency,
      executionVersion: form.executionVersion,
    })
  }

  function onCancel() {
    close()
    emit('cancel')
  }
  onDeactivated(onCancel)

  defineExpose({ show, close, setConfirmLoading })

  function environmentName(value: number) {
    return (
      environments.value.find(item => item.id === value)?.title || `环境 ${value}`
    )
  }

  function environmentColor(value: number) {
    return enumStore.colors?.[value] || 'gray'
  }
</script>

<style scoped>
  .mango-execution-environments {
    display: flex;
    min-height: 32px;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--m-space-xs);
  }

  .mango-execution-environments__empty {
    color: var(--m-muted);
  }
</style>
