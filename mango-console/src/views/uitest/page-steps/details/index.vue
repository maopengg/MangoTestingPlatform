<template>
  <TableBody ref="tableBody">
    <template #header>
      <a-card :bordered="false" style="border-radius: 10px; overflow: hidden" title="页面步骤详情">
        <template #extra>
          <a-space>
            <a-button size="small" type="primary" @click="saveFlow">保存</a-button>
            <a-button size="small" status="success" :loading="caseRunning" @click="onRunCase"
              >调试
            </a-button>
            <a-button size="small" status="danger" @click="doResetSearch">返回</a-button>
          </a-space>
        </template>
        <div class="container"></div>
      </a-card>
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
                    @dragstart="onDragStart($event, nodeType.type.toString())"
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
              :table-data="data.dataList"
              :node-types="nodeTypes"
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
            <a-tabs default-active-key="1">
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
                    <div v-if="data.formItems.length > 0" style="padding: 0px 100px 0px 0px">
                      <h5>节点详情</h5>
                      <a-form :model="formModel" ref="formRef">
                        <a-form-item
                          v-for="item of data.formItems"
                          :key="item.key"
                          :required="item.required"
                          :label="item.label"
                        >
                          <template v-if="item.type === 'input'">
                            <a-input v-model="item.value" :placeholder="item.placeholder" />
                          </template>
                          <template v-else-if="item.type === 'select' && item.label === '选择元素'">
                            <a-select
                              v-model="item.value"
                              :field-names="fieldNames"
                              :options="data.uiPageName"
                              :placeholder="item.placeholder"
                              allow-clear
                              allow-search
                              value-key="key"
                            />
                          </template>
                          <template
                            v-else-if="item.type === 'cascader' && item.label === '元素操作'"
                          >
                            <a-space direction="vertical">
                              <a-cascader
                                v-model="item.value"
                                :default-value="item.value"
                                :options="
                                  route.query.pageType === '0'
                                    ? useSelectValue.webOpe
                                    : useSelectValue.androidOpe
                                "
                                :placeholder="item.placeholder"
                                allow-clear
                                allow-search
                                expand-trigger="hover"
                                style="width: 380px"
                                value-key="key"
                                @change="upDataOpeValue(item.value)"
                              />
                            </a-space>
                          </template>
                          <template
                            v-else-if="item.type === 'cascader' && item.label === '断言操作'"
                          >
                            <a-space direction="vertical">
                              <a-cascader
                                v-model="item.value"
                                :default-value="item.value"
                                :options="useSelectValue.ass"
                                :placeholder="item.placeholder"
                                allow-clear
                                allow-search
                                expand-trigger="hover"
                                style="width: 380px"
                                value-key="key"
                                @change="upDataOpeValue(item.value)"
                              />
                            </a-space>
                          </template>
                          <template
                            v-else-if="
                              item.type === 'textarea' &&
                              item.key !== 'key_list' &&
                              item.key !== 'sql'
                            "
                          >
                            <a-textarea
                              v-model="item.value"
                              :auto-size="{ minRows: 4, maxRows: 7 }"
                              :default-value="item.value"
                              :placeholder="item.placeholder"
                              allow-clear
                            />
                          </template>
                          <template v-else-if="item.type === 'textarea' && item.key === 'key_list'">
                            <a-textarea
                              v-model="item.value"
                              :auto-size="{ minRows: 4, maxRows: 7 }"
                              :default-value="item.value"
                              :placeholder="item.placeholder"
                              allow-clear
                            />
                          </template>

                          <template v-else-if="item.type === 'textarea' && item.key === 'sql'">
                            <a-textarea
                              v-model="item.value"
                              :auto-size="{ minRows: 4, maxRows: 7 }"
                              :default-value="item.value"
                              :placeholder="item.placeholder"
                              allow-clear
                            />
                          </template>
                        </a-form-item>
                      </a-form>
                      <div class="form-actions">
                        <a-button type="primary" @click="saveFormData">保存配置</a-button>
                      </div>
                    </div>
                  </div>
                </div>
                <div v-else class="no-selection">
                  <p>请选择一个节点查看详情</p>
                </div>
              </a-tab-pane>
              <a-tab-pane key="2" title="步骤测试结果">
                <ElementTestReport :result-data="data.result_data" />
              </a-tab-pane>
            </a-tabs>
          </div>
        </div>
      </div>
    </template>
  </TableBody>
