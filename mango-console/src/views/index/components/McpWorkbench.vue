<template>
  <div class="mcp-workbench">
    <div class="mcp-head">
      <div>
        <div class="mcp-title-row">
          <span class="pulse"></span>
          <strong>MCP 智能接入</strong>
        </div>
        <p>让 AI 直接创建、执行和分析 Mango 测试资产</p>
      </div>
      <a-tag :color="apiKey ? 'green' : 'orange'" size="small">
        {{ apiKey ? 'APIKey 已就绪' : '待配置 APIKey' }}
      </a-tag>
    </div>

    <div class="endpoint-box">
      <div class="endpoint-main">
        <span>MCP 地址</span>
        <a-typography-paragraph class="endpoint-text" :ellipsis="{ rows: 1 }">
          {{ mcpUrl }}
        </a-typography-paragraph>
      </div>
      <a-tooltip content="复制 MCP 地址">
        <a-button size="mini" type="text" @click="copyText(mcpUrl, 'MCP 地址')">
          <template #icon><icon-copy /></template>
        </a-button>
      </a-tooltip>
    </div>

    <div class="status-grid">
      <div class="status-item">
        <span>当前环境</span>
        <strong>{{ modeText }}</strong>
      </div>
      <div class="status-item">
        <span>调用身份</span>
        <strong>{{ userStore.nickName || userStore.userName || '-' }}</strong>
      </div>
      <div class="status-item">
        <span>认证方式</span>
        <strong>Bearer APIKey</strong>
      </div>
    </div>

    <div class="api-key-box">
      <div class="api-key-main">
        <span>MCP APIKey</span>
        <a-typography-paragraph class="api-key-text" :ellipsis="{ rows: 1 }">
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

    <div class="capability-grid">
      <div v-for="item in capabilities" :key="item.key" class="capability-item">
        <component :is="item.icon" class="capability-icon" />
        <div>
          <strong>{{ item.title }}</strong>
          <span>{{ item.desc }}</span>
        </div>
      </div>
    </div>

    <div class="prompt-panel">
      <div class="prompt-head">
        <span>推荐指令</span>
        <a-button size="mini" type="text" @click="nextPrompt">
          <template #icon><icon-swap /></template>
        </a-button>
      </div>
      <button class="prompt-text" type="button" @click="copyText(activePrompt, '推荐指令')">
        {{ activePrompt }}
      </button>
    </div>

    <div class="action-row">
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
      modal-class="mcp-config-modal"
    >
      <div class="config-section">
        <div class="config-title">
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
      <div class="config-section">
        <div class="config-title">
          <span>Codex 配置</span>
          <a-button size="mini" type="text" @click="copyText(codexConfig, 'Codex 配置')">
            <template #icon><icon-copy /></template>
            复制
          </a-button>
        </div>
        <a-textarea :model-value="codexConfig" readonly :auto-size="{ minRows: 6, maxRows: 8 }" />
      </div>
      <div class="config-section">
        <div class="config-title">
          <span>Authorization</span>
          <a-button size="mini" type="text" :disabled="!apiKey" @click="copyAuthHeader">
            <template #icon><icon-copy /></template>
            复制
          </a-button>
        </div>
        <a-input :model-value="authHeader" readonly />
      </div>
      <div class="config-note">
        一键安装说明适合直接发送给支持 MCP 的 AI 工具；手动配置时使用下方 MCP 地址和 Authorization。APIKey
        代表当前用户身份，创建、执行和上传类操作都会使用该用户权限。
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

  const prompts = [
    '使用 mango-test-platform MCP 查询当前平台开放了哪些能力。',
    '使用 mango-test-platform MCP 创建一个 API case，执行后分析失败原因。',
    '使用 mango-test-platform MCP 分析 test_suite_id=662993174721 的失败 API 用例。',
    '使用 mango-test-platform MCP 为指定表创建数据工厂实体和状态模板。',
  ]
  const promptIndex = ref(Math.floor(Math.random() * prompts.length))

  const docsUrl =
    'http://43.142.161.61:8002/pages/MCP%E6%9C%8D%E5%8A%A1/%E4%BD%BF%E7%94%A8%E6%8C%87%E5%8D%97.html'
  const backendBaseUrl = computed(() => (baseURL || window.location.origin).replace(/\/+$/, ''))
  const mcpUrl = computed(() => `${backendBaseUrl.value}/mcp`)
  const modeText = computed(() => import.meta.env.MODE || '-')
  const activePrompt = computed(() => prompts[promptIndex.value])
  const maskedApiKey = computed(() => {
    if (!apiKey.value) return '当前用户暂无 APIKey'
    if (apiKey.value.length <= 18) return apiKey.value
    return `${apiKey.value.slice(0, 12)}...${apiKey.value.slice(-8)}`
  })
  const authHeader = computed(() => (apiKey.value ? `Bearer ${apiKey.value}` : 'Bearer <MCP APIKey>'))
  const installPrompt = computed(
    () => `请根据下面的配置帮我安装 Mango MCP 服务，并在安装后查询这个 MCP 服务开放了哪些能力。

MCP 服务名称：mango-test-platform
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
    () => `[mcp_servers.mango-test-platform]
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
      onOk: () => {
        resetting.value = true
        putUserApiKey({ id: userStore.userId })
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
  .mcp-workbench {
    display: flex;
    height: 100%;
    min-height: 0;
    flex-direction: column;
    gap: 10px;
    padding-top: 8px;
    color: var(--color-text-1);
  }

  .mcp-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 8px;

    p {
      margin: 4px 0 0;
      font-size: 12px;
      line-height: 18px;
      color: var(--color-text-3);
    }
  }

  .mcp-title-row {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
  }

  .pulse {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #22c55e;
    box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.14);
  }

  .endpoint-box,
  .api-key-box {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 8px 10px;
    border: 1px solid var(--color-neutral-3);
    border-radius: 8px;
    background: var(--color-fill-1);
  }

  .endpoint-main,
  .api-key-main {
    min-width: 0;
    flex: 1;

    span {
      display: block;
      margin-bottom: 2px;
      font-size: 11px;
      color: var(--color-text-3);
    }
  }

  .endpoint-text,
  .api-key-text {
    margin: 0;
    font-size: 12px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }

  .status-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
  }

  .status-item {
    min-width: 0;
    padding: 8px;
    border: 1px solid var(--color-neutral-3);
    border-radius: 8px;

    span,
    strong {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      font-size: 11px;
      color: var(--color-text-3);
    }

    strong {
      margin-top: 3px;
      font-size: 12px;
      font-weight: 600;
    }
  }

  .capability-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .capability-item {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    padding: 8px;
    border: 1px solid var(--color-neutral-3);
    border-radius: 8px;
    background: var(--color-bg-2);

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
      color: var(--color-text-3);
    }
  }

  .capability-icon {
    flex: 0 0 auto;
    font-size: 16px;
    color: rgb(var(--primary-6));
  }

  .prompt-panel {
    padding: 8px;
    border: 1px solid var(--color-neutral-3);
    border-radius: 8px;
  }

  .prompt-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
    font-size: 12px;
    font-weight: 600;
  }

  .prompt-text {
    width: 100%;
    min-height: 48px;
    padding: 7px 8px;
    border: none;
    border-radius: 6px;
    background: var(--color-fill-1);
    color: var(--color-text-2);
    cursor: pointer;
    font-size: 12px;
    line-height: 17px;
    text-align: left;
  }

  .action-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin-top: auto;
  }

  .config-section + .config-section {
    margin-top: 16px;
  }

  .config-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
    font-weight: 600;
  }

  .config-note {
    margin-top: 12px;
    padding: 10px;
    border-radius: 8px;
    background: var(--color-fill-1);
    color: var(--color-text-2);
    font-size: 12px;
    line-height: 20px;
  }
</style>
