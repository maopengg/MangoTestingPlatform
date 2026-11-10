<template>
  <a-drawer
    v-model:visible="visible"
    :title="drawerTitle"
    width="min(1440px, calc(100vw - 32px))"
    :footer="false"
    unmount-on-close
  >
    <MangoPanelSpin :loading="loading" class="mango-coverage-flow__spin">
      <a-button v-if="renderError && !loading" size="small" :loading="loading" @click="retry"
        >重新加载流程图</a-button
      >
      <a-tabs
        v-if="interfaceItems.length > 1"
        v-model:active-key="activeInterfaceKey"
        type="card-gutter"
        size="small"
        class="mango-coverage-flow__interface-tabs"
        @change="switchInterface"
      >
        <a-tab-pane
          v-for="item in interfaceItems"
          :key="item.key"
          :title="`${item.detail.method} ${item.detail.url}`"
        />
      </a-tabs>
      <section v-show="mermaidSource && !renderError" class="mango-coverage-flow__viewer">
        <header class="mango-coverage-flow__toolbar">
          <div class="mango-coverage-flow__meta">
            <a-tag size="small" :color="methodTagColor(interfaceDetail.method, enumStore.colors)">{{
              interfaceDetail.method
            }}</a-tag>
            <strong>{{ interfaceDetail.url }}</strong>
            <span>{{ interfaceDetail.interface_name }}</span>
            <a-tooltip :content="interfaceDetail.api_info_binding_reason || apiInfoBindingLabel">
              <a-tag size="small" :color="apiInfoBindingColor">{{ apiInfoBindingLabel }}</a-tag>
            </a-tooltip>
            <span v-if="interfaceDetail.module">
              使用模块：{{ formatModulePath(interfaceDetail.module) }}
            </span>
            <span v-if="interfaceDetail.owner_module">
              归属模块：{{ formatModulePath(interfaceDetail.owner_module) }}
            </span>
          </div>
          <a-space :size="4">
            <span v-if="selectedCaseCoverage" class="mango-coverage-flow__selection">
              {{ selectedCaseCoverage }}
            </span>
            <span v-if="selectedCaseId !== null" class="mango-coverage-flow__context-hint">
              蓝色为当前 Case，灰色为接口上下文
            </span>
            <a-button
              size="mini"
              title="复制当前完整流程图为 PNG 图片"
              :loading="copyingImage"
              @click="copyFlowImage"
            >
              复制图片
            </a-button>
            <span class="mango-coverage-flow__zoom-hint">Ctrl/⌘ + 滚轮缩放</span>
            <a-button
              size="mini"
              title="缩小画布（-）"
              :disabled="zoom <= MIN_ZOOM"
              @click="changeZoom(-ZOOM_STEP)"
            >
              缩小
            </a-button>
            <span class="mango-coverage-flow__zoom">{{ zoomPercent }}%</span>
            <a-button
              size="mini"
              title="放大画布（+）"
              :disabled="zoom >= MAX_ZOOM"
              @click="changeZoom(ZOOM_STEP)"
            >
              放大
            </a-button>
            <a-button size="mini" title="适应当前视图（0）" @click="fitFlow"> 适应视图 </a-button>
          </a-space>
        </header>

        <div class="mango-coverage-flow__workbench">
          <div
            ref="viewportRef"
            class="mango-coverage-flow__viewport"
            role="region"
            tabindex="0"
            aria-label="接口调用流程画布，可使用加号、减号或 Ctrl/Command 加滚轮缩放"
            @wheel="handleCanvasWheel"
            @keydown="handleCanvasKeydown"
          >
            <div ref="canvasRef" class="mango-coverage-flow__canvas"></div>
          </div>

          <aside class="mango-coverage-flow__cases">
            <div class="mango-coverage-flow__cases-header">
              <div>
                <strong>场景 Case</strong>
                <small>
                  已自动化 {{ interfaceDetail.completed_case_count || 0 }} / 总数
                  {{ interfaceDetail.case_count || 0 }}
                </small>
              </div>
              <a-button
                size="mini"
                type="text"
                :disabled="selectedCaseId === null"
                @click="clearSelection"
              >
                接口全景
              </a-button>
            </div>

            <div class="mango-coverage-flow__case-list" role="group" aria-label="场景 Case">
              <a-trigger
                v-for="item in interfaceCases"
                :key="item.id"
                :trigger="['hover', 'focus']"
                position="left"
                :mouse-enter-delay="1000"
                :focus-delay="1000"
                :mouse-leave-delay="120"
                :popup-offset="10"
                auto-fit-position
                update-at-scroll
                @popup-visible-change="(popupVisible) => onCaseDetailVisible(item, popupVisible)"
              >
                <div
                  role="button"
                  tabindex="0"
                  class="mango-coverage-flow__case"
                  :class="{ 'is-selected': selectedCaseId === item.id }"
                  :aria-pressed="selectedCaseId === item.id"
                  @click="toggleCaseSelection(item.id)"
                  @keydown.enter.prevent="toggleCaseSelection(item.id)"
                  @keydown.space.prevent="toggleCaseSelection(item.id)"
                >
                  <a-radio
                    :model-value="selectedCaseId === item.id"
                    tabindex="-1"
                    aria-hidden="true"
                  />
                  <span class="mango-coverage-flow__case-content">
                    <span class="mango-coverage-flow__case-title">{{ item.name }}</span>
                    <small>{{ item.test_scenario || item.legacy_scenario_assertion || '-' }}</small>
                    <small
                      v-if="item.status === 'deferred'"
                      class="mango-coverage-flow__case-deferred-reason"
                      :title="item.remark || '未填写暂不处理原因'"
                    >
                      暂不处理原因：{{ item.remark || '未填写' }}
                    </small>
                    <span class="mango-coverage-flow__case-tags">
                      <a-tag size="small" :color="statusColor(item.status)">{{
                        statusLabel(item.status)
                      }}</a-tag>
                      <a-tag v-if="item.api_case" size="small" color="green">
                        ApiCase #{{ item.api_case }}
                      </a-tag>
                    </span>
                  </span>
                </div>
                <template #content>
                  <div class="mango-coverage-flow__case-detail">
                    <a-spin :loading="!loading && Boolean(caseDetailLoading[item.id])">
                      <template v-if="caseDetailErrors[item.id]">
                        <a-alert type="error">{{ caseDetailErrors[item.id] }}</a-alert>
                      </template>
                      <template v-else>
                        <strong>{{ caseDetail(item).name || item.name }}</strong>
                        <div class="mango-coverage-flow__case-detail-grid">
                          <span>当前状态</span>
                          <b>{{ statusLabel(caseDetail(item).status || item.status) }}</b>
                          <span>测试归属</span>
                          <b>{{ caseDetail(item).test_ownership || '-' }}</b>
                          <span>测试层级</span>
                          <b>{{ scenarioLayerLabel(caseDetail(item).scenario_layer) }}</b>
                          <span>验证类型</span>
                          <b>{{ scenarioTypeLabel(caseDetail(item).scenario_type) }}</b>
                          <span>执行场景</span>
                          <b>{{ scenarioTagsLabel(caseDetail(item).scenario_tags) }}</b>
                          <span>执行结果</span>
                          <b>{{ executionResultLabel(caseDetail(item).execution_result) }}</b>
                          <span>ApiCase</span>
                          <b>{{ apiCaseLabel(caseDetail(item)) }}</b>
                          <span>最近扫描</span>
                          <b>{{ caseDetail(item).current_commit || '-' }}</b>
                        </div>
                        <div class="mango-coverage-flow__case-detail-section">
                          <span>测试场景</span>
                          <p>{{ testScenarioLabel(item) }}</p>
                        </div>
                        <div class="mango-coverage-flow__case-detail-section">
                          <span>核心断言</span>
                          <p>{{ coreAssertionLabel(item) }}</p>
                        </div>
                        <div
                          v-if="casePayloadValue(item, 'preconditions')"
                          class="mango-coverage-flow__case-detail-section"
                        >
                          <span>前置条件</span>
                          <p>{{ casePayloadValue(item, 'preconditions') }}</p>
                        </div>
                        <div class="mango-coverage-flow__case-detail-section">
                          <span>代码证据</span>
                          <p>{{ codeEvidenceLabel(item) }}</p>
                        </div>
                        <div
                          v-if="
                            (caseDetail(item).status || item.status) === 'deferred' ||
                            casePayloadValue(item, 'remark')
                          "
                          class="mango-coverage-flow__case-detail-section"
                        >
                          <span>{{
                            (caseDetail(item).status || item.status) === 'deferred'
                              ? '暂不处理原因'
                              : '备注'
                          }}</span>
                          <p>{{ casePayloadValue(item, 'remark') || '未填写暂不处理原因' }}</p>
                        </div>
                      </template>
                    </a-spin>
                  </div>
                </template>
              </a-trigger>
            </div>
          </aside>
        </div>
      </section>

      <div v-if="!loading && !mermaidSource" class="mango-empty-state mango-coverage-flow__empty">
        暂无接口流程数据
      </div>

      <a-alert v-if="renderError" type="error" class="mango-coverage-flow__error">
        Mermaid 流程渲染失败：{{ renderError }}
      </a-alert>
    </MangoPanelSpin>
  </a-drawer>
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { computed, nextTick, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import { Message } from '@arco-design/web-vue'
  import { toBlob } from 'html-to-image'
  import { useEnum } from '@/store/modules/get-enum'
  import { formatModulePath } from '@/utils/business-format'
  import {
    getCoverageCaseDetail,
    getCoverageCaseFlow,
    getCoverageInterfaceDetail,
  } from '@/api/apitest/module-coverage'
  import { scaleDensityPixels } from '@/hooks/useDisplayDensity'
  import type { CoverageRecord, CoveragePayload, CodeEvidence } from '../types'
  import { methodTagColor } from '../config'

  const enumStore = useEnum()

  const MIN_ZOOM = 0.25
  const MAX_ZOOM = 2
  const ZOOM_STEP = 0.1
  const VIEWPORT_PADDING = 64
  const LABEL_LINE_UNITS = 34
  const NODE_LABEL_PATTERN =
    /([A-Za-z_][\w-]*\s*(?:\[\[|\[\(|\(\[|\(\(|\[|\{|\())"((?:\\.|[^"\\])*)"/g
  const SVG_EXPORT_STYLE_PROPERTIES = [
    'color',
    'fill',
    'fill-opacity',
    'stroke',
    'stroke-width',
    'stroke-opacity',
    'stroke-dasharray',
    'stroke-linecap',
    'stroke-linejoin',
    'opacity',
    'font-family',
    'font-size',
    'font-style',
    'font-weight',
    'line-height',
    'text-anchor',
    'dominant-baseline',
  ]

  const visible = ref(false)
  const loading = ref(false)
  const copyingImage = ref(false)
  const mermaidSource = ref('')
  const renderError = ref('')
  const zoom = ref(1)
  const selectedCaseId = ref<number | null>(null)
  const interfaceCases = ref<CoverageRecord[]>([])
  const interfaceItems = ref<Array<{ key: string; detail: CoverageRecord }>>([])
  const activeInterfaceKey = ref('')
  const interfaceDetail = reactive<CoverageRecord>({ id: 0 })
  const caseDetailCache = reactive<Record<number, CoverageRecord>>({})
  const caseDetailLoading = reactive<Record<number, boolean>>({})
  const caseDetailErrors = reactive<Record<number, string>>({})
  const canvasRef = ref<HTMLElement>()
  const viewportRef = ref<HTMLElement>()
  const diagramSize = { width: 0, height: 0 }
  let renderSequence = 0
  let panelSession = 0
  const caseDetailTokens: Record<number, number> = {}
  let retryRows: CoverageRecord[] = []
  let retryCaseId: number | undefined

  const zoomPercent = computed(() => Math.round(zoom.value * 100))
  const selectedCaseCoverage = computed(() => {
    if (selectedCaseId.value === null) return ''
    const selected = interfaceCases.value.find((item) => item.id === selectedCaseId.value)
    if (!selected) return ''
    const nodeCount = Array.isArray(selected.node_ids) ? selected.node_ids.length : 0
    const branchCount = Array.isArray(selected.branch_ids) ? selected.branch_ids.length : 0
    return `当前 Case 覆盖 ${nodeCount} 个节点 / ${branchCount} 条分支`
  })
  const drawerTitle = computed(() =>
    interfaceItems.value.length > 1
      ? `接口调用全景（${interfaceItems.value.length}）`
      : '接口调用全景'
  )
  const apiInfoBindingLabel = computed(() => {
    if (interfaceDetail.api_info_id) return `ApiInfo #${interfaceDetail.api_info_id}`
    return (
      (
        {
          unbound: 'ApiInfo 未绑定',
          ambiguous: 'ApiInfo 候选冲突',
          mismatch: 'ApiInfo 待确认',
        } as Record<string, string>
      )[interfaceDetail.api_info_binding_status || ''] || 'ApiInfo 未绑定'
    )
  })
  const apiInfoBindingColor = computed(
    () =>
      ((
        {
          bound: 'green',
          ambiguous: 'red',
          mismatch: 'orange',
        } as Record<string, string>
      )[interfaceDetail.api_info_binding_status || ''] || 'blue')
  )

  function cssToken(name: string) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  }

  function labelCharacterUnits(character: string) {
    return /^[\x00-\xff]$/.test(character) ? 1 : 2
  }

  function labelTokenUnits(token: string) {
    return Array.from(token).reduce((total, character) => total + labelCharacterUnits(character), 0)
  }

  function labelTokens(value: string) {
    return (
      value.match(
        /(?:[/.]|::)?[A-Za-z0-9_$%=-]+|[\u3400-\u9fff]|[^\u3400-\u9fffA-Za-z0-9_$%=-]/g
      ) || []
    )
  }

  function wrapLabelLine(value: string) {
    const tokens = labelTokens(value)
    const lines: string[] = []
    let line = ''
    let lineUnits = 0

    tokens.forEach((token) => {
      const tokenUnits = labelTokenUnits(token)
      const isWhitespace = /^\s+$/.test(token)
      const isClosingPunctuation = /^[，。！？；：、,.!?;:）)\]}]$/.test(token)
      if (line && !isClosingPunctuation && lineUnits + tokenUnits > LABEL_LINE_UNITS) {
        lines.push(line.trimEnd())
        line = isWhitespace ? '' : token
        lineUnits = isWhitespace ? 0 : tokenUnits
        return
      }
      if (!line && isWhitespace) return
      line += token
      lineUnits += tokenUnits
    })

    if (line) lines.push(line.trimEnd())
    return lines.filter(Boolean)
  }

  function wrapMermaidNodeLabels(source: string) {
    return source.replace(NODE_LABEL_PATTERN, (_match, prefix: string, label: string) => {
      const wrapped = label
        .split(/\\n|<br\s*\/?>/gi)
        .flatMap((line) => wrapLabelLine(line))
        .join('<br/>')
      return `${prefix}"${wrapped}"`
    })
  }

  function currentSvg() {
    return canvasRef.value?.querySelector<SVGSVGElement>('svg')
  }

  function inlineSvgComputedStyles(sourceSvg: SVGSVGElement, targetSvg: SVGSVGElement) {
    const sourceElements: Element[] = [sourceSvg, ...Array.from(sourceSvg.querySelectorAll('*'))]
    const targetElements: Element[] = [targetSvg, ...Array.from(targetSvg.querySelectorAll('*'))]
    sourceElements.forEach((sourceElement, index) => {
      const targetElement = targetElements[index] as SVGElement | undefined
      if (!targetElement) return
      const style = getComputedStyle(sourceElement)
      SVG_EXPORT_STYLE_PROPERTIES.forEach((property) => {
        const value = style.getPropertyValue(property)
        if (value) targetElement.style.setProperty(property, value)
      })
    })
  }

  async function createFlowImageBlob() {
    const canvas = canvasRef.value
    const svg = currentSvg()
    const viewport = viewportRef.value
    if (!canvas || !svg || !viewport || !diagramSize.width || !diagramSize.height) {
      throw new Error('当前没有可复制的流程图')
    }

    const exportPadding = 32
    const width = Math.ceil(diagramSize.width + exportPadding * 2)
    const height = Math.ceil(diagramSize.height + exportPadding * 2)
    const exportHost = document.createElement('div')
    const exportNode = canvas.cloneNode(true) as HTMLElement
    const exportSvg = exportNode.querySelector<SVGSVGElement>('svg')
    if (!exportSvg) throw new Error('流程图生成失败')

    inlineSvgComputedStyles(svg, exportSvg)
    const viewportStyle = getComputedStyle(viewport)
    exportHost.style.position = 'fixed'
    exportHost.style.left = '-100000px'
    exportHost.style.top = '0'
    exportHost.style.pointerEvents = 'none'
    exportHost.style.opacity = '0'
    exportNode.style.position = 'relative'
    exportNode.style.left = '0'
    exportNode.style.top = '0'
    exportNode.style.width = `${width}px`
    exportNode.style.height = `${height}px`
    exportNode.style.minWidth = '0'
    exportNode.style.minHeight = '0'
    exportNode.style.padding = `${exportPadding}px`
    exportNode.style.backgroundColor = viewportStyle.backgroundColor
    exportNode.style.backgroundImage = viewportStyle.backgroundImage
    exportNode.style.backgroundSize = '40px 40px'
    exportSvg.style.width = `${diagramSize.width}px`
    exportSvg.style.height = `${diagramSize.height}px`
    exportHost.appendChild(exportNode)
    document.body.appendChild(exportHost)

    try {
      if (document.fonts?.ready) await document.fonts.ready
      await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()))
      const pixelRatio = Math.max(
        1,
        Math.min(
          2,
          24000 / Math.max(width, 1),
          24000 / Math.max(height, 1),
          Math.sqrt(32_000_000 / Math.max(width * height, 1))
        )
      )
      const blob = await toBlob(exportNode, {
        width,
        height,
        pixelRatio,
        cacheBust: true,
        backgroundColor: viewportStyle.backgroundColor,
      })
      if (!blob) throw new Error('流程图图片生成失败')
      return blob
    } finally {
      exportHost.remove()
    }
  }

  async function copyFlowImage() {
    if (copyingImage.value) return
    if (!navigator.clipboard?.write || typeof ClipboardItem === 'undefined') {
      Message.error('当前浏览器不支持复制图片，请使用 HTTPS 或 localhost 访问')
      return
    }
    const context = panelSession
    copyingImage.value = true
    try {
      const blob = await createFlowImageBlob()
      if (!visible.value || context !== panelSession) return
      await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
      if (visible.value && context === panelSession) Message.success('完整流程图已复制为图片')
    } catch (error) {
      if (visible.value && context === panelSession)
        Message.error(error instanceof Error ? error.message : '复制图片失败，请检查剪贴板权限')
    } finally {
      copyingImage.value = false
    }
  }

  function mermaidNodeId(node: SVGGElement) {
    const dataId = node.getAttribute('data-id')
    if (dataId) return dataId
    return node.id.replace(/^flowchart-/, '').replace(/-\d+$/, '')
  }

  function applySemanticStyles(svg: SVGSVGElement) {
    const nodes = Array.from(svg.querySelectorAll<SVGGElement>('g.node'))
    nodes.forEach((node, index) => {
      const label = node.textContent?.trim() || ''
      if (index === 0) {
        node.classList.add('mango-flow-node--entry')
      } else if (/未解析|外部边界|待确认|未知/.test(label)) {
        node.classList.add('mango-flow-node--boundary')
      } else if (node.querySelector('polygon')) {
        node.classList.add('mango-flow-node--decision')
      } else if (/错误|异常|失败|拒绝|超时|不可用|无权限/.test(label)) {
        node.classList.add('mango-flow-node--error')
      } else if (
        /^(?:映射|返回|输出).*(?:响应|结果|数据)$|^(?:成功|正常)?响应(?:$|[：:])|^(?:流程|处理)(?:完成|结束)$/.test(
          label
        )
      ) {
        node.classList.add('mango-flow-node--result')
      }
    })
  }

  function applyCaseHighlight() {
    const svg = currentSvg()
    if (!svg) return
    const selectedNodes = new Set<string>()
    const selectedBranches = new Set<string>()
    interfaceCases.value.forEach((item) => {
      if (selectedCaseId.value === item.id) {
        const nodeIds: string[] = item.node_ids || []
        const branchIds: string[] = item.branch_ids || []
        nodeIds.forEach((nodeId) => selectedNodes.add(nodeId))
        branchIds.forEach((branchId) => selectedBranches.add(branchId))
      }
    })
    const nodes = Array.from(svg.querySelectorAll<SVGGElement>('g.node'))
    const matchedNodes = nodes.filter((node) => selectedNodes.has(mermaidNodeId(node)))
    nodes.forEach((node) => {
      node.classList.remove('mango-flow-node--selected', 'mango-flow-node--muted')
      if (selectedCaseId.value === null || !matchedNodes.length) return
      node.classList.add(
        selectedNodes.has(mermaidNodeId(node))
          ? 'mango-flow-node--selected'
          : 'mango-flow-node--muted'
      )
    })

    svg.querySelectorAll<SVGGElement>('g.edgePath').forEach((edge) => {
      edge.classList.remove('mango-flow-edge--selected', 'mango-flow-edge--muted')
      if (selectedCaseId.value === null || !matchedNodes.length) return
      const descriptor = `${edge.id} ${edge.getAttribute('data-edge') || ''}`
      const matchCount = Array.from(selectedNodes).filter((nodeId) =>
        descriptor.includes(nodeId)
      ).length
      const branchMatched = Array.from(selectedBranches).some((branchId) =>
        descriptor.includes(branchId)
      )
      edge.classList.add(
        branchMatched || matchCount >= 2 ? 'mango-flow-edge--selected' : 'mango-flow-edge--muted'
      )
    })
  }

  function toggleCaseSelection(caseId: number) {
    selectedCaseId.value = selectedCaseId.value === caseId ? null : caseId
    applyCaseHighlight()
  }

  function clearSelection() {
    selectedCaseId.value = null
    applyCaseHighlight()
  }

  function clampZoom(value: number) {
    return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, value))
  }

  function applyZoom() {
    const svg = currentSvg()
    const viewport = viewportRef.value
    const canvas = canvasRef.value
    if (!svg || !viewport || !canvas || !diagramSize.width || !diagramSize.height) return
    const width = diagramSize.width * zoom.value
    const height = diagramSize.height * zoom.value
    svg.style.width = `${width}px`
    svg.style.height = `${height}px`
    canvas.style.width = `${Math.max(
      viewport.clientWidth,
      width + scaleDensityPixels(VIEWPORT_PADDING)
    )}px`
    canvas.style.height = `${Math.max(
      viewport.clientHeight,
      height + scaleDensityPixels(VIEWPORT_PADDING)
    )}px`
  }

  function centerViewport() {
    const viewport = viewportRef.value
    const canvas = canvasRef.value
    if (!viewport || !canvas) return
    viewport.scrollLeft = Math.max(0, (canvas.scrollWidth - viewport.clientWidth) / 2)
    viewport.scrollTop = Math.max(0, (canvas.scrollHeight - viewport.clientHeight) / 2)
  }

  function setZoom(value: number) {
    zoom.value = clampZoom(Number(value.toFixed(2)))
    applyZoom()
    nextTick(centerViewport)
  }

  function changeZoom(delta: number) {
    setZoom(zoom.value + delta)
  }

  function handleCanvasWheel(event: WheelEvent) {
    if (!event.ctrlKey && !event.metaKey) return
    event.preventDefault()
    const viewport = viewportRef.value
    if (!viewport) return
    const previousZoom = zoom.value
    const nextZoom = clampZoom(previousZoom + (event.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP))
    if (nextZoom === previousZoom) return
    const rect = viewport.getBoundingClientRect()
    const pointerX = event.clientX - rect.left
    const pointerY = event.clientY - rect.top
    const contentX = viewport.scrollLeft + pointerX
    const contentY = viewport.scrollTop + pointerY
    zoom.value = nextZoom
    applyZoom()
    nextTick(() => {
      const ratio = nextZoom / previousZoom
      viewport.scrollLeft = contentX * ratio - pointerX
      viewport.scrollTop = contentY * ratio - pointerY
    })
  }

  function handleCanvasKeydown(event: KeyboardEvent) {
    if (event.key === '+' || event.key === '=') {
      event.preventDefault()
      changeZoom(ZOOM_STEP)
    } else if (event.key === '-') {
      event.preventDefault()
      changeZoom(-ZOOM_STEP)
    } else if (event.key === '0') {
      event.preventDefault()
      fitFlow()
    }
  }

  function fitFlow() {
    const viewport = viewportRef.value
    if (!viewport || !diagramSize.width || !diagramSize.height) return
    const widthRatio =
      (viewport.clientWidth - scaleDensityPixels(VIEWPORT_PADDING)) / diagramSize.width
    const heightRatio =
      (viewport.clientHeight - scaleDensityPixels(VIEWPORT_PADDING)) / diagramSize.height
    setZoom(Math.min(1, widthRatio, heightRatio))
  }

  function statusLabel(status = '') {
    const labels: Record<string, string> = {
      pending_create: '待创建',
      completed: '已完成',
      deferred: '暂不处理',
      removed: '已移除',
    }
    return labels[status] || status
  }

  function statusColor(status = '') {
    if (status === 'completed') return 'green'
    if (status === 'deferred') return 'orange'
    if (status === 'removed') return 'red'
    return 'blue'
  }

  function executionResultLabel(result?: string) {
    const labels: Record<string, string> = {
      passed: '执行通过',
      failed: '执行失败',
      partial: '部分通过',
      not_applicable: '不适用',
      not_executed: '未执行',
    }
    return labels[result || ''] || result || '-'
  }

  function enumLabel(
    options: Array<{ key: string | number; title: string }>,
    value?: string | number
  ) {
    return options.find((item) => String(item.key) === String(value))?.title || '-'
  }

  function scenarioLayerLabel(value?: number) {
    return enumLabel(enumStore.api_case_scenario_layer, value)
  }

  function scenarioTypeLabel(value?: number) {
    return enumLabel(enumStore.api_case_scenario_type, value)
  }

  function scenarioTagsLabel(values?: string[]) {
    return values?.length
      ? values.map((value) => enumLabel(enumStore.api_case_scenario_tag, value)).join('、')
      : '-'
  }

  function caseDetail(item: CoverageRecord) {
    return caseDetailCache[item.id] || item
  }

  function casePayloadValue<K extends keyof CoveragePayload>(
    item: CoverageRecord,
    key: K
  ): CoveragePayload[K] {
    const detail = caseDetail(item)
    return detail.payload?.[key] ?? detail[key]
  }

  function testScenarioLabel(item: CoverageRecord) {
    return casePayloadValue(item, 'test_scenario') || '-'
  }

  function coreAssertionLabel(item: CoverageRecord) {
    return (
      casePayloadValue(item, 'core_assertion') ||
      casePayloadValue(item, 'scenario_assertion') ||
      caseDetail(item).legacy_scenario_assertion ||
      '-'
    )
  }

  function apiCaseLabel(detail: CoverageRecord) {
    if (!detail.api_case) return '-'
    return detail.api_case_name
      ? `#${detail.api_case} · ${detail.api_case_name}`
      : `#${detail.api_case}`
  }

  function codeEvidenceLabel(item: CoverageRecord) {
    const evidence = casePayloadValue(item, 'code_evidence')
    if (typeof evidence === 'string') return evidence || '-'
    if (!Array.isArray(evidence) || !evidence.length) return '-'
    return evidence
      .map((entry: CodeEvidence) => {
        const location = [entry.path, entry.symbol].filter(Boolean).join(' · ')
        const lines = entry.start_line
          ? `:${entry.start_line}${entry.end_line ? `-${entry.end_line}` : ''}`
          : ''
        return `${location}${lines}`
      })
      .join('\n')
  }

  async function onCaseDetailVisible(item: CoverageRecord, popupVisible: boolean) {
    const id = item.id
    if (!popupVisible) {
      caseDetailTokens[id] = (caseDetailTokens[id] || 0) + 1
      caseDetailLoading[id] = false
      return
    }
    if (!visible.value || caseDetailCache[id] || caseDetailLoading[id]) return
    const context = panelSession,
      token = (caseDetailTokens[id] = (caseDetailTokens[id] || 0) + 1)
    caseDetailLoading[id] = true
    delete caseDetailErrors[id]
    try {
      const response = await getCoverageCaseDetail(id)
      if (visible.value && context === panelSession && token === caseDetailTokens[id])
        caseDetailCache[id] = response.data || item
    } catch {
      if (visible.value && context === panelSession && token === caseDetailTokens[id])
        caseDetailErrors[id] = 'Case详情加载失败，请重新展开重试'
    } finally {
      if (context === panelSession && token === caseDetailTokens[id]) caseDetailLoading[id] = false
    }
  }

  async function renderFlow(source: string, sequence: number) {
    await nextTick()
    if (!canvasRef.value || sequence !== renderSequence) return
    try {
      const { default: mermaid } = await import('mermaid')
      if (!visible.value || sequence !== renderSequence) return
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: 'strict',
        theme: 'base',
        themeVariables: {
          background: cssToken('--m-surface'),
          primaryColor: cssToken('--m-surface'),
          primaryBorderColor: cssToken('--m-border-strong'),
          primaryTextColor: cssToken('--m-text'),
          lineColor: cssToken('--m-muted'),
          secondaryColor: cssToken('--m-surface-soft'),
          tertiaryColor: cssToken('--m-primary-soft'),
          edgeLabelBackground: cssToken('--m-surface'),
          fontFamily: 'inherit',
          fontSize: `${scaleDensityPixels(14)}px`,
        },
        flowchart: {
          curve: 'linear',
          // SVG labels participate in Mermaid layout; HTML labels clip long CJK text.
          htmlLabels: false,
          useMaxWidth: false,
          nodeSpacing: scaleDensityPixels(44),
          rankSpacing: scaleDensityPixels(34),
          padding: scaleDensityPixels(14),
          wrappingWidth: scaleDensityPixels(260),
        },
      })
      const rendered = await mermaid.render(
        `mango-coverage-flow-${sequence}`,
        wrapMermaidNodeLabels(source)
      )
      if (!canvasRef.value || sequence !== renderSequence) return
      canvasRef.value.innerHTML = rendered.svg
      rendered.bindFunctions?.(canvasRef.value)

      const svg = currentSvg()
      if (!svg) throw new Error('未生成有效的 SVG 流程图')
      const viewBox = svg.viewBox.baseVal
      diagramSize.width = viewBox.width || Number.parseFloat(svg.getAttribute('width') || '0')
      diagramSize.height = viewBox.height || Number.parseFloat(svg.getAttribute('height') || '0')
      svg.removeAttribute('width')
      svg.removeAttribute('height')
      svg.setAttribute('preserveAspectRatio', 'xMidYMid meet')
      applySemanticStyles(svg)
      applyCaseHighlight()
      await nextTick()
      if (visible.value && sequence === renderSequence) fitFlow()
    } catch (error) {
      if (sequence !== renderSequence) return
      renderError.value = error instanceof Error ? error.message : String(error)
      if (canvasRef.value) canvasRef.value.innerHTML = ''
    }
  }

  function resetFlow(initialCaseId?: number) {
    loading.value = true
    mermaidSource.value = ''
    renderError.value = ''
    zoom.value = 1
    selectedCaseId.value = initialCaseId || null
    interfaceCases.value = []
    diagramSize.width = 0
    diagramSize.height = 0
    for (const key of Object.keys(interfaceDetail) as Array<keyof CoverageRecord>)
      delete interfaceDetail[key]
    interfaceDetail.id = 0
    if (canvasRef.value) canvasRef.value.innerHTML = ''
  }

  function interfaceKey(row: CoverageRecord) {
    return String(
      row.key ||
        row.coverage_interface ||
        row.id ||
        [
          row.project_product?.id || row.project_product_id,
          row.module?.id || row.module_id,
          row.repository_key,
          row.branch,
          row.interface_source_key,
        ].join(':')
    )
  }

  async function fetchInterfaceDetail(
    row: CoverageRecord,
    caseId?: number,
    sequence = renderSequence
  ) {
    let interfaceId = row.coverage_interface || row.id
    if (caseId && !row.coverage_interface) {
      const flowResponse = await getCoverageCaseFlow(caseId)
      interfaceId = flowResponse.data?.coverage_interface_id
    }
    if (!visible.value || sequence !== renderSequence) return null
    const response = await getCoverageInterfaceDetail({
      id: interfaceId,
    })
    return { key: interfaceKey(row), detail: response.data || {} }
  }

  async function activateInterface(key: string, selectedCaseId?: number) {
    const target = interfaceItems.value.find((item) => item.key === String(key))
    if (!target) return
    const sequence = ++renderSequence
    ++panelSession
    Object.keys(caseDetailLoading).forEach((key) => {
      caseDetailLoading[Number(key)] = false
    })
    activeInterfaceKey.value = target.key
    resetFlow(selectedCaseId)
    try {
      Object.assign(interfaceDetail, target.detail)
      interfaceCases.value = target.detail.cases || []
      mermaidSource.value = String(target.detail.mermaid || '').trim()
      if (mermaidSource.value) await renderFlow(mermaidSource.value, sequence)
    } finally {
      if (sequence === renderSequence) loading.value = false
    }
  }

  async function openMany(rows: CoverageRecord[], selectedCaseId?: number) {
    if (!rows.length) return
    const requestSequence = ++renderSequence
    ++panelSession
    retryRows = rows.map((row) => ({ ...row }))
    retryCaseId = selectedCaseId
    visible.value = true
    interfaceItems.value = []
    activeInterfaceKey.value = ''
    Object.keys(caseDetailCache).forEach((key) => delete caseDetailCache[Number(key)])
    Object.keys(caseDetailLoading).forEach((key) => delete caseDetailLoading[Number(key)])
    Object.keys(caseDetailErrors).forEach((key) => delete caseDetailErrors[Number(key)])
    resetFlow(selectedCaseId)
    try {
      const details = await Promise.all(
        rows.map((row) => fetchInterfaceDetail(row, selectedCaseId, requestSequence))
      )
      if (requestSequence !== renderSequence) return
      const loaded = details.filter((item): item is NonNullable<typeof item> => item !== null)
      interfaceItems.value = loaded
      if (loaded[0]) await activateInterface(loaded[0].key, selectedCaseId)
      else loading.value = false
    } catch (error) {
      if (requestSequence !== renderSequence) return
      void (reportLoadError(error, "流程图加载失败，请重试", false), renderError.value = '流程图加载失败，请重试')
      loading.value = false
    }
  }

  function open(row: CoverageRecord, selectedCaseId?: number) {
    return openMany([row], selectedCaseId)
  }

  function switchInterface(key: string | number) {
    activateInterface(String(key))
  }

  function close() {
    ++panelSession
    ++renderSequence
    visible.value = false
    loading.value = false
    interfaceItems.value = []
    interfaceCases.value = []
    activeInterfaceKey.value = ''
    mermaidSource.value = ''
    renderError.value = ''
    for (const key of Object.keys(caseDetailLoading)) caseDetailLoading[Number(key)] = false
    if (canvasRef.value) canvasRef.value.innerHTML = ''
  }
  function retry() {
    return openMany(retryRows, retryCaseId)
  }
  watch(
    visible,
    (value) => {
      if (!value) close()
    },
    { flush: 'sync' }
  )
  const resizeObserver =
    typeof ResizeObserver === 'undefined'
      ? undefined
      : new ResizeObserver(() => {
          if (visible.value) fitFlow()
        })
  watch(viewportRef, (element) => {
    resizeObserver?.disconnect()
    if (element) resizeObserver?.observe(element)
  })
  onDeactivated(close)
  onBeforeUnmount(() => {
    close()
    resizeObserver?.disconnect()
  })
  defineExpose({ open, openMany, close })
