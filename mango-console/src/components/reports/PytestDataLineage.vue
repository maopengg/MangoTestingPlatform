<template>
  <section class="mango-pytest-lineage">
    <a-alert v-if="lineage.malformed" type="warning">部分血缘数据格式异常，已保留可展示的节点与关系。</a-alert>
    <div class="mango-pytest-lineage__summary">
      <span
        >数据工厂 <strong>{{ summary.factories }}</strong></span
      >
      <span
        >Repository 操作 <strong>{{ summary.operations }}</strong></span
      >
      <span
        >业务实体 <strong>{{ summary.entities }}</strong></span
      >
      <span
        >关系 <strong>{{ summary.relations }}</strong></span
      >
    </div>

    <div class="mango-pytest-lineage__canvas mango-native-scrollbar">
      <svg
        class="mango-pytest-lineage__graph"
        :viewBox="`0 0 ${canvasWidth} ${canvasHeight}`"
        role="img"
        aria-label="Pytest 数据血缘关系图"
      >
        <defs>
          <marker
            :id="markerId"
            markerWidth="8"
            markerHeight="8"
            refX="7"
            refY="3"
            orient="auto"
          >
            <path d="M0,0 L0,6 L8,3 z" class="mango-pytest-lineage__arrow" />
          </marker>
        </defs>

        <g class="mango-pytest-lineage__lanes">
          <template v-for="lane in lanes" :key="lane.kind">
            <rect :x="lane.x" y="12" :width="nodeWidth" height="32" rx="6" />
            <text :x="lane.x + 12" y="33" font-size="12">{{ lane.title }}</text>
          </template>
        </g>

        <g class="mango-pytest-lineage__edges">
          <g v-for="(edge, index) in visibleEdges" :key="`${edge.source}-${edge.target}-${index}`">
            <path :d="edgePath(edge)" :marker-end="`url(#${markerId})`" />
            <text :x="edgeLabelPosition(edge).x" :y="edgeLabelPosition(edge).y" font-size="10">
              {{ edge.relation || '关联' }}
            </text>
          </g>
        </g>

        <g
          v-for="node in positionedNodes"
          :key="node.id"
          class="mango-pytest-lineage__node"
          :class="[
            `mango-pytest-lineage__node--${node.kind}`,
            `mango-pytest-lineage__node--${node.status || 'unknown'}`,
            { active: selectedNodeId === node.id },
          ]"
          :transform="`translate(${node.x}, ${node.y})`"
          role="button"
          tabindex="0"
          :aria-label="`查看血缘节点 ${node.label || node.id}`"
          @click="selectedNodeId = node.id"
          @keydown.enter.prevent="selectedNodeId = node.id"
          @keydown.space.prevent="selectedNodeId = node.id"
        >
          <rect :width="nodeWidth" :height="nodeHeight" rx="8" />
          <circle cx="16" cy="19" r="5" />
          <text x="28" y="23" font-size="12" class="mango-pytest-lineage__node-title">
            {{ compactText(node.label || node.entity_type || node.id, 25) }}
          </text>
          <text x="14" y="47" font-size="10" class="mango-pytest-lineage__node-subtitle">
            {{ nodeSubtitle(node) }}
          </text>
        </g>
      </svg>
    </div>

    <div v-if="selectedNode" class="mango-pytest-lineage__detail">
      <div class="mango-pytest-lineage__detail-head">
        <div>
          <strong>{{ selectedNode.label || selectedNode.id }}</strong>
          <span>{{ kindText(selectedNode.kind) }} · {{ statusText(selectedNode.status) }}</span>
        </div>
        <a-tag size="small">{{ selectedNode.entity_type || selectedNode.kind || '-' }}</a-tag>
      </div>
      <dl>
        <div>
          <dt>来源</dt>
          <dd>{{ selectedNode.source || '-' }}</dd>
        </div>
        <div>
          <dt>实体标识</dt>
          <dd>{{ selectedNode.entity_id ?? '-' }}</dd>
        </div>
      </dl>
      <div class="mango-pytest-lineage__snapshot">
        <h4>节点数据快照</h4>
        <JsonDisplay :data="selectedNode.data" />
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
  import { computed, getCurrentInstance, ref, watch } from 'vue'
  import { readLineage } from './pytest-lineage'
  import type { LineageNode, LineageEdge } from './pytest-lineage'

  type PositionedNode = LineageNode & {
    x: number
    y: number
  }

  const props = defineProps<{
    graph: unknown
  }>()

  const markerId = `mango-pytest-lineage-arrow-${getCurrentInstance()?.uid ?? 'standalone'}`
  const lineage = computed(() => readLineage(props.graph))
  const canvasWidth = 940
  const nodeWidth = 220
  const nodeHeight = 64
  const rowGap = 34
  const laneX = [24, 360, 696]
  const selectedNodeId = ref('')

  const nodes = computed(() => lineage.value.nodes)
  const edges = computed(() => lineage.value.edges)
  const lanes = [
    { kind: 'factory', title: '数据工厂', x: laneX[0] },
    { kind: 'operation', title: 'Repository 操作', x: laneX[1] },
    { kind: 'entity', title: '业务实体', x: laneX[2] },
  ]
  const laneNodes = computed(() =>
    lanes.map((lane) => nodes.value.filter((node) => lineageLevel(node) === lane.kind))
  )
  const canvasHeight = computed(() => {
    const maxCount = Math.max(1, ...laneNodes.value.map((items) => items.length))
    return Math.max(220, 62 + maxCount * (nodeHeight + rowGap))
  })
  const positionedNodes = computed<PositionedNode[]>(() =>
    laneNodes.value.flatMap((items, laneIndex) =>
      items.map((node, index) => ({
        ...node,
        x: laneX[laneIndex],
        y: 62 + index * (nodeHeight + rowGap),
      }))
    )
  )
  const nodePositions = computed(() =>
    new Map(positionedNodes.value.map((node) => [node.id, node]))
  )
  const visibleEdges = computed(() =>
    edges.value.filter(
      (edge) => nodePositions.value.has(edge.source) && nodePositions.value.has(edge.target)
    )
  )
  const selectedNode = computed(
    () => nodes.value.find((node) => node.id === selectedNodeId.value) || null
  )
  const summary = computed(() => ({
    factories:
      lineage.value.summary.factories ??
      nodes.value.filter((node) => lineageLevel(node) === 'factory').length,
    operations:
      lineage.value.summary.operations ??
      nodes.value.filter((node) => lineageLevel(node) === 'operation').length,
    entities:
      lineage.value.summary.entities ??
      nodes.value.filter((node) => lineageLevel(node) === 'entity').length,
    relations: lineage.value.summary.relations ?? edges.value.length,
  }))

  function lineageLevel(node: LineageNode) {
    if (node.kind === 'factory') return 'factory'
    if (node.kind === 'operation') return 'operation'
    return 'entity'
  }

  function edgePath(edge: LineageEdge) {
    const source = nodePositions.value.get(edge.source)
    const target = nodePositions.value.get(edge.target)
    if (!source || !target) return ''
    const forward = target.x >= source.x
    const x1 = source.x + (forward ? nodeWidth : 0)
    const x2 = target.x + (forward ? 0 : nodeWidth)
    const y1 = source.y + nodeHeight / 2
    const y2 = target.y + nodeHeight / 2
    const middleX = (x1 + x2) / 2
    return `M${x1},${y1} C${middleX},${y1} ${middleX},${y2} ${x2},${y2}`
  }

  function edgeLabelPosition(edge: LineageEdge) {
    const source = nodePositions.value.get(edge.source)
    const target = nodePositions.value.get(edge.target)
    if (!source || !target) return { x: 0, y: 0 }
    const forward = target.x >= source.x
    const x1 = source.x + (forward ? nodeWidth : 0)
    const x2 = target.x + (forward ? 0 : nodeWidth)
    return {
      x: (x1 + x2) / 2,
      y: (source.y + target.y) / 2 + nodeHeight / 2 - 6,
    }
  }

  function compactText(value: unknown, maxLength: number) {
    const text = String(value || '-')
    return text.length > maxLength ? `${text.slice(0, maxLength - 1)}…` : text
  }

  function nodeSubtitle(node: LineageNode) {
    const identity = node.entity_id !== null && node.entity_id !== '' ? ` #${node.entity_id}` : ''
    return compactText(`${node.entity_type || kindText(node.kind)}${identity}`, 29)
  }

  function kindText(kind?: string) {
    if (kind === 'factory') return '数据工厂'
    if (kind === 'operation') return 'Repository 操作'
    if (kind === 'entity') return '业务实体'
    return kind || '未知节点'
  }

  function statusText(status?: string) {
    const statusMap: Record<string, string> = {
      passed: '成功',
      failed: '失败',
      active: '有效',
      deleted: '已删除',
      created: '已创建',
    }
    return statusMap[String(status || '')] || status || '未知状态'
  }

  watch(
    nodes,
    (items) => {
      if (!items.some((item) => item.id === selectedNodeId.value)) {
        selectedNodeId.value = items[0]?.id || ''
      }
    },
    { immediate: true, flush: 'sync' }
  )
