#!/usr/bin/env node
import crypto from 'node:crypto'

const DEFAULT_API = 'http://127.0.0.1:8000/api'
const DEFAULT_WS = 'ws://127.0.0.1:8011'

function parseArgs(argv) {
  const options = {
    api: process.env.MANGO_API || DEFAULT_API,
    ws: process.env.MANGO_WS || DEFAULT_WS,
    token: process.env.MANGO_TOKEN || '',
    username: process.env.MANGO_USERNAME || '',
    password: process.env.MANGO_PASSWORD || '',
    socketPassword: process.env.MANGO_SOCKET_PASSWORD || process.env.MANGO_PASSWORD || '',
    actuator: process.env.MANGO_ACTUATOR_USERNAME || '',
    testEnv: String(process.env.MANGO_TEST_ENV || '0'),
    liveResourceId: String(process.env.MANGO_LIVE_RESOURCE_ID || ''),
    liveWorkspaceType: process.env.MANGO_LIVE_WORKSPACE_TYPE || 'element_workspace',
    elementId: String(process.env.MANGO_ELEMENT_ID || ''),
    pageStepId: String(process.env.MANGO_PAGE_STEP_ID || ''),
    caseId: String(process.env.MANGO_CASE_ID || ''),
    timeout: Number(process.env.MANGO_CHAIN_TIMEOUT || 120),
    only: new Set(['live', 'element', 'step', 'case']),
    noClose: false,
    verboseWs: Boolean(process.env.MANGO_VERBOSE_WS),
  }
  for (let index = 0; index < argv.length; index += 1) {
    const item = argv[index]
    const next = argv[index + 1]
    if (item === '--api') options.api = next, index += 1
    else if (item === '--ws') options.ws = next, index += 1
    else if (item === '--token') options.token = next, index += 1
    else if (item === '--username') options.username = next, index += 1
    else if (item === '--password') options.password = next, index += 1
    else if (item === '--socket-password') options.socketPassword = next, index += 1
    else if (item === '--actuator') options.actuator = next, index += 1
    else if (item === '--test-env') options.testEnv = String(next), index += 1
    else if (item === '--live-resource-id') options.liveResourceId = String(next), index += 1
    else if (item === '--live-workspace-type') options.liveWorkspaceType = next, index += 1
    else if (item === '--element-id') options.elementId = String(next), index += 1
    else if (item === '--page-step-id') options.pageStepId = String(next), index += 1
    else if (item === '--case-id') options.caseId = String(next), index += 1
    else if (item === '--timeout') options.timeout = Number(next), index += 1
    else if (item === '--only') options.only = new Set(String(next || '').split(',').map((part) => part.trim()).filter(Boolean)), index += 1
    else if (item === '--no-close') options.noClose = true
    else if (item === '--verbose-ws') options.verboseWs = true
    else if (item === '-h' || item === '--help') usage(0)
    else fail(`未知参数：${item}`)
  }
  if (!options.token && (!options.username || !options.password)) {
    fail('请提供 --token，或同时提供 --username 和 --password')
  }
  options.api = normalizeApi(options.api)
  options.ws = normalizeWs(options.ws)
  if (!Number.isFinite(options.timeout) || options.timeout < 10) {
    fail('--timeout 必须是 >= 10 的数字')
  }
  for (const item of options.only) {
    if (!['live', 'element', 'step', 'case'].includes(item)) {
      fail(`--only 不支持：${item}`)
    }
  }
  return options
}

function usage(code) {
  console.log(`UI 自动化完整链路探针

用法:
  sh scripts/probe_ui_chain.sh --token <JWT> --element-id 30 --page-step-id 6 --case-id 46 --test-env 0
  MANGO_TOKEN=<JWT> sh scripts/probe_ui_chain.sh --only live,element
  sh scripts/probe_ui_chain.sh --username <用户名> --password <密码>

覆盖参数:
  --api                 core-api 地址，默认 ${DEFAULT_API}
  --ws                  realtime-service 地址，默认 ${DEFAULT_WS}
  --token               平台 JWT；不传时用 username/password 登录
  --username            平台和 WebSocket 用户名；未提供 token 时必填
  --password            平台登录密码；未提供 token 时必填
  --socket-password     /ws/web/socket 密码，默认同 password
  --actuator            指定执行器账号；为空时后端按当前用户/OPEN 执行器选择
  --test-env            测试环境，默认 0
  --live-resource-id    实时工作台资源 ID，element_workspace 时为页面 ID；不传则自动查首条页面
  --live-workspace-type element_workspace/page_step_workspace，默认 element_workspace
  --element-id          元素检测 ID；不传则自动查首条元素
  --page-step-id        页面步骤调试 ID；不传则自动查首条页面步骤
  --case-id             UI case ID；不传则自动查首条 UI case
  --only                只跑指定场景，逗号分隔：live,element,step,case
  --timeout             单场景等待秒数，默认 120
  --no-close            直播场景结束后不主动关闭会话/工作区
  --verbose-ws          打印未命中的业务 WebSocket 消息摘要，便于排查回传链路
`)
  process.exit(code)
}

