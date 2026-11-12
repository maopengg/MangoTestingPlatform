<template>
  <div class="mango-mcp-workbench" :class="{ 'is-compact': compact }">
    <div v-if="!compact" class="mango-mcp-head">
      <div>
        <div class="mango-mcp-title-row">
          <span class="mango-mcp-pulse"></span>
          <strong>MCP 智能接入</strong>
        </div>
        <p>让 AI 直接创建、执行和分析测试平台资产</p>
      </div>
      <a-tag :color="apiKey ? 'green' : 'orange'" size="small">
        {{ apiKey ? 'APIKey 已就绪' : '待配置 APIKey' }}
      </a-tag>
    </div>

    <div class="mango-mcp-scroll-area mango-custom-scrollbar">

      <div class="mango-mcp-prompt-panel">
        <div class="mango-mcp-prompt-head">
          <span>推荐指令</span>
          <a-button size="mini" type="text" @click="nextPrompt">
            <template #icon><icon-swap /></template>
          </a-button>
        </div>
        <button
          class="mango-mcp-prompt-text"
          type="button"
          :disabled="copyingLabel !== null"
          :aria-busy="copyingLabel === '推荐指令'"
          @click="copyText(activePrompt, '推荐指令')"
        >
          {{ activePrompt }}
        </button>
      </div>

      <div class="mango-mcp-endpoint-box">
        <div class="mango-mcp-endpoint-main">
          <span>MCP 地址</span>
          <a-typography-paragraph class="mango-mcp-endpoint-text" :ellipsis="{ rows: 1 }">
            {{ mcpUrl }}
          </a-typography-paragraph>
        </div>
        <a-tooltip content="复制 MCP 地址">
          <a-button size="mini" type="text" :loading="copyingLabel === 'MCP 地址'" :disabled="copyingLabel !== null" @click="copyText(mcpUrl, 'MCP 地址')">
            <template #icon><icon-copy /></template>
          </a-button>
        </a-tooltip>
      </div>

      <div v-if="!compact" class="mango-mcp-status-grid">
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

      <div v-if="!compact" class="mango-mcp-api-key-box">
        <div class="mango-mcp-api-key-main">
          <span>MCP APIKey</span>
          <a-typography-paragraph class="mango-mcp-api-key-text" :ellipsis="{ rows: 1 }">
            {{ maskedApiKey }}
          </a-typography-paragraph>
        </div>
        <a-space size="mini">
          <a-tooltip content="复制 Authorization 请求头">
            <a-button size="mini" type="text" :loading="copyingLabel === 'Authorization 请求头'" :disabled="keyUnavailable || copyingLabel !== null" @click="copyAuthHeader">
              <template #icon><icon-copy /></template>
            </a-button>
          </a-tooltip>
          <a-tooltip content="重置当前用户 APIKey">
            <a-button size="mini" type="text" :loading="resetting" :disabled="apiKeyLoading || resetting" @click="resetApiKey">
              <template #icon><icon-refresh /></template>
            </a-button>
          </a-tooltip>
        </a-space>
      </div>

      <div
        ref="capabilityGridRef"
        class="mango-mcp-capability-grid mango-custom-scrollbar"
        :class="{ 'mango-mcp-capability-grid--single': capabilityColumns === 1 }"
      >
        <a-popover v-for="item in capabilities" :key="item.key" :title="item.title" position="left" :trigger="['hover', 'focus']">
          <div class="mango-mcp-capability-item" tabindex="0" :aria-label="`${item.title}：${item.detail}`">
            <component :is="item.icon" class="mango-mcp-capability-icon" />
            <div><strong>{{ item.title }}</strong><span>{{ item.desc }}</span></div>
          </div>
          <template #content><p class="mango-mcp-capability-detail">{{ item.detail }}</p></template>
        </a-popover>
      </div>
    </div>

    <div class="mango-mcp-action-row">
      <a-button
        size="small"
        type="primary"
        long
        :disabled="keyUnavailable || copyingLabel !== null"
        :loading="copyingLabel === '一键安装说明'"
        @click="copyInstallPrompt"
        data-testid="qa-views-index-components-mcpworkbench-button-复制一键安装说明"
      >
        <template #icon><icon-code /></template>
        复制一键安装说明
      </a-button>
      <a-button
        size="small"
        long
        :loading="apiKeyLoading"
        @click="openConfig"
        data-testid="qa-views-index-components-mcpworkbench-button-查看配置"
      >
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
            :disabled="keyUnavailable || copyingLabel !== null"
            :loading="copyingLabel === '一键安装说明'"
            @click="copyText(installPrompt, '一键安装说明')"
            data-testid="qa-views-index-components-mcpworkbench-button-复制"
          >
            <template #icon><icon-copy /></template>
            复制
          </a-button>
        </div>
        <a-textarea :model-value="installPrompt" readonly :auto-size="{ minRows: 6, maxRows: 8 }" />
      </div>
      <div class="mango-mcp-config-section">
        <div class="mango-mcp-config-title">
          <span>Authorization</span>
          <a-button
            size="mini"
            type="text"
            :disabled="keyUnavailable || copyingLabel !== null"
            :loading="copyingLabel === 'Authorization 请求头'"
            @click="copyAuthHeader"
            data-testid="qa-views-index-components-mcpworkbench-button-复制-2"
          >
            <template #icon><icon-copy /></template>
            复制
          </a-button>
        </div>
        <a-input :model-value="authHeader" readonly />
      </div>
      <div class="mango-mcp-config-note">
        一键安装说明适合直接发送给支持 MCP 的 AI 工具；手动配置时使用下方 MCP 地址和
        Authorization。APIKey 代表当前用户身份，创建、执行和上传类操作都会使用该用户权限。
        <a-link
          :href="docsUrl"
          target="_blank"
          rel="noopener noreferrer"
          data-testid="qa-views-index-components-mcpworkbench-link-查看使用文档"
          >查看使用文档</a-link
        >
      </div>
    </a-modal>
  </div>
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { computed, markRaw, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
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
  import usePlatformBrandingStore from '@/store/modules/platform-branding'
  import { useHomeMenuIcon } from '@/views/index/composables/use-home-menu-icon'
  import { getCurrentUserApiKey, putUserApiKey } from '@/api/user/user'
  import { baseURL } from '@/api/axios.config'
  import { displayDensityScale, scaleDensityPixels } from '@/hooks/useDisplayDensity'

  withDefaults(defineProps<{ compact?: boolean }>(), {
    compact: false,
  })

  const userStore = useUserStore()
  const branding = usePlatformBrandingStore()
  const { resolveMenuIcon } = useHomeMenuIcon()
  const apiKey = ref('')
  const configVisible = ref(false)
  const resetting = ref(false)
  const apiKeyLoading = ref(false)
  const apiKeyFailed = ref(false)
  const copyingLabel = ref<string | null>(null)
  const keyUnavailable = computed(() => !apiKey.value || apiKeyLoading.value || resetting.value)
  const route = useRoute(), entryPath = route.path
  const contextKey = computed(() => JSON.stringify([
    route.fullPath, userStore.userId, userStore.roleId, userStore.token, userStore.selected_environment,
  ]))
  let active = true, mounted = false, generation = 0, keyReadSequence = 0, credentialVersion = 0
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const available = () => active && route.path === entryPath
  const capabilityGridRef = ref<HTMLElement | null>(null)
  const capabilityColumns = ref<1 | 2>(2)
  let capabilityResizeObserver: ResizeObserver | null = null
  let capabilityLayoutFrame = 0

  const capabilities = computed(() => [
    {
      key: 'api',
      detail: '查询和维护接口、请求头、全局变量与授权；编排、调试和执行 API 用例，查看场景、断言与失败原因。',
      title: 'API自动化',
      desc: '接口、用例、场景、执行和失败分析',
      icon: resolveMenuIcon('/apitest', markRaw(IconRobot)),
    },
    {
      key: 'ui',
      detail: '维护页面、元素、页面步骤与 UI 用例，导入 Playwright 步骤，执行用例并查询结果和截图。',
      title: 'UI自动化',
      desc: '页面、元素、步骤、用例和执行',
      icon: resolveMenuIcon('/uitest', markRaw(IconCode)),
    },
    {
      key: 'pytest',
      detail: '绑定 Pytest 工程、同步仓库与文件，维护用例配置，触发执行并查询执行结果。',
      title: 'Pytest自动化',
      desc: '项目绑定、仓库同步、文件读写和执行',
      icon: resolveMenuIcon('/pytest', markRaw(IconBook)),
    },
    {
      key: 'factory',
      detail: '发现数据源表结构，维护实体、字段规则与场景模板，预览并按已保存配置生成、校验及清理数据。',
      title: '数据工厂',
      desc: '表结构、实体、模板与已保存配置的执行和清理',
      icon: resolveMenuIcon('/data-factory', markRaw(IconStorage)),
    },
    {
      key: 'report',
      detail: '分页查询执行报告和条目结果，分析失败、查看调用链与执行效能，按平台规则重试失败项。',
      title: '测试报告',
      desc: '报告查询、失败分析和安全重试',
      icon: resolveMenuIcon('/report', markRaw(IconBug)),
    },
    {
      key: 'task',
      detail: '维护定时任务和执行策略，绑定或解绑 UI、API、Pytest 用例，查询触发与执行记录。',
      title: '定时任务',
      desc: '任务策略、用例绑定、触发和执行记录',
      icon: resolveMenuIcon('/timing', markRaw(IconRefresh)),
    },
    {
      key: 'monitoring', title: '监控中心', desc: '监控任务、脚本、运行控制和日志',
      detail: '查询和维护监控任务及脚本，启动或停止监控，查看任务状态和运行日志。',
      icon: resolveMenuIcon('/monitoring', markRaw(IconCode)),
    },
    {
      key: 'evaluation', title: '评测中心', desc: '数据集、版本、评分器、用例和结果',
      detail: '维护评测数据集、版本和条目，查询评分器定义，配置并执行评测用例，查看评分与执行结果。',
      icon: resolveMenuIcon('/evaluation', markRaw(IconSafe)),
    },
    {
      key: 'project', title: '项目与环境', desc: '项目产品、模块、被测对象与环境',
      detail: '查询项目产品与模块，维护产品模块层级，发现被测对象和环境，切换当前用户被测环境。',
      icon: resolveMenuIcon('/config', markRaw(IconStorage)),
    },
    {
      key: 'todo', title: '风险待办', desc: '授权到期、刷新与数据模型风险',
      detail: '查询当前用户可见的风险待办与来源详情，定位授权、刷新和数据模型异常。',
      icon: resolveMenuIcon('/personal', markRaw(IconBug)),
    },
    {
      key: 'functional',
      detail: '维护迭代、需求、设计、用例、计划、缺陷及上下文资料，管理功能用例与自动化资产的绑定。',
      title: '功能测试',
      desc: '需求、用例、资料和自动化绑定',
      icon: resolveMenuIcon('/functional-test', markRaw(IconSafe)),
    },
    {
      key: 'ai',
      detail: '发现 MCP Skill 目录、工具元数据、资源及提示模板，按能力文档选择对应工具。',
      title: '服务能力',
      desc: 'Skill 文档与 MCP 工具元数据发现',
      icon: resolveMenuIcon('/ai', markRaw(IconRobot)),
    },
    {
      key: 'file',
      detail: '查询系统文件，上传附件并获取下载地址，供用例和平台资料引用。',
      title: '系统文件',
      desc: '文件查询、上传和下载地址获取',
      icon: resolveMenuIcon('/system', markRaw(IconFile)),
    },
  ])

  const mcpServerName = computed(() => branding.englishName)
  const prompts = computed(() => [
    `使用 ${mcpServerName.value} MCP 查询当前平台开放了哪些能力。`,
    `使用 ${mcpServerName.value} MCP 查询当前用户的项目、测试环境和可用模块。`,
    `使用 ${mcpServerName.value} MCP 创建一个 API case，执行后分析失败原因。`,
    `使用 ${mcpServerName.value} MCP 创建一个 UI 页面步骤并绑定到 UI 用例中。`,
    `使用 ${mcpServerName.value} MCP 为指定表创建数据实体和模板，并预览生成数据。`,
    `使用 ${mcpServerName.value} MCP 查询测试报告，筛选失败用例并生成排查结论。`,
    `使用 ${mcpServerName.value} MCP 查询监控任务，查看运行状态和最近日志。`,
    `使用 ${mcpServerName.value} MCP 查询评测数据集和评分器，配置并执行评测用例。`,
    `使用 ${mcpServerName.value} MCP 查询 Skill 清单和工具元数据。`,
  ])
  const promptIndex = ref(Math.floor(Math.random() * prompts.value.length))

  const docsUrl =
    'http://160.202.231.91:36696/pages/MCP%E6%9C%8D%E5%8A%A1/%E4%BD%BF%E7%94%A8%E6%8C%87%E5%8D%97.html'
  const backendBaseUrl = computed(() => {
    if (!baseURL || baseURL.startsWith('/')) {
      return window.location.origin.replace(/\/+$/, '')
    }
    return baseURL.replace(/\/+$/, '').replace(/\/api$/i, '')
  })
  const mcpUrl = computed(() => `${backendBaseUrl.value}/mcp`)
  const modeText = computed(() => import.meta.env.MODE || '-')
  const activePrompt = computed(() => prompts.value[promptIndex.value])
  const maskedApiKey = computed(() => {
    if (apiKeyLoading.value) return '正在加载 APIKey'
    if (!apiKey.value) return '当前用户暂无 APIKey'
    if (apiKey.value.length <= 18) return '••••••••'
    return `${apiKey.value.slice(0, 12)}...${apiKey.value.slice(-8)}`
  })
  const authHeader = computed(() =>
    apiKey.value ? `Bearer ${apiKey.value}` : 'Bearer <MCP APIKey>'
  )
  const installPrompt = computed(
    () => `请根据下面的配置帮我安装 ${mcpServerName.value} MCP 服务。安装完成后，请查询并向我说明这个 MCP 服务开放的功能，以及服务端提供了哪些 Skill。

MCP 服务名称：${mcpServerName.value}
URL：${mcpUrl.value}
Headers：
Authorization: ${authHeader.value}

要求：
1. 使用 Streamable HTTP 方式连接，将 Authorization 直接保存到 MCP 配置中，不要作为系统变量注入。
2. 安装后读取 MCP 初始化说明并调用 get_mcp_server_info，确认连接成功。
3. 完整查询 Tools、Resources、Resource Templates 和 Prompts，并按服务实际返回归纳功能。本步骤只查看工具清单及元数据，不调用清单中的任何业务工具。
4. 读取 mango://skills/catalog；如果客户端不支持 MCP Resource，则调用 list_mcp_skills 并处理全部分页。列出每个 Skill 的名称、标题、分类、用途和当前版本，并说明如何按任务读取对应 Skill。
5. 明确说明 Skill 更新方式：后续调用 list_mcp_skills 时通过 known_versions 传入本地已知版本；发现 update_available=true 后重新获取对应 Skill，无需重新安装 MCP。
6. 安装完成后的回复包含安装及连接结果、MCP 功能清单、Skill 清单以及 Skill 使用与更新方式。`
  )
  function nextPrompt() {
    promptIndex.value = (promptIndex.value + 1) % prompts.value.length
  }

  function fallbackCopy(text: string) {
    const input = document.createElement('textarea')
    input.value = text
    input.style.position = 'fixed'
    input.style.opacity = '0'
    document.body.appendChild(input)
    try {
      input.select()
      if (!document.execCommand('copy')) throw Error('Clipboard unavailable')
    } finally { document.body.removeChild(input) }
  }

  async function copyText(text: string, label: string) {
    if (!available() || !text || copyingLabel.value !== null || resetting.value) return
    const currentGeneration = generation, version = credentialVersion
    const current = () => available() && generation === currentGeneration && credentialVersion === version
    copyingLabel.value = label
    try {
      if (navigator.clipboard && window.isSecureContext) {
        try { await navigator.clipboard.writeText(text) }
        catch {
          if (!current()) return
          fallbackCopy(text)
        }
      } else {
        fallbackCopy(text)
      }
      if (current()) Message.success(`${label}已复制`)
    } catch {
      if (current()) Message.error('复制失败，请重试')
    } finally { copyingLabel.value = null }
  }

  function copyAuthHeader() {
    if (!available() || apiKeyLoading.value || resetting.value) return
    if (!apiKey.value) {
      Message.warning('当前用户暂无 APIKey')
      return
    }
    return copyText(`Authorization: ${authHeader.value}`, 'Authorization 请求头')
  }

  function copyInstallPrompt() {
    if (!available() || apiKeyLoading.value || resetting.value) return
    if (!apiKey.value) {
      Message.warning('当前用户暂无 APIKey，请先在用户管理中生成或重置 APIKey')
      return
    }
    return copyText(installPrompt.value, '一键安装说明')
  }

  function openConfig() {
    if (available()) configVisible.value = true
  }

  function readApiKey(value: unknown): string {
    if (!value || typeof value !== 'object' || !('code' in value) || value.code !== 200 || !('data' in value)) throw Error('Invalid APIKey response')
    const data = value.data
    if (!data || typeof data !== 'object' || !('api_key' in data) || typeof data.api_key !== 'string' || !data.api_key.trim()) throw Error('Invalid APIKey response')
    return data.api_key
  }

  async function loadCurrentUserApiKey() {
    if (!available() || !userStore.userId || resetting.value) return
    const sequence = ++keyReadSequence, currentGeneration = generation
    const current = () => available() && sequence === keyReadSequence && currentGeneration === generation
    apiKeyLoading.value = true
    apiKeyFailed.value = false
    try {
      const key = readApiKey(await getCurrentUserApiKey())
      if (current()) { apiKey.value = key; credentialVersion++ }
    } catch (loadFailure0) {
      if (current()) (reportLoadError(loadFailure0, "加载失败，请重试", false), apiKeyFailed.value = true)
    } finally { if (current()) apiKeyLoading.value = false }
  }

  function resetApiKey() {
    if (!available() || !userStore.userId || resetting.value || apiKeyLoading.value || confirmation) return
    const currentGeneration = generation
    let dialog: ReturnType<typeof Modal.confirm> | null = null
    const current = () => available() && currentGeneration === generation && confirmation === dialog
    dialog = Modal.confirm({
      title: '重置 MCP APIKey',
      content: '重置后旧 APIKey 会立即失效，已配置的 MCP 客户端需要更新。',
      cancelText: '取消',
      okText: '重置',
      onClose: () => { if (confirmation === dialog) confirmation = null },
      onBeforeCancel: () => !resetting.value,
      onBeforeOk: async () => {
        if (!current() || resetting.value) return false
        resetting.value = true
        credentialVersion++
        keyReadSequence++
        try {
          const key = readApiKey(await putUserApiKey({}))
          if (!current()) return false
          apiKey.value = key
          apiKeyFailed.value = false
          Message.success('APIKey 已重置，请更新 MCP 客户端配置')
          return true
        } catch {
          if (current()) Message.error('APIKey 重置失败，请重试')
          return false
        } finally {
          resetting.value = false
          if (mounted && available() && currentGeneration !== generation) void loadCurrentUserApiKey()
        }
      },
    })
    confirmation = dialog
  }

  function updateCapabilityColumns() {
    const container = capabilityGridRef.value
    if (!container) return
    const gap = Number.parseFloat(getComputedStyle(container).rowGap) || 0
    const minimumRowHeight = scaleDensityPixels(48)
    const singleColumnHeight =
      capabilities.value.length * minimumRowHeight +
      Math.max(0, capabilities.value.length - 1) * gap
    capabilityColumns.value = container.clientHeight >= singleColumnHeight ? 1 : 2
  }

  function scheduleCapabilityLayout() {
    if (!available()) return
    if (capabilityLayoutFrame) window.cancelAnimationFrame(capabilityLayoutFrame)
    capabilityLayoutFrame = window.requestAnimationFrame(() => {
      if (available()) updateCapabilityColumns()
      capabilityLayoutFrame = 0
    })
  }

  function stopLayout() {
    capabilityResizeObserver?.disconnect()
    capabilityResizeObserver = null
    window.removeEventListener('resize', scheduleCapabilityLayout)
    if (capabilityLayoutFrame) window.cancelAnimationFrame(capabilityLayoutFrame)
    capabilityLayoutFrame = 0
  }
  function startLayout() {
    stopLayout()
    if (!available()) return
    scheduleCapabilityLayout()
    if (capabilityGridRef.value && typeof ResizeObserver !== 'undefined') {
      capabilityResizeObserver = new ResizeObserver(scheduleCapabilityLayout)
      capabilityResizeObserver.observe(capabilityGridRef.value)
    } else {
      window.addEventListener('resize', scheduleCapabilityLayout)
    }
  }

  watch(displayDensityScale, scheduleCapabilityLayout)
  watch(capabilityGridRef, startLayout, { flush: 'post' })
  function invalidate() {
    generation++; credentialVersion++; keyReadSequence++
    apiKey.value = ''; apiKeyLoading.value = false; apiKeyFailed.value = false; configVisible.value = false
    confirmation?.close(); confirmation = null
  }
  watch(contextKey, () => { invalidate(); if (mounted) void loadCurrentUserApiKey() }, { flush: 'sync' })
  onMounted(() => { mounted = true; void loadCurrentUserApiKey(); startLayout() })
  onDeactivated(() => { active = false; invalidate(); stopLayout() })
  onActivated(() => {
    if (mounted && !active) { active = true; void loadCurrentUserApiKey(); startLayout() }
  })
  onBeforeUnmount(() => { active = false; mounted = false; invalidate(); stopLayout() })
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
    overflow: hidden;
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
    display: grid;
    width: 16px;
    height: 16px;
    flex: none;
    place-items: center;
    border-radius: 50%;
    background: color-mix(in srgb, var(--m-success) 18%, transparent);

    &::after {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--m-success);
      content: '';
    }
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
    flex: 1 1 170px;
    min-height: 0;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
    align-content: start;
    overflow-y: auto;
    padding-right: 2px;
  }

  .mango-mcp-capability-grid--single {
    grid-template-columns: minmax(0, 1fr);
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

    .mango-mcp-capability-grid {
      flex-basis: 142px;
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
      flex-basis: 118px;
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

  .mango-mcp-workbench.is-compact {
    gap: 5px;
    padding-top: 3px;
    padding-bottom: 3px;

    .mango-mcp-scroll-area {
      flex: 1 1 auto;
      gap: 5px;
      overflow: hidden;
      padding-right: 4px;
    }

    .mango-mcp-endpoint-box,
    .mango-mcp-api-key-box {
      min-height: 56px;
      padding: 8px 10px;
    }

    .mango-mcp-endpoint-main span,
    .mango-mcp-api-key-main span {
      margin-bottom: 4px;
    }

    .mango-mcp-endpoint-text,
    .mango-mcp-api-key-text {
      line-height: 18px;
    }

    .mango-mcp-action-row {
      grid-template-columns: 1fr 1fr;
      gap: 5px;
      padding: 1px 0 0;
    }

    .mango-mcp-capability-grid {
      flex: 1 1 0;
      min-height: 80px;
      overflow-y: auto;
      overscroll-behavior: contain;
    }

    :deep(.arco-btn-size-small) {
      height: 26px;
      padding: 0 7px;
      font-size: 11px;
    }
  }
  .mango-mcp-prompt-panel, .mango-mcp-endpoint-box, .mango-mcp-status-grid, .mango-mcp-api-key-box, .mango-mcp-action-row { flex-shrink: 0; }
  .mango-mcp-capability-item:focus-visible { outline: 2px solid var(--m-primary); outline-offset: -2px; }
  .mango-mcp-capability-detail { max-width: 320px; margin: 0; color: var(--m-text-2); line-height: 22px; overflow-wrap: anywhere; }
</style>
