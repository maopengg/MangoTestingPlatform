<template>
  <div class="mango-datasource-performance">
    <p class="mango-datasource-performance__hint">
      所有实例统一使用对应数据源类型的配置。同地址、同端口的连接共享限额，账号与权限仍隔离。同一实例请统一连接入口，避免多个域名被计为不同实例。清理保留容量不可关闭；等待清理不会提前判为通过。
    </p>
    <p v-if="notice" class="mango-datasource-performance__error" role="status">{{ notice }}</p>
    <section v-for="kind in kinds" :key="kind.key" class="mango-datasource-performance__section">
      <h4>{{ kind.label }}</h4>
      <div v-for="field in budgetFields" :key="field.key" class="mango-system-settings__row">
        <label class="mango-system-settings__label-wrap mango-system-settings__label" :for="`${kind.key}-${field.key}`">{{ field.label }}</label>
        <div class="mango-system-settings__type"><a-tag size="small" :color="managementLevel === 2 ? 'orange' : undefined">{{ managementLevel === 2 ? '谨慎修改' : '普通配置' }}</a-tag></div>
        <div class="mango-system-settings__control">
          <a-input-number :id="`${kind.key}-${field.key}`" v-model="draft[kind.key][field.key]"
            class="mango-system-settings__input mango-system-settings__input--number"
            :min="field.min" :max="field.max" :precision="0" :disabled="loading" size="medium"
            :aria-label="`${kind.label} ${field.label}`" @blur="save" @press-enter="save" />
        </div>
        <div class="mango-system-settings__aside"><span class="mango-system-settings__help">{{ field.hint }}</span></div>
      </div>
    </section>
    <section v-if="runtimeStatus?.length" class="mango-datasource-performance__section">
      <h4>实例运行状态（刷新页面更新）</h4>
      <div v-for="item in runtimeStatus" :key="item.group" class="mango-datasource-performance__instance">
        <div>连接 ID：{{ item.connections.join('、') }}</div>
        <p class="mango-datasource-performance__hint">
          执行占用 {{ item.counts?.operation_active || 0 }} / {{ item.budget.concurrency }} ·
          连接预留 {{ item.counts?.connection_active || 0 }} / {{ item.budget.connections }} ·
          排队 {{ item.queued || 0 }} · 限流命中 {{ item.throttled || 0 }}
        </p>
        <p v-if="item.counts?.operation_suspect || item.counts?.connection_suspect" class="mango-datasource-performance__error">
          存在结果未知的占用，仍计入限额；请核查执行记录与数据源状态，不会到期自动放行。
        </p>
      </div>
    </section>
    <section class="mango-datasource-performance__section">
      <h4>连接与调度</h4>
      <div v-for="field in sharedFields" :key="field.key" class="mango-system-settings__row">
        <label class="mango-system-settings__label-wrap mango-system-settings__label" :for="field.key">{{ field.label }}</label>
        <div class="mango-system-settings__type"><a-tag size="small" :color="managementLevel === 2 ? 'orange' : undefined">{{ managementLevel === 2 ? '谨慎修改' : '普通配置' }}</a-tag></div>
        <div class="mango-system-settings__control">
          <a-input-number :id="field.key" v-model="draft[field.key]" :min="field.min" :max="field.max"
            class="mango-system-settings__input mango-system-settings__input--number"
            :precision="0" :disabled="loading" size="medium" :aria-label="field.label"
            @blur="save" @press-enter="save" />
        </div>
        <div v-if="field.hint" class="mango-system-settings__aside"><span class="mango-system-settings__help">{{ field.hint }}</span></div>
      </div>
    </section>
    <p v-if="error" class="mango-datasource-performance__error" role="alert">{{ error }}</p>
    <span v-if="loading" role="status">正在保存数据源策略…</span>
  </div>
</template>

