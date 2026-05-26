<template>
  <div class="mango-relation-flow-shell" :style="{ height: resolvedHeight }">
    <div v-if="showHeader" class="mango-relation-flow-header">
      <div class="mango-relation-flow-heading">
        <div class="mango-relation-flow-title">{{ title }}</div>
        <div v-if="subtitle" class="mango-relation-flow-subtitle">{{ subtitle }}</div>
      </div>
      <div class="mango-relation-flow-actions">
        <div class="mango-relation-flow-legend">
          <span><i class="legend-line legend-line-scene"></i>场景编排</span>
          <span><i class="legend-line legend-line-field"></i>字段依赖</span>
          <span><i class="legend-line legend-line-reuse"></i>复用</span>
        </div>
        <a-button
          v-if="showDownload"
          size="mini"
          type="primary"
          :loading="downloadLoading"
          :disabled="!flowNodes.length"
          @click="downloadImage"
        >
          下载为图片
        </a-button>
        <slot name="extra"></slot>
      </div>
    </div>
    <a-spin :loading="flowLoading" class="mango-relation-flow-spin" tip="依赖关系加载中...">
      <div v-if="!focusedDependencyTree" class="mango-empty-state mango-relation-flow-empty">
        暂无依赖关系
      </div>
      <div v-else ref="flowCanvasRef" class="mango-relation-flow-canvas">
        <VueFlow
          :id="flowId"
          v-model:nodes="flowNodes"
          v-model:edges="flowEdges"
          class="mango-relation-flow"
          :nodes-draggable="false"
          :nodes-connectable="false"
          :elements-selectable="true"
          :min-zoom="0.25"
          :max-zoom="1.2"
          @pane-ready="onFlowPaneReady"
          @nodes-initialized="onFlowNodesInitialized"
          @node-click="onNodeClick"
        >
          <template #node-tableNode="{ data }">
            <div
              :class="[
                'mango-relation-table-node',
                `mango-relation-table-node-${data.status || 'valid'}`,
                { 'mango-relation-table-node-selected': selectedNodeId === data.nodeId },
                { 'mango-relation-table-node-disabled': !data.clickable },
              ]"
            >
              <div class="mango-relation-node-header">
                <a-tag :color="data.typeColor" size="small">{{ data.typeText }}</a-tag>
                <a-tag v-if="data.reused" color="blue" size="small">复用</a-tag>
                <a-tag v-else :color="getNodeStatusColor(data.status)" size="small">
                  {{ getNodeStatusText(data.status, data.missingCount) }}
                </a-tag>
              </div>
              <div class="mango-relation-node-title">{{ data.title }}</div>
              <div class="mango-relation-node-template">{{ data.templateName || '-' }}</div>
              <div class="mango-relation-node-table">{{ data.tableName || '-' }}</div>
              <div v-if="data.linkText" class="mango-relation-node-link">{{ data.linkText }}</div>
            </div>
          </template>
          <Background pattern-color="var(--m-border)" :gap="18" />
          <MiniMap v-if="showMiniMap" class="mango-relation-flow-minimap" pannable zoomable />
          <Controls />
        </VueFlow>
      </div>
    </a-spin>
  </div>
</template>

