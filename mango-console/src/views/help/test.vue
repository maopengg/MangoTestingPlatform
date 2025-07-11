<template>
  <TableBody ref="tableBody">
    <template #default>
      <div class="flow-layout">
        <!-- 左侧节点面板 -->
        <div class="flow-panel flow-panel-left">
          <div class="flow-panel-title">节点面板</div>
          <div
            v-for="item in nodeTypes"
            :key="item.type"
            :draggable="true"
            @dragstart="(e) => onDragStart(e, item.type, item.label)"
            class="flow-draggable-node"
          >
            {{ item.label }}
          </div>
        </div>

        <!-- 中间vue-flow画布 -->
        <div class="flow-canvas-wrapper" @drop="onDrop" @dragover="onDragOver">
          <div class="flow-canvas-inner">
            <VueFlow
              :nodes="nodes"
              :edges="edges"
              class="flow-canvas"
              @node-click="onNodeClick"
              @connect="onConnect"
              :connection-mode="'loose'"
            />
          </div>
        </div>

        <!-- 右侧属性面板 -->
        <div class="flow-panel flow-panel-right">
          <div class="flow-panel-title">属性面板</div>
          <div v-if="selectedNode" class="flow-attr-list">
            <div><b>节点ID:</b> {{ selectedNode.id }}</div>
            <div><b>类型:</b> {{ selectedNode.type }}</div>
            <div><b>数据:</b> {{ selectedNode.data }}</div>
          </div>
          <div v-else class="flow-attr-empty">请选择一个节点查看详情</div>
        </div>
      </div>
    </template>
  </TableBody>
</template>

<script setup>
import { ref } from 'vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'

// 你可以自行组装 nodes/edges 数据
const nodes = ref([])
const edges = ref([])

const selectedNode = ref(null)

const nodeTypes = [
  { type: 'input', label: '开始' },
  { type: 'default', label: '节点' },
  { type: 'default', label: '判断' }, // 判断也用 default 类型
  { type: 'output', label: '结束' },
]

function onDragStart(event, nodeType, nodeLabel) {
  event.dataTransfer.setData('application/node-type', nodeType)
  event.dataTransfer.setData('application/node-label', nodeLabel)
  event.dataTransfer.effectAllowed = 'move'
}

const { project, addEdges } = useVueFlow()

// 添加连接处理
function onConnect(params) {
  edges.value.push({
    id: `edge_${Date.now()}`,
    source: params.source,
    target: params.target,
    animated: true
  })
}
</script>

<style>
@import '@vue-flow/core/dist/style.css';
@import '@vue-flow/core/dist/theme-default.css';

.flow-layout {
  display: flex;
  width: 100vw;
  height: 100vh;
  background: #f4f6fa;
}

.flow-panel {
  display: flex;
  flex-direction: column;
  min-width: 220px;
  max-width: 340px;
  width: 22%;
  background: #fff;
  border-radius: 12px;
  margin: 18px 0 18px 18px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.06);
  padding: 24px 18px 18px 18px;
  box-sizing: border-box;
  height: calc(100vh - 36px);
}
.flow-panel.flow-panel-left {
  width: 15%;
  min-width: 120px;
  max-width: 300px;
}
.flow-panel.flow-panel-right {
  width: 25%;
  min-width: 180px;
  max-width: 500px;
  margin-left: 0;
  margin-right: 18px;
}
.flow-panel-title {
  font-weight: bold;
  font-size: 18px;
  margin-bottom: 18px;
  color: #222;
}
.flow-draggable-node {
  margin-bottom: 14px;
  padding: 12px 0;
  background: #f7faff;
  border: 1.5px solid #b3c6e0;
  border-radius: 6px;
  cursor: grab;
  text-align: center;
  font-size: 16px;
  transition: background 0.2s, border 0.2s;
  box-shadow: 0 1px 4px 0 rgba(0,0,0,0.03);
}
.flow-draggable-node:hover {
  background: #e6f0ff;
  border-color: #409eff;
}
.flow-canvas-wrapper {
  width: 60%;
  min-width: 200px;
  max-width: 100vw;
  flex: unset;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
  height: 100vh;
  padding: 0 0;
}
.flow-canvas-inner {
  width: 98%;
  height: 96vh;
  background: #fafdff;
  border-radius: 12px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.04);
  overflow: hidden;
  display: flex;
  align-items: stretch;
  justify-content: stretch;
}
.flow-canvas {
  width: 100% !important;
  height: 100% !important;
  background: transparent;
}
.flow-attr-list {
  font-size: 15px;
  color: #333;
  line-height: 2.1;
}
.flow-attr-empty {
  color: #bbb;
  font-size: 15px;
  margin-top: 30px;
  text-align: center;
}

.vue-flow__handle {
  display: block !important;
  opacity: 1 !important;
}
</style>
