<template>
  <BaseSidePanel
    v-if="!embeddedMode"
    :visible="visible"
    title="浏览器实时画面"
    width="72%"
    :show-confirm-button="false"
    @update:visible="updateVisible"
    @cancel="closePanel"
  >
    <template #header-actions>
      <a-space>
        <a-tag :color="statusColor">
          {{ statusText }}{{ controlling ? ' · 自动续租' : '' }}
        </a-tag>
        <a-radio-group
          v-if="!readOnlyMode"
          v-model="interactionMode"
          type="button"
          size="small"
          class="mango-live-stream__mode"
          :disabled="!connected || controlLoading"
        >
          <a-radio value="select" data-testid="qa-components-business-uilivestreampanel-radio-选择元素">选择元素</a-radio>
          <a-radio v-if="props.allowOperate" value="operate" data-testid="qa-components-business-uilivestreampanel-radio-操作浏览器">操作浏览器</a-radio>
          <a-radio v-if="props.allowRecord" value="record" data-testid="qa-components-business-uilivestreampanel-radio-录制步骤">录制步骤</a-radio>
        </a-radio-group>
        <a-space v-if="!readOnlyMode && props.allowOperate" size="mini" class="mango-live-stream__pages">
          <a-select
            v-model="activePageId"
            size="small"
            placeholder="浏览器页签"
            class="mango-live-stream__page-select"
            :disabled="!connected"
            @change="switchPage" data-testid="qa-components-business-uilivestreampanel-select-浏览器页签"
          >
            <a-option
              v-for="page in browserPages"
              :key="page.page_id"
              :value="page.page_id"
              :label="pageTitle(page)"
            />
          </a-select>
          <a-button size="small" :loading="pageLoading" :disabled="!connected" @click="refreshPages" data-testid="qa-components-business-uilivestreampanel-button-刷新页签">刷新页签</a-button>
          <a-button
            size="small"
            status="danger"
            :disabled="!connected || browserPages.length <= 1"
            @click="closeActivePage" data-testid="qa-components-business-uilivestreampanel-button-关闭页签"
          >
            关闭页签
          </a-button>
        </a-space>
        <a-button v-if="controlling" size="small" status="warning" @click="releaseControl" data-testid="qa-components-business-uilivestreampanel-button-结束控制">
          结束控制
        </a-button>
        <a-button size="small" :loading="connecting" @click="restart" data-testid="qa-components-business-uilivestreampanel-button-重新连接">
          <template #icon><icon-refresh /></template>
          重新连接
        </a-button>
      </a-space>
    </template>

    <div class="mango-live-stream">
      <div
        ref="viewportRef"
        class="mango-live-stream__viewport"
        :class="{ 'is-controlling': controlling, 'is-operating': interactionMode !== 'select', 'is-picking': interactionMode === 'select', 'is-recording': interactionMode === 'record' }"
        tabindex="0"
        @mousemove="onMouseMove"
        @mousedown="onMouseDown"
        @mouseup="onMouseUp"
        @contextmenu.prevent
        @wheel.prevent.stop="onWheel"
        @keydown.prevent="onKeyDown"
        @keyup.prevent="onKeyUp"
        @paste.prevent="onPaste"
      >
        <textarea
          ref="imeInputRef"
          class="mango-live-stream__ime-input"
          :style="imeProxyStyle"
          aria-label="直播画面输入法代理"
          autocomplete="off"
          autocapitalize="off"
          :spellcheck="false"
          @compositionstart.stop="onCompositionStart"
          @compositionend.stop="onCompositionEnd"
          @input.stop="onImeInput"
          @keydown.stop="onImeKeyDown"
          @keyup.stop="onImeKeyUp"
          @paste.stop data-testid="qa-components-business-uilivestreampanel-textarea-直播画面输入法代理"
        ></textarea>
        <img
          v-if="frameUrl"
          ref="frameRef"
          :src="frameUrl"
          alt="执行器浏览器实时画面"
          draggable="false"
        />
        <span
          v-for="effect in clickEffects"
          :key="effect.id"
          class="mango-live-stream__click-effect"
          :style="{ left: `${effect.x}px`, top: `${effect.y}px` }"
        ></span>
        <div v-if="!frameUrl" class="mango-live-stream__empty">
          <icon-desktop />
          <strong>{{ connecting ? '正在连接实时画面' : '等待执行器画面' }}</strong>
          <span>{{ errorMessage || '请先触发对应的 UI 执行或调试任务' }}</span>
        </div>
      </div>
    </div>
  </BaseSidePanel>
  <div v-else-if="visible" class="mango-live-stream mango-live-stream--embedded">
    <Teleport v-if="actionsTarget" :to="actionsTarget">
      <div class="mango-live-stream__teleported-actions">
        <a-space>
          <a-tag :color="statusColor">
            {{ statusText }}{{ controlling ? ' · 自动续租' : '' }}
          </a-tag>
          <a-radio-group v-if="!readOnlyMode" v-model="interactionMode" type="button" size="small" class="mango-live-stream__mode" :disabled="!connected || controlLoading">
            <a-radio value="select" data-testid="qa-components-business-uilivestreampanel-radio-选择元素-2">选择元素</a-radio>
            <a-radio v-if="props.allowOperate" value="operate" data-testid="qa-components-business-uilivestreampanel-radio-操作浏览器-2">操作浏览器</a-radio>
            <a-radio v-if="props.allowRecord" value="record" data-testid="qa-components-business-uilivestreampanel-radio-录制步骤-2">录制步骤</a-radio>
          </a-radio-group>
          <a-button v-if="controlling" size="small" status="warning" @click="releaseControl" data-testid="qa-components-business-uilivestreampanel-button-结束控制-2">
            结束控制
          </a-button>
          <a-button size="small" :loading="connecting" @click="restart" data-testid="qa-components-business-uilivestreampanel-button-重新连接-2">
            <template #icon><icon-refresh /></template>
            重新连接
          </a-button>
        </a-space>
      </div>
    </Teleport>
    <template v-else>
      <div class="mango-live-stream__embedded-head">
        <a-space>
          <a-tag :color="statusColor">
            {{ statusText }}{{ controlling ? ' · 自动续租' : '' }}
          </a-tag>
          <a-radio-group v-if="!readOnlyMode" v-model="interactionMode" type="button" size="small" class="mango-live-stream__mode" :disabled="!connected || controlLoading">
            <a-radio value="select" data-testid="qa-components-business-uilivestreampanel-radio-选择元素-3">选择元素</a-radio>
            <a-radio v-if="props.allowOperate" value="operate" data-testid="qa-components-business-uilivestreampanel-radio-操作浏览器-3">操作浏览器</a-radio>
            <a-radio v-if="props.allowRecord" value="record" data-testid="qa-components-business-uilivestreampanel-radio-录制步骤-3">录制步骤</a-radio>
          </a-radio-group>
          <a-space v-if="!readOnlyMode && props.allowOperate" size="mini" class="mango-live-stream__pages">
            <a-select
              v-model="activePageId"
              size="small"
              placeholder="浏览器页签"
              class="mango-live-stream__page-select"
              :disabled="!connected"
              @change="switchPage" data-testid="qa-components-business-uilivestreampanel-select-浏览器页签-2"
            >
              <a-option
                v-for="page in browserPages"
                :key="page.page_id"
                :value="page.page_id"
                :label="pageTitle(page)"
              />
            </a-select>
            <a-button size="small" :loading="pageLoading" :disabled="!connected" @click="refreshPages" data-testid="qa-components-business-uilivestreampanel-button-刷新页签-2">刷新页签</a-button>
            <a-button
              size="small"
              status="danger"
              :disabled="!connected || browserPages.length <= 1"
              @click="closeActivePage" data-testid="qa-components-business-uilivestreampanel-button-关闭页签-2"
            >
              关闭页签
            </a-button>
          </a-space>
          <a-button v-if="controlling" size="small" status="warning" @click="releaseControl" data-testid="qa-components-business-uilivestreampanel-button-结束控制-3">
            结束控制
          </a-button>
          <a-button size="small" :loading="connecting" @click="restart" data-testid="qa-components-business-uilivestreampanel-button-重新连接-3">
            <template #icon><icon-refresh /></template>
            重新连接
          </a-button>
        </a-space>
      </div>
    </template>
    <div
      ref="viewportRef"
      class="mango-live-stream__viewport"
      :class="{ 'is-controlling': controlling, 'is-operating': interactionMode !== 'select', 'is-picking': interactionMode === 'select', 'is-recording': interactionMode === 'record' }"
      tabindex="0"
      @mousemove="onMouseMove"
      @mousedown="onMouseDown"
      @mouseup="onMouseUp"
      @contextmenu.prevent
      @wheel.prevent.stop="onWheel"
      @keydown.prevent="onKeyDown"
      @keyup.prevent="onKeyUp"
      @paste.prevent="onPaste"
    >
      <textarea
        ref="imeInputRef"
        class="mango-live-stream__ime-input"
        :style="imeProxyStyle"
        aria-label="直播画面输入法代理"
        autocomplete="off"
        autocapitalize="off"
        :spellcheck="false"
        @compositionstart.stop="onCompositionStart"
        @compositionend.stop="onCompositionEnd"
        @input.stop="onImeInput"
        @keydown.stop="onImeKeyDown"
        @keyup.stop="onImeKeyUp"
        @paste.stop data-testid="qa-components-business-uilivestreampanel-textarea-直播画面输入法代理-2"
      ></textarea>
      <img
        v-if="frameUrl"
        ref="frameRef"
        :src="frameUrl"
        alt="执行器浏览器实时画面"
        draggable="false"
      />
      <span
        v-for="effect in clickEffects"
        :key="effect.id"
        class="mango-live-stream__click-effect"
        :style="{ left: `${effect.x}px`, top: `${effect.y}px` }"
      ></span>
      <div v-if="!frameUrl" class="mango-live-stream__empty">
        <icon-desktop />
        <strong>{{ connecting ? '正在连接实时画面' : '等待执行器画面' }}</strong>
        <span>{{ errorMessage || '请先触发对应的 UI 执行或调试任务' }}</span>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { IconDesktop, IconRefresh } from '@arco-design/web-vue/es/icon'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import {
    closeUiLiveStreamSession,
    createUiLiveStreamSession,
    startUiLiveStreamSession,
  } from '@/api/uitest/live-stream'
  import useUserStore from '@/store/modules/user'

  const props = defineProps<{
    visible: boolean
    executionType:
      | 'ui_case'
      | 'page_step_debug'
      | 'element_check'
      | 'element_workspace'
      | 'page_step_workspace'
    executionId: string | number
    resourceId?: string | number
    readOnly?: boolean
    actuatorUsername?: string
    embedded?: boolean
    actionsTarget?: string
    allowOperate?: boolean
    allowRecord?: boolean
  }>()
  const emit = defineEmits<{
    (event: 'update:visible', value: boolean): void
    (event: 'command-result', value: any): void
    (event: 'stream-ready'): void
    (event: 'stream-connection', value: boolean): void
    (event: 'reconnect-workspace'): void
    (event: 'workspace-expired', executionId: string | number): void
    (event: 'interaction-mode', value: 'select' | 'operate' | 'record'): void
  }>()

  const socket = ref<WebSocket | null>(null)
  const frameRef = ref<HTMLImageElement | null>(null)
  const viewportRef = ref<HTMLElement | null>(null)
  const imeInputRef = ref<HTMLTextAreaElement | null>(null)
  const imeProxyStyle = ref<Record<string, string>>({ left: '50%', top: '50%' })
  const frameUrl = ref('')
  const streamId = ref('')
  const connecting = ref(false)
  const connected = ref(false)
  const controlling = ref(false)
  const controlLoading = ref(false)
  const controlSuspended = ref(false)
  type InteractionMode = 'select' | 'operate' | 'record'
  const interactionMode = ref<InteractionMode>('select')
  const browserPages = ref<any[]>([])
  const activePageId = ref('')
  const pageLoading = ref(false)
  const errorMessage = ref('')
  const lastFrameAt = ref('')
  const reconnectTimer = ref<number | null>(null)
  const renewTimer = ref<number | null>(null)
  const pageRequestTimer = ref<number | null>(null)
  const publisherWaitTimer = ref<number | null>(null)
  const publisherRestartTimer = ref<number | null>(null)
  const publisherRestartCount = ref(0)
  const workspaceExpired = ref(false)
  const readyTicket = ref('')
  const closedByUser = ref(false)
  const streamCompleted = ref(false)
  const clickEffects = ref<Array<{ id: number; x: number; y: number }>>([])
  let reconnectAttempt = 0
  let controlSequence = 0
  let receivedFrameCount = 0
  let controlReleasePromise: Promise<boolean> | null = null
  let controlReleaseResolver: ((released: boolean) => void) | null = null
  let controlReleaseTimer: number | null = null
  let controlAcquirePromise: Promise<boolean> | null = null
  let controlAcquireResolver: ((acquired: boolean) => void) | null = null
  let controlAcquireTimer: number | null = null
  const pendingControlEvents = new Map<number, string>()
  const queuedRecordEvents: any[] = []
  let lastMouseMoveAt = 0
  let lastPointer = { x: 0.5, y: 0.5 }
  let wheelDeltaX = 0
  let wheelDeltaY = 0
  let wheelPointer = { x: 0.5, y: 0.5 }
  let wheelFlushTimer: number | null = null
  let clickEffectId = 0
  let recordedTextBuffer = ''
  let recordedTextTimer: number | null = null
  let recordedClickTimer: number | null = null
  let pendingRecordedClick: any = null
  let imeComposing = false
  let skipNextImeInput = false
  let pendingMouseDown:
    | {
        button: string
        pointer: { x: number; y: number }
        clientX: number
        clientY: number
      }
    | null = null
  let mouseDragging = false

  const readOnlyMode = computed(() => Boolean(props.readOnly))
  const embeddedMode = computed(() => Boolean(props.embedded))
  const actionsTarget = computed(() => props.actionsTarget || '')
  const workspaceExecutionMode = computed(
    () => props.executionType === 'element_workspace' || props.executionType === 'page_step_workspace'
  )
  const statusText = computed(() => {
    if (controlling.value) {
      if (interactionMode.value === 'record') return '录制步骤'
      return interactionMode.value === 'operate' ? '操作浏览器' : '选择元素'
    }
    if (connected.value && frameUrl.value) return '画面传输中'
    if (connected.value) return '等待执行器推流'
    if (connecting.value) return '连接中'
    if (streamCompleted.value) return '执行完成'
    return errorMessage.value ? '连接异常' : '未连接'
  })
  const statusColor = computed(() => {
    if (controlling.value) return interactionMode.value === 'record' ? 'purple' : interactionMode.value === 'operate' ? 'orange' : 'blue'
    if (connected.value) return 'green'
    if (connecting.value) return 'blue'
    if (streamCompleted.value) return 'green'
    return errorMessage.value ? 'red' : 'gray'
  })
  const operateMode = computed({
    get: () => interactionMode.value !== 'select',
    set: (value: boolean) => { interactionMode.value = value ? 'operate' : 'select' },
  })
  const operateModeValue = computed(() => operateMode.value)
  const interactionModeValue = computed(() => interactionMode.value)
  const activePageIdValue = computed(() => activePageId.value)
  const browserPagesValue = computed(() => browserPages.value)
  const pageLoadingValue = computed(() => pageLoading.value)

  function liveLog(message: string, extra: Record<string, any> = {}) {
    console.info('[UI实时画面]', message, {
      executionType: props.executionType,
      executionId: props.executionId,
      streamId: streamId.value || '-',
      visible: props.visible,
      connected: connected.value,
      connecting: connecting.value,
      ...extra,
    })
  }

  function realtimeWebSocketUrl(path: string, token: string) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host =
      window.location.port === '5173' ? `${window.location.hostname}:8011` : window.location.host
    return `${protocol}//${host}${path}?token=${encodeURIComponent(token)}`
  }

  async function connect() {
    if (!props.executionId || connecting.value) return
    connecting.value = true
    errorMessage.value = ''
    streamCompleted.value = false
    closedByUser.value = false
    try {
      liveLog('开始创建直播会话')
      const response = await createUiLiveStreamSession(props.executionType, props.executionId, {
        resourceId: props.resourceId,
        readOnly: props.readOnly,
        actuatorUsername: props.actuatorUsername,
      })
      const session = response.data || {}
      streamId.value = session.stream_id
      liveLog('直播会话创建成功，开始订阅', { subscribeUrl: session.subscribe_url })
      const userStore = useUserStore()
      const ws = new WebSocket(realtimeWebSocketUrl(session.subscribe_url, userStore.token))
      ws.binaryType = 'arraybuffer'
      socket.value = ws
      ws.onopen = () => {
        liveLog('订阅 WebSocket 已连接')
        workspaceExpired.value = false
        connected.value = true
        emit('stream-connection', true)
        connecting.value = false
        reconnectAttempt = 0
      }
      ws.onmessage = handleMessage
      ws.onerror = () => {
        liveLog('订阅 WebSocket 异常')
        errorMessage.value = '实时画面连接异常'
      }
      ws.onclose = (event) => {
        liveLog('订阅 WebSocket 已关闭', {
          closedByUser: closedByUser.value,
          code: (event as CloseEvent)?.code,
          reason: (event as CloseEvent)?.reason,
        })
        if (socket.value !== ws) return
        connected.value = false
        emit('stream-connection', false)
        controlling.value = false
        finishControlAcquire(false)
        stopRenew()
        if (!closedByUser.value && props.visible) scheduleReconnect()
      }
    } catch (error: any) {
      connecting.value = false
      errorMessage.value = normalizeErrorMessage(error, '创建实时画面会话失败')
      liveLog('创建直播会话失败', { error: errorMessage.value })
      if (workspaceExecutionMode.value && isWorkspaceExpiredMessage(errorMessage.value)) {
        workspaceExpired.value = true
        await disconnect(false)
        emit('workspace-expired', props.executionId)
        return
      }
      if (!closedByUser.value && props.visible) scheduleReconnect()
    }
  }

  async function handleMessage(event: MessageEvent) {
    if (event.data instanceof ArrayBuffer) {
      receivedFrameCount += 1
      if (receivedFrameCount === 1 || receivedFrameCount % 100 === 0) {
        liveLog('收到二进制帧', { bytes: event.data.byteLength, frameCount: receivedFrameCount })
      }
      replaceFrame(new Blob([event.data], { type: 'image/jpeg' }))
      return
    }
    if (event.data instanceof Blob) {
      receivedFrameCount += 1
      if (receivedFrameCount === 1 || receivedFrameCount % 100 === 0) {
        liveLog('收到 Blob 帧', { bytes: event.data.size, frameCount: receivedFrameCount })
      }
      replaceFrame(event.data)
      return
    }
    let message: any
    try {
      message = JSON.parse(event.data)
    } catch (_) {
      return
    }
    if (message.type === 'subscriber_ready') {
      liveLog('订阅端 ready，通知执行器开始推流')
      readyTicket.value = message.ready_ticket || ''
      publisherRestartCount.value = 0
      try {
        await startUiLiveStreamSession(streamId.value, readyTicket.value)
        startPublisherWaitTimeout()
      } catch (error: any) {
        errorMessage.value = normalizeErrorMessage(error, '启动实时画面失败')
        if (workspaceExecutionMode.value && isWorkspaceExpiredMessage(errorMessage.value)) {
          workspaceExpired.value = true
          await disconnect(false)
          emit('workspace-expired', props.executionId)
          return
        }
        Message.error(errorMessage.value)
      }
    } else if (message.type === 'control_granted') {
      controlLoading.value = false
      if (controlSuspended.value) {
        controlling.value = false
        finishControlAcquire(false)
        stopRenew()
        sendJson({ type: 'control_release' })
        return
      }
      controlling.value = true
      finishControlAcquire(true)
      startRenew(Number(message.lease_seconds || 30))
      refreshPages()
      scheduleWheelFlush()
      await nextTick()
      frameRef.value?.focus()
    } else if (message.type === 'control_denied' || message.type === 'error') {
      controlLoading.value = false
      const deniedMessage = String(message.message || '')
      if (workspaceExecutionMode.value && isWorkspaceExpiredMessage(deniedMessage)) {
        await disconnect(false)
        emit('workspace-expired', props.executionId)
        return
      }
      if (deniedMessage.includes('远程控制事件')) {
        finishPageRequest('页签管理暂不可用，请确认实时服务和执行器已更新并重启')
        return
      }
      if (message.type === 'control_denied') {
        controlling.value = false
        finishControlAcquire(false)
        clearWheelQueue()
        stopRenew()
        if (controlSuspended.value) finishControlRelease(true)
      }
      finishPageRequest()
      errorMessage.value = message.message || '实时画面服务异常'
      Message.error(errorMessage.value)
    } else if (message.type === 'control_stopped') {
      controlling.value = false
      finishControlAcquire(false)
      clearWheelQueue()
      stopRenew()
      finishPageRequest()
      finishControlRelease(true)
      if (message.reason === 'idle_takeover') {
        Message.info('控制权已由其他观看页面接管，当前页面仍可继续观看直播')
      }
    } else if (message.type === 'control_ack') {
      const sequence = Number(message.sequence || 0)
      const eventType = pendingControlEvents.get(sequence)
      const pagePayload = resolvePagePayload(message)
      const commandPayload = resolveCommandPayload(message)
      pendingControlEvents.delete(sequence)
      flushQueuedRecordEvent()
      scheduleWheelFlush()
      if (message.success === false) {
        if (!['list_pages', 'switch_page', 'close_page'].includes(eventType || '')) {
          emit('command-result', { ...message, data: commandPayload || {} })
        }
        if (['list_pages', 'switch_page', 'close_page'].includes(eventType || '')) {
          browserPages.value = []
          activePageId.value = ''
          finishPageRequest('页签管理暂不可用，请确认实时服务和执行器已更新并重启')
          return
        }
        finishPageRequest()
        Message.error(message.message || `远程控制事件 ${message.sequence || '-'} 执行失败`)
      } else if (commandPayload) {
        if (pagePayload) syncPages(pagePayload)
        else if (['list_pages', 'switch_page', 'close_page'].includes(eventType || '')) finishPageRequest()
        emit('command-result', { ...message, data: commandPayload })
      } else if (['list_pages', 'switch_page', 'close_page'].includes(eventType || '')) {
        finishPageRequest()
      }
    } else if (message.type === 'stream_status') {
      liveLog('收到推流状态', { data: message.data || {} })
      if (message.data?.status === 'streaming') clearPublisherWaitTimeout()
      if (message.data?.status === 'completed') {
        streamCompleted.value = true
        closedByUser.value = true
        errorMessage.value = ''
        clearPublisherWaitTimeout()
        if (publisherRestartTimer.value) window.clearTimeout(publisherRestartTimer.value)
        publisherRestartTimer.value = null
        finishPageRequest()
        return
      }
      if (['error', 'disconnected'].includes(message.data?.status)) {
        if (streamCompleted.value) return
        errorMessage.value = message.data.message || '执行器推流异常'
        finishPageRequest()
        schedulePublisherRestart()
      }
    }
  }

  function replaceFrame(blob: Blob) {
    clearPublisherWaitTimeout()
    publisherRestartCount.value = 0
    const isFirstFrame = !frameUrl.value
    if (isFirstFrame) {
      liveLog('收到第一帧画面')
      emit('stream-ready')
    }
    const previous = frameUrl.value
    frameUrl.value = URL.createObjectURL(blob)
    lastFrameAt.value = new Date().toLocaleTimeString()
    if (previous) URL.revokeObjectURL(previous)
  }

  function clearFrame() {
    if (frameUrl.value) URL.revokeObjectURL(frameUrl.value)
    frameUrl.value = ''
    lastFrameAt.value = ''
  }

  async function requestControl() {
    return ensureControl()
  }

  async function ensureControl() {
    if (readOnlyMode.value || controlSuspended.value || controlling.value) {
      return controlling.value
    }
    if (controlAcquirePromise) return controlAcquirePromise
    if (!streamId.value || !socket.value) return false
    controlLoading.value = true
    controlAcquirePromise = new Promise<boolean>((resolve) => {
      controlAcquireResolver = resolve
      controlAcquireTimer = window.setTimeout(() => finishControlAcquire(false), 5000)
      sendJson({ type: 'control_request' })
    })
    return controlAcquirePromise
  }

  function finishControlAcquire(acquired: boolean) {
    if (controlAcquireTimer) window.clearTimeout(controlAcquireTimer)
    controlAcquireTimer = null
    controlLoading.value = false
    const resolve = controlAcquireResolver
    controlAcquireResolver = null
    controlAcquirePromise = null
    resolve?.(acquired)
  }

  function releaseControl() {
    sendJson({ type: 'control_release' })
    controlling.value = false
    controlLoading.value = false
    clearWheelQueue()
    stopRenew()
  }

  function finishControlRelease(released: boolean) {
    if (controlReleaseTimer) window.clearTimeout(controlReleaseTimer)
    controlReleaseTimer = null
    const resolve = controlReleaseResolver
    controlReleaseResolver = null
    controlReleasePromise = null
    resolve?.(released)
  }

  async function suspendControlForAutomation() {
    controlSuspended.value = true
    stopRenew()
    if (
      readOnlyMode.value ||
      !connected.value ||
      !socket.value ||
      socket.value.readyState !== WebSocket.OPEN ||
      (!controlling.value && !controlLoading.value)
    ) {
      controlling.value = false
      controlLoading.value = false
      return true
    }
    if (controlReleasePromise) return controlReleasePromise
    controlReleasePromise = new Promise<boolean>((resolve) => {
      controlReleaseResolver = resolve
      controlReleaseTimer = window.setTimeout(() => finishControlRelease(false), 5000)
      sendJson({ type: 'control_release' })
      controlling.value = false
      controlLoading.value = false
    })
    return controlReleasePromise
  }

  function resumeControlAfterAutomation(requestControl = true) {
    controlSuspended.value = false
    if (requestControl && connected.value && frameUrl.value && !readOnlyMode.value) ensureControl()
  }

  function startRenew(leaseSeconds: number) {
    stopRenew()
    renewTimer.value = window.setInterval(() => {
      if (controlling.value) sendJson({ type: 'control_renew' })
    }, Math.max(5000, (leaseSeconds - 10) * 1000))
  }

  function stopRenew() {
    if (renewTimer.value) window.clearInterval(renewTimer.value)
    renewTimer.value = null
  }

  function startPageRequestTimeout() {
    clearPageRequestTimeout()
    pageRequestTimer.value = window.setTimeout(() => {
      pageRequestTimer.value = null
      if (!pageLoading.value) return
      pendingControlEvents.clear()
      scheduleWheelFlush()
      finishPageRequest('页签列表刷新超时，请确认实时服务和执行器已更新并重启')
    }, 8000)
  }

  function clearPageRequestTimeout() {
    if (pageRequestTimer.value) window.clearTimeout(pageRequestTimer.value)
    pageRequestTimer.value = null
  }

  function finishPageRequest(message = '') {
    clearPageRequestTimeout()
    pageLoading.value = false
    if (message) errorMessage.value = message
  }

  function startPublisherWaitTimeout() {
    clearPublisherWaitTimeout()
    publisherWaitTimer.value = window.setTimeout(() => {
      publisherWaitTimer.value = null
      if (!frameUrl.value) {
        errorMessage.value = '执行器正在打开浏览器并准备推流，请稍候'
        if (workspaceExecutionMode.value) {
          liveLog('等待第一帧超时，保留订阅端并重发推流启动命令')
          retryPublisherStart()
          return
        }
        liveLog('等待第一帧超时，尝试重启推流')
        schedulePublisherRestart()
      }
    }, workspaceExecutionMode.value ? 30000 : 35000)
  }

  function clearPublisherWaitTimeout() {
    if (publisherWaitTimer.value) window.clearTimeout(publisherWaitTimer.value)
    publisherWaitTimer.value = null
  }

  function sendJson(data: any) {
    if (socket.value?.readyState === WebSocket.OPEN) socket.value.send(JSON.stringify(data))
  }

  function sendControl(data: any) {
    if (controlling.value) {
      const eventType = data?.event_type || ''
      if (
        pendingControlEvents.size > 0 &&
        ['mouse_move', 'mouse_wheel'].includes(eventType)
      ) {
        return
      }
      if (pendingControlEvents.size > 0 && ['record_action', 'record_poll'].includes(eventType)) {
        if (eventType === 'record_action') queuedRecordEvents.push(data)
        return
      }
      controlSequence += 1
      pendingControlEvents.set(controlSequence, eventType)
      sendJson({ type: 'control_event', data: { ...data, sequence: controlSequence } })
    }
  }

  function flushQueuedRecordEvent() {
    if (pendingControlEvents.size || !queuedRecordEvents.length) return
    const next = queuedRecordEvents.shift()
    if (next) sendControl(next)
  }

  function scheduleRecordedText(text: string) {
    recordedTextBuffer += text
    if (recordedTextTimer) window.clearTimeout(recordedTextTimer)
    recordedTextTimer = window.setTimeout(flushRecordedText, 320)
  }

  function flushRecordedText() {
    if (recordedTextTimer) window.clearTimeout(recordedTextTimer)
    recordedTextTimer = null
    if (!recordedTextBuffer) return
    const text = recordedTextBuffer
    recordedTextBuffer = ''
    sendControl({ event_type: 'record_action', action: 'input', text })
  }

  function flushRecordedClick() {
    if (recordedClickTimer) window.clearTimeout(recordedClickTimer)
    recordedClickTimer = null
    if (!pendingRecordedClick) return
    sendControl(pendingRecordedClick)
    pendingRecordedClick = null
  }

  function normalizeWheelDelta(event: WheelEvent) {
    const lineHeight = 32
    const pageHeight = Math.max(1, frameRef.value?.clientHeight || 720)
    const factor =
      event.deltaMode === WheelEvent.DOM_DELTA_LINE
        ? lineHeight
        : event.deltaMode === WheelEvent.DOM_DELTA_PAGE
          ? pageHeight
          : 1
    return {
      deltaX: event.deltaX * factor,
      deltaY: event.deltaY * factor,
    }
  }

  function clearWheelQueue() {
    if (wheelFlushTimer) window.clearTimeout(wheelFlushTimer)
    wheelFlushTimer = null
    wheelDeltaX = 0
    wheelDeltaY = 0
  }

  function scheduleWheelFlush(delay = 24) {
    if (wheelFlushTimer || (!wheelDeltaX && !wheelDeltaY)) return
    wheelFlushTimer = window.setTimeout(() => {
      wheelFlushTimer = null
      flushWheel()
    }, delay)
  }

  function flushWheel() {
    if (!wheelDeltaX && !wheelDeltaY) return
    if (!controlling.value || pendingControlEvents.size > 0) return
    const deltaX = Math.max(-5000, Math.min(5000, wheelDeltaX))
    const deltaY = Math.max(-5000, Math.min(5000, wheelDeltaY))
    wheelDeltaX -= deltaX
    wheelDeltaY -= deltaY
    sendControl(interactionMode.value === 'record'
      ? {
          event_type: 'record_action',
          action: 'scroll',
          delta_x: deltaX,
          delta_y: deltaY,
          ...wheelPointer,
        }
      : {
          event_type: 'mouse_wheel',
          delta_x: deltaX,
          delta_y: deltaY,
          ...wheelPointer,
        })
  }

  async function refreshPages() {
    if (!connected.value || readOnlyMode.value) return
    pageLoading.value = true
    startPageRequestTimeout()
    const ok = await ensureControl()
    if (ok) sendControl({ event_type: 'list_pages' })
    else finishPageRequest()
  }

  async function switchPage(pageId: string | number) {
    if (!pageId || readOnlyMode.value) return
    pageLoading.value = true
    startPageRequestTimeout()
    const ok = await ensureControl()
    if (ok) sendControl({ event_type: 'switch_page', page_id: pageId })
    else finishPageRequest()
  }

  function setOperateMode(value: boolean) {
    interactionMode.value = value ? 'operate' : 'select'
    if (value) ensureControl()
  }

  function setInteractionMode(value: InteractionMode) {
    interactionMode.value = value
    if (value !== 'select') ensureControl()
  }

  async function closeActivePage() {
    if (!activePageId.value || browserPages.value.length <= 1 || readOnlyMode.value) return
    pageLoading.value = true
    startPageRequestTimeout()
    const ok = await ensureControl()
    if (ok) sendControl({ event_type: 'close_page', page_id: activePageId.value })
    else finishPageRequest()
  }

  function resolvePagePayload(message: any) {
    const candidates = [
      message?.data,
      message?.data?.data,
      message?.data?.result,
      message?.result,
      message?.payload,
    ]
    return candidates.find((item) => Array.isArray(item?.pages)) || null
  }

  function resolveCommandPayload(message: any) {
    const candidates = [
      message?.data,
      message?.data?.data,
      message?.data?.result,
      message?.result,
      message?.payload,
    ]
    return candidates.find((item) => item && typeof item === 'object') || null
  }

  function normalizePage(item: any, index: number) {
    const pageId = String(item?.page_id ?? item?.pageId ?? item?.id ?? item?.guid ?? index)
    return {
      ...item,
      page_id: pageId,
      index: Number.isFinite(Number(item?.index)) ? Number(item.index) : index,
      title: item?.title || '',
      url: item?.url || '',
      active: Boolean(item?.active || item?.current),
    }
  }

  function syncPages(data: any) {
    if (!Array.isArray(data?.pages)) {
      finishPageRequest()
      return
    }
    const pages = data.pages.map(normalizePage)
    browserPages.value = pages
    activePageId.value = pages.find((page: any) => page.active)?.page_id || pages[0]?.page_id || ''
    finishPageRequest()
  }

  function pageTitle(page: any) {
    const title = page?.title || page?.url || `页面 ${Number(page?.index || 0) + 1}`
    return `${page?.active ? '当前 / ' : ''}${title}`
  }

  async function sendWorkspaceCommand(eventType: string, data: Record<string, any> = {}) {
    if (readOnlyMode.value) return false
    if (!controlling.value) {
      const acquired = await ensureControl()
      if (!acquired) return false
    }
    const pointerData = eventType === 'pick_element' ? { ...lastPointer, ...data } : data
    sendControl({ event_type: eventType, ...pointerData })
    return true
  }

  function pointer(event: MouseEvent) {
    const target = frameRef.value
    if (!target) return null
    const rect = target.getBoundingClientRect()
    if (
      event.clientX < rect.left ||
      event.clientX > rect.right ||
      event.clientY < rect.top ||
      event.clientY > rect.bottom
    ) {
      return null
    }
    return {
      x: Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)),
      y: Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height)),
    }
  }

  function buttonName(button: number) {
    return button === 2 ? 'right' : button === 1 ? 'middle' : 'left'
  }
  function onMouseMove(event: MouseEvent) {
    if (readOnlyMode.value) return
    const currentPointer = pointer(event)
    if (!currentPointer) return
    lastPointer = currentPointer
    if (interactionMode.value === 'select') return
    const now = performance.now()
    if (now - lastMouseMoveAt < 34) return
    lastMouseMoveAt = now
    if (pendingMouseDown) {
      const distance = Math.hypot(
        event.clientX - pendingMouseDown.clientX,
        event.clientY - pendingMouseDown.clientY
      )
      if (!mouseDragging && distance > 4) {
        mouseDragging = true
        if (interactionMode.value === 'operate') sendControl({
          event_type: 'mouse_down',
          button: pendingMouseDown.button,
          ...pendingMouseDown.pointer,
        })
      }
    }
    if (mouseDragging && interactionMode.value === 'operate') sendControl({ event_type: 'mouse_move', ...currentPointer })
  }
  async function onMouseDown(event: MouseEvent) {
    if (readOnlyMode.value) return
    if (interactionMode.value === 'record') flushRecordedText()
    viewportRef.value?.focus()
    const currentPointer = pointer(event)
    if (!currentPointer) return
    await ensureControl()
    lastPointer = currentPointer
    pendingMouseDown = {
      button: buttonName(event.button),
      pointer: currentPointer,
      clientX: event.clientX,
      clientY: event.clientY,
    }
    mouseDragging = false
    showClickEffect(event)
    positionImeProxy(event)
  }
  async function onMouseUp(event: MouseEvent) {
    if (readOnlyMode.value) return
    const currentPointer = pointer(event)
    if (!currentPointer) {
      pendingMouseDown = null
      mouseDragging = false
      return
    }
    lastPointer = currentPointer
    if (interactionMode.value === 'select') {
      const ok = await ensureControl()
      if (ok) sendControl({ event_type: 'pick_element', ...currentPointer })
      pendingMouseDown = null
      mouseDragging = false
      return
    }
    const button = pendingMouseDown?.button || buttonName(event.button)
    if (interactionMode.value === 'record') {
      const recordEvent = {
        event_type: 'record_action',
        action: mouseDragging
          ? 'drag'
          : button === 'right'
            ? 'right_click'
            : event.detail >= 2
              ? 'double_click'
              : 'click',
        ...pendingMouseDown?.pointer,
        ...(mouseDragging ? { to_x: currentPointer.x, to_y: currentPointer.y } : {}),
      }
      if (mouseDragging || button === 'right') {
        flushRecordedClick()
        sendControl(recordEvent)
      } else if (event.detail >= 2) {
        if (recordedClickTimer) window.clearTimeout(recordedClickTimer)
        recordedClickTimer = null
        pendingRecordedClick = null
        sendControl(recordEvent)
      } else {
        pendingRecordedClick = recordEvent
        if (recordedClickTimer) window.clearTimeout(recordedClickTimer)
        recordedClickTimer = window.setTimeout(flushRecordedClick, 220)
      }
    } else if (mouseDragging) {
      sendControl({ event_type: 'mouse_up', button, ...currentPointer })
    } else {
      sendControl({ event_type: 'mouse_click', button, click_count: 1, ...currentPointer })
    }
    pendingMouseDown = null
    mouseDragging = false
    focusImeProxy()
  }
  async function onWheel(event: WheelEvent) {
    if (readOnlyMode.value) return
    if (interactionMode.value === 'select') return
    const currentPointer = pointer(event)
    if (!currentPointer) return
    lastPointer = currentPointer
    wheelPointer = currentPointer
    const delta = normalizeWheelDelta(event)
    wheelDeltaX += delta.deltaX
    wheelDeltaY += delta.deltaY
    if (!controlling.value) await ensureControl()
    scheduleWheelFlush()
  }
  function onKeyDown(event: KeyboardEvent) {
    if (readOnlyMode.value) return
    if (interactionMode.value === 'select') return
    if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
      if (interactionMode.value === 'record') scheduleRecordedText(event.key)
      else sendControl({ event_type: 'text_input', text: event.key })
    } else {
      if (interactionMode.value === 'record') flushRecordedText()
      sendControl(interactionMode.value === 'record'
        ? { event_type: 'record_action', action: 'key_press', key: playwrightKey(event) }
        : { event_type: 'keyboard_down', key: playwrightKey(event) })
    }
  }
  function positionImeProxy(event: MouseEvent) {
    const target = viewportRef.value
    if (!target) return
    const rect = target.getBoundingClientRect()
    imeProxyStyle.value = {
      left: `${Math.max(0, Math.min(rect.width, event.clientX - rect.left))}px`,
      top: `${Math.max(0, Math.min(rect.height, event.clientY - rect.top))}px`,
    }
  }
  function focusImeProxy() {
    if (readOnlyMode.value || interactionMode.value === 'select') return
    window.setTimeout(() => imeInputRef.value?.focus({ preventScroll: true }), 0)
  }
  function commitImeText(text: string) {
    if (!text || readOnlyMode.value || interactionMode.value === 'select') return
    if (interactionMode.value === 'record') scheduleRecordedText(text)
    else sendControl({ event_type: 'text_input', text })
  }
  function clearImeInput(target?: HTMLTextAreaElement | null) {
    const input = target || imeInputRef.value
    if (input) input.value = ''
  }
  function onCompositionStart() {
    imeComposing = true
    skipNextImeInput = false
  }
  function onCompositionEnd(event: CompositionEvent) {
    imeComposing = false
    const target = event.target as HTMLTextAreaElement | null
    const text = event.data || target?.value || ''
    commitImeText(text)
    skipNextImeInput = true
    window.setTimeout(() => {
      skipNextImeInput = false
      clearImeInput(target)
    }, 0)
  }
  function onImeInput(event: Event) {
    const target = event.target as HTMLTextAreaElement | null
    if (imeComposing || (event as InputEvent).isComposing) return
    if (skipNextImeInput) {
      skipNextImeInput = false
      clearImeInput(target)
      return
    }
    commitImeText(target?.value || '')
    clearImeInput(target)
  }
  function isCompositionKey(event: KeyboardEvent) {
    return imeComposing || event.isComposing || ['Process', 'Unidentified', 'Dead'].includes(event.key)
  }
  function isLocalPasteShortcut(event: KeyboardEvent) {
    return (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'v'
  }
  function onImeKeyDown(event: KeyboardEvent) {
    if (isCompositionKey(event) || isLocalPasteShortcut(event)) return
    if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) return
    event.preventDefault()
    onKeyDown(event)
  }
  function onImeKeyUp(event: KeyboardEvent) {
    if (isCompositionKey(event) || isLocalPasteShortcut(event)) return
    if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) return
    event.preventDefault()
    onKeyUp(event)
  }
  function onKeyUp(event: KeyboardEvent) {
    if (readOnlyMode.value) return
    if (interactionMode.value === 'select') return
    if (interactionMode.value === 'record') return
    if (event.key.length !== 1 || event.ctrlKey || event.metaKey || event.altKey) {
      sendControl({ event_type: 'keyboard_up', key: playwrightKey(event) })
    }
  }
  function onPaste(event: ClipboardEvent) {
    if (readOnlyMode.value) return
    if (interactionMode.value === 'select') return
    const text = event.clipboardData?.getData('text') || ''
    if (interactionMode.value === 'record') scheduleRecordedText(text)
    else sendControl({ event_type: 'text_input', text })
  }

  function showClickEffect(event: MouseEvent) {
    const target = viewportRef.value
    if (!target) return
    const rect = target.getBoundingClientRect()
    const effect = {
      id: ++clickEffectId,
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
    }
    clickEffects.value.push(effect)
    window.setTimeout(() => {
      clickEffects.value = clickEffects.value.filter((item) => item.id !== effect.id)
    }, 460)
  }

  function playwrightKey(event: KeyboardEvent) {
    const keyMap: Record<string, string> = {
      ' ': 'Space',
      Meta: 'Meta',
      Control: 'Control',
      Alt: 'Alt',
      Shift: 'Shift',
      Esc: 'Escape',
    }
    return keyMap[event.key] || event.key
  }

  function normalizeErrorMessage(error: any, fallback: string) {
    return (
      error?.msg ||
      error?.response?.data?.msg ||
      error?.data?.msg ||
      error?.message ||
      fallback
    )
  }

  function isWorkspaceExpiredMessage(message: string) {
    return /实时工作区不存在|实时工作区.*过期|执行器连接已变化/.test(String(message || ''))
  }

  function scheduleReconnect() {
    if (reconnectTimer.value) return
    const delay = Math.min(10000, 1000 * 2 ** Math.min(reconnectAttempt++, 3))
    reconnectTimer.value = window.setTimeout(() => {
      reconnectTimer.value = null
      connect()
    }, delay)
  }

  function schedulePublisherRestart() {
    if (publisherRestartTimer.value || closedByUser.value || !props.visible) return
    publisherRestartCount.value += 1
    if (workspaceExecutionMode.value && publisherRestartCount.value >= 3) {
      liveLog('连续无帧，停止自动重建实时工作区', {
        restartCount: publisherRestartCount.value,
      })
      errorMessage.value = '实时画面连接已中断，请点击“重新连接”'
      return
    }
    publisherRestartTimer.value = window.setTimeout(() => {
      publisherRestartTimer.value = null
      if (props.visible && !closedByUser.value) restart()
    }, 2000)
  }

  async function retryPublisherStart() {
    if (publisherRestartTimer.value || closedByUser.value || !props.visible) return
    publisherRestartCount.value += 1
    if (!streamId.value || !readyTicket.value) {
      schedulePublisherRestart()
      return
    }
    if (workspaceExecutionMode.value && publisherRestartCount.value >= 3) {
      liveLog('连续无帧，停止自动重建实时工作区', {
        restartCount: publisherRestartCount.value,
      })
      errorMessage.value = '实时画面连接已中断，请点击“重新连接”'
      return
    }
    try {
      await startUiLiveStreamSession(streamId.value, readyTicket.value)
      startPublisherWaitTimeout()
    } catch (error: any) {
      errorMessage.value = normalizeErrorMessage(error, '重新启动推流失败')
      schedulePublisherRestart()
    }
  }

  async function disconnect(closeRemote = true) {
    closedByUser.value = true
    if (reconnectTimer.value) window.clearTimeout(reconnectTimer.value)
    reconnectTimer.value = null
    if (publisherRestartTimer.value) window.clearTimeout(publisherRestartTimer.value)
    publisherRestartTimer.value = null
    clearPublisherWaitTimeout()
    clearPageRequestTimeout()
    flushRecordedText()
    flushRecordedClick()
    pendingControlEvents.clear()
    queuedRecordEvents.splice(0)
    clearWheelQueue()
    stopRenew()
    finishControlAcquire(false)
    finishControlRelease(false)
    releaseControl()
    const currentStreamId = streamId.value
    socket.value?.close()
    socket.value = null
    connected.value = false
    connecting.value = false
    browserPages.value = []
    activePageId.value = ''
    finishPageRequest()
    clearFrame()
    streamId.value = ''
    readyTicket.value = ''
    receivedFrameCount = 0
    if (closeRemote && currentStreamId) {
      try {
        await closeUiLiveStreamSession(currentStreamId)
      } catch (_) {}
    }
  }

  async function restart() {
    if (workspaceExecutionMode.value) {
      await disconnect(true)
      if (workspaceExpired.value || !props.executionId) {
        workspaceExpired.value = false
        emit('reconnect-workspace')
      } else {
        await connect()
      }
      return
    }
    if (!props.executionId) {
      await disconnect(false)
      emit('reconnect-workspace')
      return
    }
    await disconnect(!workspaceExecutionMode.value)
    await connect()
  }
  function updateVisible(value: boolean) {
    emit('update:visible', value)
  }
  function closePanel() {
    emit('update:visible', false)
  }

  watch(
    () => props.visible,
    (value) => {
      if (value) connect()
      else disconnect()
    }
  )
  watch(interactionMode, (value) => {
    flushRecordedText()
    flushRecordedClick()
    if (value === 'select') clearWheelQueue()
    else {
      focusImeProxy()
      void ensureControl()
    }
    emit('interaction-mode', value)
  })
  watch(
    () => [props.executionType, props.executionId],
    async () => {
      if (!props.visible) return
      if (!props.executionId) {
        await disconnect(false)
        return
      }
      if (workspaceExecutionMode.value) {
        await disconnect(false)
        await connect()
        return
      }
      await restart()
    }
  )
  onBeforeUnmount(() => {
    flushRecordedText()
    flushRecordedClick()
    disconnect()
  })
  onMounted(() => {
    if (props.visible && props.executionId) {
      liveLog('组件挂载时 visible=true，主动连接')
      connect()
    }
  })
  defineExpose({
    sendWorkspaceCommand,
    requestControl,
    suspendControlForAutomation,
    resumeControlAfterAutomation,
    setOperateMode,
    setInteractionMode,
    switchPage,
    refreshPages,
    closeActivePage,
    restart,
    pageTitle,
    operateModeValue,
    interactionModeValue,
    activePageIdValue,
    browserPagesValue,
    pageLoadingValue,
    controllingValue: controlling,
  })
