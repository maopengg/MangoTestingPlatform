<template>
  <a-modal modal-class="mango-simple-form-modal" :visible="visible" title="执行性能场景" :width="560" :ok-loading="submitting" :on-before-ok="confirm" @cancel="close" @update:visible="onVisibleChange">
    <template #default>
      <a-form class="mango-simple-form" ref="formRef" :model="draft" :disabled="submitting" layout="horizontal" auto-label-width>
        <a-form-item class="mango-simple-form-item"
          field="test_env"
          label="测试环境"
          required
          :rules="[{ required: true, message: '请选择测试环境' }]"
          ><a-select
            v-model="draft.test_env"
            :options="enumStore.environment_type"
            :field-names="fieldNames"
            placeholder="请选择目标环境"
        /></a-form-item>
        <a-form-item class="mango-simple-form-item"
          field="selected_executor_fingerprints"
          label="执行器"
          required
          :rules="[
            {
              required: true,
              type: 'array',
              message: `请选择 ${executorCount} 个执行器`,
            },
          ]"
          ><a-select
            v-model="draft.selected_executor_fingerprints"
            multiple
            allow-clear
            :loading="executorLoading"
            :options="executorOptions"
            :max-tag-count="3"
            :limit="Number(executorCount)"
            placeholder="必须选择足量执行器后才能开始"
        /></a-form-item>
        <a-alert
          v-if="draft.test_env !== undefined"
          :type="executorSelectionReady ? 'success' : 'warning'"
          class="mango-perf-executor-alert"
          >需要 {{ executorCount }} 个执行器，已选择
          {{ draft.selected_executor_fingerprints.length }} 个；每个节点至少需要
          {{ preflight?.required_per_node ?? '—' }}
          {{ String(preflight?.capacity_type || '').toUpperCase() }} 安全容量。</a-alert
        >
        <a-form-item class="mango-simple-form-item" label="请求记录">
          <a-space>
            <a-checkbox v-model="draft.capture_request">记录请求</a-checkbox>
            <a-checkbox v-model="draft.capture_response">记录响应</a-checkbox>
          </a-space>
        </a-form-item>
        <a-alert v-if="draft.capture_request || draft.capture_response" type="warning" class="mango-perf-profile-hint">
          每个执行器分别生成 CSV；单文件超过 100 MB 不上传。可能包含业务敏感数据，请按需开启。
        </a-alert>
        <a-form-item class="mango-simple-form-item"
          v-if="Number(draft.test_env) === 2"
          field="production_load_confirmed"
          label="生产风险确认"
          required
          :rules="[{ required: true, type: 'boolean', message: '请确认已获得生产环境发压授权' }]"
          ><a-checkbox v-model="draft.production_load_confirmed"
            >我确认已获得授权，并理解生产发压风险</a-checkbox
          ></a-form-item
        >
        <a-form-item class="mango-simple-form-item" field="remark" label="运行备注"
          ><a-textarea
            v-model="draft.remark"
            placeholder="本次执行目的、变更单号或关注点"
            :max-length="512"
            show-word-limit
        /></a-form-item>
      </a-form>
      <MangoRequestFeedback v-if="preflightError" :message="&quot;预检失败，请重试。&quot;"><template #action><a-button size="small" :loading="executorLoading" :disabled="submitting" @click="refreshPreflight">重试</a-button></template></MangoRequestFeedback>
    </template>
  </a-modal>

</template>

