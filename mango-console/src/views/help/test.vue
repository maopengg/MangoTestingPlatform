<template>
  <TableBody ref="tableBody">
    <template #header>
      <div class="demo-header">
        <h3>FlowChart 组件使用示例</h3>
        <div class="demo-actions">
          <a-button type="primary" @click="saveFlow">保存</a-button>
          <a-button @click="executeFlow">执行</a-button>
          <a-button @click="addDemoFormItems">添加示例表单</a-button>
        </div>
      </div>
    </template>
    <template #default>
      <div class="flow-demo-page">
        <div class="demo-body">
          <!-- 左侧操作面板 -->
          <div class="left-panel">
            <a-card title="操作面板" :bordered="false">
              <!-- 拖拽面板 -->
              <div class="drag-panel">
                <div class="node-types">
                  <div
                    v-for="nodeType in nodeTypes"
                    :key="nodeType.type"
                    class="node-type-item"
                    draggable="true"
                    @dragstart="onDragStart($event, nodeType.type)"
                  >
                    <span class="color-dot" :style="{ backgroundColor: nodeType.color }"></span>
                    {{ nodeType.label }}
                  </div>
                </div>
              </div>
            </a-card>
          </div>

          <!-- 中间 FlowChart 组件 -->
          <div class="center-panel">
            <FlowChart
              ref="flowChartRef"
              :flow-data="flowData"
              :readonly="false"
              :allow-drop="true"
              :color-map="colorMap"
              @node-click="onNodeClick"
              @node-select="onNodeSelect"
              @flow-change="onFlowChange"
              @edge-delete="onEdgeDelete"
              @node-delete="onNodeDelete"
            />
          </div>

          <!-- 右侧详情面板 -->
          <div class="right-panel">
            <a-tabs default-active-key="2">
              <a-tab-pane key="1" title="节点配置信息">
                <div v-if="selectedNode" class="node-details">
                  <h4>{{ selectedNode.label }}</h4>
                  <div class="detail-item">
                    <label>ID:</label>
                    <span>{{ selectedNode.id }}</span>
                  </div>
                  <div class="detail-item">
                    <label>类型:</label>
                    <span>{{ selectedNode.type }}</span>
                  </div>
                  <div class="detail-item">
                    <label>位置:</label>
                    <span>x: {{ selectedNode.position.x }}, y: {{ selectedNode.position.y }}</span>
                  </div>
                  <div class="detail-item">
                    <label>配置:</label>
                    <pre class="config-json">{{
                      JSON.stringify(selectedNode.config, null, 2)
                    }}</pre>
                  </div>

                  <!-- 自定义配置编辑 -->
                  <div class="config-editor">
                    <h5>编辑配置</h5>
                    <a-textarea
                      v-model="configText"
                      :rows="6"
                      placeholder="请输入 JSON 格式的配置"
                      @blur="updateNodeConfig"
                    />
                  </div>
                </div>
                <div v-else class="no-selection">
                  <p>请选择一个节点查看详情</p>
                </div>
              </a-tab-pane>
              <a-tab-pane key="2" title="步骤测试结果">
                <ElementTestReport :result-data="data.pageSteps?.result_data" />
              </a-tab-pane>
            </a-tabs>
          </div>
        </div>
      </div>
    </template>
  </TableBody>
</template>

