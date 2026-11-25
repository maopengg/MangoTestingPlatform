<template>
  <div class="mango-datasource-performance">
    <p class="mango-datasource-performance__hint">
      Case 并发是主要执行控制，不再对 SQL、Redis、ES
      操作另行限频。这里只保护同实例物理连接总量，保留清理连接容量；连接不足时等待，不能提前判为通过。
    </p>
    <p v-if="notice" class="mango-datasource-performance__error" role="status">{{ notice }}</p>
    <p
      data-feedback-kind="validation"
      v-if="modelError"
      class="mango-datasource-performance__error"
      role="alert"
      >{{ modelError }}</p
    >

    <section v-for="kind in kinds" :key="kind.key" class="mango-datasource-performance__section">
      <h4>{{ kind.label }}</h4>
      <div v-for="field in budgetFields" :key="field.key" class="mango-system-settings__row">
        <label
          class="mango-system-settings__label-wrap mango-system-settings__label"
          :for="`${kind.key}-${field.key}`"
          >{{ field.label }}</label
        >
        <div class="mango-system-settings__type"
          ><a-tag size="small" :color="managementLevel === 2 ? 'orange' : undefined">{{
            managementLevel === 2 ? '谨慎修改' : '普通配置'
          }}</a-tag></div
        >
        <div class="mango-system-settings__control">
          <a-input-number
            :id="`${kind.key}-${field.key}`"
            v-model="draft[kind.key][field.key]"
            class="mango-system-settings__input mango-system-settings__input--number"
            :min="field.min"
            :max="field.max"
            :precision="0"
            :disabled="loading || Boolean(modelError)"
            size="medium"
            :aria-label="`${kind.label} ${field.label}`"
            @blur="save"
            @press-enter="save"
          />
        </div>
        <div class="mango-system-settings__aside"
          ><span class="mango-system-settings__help">{{ field.hint }}</span></div
        >
      </div>
    </section>
    <section v-if="runtime.rows.length" class="mango-datasource-performance__section">
      <h4>实例运行状态（刷新页面更新）</h4>
      <div
        v-for="item in runtime.rows"
        :key="item.group"
        class="mango-datasource-performance__instance"
      >
        <div>连接 ID：{{ item.connections.join('、') }}</div>
        <p class="mango-datasource-performance__hint">
          物理连接占用 {{ item.counts.connection_active + item.counts.connection_suspect }} /
          {{ item.budget.connections }} ·
          {{ item.connection_waiting ? '正在等待可用连接' : '近期无连接容量等待' }}
        </p>
        <p v-if="item.counts?.connection_suspect" class="mango-datasource-performance__error">
          存在
          {{
            item.counts.connection_suspect
          }}
          个关闭状态未确认的连接；请核查原连接和进程证据，不能按过期直接释放。
        </p>
      </div>
    </section>
    <section class="mango-datasource-performance__section">
      <h4>连接与调度</h4>
      <div v-for="field in sharedFields" :key="field.key" class="mango-system-settings__row">
        <label
          class="mango-system-settings__label-wrap mango-system-settings__label"
          :for="field.key"
          >{{ field.label }}</label
        >
        <div class="mango-system-settings__type"
          ><a-tag size="small" :color="managementLevel === 2 ? 'orange' : undefined">{{
            managementLevel === 2 ? '谨慎修改' : '普通配置'
          }}</a-tag></div
        >
        <div class="mango-system-settings__control">
          <a-input-number
            :id="field.key"
            v-model="draft[field.key]"
            :min="field.min"
            :max="field.max"
            class="mango-system-settings__input mango-system-settings__input--number"
            :precision="0"
            :disabled="loading || Boolean(modelError)"
            size="medium"
            :aria-label="field.label"
            @blur="save"
            @press-enter="save"
          />
        </div>
        <div v-if="field.hint" class="mango-system-settings__aside"
          ><span class="mango-system-settings__help">{{ field.hint }}</span></div
        >
      </div>
    </section>
    <p
      data-feedback-kind="validation"
      v-if="error"
      class="mango-datasource-performance__error"
      role="alert"
      >{{ error }}</p
    >
    <span v-if="loading" role="status">正在保存数据源策略…</span>
  </div>
</template>