function normalizeApi(value) {
  const trimmed = String(value || DEFAULT_API).replace(/\/+$/, '')
  return trimmed.endsWith('/api') ? trimmed : `${trimmed}/api`
}

function normalizeWs(value) {
  return String(value || DEFAULT_WS).replace(/\/+$/, '')
}

function md5(value) {
  return crypto.createHash('md5').update(String(value)).digest('hex')
}

function socketDigest(password) {
  return md5(md5(password))
}

function now() {
  return new Date().toISOString().slice(11, 19)
}

function log(message, data = undefined) {
  console.log(`[${now()}] ${message}${data === undefined ? '' : ` ${JSON.stringify(data)}`}`)
}

function fail(message) {
  console.error(`\n[FAIL] ${message}`)
  process.exit(1)
}

async function request(options, method, path, body = undefined) {
  const response = await fetch(`${options.api}${path}`, {
    method,
    headers: {
      Accept: 'application/json, text/plain, */*',
      'Content-Type': 'application/json; charset=UTF-8',
      'Source-Type': '1',
      ...(options.token ? { Authorization: options.token } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const text = await response.text()
  let payload
  try {
    payload = text ? JSON.parse(text) : {}
  } catch {
    throw new Error(`${method} ${path} 返回非 JSON：HTTP ${response.status} ${text.slice(0, 240)}`)
  }
  if (!response.ok) {
    throw new Error(`${method} ${path} HTTP ${response.status}: ${payload.msg || text}`)
  }
  if (payload.code !== 200) {
    throw new Error(`${method} ${path} code=${payload.code}: ${payload.msg || '请求失败'}`)
  }
  return payload.data
}

async function waitExecutorTask(options, taskId, label) {
  if (!taskId) throw new Error(`${label}未返回 task_id`)
  const deadline = Date.now() + options.timeout * 1000
  while (Date.now() < deadline) {
    const task = await request(
      options,
      'GET',
      `/system/executor/task?task_id=${encodeURIComponent(taskId)}`,
    )
    if (task?.terminal) return task
    await new Promise((resolve) => setTimeout(resolve, 1000))
  }
  throw new Error(`${label}等待任务终态超时：task_id=${taskId}`)
}

function assertTaskSuccess(task, label) {
  if (task?.status !== 'success') {
    throw new Error(`${label}失败：${task?.error_message || task?.error_code || task?.status || '未知错误'}`)
  }
  return task.result || {}
}

async function ensureToken(options) {
  if (options.token) return
  log('登录平台账号')
  const data = await request(
    { ...options, token: '' },
    'POST',
    '/login',
    { username: options.username, password: socketDigest(options.password), type: 1 },
  )
  options.token = data.token
  log('登录成功', { username: data.userName || options.username })
}

async function discoverFirstId(options, label, path, fieldName = 'id') {
  const separator = path.includes('?') ? '&' : '?'
  const data = await request(options, 'GET', `${path}${separator}page=1&pageSize=50`)
  const rows = Array.isArray(data) ? data : data?.data || data?.items || []
  const selectableRows = label === '页面步骤'
    ? rows.filter((item) => !String(item?.name || '').includes('超过'))
    : rows
  const stableStepNames = ['演示-元素点击操作', '演示-输入框', '演示-浏览器弹窗', '百度-搜索一个关键词']
  const first = label === '页面步骤'
    ? stableStepNames
      .map((name) => selectableRows.find((item) => String(item?.name || '') === name))
      .find(Boolean)
    : null
  const selected = first
    || selectableRows.find((item) => Number(item?.latest_match_count || item?.latest_ele_count || 0) > 0)
    || selectableRows.find((item) => item?.status === 1)
    || selectableRows[0]
    || rows[0]
  const value = selected?.[fieldName]
  if (value === undefined || value === null || value === '') {
    throw new Error(`未找到可用于测试的${label}数据，请手动传入对应 ID`)
  }
  log(`自动选择${label}`, { id: value, name: selected?.name || '-' })
  return String(value)
}

async function discoverDefaults(options) {
  if (options.only.has('live') && !options.liveResourceId) {
    options.liveResourceId = await discoverFirstId(options, 'UI页面', '/ui/page')
  }
  if (options.only.has('element') && !options.elementId) {
    options.elementId = await discoverFirstId(options, '页面元素', '/ui/element')
  }
  if (options.only.has('step') && !options.pageStepId) {
    options.pageStepId = await discoverFirstId(options, '页面步骤', '/ui/page/steps')
  }
  if (options.only.has('case') && !options.caseId) {
    options.caseId = await discoverFirstId(options, 'UI Case', '/ui/case')
  }
}

function openJsonSocket(url, label) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url)
    ws.binaryType = 'arraybuffer'
    const timer = setTimeout(() => {
      cleanup()
      reject(new Error(`${label} 连接超时`))
    }, 10000)
    const cleanup = () => {
      clearTimeout(timer)
      ws.removeEventListener('open', onOpen)
      ws.removeEventListener('error', onError)
    }
    const onOpen = () => {
      cleanup()
      resolve(ws)
    }
    const onError = (event) => {
      cleanup()
      reject(new Error(`${label} 连接失败：${event.message || 'unknown'}`))
    }
    ws.addEventListener('open', onOpen)
    ws.addEventListener('error', onError)
  })
}

