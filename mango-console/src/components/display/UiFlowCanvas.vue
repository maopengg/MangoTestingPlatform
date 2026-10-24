<template>
  <VueFlow
    :id="id"
    v-model:nodes="nodesModel"
    v-model:edges="edgesModel"
    :nodes-draggable="nodesDraggable"
    :nodes-connectable="nodesConnectable"
    :elements-selectable="elementsSelectable"
    :connection-mode="connectionMode"
    :delete-key-code="null"
    :min-zoom="minZoom"
    :max-zoom="maxZoom"
    class="mango-ui-flow-canvas"
    @connect="emit('connect', $event)"
    @node-click="emit('nodeClick', $event)"
    @edge-click="emit('edgeClick', $event)"
    @node-drag-stop="emit('nodeDragStop', $event)"
  >
    <template #node-uiStepNode="slotProps">
      <slot name="node-uiStepNode" v-bind="slotProps"></slot>
    </template>
    <template #node-resultNode="slotProps">
      <slot name="node-resultNode" v-bind="slotProps"></slot>
    </template>
    <Background v-if="showBackground" pattern-color="var(--m-border)" :gap="backgroundGap" />
    <MiniMap v-if="showMiniMap" pannable zoomable />
    <Controls v-if="showControls" />
  </VueFlow>
</template>

<script lang="ts" setup>
  import { computed } from 'vue'
  import { ConnectionMode, VueFlow } from '@vue-flow/core'
  import type {
    Connection,
    Edge,
    EdgeMouseEvent,
    Node,
    NodeDragEvent,
    NodeMouseEvent,
  } from '@vue-flow/core'
  import { Background, Controls, MiniMap } from '@vue-flow/additional-components'
  import { UI_FLOW_MAX_ZOOM, UI_FLOW_MIN_ZOOM } from './ui-flow'
  import '@vue-flow/core/dist/style.css'
  import '@vue-flow/core/dist/theme-default.css'

  const props = withDefaults(
    defineProps<{
      id: string
      nodes: Node[]
      edges: Edge[]
      nodesDraggable?: boolean
      nodesConnectable?: boolean
      elementsSelectable?: boolean
      connectionMode?: ConnectionMode
      minZoom?: number
      maxZoom?: number
      showBackground?: boolean
      backgroundGap?: number
      showMiniMap?: boolean
      showControls?: boolean
    }>(),
    {
      nodesDraggable: false,
      nodesConnectable: false,
      elementsSelectable: true,
      connectionMode: ConnectionMode.Loose,
      minZoom: UI_FLOW_MIN_ZOOM,
      maxZoom: UI_FLOW_MAX_ZOOM,
      showBackground: true,
      backgroundGap: 18,
      showMiniMap: true,
      showControls: true,
    }
  )

  const emit = defineEmits<{
    (event: 'update:nodes', nodes: Node[]): void
    (event: 'update:edges', edges: Edge[]): void
    (event: 'connect', connection: Connection): void
    (event: 'nodeClick', nodeEvent: NodeMouseEvent): void
    (event: 'edgeClick', edgeEvent: EdgeMouseEvent): void
    (event: 'nodeDragStop', dragEvent: NodeDragEvent): void
  }>()

  const nodesModel = computed({
    get: () => props.nodes,
    set: (value) => emit('update:nodes', value),
  })
  const edgesModel = computed({
    get: () => props.edges,
    set: (value) => emit('update:edges', value),
  })
</script>

<style scoped>
  .mango-ui-flow-canvas {
    width: 100%;
    height: 100%;
    background: linear-gradient(
        180deg,
        color-mix(in srgb, var(--m-surface) 72%, transparent),
        color-mix(in srgb, var(--m-surface-soft) 85%, transparent)
      ),
      var(--m-surface-soft);
  }
</style>