</script>

<style lang="less" scoped>
  .mango-coverage-flow__spin {
    display: flex;
    width: 100%;
    min-height: 560px;
    flex-direction: column;
  }

  .mango-coverage-flow__spin :deep(> .mango-panel-spin__content) {
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  .mango-coverage-flow__interface-tabs {
    flex: none;
    margin-bottom: var(--m-page-gap);
  }

  .mango-coverage-flow__viewer {
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
  }

  .mango-coverage-flow__toolbar {
    display: flex;
    min-height: 44px;
    align-items: center;
    justify-content: space-between;
    gap: var(--m-page-gap);
    padding: 0 var(--m-page-gap);
    border-bottom: 1px solid var(--m-border);
  }

  .mango-coverage-flow__meta {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: var(--m-page-gap);
  }

  .mango-coverage-flow__meta strong,
  .mango-coverage-flow__meta span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-coverage-flow__meta span,
  .mango-coverage-flow__selection,
  .mango-coverage-flow__context-hint,
  .mango-coverage-flow__zoom-hint {
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-coverage-flow__selection {
    color: var(--m-primary);
    font-weight: 500;
  }

  .mango-coverage-flow__zoom {
    display: inline-flex;
    width: 46px;
    justify-content: center;
    color: var(--m-text-2);
    font-variant-numeric: tabular-nums;
  }

  .mango-coverage-flow__workbench {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 300px;
    height: calc(100vh - 142px);
    min-height: 520px;
  }

  .mango-coverage-flow__interface-tabs
    + .mango-coverage-flow__viewer
    .mango-coverage-flow__workbench {
    height: calc(100vh - 190px);
  }

  .mango-coverage-flow__viewport {
    min-width: 0;
    overflow: auto;
    background-color: var(--m-surface-soft);
    background-image: linear-gradient(
        to right,
        color-mix(in srgb, var(--m-border) 58%, transparent) 1px,
        transparent 1px
      ),
      linear-gradient(
        to bottom,
        color-mix(in srgb, var(--m-border) 58%, transparent) 1px,
        transparent 1px
      );
    background-size: 20px 20px;
  }

  .mango-coverage-flow__viewport:focus-visible {
    box-shadow: inset 0 0 0 2px var(--m-primary-border);
  }

  .mango-coverage-flow__canvas {
    display: flex;
    min-width: 100%;
    min-height: 100%;
    align-items: center;
    justify-content: center;
    padding: 32px;
    box-sizing: border-box;
  }

  .mango-coverage-flow__cases {
    display: flex;
    min-height: 0;
    flex-direction: column;
    border-left: 1px solid var(--m-border);
    background: var(--m-surface);
  }

  .mango-coverage-flow__cases-header {
    display: flex;
    min-height: 52px;
    align-items: center;
    justify-content: space-between;
    gap: var(--m-page-gap);
    padding: 0 12px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-coverage-flow__cases-header > div {
    display: flex;
    min-width: 0;
    flex-direction: column;
  }

  .mango-coverage-flow__cases-header small,
  .mango-coverage-flow__case small {
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-coverage-flow__case-list {
    min-height: 0;
    overflow: auto;
    padding: var(--m-page-gap);
  }

  .mango-coverage-flow__case {
    display: flex;
    width: 100%;
    align-items: flex-start;
    gap: var(--m-page-gap);
    margin: 0 0 var(--m-page-gap);
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    color: var(--m-text);
    background: var(--m-surface);
    text-align: left;
    cursor: pointer;
    transition: border-color 0.16s ease, background-color 0.16s ease;
  }

  .mango-coverage-flow__case:hover,
  .mango-coverage-flow__case.is-selected {
    border-color: var(--m-primary-border);
    background: var(--m-primary-soft);
  }

  .mango-coverage-flow__case-content {
    display: flex;
    min-width: 0;
    flex: 1;
    flex-direction: column;
    gap: 5px;
  }

  .mango-coverage-flow__case-title {
    overflow: hidden;
    font-weight: 500;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-coverage-flow__case-deferred-reason {
    color: var(--m-warning) !important;
  }

  .mango-coverage-flow__case-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .mango-coverage-flow__case-detail {
    width: 420px;
    max-width: calc(100vw - 48px);
    max-height: min(520px, calc(100vh - 48px));
    padding: 14px;
    overflow: auto;
    border: 1px solid var(--m-border-strong);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    box-shadow: var(--m-shadow);
    color: var(--m-text);
  }

  .mango-coverage-flow__case-detail > :deep(.arco-spin) {
    display: block;
    min-height: 36px;
  }

  .mango-coverage-flow__case-detail strong {
    display: block;
    margin-bottom: 12px;
    font-size: 15px;
    line-height: 1.5;
    overflow-wrap: anywhere;
  }

  .mango-coverage-flow__case-detail-grid {
    display: grid;
    grid-template-columns: 72px minmax(0, 1fr);
    gap: 8px 12px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--m-border);
    font-size: 12px;
    line-height: 1.5;
  }

  .mango-coverage-flow__case-detail-grid span,
  .mango-coverage-flow__case-detail-section > span {
    color: var(--m-muted);
  }

  .mango-coverage-flow__case-detail-grid b {
    min-width: 0;
    font-weight: 500;
    overflow-wrap: anywhere;
  }

  .mango-coverage-flow__case-detail-section {
    margin-top: 12px;
    font-size: 12px;
  }

  .mango-coverage-flow__case-detail-section p {
    margin: 4px 0 0;
    line-height: 1.6;
    overflow-wrap: anywhere;
    white-space: pre-wrap;
  }

  .mango-coverage-flow__canvas :deep(svg) {
    display: block;
    max-width: none !important;
    overflow: visible;
  }

  .mango-coverage-flow__canvas :deep(.node),
  .mango-coverage-flow__canvas :deep(.edgePath) {
    transition: opacity 0.16s ease;
  }

  .mango-coverage-flow__canvas :deep(.node rect),
  .mango-coverage-flow__canvas :deep(.node polygon),
  .mango-coverage-flow__canvas :deep(.node circle),
  .mango-coverage-flow__canvas :deep(.node path) {
    stroke-width: 1.25px;
    filter: drop-shadow(0 4px 7px color-mix(in srgb, var(--m-text) 9%, transparent));
  }

  .mango-coverage-flow__canvas :deep(.node rect) {
    rx: 8px;
    ry: 8px;
  }

  .mango-coverage-flow__canvas :deep(.nodeLabel) {
    color: var(--m-text) !important;
    font-weight: 500;
    line-height: 1.45;
  }

  .mango-coverage-flow__canvas :deep(.edgePath path) {
    stroke-width: 1.4px;
  }

  .mango-coverage-flow__canvas :deep(.edgeLabel) {
    color: var(--m-text-2) !important;
    font-size: 12px;
  }

  .mango-coverage-flow__canvas :deep(.edgeLabel rect),
  .mango-coverage-flow__canvas :deep(.labelBkg) {
    fill: var(--m-surface) !important;
    opacity: 0.96 !important;
  }

  .mango-coverage-flow__canvas :deep(.mango-flow-node--entry rect),
  .mango-coverage-flow__canvas :deep(.mango-flow-node--entry path) {
    fill: var(--m-primary-soft) !important;
    stroke: var(--m-primary) !important;
  }

  .mango-coverage-flow__canvas :deep(.mango-flow-node--decision polygon),
  .mango-coverage-flow__canvas :deep(.mango-flow-node--decision path) {
    fill: color-mix(in srgb, var(--m-warning) 12%, var(--m-surface)) !important;
    stroke: var(--m-warning) !important;
  }

  .mango-coverage-flow__canvas :deep(.mango-flow-node--boundary rect),
  .mango-coverage-flow__canvas :deep(.mango-flow-node--boundary path) {
    fill: color-mix(in srgb, var(--m-danger) 8%, var(--m-surface)) !important;
    stroke: var(--m-danger) !important;
    stroke-dasharray: 5 3;
  }

  .mango-coverage-flow__canvas :deep(.mango-flow-node--error rect),
  .mango-coverage-flow__canvas :deep(.mango-flow-node--error path) {
    fill: color-mix(in srgb, var(--m-danger) 10%, var(--m-surface)) !important;
    stroke: var(--m-danger) !important;
  }

  .mango-coverage-flow__canvas :deep(.mango-flow-node--result rect),
  .mango-coverage-flow__canvas :deep(.mango-flow-node--result circle),
  .mango-coverage-flow__canvas :deep(.mango-flow-node--result path) {
    fill: color-mix(in srgb, var(--m-success) 10%, var(--m-surface)) !important;
    stroke: var(--m-success) !important;
  }

  .mango-coverage-flow__canvas :deep(.mango-flow-node--muted),
  .mango-coverage-flow__canvas :deep(.mango-flow-edge--muted) {
    opacity: 0.16;
  }

  .mango-coverage-flow__canvas :deep(.mango-flow-node--selected rect),
  .mango-coverage-flow__canvas :deep(.mango-flow-node--selected polygon),
  .mango-coverage-flow__canvas :deep(.mango-flow-node--selected circle),
  .mango-coverage-flow__canvas :deep(.mango-flow-node--selected path),
  .mango-coverage-flow__canvas :deep(.mango-flow-edge--selected path) {
    stroke: var(--m-primary) !important;
    stroke-width: 2.2px !important;
  }

  .mango-coverage-flow__empty {
    min-height: 520px;
  }

  .mango-coverage-flow__error {
    margin-bottom: var(--m-page-gap);
  }
</style>