function parseSocketMessage(event) {
  if (event.data instanceof ArrayBuffer || Buffer.isBuffer(event.data)) {
    const frame = Buffer.isBuffer(event.data) ? event.data : Buffer.from(event.data)
    return { type: '__binary_frame__', bytes: frame.length, raw: frame }
  }
  const text = typeof event.data === 'string' ? event.data : event.data?.toString?.() || ''
  try {
    return JSON.parse(text)
  } catch {
    return { type: '__text__', text }
  }
}

function waitForSocket(ws, predicate, timeoutMs, label, options = {}) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      cleanup()
      reject(new Error(`等待 ${label} 超时`))
    }, timeoutMs)
    const onMessage = (event) => {
      const message = parseSocketMessage(event)
      if (message.type === 'error') {
        cleanup()
        reject(new Error(message.message || `${label} 返回错误`))
        return
      }
      if (predicate(message)) {
        cleanup()
        resolve(message)
      } else if (options.verboseWs) {
        log(`WebSocket 消息未命中：${label}`, summarizeMessage(message))
      }
    }
    const onError = (event) => {
      cleanup()
      reject(new Error(`WebSocket 异常：${event.message || 'unknown'}`))
    }
    const onClose = () => {
      cleanup()
      reject(new Error(`WebSocket 已关闭，未等到 ${label}`))
    }
    const cleanup = () => {
      clearTimeout(timer)
      ws.removeEventListener('message', onMessage)
      ws.removeEventListener('error', onError)
      ws.removeEventListener('close', onClose)
    }
    ws.addEventListener('message', onMessage)
    ws.addEventListener('error', onError)
    ws.addEventListener('close', onClose)
  })
}

async function connectWebSocket(options) {
  const url = `${options.ws}/ws/web/socket?username=${encodeURIComponent(options.username)}&password=${socketDigest(options.socketPassword)}`
  const ws = await openJsonSocket(url, '平台 WebSocket')
  const hello = await waitForSocket(ws, (message) => message.code === 200 && message.connection_id, 10000, '平台 WebSocket 握手')
  ws.__probeVerboseWs = Boolean(options.verboseWs)
  log('平台 WebSocket 已连接', { connection_id: hello.connection_id })
  return ws
}

function summarizeMessage(message) {
  if (!message || typeof message !== 'object') return message
  if (message.type === '__binary_frame__') return { type: message.type, bytes: message.bytes }
  return {
    code: message.code,
    msg: message.msg,
    type: message.type,
    func_name: messageFuncName(message),
    is_notice: message.is_notice,
    user: message.user,
    message_id: message.message_id,
  }
}

function findQueuePayload(value, funcName = '') {
  if (!value || typeof value !== 'object') return null
  if (typeof value.func_name === 'string' && (!funcName || value.func_name === funcName)) return value
  for (const child of Object.values(value)) {
    const found = findQueuePayload(child, funcName)
    if (found) return found
  }
  return null
}

function messageFuncName(message) {
  return findQueuePayload(message)?.func_name || ''
}

function messageData(message) {
  const queuePayload = findQueuePayload(message)
  return queuePayload?.func_args || message?.data || message
}

function terminalStatus(payload) {
  const data = messageData(payload)
  const status = data?.status ?? data?.page_step_result_model?.status ?? data?.case_result_model?.status
  const msg = payload?.msg || data?.error_message || data?.msg || ''
  return { status, msg, data }
}

