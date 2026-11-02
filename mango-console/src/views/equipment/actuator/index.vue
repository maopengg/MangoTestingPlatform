<template>
  <TableBody ref="tableBody" plain class="mango-detail-workbench-page">
    <template #header>
      <TableHeader title="执行器管理" />
    </template>

    <template #default>
      <div class="mango-equipment-page">
        <div
          v-if="tableLoading && dataList.length === 0"
          class="mango-equipment-initial-loading"
        >
          <mango-panel-spin />
        </div>
        <mango-panel-spin v-else :loading="tableLoading" class="mango-equipment-spin">
          <div class="mango-equipment-grid">
            <div v-for="record in dataList" :key="record.id" class="mango-equipment-grid-item">
              <a-card class="executor-card" :bordered="false" hoverable>
                <template #title>
                  <div class="card-header">
                    <a-avatar :size="24" class="avatar">
                      <icon-user />
                    </a-avatar>
                    <div class="header-info">
                      <span class="owner-name">{{ record.name }} ({{ record.username }})</span>
                    </div>
                    <div class="online-status" title="在线"></div>
                  </div>
                </template>

                <div class="card-content">
                  <!-- IP地址 -->
                  <div class="info-item">
                    <icon-desktop class="info-icon" />
                    <span class="info-label">IP地址：</span>
                    <span class="info-value">{{ record.ip }}</span>
                  </div>

                  <!-- 类型 -->
                  <div class="info-item">
                    <icon-tag class="info-icon" />
                    <span class="info-label">类型：</span>
                    <span class="info-value type-badge" :class="getTypeClass(record.type)">{{
                      getTypeLabel(record.type)
                    }}</span>
                  </div>

                  <div class="info-item">
                    <icon-desktop class="info-icon" />
                    <span class="info-label">WEB直播：</span>
                    <span class="info-value live-badge" :class="{ 'is-supported': record.web_live_stream_supported }">
                      {{ record.web_live_stream_supported ? '支持' : '不支持' }}
                    </span>
                  </div>

                  <!-- OPEN状态 -->
                  <div class="status-item">
                    <icon-link class="status-icon" />
                    <span class="status-label">OPEN状态：</span>
                    <a-switch
                      :model-value="record.is_open === true"
                      :beforeChange="(newValue) => onModifyStatus(newValue, record.username)"
                      size="small"
                    />
                  </div>

                  <!-- DEBUG状态 -->
                  <div class="status-item">
                    <icon-bug class="status-icon" />
                    <span class="status-label">DEBUG状态：</span>
                    <a-switch
                      :model-value="record.debug === true"
                      :beforeChange="(newValue) => onModifyDebug(newValue, record.username)"
                      size="small"
                    />
                  </div>
                </div>

                <template #actions>
                  <a-button
                    size="medium"
                    type="primary"
                    :loading="configRequestLoading[record.username]"
                    @click="handleEditConfig(record)" data-testid="qa-views-equipment-actuator-button-编辑配置"
                  >
                    编辑配置
                  </a-button>
                  <a-button
                    disabled
                    size="medium"
                    status="danger"
                    type="text"
                    @click="onDelete(record)" data-testid="qa-views-equipment-actuator-button-下线"
                  >
                    下线
                  </a-button>
                </template>
              </a-card>
            </div>

            <div v-if="!tableLoading && dataList.length === 0" class="mango-equipment-empty">
              <div class="mango-empty-state">暂无在线执行器</div>
            </div>
          </div>
        </mango-panel-spin>
      </div>
    </template>
  </TableBody>

  <BaseSidePanel
    v-model:visible="configDrawer.visible"
    title="编辑执行器配置"
    width="860px"
    @cancel="handleConfigDrawerCancel"
  >
    <div class="mango-actuator-config-drawer">
      <section class="mango-section-card">
        <div class="mango-section-title">
          <div>
            <h2>{{ configDrawer.record?.name }} ({{ configDrawer.record?.username }})</h2>
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
              <a-input v-model="configForm.server.host" placeholder="请输入服务地址" data-testid="qa-views-equipment-actuator-input-请输入服务地址" />
            </div>
          </div>
          <div class="mango-config-form-row">
            <span class="mango-config-form-label">WS链接</span>
            <div class="mango-config-form-control">
              <a-input v-model="configForm.server.ws" placeholder="请输入 WS 链接" data-testid="qa-views-equipment-actuator-input-请输入-ws-链接" />
            </div>
          </div>
          <div class="mango-config-form-row">
            <span class="mango-config-form-label">代理地址</span>
            <div class="mango-config-form-control">
              <a-input v-model="configForm.server.proxy_url" placeholder="为空则不使用代理" data-testid="qa-views-equipment-actuator-input-为空则不使用代理" />
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
              <a-select v-model="configForm.ui.web_type" placeholder="请选择浏览器类型" data-testid="qa-views-equipment-actuator-select-请选择浏览器类型">
                <a-option :value="0" data-testid="qa-views-equipment-actuator-option-谷歌浏览器">谷歌浏览器</a-option>
                <a-option :value="1" data-testid="qa-views-equipment-actuator-option-微软edge浏览器">微软Edge浏览器</a-option>
                <a-option :value="2" data-testid="qa-views-equipment-actuator-option-火狐浏览器">火狐浏览器</a-option>
                <a-option :value="3" data-testid="qa-views-equipment-actuator-option-safari浏览器">Safari浏览器</a-option>
              </a-select>
            </div>
          </div>
          <div class="mango-config-form-row">
            <span class="mango-config-form-label">浏览器路径</span>
            <div class="mango-config-form-control">
              <a-input v-model="configForm.ui.web_path" placeholder="为空则自动查找" data-testid="qa-views-equipment-actuator-input-为空则自动查找" />
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
              <a-select v-model="configForm.ui.web_h5" placeholder="不选择则关闭" allow-clear data-testid="qa-views-equipment-actuator-select-不选择则关闭">
                <a-option value="" data-testid="qa-views-equipment-actuator-option-不开启">不开启</a-option>
                <a-option value="iPhone 12" data-testid="qa-views-equipment-actuator-option-iphone-12">iPhone 12</a-option>
                <a-option value="Pixel 5" data-testid="qa-views-equipment-actuator-option-pixel-5">Pixel 5</a-option>
                <a-option value="iPad Pro 11" data-testid="qa-views-equipment-actuator-option-ipad-pro-11">iPad Pro 11</a-option>
              </a-select>
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
              <p class="mango-config-form-desc">开放给其他用户使用，也用于测试报告执行 case 时接单。</p>
              <a-switch v-model="configForm.runtime.is_open" size="small" />
            </div>
          </div>
          <div class="mango-config-form-row">
            <span class="mango-config-form-label">DEBUG状态</span>
            <div class="mango-config-form-control">
              <p class="mango-config-form-desc">开启后执行器会输出 debug 级别日志，便于排查执行问题。</p>
              <a-switch v-model="configForm.runtime.debug" size="small" />
            </div>
          </div>
          <div class="mango-config-form-row">
            <span class="mango-config-form-label">WEB直播</span>
            <div class="mango-config-form-control">
              <p class="mango-config-form-desc">由执行器启动环境自动检测，仅展示，不能手动修改。</p>
              <a-tag :color="configForm.runtime.web_live_stream_supported ? 'green' : 'red'">
                {{ configForm.runtime.web_live_stream_supported ? '支持' : '不支持' }}
              </a-tag>
            </div>
          </div>
        </div>
      </section>
    </div>

    <template #footer-buttons>
      <a-button @click="handleConfigDrawerCancel" data-testid="qa-views-equipment-actuator-button-取消">取消</a-button>
      <a-button  type="primary" :loading="configSaveLoading" @click="handleSaveConfig" data-testid="qa-views-equipment-actuator-button-保存配置">保存配置</a-button>
    </template>
  </BaseSidePanel>
