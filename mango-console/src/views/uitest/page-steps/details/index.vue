<template>
  <TableBody ref="tableBody">
    <template #header>
      <a-card :bordered="false" style="border-radius: 10px; overflow: hidden" title="页面步骤详情">
        <template #extra>
          <a-space>
            <a-button size="small" type="outline" @click="beautifyCanvas">美化画布</a-button>
            <a-button size="small" type="primary" @click="saveFlow">保存画布</a-button>
            <a-button size="small" status="success" :loading="caseRunning" @click="onRunCase"
              >调试
            </a-button>
            <a-button size="small" status="warning" @click="doResetSearch">返回</a-button>
          </a-space>
        </template>

        <div class="flow-demo-page">
          <div class="demo-body">
            <!-- FlowChart 组件（包含左侧操作面板） -->
            <div class="center-panel">
              <FlowChart
                ref="flowChartRef"
                :flow-data="flowData"
                :table-data="data.dataList"
                :node-types="nodeTypes"
                :readonly="false"
                :allow-drop="true"
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
                    <h3>最近测试的元素信息</h3>
                    <div class="detail-item">
                      <div
                        v-if="
                          data?.selectResultData?.elements &&
                          data.selectResultData.elements.length > 0
                        "
                      >
                        <div
                          v-for="(element, index) in data.selectResultData.elements"
                          :key="index"
                          style="margin-bottom: 16px"
                        >
                          <div style="font-weight: 600; margin-bottom: 8px"
                            >元素 {{ index + 1 }}</div
                          >
                          <div style="display: flex; flex-direction: column; gap: 6px">
                            <div style="display: flex">
                              <span>定位类型：</span>
                              <span>{{
                                enumStore.element_exp.find((item1) => item1.key === element.exp)
                                  .title
                              }}</span>
                            </div>
                            <div style="display: flex">
                              <span>元素定位：</span>
                              <span>{{ element.loc }}</span>
                            </div>
                            <div style="display: flex">
                              <span>元素个数：</span>
                              <span>{{ element.ele_quantity }}</span>
                            </div>
                            <div style="display: flex">
                              <span>元素文本：</span>
                              <span>{{ element.element_text }}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                      <div v-else>
                        <span style="color: #c9cdd4">暂无元素信息</span>
                      </div>
                    </div>

                    <!-- 自定义配置编辑 -->
                    <div class="config-editor">
                      <div v-if="data.formItems.length > 0">
                        <h3>节点详情</h3>
                        <TipMessage
                          v-if="data.condition"
                          :message="
                            data.isAdd
                              ? '判断请在判断后续节点中选择判断结果，如果成立则会执行这个分支的操作！'
                              : '判断节点直接判断为True或False，为True则走第一条线，为False则走第二条线，设置第三条线无意义'
                          "
                        />

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
                            <template
                              v-else-if="item.type === 'select' && item.label === '选择元素'"
                            >
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
                                value-key="key"
                                @change="upDataOpeValue(item.value)"
                              />
                            </template>
                            <template
                              v-else-if="
                                item.type === 'cascader' &&
                                (item.label === '断言操作' || item.label === '判断方法')
                              "
                            >
                              <a-cascader
                                v-model="item.value"
                                :default-value="item.value"
                                :options="
                                  route.query.pageType === '0'
                                    ? useSelectValue.assWeb
                                    : useSelectValue.assAndroid
                                "
                                :placeholder="item.placeholder"
                                allow-clear
                                allow-search
                                expand-trigger="hover"
                                value-key="key"
                                @change="upDataOpeValue(item.value)"
                              />
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
                            <template
                              v-else-if="item.type === 'textarea' && item.key === 'key_list'"
                            >
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
                            <template v-else-if="item.type === 'code'">
                              <CodeEditor
                                v-model="item.value"
                                :placeholder="item.placeholder"
                                style="height: 360px"
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
                  <div v-if="data.result_data">
                    <ElementTestReport :result-data="data.result_data || {}" />
                  </div>
                </a-tab-pane>
              </a-tabs>
            </div>
          </div>
        </div>
      </a-card>
    </template>
  </TableBody>
