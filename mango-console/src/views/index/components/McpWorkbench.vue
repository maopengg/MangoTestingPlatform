<template>
  <div class="mango-mcp-workbench">
    <div class="mango-mcp-head">
      <div>
        <div class="mango-mcp-title-row">
          <span class="mango-mcp-pulse"></span>
          <strong>MCP 智能接入</strong>
        </div>
        <p>让 AI 直接创建、执行和分析 Mango 测试资产</p>
      </div>
      <a-tag :color="apiKey ? 'green' : 'orange'" size="small">
        {{ apiKey ? 'APIKey 已就绪' : '待配置 APIKey' }}
      </a-tag>
    </div>

    <div class="mango-mcp-scroll-area mango-custom-scrollbar">
      <div class="mango-mcp-endpoint-box">
        <div class="mango-mcp-endpoint-main">
          <span>MCP 地址</span>
          <a-typography-paragraph class="mango-mcp-endpoint-text" :ellipsis="{ rows: 1 }">
            {{ mcpUrl }}
          </a-typography-paragraph>
        </div>
        <a-tooltip content="复制 MCP 地址">
          <a-button size="mini" type="text" @click="copyText(mcpUrl, 'MCP 地址')">
            <template #icon><icon-copy /></template>
          </a-button>
        </a-tooltip>
      </div>

      <div class="mango-mcp-status-grid">
        <div class="mango-mcp-status-item">
          <span>当前环境</span>
          <strong>{{ modeText }}</strong>
        </div>
        <div class="mango-mcp-status-item">
          <span>调用身份</span>
          <strong>{{ userStore.nickName || userStore.userName || '-' }}</strong>
        </div>
        <div class="mango-mcp-status-item">
          <span>认证方式</span>
          <strong>Bearer APIKey</strong>
        </div>
      </div>

      <div class="mango-mcp-api-key-box">
        <div class="mango-mcp-api-key-main">
          <span>MCP APIKey</span>
          <a-typography-paragraph class="mango-mcp-api-key-text" :ellipsis="{ rows: 1 }">
            {{ maskedApiKey }}
          </a-typography-paragraph>
        </div>
        <a-space size="mini">
          <a-tooltip content="复制 Authorization 请求头">
            <a-button size="mini" type="text" :disabled="!apiKey" @click="copyAuthHeader">
              <template #icon><icon-copy /></template>
            </a-button>
          </a-tooltip>
          <a-tooltip content="重置当前用户 APIKey">
            <a-button size="mini" type="text" :loading="resetting" @click="resetApiKey">
              <template #icon><icon-refresh /></template>
            </a-button>
          </a-tooltip>
        </a-space>
      </div>

      <div class="mango-mcp-capability-grid">
        <div v-for="item in capabilities" :key="item.key" class="mango-mcp-capability-item">
          <component :is="item.icon" class="mango-mcp-capability-icon" />
          <div>
            <strong>{{ item.title }}</strong>
            <span>{{ item.desc }}</span>
          </div>
        </div>
      </div>

      <div class="mango-mcp-prompt-panel">
        <div class="mango-mcp-prompt-head">
          <span>推荐指令</span>
          <a-button size="mini" type="text" @click="nextPrompt">
            <template #icon><icon-swap /></template>
          </a-button>
        </div>
        <button class="mango-mcp-prompt-text" type="button" @click="copyText(activePrompt, '推荐指令')">
          {{ activePrompt }}
        </button>
      </div>
    </div>

    <div class="mango-mcp-action-row">
      <a-button size="small" type="primary" long :disabled="!apiKey" @click="copyInstallPrompt">
        <template #icon><icon-code /></template>
        复制一键安装说明
      </a-button>
      <a-button size="small" long @click="openConfig">
        <template #icon><icon-book /></template>
        查看配置
      </a-button>
    </div>

    <a-modal
      v-model:visible="configVisible"
      title="MCP 客户端配置"
      :footer="false"
      width="720px"
      modal-class="mango-mcp-config-modal"
    >
      <div class="mango-mcp-config-section">
        <div class="mango-mcp-config-title">
          <span>一键安装说明</span>
          <a-button
            size="mini"
            type="text"
            :disabled="!apiKey"
            @click="copyText(installPrompt, '一键安装说明')"
          >
            <template #icon><icon-copy /></template>
            复制
          </a-button>
        </div>
        <a-textarea :model-value="installPrompt" readonly :auto-size="{ minRows: 6, maxRows: 8 }" />
      </div>
      <div class="mango-mcp-config-section">
        <div class="mango-mcp-config-title">
          <span>Codex 配置</span>
          <a-button size="mini" type="text" @click="copyText(codexConfig, 'Codex 配置')">
            <template #icon><icon-copy /></template>
            复制
          </a-button>
        </div>
        <a-textarea :model-value="codexConfig" readonly :auto-size="{ minRows: 6, maxRows: 8 }" />
      </div>
      <div class="mango-mcp-config-section">
        <div class="mango-mcp-config-title">
          <span>Authorization</span>
          <a-button size="mini" type="text" :disabled="!apiKey" @click="copyAuthHeader">
            <template #icon><icon-copy /></template>
            复制
          </a-button>
        </div>
        <a-input :model-value="authHeader" readonly />
      </div>
      <div class="mango-mcp-config-note">
        一键安装说明适合直接发送给支持 MCP 的 AI 工具；手动配置时使用下方 MCP 地址和
        Authorization。APIKey 代表当前用户身份，创建、执行和上传类操作都会使用该用户权限。
        <a-link :href="docsUrl" target="_blank">查看使用文档</a-link>
      </div>
    </a-modal>
  </div>