</script>

<style scoped lang="less">
  .mango-pytest-lineage {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 10px;
  }

  .mango-pytest-lineage__summary {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .mango-pytest-lineage__summary span {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-pytest-lineage__summary strong {
    color: var(--m-text);
    font-size: 13px;
  }

  .mango-pytest-lineage__canvas {
    min-width: 0;
    overflow-x: auto;
    overflow-y: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }

  .mango-pytest-lineage__graph {
    display: block;
    width: 940px;
    min-width: 940px;
    height: auto;
  }

  .mango-pytest-lineage__lanes rect {
    fill: var(--m-surface);
    stroke: var(--m-border);
  }

  .mango-pytest-lineage__lanes text {
    fill: var(--m-text-2);
    font-weight: 600;
  }

  .mango-pytest-lineage__edges path {
    fill: none;
    stroke: var(--m-border-strong);
    stroke-width: 1.5;
  }

  .mango-pytest-lineage__edges text {
    fill: var(--m-muted);
    text-anchor: middle;
  }

  .mango-pytest-lineage__arrow {
    fill: var(--m-border-strong);
  }

  .mango-pytest-lineage__node {
    cursor: pointer;
  }

  .mango-pytest-lineage__node rect {
    fill: var(--m-surface);
    stroke: var(--m-border-strong);
    stroke-width: 1.2;
    transition: fill var(--m-motion-duration-fast), stroke var(--m-motion-duration-fast);
  }

  .mango-pytest-lineage__node circle {
    fill: var(--m-primary);
  }

  .mango-pytest-lineage__node:hover rect,
  .mango-pytest-lineage__node:focus rect,
  .mango-pytest-lineage__node.active rect {
    fill: var(--m-primary-soft);
    stroke: var(--m-primary);
    stroke-width: 2;
  }

  .mango-pytest-lineage__node--factory circle {
    fill: var(--m-primary);
  }

  .mango-pytest-lineage__node--operation circle {
    fill: var(--m-warning);
  }

  .mango-pytest-lineage__node--entity circle,
  .mango-pytest-lineage__node--passed circle,
  .mango-pytest-lineage__node--active circle {
    fill: var(--m-success);
  }

  .mango-pytest-lineage__node--failed circle,
  .mango-pytest-lineage__node--deleted circle {
    fill: var(--m-danger);
  }

  .mango-pytest-lineage__node-title {
    fill: var(--m-text);
    font-weight: 600;
  }

  .mango-pytest-lineage__node-subtitle {
    fill: var(--m-muted);
  }

  .mango-pytest-lineage__detail {
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .mango-pytest-lineage__detail-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 10px;
  }

  .mango-pytest-lineage__detail-head > div {
    display: flex;
    min-width: 0;
    flex-direction: column;
  }

  .mango-pytest-lineage__detail-head strong {
    overflow: hidden;
    color: var(--m-text);
    font-size: 14px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-pytest-lineage__detail-head span,
  .mango-pytest-lineage__detail dt {
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-pytest-lineage__detail dl {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
    margin: 0 0 12px;
  }

  .mango-pytest-lineage__detail dl > div {
    min-width: 0;
    padding: 8px 10px;
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }

  .mango-pytest-lineage__detail dd {
    margin: 3px 0 0;
    overflow: hidden;
    color: var(--m-text);
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-pytest-lineage__snapshot h4 {
    margin: 0 0 7px;
    color: var(--m-text);
    font-size: 13px;
  }

  @media (max-width: 760px) {
    .mango-pytest-lineage__detail dl {
      grid-template-columns: 1fr;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .mango-pytest-lineage__node rect {
      transition: none;
    }
  }
</style>