<script setup lang="ts">
  import { computed, reactive, ref, toRaw, watch } from 'vue'
  import { reportLoadError } from '@/utils/load-error'
  import {
    createDatasourcePolicy,
    datasourcePolicyPayload,
    parseDatasourceRuntime,
  } from '../datasource-policy'
  import type {
    DatasourceBudget,
    DatasourceSharedBudget,
    DatasourceKind,
    DatasourceField,
    DatasourcePolicy,
  } from '../datasource-policy'

  const props = withDefaults(
    defineProps<{
      modelValue: unknown
      runtimeStatus?: unknown
      notice?: string
      loading: boolean
      managementLevel?: number
    }>(),
    { managementLevel: 2 }
  )
  const emit = defineEmits<{
    (event: 'update:modelValue', value: DatasourcePolicy): void
    (event: 'save'): void
  }>()
  const kinds: { key: DatasourceKind; label: string }[] = [
    { key: 'mysql', label: 'MySQL' },
    { key: 'redis', label: 'Redis' },
    { key: 'elasticsearch', label: 'Elasticsearch' },
  ]
  const budgetFields: DatasourceField<keyof DatasourceBudget>[] = [
    {
      key: 'connections',
      label: '物理连接总数（含空闲）',
      min: 2,
      max: 128,
      hint: '同实例跨进程共享的物理连接上限，不是SQL并发。已有连接可直接执行；容量满时只等待新连接，清理保留一个池的连接容量。',
    },
  ]
  const sharedFields: DatasourceField<keyof DatasourceSharedBudget>[] = [
    {
      key: 'cleanup_consumer_threads',
      label: '清理消费线程数',
      min: 1,
      max: 16,
      hint: '每个scheduler默认2个线程；有正式报告的清理交给scheduler，无报告仍同步清理。必须等待清理和回查完成才汇总结果。',
    },
    {
      key: 'pool_size',
      label: '单进程每池连接数',
      min: 1,
      max: 8,
      hint: '默认4个，连接用满后等待。普通与清理使用独立池，仍受实例物理连接总量保护；不限制业务API并发。',
    },
    {
      key: 'pool_idle_seconds',
      label: '空闲池回收（秒）',
      min: 5,
      max: 600,
      hint: '默认60秒；只回收闲置连接，不中断使用中的连接。',
    },
    {
      key: 'max_local_pools',
      label: '闲置连接池缓存上限',
      min: 1,
      max: 128,
      hint: '默认32个。超过时回收闲置池，不因活跃池较多拒绝Case或阻止另一个数据源连接。',
    },
    {
      key: 'cleanup_completion_seconds',
      label: '每阶段清理处理预算（秒）',
      min: 60,
      max: 3600,
      hint: '默认每阶段300秒；SQL阶段（含归属预检）与ES阶段分别累计，不包含连接或scheduler等待。原累计总时间仍保留。超限保留清理责任，不能跳过校验或判为成功。',
    },
  ]
  const draft = reactive(createDatasourcePolicy({}))
  const error = ref(''),
    modelError = ref('')
  let lastEmission: DatasourcePolicy | null = null
  const runtime = computed(() => {
    try {
      return { rows: parseDatasourceRuntime(props.runtimeStatus ?? []), error: '' }
    } catch {
      return { rows: [], error: '数据源运行状态格式异常，请重新读取系统配置' }
    }
  })
  watch(
    () => runtime.value.error,
    (message) => {
      if (message) reportLoadError(new Error(message), message)
    },
    { immediate: true }
  )
  watch(
    () => props.modelValue,
    (value) => {
      if (lastEmission !== null && toRaw(value) === lastEmission) return
      try {
        Object.assign(draft, createDatasourcePolicy(value))
        modelError.value = ''
        error.value = ''
      } catch {
        modelError.value = '数据源策略格式异常，请重新读取系统配置'
      }
    },
    { immediate: true }
  )
  function save() {
    if (props.loading || modelError.value) return
    error.value = ''
    try {
      const payload = datasourcePolicyPayload(draft, budgetFields, sharedFields)
      lastEmission = payload
      emit('update:modelValue', payload)
      emit('save')
    } catch (exception) {
      error.value = exception instanceof Error ? exception.message : '请检查数据源策略'
    }
  }
</script>

<style scoped>
  .mango-datasource-performance {
    width: 100%;
    min-width: 0;
  }
  .mango-datasource-performance__section + .mango-datasource-performance__section {
    margin-top: var(--m-space-lg);
    padding-top: var(--m-space-lg);
    border-top: 1px solid var(--m-border);
  }
  .mango-datasource-performance__section h4 {
    margin: 0 0 var(--m-space-md);
    color: var(--m-text-2);
    font-size: var(--m-font-body);
    font-weight: 600;
  }
  .mango-datasource-performance__hint {
    margin: 0 0 var(--m-space-md);
    color: var(--m-muted);
    font-size: var(--m-font-caption);
    line-height: 1.6;
  }
  .mango-datasource-performance__instance {
    padding-block: var(--m-card-padding);
    border-bottom: 1px solid var(--m-border);
  }
  .mango-datasource-performance__error {
    color: var(--m-danger);
  }
</style>