<script lang="ts" setup>
  import { ref, reactive, computed, watch, onMounted, nextTick } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import FlowChart from '@/components/FlowChart.vue'
  import { FlowData, UINode, UIEdge, FormItem } from '@/types/components'
  import { getUiSteps, putUiSteps } from '@/api/uitest/page-steps'
  import ElementTestReport from '@/components/ElementTestReport.vue'

  const flowChartRef = ref()
  const selectedNode = ref<UINode | null>(null)
  const configText = ref('')

  const data: any = reactive({
    pageSteps: {},
  })

  const flowData = ref<FlowData>({
    nodes: [],
    edges: [],
  })

  // 节点类型定义
  const nodeTypes = ref([
    { type: 'element', label: '元素操作', color: '#52c41a' },
    { type: 'ass', label: '断言操作', color: '#1677ff' },
    { type: 'sql', label: 'SQL操作', color: '#fa8c16' },
    { type: 'if', label: '条件判断', color: '#722ed1' },
    { type: 'custom', label: '自定义变量', color: '#eb2f96' },
  ])

  // 颜色映射
  const colorMap = computed(() => {
    const map: Record<string, string> = {}
    nodeTypes.value.forEach((item) => {
      map[item.type] = item.color
    })
    return map
  })

  // 监听选中节点变化，更新配置文本
  watch(
    selectedNode,
    (node) => {
      if (node) {
        configText.value = JSON.stringify(node.config || {}, null, 2)
      } else {
        configText.value = ''
      }
    },
    { immediate: true }
  )

  // 拖拽开始
  const onDragStart = (event: DragEvent, type: string) => {
    event.dataTransfer?.setData('application/mango-flow', type)
    event.dataTransfer!.effectAllowed = 'move'
  }

  // 节点点击事件
  const onNodeClick = (node: UINode) => {
    console.log('节点被点击:', node)
    Message.info(`点击了节点: ${node.label}`)
  }

  // 节点选中事件
  const onNodeSelect = (node: UINode | null) => {
    selectedNode.value = node
  }

  // 流程图数据变化事件
  const onFlowChange = (newFlowData: FlowData) => {
    flowData.value = newFlowData
  }

  // 连接线删除事件
  const onEdgeDelete = (edge: UIEdge) => {
    Message.success('连接线已删除')
  }

  // 节点删除事件
  const onNodeDelete = (node: UINode) => {
    Message.success(`节点 ${node.label} 已删除`)
    // 如果删除的是当前选中的节点，清空选择
    if (selectedNode.value?.id === node.id) {
      selectedNode.value = null
    }
  }

  // 更新节点配置
  const updateNodeConfig = () => {
    if (!selectedNode.value || !configText.value.trim()) return

    try {
      const config = JSON.parse(configText.value)
      // 创建新的节点数据
      const updatedNode = {
        ...selectedNode.value,
        config,
      }

      // 更新流程图中的节点
      const nodeIndex = flowData.value.nodes.findIndex((n) => n.id === selectedNode.value!.id)
      if (nodeIndex !== -1) {
        flowData.value.nodes[nodeIndex] = updatedNode
        selectedNode.value = updatedNode
        Message.success('节点配置已更新')
      }
    } catch (error) {
      Message.error('JSON 格式错误，请检查配置')
    }
  }

  // 保存流程
  const saveFlow = () => {
    const value = {}
    value['id'] = '2'
    value['flow_data'] = flowData.value
    putUiSteps(value)
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  // 执行流程
  const executeFlow = () => {
    console.log('执行流程:', flowData.value)
    Message.success('流程执行成功！')
  }

  function doRefresh1() {
    const value = {}
    value['id'] = '2'
    getUiSteps(value)
      .then((res) => {
        flowData.value = res.data[0].flow_data
        data.pageSteps = res.data[0]
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh1()
    })
  })
</script>

<style scoped>
  .flow-demo-page {
    padding: 16px;
    height: calc(100vh - 32px);
    display: flex;
    flex-direction: column;
  }

  .demo-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    background: #fff;
    border-bottom: 1px solid var(--color-border);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  }

  .demo-header h2 {
    margin: 0;
    color: var(--color-text-1);
    font-size: 18px;
    font-weight: 600;
  }

  .demo-actions {
    display: flex;
    gap: 12px;
  }

  .demo-body {
    flex: 1;
    display: flex;
    gap: 16px;
    min-height: 0;
  }

  .left-panel {
    flex: 0 0 10%;
    min-width: 200px;
  }

  .center-panel {
    flex: 0 0 50%;
    min-width: 0;
  }

  .right-panel {
    flex: 0 0 40%;
    min-width: 300px;
  }

  .drag-panel {
    margin-bottom: 20px;
  }

  .drag-panel h4,
  .data-display h4 {
    margin: 0 0 12px 0;
    font-size: 14px;
    color: var(--color-text-2);
  }

  .node-types {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .node-type-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border: 1px dashed var(--color-border);
    border-radius: 6px;
    cursor: grab;
    background: var(--color-bg-2);
    transition: all 0.2s;
  }

  .node-type-item:hover {
    border-color: var(--color-primary);
    background: var(--color-primary-light-1);
  }

  .node-type-item:active {
    cursor: grabbing;
  }

  .color-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .data-display {
    border-top: 1px solid var(--color-border);
    padding-top: 16px;
  }

  .data-info {
    margin: 8px 0 12px 0;
  }

  .data-info p {
    margin: 4px 0;
    font-size: 13px;
    color: var(--color-text-3);
  }

  .node-details h4 {
    margin: 0 0 16px 0;
    color: var(--color-text-1);
  }

  .detail-item {
    display: flex;
    margin-bottom: 12px;
    font-size: 13px;
  }

  .detail-item label {
    flex: 0 0 60px;
    color: var(--color-text-2);
    font-weight: 500;
  }

  .detail-item span {
    color: var(--color-text-1);
  }

  .config-json {
    background: var(--color-fill-2);
    padding: 8px;
    border-radius: 4px;
    font-size: 12px;
    margin: 0;
    white-space: pre-wrap;
    max-height: 120px;
    overflow-y: auto;
  }

  .config-editor {
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid var(--color-border);
  }

  .config-editor h5 {
    margin: 0 0 8px 0;
    font-size: 13px;
    color: var(--color-text-2);
  }

  .no-selection {
    text-align: center;
    color: var(--color-text-3);
    padding: 40px 0;
  }

  .dynamic-form {
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid var(--color-border);
  }

  .dynamic-form h5 {
    margin: 0 0 12px 0;
    font-size: 13px;
    color: var(--color-text-2);
  }

  .form-item__require :deep(.arco-form-item-label-col) {
    font-weight: 600;
  }

  .form-item__require :deep(.arco-form-item-label-col::before) {
    content: '*';
    color: #f53f3f;
    margin-right: 4px;
  }

  .form-actions {
    margin-top: 16px;
    display: flex;
    gap: 12px;
    justify-content: flex-end;
  }
</style>
