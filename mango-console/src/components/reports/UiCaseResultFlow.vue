<template>
  <div class="mango-ui-case-result-flow">
    <a-empty v-if="!flowNodes.length" description="暂无最近执行结果" />
    <UiFlowCanvas
      v-else
      :id="flowId"
      v-model:nodes="flowNodes"
      v-model:edges="flowEdges"
      class="mango-ui-case-result-flow__canvas"
      @node-click="onNodeClick"
    >
      <template #node-resultNode="{ data }">
        <a-popover position="right" trigger="hover">
          <UiFlowNodeCard
            :badges="[{ label: data.statusText, tone: data.statusKey }]"
            :operation="data.methodName"
            :selected="selectedNodeId === data.nodeId"
            :status-key="data.statusKey"
            :title="data.nodeName"
            :type-text="`${data.orderText} · ${data.typeName}`"
          />
          <template #content>
            <div class="mango-ui-case-result-popover">
              <strong>{{ data.nodeName }}</strong>
              <span>页面步骤：{{ data.pageStepName }}</span>
              <span>页面：{{ data.pageName }}</span>
              <span>模块：{{ data.moduleName }}</span>
              <span>项目/产品：{{ data.productName }}</span>
              <span>节点类型：{{ data.typeName }}</span>
              <span>执行方法：{{ data.methodName }}</span>
              <span>状态：{{ data.statusText }}</span>
              <span v-if="data.durationText">耗时：{{ data.durationText }}</span>
              <span v-if="data.pageTitle">页面标题：{{ data.pageTitle }}</span>
              <span v-if="data.pageUrl">页面地址：{{ data.pageUrl }}</span>
              <span data-feedback-kind="execution-result" v-if="data.errorMessage" class="mango-ui-case-result-popover__error">
                错误：{{ data.errorMessage }}
              </span>
            </div>
          </template>
        </a-popover>
      </template>
    </UiFlowCanvas>
  </div>
</template>