<script setup lang="ts">
  import { reactive, ref, watch } from 'vue'

  const props = withDefaults(defineProps<{ modelValue: Record<string, any>; runtimeStatus?: any[]; notice?: string; loading: boolean; managementLevel?: number }>(), { managementLevel: 2 })
  const emit = defineEmits<{ (event: 'update:modelValue', value: Record<string, any>): void; (event: 'save'): void }>()
  const kinds = [{ key: 'mysql', label: 'MySQL' }, { key: 'redis', label: 'Redis' }, { key: 'elasticsearch', label: 'Elasticsearch' }]
  const budgetFields = [
    { key: 'cleanup_backlog_limit', label: '自动清理积压水位（明细数）', min: 1, max: 10000, hint: '同实例待自动清理明细达到此数量后，新的工厂造数等待清理排空；不是Case并发上限。调高会增加未清理数据积压。' },
    { key: 'concurrency', label: '数据源操作并发上限', min: 2, max: 64, hint: '同实例同时执行的数据源操作总量，包含清理；额度满时排队。不限制Case业务API并发，调高会增加数据源压力。' },
    { key: 'requests_per_second', label: '数据源操作每秒请求', min: 2, max: 1000, hint: '同实例每秒补充的数据源操作额度，包含清理；不是业务API请求速率。调低会延长排队，调高会增加数据源负载。' },
    { key: 'connections', label: '连接总数（含空闲）', min: 2, max: 128, hint: '同实例跨进程共享的物理连接预算，空闲池连接也计入。不是每个Worker各有此额度，需大于单池连接数以保留清理容量。' },
    { key: 'cleanup_reserved', label: '清理保留并发', min: 1, max: 32, hint: '从操作并发总额中留给清理的名额，不额外增加总并发。不可关闭且须小于总并发，避免造数和查询占满后无法清理。' },
    { key: 'cleanup_rate_percent', label: '清理保留速率（%）', min: 1, max: 90, hint: '总请求速率中留给清理的比例，不是额外额度。调高会减少普通操作可用速率；清理容量不能关闭。' },
    { key: 'metadata_per_second', label: '元数据每秒请求', min: 1, max: 10, hint: '限制表结构、索引发现及连接测试等元数据操作的速率，同时受实例总速率限制；不限制业务API请求。' },
  ]
  const sharedFields = [
    { key: 'cleanup_consumer_threads', label: '清理消费线程数', min: 1, max: 16, hint: '每个scheduler处理正式报告清理任务的线程数，默认2个；无报告执行仍同步清理。保存后下一轮调整，缩容等待当前阶段完成，不扩大数据源总限额。' },
    { key: 'queue_timeout_seconds', label: '排队凭据续期窗口（秒）', min: 1, max: 120, hint: '等待者定期续期其排队登记，停止续期的登记到期后移除。不是SQL超时，也不是Case最长排队时间。' },
    { key: 'max_waiters', label: '实例等待队列上限', min: 1, max: 256, hint: '每个实例最多登记的等待者数量，默认256；未登记的操作继续等待。不是Case总数或业务API并发上限，调高会增加协调开销。' },
    { key: 'permit_lease_seconds', label: '配额租约（秒）', min: 30, max: 3600, hint: '运行中的配额占用需在此窗口内续约；过期后先核查，不会自动释放结果未知的占用。设置过短会增加续约中断导致待核查的风险。' },
    { key: 'pool_size', label: '单进程每池连接数', min: 1, max: 8, hint: '单个进程内每个连接池的连接额度，仍受同实例连接总预算限制；须小于实例连接总数，调高会增加连接占用。' },
    { key: 'transaction_statement_budget', label: '事务 SQL 速率预留批量', min: 2, max: 64, hint: '事务开始前一次最多预留多少条SQL的速率额度，不限制事务SQL总数；后续不足时继续等待额度，不跳过SQL。' },
    { key: 'pool_idle_seconds', label: '空闲池回收（秒）', min: 5, max: 600, hint: '连接池空闲超过此时长后可回收。调低可减少空闲占用，但会增加重建连接的开销；不会强行中断正在使用的连接。' },
    { key: 'max_local_pools', label: '进程连接池数量上限', min: 1, max: 128, hint: '限制每个进程保留的连接池数量，不是物理连接总数；不同配置可能使用不同池，所有池仍受实例连接总预算约束。' },
    { key: 'cleanup_completion_seconds', label: '清理处理预算（不含排队，秒）', min: 60, max: 3600, hint: '累计实际清理处理时间的上限，不含资源排队等待。超限后仍保留清理责任，不能提前判为通过；调低可能使清理无法完成。' },
  ]
  const baseBudget = { cleanup_backlog_limit: 100, concurrency: 6, requests_per_second: 30, connections: 12, cleanup_reserved: 2, cleanup_rate_percent: 25, metadata_per_second: 2 }
  const draft = reactive<Record<string, any>>({})
  const error = ref('')
  watch(() => props.modelValue, value => {
    const uniform = Object.fromEntries(Object.entries(value || {}).filter(([key]) => !['instances', 'scopes'].includes(key)))
    Object.assign(draft, {
      ...uniform,
      mysql: { ...baseBudget, ...value?.mysql },
      redis: { ...baseBudget, concurrency: 12, requests_per_second: 75, connections: 16, ...value?.redis },
      elasticsearch: { ...baseBudget, requests_per_second: 15, ...value?.elasticsearch },
      queue_timeout_seconds: value?.queue_timeout_seconds ?? 30,
      cleanup_consumer_threads: value?.cleanup_consumer_threads ?? 2,
      max_waiters: value?.max_waiters ?? 256, permit_lease_seconds: value?.permit_lease_seconds ?? 300,
      pool_size: value?.pool_size ?? 3, pool_idle_seconds: value?.pool_idle_seconds ?? 60,
      transaction_statement_budget: value?.transaction_statement_budget ?? 8,
      max_local_pools: value?.max_local_pools ?? 32, cleanup_completion_seconds: value?.cleanup_completion_seconds ?? 300,
    })
    for (const kind of kinds) {
      const saved = value?.[kind.key]
      if (saved?.concurrency === 2 && !Object.prototype.hasOwnProperty.call(saved, 'cleanup_reserved')) {
        draft[kind.key].cleanup_reserved = 1
      }
    }
    if (!Object.prototype.hasOwnProperty.call(value || {}, 'pool_size') && kinds.some(kind => value?.[kind.key]?.connections === 3)) {
      draft.pool_size = 2
    }
  }, { immediate: true })
  function save() {
    if (props.loading) return
    error.value = ''
    for (const budget of kinds.map(kind => draft[kind.key])) {
      if (budget.cleanup_reserved >= budget.concurrency || budget.metadata_per_second > budget.requests_per_second) {
        error.value = '清理保留并发必须小于总并发，元数据速率不能超过总速率。'; return
      }
      if (budget.connections <= draft.pool_size) {
        error.value = '连接总数必须大于单池连接数，为清理保留连接容量。'; return
      }
    }
    emit('update:modelValue', JSON.parse(JSON.stringify(draft)))
    emit('save')
  }
</script>

<style scoped>
  .mango-datasource-performance { width: 100%; min-width: 0; }
  .mango-datasource-performance__section + .mango-datasource-performance__section { margin-top: var(--m-space-lg); padding-top: var(--m-space-lg); border-top: 1px solid var(--m-border); }
  .mango-datasource-performance__section h4 { margin: 0 0 var(--m-space-md); color: var(--m-text-2); font-size: var(--m-font-body); font-weight: 600; }
  .mango-datasource-performance__hint { margin: 0 0 var(--m-space-md); color: var(--m-muted); font-size: var(--m-font-caption); line-height: 1.6; }
  .mango-datasource-performance__instance { padding-block: var(--m-card-padding); border-bottom: 1px solid var(--m-border); }
  .mango-datasource-performance__error { color: var(--m-danger); }
</style>