</template>
<script lang="ts" setup>
  import { onMounted, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import FlowChart from '@/components/FlowChart.vue'
  import { FlowData, UINode, UIEdge } from '@/types/components'
  import { useRoute } from 'vue-router'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { usePageData } from '@/store/page-data'
  import {
    formItemsElement4,
    formItemsElementAss,
    formItemsElementCode,
    formItemsElementCondition,
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
  import CodeEditor from '@/components/CodeEditor.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import TipMessage from '@/components/TipMessage.vue'

  const formRef = ref()

  const flowChartRef = ref()
  const selectedNode = ref<UINode | null>(null)
  const configText = ref('')

  const flowData = ref<FlowData>({
    nodes: [],
    edges: [],
  })
  const enumStore = useEnum()
  const pageData = usePageData()
  const userStore = useUserStore()
  const useSelectValue = useSelectValueStore()

  const route = useRoute()
  const formModel = ref({})

  // 节点类型定义
  const nodeTypes = [
    { type: 0, label: '元素操作', color: '#52c41a' },
    { type: 1, label: '断言操作', color: '#1677ff' },
    { type: 2, label: 'SQL操作', color: '#fa8c16' },
    { type: 3, label: '自定义变量', color: '#eb2f96' },
    { type: 4, label: '条件判断', color: '#722ed1' },
    { type: 5, label: 'python代码', color: '#ff6b35' },
  ]

  const data: any = reactive({
    dataList: [],
    selectData: {}, // 选择的节点数据
    uiPageName: [], // 元素名称
    type: 0, // 点击的节点类型
    condition: 0, // 上一个节点是否是判断类型
    conditionId: 0, // 上一个节点是否是判断类型
    result_data: [], // 测试结果数据
    selectResultData: {}, // 选择的节点数据
    formItems: [], // 表单数据
    isConditionExpect: true,
    isAdd: false,
  })
  const caseRunning = ref(false)

  // 美化画布布局
  const beautifyCanvas = () => {
    if (flowData.value.nodes.length === 0) {
      Message.warning('画布中没有节点')
      return
    }

    // 调用 FlowChart 组件的美化方法
    if (flowChartRef.value && flowChartRef.value.beautifyLayout) {
      flowChartRef.value.beautifyLayout()
      Message.success('画布已美化')
    }
  }

  const saveFlow = () => {
    if (!checkNodeConnections()) return
    const value = {}
    value['id'] = pageData.record?.id || route.query.id
    value['parent_id'] = pageData.record?.id || route.query.id
    value['flow_data'] = flowData.value
    putUiSteps(value)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function setSelectData(node: UINode) {
    data.selectData = {}
    data.dataList.forEach((item: any) => {
      if (item.id === node.config.id) {
        data.selectData = item
      }
    })
    data.selectResultData = {}
    console.log(data.result_data)
    console.log(data.selectData.id)
    data.result_data?.element_result_list.forEach((item: any) => {
      debugger
      if (item.id === data.selectData.id) {
        data.selectResultData = item
      }
    })
  }

  function doResetSearch() {
    window.history.back()
  }

  function doRefresh() {
    getUiPageStepsDetailed(route.query.id)
      .then((res) => {
        data.dataList = res.data || []
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
    for (let i = data.formItems.length - 1; i >= 0; i--) {
      let key = data.formItems[i].key
      if (!['condition_value', 'ope_key'].includes(key)) {
        data.formItems.splice(i, 1)
      }
    }
    const label: any = useSelectValue.getTopLevelLabelByValue(value)
    if (inputItem && inputItem.parameter) {
      inputItem.parameter.forEach((select: any) => {
        if (
          !['函数断言', '文件断言', 'sql断言'].includes(label.label) &&
          (select.f === 'actual' || select.f === 'locating') &&
          !data.formItems.some((item) => item.key === select.f)
        ) {
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
        } else if (
          select.d === true && data.type === 4
            ? ['函数断言', '文件断言', 'sql断言'].includes(label.label) &&
              select.f !== 'expect' &&
              select.n !== '函数代码'
            : !data.formItems.some((item) => item.key === select.f)
        ) {
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
              // this.value = JSON.parse(this.value)
              return true
            },
          }
          data.formItems.push(d)
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
    } catch (e) {
    } finally {
      caseRunning.value = false
      doRefreshSteps(pageData.record.id)
    }
  }

  function doRefreshSteps(pageStepsId: any) {
    getUiSteps({ id: pageStepsId })
      .then((res) => {
        data.result_data = res.data[0].result_data
        flowData.value = res.data[0].flow_data
      })
      .catch(console.log)
  }

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

  // 查找指定节点的上一个节点
  const findPreviousNode = (nodeId: string): UINode | null => {
    // 查找连接到当前节点的边
    const incomingEdge = flowData.value.edges.find((edge) => edge.target.node_id === nodeId)
    if (!incomingEdge) {
      return null // 没有上一个节点
    }
    // 查找上一个节点
    const previousNode = flowData.value.nodes.find(
      (node) => node.id === incomingEdge.source.node_id
    )
    return previousNode || null
  }

  const onNodeClick = (node: UINode) => {
    setSelectData(node)
    // 检查上一个节点是否为判断类型（type: 4）
    const previousNode = findPreviousNode(node.id)
    data.isAdd = false
    if (previousNode && previousNode.type === 4) {
      data.conditionId = previousNode.config.id
      data.condition = true
    } else {
      data.condition = false
    }
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
    }
    formFeedback()
  }

  function changeStatus(event: number) {
    data.type = event
    // 清空表单项，重新构建
    data.formItems = []
    if (data.condition) {
      data.dataList.forEach((item: any) => {
        if (item.id === data.conditionId) {
          let byValue = useSelectValue.findItemByValue(item.ope_key)
          byValue.parameter.forEach((itme1) => {
            if (itme1.f === 'expect') {
              data.isAdd = true
            }
          })
        }
      })
      if (data.isAdd) {
        data.formItems.push(...formItemsElementCondition)
      }
    }
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
      // 条件判断
    } else if (event === 4) {
      data.formItems.push(...formItemsElement4)
    } else if (event === 5) {
      data.formItems.push(...formItemsElementCode)
    }
  }

  // 处理所有表单项的回显
  function formFeedback() {
    data.formItems.forEach((it: any) => {
      let propName: any = data.selectData[it.key]
      if (it.key === 'key') {
        propName = data.selectData?.custom ? data.selectData?.custom[0]['key'] : ''
      } else if (it.key === 'value') {
        propName = data.selectData?.custom ? data.selectData?.custom[0]['value'] : ''
      } else if (it.key === 'sql') {
        propName = data.selectData?.sql_execute ? data.selectData?.sql_execute[0]['sql'] : ''
      } else if (it.key === 'key_list') {
        propName = data.selectData?.sql_execute ? data.selectData?.sql_execute[0]['key_list'] : ''
      }
      if ((it.key.includes('locating') || it.key.includes('actual')) && it.label !== '函数代码') {
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
        it.value = propName.id ? propName?.id : propName?.expect
      } else {
        it.value = propName
      }
    })
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
    if (!node.config?.id) {
      setTimeout(() => {
        saveFlow()
      }, 100) // 确保flowData已经同步更新
      return
    }
    deleteUiPageStepsDetailed(node.config.id, route.query.id)
      .then((res) => {
        Message.success(res.msg)
        // 等待FlowChart组件数据同步完成后再保存
        setTimeout(() => {
          saveFlow()
        }, 100) // 确保flowData已经同步更新
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
      const inputConnections = flowData.value.edges.filter(
        (edge) => edge.target.node_id === node.id
      )
      const outputConnections = flowData.value.edges.filter(
        (edge) => edge.source.node_id === node.id
      )

      // 条件判断节点（type: 4）的连接规则较为灵活，可以有多个输出
      if (node.type !== 4) {
        // 其他节点类型（0-元素操作、1-断言操作、2-SQL操作、3-自定义变量）
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

    let value: any = getFormItems(data.formItems)
    value['page_step'] = route.query.id
    value['type'] = data.type
    if (data?.selectData?.id) {
      value['id'] = data.selectData.id
    }
    value['flow_data'] = flowData.value
    value['node_id'] = selectedNode.value.id
    value['step_sort'] = 0
    if (value.condition_value) {
      value['condition_value'] = { expect: value.condition_value }
    }
    if (value.key || value.value) {
      value['custom'] = [{ key: value.key, value: value.value }]
      delete value.key
      delete value.value
    }
    if (value.sql || value.key_list) {
      value['sql_execute'] = [{ sql: value.sql, key_list: value.key_list }]
      delete value.sql
      delete value.key_list
    }

    postUiPageStepsDetailed({ ...value, ...processOptionData(value) }, route.query.id)
      .then((res) => {
        Message.success(res.msg)
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
    if (!value.ope_key) {
      return {}
    }
    const parameter = useSelectValue.findItemByValue(value.ope_key)?.parameter
    if (!parameter) {
      return {}
    }
    for (const key in value) {
      const newKey = key.replace('-ope_value', '')
      parameter.forEach((item: any) => {
        const isDuplicate = extractedValues.some(
          (existingItem) => existingItem.d === item.d && existingItem.f === item.f
        )
        if (key == 'locating' || key == 'actual') {
          value['ele_name'] = value[key]
          if (!isDuplicate) {
            extractedValues.push(item)
          }
        } else if (newKey && item.f === newKey) {
          item['v'] = value[key]
          if (!isDuplicate) {
            extractedValues.push(item)
          }
          delete value[key]
        }
      })
    }
    return { ope_value: extractedValues, ele_name: value['ele_name'] }
  }

  onMounted(() => {
    doRefreshSteps(pageData.record.id)
    doRefresh()
    getEleName()
    useSelectValue.getSelectValue()
  })
</script>
<style scoped>
  .flow-demo-page {
    height: calc(100vh - 210px);
    display: flex;
    flex-direction: column;
    padding: 0;
    overflow: hidden;
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
    gap: 12px;
    min-height: 0;
  }

  .center-panel {
    flex: 1;
    min-width: 0;
  }

  .right-panel {
    flex: 0 0 40%;
    min-width: 500px;
    border: 1px solid #e5e6eb;
    border-radius: 4px;
    background: #fff;
  }

  .node-details h3 {
    margin: 0 0 20px 0;
    font-size: 14px;
    font-weight: 600;
  }

  .detail-item {
    display: flex;
    margin-bottom: 12px;
    font-size: 13px;
    padding: 0 0 0 40px;
  }

  .detail-item label {
    flex: 0 0 60px;
    color: var(--color-text-2);
    font-weight: 500;
  }

  .detail-item span {
    color: var(--color-text-1);
  }

  .detail-item > div > div > div > span:last-child {
    color: #1d2129;
    word-break: break-all;
  }

  .config-editor {
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid var(--color-border-2);
  }

  .config-editor h3 {
    margin: 0 0 16px 0;
    font-size: 14px;
    font-weight: 600;
  }

  .config-editor > div {
    padding: 0 !important;
  }

  .no-selection {
    text-align: center;
    color: var(--color-text-3);
    padding: 60px 20px;
  }

  .no-selection p {
    font-size: 14px;
    margin: 0;
  }

  .form-actions {
    margin-top: 16px;
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }
</style>