</template>
<script lang="ts" setup>
  import { computed, onMounted, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import FlowChart from '@/components/FlowChart.vue'
  import { FlowData, UINode, UIEdge } from '@/types/components'
  import { useRoute } from 'vue-router'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { usePageData } from '@/store/page-data'
  import {
    formItemsElementAss,
    formItemsElementKey,
    formItemsElementOpe,
    formItemsElementSql,
  } from './config'
  import {
    deleteUiPageStepsDetailed,
    getUiPageStepsDetailed,
    postUiPageStepsDetailed,
  } from '@/api/uitest/page-steps-detailed'
  import { getUiSteps, getUiStepsTest, putUiSteps } from '@/api/uitest/page-steps'
  import { getUiUiElementName } from '@/api/uitest/element'
  import useUserStore from '@/store/modules/user'
  import ElementTestReport from '@/components/ElementTestReport.vue'
  import { useSelectValueStore } from '@/store/modules/get-ope-value'

  const formRef = ref()

  const flowChartRef = ref()
  const selectedNode = ref<UINode | null>(null)
  const configText = ref('')

  const flowData = ref<FlowData>({
    nodes: [],
    edges: [],
  })

  const nodeTypes = ref([
    { type: 0, label: '元素操作', color: '#52c41a' },
    { type: 1, label: '断言操作', color: '#1677ff' },
    { type: 2, label: 'SQL操作', color: '#fa8c16' },
    { type: 3, label: '条件判断', color: '#722ed1' },
    { type: 4, label: '自定义变量', color: '#eb2f96' },
  ])

  const pageData = usePageData()
  const userStore = useUserStore()
  const useSelectValue = useSelectValueStore()

  const route = useRoute()
  const formModel = ref({})
  const data: any = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
    dataList: [],
    selectData: {},
    uiPageName: [],
    type: 0,
    plainOptions: [],
    result_data: {},
    opeSelect: [],
    formItems: [],
  })
  const caseRunning = ref(false)

  function changeStatus(event: number) {
    data.type = event
    // 清空表单项，重新构建
    data.formItems = []
    if (event === 0) {
      data.formItems.push(...formItemsElementOpe)
      // 元素断言
    } else if (event === 1) {
      data.formItems.push(...formItemsElementAss)
      // sql操作
    } else if (event === 2) {
      data.formItems.push(...formItemsElementSql)
      // 自定义变量
    } else if (event === 3) {
      data.formItems.push(...formItemsElementKey)
    }
  }

  const saveFlow = () => {
    if (!checkNodeConnections()) return
    const value = {}
    value['id'] = pageData.record?.id || route.query.id
    value['flow_data'] = flowData.value
    putUiSteps(value)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function doResetSearch() {
    window.history.back()
  }

  function doRefresh(flushed = false) {
    getUiPageStepsDetailed(route.query.id)
      .then((res) => {
        data.dataList = res.data || []
        // 安全检查流程图数据
        if (flushed) {
          const pageFlowData = pageData.record?.flow_data
          if (pageFlowData && typeof pageFlowData === 'object') {
            flowData.value = {
              nodes: Array.isArray(pageFlowData.nodes) ? pageFlowData.nodes : [],
              edges: Array.isArray(pageFlowData.edges) ? pageFlowData.edges : [],
            }
          } else {
            flowData.value = { nodes: [], edges: [] }
          }
        }
      })
      .catch(console.log)
  }

  function getEleName() {
    getUiUiElementName(route.query.pageId)
      .then((res) => {
        data.uiPageName = res.data
      })
      .catch(console.log)
  }

  function upDataOpeValue(value: any) {
    const inputItem = useSelectValue.findItemByValue(value)
    if (inputItem && inputItem.parameter) {
      inputItem.parameter.forEach((select: any) => {
        if (
          select.n !== '函数代码' &&
          (select.f === 'actual' || select.f === 'locating') &&
          !data.formItems.some((item) => item.key === select.f)
        ) {
          if (data.type !== 4) {
            data.formItems.push({
              label: '选择元素',
              key: select.f,
              value: ref(''),
              placeholder: '请选择一个元素',
              required: true,
              type: 'select',
              validator: function () {
                if (!this.value && this.value !== 0) {
                  Message.error(this.placeholder || '')
                  return false
                }
                return true
              },
            })
          } else {
            data.formItems.splice(-3, 0, {
              label: '选择元素',
              key: select.f,
              value: ref(''),
              placeholder: '请选择一个元素，手动输入的实际值会覆盖此元素结果',
              required: false,
              type: 'select',
              validator: function () {
                return true
              },
            })
          }
        } else if (select.d === true && !data.formItems.some((item) => item.key === select.f)) {
          let d = {
            label: select.n ? select.n : select.f,
            key: `${select.f}-ope_value`,
            value:
              select.v !== null && typeof select.v === 'object'
                ? JSON.stringify(select.v)
                : select.v,
            type: 'textarea',
            required: true,
            placeholder: select.p,
            validator: function () {
              if (!this.value && this.value !== 0) {
                Message.error(this.placeholder || '')
                return false
              }
              this.value = JSON.parse(this.value)
              return true
            },
          }
          if (data.type !== 4) {
            data.formItems.push(d)
          } else {
            data.formItems.splice(-2, 0, d)
          }
        }
      })
    }
  }

  const onRunCase = async () => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (caseRunning.value) return
    caseRunning.value = true
    try {
      const res = await getUiStepsTest(route.query.id, userStore.selected_environment)
      Message.loading(res.msg)
      doRefresh()
    } catch (e) {
    } finally {
      caseRunning.value = false
    }
  }

  function doRefreshSteps(pageStepsId: any) {
    getUiSteps({ id: pageStepsId })
      .then((res) => {
        data.result_data = res.data[0].result_data
      })
      .catch(console.log)
  }

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

  const onNodeClick = (node: UINode) => {
    data.selectData = {}
    data.dataList.forEach((item) => {
      if (item.id === node.config.id) {
        data.selectData = item
      }
    })
    // 先清空表单项，重新构建基础表单
    changeStatus(node.type)
    
    // 如果有选中的数据，需要处理回显和动态表单项
    if (Object.keys(data.selectData).length > 0) {
      // 先处理操作类型选择，触发动态表单生成
      const opeKeyItem = data.formItems.find((item: any) => item.key === 'ope_key')
      if (opeKeyItem && data.selectData.ope_key) {
        opeKeyItem.value = data.selectData.ope_key
        // 触发动态表单项生成
        upDataOpeValue(data.selectData.ope_key)
      }
      
      // 然后处理所有表单项的回显
      data.formItems.forEach((it: any) => {
        let propName: any = data.selectData[it.key]
        if (it.key.includes('locating') || it.key.includes('actual')) {
          propName = data.selectData.ele_name
        } else if (it.key.includes('ope_value')) {
          if (data.selectData.ope_value) {
            data.selectData.ope_value.forEach((item1: any) => {
              if (item1.d && it.key.includes(item1.f)) {
                propName = item1.v
              }
            })
          }
        } else if (typeof propName === 'undefined' && data.selectData.ope_value) {
          data.selectData.ope_value.forEach((item: any) => {
            if (item.f === it.key) {
              propName = item.v
            }
          })
        }
        if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
        } else {
          it.value = propName
        }
      })
    }
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
    if (selectedNode.value?.id === node.id) {
      selectedNode.value = null
    }
    deleteUiPageStepsDetailed(node.config.id, route.query.id)
      .then((res) => {
        Message.success(res.msg)
        saveFlow()
      })
      .catch(console.log)
  }

  // 检查是否有节点没有进行连接
  const checkNodeConnections = (): boolean => {
    // 如果没有节点，返回true（通过检查）
    if (flowData.value.nodes.length === 0) {
      return true
    }

    // 如果只有一个节点，也认为是有效的（单节点流程）
    if (flowData.value.nodes.length === 1) {
      return true
    }

    // 检查每个节点的连接情况
    for (const node of flowData.value.nodes) {
      // 统计该节点的输入和输出连接
      const inputConnections = flowData.value.edges.filter((edge) => edge.target.nodeId === node.id)
      const outputConnections = flowData.value.edges.filter(
        (edge) => edge.source.nodeId === node.id
      )

      // 条件判断节点（type: 3）的连接规则较为灵活，可以有多个输出
      if (node.type === 3) {
        // 条件判断节点至少需要有一个输出连接
        if (outputConnections.length === 0 && flowData.value.nodes.length > 1) {
          Message.warning('有步骤节点没有进行连接，请先连接节点后再保存！')
          return false
        }
      } else {
        // 其他节点类型（0-元素操作、1-断言操作、2-SQL操作、4-自定义变量）
        // 如果不是第一个节点，必须有输入连接
        // 如果不是最后一个节点，必须有输出连接
        const hasInput = inputConnections.length > 0
        const hasOutput = outputConnections.length > 0

        // 检查是否为孤立节点（既没有输入也没有输出）
        if (!hasInput && !hasOutput && flowData.value.nodes.length > 1) {
          Message.warning('有步骤节点没有进行连接，请先连接节点后再保存！')
          return false
        }
      }
    }

    return true
  }

  // 保存表单数据
  const saveFormData = () => {
    if (!selectedNode.value) return
    if (!checkNodeConnections()) return

    // 添加必填校验
    if (!data.formItems.every((it: any) => (it.validator ? it.validator() : true))) {
      return
    }

    let value = getFormItems(data.formItems)
    value['page_step'] = route.query.id
    value['type'] = data.type
    if (data?.selectData?.id) {
      value['id'] = data.selectData.id
    }
    value['ope_value'] = processOptionData(value)
    value['flow_data'] = flowData.value

    postUiPageStepsDetailed(value, route.query.id)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
        const updatedNode = {
          ...selectedNode.value,
          config: { id: res.data.id },
        }
        const nodeIndex = flowData.value.nodes.findIndex((n) => n.id === selectedNode.value!.id)
        if (nodeIndex !== -1) {
          flowData.value.nodes[nodeIndex] = updatedNode
          selectedNode.value = updatedNode
        }
        doRefresh()
      })
      .catch(console.log)
  }

  function processOptionData(value: any) {
    const extractedValues = []
    for (const key in value) {
      if (key == 'locating' || key == 'actual') {
        value['ele_name'] = value[key]
        extractedValues.push({
          f: key,
          v: '',
          d: false,
        })
        delete value[key]
      } else if (key.includes('-ope_value')) {
        const newKey = key.replace('-ope_value', '')
        if (newKey && data.type === 0) {
          useSelectValue.findItemByValue(value.ope_key).parameter.forEach((item: any) => {
            if (item.f === newKey) {
              extractedValues.push({
                f: newKey,
                v: value[key],
                d: item.d,
              })
            }
          })
        } else if (newKey && data.type === 1) {
          useSelectValue.findItemByValue(value.ope_key).parameter.forEach((item: any) => {
            if (item.f === newKey) {
              extractedValues.push({
                f: newKey,
                v: value[key],
                d: item.d,
              })
            }
          })
        }
        delete value[key]
      }
    }
    return extractedValues
  }

  onMounted(() => {
    doRefresh(true)
    doRefreshSteps(pageData.record.id)
    getEleName()
    useSelectValue.getSelectValue()
  })
</script>
<style scoped>
  .container .a-space span {
    font-size: 14px !important;
    display: block;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .flow-demo-page {
    padding: 16px;
    height: calc(100vh - 32px);
    display: flex;
    flex-direction: column;
  }

  .demo-header h2 {
    margin: 0;
    color: var(--color-text-1);
    font-size: 18px;
    font-weight: 600;
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