<script setup lang="ts">
  import { requestFailureMessage, reportLoadError } from '@/utils/load-error'
  import { computed, nextTick, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import type { FormInstance } from '@arco-design/web-vue'
  import { executePerfScenario, preflightPerfScenario } from '@/api/perf'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import { createScenarioExecutionDraft } from '../config'
  import { executionDraftError, executionPayload, executionSelectionReady, readExecutionRunId, readExecutorPreflight } from '../execution'
  import type { ExecutorCandidate, ExecutorPreflight } from '../types'

  const props = defineProps<{
    scenarioId: string
    contextVersion: number
    executorCount: number
    isContextCurrent: (version: number) => boolean
    saveConfiguration: (isCurrent: () => boolean) => Promise<boolean>
  }>()
  const emit = defineEmits<{
    (event: 'busy-change', busy: boolean): void
    (event: 'executed', runId: number, version: number): void
  }>()
  const enumStore = useEnum()
  const visible = ref(false)
  const submitting = ref(false)
  const executorLoading = ref(false)
  const preflightError = ref(false)
  const formRef = ref<FormInstance | null>(null)
  const draft = reactive(createScenarioExecutionDraft())
  const preflight = ref<ExecutorPreflight | null>(null)
  const executorCandidates = ref<ExecutorCandidate[]>([])
  const executorCount = computed(() => props.executorCount)
  const executorOptions = computed(() => executorCandidates.value.map(item => ({
    value: item.fingerprint,
    label: `${item.executor_name || item.fingerprint} · 可用 ${item.available} ${(preflight.value?.capacity_type || '').toUpperCase()}${item.calibrated ? ' · 已校准' : ' · 未校准'}`,
  })))
  const executorSelectionReady = computed(() => !executorLoading.value && !preflightError.value &&
    executionSelectionReady(draft, preflight.value, props.executorCount))
  let generation = 0, readVersion = 0, draftRevision = 0, updatingDraft = false

  function capture() {
    const current = generation, version = props.contextVersion, id = props.scenarioId
    return {
      id, version,
      isCurrent: () => visible.value && current === generation && id === props.scenarioId &&
        version === props.contextVersion && props.isContextCurrent(version),
    }
  }

  function close(): void {
    generation++
    readVersion++
    visible.value = false
    preflight.value = null
    executorCandidates.value = []
    preflightError.value = false
    executorLoading.value = false
  }

  async function open(): Promise<boolean> {
    close()
    if (!/^\d+$/.test(props.scenarioId) || Number(props.scenarioId) < 1 || !Number.isSafeInteger(Number(props.scenarioId)) ||
      !props.isContextCurrent(props.contextVersion)) return false
    updatingDraft = true
    Object.assign(draft, createScenarioExecutionDraft())
    updatingDraft = false
    visible.value = true
    const context = capture()
    await nextTick()
    if (!context.isCurrent()) return false
    formRef.value?.clearValidate()
    return true
  }

  function onVisibleChange(value: boolean): void { if (!value) close() }

  async function refreshPreflight(): Promise<boolean> {
    const context = capture(), request = ++readVersion
    preflight.value = null
    preflightError.value = false
    if (!context.isCurrent() || draft.test_env === undefined || !Number.isSafeInteger(draft.test_env) || draft.test_env < 0) {
      executorLoading.value = false
      return false
    }
    const payload = { test_env: draft.test_env, selected_executor_fingerprints: [...draft.selected_executor_fingerprints] }
    executorLoading.value = true
    try {
      const response = await preflightPerfScenario(context.id, payload)
      if (!context.isCurrent() || request !== readVersion) return false
      const result = readExecutorPreflight(response)
      preflight.value = result
      executorCandidates.value = result.candidates
      return true
    } catch (loadFailure0) {
      if (context.isCurrent() && request === readVersion) (reportLoadError(loadFailure0, "加载失败，请重试", false), preflightError.value = requestFailureMessage(loadFailure0, true, "预检失败，请重试。"))
      return false
    } finally {
      if (context.isCurrent() && request === readVersion) executorLoading.value = false
    }
  }

  watch(() => [draft.test_env, JSON.stringify(draft.selected_executor_fingerprints)] as const, (value, previous) => {
    if (updatingDraft || !visible.value) return
    if (value[0] !== previous[0]) {
      updatingDraft = true
      draft.selected_executor_fingerprints = []
      draft.production_load_confirmed = false
      updatingDraft = false
      executorCandidates.value = []
    }
    void refreshPreflight()
  }, { flush: 'sync' })
  watch(() => JSON.stringify(executionPayload(draft)), () => { draftRevision++ }, { flush: 'sync' })

  async function confirm(): Promise<boolean> {
    const context = capture()
    if (!context.isCurrent() || submitting.value || !formRef.value) return false
    const revision = draftRevision
    const isCurrent = () => context.isCurrent() && revision === draftRevision
    submitting.value = true
    emit('busy-change', true)
    try {
      const errors = await formRef.value.validate()
      if (!isCurrent() || errors) return false
      const message = executionDraftError(draft, props.executorCount)
      if (message) { Message.warning(message); return false }
      if (!executorSelectionReady.value) {
        Message.warning(`必须选择 ${props.executorCount} 个容量充足的执行器`)
        return false
      }
      const payload = executionPayload(draft)
      if (!(await props.saveConfiguration(isCurrent)) || !isCurrent()) return false
      // 保存可能改变负载和节点策略，执行前重新校验这次选择的容量。
      let fresh: ExecutorPreflight
      try {
        const response = await preflightPerfScenario(context.id, {
          test_env: payload.test_env, selected_executor_fingerprints: [...payload.selected_executor_fingerprints],
        })
        if (!isCurrent()) return false
        fresh = readExecutorPreflight(response)
      } catch (error) {
        if (isCurrent()) {
          preflight.value = null
          preflightError.value = requestFailureMessage(error, true, "预检失败，请重试。")
        }
        throw error
      }
      preflight.value = fresh
      executorCandidates.value = preflight.value.candidates
      if (!executionSelectionReady(draft, preflight.value, props.executorCount)) {
        Message.warning('执行器可用容量已变化，请重新选择')
        return false
      }
      const result = await executePerfScenario(context.id, payload)
      if (!isCurrent()) return false
      const runId = readExecutionRunId(result)
      emit('executed', runId, context.version)
      close()
      return true
    } catch {
      if (isCurrent()) Message.error('执行准备或启动失败，请重试')
      return false
    } finally {
      submitting.value = false
      emit('busy-change', false)
    }
  }

  function pause(): void { close() }
  function visibilityChanged(): void { if (document.visibilityState === 'hidden') pause() }
  watch(() => [props.scenarioId, props.contextVersion, props.executorCount], close, { flush: 'sync' })
  onMounted(() => document.addEventListener('visibilitychange', visibilityChanged))
  onDeactivated(pause)
  onBeforeUnmount(() => { close(); document.removeEventListener('visibilitychange', visibilityChanged) })
  defineExpose({ open, close })
</script>

<style scoped lang="less">
  .mango-perf-profile-hint,
  .mango-perf-executor-alert {
    margin-bottom: var(--m-page-gap);
  }
</style>