function assertSuccessStatus(terminal, label) {
  if (Number(terminal.status) === 0) {
    throw new Error(`${label}失败：${terminal.msg || '未知错误'}`)
  }
}

async function connectSubscriber(options, streamId) {
  const url = `${options.ws}/ws/ui-stream/subscribe/${streamId}?token=${encodeURIComponent(options.token)}`
  return openJsonSocket(url, '直播订阅 WebSocket')
}

async function waitFirstFrame(subscriber, timeoutSeconds) {
  const first = await waitForSocket(
    subscriber,
    (message) => message.type === 'stream_status' || message.type === '__binary_frame__',
    timeoutSeconds * 1000,
    'stream_status 或首帧',
  )
  if (first.type === '__binary_frame__') return first
  log('收到推流状态', { status: first.status, page_url: first.page_url })
  return waitForSocket(
    subscriber,
    (message) => message.type === '__binary_frame__',
    timeoutSeconds * 1000,
    '首帧画面',
  )
}

let sequence = 1
async function sendControl(subscriber, event, timeoutMs = 15000) {
  const current = sequence++
  subscriber.send(JSON.stringify({
    type: 'control_event',
    data: { ...event, sequence: current },
  }))
  const ack = await waitForSocket(
    subscriber,
    (message) => message.type === 'control_ack' && message.sequence === current,
    timeoutMs,
    `${event.event_type} control_ack`,
  )
  if (!ack.success) {
    throw new Error(`${event.event_type} 控制事件失败：${ack.message || 'unknown'}`)
  }
  return ack.data
}

async function runLiveProbe(options) {
  log('开始场景：实时画面、点击、输入、元素收集、基线采集')
  const workspace = await request(options, 'POST', '/ui/live-stream/workspace', {
    workspace_type: options.liveWorkspaceType,
    resource_id: Number(options.liveResourceId),
    test_env: Number(options.testEnv),
    actuator_username: options.actuator || undefined,
  })
  if (workspace.status === 'select_actuator') {
    throw new Error(`没有可直接使用的执行器，可选执行器：${(workspace.actuators || []).map((item) => item.username).join(', ') || '-'}`)
  }
  log('实时工作区已创建', {
    workspace_id: workspace.workspace_id,
    execution_type: workspace.execution_type,
    execution_id: workspace.execution_id,
    reused: Boolean(workspace.reused),
  })

  const session = await request(options, 'POST', '/ui/live-stream/session', {
    execution_type: workspace.execution_type,
    execution_id: workspace.execution_id,
    resource_id: workspace.resource_id,
    read_only: false,
  })
  log('直播会话已创建', { stream_id: session.stream_id })
  const subscriber = await connectSubscriber(options, session.stream_id)
  try {
    const ready = await waitForSocket(subscriber, (message) => message.type === 'subscriber_ready', 10000, 'subscriber_ready')
    log('订阅端已就绪', { connection_id: ready.connection_id })
    await request(options, 'POST', `/ui/live-stream/session/${session.stream_id}/start`, {
      ready_ticket: ready.ready_ticket,
    })
    const frame = await waitFirstFrame(subscriber, options.timeout)
    log('首帧画面通过', { bytes: frame.bytes })

    subscriber.send(JSON.stringify({ type: 'control_request' }))
    await waitForSocket(subscriber, (message) => message.type === 'control_granted', 10000, 'control_granted')
    const pages = await sendControl(subscriber, { event_type: 'list_pages' })
    log('页签链路通过', { pages: pages?.pages?.length ?? 0 })
    await sendControl(subscriber, { event_type: 'mouse_click', x: 0.5, y: 0.5, button: 'left' })
    log('点击链路通过')
    await sendControl(subscriber, { event_type: 'text_input', text: 'mango-probe' })
    log('输入链路通过')
    const picked = await sendControl(subscriber, { event_type: 'pick_element', x: 0.5, y: 0.5 }, 30000)
    const pickedLocators = picked?.element?.locators || []
    log('元素收集链路通过', {
      locators: pickedLocators.length,
      has_baseline: Boolean(picked?.element?.baseline_snapshot && Object.keys(picked.element.baseline_snapshot).length),
      result_status: picked?.element_result?.status,
    })
    let rows = []
    if (workspace.workspace_type === 'element_workspace') {
      const scanDispatch = await request(options, 'POST', '/ui/element/scan', {
        page_id: Number(workspace.resource_id),
        workspace_id: workspace.workspace_id,
        mode: 'quick',
      })
      const scanTask = await waitExecutorTask(options, scanDispatch.task_id, '页面元素扫描')
      const scanned = assertTaskSuccess(scanTask, '页面元素扫描')
      rows = scanned?.elements || []
      log('页面元素扫描任务链路通过', { task_id: scanTask.id, elements: rows.length })
    }
    const row = rows.find((item) => (item.locators || []).length) || rows[0]
    if (row) {
      const checked = await sendControl(subscriber, {
        event_type: 'check_locator',
        row_key: 'probe-row',
        name: row.text || row.label || row.placeholder || '探针扫描元素',
        locators: (row.locators || []).slice(0, 3),
      }, 30000)
      log('扫描元素检测链路通过', {
        status: checked?.scan_check_result?.status,
        count: checked?.scan_check_result?.elements?.[0]?.ele_quantity,
      })
    }
  } finally {
    if (!options.noClose) {
      await request(options, 'DELETE', `/ui/live-stream/session/${session.stream_id}`).catch((error) => {
        log('关闭直播会话失败', { error: error.message })
      })
      await request(options, 'DELETE', `/ui/live-stream/workspace/${workspace.workspace_id}?force=true`).catch((error) => {
        log('关闭实时工作区失败', { error: error.message })
      })
    }
    if (subscriber.readyState === WebSocket.OPEN || subscriber.readyState === WebSocket.CONNECTING) {
      subscriber.close(1000)
    }
  }
}