<script lang="ts" setup>
  import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { VueFlow, useVueFlow } from '@vue-flow/core'
  import type { Edge, Node } from '@vue-flow/core'
  import { Background, Controls, MiniMap } from '@vue-flow/additional-components'
  import '@vue-flow/core/dist/style.css'
  import '@vue-flow/core/dist/theme-default.css'

  interface PreviewNode {
    template_id?: number | null
    template_name?: string
    entity_id?: number | null
    entity_name?: string
    table_name?: string
    alias?: string
    field?: string
    target_field?: string
    action?: string
    reused?: boolean
    scene_item_id?: number | string
    scene_item_name?: string
    status?: string
    missing_count?: number
    fields?: any[]
    missing_fields?: any[]
    children?: PreviewNode[]
  }

  const props = withDefaults(
    defineProps<{
      dependencyTree?: PreviewNode | null
      focusNodeKey?: string
      editableRoot?: boolean
      flowLoading?: boolean
      title?: string
      subtitle?: string
      height?: string
      showHeader?: boolean
      initialMaxZoom?: number
      showDownload?: boolean
      downloadName?: string
      showMiniMap?: boolean
    }>(),
    {
      dependencyTree: null,
      focusNodeKey: 'root',
      editableRoot: false,
      flowLoading: false,
      title: '依赖关系',
      subtitle: '',
      height: '100%',
      showHeader: true,
      initialMaxZoom: 0.62,
      showDownload: false,
      downloadName: 'data-factory-relation-flow',
      showMiniMap: false,
    }
  )

  const emit = defineEmits<{
    (event: 'selectNode', value: { id: string; node?: PreviewNode }): void
  }>()

  const selectedNodeId = ref('')
  const flowNodes = ref<Node[]>([])
  const flowEdges = ref<Edge[]>([])
  const flowCanvasRef = ref<HTMLElement>()
  const flowPaneReady = ref(false)
  const fitFrameId = ref<number>()
  const fitTimerId = ref<number>()
  const downloadLoading = ref(false)
  const flowId = `mango-data-factory-relation-flow-${Math.random().toString(36).slice(2)}`
  const NODE_WIDTH = 218
  const NODE_HEIGHT = 118
  const LEVEL_GAP = 360
  const ROW_GAP = 190

  const resolvedHeight = computed(() => props.height || '100%')
  const focusedDependencyTree = computed(() => {
    return (
      findNodeByEditableKey(props.dependencyTree, props.focusNodeKey || 'root') ||
      props.dependencyTree
    )
  })
  const nodeMap = computed(() => {
    const map = new Map<string, PreviewNode>()
    flattenTree(focusedDependencyTree.value).forEach((item) => map.set(item.id, item.node))
    return map
  })
  const { fitView, areNodesInitialized } = useVueFlow(flowId)

  watch(
    () => props.dependencyTree,
    () => {
      buildFlow()
      scheduleFitView()
    },
    { immediate: true, deep: true }
  )

  watch(
    () => props.focusNodeKey,
    () => {
      buildFlow()
      scheduleFitView()
    }
  )

  watch(
    () => props.flowLoading,
    (loading) => {
      if (!loading) {
        scheduleFitView()
      }
    }
  )

  watch(areNodesInitialized, (ready) => {
    if (ready) {
      scheduleFitView()
    }
  })

  onBeforeUnmount(() => {
    cancelScheduledFitView()
  })

  function onFlowPaneReady() {
    flowPaneReady.value = true
    scheduleFitView()
  }

  function onFlowNodesInitialized() {
    scheduleFitView()
  }

  function cancelScheduledFitView() {
    if (fitFrameId.value) {
      window.cancelAnimationFrame(fitFrameId.value)
      fitFrameId.value = undefined
    }
    if (fitTimerId.value) {
      window.clearTimeout(fitTimerId.value)
      fitTimerId.value = undefined
    }
  }

  function scheduleFitView(retry = 0) {
    cancelScheduledFitView()
    nextTick(() => {
      fitFrameId.value = window.requestAnimationFrame(() => {
        const rect = flowCanvasRef.value?.getBoundingClientRect()
        const canFit =
          flowPaneReady.value &&
          areNodesInitialized.value &&
          flowNodes.value.length > 0 &&
          rect &&
          rect.width > 80 &&
          rect.height > 80

        if (!canFit) {
          if (retry < 8) {
            fitTimerId.value = window.setTimeout(() => scheduleFitView(retry + 1), 80)
          }
          return
        }

        fitView({
          padding: 0.38,
          maxZoom: props.initialMaxZoom,
          duration: retry ? 0 : 180,
        })

        if (retry === 0) {
          fitTimerId.value = window.setTimeout(() => scheduleFitView(1), 120)
        }
      })
    })
  }

  function buildFlow() {
    const nodes: Node[] = []
    const edges: Edge[] = []
    let leafIndex = 0

    interface LayoutNode {
      id: string
      node: PreviewNode
      level: number
      y: number
      children: LayoutNode[]
    }

    function layout(node: PreviewNode, level = 0, indexPath = '0'): LayoutNode {
      const id = buildNodeId(node, indexPath)
      const children = (node.children || []).map((child, childIndex) =>
        layout(child, level + 1, `${indexPath}-${childIndex}`)
      )
      const y = children.length
        ? (children[0].y + children[children.length - 1].y) / 2
        : leafIndex++ * ROW_GAP
      return {
        id,
        node,
        level,
        y,
        children,
      }
    }

    function walk(layoutNode: LayoutNode) {
      const { id, node, level, y } = layoutNode
      nodes.push({
        id,
        type: 'tableNode',
        position: { x: level * LEVEL_GAP, y },
        selectable: node.action !== 'reuse' && !node.reused,
        data: {
          nodeId: id,
          templateName: node.template_name || node.alias || '-',
          entityName: node.entity_name || node.alias || '-',
          tableName: node.table_name || '',
          title: getNodeTitle(node),
          typeText: getNodeTypeText(node),
          typeColor: getNodeTypeColor(node),
          status: node.status || 'valid',
          missingCount: node.missing_count || 0,
          clickable: node.action !== 'reuse' && !node.reused,
          reused: node.action === 'reuse' || node.reused,
          linkText: node.field ? `${node.field} -> ${node.target_field || 'id'}` : '',
        },
      })
      layoutNode.children.forEach((childLayout) => {
        const child = childLayout.node
        edges.push({
          id: `${id}-${childLayout.id}`,
          source: id,
          target: childLayout.id,
          label: getEdgeLabel(child),
          type: 'default',
          animated: false,
          class: getEdgeClass(child),
          style: getEdgeStyle(child),
          labelStyle: { fill: 'var(--m-text-2)', fontSize: 12 },
          labelBgStyle: { fill: 'var(--m-surface)', fillOpacity: 0.85 },
        })
        walk(childLayout)
      })
    }

    if (focusedDependencyTree.value) {
      walk(layout(focusedDependencyTree.value))
    }
    flowNodes.value = nodes
    flowEdges.value = edges
    selectedNodeId.value = nodes.some((node) => node.id === selectedNodeId.value)
      ? selectedNodeId.value
      : nodes[0]?.id || ''
    emitSelectedNode()
  }

  function flattenTree(
    tree?: PreviewNode | null,
    indexPath = '0'
  ): Array<{ id: string; node: PreviewNode }> {
    if (!tree) {
      return []
    }
    const id = buildNodeId(tree, indexPath)
    return [
      { id, node: tree },
      ...(tree.children || []).flatMap((child, index) =>
        flattenTree(child, `${indexPath}-${index}`)
      ),
    ]
  }

  function buildNodeId(node: PreviewNode, indexPath: string) {
    return `node-${
      node.scene_item_id || node.template_id || node.entity_id || node.alias || indexPath
    }-${indexPath}`
  }

  function getEditableNodeKey(node?: PreviewNode | null) {
    if (!node) {
      return ''
    }
    if (node.action === 'root' && props.editableRoot) {
      return 'root'
    }
    if (node.scene_item_id !== undefined && node.scene_item_id !== null) {
      return `item:${node.scene_item_id}`
    }
    return ''
  }

  function findNodeByEditableKey(tree?: PreviewNode | null, key = 'root'): PreviewNode | null {
    if (!tree) {
      return null
    }
    if (getEditableNodeKey(tree) === key) {
      return tree
    }
    for (const child of tree.children || []) {
      const found = findNodeByEditableKey(child, key)
      if (found) {
        return found
      }
    }
    return null
  }

  function onNodeClick(event: any) {
    if (!event.node?.data?.clickable) {
      return
    }
    selectedNodeId.value = event.node?.id || ''
    emitSelectedNode()
  }

  function emitSelectedNode() {
    emit('selectNode', {
      id: selectedNodeId.value,
      node: nodeMap.value.get(selectedNodeId.value),
    })
  }

  function getNodeStatusColor(status?: string) {
    if (status === 'warning') {
      return 'orange'
    }
    if (status === 'error') {
      return 'red'
    }
    return 'green'
  }

  function getNodeStatusText(status?: string, missingCount?: number) {
    if (status === 'warning') {
      return `缺 ${missingCount || 0} 项`
    }
    if (status === 'error') {
      return '异常'
    }
    return '可生成'
  }

  function getNodeTitle(node: PreviewNode) {
    if (node.scene_item_name) {
      return node.scene_item_name
    }
    return node.entity_name || node.alias || node.template_name || '-'
  }

  function getNodeTypeText(node: PreviewNode) {
    if (node.action === 'root') {
      return '主场景'
    }
    if (node.scene_item_id !== undefined && node.scene_item_id !== null) {
      return '关联模板'
    }
    if (node.reused || node.action === 'reuse') {
      return '复用数据'
    }
    if (node.field) {
      return '字段依赖'
    }
    return '依赖模板'
  }

  function getNodeTypeColor(node: PreviewNode) {
    if (node.action === 'root') {
      return 'arcoblue'
    }
    if (node.scene_item_id !== undefined && node.scene_item_id !== null) {
      return 'purple'
    }
    if (node.reused || node.action === 'reuse') {
      return 'blue'
    }
    if (node.field) {
      return 'gray'
    }
    return 'cyan'
  }

  function getEdgeLabel(node: PreviewNode) {
    if (node.scene_item_id !== undefined && node.scene_item_id !== null) {
      return '场景编排'
    }
    if (node.field) {
      return `${node.field} -> ${node.target_field || 'id'}`
    }
    if (node.reused || node.action === 'reuse') {
      return '复用已有数据'
    }
    return '依赖创建'
  }

  function getEdgeStyle(node: PreviewNode) {
    if (node.reused || node.action === 'reuse') {
      return {
        stroke: 'var(--m-success)',
        strokeWidth: 2.8,
        strokeDasharray: '1 8',
        strokeLinecap: 'round',
      }
    }
    if (node.scene_item_id !== undefined && node.scene_item_id !== null) {
      return {
        stroke: 'var(--m-primary)',
        strokeWidth: 3,
      }
    }
    if (node.field) {
      return {
        stroke: 'var(--m-danger)',
        strokeWidth: 2.8,
        strokeDasharray: '9 6',
      }
    }
    return {
      stroke: 'var(--m-warning)',
      strokeWidth: 2.6,
      strokeDasharray: '14 6',
    }
  }

  function getEdgeClass(node: PreviewNode) {
    if (node.reused || node.action === 'reuse') {
      return 'mango-relation-edge-reuse'
    }
    if (node.scene_item_id !== undefined && node.scene_item_id !== null) {
      return 'mango-relation-edge-scene'
    }
    if (node.field) {
      return 'mango-relation-edge-field'
    }
    return 'mango-relation-edge-dependency'
  }

  async function downloadImage() {
    if (!flowNodes.value.length) {
      Message.warning('暂无可下载的流程图')
      return
    }
    downloadLoading.value = true
    try {
      await nextTick()
      let pngBlob: Blob
      try {
        pngBlob = await buildDomSnapshotPng()
      } catch (error) {
        pngBlob = await buildCanvasFallbackPng()
      }
      downloadBlob(pngBlob, `${sanitizeFileName(props.downloadName)}.png`)
      Message.success('流程图 PNG 已下载')
    } catch (error) {
      Message.error('流程图 PNG 生成失败')
    } finally {
      downloadLoading.value = false
    }
  }

  async function buildDomSnapshotPng() {
    const svg = buildDomSnapshotSvg()
    const svgBlob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(svgBlob)
    try {
      const image = new Image()
      image.crossOrigin = 'anonymous'
      await new Promise<void>((resolve, reject) => {
        image.onload = () => resolve()
        image.onerror = () => reject(new Error('image load failed'))
        image.src = url
      })
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 2)
      const canvas = document.createElement('canvas')
      canvas.width = Math.max(Math.floor(image.width * pixelRatio), 1)
      canvas.height = Math.max(Math.floor(image.height * pixelRatio), 1)
      const context = canvas.getContext('2d')
      if (!context) {
        throw new Error('canvas context unavailable')
      }
      context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)
      context.drawImage(image, 0, 0)
      return canvasToBlob(canvas)
    } finally {
      URL.revokeObjectURL(url)
    }
  }

  function buildDomSnapshotSvg() {
    const target = flowCanvasRef.value
    if (!target) {
      throw new Error('flow canvas unavailable')
    }
    const rect = target.getBoundingClientRect()
    const width = Math.max(Math.ceil(rect.width), 1)
    const height = Math.max(Math.ceil(rect.height), 1)
    const clone = target.cloneNode(true) as HTMLElement
    clone.setAttribute('xmlns', 'http://www.w3.org/1999/xhtml')
    clone.style.width = `${width}px`
    clone.style.height = `${height}px`
    clone.style.margin = '0'
    clone.style.overflow = 'hidden'
    inlineComputedStyles(target, clone)
    const html = new XMLSerializer().serializeToString(clone)
    return `
      <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
        <foreignObject x="0" y="0" width="100%" height="100%">
          ${html}
        </foreignObject>
      </svg>
    `
  }

  function inlineComputedStyles(source: Element, clone: Element) {
    const computedStyle = window.getComputedStyle(source)
    const cloneElement = clone as HTMLElement
    for (let index = 0; index < computedStyle.length; index += 1) {
      const property = computedStyle[index]
      cloneElement.style.setProperty(
        property,
        computedStyle.getPropertyValue(property),
        computedStyle.getPropertyPriority(property)
      )
    }
    Array.from(source.children).forEach((child, index) => {
      const clonedChild = clone.children[index]
      if (clonedChild) {
        inlineComputedStyles(child, clonedChild)
      }
    })
  }

  async function buildCanvasFallbackPng() {
    const nodeWidth = NODE_WIDTH
    const nodeHeight = NODE_HEIGHT
    const padding = 56
    const bounds = flowNodes.value.reduce(
      (result, node) => {
        result.minX = Math.min(result.minX, node.position.x)
        result.minY = Math.min(result.minY, node.position.y)
        result.maxX = Math.max(result.maxX, node.position.x + nodeWidth)
        result.maxY = Math.max(result.maxY, node.position.y + nodeHeight)
        return result
      },
      {
        minX: Number.POSITIVE_INFINITY,
        minY: Number.POSITIVE_INFINITY,
        maxX: Number.NEGATIVE_INFINITY,
        maxY: Number.NEGATIVE_INFINITY,
      }
    )
    const width = Math.max(Math.ceil(bounds.maxX - bounds.minX + padding * 2), 760)
    const height = Math.max(Math.ceil(bounds.maxY - bounds.minY + padding * 2), 420)
    const pixelRatio = Math.min(window.devicePixelRatio || 1, 2)
    const canvas = document.createElement('canvas')
    canvas.width = Math.floor(width * pixelRatio)
    canvas.height = Math.floor(height * pixelRatio)
    canvas.style.width = `${width}px`
    canvas.style.height = `${height}px`
    const context = canvas.getContext('2d')
    if (!context) {
      throw new Error('canvas context unavailable')
    }
    context.scale(pixelRatio, pixelRatio)
    const tokens = getCanvasTokens()
    const offsetX = padding - bounds.minX
    const offsetY = padding - bounds.minY
    context.fillStyle = tokens.surfaceSoft
    context.fillRect(0, 0, width, height)
    drawGrid(context, width, height, tokens.border)
    const nodeLookup = new Map(flowNodes.value.map((node) => [node.id, node]))
    flowEdges.value.forEach((edge) => {
      const source = nodeLookup.get(edge.source)
      const target = nodeLookup.get(edge.target)
      if (!source || !target) {
        return
      }
      drawCanvasEdge(context, edge, source, target, offsetX, offsetY, nodeWidth, nodeHeight, tokens)
    })
    flowNodes.value.forEach((node) => {
      drawCanvasNode(context, node, offsetX, offsetY, nodeWidth, nodeHeight, tokens)
    })
    return canvasToBlob(canvas)
  }

  function drawGrid(context: CanvasRenderingContext2D, width: number, height: number, color: string) {
    context.save()
    context.strokeStyle = color
    context.globalAlpha = 0.42
    context.lineWidth = 1
    for (let x = 0; x <= width; x += 18) {
      context.beginPath()
      context.moveTo(x, 0)
      context.lineTo(x, height)
      context.stroke()
    }
    for (let y = 0; y <= height; y += 18) {
      context.beginPath()
      context.moveTo(0, y)
      context.lineTo(width, y)
      context.stroke()
    }
    context.restore()
  }

  function drawCanvasEdge(
    context: CanvasRenderingContext2D,
    edge: Edge,
    source: Node,
    target: Node,
    offsetX: number,
    offsetY: number,
    nodeWidth: number,
    nodeHeight: number,
    tokens: ReturnType<typeof getCanvasTokens>
  ) {
    const sourceX = source.position.x + offsetX + nodeWidth
    const sourceY = source.position.y + offsetY + nodeHeight / 2
    const targetX = target.position.x + offsetX
    const targetY = target.position.y + offsetY + nodeHeight / 2
    const middleX = sourceX + Math.max((targetX - sourceX) / 2, 48)
    const edgeClass = String(edge.class || '')
    const color = edgeClass.includes('reuse')
      ? tokens.success
      : edgeClass.includes('field')
      ? tokens.danger
      : edgeClass.includes('dependency')
      ? tokens.warning
      : tokens.primary
    context.save()
    context.strokeStyle = color
    context.lineWidth = edgeClass.includes('scene') ? 3 : 2.8
    context.setLineDash(
      edgeClass.includes('reuse')
        ? [1, 8]
        : edgeClass.includes('field')
        ? [9, 6]
        : edgeClass.includes('dependency')
        ? [14, 6]
        : []
    )
    context.lineCap = edgeClass.includes('reuse') ? 'round' : 'butt'
    context.beginPath()
    context.moveTo(sourceX, sourceY)
    context.bezierCurveTo(middleX, sourceY, middleX, targetY, targetX, targetY)
    context.stroke()
    drawEdgeLabel(context, String(edge.label || ''), (sourceX + targetX) / 2, (sourceY + targetY) / 2 - 10, tokens)
    context.restore()
  }

  function drawEdgeLabel(
    context: CanvasRenderingContext2D,
    label: string,
    x: number,
    y: number,
    tokens: ReturnType<typeof getCanvasTokens>
  ) {
    if (!label) {
      return
    }
    context.save()
    context.font = '12px sans-serif'
    const textWidth = context.measureText(label).width
    const width = textWidth + 16
    roundRect(context, x - width / 2, y - 12, width, 22, 6)
    context.fillStyle = tokens.surface
    context.globalAlpha = 0.9
    context.fill()
    context.globalAlpha = 1
    context.fillStyle = tokens.text2
    context.textAlign = 'center'
    context.textBaseline = 'middle'
    context.fillText(label, x, y)
    context.restore()
  }

  function drawCanvasNode(
    context: CanvasRenderingContext2D,
    node: Node,
    offsetX: number,
    offsetY: number,
    width: number,
    height: number,
    tokens: ReturnType<typeof getCanvasTokens>
  ) {
    const data: any = node.data || {}
    const x = node.position.x + offsetX
    const y = node.position.y + offsetY
    const statusColor = getCanvasStatusColor(data.status, tokens)
    const typeColor = getCanvasTypeColor(data.typeColor, tokens)
    context.save()
    context.shadowColor = tokens.shadow
    context.shadowBlur = 10
    context.shadowOffsetY = 2
    roundRect(context, x, y, width, height, 8)
    context.fillStyle = tokens.surface
    context.fill()
    context.shadowColor = 'transparent'
    context.lineWidth = selectedNodeId.value === node.id ? 2 : 1
    context.strokeStyle = selectedNodeId.value === node.id ? tokens.primary : statusColor
    context.stroke()
    drawPill(context, data.typeText || '', x + 12, y + 12, 64, 22, typeColor)
    drawPill(context, getNodeStatusText(data.status, data.missingCount), x + width - 74, y + 12, 62, 22, statusColor)
    context.fillStyle = tokens.text
    context.font = '600 14px sans-serif'
    context.textAlign = 'left'
    context.textBaseline = 'alphabetic'
    context.fillText(truncateText(data.title || '-', 18), x + 12, y + 56)
    context.fillStyle = tokens.text2
    context.font = '12px sans-serif'
    context.fillText(truncateText(data.templateName || '-', 24), x + 12, y + 78)
    context.fillText(truncateText(data.tableName || '-', 24), x + 12, y + 98)
    context.restore()
  }

  function drawPill(
    context: CanvasRenderingContext2D,
    text: string,
    x: number,
    y: number,
    width: number,
    height: number,
    color: string
  ) {
    context.save()
    context.globalAlpha = 0.14
    roundRect(context, x, y, width, height, 6)
    context.fillStyle = color
    context.fill()
    context.globalAlpha = 1
    context.fillStyle = color
    context.font = '600 12px sans-serif'
    context.textAlign = 'center'
    context.textBaseline = 'middle'
    context.fillText(truncateText(text, 5), x + width / 2, y + height / 2 + 1)
    context.restore()
  }

  function roundRect(
    context: CanvasRenderingContext2D,
    x: number,
    y: number,
    width: number,
    height: number,
    radius: number
  ) {
    context.beginPath()
    context.moveTo(x + radius, y)
    context.lineTo(x + width - radius, y)
    context.quadraticCurveTo(x + width, y, x + width, y + radius)
    context.lineTo(x + width, y + height - radius)
    context.quadraticCurveTo(x + width, y + height, x + width - radius, y + height)
    context.lineTo(x + radius, y + height)
    context.quadraticCurveTo(x, y + height, x, y + height - radius)
    context.lineTo(x, y + radius)
    context.quadraticCurveTo(x, y, x + radius, y)
    context.closePath()
  }

  function getCanvasTokens() {
    const style = getComputedStyle(flowCanvasRef.value || document.documentElement)
    return {
      surface: readCssToken(style, '--m-surface', '#ffffff'),
      surfaceSoft: readCssToken(style, '--m-surface-soft', '#f7f8fa'),
      text: readCssToken(style, '--m-text', '#1d2129'),
      text2: readCssToken(style, '--m-text-2', '#4e5969'),
      primary: readCssToken(style, '--m-primary', '#165dff'),
      success: readCssToken(style, '--m-success', '#00b42a'),
      warning: readCssToken(style, '--m-warning', '#ff7d00'),
      danger: readCssToken(style, '--m-danger', '#f53f3f'),
      border: readCssToken(style, '--m-border', '#e5e6eb'),
      shadow: 'rgba(0, 0, 0, 0.12)',
    }
  }

  function readCssToken(style: CSSStyleDeclaration, token: string, fallback: string) {
    return style.getPropertyValue(token).trim() || fallback
  }

  function getCanvasStatusColor(status: string | undefined, tokens: ReturnType<typeof getCanvasTokens>) {
    if (status === 'warning') {
      return tokens.warning
    }
    if (status === 'error') {
      return tokens.danger
    }
    return tokens.success
  }

  function getCanvasTypeColor(color: string | undefined, tokens: ReturnType<typeof getCanvasTokens>) {
    if (color === 'purple') {
      return tokens.danger
    }
    if (color === 'blue') {
      return tokens.success
    }
    if (color === 'gray') {
      return tokens.text2
    }
    if (color === 'cyan') {
      return tokens.warning
    }
    return tokens.primary
  }

  function truncateText(value: string, maxLength: number) {
    return value.length > maxLength ? `${value.slice(0, maxLength - 1)}...` : value
  }

  function canvasToBlob(canvas: HTMLCanvasElement) {
    return new Promise<Blob>((resolve, reject) => {
      canvas.toBlob((blob) => {
        if (blob) {
          resolve(blob)
        } else {
          reject(new Error('canvas toBlob failed'))
        }
      }, 'image/png')
    })
  }

  function downloadBlob(blob: Blob, fileName: string) {
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = fileName
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  function escapeSvg(value: string) {
    return value
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;')
  }

  function sanitizeFileName(value: string) {
    return (value || 'data-factory-relation-flow').replace(/[\\/:*?"<>|]/g, '_')
  }
</script>

<style scoped lang="less">
  .mango-relation-flow-shell {
    display: flex;
    overflow: hidden;
    flex-direction: column;
    min-height: 0;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .mango-relation-flow-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-height: 58px;
    padding: 10px 12px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-relation-flow-heading {
    min-width: 0;
  }

  .mango-relation-flow-title {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }

  .mango-relation-flow-subtitle {
    overflow: hidden;
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-relation-flow-actions {
    display: flex;
    align-items: center;
    flex-shrink: 0;
    gap: 10px;
  }

  .mango-relation-flow-legend {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 8px 10px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-relation-flow-legend span {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    white-space: nowrap;
  }

  .legend-line {
    display: inline-block;
    width: 18px;
    height: 0;
    border-top: 2px solid var(--m-muted);
  }

  .legend-line-scene {
    border-color: var(--m-primary);
  }

  .legend-line-field {
    border-color: var(--m-danger);
    border-top-style: dashed;
  }

  .legend-line-reuse {
    border-color: var(--m-success);
    border-top-style: dotted;
  }

  .mango-relation-flow-spin {
    display: block;
    flex: 1;
    height: 100%;
    min-height: 0;
  }

  .mango-relation-flow-spin :deep(.arco-spin),
  .mango-relation-flow-spin :deep(.arco-spin-children) {
    height: 100%;
    min-height: 0;
  }

  .mango-relation-flow-canvas {
    flex: 1;
    height: 100%;
    min-height: 0;
  }

  .mango-relation-flow-empty {
    height: 100%;
    min-height: 180px;
  }

  .mango-relation-flow {
    width: 100%;
    height: 100%;
    background: linear-gradient(
        180deg,
        color-mix(in srgb, var(--m-surface) 72%, transparent),
        color-mix(in srgb, var(--m-surface-soft) 85%, transparent)
      ),
      var(--m-surface-soft);
  }

  .mango-relation-flow :deep(.mango-relation-edge-scene .vue-flow__edge-path) {
    stroke: var(--m-primary) !important;
    stroke-dasharray: none !important;
    stroke-width: 3 !important;
  }

  .mango-relation-flow :deep(.mango-relation-edge-field .vue-flow__edge-path) {
    stroke: var(--m-danger) !important;
    stroke-dasharray: 9 6 !important;
    stroke-width: 2.8 !important;
  }

  .mango-relation-flow :deep(.mango-relation-edge-reuse .vue-flow__edge-path) {
    stroke: var(--m-success) !important;
    stroke-dasharray: 1 8 !important;
    stroke-linecap: round;
    stroke-width: 2.8 !important;
  }

  .mango-relation-flow :deep(.mango-relation-edge-dependency .vue-flow__edge-path) {
    stroke: var(--m-warning) !important;
    stroke-dasharray: 14 6 !important;
    stroke-width: 2.6 !important;
  }

  .mango-relation-flow-minimap {
    right: 14px;
    bottom: 14px;
    width: 180px;
    height: 118px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    box-shadow: var(--m-shadow);
  }

  .mango-relation-flow-minimap :deep(.vue-flow__minimap-mask) {
    fill: color-mix(in srgb, var(--m-primary) 12%, transparent);
    stroke: var(--m-primary);
  }

  .mango-relation-flow-minimap :deep(.vue-flow__minimap-node) {
    fill: var(--m-surface-soft);
    stroke: var(--m-border-strong);
  }

  .mango-relation-table-node {
    width: 218px;
    padding: 10px 11px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    cursor: pointer;
    box-shadow: var(--m-shadow);
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }

  .mango-relation-table-node-selected {
    border-color: var(--m-primary);
    box-shadow: var(--m-form-focus-shadow);
  }

  .mango-relation-table-node-disabled {
    cursor: not-allowed;
    opacity: 0.72;
  }

  .mango-relation-table-node-warning {
    border-color: var(--m-warning);
  }

  .mango-relation-table-node-error {
    border-color: var(--m-danger);
  }

  .mango-relation-node-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .mango-relation-node-title {
    overflow: hidden;
    margin-top: 8px;
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-relation-node-table,
  .mango-relation-node-template,
  .mango-relation-node-link {
    overflow: hidden;
    margin-top: 4px;
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-relation-node-link {
    display: inline-flex;
    max-width: 100%;
    padding: 1px 6px;
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
    color: var(--m-primary);
  }
</style>
