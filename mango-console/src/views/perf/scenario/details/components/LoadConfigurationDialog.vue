<template>
  <a-modal modal-class="mango-simple-form-modal" :visible="visible" title="编辑负载配置" :width="560" :ok-loading="confirming" :on-before-ok="confirm" @cancel="close" @update:visible="onVisibleChange">
    <template #default>
      <a-form ref="formRef" :model="draft" :disabled="confirming" class="mango-perf-load-form mango-simple-form" layout="horizontal" auto-label-width>
        <a-form-item field="profile" label="压测方案" required class="mango-perf-load-form__wide mango-simple-form-item"
          :rules="[{ required: true, message: '请选择压测方案' }]">
          <a-select v-model="draft.profile" :options="loadProfileOptions" @change="selectLoadProfile" />
        </a-form-item>
        <a-alert type="info" class="mango-perf-profile-hint mango-perf-load-form__wide">{{ loadProfileHint }}</a-alert>
        <a-form-item
          field="name"
          class="mango-perf-load-form__wide mango-simple-form-item"
          label="配置名称"
          required
          :rules="[{ required: true, message: '请输入配置名称' }]"
          ><a-input v-model="draft.name" :max-length="64" placeholder="例如：短稳态负载"
        /></a-form-item>
        <a-form-item class="mango-simple-form-item"
          v-if="showFixedDuration"
          field="duration_seconds"
          :label="draft.profile === 'fixed_iterations' ? '截止时间' : '持续时间'"
          required
          :rules="[{ required: true, message: '请输入持续时间' }]"
          ><a-input-number v-model="draft.duration_seconds" :min="1"
            ><template #suffix>秒</template></a-input-number
          ></a-form-item
        >
        <a-form-item class="mango-simple-form-item"
          v-if="!isRateProfile"
          field="target_users"
          :label="draft.profile === 'spike' ? '峰值并发' : '目标并发'"
          required
          :rules="[{ required: true, message: '请输入目标并发用户数' }]"
          ><a-input-number v-model="draft.target_users" :min="1"
        /></a-form-item>
        <a-form-item class="mango-simple-form-item" v-if="draft.profile === 'fixed_iterations'" field="total_iterations" label="Case 执行次数" required
          :rules="[{ required: true, message: '请输入 Case 执行次数' }]">
          <a-input-number v-model="draft.total_iterations" :min="1" />
        </a-form-item>
        <template v-if="draft.profile === 'staircase'">
          <a-form-item class="mango-simple-form-item" label="每阶增加并发" field="step_users" required :rules="[{ required: true, message: '请输入每阶增加并发' }]">
            <a-input-number v-model="draft.step_users" :min="1" />
          </a-form-item>
          <a-form-item class="mango-simple-form-item" label="阶梯间隔" field="step_interval_seconds" required :rules="[{ required: true, message: '请输入阶梯间隔' }]">
            <a-input-number v-model="draft.step_interval_seconds" :min="1"><template #suffix>秒/阶</template></a-input-number>
          </a-form-item>
          <a-form-item class="mango-simple-form-item" label="峰值保持"><a-input-number v-model="draft.hold_seconds" :min="0"><template #suffix>秒</template></a-input-number></a-form-item>
        </template>
        <template v-if="draft.profile === 'linear_ramp' || draft.profile === 'spike'">
          <a-form-item class="mango-simple-form-item" label="起始并发" field="start_users" required :rules="[{ required: true, message: '请输入起始并发' }]">
            <a-input-number v-model="draft.start_users" :min="draft.profile === 'spike' ? 1 : 0" />
          </a-form-item>
          <a-form-item class="mango-simple-form-item" v-if="draft.profile === 'spike'" label="基线时间" field="baseline_seconds" required :rules="[{ required: true, message: '请输入基线时间' }]">
            <a-input-number v-model="draft.baseline_seconds" :min="1"><template #suffix>秒</template></a-input-number>
          </a-form-item>
          <a-form-item class="mango-simple-form-item" label="爬坡时间" field="ramp_seconds" required :rules="[{ required: true, message: '请输入爬坡时间' }]">
            <a-input-number v-model="draft.ramp_seconds" :min="1"><template #suffix>秒</template></a-input-number>
          </a-form-item>
          <a-form-item class="mango-simple-form-item" label="峰值保持"><a-input-number v-model="draft.hold_seconds" :min="draft.profile === 'spike' ? 1 : 0"><template #suffix>秒</template></a-input-number></a-form-item>
          <a-form-item class="mango-simple-form-item" v-if="draft.profile === 'spike'" label="恢复时间" field="recovery_seconds" required :rules="[{ required: true, message: '请输入恢复时间' }]">
            <a-input-number v-model="draft.recovery_seconds" :min="1"><template #suffix>秒</template></a-input-number>
          </a-form-item>
        </template>
        <template v-if="isRateProfile">
          <a-form-item class="mango-simple-form-item"
            field="target_rate"
            label="目标速率"
            required
            :rules="[{ required: true, message: '请输入目标速率' }]"
            ><a-input-number v-model="draft.target_rate" :min="0"
          /></a-form-item>
          <a-form-item class="mango-simple-form-item" label="速率单位"
            ><a-select
              v-model="draft.rate_time_unit"
              :options="rateTimeUnitOptions"
          /></a-form-item>
          <a-form-item class="mango-simple-form-item" label="预分配 VU"
            ><a-input-number v-model="draft.preallocated_vus" :min="1"
          /></a-form-item>
          <a-form-item class="mango-simple-form-item" label="最大 VU"
            ><a-input-number v-model="draft.max_vus" :min="1"
          /></a-form-item>
        </template>
        <a-form-item label="迭代间等待" class="mango-perf-load-form__wide mango-simple-form-item">
          <a-input-group>
            <a-input-number v-model="draft.user_wait_min_ms" :min="0" :max="3600000" :precision="0" placeholder="最小 ms" />
            <span class="mango-perf-input-separator">至</span>
            <a-input-number v-model="draft.user_wait_max_ms" :min="0" :max="3600000" :precision="0" placeholder="最大 ms" />
          </a-input-group>
        </a-form-item>
        <a-alert type="info" class="mango-perf-profile-hint mango-perf-load-form__wide">预计运行 {{ editedDuration }} 秒；执行器 {{ executorCount }} 个。定量任务按完整 Case 迭代计数，不等于 HTTP 请求数。</a-alert>
      </a-form>
    </template>
  </a-modal>