</template>

<script lang="ts" setup>
  import { computed, onMounted, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import {
    IconBook,
    IconBug,
    IconCode,
    IconCopy,
    IconFile,
    IconRefresh,
    IconRobot,
    IconSafe,
    IconStorage,
    IconSwap,
  } from '@arco-design/web-vue/es/icon'
  import useUserStore from '@/store/modules/user'
  import { getUserInfo, putUserApiKey } from '@/api/user/user'
  import { baseURL } from '@/api/axios.config'

  const userStore = useUserStore()
  const apiKey = ref('')
  const configVisible = ref(false)
  const resetting = ref(false)

  const capabilities = [
    { key: 'api', title: 'API 自动化', desc: '接口、用例、执行、失败分析', icon: IconRobot },
    { key: 'factory', title: '数据工厂', desc: '实体、模板、前置数据绑定', icon: IconStorage },
    { key: 'report', title: '测试报告', desc: '失败筛选、聚类和诊断', icon: IconBug },
    { key: 'project', title: '项目上下文', desc: '环境、模块、负责人查询', icon: IconSafe },
    { key: 'file', title: '文件上传', desc: '上传并生成 get_file 引用', icon: IconFile },
  ]

  const mcpServerName =
    String(import.meta.env.VITE_APP_MCP_SERVER_NAME || '').trim() || 'mango-test-platform'
  const prompts = [
    `使用 ${mcpServerName} MCP 查询当前平台开放了哪些能力。`,
    `使用 ${mcpServerName} MCP 创建一个 API case，执行后分析失败原因。`,
    `使用 ${mcpServerName} MCP 分析 test_suite_id=662993174721 的失败 API 用例。`,
    `使用 ${mcpServerName} MCP 为指定表创建数据工厂实体和状态模板。`,
  ]
  const promptIndex = ref(Math.floor(Math.random() * prompts.length))

  const docsUrl =
    'http://43.142.161.61:8002/pages/MCP%E6%9C%8D%E5%8A%A1/%E4%BD%BF%E7%94%A8%E6%8C%87%E5%8D%97.html'
  const backendBaseUrl = computed(() => {
    if (!baseURL || baseURL.startsWith('/')) {
      return window.location.origin.replace(/\/+$/, '')
    }
    return baseURL.replace(/\/+$/, '')
  })
  const mcpUrl = computed(() => `${backendBaseUrl.value}/mcp`)
  const modeText = computed(() => import.meta.env.MODE || '-')
  const activePrompt = computed(() => prompts[promptIndex.value])
  const maskedApiKey = computed(() => {
    if (!apiKey.value) return '当前用户暂无 APIKey'
    if (apiKey.value.length <= 18) return apiKey.value
    return `${apiKey.value.slice(0, 12)}...${apiKey.value.slice(-8)}`
  })
  const authHeader = computed(() =>
    apiKey.value ? `Bearer ${apiKey.value}` : 'Bearer <MCP APIKey>'
  )
  const installPrompt = computed(
    () => `请根据下面的配置帮我安装 Mango MCP 服务，并在安装后查询这个 MCP 服务开放了哪些能力。

MCP 服务名称：${mcpServerName}
URL：${mcpUrl.value}
Headers：
Authorization: ${authHeader.value}

说明：
1. 这是 Mango 测试平台的 MCP 服务。
2. 请使用 streamable HTTP 方式连接。
3. 安装完成后优先调用服务发现能力，确认 API 自动化、数据工厂、测试报告、项目上下文、文件上传等能力是否可用。
4. 后续创建、执行、上传等操作都使用这个 Authorization 对应的 Mango 用户权限。`
  )
  const codexConfig = computed(
    () => `[mcp_servers.${mcpServerName}]
url = "${mcpUrl.value}"
env_http_headers = { Authorization = "MANGO_TEST_PLATFORM_AUTH_HEADER" }

MANGO_TEST_PLATFORM_AUTH_HEADER=${authHeader.value}`
  )

  function nextPrompt() {
    promptIndex.value = (promptIndex.value + 1) % prompts.length
  }

  function fallbackCopy(text: string) {
    const input = document.createElement('textarea')
    input.value = text
    input.style.position = 'fixed'
    input.style.opacity = '0'
    document.body.appendChild(input)
    input.select()
    document.execCommand('copy')
    document.body.removeChild(input)
  }

  async function copyText(text: string, label: string) {
    if (!text) return
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text)
      } else {
        fallbackCopy(text)
      }
      Message.success(`${label}已复制`)
    } catch (error) {
      fallbackCopy(text)
      Message.success(`${label}已复制`)
    }
  }

  function copyAuthHeader() {
    if (!apiKey.value) {
      Message.warning('当前用户暂无 APIKey')
      return
    }
    copyText(`Authorization: ${authHeader.value}`, 'Authorization 请求头')
  }

  function copyInstallPrompt() {
    if (!apiKey.value) {
      Message.warning('当前用户暂无 APIKey，请先在用户管理中生成或重置 APIKey')
      return
    }
    copyText(installPrompt.value, '一键安装说明')
  }

  function openConfig() {
    configVisible.value = true
  }

  function openDocs() {
    window.open(docsUrl, '_blank')
  }

  function loadCurrentUserApiKey() {
    if (!userStore.userId) return
    getUserInfo({ id: userStore.userId, page: 1, pageSize: 1 })
      .then((res) => {
        const list = Array.isArray(res.data) ? res.data : []
        const current = list.find((item: any) => item.id === userStore.userId) || list[0]
        apiKey.value = current?.api_key || ''
      })
      .catch(console.log)
  }

  function resetApiKey() {
    if (!userStore.userId) return
    Modal.confirm({
      title: '重置 MCP APIKey',
      content: '重置后旧 APIKey 会立即失效，已配置的 MCP 客户端需要更新。',
      cancelText: '取消',
      okText: '重置',
      onBeforeOk: () => {
        resetting.value = true
        return putUserApiKey({ id: userStore.userId })
          .then((res) => {
            Message.success(`${res.msg}，请复制新的 APIKey 更新 MCP 客户端配置`)
            apiKey.value = res.data?.api_key || ''
            loadCurrentUserApiKey()
          })
          .catch(console.log)
          .finally(() => {
            resetting.value = false
          })
      },
    })
  }

  onMounted(() => {
    loadCurrentUserApiKey()
  })