async function runElementCheckProbe(options) {
  log('开始场景：元素检查', { element_id: options.elementId, test_env: options.testEnv })
  const created = await request(options, 'POST', '/ui/element/check', {
    element_id: Number(options.elementId),
    test_env: Number(options.testEnv),
  })
  const task = await waitExecutorTask(options, created?.task_id, '元素检查')
  const result = assertTaskSuccess(task, '元素检查')
  const terminal = terminalStatus(result)
  assertSuccessStatus(terminal, '元素检查')
  log('元素检查回传', {
    status: terminal.status,
    msg: terminal.msg,
    element_id: terminal.data?.element_id,
    check_status: terminal.data?.check_status,
  })
}

async function runPageStepProbe(options) {
  log('开始场景：页面步骤调试', { page_step_id: options.pageStepId, test_env: options.testEnv })
  const created = await request(options, 'GET', `/ui/page/steps/test?page_step_id=${encodeURIComponent(options.pageStepId)}&te=${encodeURIComponent(options.testEnv)}`)
  const task = await waitExecutorTask(options, created?.task_id, '页面步骤调试')
  const result = assertTaskSuccess(task, '页面步骤调试')
  const terminal = terminalStatus(result)
  assertSuccessStatus(terminal, '页面步骤调试')
  log('页面步骤调试回传', {
    status: terminal.status,
    msg: terminal.msg,
    name: terminal.data?.name || terminal.data?.page_step_result_model?.name,
  })
}

async function runCaseProbe(options) {
  log('开始场景：UI Case 执行', { case_id: options.caseId, test_env: options.testEnv })
  const created = await request(options, 'GET', `/ui/case/test?case_id=${encodeURIComponent(options.caseId)}&test_env=${encodeURIComponent(options.testEnv)}`)
  const task = await waitExecutorTask(options, created?.task_id, 'UI Case 执行')
  const result = assertTaskSuccess(task, 'UI Case 执行')
  const terminal = terminalStatus(result)
  assertSuccessStatus(terminal, 'UI Case 执行')
  log('UI Case 执行回传', {
    status: terminal.status,
    msg: terminal.msg,
    name: terminal.data?.name || terminal.data?.case_result_model?.name,
  })
}

async function main() {
  const options = parseArgs(process.argv.slice(2))
  await ensureToken(options)
  await discoverDefaults(options)

  const webSocketNeeded = options.only.has('live')
  const webSocket = webSocketNeeded ? await connectWebSocket(options) : null
  const failures = []
  try {
    for (const [name, runner] of [
      ['live', runLiveProbe],
      ['element', runElementCheckProbe],
      ['step', runPageStepProbe],
      ['case', runCaseProbe],
    ]) {
      if (!options.only.has(name)) continue
      try {
        await runner(options, webSocket)
        log(`场景通过：${name}`)
      } catch (error) {
        failures.push({ name, error: error.stack || error.message })
        log(`场景失败：${name}`, { error: error.message })
      }
    }
  } finally {
    if (webSocket && (webSocket.readyState === WebSocket.OPEN || webSocket.readyState === WebSocket.CONNECTING)) {
      webSocket.close(1000)
    }
  }
  if (failures.length) {
    console.error('\n链路探针失败明细：')
    for (const item of failures) {
      console.error(`\n[${item.name}]\n${item.error}`)
    }
    process.exit(1)
  }
  log('全部链路探针通过')
}

main().catch((error) => fail(error.stack || error.message))