</template>

<script setup lang="ts">
  import { computed, nextTick, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import type { FormInstance } from '@arco-design/web-vue'
  import { loadProfileOptions } from '../../config'
  import { loadProfileHints, rateTimeUnitOptions } from '../config'
  import { commitLoadDraft, createLoadDraft, isLoadProfile, isRateLoadProfile, loadDuration, loadTypeForProfile } from '../load-configuration'
  import type { LoadConfigurationChange, LoadType } from '../types'

  const props = withDefaults(defineProps<{ contextKey?: string; contextVersion?: number; isContextCurrent?: (version: number) => boolean; executorCount?: number }>(), {
    contextKey: '', contextVersion: 0, executorCount: 1,
  })
  const emit = defineEmits<{ (event: 'confirm', value: LoadConfigurationChange): void }>()
  const visible = ref(false)
  const confirming = ref(false)
  const formRef = ref<FormInstance | null>(null)
  const draft = reactive(createLoadDraft(undefined, 'concurrency'))
  const executorCount = computed(() => props.executorCount)
  const isRateProfile = computed(() => isRateLoadProfile(draft.profile))
  const showFixedDuration = computed(() => !['staircase', 'linear_ramp', 'spike'].includes(draft.profile))
  const editedDuration = computed(() => loadDuration(draft))
  const loadProfileHint = computed(() => loadProfileHints[draft.profile])
  let generation = 0
  let openedContextVersion = 0
  const isCurrentContext = () => !props.isContextCurrent || props.isContextCurrent(openedContextVersion)

  async function open(value: unknown, loadType: LoadType = 'concurrency'): Promise<boolean> {
    openedContextVersion = props.contextVersion
    if (!isCurrentContext()) return false
    const current = ++generation
    try {
      Object.assign(draft, createLoadDraft(value, loadType))
    } catch {
      visible.value = false
      Message.error('负载配置格式不正确，请重新加载场景')
      return false
    }
    visible.value = true
    await nextTick()
    if (current !== generation || !visible.value || !isCurrentContext()) return false
    formRef.value?.clearValidate()
    return true
  }

  function close(): void {
    generation++
    visible.value = false
  }

  function onVisibleChange(value: boolean): void {
    if (!value) close()
  }

  function selectLoadProfile(value: unknown): void {
    if (!isLoadProfile(value) || confirming.value) return
    const defaults = createLoadDraft(undefined, loadTypeForProfile(value))
    Object.assign(draft, defaults, {
      name: draft.name, profile: value,
      user_wait_min_ms: draft.user_wait_min_ms, user_wait_max_ms: draft.user_wait_max_ms,
    })
    formRef.value?.clearValidate()
  }

  async function confirm(): Promise<boolean> {
    if (!visible.value || confirming.value || !formRef.value || !isCurrentContext()) return false
    const current = generation
    confirming.value = true
    try {
      const errors = await formRef.value.validate()
      if (current !== generation || !visible.value || !isCurrentContext() || errors) return false
      let change: LoadConfigurationChange
      try {
        change = commitLoadDraft(draft, props.executorCount)
      } catch (error) {
        Message.warning(error instanceof Error ? error.message : '负载配置无效')
        return false
      }
      emit('confirm', change)
      close()
      return true
    } catch {
      if (current === generation && visible.value && isCurrentContext()) Message.error('校验失败，请重试')
      return false
    } finally {
      confirming.value = false
    }
  }

  watch(() => [props.contextKey, props.contextVersion, props.executorCount], close, { flush: 'sync' })
  onDeactivated(close)
  onBeforeUnmount(close)
  defineExpose({ open, close })
</script>

<style scoped lang="less">
  .mango-perf-load-form {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: 16px;
    align-items: start;
    max-height: 65vh;
    overflow-y: auto;
    padding: var(--m-page-gap);
  }
  .mango-perf-load-form__wide {
    grid-column: 1 / -1;
  }
  .mango-perf-profile-hint {
    margin-bottom: var(--m-page-gap);
  }
  .mango-perf-input-separator {
    display: inline-flex;
    align-items: center;
    padding: 0 6px;
    border-block: 1px solid var(--m-border);
    color: var(--m-muted);
    font-size: 12px;
  }
</style>
