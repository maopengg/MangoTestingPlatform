<template>
  <BaseSidePanel
    :visible="visible"
    @update:visible="onVisibleChange"
    :title="title"
    :width="configDrawerWidth"
    @cancel="close"
  >
    <mango-panel-spin
      :loading="loading"
      class="mango-actuator-read-panel"
      tip="执行器配置读取中..."
    >
      
      <div v-if="ready" class="mango-actuator-config-drawer" :inert="saving ? '' : undefined">
        <section class="mango-section-card">
          <div class="mango-section-title">
            <div>
              <h2>{{ selectedActuator?.name }} ({{ selectedActuator?.username }})</h2>
              <p>读取并修改当前在线执行器的本地配置。</p>
            </div>
          </div>
        </section>

        <section class="mango-section-card">
          <div class="mango-section-title">
            <div>
              <h2>服务连接</h2>
              <p>服务端地址、WebSocket 地址和代理配置。</p>
            </div>
          </div>
          <div class="mango-config-form-grid">
            <div class="mango-config-form-row">
              <span class="mango-config-form-label">服务地址</span>
              <div class="mango-config-form-control">
                <a-input
                  v-model="configForm.server.host"
                  placeholder="请输入服务地址"
                  data-testid="qa-views-equipment-actuator-input-请输入服务地址"
                />
              </div>
            </div>
            <div class="mango-config-form-row">
              <span class="mango-config-form-label">WS链接</span>
              <div class="mango-config-form-control">
                <a-input
                  v-model="configForm.server.ws"
                  placeholder="请输入 WS 链接"
                  data-testid="qa-views-equipment-actuator-input-请输入-ws-链接"
                />
              </div>
            </div>
            <div class="mango-config-form-row">
              <span class="mango-config-form-label">代理地址</span>
              <div class="mango-config-form-control">
                <a-input
                  v-model="configForm.server.proxy_url"
                  placeholder="为空则不使用代理"
                  data-testid="qa-views-equipment-actuator-input-为空则不使用代理"
                />
              </div>
            </div>
            <div class="mango-config-form-row">
              <span class="mango-config-form-label">登录账号</span>
              <div class="mango-config-form-control">
                <a-input v-model="configForm.server.username" disabled />
              </div>
            </div>
          </div>
        </section>

        <section class="mango-section-card">
          <div class="mango-section-title">
            <div>
              <h2>UI自动化</h2>
              <p>浏览器、执行并发、队列和运行采集配置。</p>
            </div>
          </div>
          <div class="mango-config-form-grid">
            <div class="mango-config-form-row">
              <span class="mango-config-form-label">浏览器类型</span>
              <div class="mango-config-form-control">
                <a-select
                  v-model="configForm.ui.web_type"
                  :options="browserOptions"
                  placeholder="请选择浏览器类型"
                />
              </div>
            </div>
            <div class="mango-config-form-row">
              <span class="mango-config-form-label">浏览器路径</span>
              <div class="mango-config-form-control">
                <a-input
                  v-model="configForm.ui.web_path"
                  placeholder="为空则自动查找"
                  data-testid="qa-views-equipment-actuator-input-为空则自动查找"
                />
              </div>
            </div>
            <div class="mango-config-form-row">
              <span class="mango-config-form-label">浏览器并行数</span>
              <div class="mango-config-form-control">
                <a-input-number v-model="configForm.ui.web_parallel" :min="1" :max="50" />
              </div>
            </div>
            <div class="mango-config-form-row">
              <span class="mango-config-form-label">UI队列容量</span>
              <div class="mango-config-form-control">
                <a-input-number v-model="configForm.ui.ui_queue_size" :min="1" :max="200" />
              </div>
            </div>
            <div class="mango-config-form-row">
              <span class="mango-config-form-label">浏览器H5模式</span>
              <div class="mango-config-form-control">
                <a-select
                  v-model="configForm.ui.web_h5"
                  :options="h5Options"
                  placeholder="不选择则关闭"
                  allow-clear
                />
              </div>
            </div>
            <div class="mango-config-form-row">
              <span class="mango-config-form-label">静态资源缓存</span>
              <div class="mango-config-form-control">
                <a-switch v-model="configForm.ui.web_static_cache_enabled" size="small" />
              </div>
            </div>
            <div class="mango-config-form-row">
              <span class="mango-config-form-label">静态资源缓存目录</span>
              <div class="mango-config-form-control">
                <a-input v-model="configForm.ui.web_static_cache_path" disabled />
              </div>
            </div>
            <div class="mango-config-form-row">
              <span class="mango-config-form-label">最大化</span>
              <div class="mango-config-form-control">
                <a-switch v-model="configForm.ui.web_max" size="small" />
              </div>
            </div>
            <div class="mango-config-form-row">
              <span class="mango-config-form-label">视频录制</span>
              <div class="mango-config-form-control">
                <a-switch v-model="configForm.ui.web_recording" size="small" />
              </div>
            </div>
            <div class="mango-config-form-row">
              <span class="mango-config-form-label">无头模式</span>
              <div class="mango-config-form-control">
                <a-switch v-model="configForm.ui.web_headers" size="small" />
              </div>
            </div>
            <div class="mango-config-form-row">
              <span class="mango-config-form-label">步骤截图</span>
              <div class="mango-config-form-control">
                <a-switch v-model="configForm.ui.web_step_screenshot" size="small" />
              </div>
            </div>
          </div>
        </section>

        <section class="mango-section-card">
          <div class="mango-section-title">
            <div>
              <h2>Pytest</h2>
              <p>Pytest 执行并发和本地队列容量。</p>
            </div>
          </div>
          <div class="mango-config-form-grid">
            <div class="mango-config-form-row">
              <span class="mango-config-form-label">Pytest并行数</span>
              <div class="mango-config-form-control">
                <a-input-number v-model="configForm.pytest.pytest_parallel" :min="1" :max="50" />
              </div>
            </div>
            <div class="mango-config-form-row">
              <span class="mango-config-form-label">Pytest队列容量</span>
              <div class="mango-config-form-control">
                <a-input-number v-model="configForm.pytest.pytest_queue_size" :min="1" :max="200" />
              </div>
            </div>
          </div>
        </section>

        <section class="mango-section-card">
          <div class="mango-section-title">
            <div>
              <h2>运行状态</h2>
              <p>立即影响执行器接单和调试日志输出。</p>
            </div>
          </div>
          <div class="mango-config-form-grid">
            <div class="mango-config-form-row">
              <span class="mango-config-form-label">OPEN状态</span>
              <div class="mango-config-form-control">
                <p class="mango-config-form-desc"
                  >开放给其他用户使用，也用于测试报告执行 case 时接单。</p
                >
                <a-switch v-model="configForm.runtime.is_open" size="small" />
              </div>
            </div>
            <div class="mango-config-form-row">
              <span class="mango-config-form-label">DEBUG状态</span>
              <div class="mango-config-form-control">
                <p class="mango-config-form-desc"
                  >开启后执行器会输出 debug 级别日志，便于排查执行问题。</p
                >
                <a-switch v-model="configForm.runtime.debug" size="small" />
              </div>
            </div>
            <div class="mango-config-form-row">
              <span class="mango-config-form-label">WEB直播</span>
              <div class="mango-config-form-control">
                <p class="mango-config-form-desc"
                  >由执行器启动环境自动检测，仅展示，不能手动修改。</p
                >
                <a-tag :color="configForm.runtime.web_live_stream_supported ? 'green' : 'red'">
                  {{ configForm.runtime.web_live_stream_supported ? '支持' : '不支持' }}
                </a-tag>
              </div>
            </div>
          </div>
        </section>
      </div>
    </mango-panel-spin>
    <template #footer-buttons>
      <a-button @click="close" data-testid="qa-views-equipment-actuator-button-取消">取消</a-button>
      <a-button
        type="primary"
        :loading="saving"
        :disabled="!ready || loading"
        @click="save"
        data-testid="qa-views-equipment-actuator-button-保存配置"
        >保存配置</a-button
      >
    </template>
  </BaseSidePanel>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { ref, reactive, computed } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import {
    postSystemSocketActuatorConfigRequest,
    getSystemSocketActuatorConfigResult,
    putSystemSocketActuatorConfig,
    getSystemSocketActuatorConfigSaveResult,
  } from '@/api/system/socket_api'
  import { normalizeConfig } from '../form'
  import { browserOptions, h5Options, configDrawerWidth } from '../config'
  import { useActuatorScope } from '../composables/useActuatorScope'
  import { useConfigResult } from '../composables/useConfigResult'
  import type { ActuatorRecord, ActuatorDraft } from '../types'
  const emit = defineEmits<{
    (event: 'saved'): void
    (event: 'busy-change', username: string, kind: 'read' | 'save', pending: boolean): void
  }>()
  const selectedActuator = ref<ActuatorRecord | null>(null),
    visible = ref(false),
    loading = ref(false),
    saving = ref(false),
    ready = ref(false),
    readError = ref('')
  const configForm: ActuatorDraft = reactive(normalizeConfig())
  let session = 0,
    readRequest = 0
  const readPoll = useConfigResult(),
    savePoll = useConfigResult()
  const scope = useActuatorScope(() => {
    close()
    savePoll.cancel()
  })
  const title = computed(() =>
    selectedActuator.value
      ? `编辑执行器配置 / ${selectedActuator.value.username}`
      : '编辑执行器配置'
  )
  function close() {
    ++session
    ++readRequest
    readPoll.cancel()
    visible.value = false
    selectedActuator.value = null
    loading.value = false
    ready.value = false
    readError.value = ''
    Object.assign(configForm, normalizeConfig())
  }
  function onVisibleChange(value: boolean) {
    if (!value) close()
  }
  function open(record: ActuatorRecord) {
    if (!scope.isActive() || saving.value) return
    close()
    selectedActuator.value = { ...record }
    visible.value = true
    void load()
  }
  async function load(): Promise<boolean> {
    if (!scope.isActive() || !visible.value || !selectedActuator.value || saving.value) return false
    const request = ++readRequest,
      current = session,
      version = scope.snapshot(),
      username = selectedActuator.value.username
    readPoll.cancel()
    loading.value = true
    ready.value = false
    readError.value = ''
    emit('busy-change', username, 'read', true)
    const valid = () => request === readRequest && current === session && scope.current(version)
    try {
      const response = await postSystemSocketActuatorConfigRequest(username)
      if (!valid()) return false
      const result = await readPoll.wait(
        response.data?.request_id,
        username,
        getSystemSocketActuatorConfigResult,
        valid,
        '读取'
      )
      if (!valid() || !result) return false
      if (!result.config) throw Error('执行器未返回配置，请重试')
      Object.assign(configForm, normalizeConfig(result.config))
      ready.value = true
      return true
    } catch (error: unknown) {
      if (valid()) (reportLoadError(error, "执行器配置读取失败", false), readError.value = error instanceof Error ? error.message : '执行器配置读取失败')
      return false
    } finally {
      if (request === readRequest) loading.value = false
      emit('busy-change', username, 'read', false)
    }
  }
  async function save(): Promise<boolean> {
    if (
      !scope.isActive() ||
      !visible.value ||
      !selectedActuator.value ||
      saving.value ||
      loading.value ||
      !ready.value
    )
      return false
    const current = session,
      version = scope.snapshot(),
      username = selectedActuator.value.username,
      payload = normalizeConfig(configForm)
    saving.value = true
    emit('busy-change', username, 'save', true)
    try {
      const response = await putSystemSocketActuatorConfig(username, payload)
      // Closing the drawer only abandons its UI; observe the accepted operation until it settles.
      const result = await savePoll.wait(
        response.data?.request_id,
        username,
        getSystemSocketActuatorConfigSaveResult,
        () => scope.current(version),
        '保存'
      )
      if (!result || current !== session || !scope.current(version)) return false
      Message.success('执行器配置保存成功')
      emit('saved')
      close()
      return true
    } catch (error: unknown) {
      if (current === session && scope.current(version))
        Message.error(error instanceof Error ? error.message : '执行器配置保存失败')
      return false
    } finally {
      saving.value = false
      emit('busy-change', username, 'save', false)
    }
  }
  defineExpose({ open, close })
</script>
<style scoped>
  .mango-actuator-read-panel {
    display: block;
    min-height: 120px;
  }
  .mango-actuator-config-drawer {
    display: flex;
    flex-direction: column;
    min-width: 0;
    gap: var(--m-page-gap);
  }
</style>
