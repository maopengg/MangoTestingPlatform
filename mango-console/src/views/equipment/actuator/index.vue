<template>
  <TableBody plain class="mango-detail-workbench-page">
    <template #header><TableHeader title="执行器管理" /></template>
    <div class="mango-equipment-page">
      
      <mango-panel-spin :loading="listLoading" class="mango-equipment-spin">
        <div class="mango-equipment-grid">
          <section
            v-for="record in rows"
            :key="record.username"
            class="mango-actuator-card mango-section-card"
          >
            <header class="mango-actuator-card-header">
              <a-avatar :size="24"><IconUser /></a-avatar>
              <span class="mango-actuator-owner" :title="`${record.name} (${record.username})`"
                >{{ record.name }} ({{ record.username }})</span
              >
              <span class="mango-actuator-online" title="在线" aria-label="在线"></span>
            </header>
            <dl class="mango-actuator-info">
              <div
                ><dt>IP地址</dt><dd :title="record.ip">{{ record.ip }}</dd></div
              >
              <div
                ><dt>类型</dt
                ><dd
                  ><span class="mango-actuator-type" :class="getTypeClass(record.type)">{{
                    getTypeLabel(record.type)
                  }}</span></dd
                ></div
              >
              <div
                ><dt>WEB直播</dt
                ><dd
                  ><a-tag
                    :color="record.web_live_stream_supported ? 'green' : 'red'"
                    size="small"
                    >{{ record.web_live_stream_supported ? '支持' : '不支持' }}</a-tag
                  ></dd
                ></div
              >
              <div
                ><dt>OPEN状态</dt
                ><dd
                  ><a-switch
                    size="small"
                    :model-value="record.is_open === true"
                    :loading="statusPending.has(record.username)"
                    :disabled="isBusy(record.username)"
                    :before-change="(value) => onModifyStatus(value, record.username)" /></dd
              ></div>
              <div
                ><dt>DEBUG状态</dt
                ><dd
                  ><a-switch
                    size="small"
                    :model-value="record.debug === true"
                    :loading="debugPending.has(record.username)"
                    :disabled="isBusy(record.username)"
                    :before-change="(value) => onModifyDebug(value, record.username)" /></dd
              ></div>
            </dl>
            <footer class="mango-actuator-actions">
              <a-button
                size="small"
                type="primary"
                :loading="configPending.has(record.username)"
                :disabled="isBusy(record.username)"
                @click="handleEditConfig(record)"
                data-testid="qa-views-equipment-actuator-button-编辑配置"
                >编辑配置</a-button
              >
              <a-button
                size="small"
                status="danger"
                type="text"
                disabled
                data-testid="qa-views-equipment-actuator-button-下线"
                >下线</a-button
              >
            </footer>
          </section>
          
        </div>
      </mango-panel-spin>
    </div>
    <ActuatorConfigDrawer ref="configRef" @saved="doRefresh" @busy-change="onConfigBusy" />
  </TableBody>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { onMounted, ref, reactive } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { IconUser } from '@arco-design/web-vue/es/icon'
  import {
    getSystemSocketUserList,
    getSystemSocketPutOpenStatus,
    getSystemSocketPutDebug,
  } from '@/api/system/socket_api'
  import ActuatorConfigDrawer from './components/ActuatorConfigDrawer.vue'
  import { getTypeLabel, getTypeClass } from './config'
  import { useActuatorScope } from './composables/useActuatorScope'
  import type { ActuatorRecord, ConfigHandle } from './types'
  const rows = ref<ActuatorRecord[]>([]),
    listLoading = ref(false),
    loadError = ref(false),
    configRef = ref<ConfigHandle | null>(null)
  const statusPending = reactive(new Set<string>()),
    debugPending = reactive(new Set<string>()),
    configPending = reactive(new Set<string>())
  const configCounts = new Map<string, number>()
  let request = 0
  const scope = useActuatorScope(reset, () => {
    void doRefresh()
  })
  function reset() {
    ++request
    rows.value = []
    listLoading.value = false
    loadError.value = false
    configRef.value?.close()
  }
  async function doRefresh() {
    if (!scope.isActive()) return
    const current = ++request,
      version = scope.snapshot()
    listLoading.value = true
    loadError.value = false
    try {
      const response = await getSystemSocketUserList({ page: 1, pageSize: 100 })
      if (current === request && scope.current(version)) rows.value = response.data || []
    } catch (loadFailure0) {
      if (current === request && scope.current(version)) (reportLoadError(loadFailure0, "加载失败，请重试", false), loadError.value = true)
    } finally {
      if (current === request) listLoading.value = false
    }
  }
  function isBusy(username: string) {
    return statusPending.has(username) || debugPending.has(username) || configPending.has(username)
  }
  function onConfigBusy(username: string, _kind: 'read' | 'save', pending: boolean) {
    const count = Math.max(0, (configCounts.get(username) || 0) + (pending ? 1 : -1))
    if (count) {
      configCounts.set(username, count)
      configPending.add(username)
    } else {
      configCounts.delete(username)
      configPending.delete(username)
    }
  }
  function handleEditConfig(record: ActuatorRecord) {
    if (scope.isActive() && !isBusy(record.username)) configRef.value?.open(record)
  }
  async function changeRuntime(
    value: boolean,
    username: string,
    kind: 'is_open' | 'debug'
  ): Promise<boolean> {
    if (!scope.isActive() || isBusy(username)) return false
    const version = scope.snapshot(),
      pending = kind === 'is_open' ? statusPending : debugPending
    pending.add(username)
    try {
      const response = await (kind === 'is_open'
        ? getSystemSocketPutOpenStatus
        : getSystemSocketPutDebug)(username, value ? 1 : 0)
      if (!scope.current(version) || response.code !== 200) return false
      const record = rows.value.find((item) => item.username === username)
      if (record) record[kind] = value
      Message.success(response.msg)
      return true
    } catch {
      return false
    } finally {
      pending.delete(username)
    }
  }
  function onModifyStatus(value: boolean, username: string) {
    return changeRuntime(value, username, 'is_open')
  }
  function onModifyDebug(value: boolean, username: string) {
    return changeRuntime(value, username, 'debug')
  }
  onMounted(() => {
    void doRefresh()
  })