</script>

<style scoped>
  .mango-live-stream__page-select {
    width: 220px;
  }

  .mango-live-stream {
    display: flex;
    min-height: 100%;
    flex-direction: column;
    background: var(--m-bg-soft);
  }
  .mango-live-stream--embedded {
    height: 100%;
    min-height: 0;
    border-right: 1px solid var(--m-border);
  }
  .mango-live-stream__embedded-head {
    display: flex;
    min-height: 44px;
    align-items: center;
    justify-content: flex-end;
    padding: 8px 12px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-bg);
  }
  .mango-live-stream__mode {
    display: inline-flex;
    width: max-content;
    min-width: max-content;
    flex: 0 0 auto;
    flex-wrap: nowrap;
    color: var(--m-text-2);
    font-size: 12px;
  }
  .mango-live-stream__mode :deep(.arco-radio-button) {
    width: auto;
    min-width: max-content;
    flex: 0 0 auto;
  }
  .mango-live-stream__mode :deep(.arco-radio-button-content) {
    padding-right: 14px;
    padding-left: 14px;
    white-space: nowrap;
  }
  .mango-live-stream__pages {
    min-width: 0;
  }
  .mango-live-stream__embedded-head {
    flex-wrap: wrap;
    gap: 8px;
  }
  .mango-live-stream__viewport {
    position: relative;
    display: flex;
    min-height: 0;
    flex: 1;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    padding: 0;
    background: var(--m-bg-soft);
    outline: 0;
  }
  .mango-live-stream__viewport img {
    display: block;
    width: auto;
    height: auto;
    max-width: 100%;
    max-height: 100%;
    outline: 0;
    user-select: none;
  }
  .mango-live-stream__ime-input {
    position: absolute;
    z-index: 3;
    width: 2px;
    height: 2px;
    overflow: hidden;
    padding: 0;
    border: 0;
    opacity: 0.01;
    outline: 0;
    pointer-events: none;
    resize: none;
    transform: translate(-50%, -50%);
  }
  .mango-live-stream__viewport.is-controlling.is-picking img {
    cursor: cell;
    box-shadow: 0 0 0 2px var(--m-primary);
  }
  .mango-live-stream__viewport.is-controlling.is-operating img {
    cursor: crosshair;
    box-shadow: 0 0 0 2px var(--m-primary);
  }
  .mango-live-stream__click-effect {
    position: absolute;
    z-index: 2;
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: var(--m-primary);
    box-shadow: 0 0 0 0 rgba(var(--primary-6), 0.28);
    pointer-events: none;
    transform: translate(-50%, -50%);
    animation: mango-live-click-effect 460ms ease-out forwards;
  }
  @keyframes mango-live-click-effect {
    0% {
      opacity: 0.95;
      box-shadow: 0 0 0 0 rgba(var(--primary-6), 0.38);
      transform: translate(-50%, -50%) scale(1);
    }
    100% {
      opacity: 0;
      box-shadow: 0 0 0 18px rgba(var(--primary-6), 0);
      transform: translate(-50%, -50%) scale(1.5);
    }
  }
  .mango-live-stream__empty {
    display: flex;
    align-items: center;
    flex-direction: column;
    gap: 10px;
    color: var(--m-text-inverse);
  }
  .mango-live-stream__empty :deep(svg) {
    width: 42px;
    height: 42px;
  }
</style>
