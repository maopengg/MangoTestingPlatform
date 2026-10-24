<template>
  <div class="mango-ai-assistant">
    <a-tooltip v-if="showTrigger" content="Mango AI 助手" position="left">
      <button class="mango-ai-assistant__trigger" type="button" @click="togglePanel">
        <icon-robot class="mango-ai-assistant__trigger-icon" />
        <span
          :class="[
            'mango-ai-assistant__trigger-status',
            aiOnline
              ? 'mango-ai-assistant__trigger-status--online'
              : 'mango-ai-assistant__trigger-status--offline',
          ]"
        ></span>
      </button>
    </a-tooltip>

    <section v-if="visible" class="mango-ai-assistant__panel">
      <header class="mango-ai-assistant__header">
        <div>
          <strong>Mango AI 助手</strong>
          <span>{{ statusText }}</span>
        </div>
        <a-space class="mango-ai-assistant__header-actions" size="mini">
          <a-tooltip content="新建对话">
            <a-button
              size="mini"
              type="text"
              :disabled="!aiOnline || sending"
              @click="createSession"
            >
              <template #icon><icon-plus /></template>
            </a-button>
          </a-tooltip>
          <a-tooltip content="刷新 AI / MCP 状态">
            <a-button size="mini" type="text" :loading="statusLoading" @click="loadStatus">
              <template #icon><icon-refresh /></template>
            </a-button>
          </a-tooltip>
          <a-button size="mini" type="text" @click="closeAiAssistant">
            <template #icon><icon-close /></template>
          </a-button>
        </a-space>
      </header>

      <div class="mango-ai-assistant__body">
        <div class="mango-ai-assistant__chat">
          <a-alert v-if="!aiOnline" class="mango-ai-assistant__alert" type="warning">
            AI 当前不可用，请检查系统管理中的 AI 配置。
          </a-alert>
          <a-alert v-else-if="!mcpOnline" class="mango-ai-assistant__alert" type="info">
            当前 MCP 未连接，仍可进行普通 AI 对话，但不能查询或操作平台资产。
          </a-alert>
          <div class="mango-ai-assistant__context-bar">
            <div>
              <span>当前上下文</span>
              <strong>{{ activeSessionTitle }}</strong>
            </div>
            <div class="mango-ai-assistant__context-actions">
              <a-select
                v-model="selectedMcpServerId"
                size="mini"
                :options="mcpOptions"
                :field-names="{ value: 'value', label: 'label' }"
                allow-clear
                placeholder="选择MCP"
                @change="loadStatus" data-testid="qa-components-ai-aiassistantwidget-select-选择mcp"
              />
              <a-button size="mini" type="text" @click="historyVisible = true" data-testid="qa-components-ai-aiassistantwidget-button-切换">切换</a-button>
            </div>
          </div>

          <main ref="messageBody" class="mango-ai-assistant__messages mango-custom-scrollbar">
            <div v-if="messages.length === 0" class="mango-ai-assistant__empty">
              <icon-robot />
              <span>{{
                aiOnline ? '可以直接提问；选择可用 MCP 后还能查询测试资产。' : '请先配置可用的 AI。'
              }}</span>
            </div>
            <article
              v-for="item in messages"
              :key="item.id || item.local_id"
              :class="['mango-ai-assistant__message', `mango-ai-assistant__message--${item.role}`]"
            >
              <div class="mango-ai-assistant__bubble">
                <div
                  class="mango-ai-assistant__markdown"
                  v-html="renderMarkdown(item.content)"
                ></div>
                <div v-if="item.need_confirm" class="mango-ai-assistant__confirm">
                  <div>
                    <strong>{{ item.tool_name }}</strong>
                    <span>该操作需要确认后才会调用 MCP。</span>
                  </div>
                  <a-collapse :bordered="false">
                    <a-collapse-item key="args" header="查看参数">
                      <pre>{{ formatJson(item.tool_arguments) }}</pre>
                    </a-collapse-item>
                  </a-collapse>
                  <a-space size="mini">
                    <a-button
                      size="small"
                      type="primary"
                      :loading="confirmLoading === item.id"
                      @click="confirmTool(item)" data-testid="qa-components-ai-aiassistantwidget-button-确认执行"
                    >
                      确认执行
                    </a-button>
                    <a-button size="small" @click="item.need_confirm = false" data-testid="qa-components-ai-aiassistantwidget-button-取消">取消</a-button>
                  </a-space>
                </div>
              </div>
            </article>
            <div v-if="sending" class="mango-ai-assistant__typing">
              <a-spin size="small" />
              <span>正在处理...</span>
            </div>
          </main>

          <footer class="mango-ai-assistant__footer">
            <a-textarea
              v-model="input"
              :disabled="!aiOnline || sending"
              :auto-size="{ minRows: 2, maxRows: 4 }"
              placeholder="输入问题，Enter 发送，Shift + Enter 换行"
              @compositionstart="isComposing = true"
              @compositionend="isComposing = false"
              @keydown.enter.exact="handleEnter" data-testid="qa-components-ai-aiassistantwidget-textarea-输入问题-enter-发送-shift-enter-换行"
            />
            <a-button
              class="mango-ai-assistant__send-button"
              type="primary"
              :status="sending ? 'warning' : 'normal'"
              :disabled="!sending && (!aiOnline || !input.trim())"
              @click="sending ? stopMessage() : sendMessage()"
            >
              <template #icon>
                <icon-pause-circle v-if="sending" />
                <icon-send v-else />
              </template>
            </a-button>
          </footer>
        </div>
      </div>

      <aside v-if="historyVisible" class="mango-ai-assistant__history">
        <div class="mango-ai-assistant__history-head">
          <div>
            <strong>历史上下文</strong>
            <span>{{ sessions.length }} 个会话</span>
          </div>
          <a-space size="mini">
            <a-button
              size="mini"
              type="text"
              :disabled="!aiOnline || sending"
              @click="createSession" data-testid="qa-components-ai-aiassistantwidget-button-新建"
              >新建</a-button
            >
            <a-tooltip content="清空当前会话">
              <a-button
                size="mini"
                type="text"
                :disabled="!sessionId || sending"
                @click="clearSession"
              >
                <template #icon><icon-delete /></template>
              </a-button>
            </a-tooltip>
            <a-button size="mini" type="text" @click="historyVisible = false">
              <template #icon><icon-close /></template>
            </a-button>
          </a-space>
        </div>
        <div class="mango-ai-assistant__session-list mango-custom-scrollbar">
          <button
            v-for="item in sessions"
            :key="item.id"
            :class="[
              'mango-ai-assistant__session-item',
              { 'mango-ai-assistant__session-item--active': item.id === sessionId },
            ]"
            type="button"
            :disabled="sending"
            @click="selectSession(item.id)"
          >
            <strong>{{ item.title || '新会话' }}</strong>
            <span>{{ item.current_page || '无页面上下文' }}</span>
            <small>{{ item.update_time || item.create_time }}</small>
          </button>
          <a-empty v-if="!sessionLoading && sessions.length === 0" description="暂无上下文" />
        </div>
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
  import { computed, nextTick, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message } from '@arco-design/web-vue'
  import {
    fetchAiAssistantMessageStream,
    getAiAssistantMessage,
    getAiAssistantSession,
    getAiAssistantSessionList,
    getAiAssistantStatus,
    postAiAssistantClear,
    postAiAssistantSession,
    postAiAssistantToolConfirm,
  } from '@/api/ai'
  import { useAiAssistantPanel } from '@/hooks/use-ai-assistant-panel'

  const props = withDefaults(
    defineProps<{
      showTrigger?: boolean
    }>(),
    {
      showTrigger: false,
    }
  )

  const route = useRoute()
  const { visible, closeAiAssistant, toggleAiAssistant } = useAiAssistantPanel()
  const showTrigger = computed(() => props.showTrigger)
  const statusLoading = ref(false)
  const sessionLoading = ref(false)
  const sending = ref(false)
  const confirmLoading = ref<number | string>('')
  const historyVisible = ref(false)
  const aiOnline = ref(false)
  const mcpOnline = ref(false)
  const status = ref<any>({})
  const selectedMcpServerId = ref<number | null>(null)
  const sessionId = ref<number | null>(null)
  const sessions = ref<any[]>([])
  const messages = ref<any[]>([])
  const input = ref('')
  const isComposing = ref(false)
  const streamController = ref<AbortController | null>(null)
  const messageBody = ref<HTMLElement>()

  const statusText = computed(() => {
    if (statusLoading.value) return '正在检测 AI / MCP'
    if (!aiOnline.value) return 'AI 未连接'
    return mcpOnline.value ? 'AI 已连接，MCP 已连接' : 'AI 已连接，MCP 未连接'
  })
  const mcpOptions = computed(() =>
    (status.value?.candidates || []).map((item: any) => ({
      value: item.server_id,
      label: `${item.is_builtin ? '内置 / ' : ''}${item.server_name || `MCP #${item.server_id}`}${
        item.is_connected ? '' : '（未连接）'
      }`,
    }))
  )
  const activeSessionTitle = computed(() => {
    const session = sessions.value.find((item) => item.id === sessionId.value)
    return (
      session?.title ||
      session?.current_page ||
      String(route.meta?.title || route.name || '当前页面')
    )
  })

  async function togglePanel() {
    toggleAiAssistant()
    historyVisible.value = false
  }

  async function loadStatus() {
    statusLoading.value = true
    try {
      const res = await getAiAssistantStatus(
        selectedMcpServerId.value ? { mcp_server_id: selectedMcpServerId.value } : {}
      )
      status.value = res.data || {}
      aiOnline.value = !!status.value.ai_available
      mcpOnline.value = !!status.value.is_connected
      const candidates = status.value.candidates || []
      if (!selectedMcpServerId.value) {
        selectedMcpServerId.value =
          candidates.find((item: any) => item.is_builtin)?.server_id ||
          status.value.server_id ||
          candidates.find((item: any) => item.is_connected)?.server_id ||
          null
      }
    } finally {
      statusLoading.value = false
    }
  }

  async function loadSessions() {
    sessionLoading.value = true
    try {
      const res = await getAiAssistantSessionList()
      sessions.value = res.data || []
    } finally {
      sessionLoading.value = false
    }
  }

  async function loadSession(id?: number | null) {
    const sessionRes = await getAiAssistantSession(id ? { id } : {})
    sessionId.value = sessionRes.data?.id || null
    if (!sessionId.value) return
    const messageRes = await getAiAssistantMessage({ session_id: sessionId.value })
    messages.value = (messageRes.data || []).filter((item: any) => item.role !== 'tool')
    await loadSessions()
    scrollToBottom()
  }

  async function createSession() {
    if (!aiOnline.value || sending.value) return
    const res = await postAiAssistantSession({ page_context: pageContext(), title: '新会话' })
    sessionId.value = res.data?.id || null
    messages.value = []
    historyVisible.value = false
    await loadSessions()
    scrollToBottom()
  }

  async function switchSession(id: number) {
    if (sending.value || id === sessionId.value) return
    await loadSession(id)
  }

  async function selectSession(id: number) {
    await switchSession(id)
    historyVisible.value = false
  }

  function pageContext() {
    return {
      route: route.fullPath,
      name: route.name,
      title: route.meta?.title,
      query: route.query,
      params: route.params,
    }
  }

  function currentMcpServerId() {
    return selectedMcpServerId.value || status.value?.server_id || null
  }

  function handleEnter(event: KeyboardEvent) {
    if (isComposing.value || event.isComposing) {
      return
    }
    event.preventDefault()
    sendMessage()
  }

  async function sendMessage() {
    const content = input.value.trim()
    if (!content || !aiOnline.value || sending.value) return
    streamController.value = new AbortController()
    const localMessage = { local_id: Date.now(), role: 'user', content }
    const assistantMessage = { local_id: Date.now() + 1, role: 'assistant', content: '' }
    messages.value.push(localMessage)
    messages.value.push(assistantMessage)
    input.value = ''
    sending.value = true
    scrollToBottom()
    try {
      await fetchAiAssistantMessageStream(
        {
          session_id: sessionId.value,
          content,
          page_context: pageContext(),
          mcp_server_id: currentMcpServerId(),
        },
        ({ event, data }) => {
          if (event === 'session' && data?.session_id) {
            sessionId.value = data.session_id
          } else if (event === 'delta') {
            assistantMessage.content += data?.content || ''
            scrollToBottom()
          } else if (event === 'message') {
            Object.assign(assistantMessage, data)
            scrollToBottom()
          } else if (event === 'error') {
            assistantMessage.content = data?.message || 'AI 助手暂不可用'
            if (data?.status) {
              status.value = data.status
              aiOnline.value = !!data.status.ai_available
              mcpOnline.value = !!data.status.is_connected
            }
            Message.warning(assistantMessage.content)
          }
        },
        streamController.value.signal
      )
      await loadSessions()
    } catch (error) {
      if ((error as Error)?.name === 'AbortError') {
        assistantMessage.content = assistantMessage.content || '已暂停'
        return
      }
      await loadStatus()
      assistantMessage.content = 'AI 助手暂不可用，请检查 AI 配置'
      Message.warning('AI 助手暂不可用，请检查 AI 配置')
    } finally {
      sending.value = false
      streamController.value = null
      scrollToBottom()
    }
  }

  function stopMessage() {
    streamController.value?.abort()
  }

  async function confirmTool(item: any) {
    confirmLoading.value = item.id
    try {
      const res = await postAiAssistantToolConfirm({ message_id: item.id })
      item.need_confirm = false
      if (res.data?.message) {
        messages.value.push(res.data.message)
      }
    } finally {
      confirmLoading.value = ''
      scrollToBottom()
    }
  }

  async function clearSession() {
    if (!sessionId.value) return
    await postAiAssistantClear({ session_id: sessionId.value })
    sessionId.value = null
    messages.value = []
    if (aiOnline.value) {
      await loadSessions()
      if (sessions.value[0]?.id) {
        await loadSession(sessions.value[0].id)
      } else {
        await createSession()
      }
    }
  }

  watch(visible, async (isVisible) => {
    if (!isVisible) return
    historyVisible.value = false
    await loadStatus()
    if (aiOnline.value) {
      await loadSessions()
      await loadSession(sessionId.value || sessions.value[0]?.id)
    }
  })

  function scrollToBottom() {
    nextTick(() => {
      if (messageBody.value) {
        messageBody.value.scrollTop = messageBody.value.scrollHeight
      }
    })
  }

  function formatJson(value: any) {
    return JSON.stringify(value || {}, null, 2)
  }

  function escapeHtml(value: string) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;')
  }

  function renderInlineMarkdown(value: string) {
    return escapeHtml(value)
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  }

  function renderMarkdown(value: string) {
    const lines = String(value || '').split('\n')
    const html: string[] = []
    let inCode = false
    let codeLines: string[] = []
    let listType = ''

    const closeList = () => {
      if (listType) {
        html.push(`</${listType}>`)
        listType = ''
      }
    }

    lines.forEach((line) => {
      if (line.trim().startsWith('```')) {
        if (inCode) {
          html.push(`<pre><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`)
          codeLines = []
          inCode = false
        } else {
          closeList()
          inCode = true
        }
        return
      }
      if (inCode) {
        codeLines.push(line)
        return
      }

      const ordered = line.match(/^\s*\d+\.\s+(.+)$/)
      const unordered = line.match(/^\s*[-*]\s+(.+)$/)
      if (ordered || unordered) {
        const type = ordered ? 'ol' : 'ul'
        if (listType !== type) {
          closeList()
          html.push(`<${type}>`)
          listType = type
        }
        html.push(`<li>${renderInlineMarkdown((ordered || unordered)?.[1] || '')}</li>`)
        return
      }

      closeList()
      if (!line.trim()) {
        html.push('<br />')
        return
      }
      html.push(`<p>${renderInlineMarkdown(line)}</p>`)
    })

    closeList()
    if (inCode) {
      html.push(`<pre><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`)
    }
    return html.join('')
  }
