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
                    <div v-if="formItems.length > 0">
                      <h5>节点配置表单</h5>
                      <a-form :model="formModel">
                        <a-form-item
                          v-for="item of formItems"
                          :key="item.key"
                          :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
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
                          <template v-else-if="item.type === 'select' && item.key === 'if_failure'">
                            <a-select
                              v-model="item.value"
                              :field-names="fieldNames"
                              :options="enumStore.condition_fail"
                              :placeholder="item.placeholder"
                              allow-clear
                              allow-search
                              value-key="key"
                            />
                          </template>
                          <template v-else-if="item.type === 'select' && item.key === 'if_pass'">
                            <a-select
                              v-model="item.value"
                              :field-names="fieldNames"
                              :options="enumStore.condition_pass"
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
                                :options="data.ope"
                                :placeholder="item.placeholder"
                                allow-clear
                                allow-search
                                expand-trigger="hover"
                                style="width: 380px"
                                value-key="key"
                                @change="upDataOpeValue(data.ope, item.value)"
                              />
                            </a-space>
                          </template>
                          <template
                            v-else-if="
                              item.type === 'cascader' &&
                              (item.label === '断言操作' || item.label === '判断条件')
                            "
                          >
                            <a-space direction="vertical">
                              <a-cascader
                                v-model="item.value"
                                :default-value="item.value"
                                :options="data.ass"
                                :placeholder="item.placeholder"
                                allow-clear
                                allow-search
                                expand-trigger="hover"
                                style="width: 380px"
                                value-key="key"
                                @change="upDataOpeValue(data.ass, item.value)"
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

                          <template v-else-if="item.type === 'radio' && item.key === 'type'">
                            <a-select
                              v-model="data.type"
                              :field-names="fieldNames"
                              :options="enumStore.element_ope"
                              :placeholder="item.placeholder"
                              allow-clear
                              allow-search
                              value-key="key"
                              @change="changeStatus"
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
                        <a-button @click="clearForm">清空表单</a-button>
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
  import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import FlowChart from '@/components/FlowChart.vue'
  import { FlowData, UINode, UIEdge } from '@/types/components'
  import { ModalDialogType } from '@/types/components'
  import { useRoute } from 'vue-router'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { usePageData } from '@/store/page-data'
  import { columns, formItems } from './config'
  import {
    deleteUiPageStepsDetailed,
    getUiPageStepsDetailed,
    getUiPageStepsDetailedTest,
    postUiPageStepsDetailed,
    putUiPagePutStepSort,
    putUiPageStepsDetailed,
  } from '@/api/uitest/page-steps-detailed'
  import { getUiSteps, getUiStepsTest, putUiSteps } from '@/api/uitest/page-steps'
  import { getUiUiElementName } from '@/api/uitest/element'
  import useUserStore from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import ElementTestReport from '@/components/ElementTestReport.vue'
  import { getSystemCacheDataKeyValue } from '@/api/system/cache_data'

  const flowChartRef = ref()
  const selectedNode = ref<UINode | null>(null)
  const configText = ref('')

  const flowData = ref<FlowData>({
    nodes: [],
    edges: [],
  })

  // 节点类型定义
  const nodeTypes = ref([
    { type: 0, label: '元素操作', color: '#52c41a' },
    { type: 1, label: '断言操作', color: '#1677ff' },
    { type: 2, label: 'SQL操作', color: '#fa8c16' },
    { type: 3, label: '条件判断', color: '#722ed1' },
    { type: 4, label: '自定义变量', color: '#eb2f96' },
  ])
  const enumStore = useEnum()

  const pageData = usePageData()
  const userStore = useUserStore()

  const route = useRoute()
  const formModel = ref({})
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const data: any = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
    dataList: [],
    uiPageName: [],
    type: 0,
    plainOptions: [],
    result_data: {},
    ass: [],
    ope: [],
    opeSelect: [],
  })
  const caseRunning = ref(false)

  function changeStatus(event: number, value: any = null) {
    data.type = event
    for (let i = formItems.length - 1; i >= 0; i--) {
      if (formItems[i].key !== 'type') {
        formItems.splice(i, 1)
      }
    }
    // 元素操作
    if (event === 0) {
      formItems.push({
        label: '元素操作',
        key: 'ope_key',
        value: value ? value : ref(''),
        type: 'cascader',
        required: true,
        placeholder: '请选择对元素的操作',
        validator: function () {
          if (!this.value && this.value !== 0) {
            Message.error(this.placeholder || '')
            return false
          }
          return true
        },
      })
      // 元素断言
    } else if (event === 1) {
      formItems.push({
        label: '断言操作',
        key: 'ope_key',
        value: value ? value : ref(''),
        type: 'cascader',
        required: true,
        placeholder: '请选择断言类型',
        validator: function () {
          if (!this.value && this.value !== 0) {
            Message.error(this.placeholder || '')
            return false
          }
          return true
        },
      })
      // sql操作
    } else if (event === 2) {
      formItems.push({
        label: 'key_list',
        key: 'key_list',
        value: ref(''),
        type: 'textarea',
        required: true,
        placeholder: '请输入sql查询结果的key_list',
        validator: function () {
          if (this.value !== '') {
            try {
              this.value = JSON.parse(this.value)
            } catch (e) {
              Message.error('key_list值请输入json数据类型')
              return false
            }
          }
          return true
        },
      })
      formItems.push({
        label: 'sql语句',
        key: 'sql',
        value: ref(''),
        type: 'textarea',
        required: true,
        placeholder: '请输入sql',
        validator: function () {
          if (!this.value && this.value !== 0) {
            Message.error(this.placeholder || '')
            return false
          }
          return true
        },
      })
      // 自定义变量
    } else if (event === 3) {
      formItems.push({
        label: 'key',
        key: 'key',
        value: ref(''),
        type: 'input',
        required: true,
        placeholder: '请输入key',
        validator: function () {
          if (!this.value && this.value !== 0) {
            Message.error(this.placeholder || '')
            return false
          }
          return true
        },
      })
      formItems.push({
        label: 'value',
        key: 'value',
        value: ref(''),
        type: 'input',
        required: true,
        placeholder: '请输入value',
        validator: function () {
          if (!this.value && this.value !== 0) {
            Message.error(this.placeholder || '')
            return false
          }
          return true
        },
      })
    }
    // 条件判断
    else if (event === 4) {
      formItems.push({
        label: '判断条件',
        key: 'ope_key',
        value: value ? value : ref(''),
        type: 'cascader',
        required: true,
        placeholder: '请选择条件判断方法',
        validator: function () {
          if (!this.value && this.value !== 0) {
            Message.error(this.placeholder || '')
            return false
          }
          return true
        },
      })
      formItems.push({
        label: '实际值',
        key: 'if_actual',
        value: ref(''),
        type: 'input',
        required: false,
        placeholder: '实际值和选择元素是二选一必填，这个值会覆盖选择的元素',
        validator: function () {
          return true
        },
      })
      formItems.push({
        label: '如果成立',
        key: 'if_pass',
        value: ref(0),
        type: 'select',
        required: true,
        placeholder: '请选择如果条件判断成立的选项',
        validator: function () {
          if (!this.value && this.value !== 0) {
            Message.error(this.placeholder || '')
            return false
          }
          return true
        },
      })
      formItems.push({
        label: '如不成立',
        key: 'if_failure',
        value: ref(''),
        type: 'select',
        required: true,
        placeholder: '请选择如果条件判断不成立的选项',
        validator: function () {
          if (!this.value && this.value !== 0) {
            Message.error(this.placeholder || '')
            return false
          }
          return true
        },
      })
    }
  }

  const saveFlow = () => {
    const value = {}
    value['id'] = pageData.record?.id || route.query.id
    value['flow_data'] = flowData.value
    putUiSteps(value)
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此步骤详情？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteUiPageStepsDetailed(record.id, record.page_step.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function onUpdate(item: any) {
    data.type = item.type
    if (item.ope_key && item.type === 0) {
      upDataOpeValue(data.ope, item.ope_key)
    } else {
      upDataOpeValue(data.ass, item.ope_key)
    }
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it: any) => {
        let propName: any = item[it.key]
        if (it.key.includes('locating') || it.key.includes('actual')) {
          propName = item.ele_name
        } else if (it.key.includes('ope_value')) {
          if (item.ope_value) {
            item.ope_value.forEach((item1: any) => {
              if (item1.d && it.key.includes(it.key)) {
                propName = item1.v
              }
            })
          }
        } else if (typeof propName === 'undefined') {
          item.ope_value.forEach((item: any) => {
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
    })
  }

  const handleChange = (_data: any) => {
    data.dataList = _data
    let data1: any = []
    data.dataList.forEach((item: any, index) => {
      data1.push({
        id: item.id,
        step_sort: index,
      })
    })
    putUiPagePutStepSort(data1)
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      modalDialogRef.value?.toggle()
      let value = getFormItems(formItems)
      value['page_step'] = route.query.id
      value['type'] = data.type
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
            findItemByValue(data.ope, value.ope_key).parameter.forEach((item: any) => {
              if (item.f === newKey) {
                extractedValues.push({
                  f: newKey,
                  v: value[key],
                  d: item.d,
                })
              }
            })
          } else if (newKey && data.type === 1) {
            findItemByValue(data.ass, value.ope_key).parameter.forEach((item: any) => {
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
      value['ope_value'] = extractedValues

      if (data.isAdd) {
        value['step_sort'] = data.dataList.length
        postUiPageStepsDetailed(value, route.query.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      } else {
        value['id'] = data.updateId
        putUiPageStepsDetailed(value, route.query.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      }
    }
  }

  function doResetSearch() {
    window.history.back()
  }

  function doRefresh() {
    getUiPageStepsDetailed(route.query.id)
      .then((res) => {
        data.dataList = res.data || []
        // 安全检查流程图数据
        const pageFlowData = pageData.record?.flow_data
        if (pageFlowData && typeof pageFlowData === 'object') {
          flowData.value = {
            nodes: Array.isArray(pageFlowData.nodes) ? pageFlowData.nodes : [],
            edges: Array.isArray(pageFlowData.edges) ? pageFlowData.edges : [],
          }
        } else {
          flowData.value = { nodes: [], edges: [] }
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

  function upDataOpeValue(selectData: any, value: any) {
    changeStatus(data.type, value)
    const inputItem = findItemByValue(selectData, value)
    if (inputItem && inputItem.parameter) {
      inputItem.parameter.forEach((select: any) => {
        if (
          select.n !== '函数代码' &&
          (select.f === 'actual' || select.f === 'locating') &&
          !formItems.some((item) => item.key === select.f)
        ) {
          if (data.type !== 4) {
            formItems.push({
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
            formItems.splice(-3, 0, {
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
        } else if (select.d === true && !formItems.some((item) => item.key === select.f)) {
          console.log(select.v)
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
            formItems.push(d)
          } else {
            formItems.splice(-2, 0, d)
          }
        }
      })
    }
  }

  function findItemByValue(data: any, value: string) {
    for (let i = 0; i < data.length; i++) {
      const item = data[i]
      if (item.value === value) {
        return item
      }
      if (item.children) {
        const childItem = findItemByValue(item.children, value)
        if (childItem) {
          return childItem
        }
      }
    }
    return undefined
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
  const onTest = async (record) => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (caseRunning.value) return
    caseRunning.value = true
    try {
      const res = await getUiPageStepsDetailedTest(record.id, userStore.selected_environment)
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

  function getUiRunSortOpe() {
    getSystemCacheDataKeyValue('select_value')
      .then((res) => {
        res.data.forEach((item: any) => {
          if (item.value === 'web') {
            if (route.query.pageType === '0') {
              data.ope.push(...item.children)
            }
          } else if (item.value === 'android') {
            if (route.query.pageType === '1') {
              data.ope.push(...item.children)
            }
          } else if (item.value === 'ass_android') {
            if (route.query.pageType === '1') {
              data.ass.unshift(...item.children)
            }
          } else if (item.value === 'ass_web') {
            if (route.query.pageType === '0') {
              data.ass.unshift(...item.children)
            }
          } else if (item.value.includes('断言')) {
            data.ass.push(item)
          }
        })
      })
      .catch(console.log)
  }

  function getLabelByValue(opeData: any, value: string): string {
    const list = [...opeData]
    for (const item of list) {
      if (item.children) {
        list.push(...item.children)
      }
    }
    return list.find((item: any) => item.value === value)?.label
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

  // 保存表单数据
  const saveFormData = () => {
    if (!selectedNode.value) return

    const formData = {}
    formItems.forEach((item: any) => {
      formData[item.key] = item.value
    })

    // 更新选中节点的配置
    const updatedNode = {
      ...selectedNode.value,
      config: { ...selectedNode.value.config, ...formData },
    }

    const nodeIndex = flowData.value.nodes.findIndex((n) => n.id === selectedNode.value!.id)
    if (nodeIndex !== -1) {
      flowData.value.nodes[nodeIndex] = updatedNode
      selectedNode.value = updatedNode
      Message.success('节点配置已保存')
    }
  }

  // 清空表单
  const clearForm = () => {
    formItems.forEach((item: any) => {
      if (item.reset) {
        item.reset()
      } else {
        item.value = ''
      }
    })
    Message.success('表单已清空')
  }
  onMounted(() => {
    doRefresh()
    doRefreshSteps(pageData.record.id)
    getEleName()
    getUiRunSortOpe()
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

  .box {
    width: 100%;
    margin: 0 auto;
    padding: 5px;
    box-sizing: border-box;
    display: flex;
  }

  .left {
    flex: 6;
    padding: 5px;
  }

  .right {
    flex: 4;
    padding: 5px;
    max-width: 60%;
  }

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