</template>

<script lang="ts" setup>
  import { useTable } from '@/hooks/table'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, nextTick, onUnmounted, reactive, ref } from 'vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import {
    getSystemSocketUserList,
    getSystemSocketPutOpenStatus,
    getSystemSocketPutDebug,
    postSystemSocketActuatorConfigRequest,
    getSystemSocketActuatorConfigResult,
    putSystemSocketActuatorConfig,
    getSystemSocketActuatorConfigSaveResult,
  } from '@/api/system/socket_api'
  import { IconUser, IconDesktop, IconLink, IconBug, IconTag } from '@arco-design/web-vue/es/icon'

  const { dataList, tableLoading, handleSuccess } = useTable()
  const configRequestLoading = reactive<Record<string, boolean>>({})
  const configSaveLoading = ref(false)
  const pollTimers: number[] = []
  const configDrawer = reactive({
    visible: false,
    record: null as any,
  })
  const configForm = reactive<any>({
    server: {},
    ui: {},
    pytest: {},
    runtime: {},
  })

  // 获取类型标签文本
  const getTypeLabel = (type: string) => {
    const typeMap: Record<string, string> = {
      pytest: 'Pytest',
      pytest_web: 'Pytest Web',
      web_ui: 'Web UI',
      android_ui: 'Android UI',
    }
    return typeMap[type] || 'Pytest Web' // 默认值
  }

  // 获取类型标签样式类
  const getTypeClass = (type: string) => {
    const typeClassMap: Record<string, string> = {
      pytest: 'type-pytest',
      pytest_web: 'type-pytest-web',
      web_ui: 'type-web-ui',
      android_ui: 'type-android-ui',
    }
    return typeClassMap[type] || 'type-pytest-web' // 默认值
  }

  function doRefresh() {
    getSystemSocketUserList({
      page: 1,
      pageSize: 100, // 获取所有数据
    })
      .then((res) => {
        handleSuccess(res)
      })
      .catch(console.log)
  }

  function onReceive() {
    Message.warning('开发中.....')
  }

  const sleep = (ms: number) => new Promise((resolve) => {
    const timer = window.setTimeout(resolve, ms)
    pollTimers.push(timer)
  })

  const normalizeConfig = (config: any = {}) => ({
    server: {
      host: config.server?.host || '',
      ws: config.server?.ws || '',
      proxy_url: config.server?.proxy_url || '',
      username: config.server?.username || '',
    },
    ui: {
      web_type: Number(config.ui?.web_type ?? 0),
      web_path: config.ui?.web_path || '',
      web_parallel: Number(config.ui?.web_parallel ?? 5),
      ui_queue_size: Number(config.ui?.ui_queue_size ?? 10),
      web_h5: config.ui?.web_h5 || '',
      web_max: Boolean(config.ui?.web_max),
      web_recording: Boolean(config.ui?.web_recording),
      web_headers: Boolean(config.ui?.web_headers),
      web_step_screenshot: Boolean(config.ui?.web_step_screenshot),
      web_static_cache_enabled: Boolean(config.ui?.web_static_cache_enabled),
      web_static_cache_path: config.ui?.web_static_cache_path || '',
    },
    pytest: {
      pytest_parallel: Number(config.pytest?.pytest_parallel ?? 5),
      pytest_queue_size: Number(config.pytest?.pytest_queue_size ?? 10),
    },
    runtime: {
      is_open: Boolean(config.runtime?.is_open),
      debug: Boolean(config.runtime?.debug),
      web_live_stream_supported: Boolean(config.runtime?.web_live_stream_supported),
    },
  })

  const assignConfigForm = (config: any) => {
    const next = normalizeConfig(config)
    configForm.server = next.server
    configForm.ui = next.ui
    configForm.pytest = next.pytest
    configForm.runtime = next.runtime
  }

  const waitForConfigResult = async (requestId: string) => {
    for (let index = 0; index < 20; index += 1) {
      await sleep(1000)
      const res = await getSystemSocketActuatorConfigResult(requestId)
      if (res.data?.status === 'success') return res.data
      if (res.data?.status === 'failed') throw new Error(res.data?.message || '执行器配置读取失败')
      if (res.data?.status === 'expired') throw new Error('执行器配置读取超时')
    }
    throw new Error('执行器配置读取超时')
  }

  const waitForSaveResult = async (requestId: string) => {
    for (let index = 0; index < 20; index += 1) {
      await sleep(1000)
      const res = await getSystemSocketActuatorConfigSaveResult(requestId)
      if (res.data?.status === 'success') return res.data
      if (res.data?.status === 'failed') throw new Error(res.data?.message || '执行器配置保存失败')
      if (res.data?.status === 'expired') throw new Error('执行器配置保存超时')
    }
    throw new Error('执行器配置保存超时')
  }

  const handleEditConfig = async (record: any) => {
    configRequestLoading[record.username] = true
    try {
      const res = await postSystemSocketActuatorConfigRequest(record.username)
      const result = await waitForConfigResult(res.data?.request_id)
      assignConfigForm(result.config)
      configDrawer.record = record
      configDrawer.visible = true
    } catch (error: any) {
      Message.error(error.message || '执行器配置读取失败')
    } finally {
      configRequestLoading[record.username] = false
    }
  }

  const handleSaveConfig = async () => {
    if (!configDrawer.record?.username) return
    configSaveLoading.value = true
    try {
      const res = await putSystemSocketActuatorConfig(configDrawer.record.username, normalizeConfig(configForm))
      await waitForSaveResult(res.data?.request_id)
      Message.success('执行器配置保存成功')
      configDrawer.visible = false
      doRefresh()
    } catch (error: any) {
      Message.error(error.message || '执行器配置保存失败')
    } finally {
      configSaveLoading.value = false
    }
  }

  const handleConfigDrawerCancel = () => {
    configDrawer.visible = false
  }

  // 添加删除方法
  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要下线此执行器？',
      cancelText: '取消',
      okText: '下线',
      onBeforeOk: () => {
        // 这里应该调用实际的下线接口，但由于按钮是禁用的，这里只是示例
        Message.info('此功能暂未开放')
      },
    })
  }

  const onModifyStatus = async (newValue: any, id: string) => {
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value: any = false
          await getSystemSocketPutOpenStatus(id, newValue ? 1 : 0)
            .then((res) => {
              Message.success(res.msg)
              value = res.code === 200
            })
            .catch(reject)
          resolve(value)
        } catch (error) {
          reject(error)
        }
      }, 300)
    })
  }

  const onModifyDebug = async (newValue: any, id: string) => {
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value: any = false
          await getSystemSocketPutDebug(id, newValue ? 1 : 0)
            .then((res) => {
              Message.success(res.msg)
              value = res.code === 200
            })
            .catch(reject)
          resolve(value)
        } catch (error) {
          reject(error)
        }
      }, 300)
    })
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
    })
  })

  onUnmounted(() => {
    pollTimers.forEach((timer) => window.clearTimeout(timer))
  })
