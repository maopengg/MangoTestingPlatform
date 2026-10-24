<template>
  <a-drawer
    :visible="visible"
    width="50%"
    title="版本比对"
    :footer="false"
    unmount-on-close
    @update:visible="(value) => emit('update:visible', value)"
    @cancel="emit('update:visible', false)"
  >
    <div class="api-version-compare">
      <div class="api-version-compare__toolbar">
        <a-form :model="compareFormModel" layout="inline" class="api-version-compare__selector">
          <a-form-item label="左侧版本">
            <a-select
              v-model="leftKey"
              allow-search
              placeholder="请选择左侧版本"
              :loading="loading"
              @change="(value) => loadSidePayload('left', String(value))" data-testid="qa-components-business-apiversioncomparedrawer-select-请选择左侧版本"
            >
              <a-option v-for="item in compareTargets" :key="item.key" :value="item.key">
                {{ item.label }}
              </a-option>
            </a-select>
          </a-form-item>
          <a-form-item label="右侧版本">
            <a-select
              v-model="rightKey"
              allow-search
              placeholder="请选择右侧版本"
              :loading="loading"
              @change="(value) => loadSidePayload('right', String(value))" data-testid="qa-components-business-apiversioncomparedrawer-select-请选择右侧版本"
            >
              <a-option v-for="item in compareTargets" :key="item.key" :value="item.key">
                {{ item.label }}
              </a-option>
            </a-select>
          </a-form-item>
        </a-form>
      </div>

      <mango-panel-spin :loading="loading" class="api-version-compare__spin">
        <a-empty v-if="!leftTarget || !rightTarget" description="请选择左右版本进行比对" />
        <template v-else>
          <div class="api-version-compare__summary">
            <div class="api-version-compare__pair">
              <span>左侧</span>
              <strong>{{ leftTarget.label }}</strong>
              <a-divider direction="vertical" />
              <span>右侧</span>
              <strong>{{ rightTarget.label }}</strong>
            </div>
            <div class="api-version-compare__metrics">
              <a-statistic title="差异" :value="diffs.length" />
              <a-statistic title="新增" :value="addedCount" />
              <a-statistic title="删除" :value="removedCount" />
              <a-statistic title="修改" :value="changedCount" />
            </div>
          </div>

          <a-alert
            v-if="!diffs.length"
            type="success"
            show-icon
            content="两个版本的可编辑配置一致"
          />

          <div v-else class="api-version-compare__diff-list">
            <div
              v-for="item in diffs"
              :key="item.path"
              class="api-version-compare__diff-item"
              :class="`is-${item.type}`"
            >
              <div class="api-version-compare__diff-head">
                <a-tag size="small" :color="diffColor(item.type)">
                  {{ diffTypeText(item.type) }}
                </a-tag>
                <strong>{{ item.path }}</strong>
              </div>
              <div class="api-version-compare__diff-values">
                <div>
                  <header>{{ leftTarget.label }}</header>
                  <pre>{{ stringifyValue(item.left) }}</pre>
                </div>
                <div>
                  <header>{{ rightTarget.label }}</header>
                  <pre>{{ stringifyValue(item.right) }}</pre>
                </div>
              </div>
            </div>
          </div>

          <a-collapse class="api-version-compare__raw" :default-active-key="[]">
            <a-collapse-item key="raw" header="查看原始快照">
              <div class="api-version-compare__snapshot-grid">
                <section>
                  <header>{{ leftTarget.label }}</header>
                  <pre>{{ stringifyValue(leftComparePayload) }}</pre>
                </section>
                <section>
                  <header>{{ rightTarget.label }}</header>
                  <pre>{{ stringifyValue(rightPayload) }}</pre>
                </section>
              </div>
            </a-collapse-item>
          </a-collapse>
        </template>
      </mango-panel-spin>
    </div>
  </a-drawer>
</template>