</script>

<style lang="less" scoped>
  .mango-mcp-workbench {
    display: flex;
    height: 100%;
    min-height: 0;
    flex-direction: column;
    gap: 8px;
    overflow: hidden;
    padding-top: 6px;
    padding-bottom: 5px;
    color: var(--m-text);
  }

  .mango-mcp-scroll-area {
    display: flex;
    min-height: 0;
    flex: 1 1 auto;
    flex-direction: column;
    gap: 8px;
    overflow-y: auto;
    padding-right: 2px;
  }

  .mango-mcp-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 8px;

    p {
      margin: 4px 0 0;
      font-size: 12px;
      line-height: 18px;
      color: var(--m-muted);
    }
  }

  .mango-mcp-title-row {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
  }

  .mango-mcp-pulse {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--m-success);
    box-shadow: 0 0 0 4px color-mix(in srgb, var(--m-success) 18%, transparent);
  }

  .mango-mcp-endpoint-box,
  .mango-mcp-api-key-box {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 8px 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface-soft);
  }

  .mango-mcp-endpoint-main,
  .mango-mcp-api-key-main {
    min-width: 0;
    flex: 1;

    span {
      display: block;
      margin-bottom: 2px;
      font-size: 11px;
      color: var(--m-muted);
    }
  }

  .mango-mcp-endpoint-text,
  .mango-mcp-api-key-text {
    margin: 0;
    font-size: 12px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }

  .mango-mcp-status-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
  }

  .mango-mcp-status-item {
    min-width: 0;
    padding: 8px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);

    span,
    strong {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      font-size: 11px;
      color: var(--m-muted);
    }

    strong {
      margin-top: 3px;
      font-size: 12px;
      font-weight: 600;
    }
  }

  .mango-mcp-capability-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .mango-mcp-capability-item {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    padding: 7px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);

    div {
      min-width: 0;
    }

    strong,
    span {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    strong {
      font-size: 12px;
      font-weight: 600;
    }

    span {
      margin-top: 2px;
      font-size: 10px;
      color: var(--m-muted);
    }
  }

  .mango-mcp-capability-icon {
    flex: 0 0 auto;
    font-size: 16px;
    color: var(--m-primary);
  }

  .mango-mcp-prompt-panel {
    flex: 0 0 auto;
    min-height: 88px;
    padding: 8px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
  }

  .mango-mcp-prompt-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
    font-size: 12px;
    font-weight: 600;
  }

  .mango-mcp-prompt-text {
    width: 100%;
    min-height: 44px;
    padding: 7px 8px;
    overflow: auto;
    border: none;
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
    color: var(--m-text-2);
    cursor: pointer;
    font-size: 12px;
    line-height: 17px;
    text-align: left;
  }

  .mango-mcp-action-row {
    display: grid;
    flex: 0 0 auto;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin-top: 0;
    padding: 4px 0 1px;
  }

  .mango-mcp-config-section + .mango-mcp-config-section {
    margin-top: 16px;
  }

  .mango-mcp-config-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
    font-weight: 600;
  }

  .mango-mcp-config-note {
    margin-top: 12px;
    padding: 10px;
    border-radius: var(--m-radius-lg);
    background: var(--m-primary-soft);
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 20px;
  }

  @media (max-width: 1440px), (max-height: 820px) {
    .mango-mcp-workbench,
    .mango-mcp-scroll-area {
      gap: 6px;
    }

    .mango-mcp-workbench {
      padding-top: 4px;
      padding-bottom: 3px;
    }

    .mango-mcp-head p {
      margin-top: 2px;
      line-height: 16px;
    }

    .mango-mcp-endpoint-box,
    .mango-mcp-api-key-box {
      padding: 7px 8px;
    }

    .mango-mcp-status-grid,
    .mango-mcp-capability-grid,
    .mango-mcp-action-row {
      gap: 6px;
    }

    .mango-mcp-status-item {
      padding: 6px;
    }

    .mango-mcp-capability-item {
      gap: 6px;
      padding: 6px;
    }

    .mango-mcp-prompt-panel {
      min-height: 76px;
      padding: 7px;
    }

    .mango-mcp-prompt-text {
      min-height: 38px;
      padding: 6px 7px;
      line-height: 16px;
    }
  }

  @media (max-width: 1280px), (max-height: 760px) {
    .mango-mcp-head {
      align-items: center;
    }

    .mango-mcp-head p,
    .mango-mcp-capability-item span {
      display: none;
    }

    .mango-mcp-status-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .mango-mcp-status-item:last-child {
      grid-column: 1 / -1;
    }

    .mango-mcp-capability-grid {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .mango-mcp-capability-item {
      justify-content: center;
      text-align: center;
    }

    .mango-mcp-capability-item strong {
      font-size: 11px;
    }

    .mango-mcp-capability-icon {
      font-size: 15px;
    }

    .mango-mcp-action-row {
      grid-template-columns: 1fr;
      padding-top: 2px;
    }
  }
</style>