</script>

<style lang="less" scoped>
  .mango-equipment-page {
    display: flex;
    width: 100%;
    height: 100%;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
  }

  .mango-equipment-initial-loading {
    display: flex;
    flex: 1;
    min-height: 0;
    align-items: center;
    justify-content: center;
  }

  .mango-equipment-spin {
    display: block;
    width: 100%;
    margin-top: 8px;
  }

  .mango-equipment-spin :deep(> .mango-panel-spin__content) {
    display: block;
    width: 100%;
  }

  .mango-equipment-grid {
    display: grid;
    width: 100%;
    min-width: 0;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: var(--m-page-gap);
  }

  .mango-equipment-grid-item {
    min-width: 0;
  }

  .mango-equipment-empty {
    grid-column: 1 / -1;
  }

  .mango-actuator-config-drawer {
    display: flex;
    flex-direction: column;
    min-width: 0;
    gap: 8px;
  }

  .executor-card {
    display: flex;
    width: 100%;
    min-width: 0;
    height: 100%;
    flex-direction: column;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
    box-shadow: var(--m-shadow);
    overflow: hidden;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;

    &:hover {
      border-color: var(--m-primary-border);
      box-shadow: var(--m-shadow);
    }

    :deep(.arco-card-header) {
      padding: 12px 16px;
      border-bottom: 1px solid var(--m-border);
    }

    :deep(.arco-card-body) {
      flex: 1;
      padding: 12px 16px;
    }

    :deep(.arco-card-footer) {
      border-top: 1px solid var(--m-border);
      padding: 4px 16px;
    }

    .card-header {
      display: flex;
      align-items: center;

      .avatar {
        background-color: var(--m-primary-soft);
        margin-right: 12px;
      }

      .header-info {
        display: flex;
        flex-direction: column;
        flex: 1;

        .owner-name {
          font-size: 16px;
          font-weight: 500;
          color: var(--m-text);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
      }

      .online-status {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: color-mix(in srgb, var(--m-success) 24%, var(--m-surface));
        border: 2px solid color-mix(in srgb, var(--m-success) 34%, transparent);
        margin-left: 12px;
        flex-shrink: 0;
      }
    }

    .card-content {
      .info-item,
      .status-item {
        display: flex;
        align-items: center;
        margin-bottom: 10px;

        &:last-child {
          margin-bottom: 4px;
        }

        .info-icon,
        .status-icon {
          font-size: 16px;
          margin-right: 8px;
          color: var(--m-muted);
        }

        .info-label,
        .status-label {
          font-size: 14px;
          color: var(--m-text-2);
          margin-right: 8px;
          flex-shrink: 0;
        }

        .info-value {
          font-size: 14px;
          color: var(--m-text);
          flex: 1;
          text-align: right;

          &.type-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;

            &.type-pytest {
              background-color: color-mix(in srgb, var(--m-chart-5) 16%, var(--m-surface));
              color: var(--m-chart-5);
            }

            &.type-pytest-web {
              background-color: var(--m-primary-soft);
              color: var(--m-primary);
            }

            &.type-web-ui {
              background-color: color-mix(in srgb, var(--m-success) 16%, var(--m-surface));
              color: var(--m-success);
            }

            &.type-android-ui {
              background-color: color-mix(in srgb, var(--m-danger) 14%, var(--m-surface));
              color: var(--m-danger);
            }
          }

          &.live-badge {
            display: inline-block;
            flex: initial;
            padding: 2px 8px;
            border-radius: 4px;
            background-color: color-mix(in srgb, var(--m-danger) 12%, var(--m-surface));
            color: var(--m-danger);
            font-size: 12px;
            font-weight: 500;

            &.is-supported {
              background-color: color-mix(in srgb, var(--m-success) 14%, var(--m-surface));
              color: var(--m-success);
            }
          }
        }

        :deep(.arco-switch) {
          flex-shrink: 0;
          margin-left: auto;
        }
      }

      .status-item {
        .status-icon {
          color: var(--m-primary);
        }
      }
    }

    :deep(.arco-card-actions) {
      display: flex;
      justify-content: flex-end;
      padding: 2px 0 0;
    }
  }

  // 响应式调整
  @media (max-width: 1200px) {
    .mango-equipment-grid {
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    }
  }

  @media (max-width: 640px) {
    .mango-equipment-grid {
      grid-template-columns: 1fr;
    }

    .executor-card {
      :deep(.arco-card-body) {
        padding: 10px 12px;
      }

      :deep(.arco-card-footer) {
        padding: 3px 12px;
      }

      .card-header {
        .header-info {
          .owner-name {
            font-size: 14px;
          }
        }

        .online-status {
          width: 8px;
          height: 8px;
          margin-left: 10px;
        }
      }

      .card-content {
        .info-item,
        .status-item {
          margin-bottom: 8px;

          &:last-child {
            margin-bottom: 3px;
          }

          .info-label,
          .status-label {
            font-size: 13px;
          }

          .info-value {
            font-size: 13px;

            &.type-badge {
              font-size: 11px;
              padding: 1px 6px;
            }
          }
        }
      }

      :deep(.arco-card-actions) {
        padding: 1px 0 0;
      }
    }
  }
</style>