<script lang="ts" setup>
  import { nextTick, ref, watch } from 'vue'
  import { useVueFlow } from '@vue-flow/core'
  import type { Edge, Node, NodeMouseEvent } from '@vue-flow/core'
  import { useSelectValueStore } from '@/store/modules/get-ope-value'
  import UiFlowCanvas from '@/components/display/UiFlowCanvas.vue'
  import UiFlowNodeCard from '@/components/display/UiFlowNodeCard.vue'
  import { UI_FLOW_INITIAL_MAX_ZOOM } from '@/components/display/ui-flow'

  const props = withDefaults(
    defineProps<{
      caseSteps?: any[]
      result?: any
    }>(),
    {
      caseSteps: () => [],
      result: null,
    }
  )

  const emit = defineEmits<{
    (
      event: 'select',
      value: {
        configuredCaseStep: any
        configuredNode: any
        result: any
        pageStepIndex: number
        nodeIndex: number
      }
    ): void
  }>()

  const flowId = `mango-ui-case-result-${Math.random().toString(36).slice(2)}`
  const selectValueStore = useSelectValueStore()
  const flowNodes = ref<Node[]>([])
  const flowEdges = ref<Edge[]>([])
  const selectedNodeId = ref('')
  const nodePayload = new Map<
    string,
    {
      configuredCaseStep: any
      configuredNode: any
      result: any
      pageStepIndex: number
      nodeIndex: number
    }
  >()
  const { fitView } = useVueFlow(flowId)

  watch(
    [() => props.caseSteps, () => props.result],
    () => {
      buildFlow()
      nextTick(() => {
        void fitView({ padding: 0.35, maxZoom: UI_FLOW_INITIAL_MAX_ZOOM, duration: 200 })
      })
    },
    { immediate: true, deep: true }
  )

  function buildFlow() {
    const configuredSteps = Array.isArray(props.caseSteps) ? props.caseSteps : []
    const resultSteps = Array.isArray(props.result?.steps) ? props.result.steps : []
    const flowSteps = [...configuredSteps]
    resultSteps.forEach((resultStep: any) => {
      const exists = flowSteps.some(
        (item: any) => String(item?.id) === String(resultStep?.case_step_details_id)
      )
      if (!exists) {
        flowSteps.push({
          id: resultStep?.case_step_details_id,
          page_step: { name: resultStep?.name || '运行时页面步骤' },
          case_data: [],
        })
      }
    })
    nodePayload.clear()
    const resultNodes: Node[] = []
    const resultEdges: Edge[] = []
    let verticalOffset = 40
    let previousTerminalNodeId = ''

    flowSteps.forEach((configuredCaseStep: any, pageStepIndex: number) => {
      const pageStepResult =
        resultSteps.find(
          (item: any) => String(item?.case_step_details_id) === String(configuredCaseStep?.id)
        ) || null
      const configuredNodes = Array.isArray(configuredCaseStep?.case_data)
        ? configuredCaseStep.case_data
        : []
      const runtimeResults = Array.isArray(pageStepResult?.element_result_list)
        ? pageStepResult.element_result_list.filter((item: any) => !item?.runtime_pending)
        : []
      const runtimeMap = new Map<string, { result: any; index: number }>(
        runtimeResults.map((item: any, index: number) => [
          String(item?.id),
          { result: item, index },
        ])
      )
      const savedFlow = configuredCaseStep?.page_step?.flow_data
      const savedNodes = Array.isArray(savedFlow?.nodes) ? savedFlow.nodes : []
      const savedEdges = Array.isArray(savedFlow?.edges) ? savedFlow.edges : []
      const sourceNodes = savedNodes.length
        ? savedNodes
        : runtimeResults.map((result: any, index: number) => ({
            id: `runtime-${result?.id ?? index}-${index}`,
            type: result?.type,
            label: result?.name || '',
            config: { id: result?.id },
            position: { x: 80, y: index * 150 },
          }))
      if (!sourceNodes.length) return
      const minX = Math.min(...sourceNodes.map((item: any) => Number(item?.position?.x) || 0))
      const minY = Math.min(...sourceNodes.map((item: any) => Number(item?.position?.y) || 0))
      const maxY = Math.max(...sourceNodes.map((item: any) => Number(item?.position?.y) || 0))
      const nodeIdMap = new Map<string, string>()

      sourceNodes.forEach((savedNode: any, nodeIndex: number) => {
        const detailId = savedNode?.config?.id
        const runtimeEntry: any = runtimeMap.get(String(detailId))
        const runtimeResult = runtimeEntry?.result || null
        const configuredNode =
          configuredNodes.find(
            (item: any) => String(item?.page_step_details_id) === String(detailId)
          ) || null
        const nodeId = `case-${configuredCaseStep?.id ?? pageStepIndex}-${
          savedNode?.id ?? nodeIndex
        }`
        nodeIdMap.set(String(savedNode?.id), nodeId)
        const payload = {
          configuredCaseStep,
          configuredNode,
          result: runtimeResult,
          pageStepIndex,
          nodeIndex,
        }
        nodePayload.set(nodeId, payload)
        const status = resolveStatus(runtimeResult)
        resultNodes.push({
          id: nodeId,
          type: 'resultNode',
          position: {
            x: 80 + (Number(savedNode?.position?.x) || 0) - minX,
            y: verticalOffset + (Number(savedNode?.position?.y) || 0) - minY,
          },
          data: {
            nodeId,
            orderText:
              runtimeEntry?.index !== undefined ? `执行 ${runtimeEntry.index + 1}` : '未执行',
            nodeName:
              runtimeResult?.name ||
              configuredNode?.page_step_details_name ||
              savedNode?.label ||
              getMethodName(runtimeResult?.ope_key || configuredNode?.ope_key) ||
              getTypeName(runtimeResult?.type ?? configuredNode?.type ?? savedNode?.type),
            methodName:
              getMethodName(runtimeResult?.ope_key || configuredNode?.ope_key) ||
              getTypeName(runtimeResult?.type ?? configuredNode?.type ?? savedNode?.type),
            pageStepName:
              configuredCaseStep?.page_step?.name ||
              pageStepResult?.name ||
              `页面步骤 ${pageStepIndex + 1}`,
            pageName:
              configuredCaseStep?.page_step?.page?.name || configuredCaseStep?.page_name || '-',
            moduleName:
              configuredCaseStep?.page_step?.module?.name || configuredCaseStep?.module_name || '-',
            productName:
              configuredCaseStep?.page_step?.project_product?.name ||
              configuredCaseStep?.product_name ||
              props.result?.project_product_name ||
              '-',
            typeName: getTypeName(runtimeResult?.type ?? configuredNode?.type),
            durationText: formatDuration(runtimeResult?.duration_ms),
            pageTitle: runtimeResult?.page_title || '',
            pageUrl: runtimeResult?.page_url || '',
            errorMessage: runtimeResult?.error_message || '',
            ...status,
          },
        })
      })

      const incomingNodeIds = new Set<string>()
      const outgoingNodeIds = new Set<string>()
      savedEdges.forEach((savedEdge: any, edgeIndex: number) => {
        const source = nodeIdMap.get(String(savedEdge?.source?.node_id))
        const target = nodeIdMap.get(String(savedEdge?.target?.node_id))
        if (!source || !target) return
        incomingNodeIds.add(target)
        outgoingNodeIds.add(source)
        const sourcePayload = nodePayload.get(source)
        const targetPayload = nodePayload.get(target)
        const sourceResult = sourcePayload?.result
        const targetResult = targetPayload?.result
        const sourceRuntimeIndex = runtimeMap.get(
          String(sourcePayload?.configuredNode?.page_step_details_id)
        )?.index
        const targetRuntimeIndex = runtimeMap.get(
          String(targetPayload?.configuredNode?.page_step_details_id)
        )?.index
        const edgeExecuted =
          Boolean(sourceResult && targetResult) &&
          (sourceResult?.next_node_id != null
            ? String(sourceResult.next_node_id) ===
              String(targetPayload?.configuredNode?.page_step_details_id)
            : Number(targetRuntimeIndex) === Number(sourceRuntimeIndex) + 1)
        resultEdges.push(
          createEdge(
            source,
            target,
            resultNodes.find((item) => item.id === source),
            edgeExecuted,
            `case-result-edge-${configuredCaseStep?.id}-${savedEdge?.id || edgeIndex}`
          )
        )
      })

      if (!savedEdges.length) {
        const currentPageNodeIds = sourceNodes
          .map((savedNode: any) => nodeIdMap.get(String(savedNode?.id)))
          .filter(Boolean) as string[]
        currentPageNodeIds.slice(0, -1).forEach((source, index) => {
          const target = currentPageNodeIds[index + 1]
          resultEdges.push(
            createEdge(
              source,
              target,
              resultNodes.find((item) => item.id === source),
              true,
              `case-result-fallback-edge-${configuredCaseStep?.id}-${index}`
            )
          )
          incomingNodeIds.add(target)
          outgoingNodeIds.add(source)
        })
      }

      const currentNodeIds = Array.from(nodeIdMap.values())
      const firstExecutedId = runtimeResults[0]?.id
      const lastExecutedId = runtimeResults[runtimeResults.length - 1]?.id
      const firstExecutedNodeId =
        currentNodeIds.find(
          (id) => String(nodePayload.get(id)?.result?.id) === String(firstExecutedId)
        ) || ''
      const lastExecutedNodeId =
        [...currentNodeIds]
          .reverse()
          .find((id) => String(nodePayload.get(id)?.result?.id) === String(lastExecutedId)) || ''
      const rootNodeId =
        firstExecutedNodeId || currentNodeIds.find((id) => !incomingNodeIds.has(id)) || ''
      const terminalNodeId =
        lastExecutedNodeId ||
        [...currentNodeIds].reverse().find((id) => !outgoingNodeIds.has(id)) ||
        ''
      if (previousTerminalNodeId && rootNodeId) {
        const previousNode = resultNodes.find((item) => item.id === previousTerminalNodeId)
        const transitionExecuted = Boolean(
          nodePayload.get(previousTerminalNodeId)?.result && nodePayload.get(rootNodeId)?.result
        )
        resultEdges.push(
          createEdge(
            previousTerminalNodeId,
            rootNodeId,
            previousNode,
            transitionExecuted,
            `case-step-transition-${pageStepIndex}`
          )
        )
      }
      previousTerminalNodeId = terminalNodeId || previousTerminalNodeId
      verticalOffset += Math.max(180, maxY - minY + 220)
    })

    flowNodes.value = resultNodes
    flowEdges.value = resultEdges
    selectedNodeId.value =
      flowNodes.value.find((node) => (node.data as any)?.statusKey === 'failed')?.id ||
      flowNodes.value.find((node) => (node.data as any)?.statusKey !== 'pending')?.id ||
      flowNodes.value[0]?.id ||
      ''
    emitSelected()
  }

  function createEdge(
    source: string,
    target: string,
    sourceNode: Node | undefined,
    executed: boolean,
    edgeId: string
  ): Edge {
    const sourceStatus = (sourceNode?.data as any)?.statusKey
    return {
      id: edgeId,
      source,
      target,
      type: 'smoothstep',
      animated: executed && sourceStatus === 'running',
      style: {
        stroke: executed
          ? sourceStatus === 'failed'
            ? 'var(--m-danger)'
            : 'var(--m-success)'
          : 'var(--m-border-strong)',
        strokeWidth: 2,
        strokeDasharray: executed ? undefined : '5 5',
      },
    }
  }

  function onNodeClick(event: NodeMouseEvent) {
    selectedNodeId.value = event.node.id
    emitSelected()
  }

  function emitSelected() {
    const payload = nodePayload.get(selectedNodeId.value)
    if (payload) emit('select', payload)
  }

  function resolveStatus(result: any) {
    if (!result) {
      return { statusKey: 'pending', statusText: '未执行' }
    }
    if (result.status === 1) {
      return { statusKey: 'passed', statusText: '通过' }
    }
    if (result.status === 0) {
      return { statusKey: 'failed', statusText: '失败' }
    }
    return { statusKey: 'running', statusText: '执行中' }
  }

  function getTypeName(value: unknown) {
    const labels: Record<number, string> = {
      0: '元素操作',
      1: '断言操作',
      2: 'SQL 操作',
      3: '自定义变量',
      4: '条件判断',
      5: 'Python 代码',
    }
    return labels[Number(value)] || '执行节点'
  }

  function getMethodName(value: unknown) {
    if (!value) return ''
    return selectValueStore.findItemByValue(value)?.label || String(value)
  }

  function formatDuration(value: unknown) {
    const duration = Number(value)
    if (!Number.isFinite(duration) || duration < 0) return ''
    if (duration < 1000) return `${Math.round(duration)} ms`
    return `${(duration / 1000).toFixed(2)} 秒`
  }
</script>

<style scoped>
  .mango-ui-case-result-flow {
    width: 100%;
    height: 100%;
    min-height: 520px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }

  .mango-ui-case-result-flow__canvas {
    width: 100%;
    height: 100%;
  }

  .mango-ui-case-result-popover {
    display: flex;
    max-width: 360px;
    flex-direction: column;
    gap: 6px;
    color: var(--m-text);
    font-size: 12px;
  }

  .mango-ui-case-result-popover__error {
    color: var(--m-danger);
    white-space: normal;
  }
</style>