</script>

<style scoped lang="less">
  .mango-ai-assistant {
    position: fixed;
    right: 24px;
    bottom: 80px;
    z-index: 2200;
  }

  .mango-ai-assistant__trigger {
    position: relative;
    display: inline-flex;
    width: 48px;
    height: 48px;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--m-border);
    border-radius: 50%;
    background: var(--m-surface);
    color: var(--m-text);
    box-shadow: var(--m-shadow);
    cursor: pointer;
    transition: border-color 0.16s ease, transform 0.16s ease, box-shadow 0.16s ease;
  }

  .mango-ai-assistant__trigger:hover {
    border-color: var(--m-primary-border);
    transform: translateY(-2px);
  }

  .mango-ai-assistant__trigger-icon {
    color: var(--m-primary);
    font-size: 22px;
  }

  .mango-ai-assistant__trigger-status {
    position: absolute;
    right: 7px;
    bottom: 7px;
    width: 8px;
    height: 8px;
    border: 1px solid var(--m-surface);
    border-radius: 50%;
    background: var(--m-muted);
  }

  .mango-ai-assistant__trigger-status--online {
    background: var(--m-success);
  }

  .mango-ai-assistant__trigger-status--offline {
    background: var(--m-muted);
  }

  .mango-ai-assistant__panel {
    position: absolute;
    right: 0;
    bottom: 60px;
    display: flex;
    width: min(430px, calc(100vw - 32px));
    height: min(780px, calc(100vh - 96px));
    overflow: hidden;
    flex-direction: column;
    border: 1px solid var(--m-border);
    border-radius: 8px;
    background: var(--m-surface);
    box-shadow: var(--m-shadow);
  }

  .mango-ai-assistant__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 12px 14px;
    border-bottom: 1px solid var(--m-border);

    > div {
      display: grid;
      gap: 2px;
      min-width: 0;
    }

    strong {
      color: var(--m-text);
      font-size: 14px;
    }

    span {
      color: var(--m-text-2);
      font-size: 12px;
    }
  }

  .mango-ai-assistant__header > .mango-ai-assistant__header-actions {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    gap: 4px;
  }

  .mango-ai-assistant__body {
    display: flex;
    flex: 1;
    min-height: 0;
    flex-direction: column;
  }

  .mango-ai-assistant__history {
    position: absolute;
    inset: 49px 0 0;
    z-index: 2;
    display: flex;
    flex-direction: column;
    background: var(--m-surface);
  }

  .mango-ai-assistant__history-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 12px;
    border-bottom: 1px solid var(--m-border);

    > div {
      display: grid;
      gap: 2px;
      min-width: 0;
    }

    strong {
      color: var(--m-text);
      font-size: 14px;
    }

    span {
      color: var(--m-muted);
      font-size: 12px;
    }
  }

  .mango-ai-assistant__session-list {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 10px;
  }

  .mango-ai-assistant__session-item {
    display: grid;
    width: 100%;
    gap: 3px;
    margin-bottom: 8px;
    padding: 9px 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
    color: var(--m-text-2);
    cursor: pointer;
    text-align: left;
  }

  .mango-ai-assistant__session-item:hover {
    border-color: color-mix(in srgb, var(--m-primary) 28%, var(--m-border));
  }

  .mango-ai-assistant__session-item--active {
    border-color: var(--m-primary);
    background: color-mix(in srgb, var(--m-primary) 7%, var(--m-surface));
  }

  .mango-ai-assistant__session-item strong,
  .mango-ai-assistant__session-item span,
  .mango-ai-assistant__session-item small {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-ai-assistant__session-item strong {
    color: var(--m-text);
    font-size: 13px;
  }

  .mango-ai-assistant__session-item span,
  .mango-ai-assistant__session-item small {
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-ai-assistant__chat {
    display: flex;
    min-width: 0;
    min-height: 0;
    flex: 1;
    flex-direction: column;
  }

  .mango-ai-assistant__context-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 8px 12px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface-soft);

    > div {
      display: grid;
      gap: 2px;
      min-width: 0;
    }

    span {
      color: var(--m-muted);
      font-size: 12px;
    }

    strong {
      overflow: hidden;
      color: var(--m-text);
      font-size: 12px;
      font-weight: 500;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .mango-ai-assistant__context-actions {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    gap: 6px;

    :deep(.arco-select) {
      width: 168px;
    }
  }

  .mango-ai-assistant__alert {
    margin: 10px 12px 0;
  }

  .mango-ai-assistant__messages {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 12px;
    background: var(--m-bg);
  }

  .mango-ai-assistant__empty {
    display: grid;
    height: 100%;
    place-items: center;
    align-content: center;
    gap: 10px;
    color: var(--m-text-2);
    text-align: center;
    font-size: 13px;
  }

  .mango-ai-assistant__message {
    display: flex;
    margin-bottom: 10px;
  }

  .mango-ai-assistant__message--user {
    justify-content: flex-end;
  }

  .mango-ai-assistant__message--assistant {
    justify-content: flex-start;
  }

  .mango-ai-assistant__bubble {
    max-width: 92%;
    border: 1px solid var(--m-border);
    border-radius: 8px;
    background: var(--m-surface);
    padding: 8px 10px;
  }

  .mango-ai-assistant__markdown {
    color: var(--m-text);
    font-size: 13px;
    line-height: 1.55;

    :deep(p) {
      margin: 0;
      white-space: pre-wrap;
    }

    :deep(p + p),
    :deep(p + ol),
    :deep(p + ul),
    :deep(ol + p),
    :deep(ul + p) {
      margin-top: 6px;
    }

    :deep(ol),
    :deep(ul) {
      margin: 6px 0 0 18px;
      padding: 0;
    }

    :deep(li) {
      margin: 3px 0;
      padding-left: 2px;
    }

    :deep(strong) {
      color: var(--m-text);
      font-weight: 600;
    }

    :deep(code) {
      border: 1px solid var(--m-border);
      border-radius: var(--m-radius-sm);
      background: var(--m-surface-soft);
      padding: 1px 4px;
      color: var(--m-text);
      font-size: 12px;
    }

    :deep(pre) {
      max-width: 100%;
      margin: 6px 0 0;
      overflow: auto;
      border: 1px solid var(--m-border);
      border-radius: var(--m-radius-sm);
      background: var(--m-surface-soft);
      padding: 8px;
    }

    :deep(pre code) {
      border: 0;
      background: transparent;
      padding: 0;
      white-space: pre;
    }
  }

  .mango-ai-assistant__message--user .mango-ai-assistant__bubble {
    border-color: var(--m-primary-border);
    background: var(--m-primary-soft);
  }

  .mango-ai-assistant__confirm {
    display: grid;
    gap: 8px;
    margin-top: 10px;
    padding-top: 8px;
    border-top: 1px solid var(--m-border);

    div {
      display: grid;
      gap: 2px;
    }

    strong {
      color: var(--m-text);
      font-size: 13px;
    }

    span {
      color: var(--m-text-2);
      font-size: 12px;
    }

    pre {
      max-height: 180px;
      margin: 0;
      overflow: auto;
      color: var(--m-text);
      font-size: 12px;
      white-space: pre-wrap;
    }
  }

  .mango-ai-assistant__typing {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--m-text-2);
    font-size: 12px;
  }

  .mango-ai-assistant__footer {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    border-top: 1px solid var(--m-border);
    background: var(--m-surface);
  }

  .mango-ai-assistant__footer :deep(.arco-textarea-wrapper) {
    flex: 1;
  }

  .mango-ai-assistant__footer .mango-ai-assistant__send-button {
    flex-shrink: 0;
    width: 36px;
    height: 32px;
    padding: 0;
  }

  @media (max-width: 640px) {
    .mango-ai-assistant {
      right: 16px;
      bottom: 72px;
    }

    .mango-ai-assistant__panel {
      width: calc(100vw - 32px);
      height: min(680px, calc(100vh - 88px));
    }
  }
</style>