<script lang="ts" setup>
  import { computed, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import type { ApiVersionCompareTarget } from '@/types/api-test/version-compare'
  import { isLosslessJsonNumber, stringifyLosslessJson } from '@/utils/lossless-json'

  type DiffType = 'added' | 'removed' | 'changed'

  interface DiffItem {
    path: string
    type: DiffType
    left: unknown
    right: unknown
  }

  const props = defineProps<{
    visible: boolean
    leftTitle: string
    leftPayload: unknown
    targets: ApiVersionCompareTarget[]
    loadTargetPayload: (target: ApiVersionCompareTarget) => Promise<unknown>
  }>()

  const emit = defineEmits<{
    (event: 'update:visible', value: boolean): void
  }>()

  const leftKey = ref('')
  const rightKey = ref('')
  const leftComparePayload = ref<unknown>(null)
  const rightPayload = ref<unknown>(null)
  const loading = ref(false)
  const compareFormModel = ref({})

  const currentTarget = computed<ApiVersionCompareTarget>(() => ({
    key: 'current',
    label: props.leftTitle,
    payload: props.leftPayload,
  }))
  const compareTargets = computed<ApiVersionCompareTarget[]>(() => {
    const targets = props.targets.filter((item) => item.key !== currentTarget.value.key)
    return [currentTarget.value, ...targets]
  })
  const leftTarget = computed(
    () => compareTargets.value.find((item) => item.key === leftKey.value) || null
  )
  const rightTarget = computed(
    () => compareTargets.value.find((item) => item.key === rightKey.value) || null
  )
  const diffs = computed(() => compareValues(leftComparePayload.value, rightPayload.value))
  const addedCount = computed(() => diffs.value.filter((item) => item.type === 'added').length)
  const removedCount = computed(() => diffs.value.filter((item) => item.type === 'removed').length)
  const changedCount = computed(() => diffs.value.filter((item) => item.type === 'changed').length)

  function isPlainObject(value: unknown): value is Record<string, unknown> {
    return (
      !isLosslessJsonNumber(value) &&
      Object.prototype.toString.call(value) === '[object Object]'
    )
  }

  function isEqual(left: unknown, right: unknown) {
    return stringifyLosslessJson(left) === stringifyLosslessJson(right)
  }

  function formatPath(parent: string, key: string | number) {
    if (typeof key === 'number') return `${parent}[${key}]`
    return parent ? `${parent}.${key}` : key
  }

  function compareValues(left: unknown, right: unknown, path = ''): DiffItem[] {
    if (isEqual(left, right)) return []
    if (Array.isArray(left) && Array.isArray(right)) {
      const length = Math.max(left.length, right.length)
      return Array.from({ length }).flatMap((_, index) => {
        const nextPath = formatPath(path, index)
        if (index >= left.length)
          return [
            { path: nextPath, type: 'added' as DiffType, left: undefined, right: right[index] },
          ]
        if (index >= right.length)
          return [
            { path: nextPath, type: 'removed' as DiffType, left: left[index], right: undefined },
          ]
        return compareValues(left[index], right[index], nextPath)
      })
    }
    if (isPlainObject(left) && isPlainObject(right)) {
      const keys = Array.from(new Set([...Object.keys(left), ...Object.keys(right)])).sort()
      return keys.flatMap((key) => {
        const nextPath = formatPath(path, key)
        if (!(key in left))
          return [{ path: nextPath, type: 'added' as DiffType, left: undefined, right: right[key] }]
        if (!(key in right))
          return [
            { path: nextPath, type: 'removed' as DiffType, left: left[key], right: undefined },
          ]
        return compareValues(left[key], right[key], nextPath)
      })
    }
    return [{ path: path || '根配置', type: 'changed', left, right }]
  }

  function stringifyValue(value: unknown) {
    if (value === undefined) return '未配置'
    if (typeof value === 'string') return value || '空字符串'
    try {
      return stringifyLosslessJson(value, 2)
    } catch {
      return String(value)
    }
  }

  function diffTypeText(type: DiffType) {
    const map: Record<DiffType, string> = {
      added: '右侧新增',
      removed: '右侧缺少',
      changed: '内容不同',
    }
    return map[type]
  }

  function diffColor(type: DiffType) {
    const map: Record<DiffType, string> = {
      added: 'green',
      removed: 'red',
      changed: 'orange',
    }
    return map[type]
  }

  async function resolveTargetPayload(target: ApiVersionCompareTarget) {
    if (target.key === currentTarget.value.key) return props.leftPayload
    if (target.payload !== undefined) return target.payload
    return props.loadTargetPayload(target)
  }

  async function loadSidePayload(side: 'left' | 'right', key: string) {
    if (side === 'left') {
      leftKey.value = key
    } else {
      rightKey.value = key
    }
    const target = compareTargets.value.find((item) => item.key === key) || null
    if (!target) {
      if (side === 'left') {
        leftComparePayload.value = null
      } else {
        rightPayload.value = null
      }
      return
    }
    loading.value = true
    try {
      const payload = await resolveTargetPayload(target)
      if (side === 'left') {
        leftComparePayload.value = payload
      } else {
        rightPayload.value = payload
      }
    } catch (error) {
      console.error(error)
      Message.error('加载比对版本失败')
      if (side === 'left') {
        leftComparePayload.value = null
      } else {
        rightPayload.value = null
      }
    } finally {
      loading.value = false
    }
  }

  watch(
    () => props.visible,
    (visible) => {
      if (!visible) return
      leftKey.value = currentTarget.value.key
      rightKey.value = props.targets[0]?.key || currentTarget.value.key
      void loadSidePayload('left', leftKey.value)
      void loadSidePayload('right', rightKey.value)
    }
  )
</script>

<style scoped>
  .api-version-compare {
    display: flex;
    height: 100%;
    min-height: 0;
    flex-direction: column;
    gap: 12px;
  }

  .api-version-compare__toolbar {
    display: block;
    flex: 0 0 auto;
    padding: 12px 16px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface);
  }

  .api-version-compare__side-title {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 2px;
  }

  .api-version-compare__side-title span {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .api-version-compare__side-title strong {
    color: var(--m-text);
    font-size: 14px;
    line-height: 20px;
  }

  .api-version-compare__selector {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 12px;
  }

  .api-version-compare__selector :deep(.arco-select) {
    width: 100%;
  }

  .api-version-compare__spin {
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  .api-version-compare__spin :deep(> .mango-panel-spin__content) {
    display: flex;
    height: 100%;
    min-height: 0;
    flex-direction: column;
    gap: 12px;
    padding: 0 16px 16px;
    overflow-y: auto;
  }

  .api-version-compare__summary {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 12px;
    align-items: stretch;
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .api-version-compare__pair {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 8px;
    color: var(--m-muted);
  }

  .api-version-compare__pair strong {
    min-width: 0;
    overflow: hidden;
    color: var(--m-text);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .api-version-compare__metrics {
    display: grid;
    min-width: 360px;
    grid-template-columns: repeat(4, minmax(64px, 1fr));
    gap: 8px;
  }

  .api-version-compare__metrics :deep(.arco-statistic) {
    padding: 6px 10px;
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }

  .api-version-compare__metrics :deep(.arco-statistic-title) {
    margin-bottom: 2px;
    color: var(--m-muted);
    font-size: 12px;
  }

  .api-version-compare__metrics :deep(.arco-statistic-value) {
    color: var(--m-text);
    font-size: 18px;
    font-weight: 700;
  }

  .api-version-compare__diff-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .api-version-compare__diff-item {
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    overflow: hidden;
  }

  .api-version-compare__diff-item.is-added {
    border-color: color-mix(in srgb, #00b42a 35%, var(--m-border));
  }

  .api-version-compare__diff-item.is-removed {
    border-color: color-mix(in srgb, #f53f3f 35%, var(--m-border));
  }

  .api-version-compare__diff-item.is-changed {
    border-color: color-mix(in srgb, #ff7d00 35%, var(--m-border));
  }

  .api-version-compare__diff-head {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    border-bottom: 1px solid var(--m-border);
  }

  .api-version-compare__diff-head strong {
    min-width: 0;
    overflow: hidden;
    color: var(--m-text);
    font-size: 13px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .api-version-compare__diff-values {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }

  .api-version-compare__snapshot-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }

  .api-version-compare__diff-values > div,
  .api-version-compare__snapshot-grid section {
    min-width: 0;
    border-right: 1px solid var(--m-border);
  }

  .api-version-compare__diff-values > div:last-child,
  .api-version-compare__snapshot-grid section:last-child {
    border-right: 0;
  }

  .api-version-compare__diff-values header,
  .api-version-compare__snapshot-grid header {
    padding: 8px 10px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface);
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
  }

  .api-version-compare__diff-values pre,
  .api-version-compare__snapshot-grid pre {
    min-height: 0;
    margin: 0;
    padding: 10px;
    overflow: auto;
    border-right: 1px solid var(--m-border);
    background: var(--m-surface-soft);
    color: var(--m-text-2);
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 12px;
    line-height: 18px;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .api-version-compare__snapshot-grid {
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    overflow: hidden;
  }

  .api-version-compare__snapshot-grid section {
    display: flex;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
  }

  .api-version-compare__raw {
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  @media (max-width: 900px) {
    .api-version-compare__toolbar,
    .api-version-compare__diff-values,
    .api-version-compare__snapshot-grid,
    .api-version-compare__summary,
    .api-version-compare__selector {
      grid-template-columns: 1fr;
    }

    .api-version-compare__metrics {
      min-width: 0;
    }
  }
</style>