</script>
<style scoped>
  .mango-equipment-page {
    min-width: 0;
    margin-top: var(--m-page-gap);
  }
  .mango-equipment-spin {
    display: block;
    width: 100%;
    min-height: 120px;
  }
  .mango-equipment-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: var(--m-page-gap);
  }
  .mango-actuator-card {
    display: flex;
    min-width: 0;
    flex-direction: column;
    padding: 0;
    overflow: hidden;
  }
  .mango-actuator-card-header {
    display: flex;
    align-items: center;
    gap: var(--m-page-gap);
    padding: 12px 16px;
    border-bottom: 1px solid var(--m-border);
  }
  .mango-actuator-owner {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--m-text);
    font-weight: 600;
  }
  .mango-actuator-online {
    width: 10px;
    height: 10px;
    flex: none;
    border-radius: 50%;
    background: var(--m-success);
  }
  .mango-actuator-info {
    margin: 0;
    padding: 12px 16px;
    display: grid;
    gap: 10px;
  }
  .mango-actuator-info > div {
    display: flex;
    gap: var(--m-page-gap);
    align-items: center;
    min-width: 0;
  }
  .mango-actuator-info dt {
    color: var(--m-text-2);
    flex: none;
  }
  .mango-actuator-info dd {
    margin: 0 0 0 auto;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-actuator-actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--m-page-gap);
    padding: 8px 16px;
    border-top: 1px solid var(--m-border);
  }
  .mango-actuator-empty {
    grid-column: 1/-1;
  }
  .mango-actuator-type {
    display: inline-block;
    padding: 2px 8px;
    border-radius: var(--m-radius-sm);
    font-size: 12px;
  }
  .mango-type-pytest {
    background: color-mix(in srgb, var(--m-chart-5) 16%, var(--m-surface));
    color: var(--m-chart-5);
  }
  .mango-type-pytest-web {
    background: var(--m-primary-soft);
    color: var(--m-primary);
  }
  .mango-type-web-ui {
    background: color-mix(in srgb, var(--m-success) 16%, var(--m-surface));
    color: var(--m-success);
  }
  .mango-type-android-ui {
    background: color-mix(in srgb, var(--m-danger) 14%, var(--m-surface));
    color: var(--m-danger);
  }
</style>
