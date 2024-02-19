<template>
  <div>
    <a-card title="组合用例场景">
      <template #extra>
        <a-space>
          <a-button type="primary" size="small" @click="addApiInfo">增加接口</a-button>
          <a-button status="success" size="small" @click="caseRun(null)">全部执行</a-button>
          <a-button type="primary" status="warning" size="small" @click="doResetSearch"
            >返回</a-button
          >
        </a-space>
      </template>
      <div class="container">
        <a-space direction="vertical" style="width: 50%">
          <span>用例ID：{{ pageData.record.id }}</span>
          <span>所属项目：{{ pageData.record.project?.name }}</span>
          <span>顶级模块：{{ pageData.record.module_name?.superior_module }}</span>
          <span>所属模块：{{ pageData.record.module_name?.name }}</span>
        </a-space>
        <a-space direction="vertical" style="width: 50%">
          <span>用例名称：{{ pageData.record.name }}</span>
          <span>用例负责人：{{ pageData.record.case_people?.nickname }}</span>
          <span>执行顺序：{{ pageData.record.case_flow }}</span>
        </a-space>
      </div>
    </a-card>
    <a-card>
      <div class="container">
        <div class="left">
          <a-table
            :columns="columns"
            :data="apiCaseData.data"
            :draggable="{ type: 'handle', width: 40 }"
            :pagination="false"
            :bordered="true"
            @row-click="select"
            @change="handleChange"
          >
            <template #columns>
              <a-table-column
                v-for="item of columns"
                :key="item.key"
                :align="item.align"
                :title="item.title"
                :width="item.width"
                :data-index="item.dataIndex"
                :fixed="item.fixed"
              >
                <template v-if="item.dataIndex === 'client'" #cell="{ record }">
                  <a-tag color="arcoblue" size="small" v-if="record.client === 0">WEB</a-tag>
                  <a-tag color="magenta" size="small" v-else-if="record.client === 1">APP</a-tag>
                  <a-tag color="green" size="small" v-else-if="record.client === 2">MINI</a-tag>
                </template>
                <template v-else-if="item.dataIndex === 'method'" #cell="{ record }">
                  <a-tag color="green" size="small" v-if="record.method === 0">GET</a-tag>
                  <a-tag color="gold" size="small" v-else-if="record.method === 1">POST</a-tag>
                  <a-tag color="arcoblue" size="small" v-else-if="record.method === 2">PUT</a-tag>
                  <a-tag color="magenta" size="small" v-else-if="record.method === 3">DELETE</a-tag>
                </template>
                <template v-else-if="item.dataIndex === 'status'" #cell="{ record }">
                  <a-tag color="green" size="small" v-if="record.status === 1">通过</a-tag>
                  <a-tag color="red" size="small" v-else-if="record.status === 0">失败</a-tag>
                  <a-tag color="gray" size="small" v-else>未测试</a-tag>
                </template>
                <template v-else-if="item.dataIndex === 'actions'" #cell="{ record }">
                  <a-button type="text" size="mini" @click="caseRun(record.case_sort)"
                    >执行到此处</a-button
                  >
                  <a-button type="text" size="mini" @click="refresh(record.id)">刷新</a-button>
                  <a-button status="danger" type="text" size="mini" @click="onDelete(record)"
                    >删除</a-button
                  >
                </template>
              </a-table-column>
            </template>
          </a-table>
        </div>
        <div class="right">
          <a-space direction="vertical" fill>
            <a-radio-group
              v-model="apiCaseData.position"
              type="button"
              @change="clickRadioGroup"
              size="large"
            >
              <a-radio value="request" :default-checked="true">请求信息</a-radio>
              <a-radio value="front">前置处理</a-radio>
              <a-radio value="response">响应结果</a-radio>
              <a-radio value="assertion">接口断言</a-radio>
              <a-radio value="posterior">后置处理</a-radio>
              <a-radio value="dump">数据清除</a-radio>
              <a-radio value="cache">缓存数据</a-radio>
              <a-button type="text" :disabled="apiCaseData.disabled" @click="clickAdd"
                >增加一条</a-button
              >
            </a-radio-group>
            <a-tabs position="left" @tab-click="tabsChange">
              <a-tab-pane
                v-for="item of apiCaseData.selectData"
                :key="item.key"
                :title="item.title"
              >
                <template v-if="item.type === 'descriptions'">
                  <a-descriptions style="margin-top: 20px" :data="item.data" :column="1" />
                </template>
                <template v-else-if="item.type === 'textarea'">
                  <a-textarea
                    placeholder="请输入等待时间单位秒"
                    v-model="item.data"
                    @blur="blurSave(item)"
                    auto-size
                    allow-clear
                    show-word-limit
                  />
                </template>
                <template v-else-if="item.type === 'list'">
                  <a-space direction="vertical" fill>
                    <a-space v-for="(inputObj, index) of item.data" :key="index">
                      <a-space>
                        <a-input
                          placeholder="请输入"
                          v-model="item.data[index]"
                          @blur="blurSave(item)"
                        />
                        <a-button
                          type="text"
                          size="small"
                          status="danger"
                          @click="removeFrontSql(item, index)"
                          >移除
                        </a-button>
                      </a-space>
                    </a-space>
                  </a-space>
                </template>
                <template v-else-if="item.type === 'assertion'">
                  <a-space direction="vertical">
                    <a-space v-for="(value, index) of item.data" :key="index">
                      <a-input
                        placeholder="请输入"
                        v-model="item.data[index].value"
                        @blur="blurSave(item)"
                      />
                      <a-cascader
                        v-model="item.data[index].method"
                        :options="apiCaseData.ass"
                        :default-value="item.data[index].method"
                        expand-trigger="hover"
                        placeholder="请选择断言方法"
                        value-key="key"
                        @blur="blurSave(item)"
                      />
                      <a-input
                        placeholder="请输入"
                        v-model="item.data[index].expect"
                        @blur="blurSave(item)"
                      />
                      <a-button type="text" status="danger" @click="removeFrontSql(item, index)"
                        >移除</a-button
                      >
                    </a-space>
                  </a-space>
                </template>
                <template v-else-if="item.type === 'posterior'">
                  <a-space direction="vertical">
                    <a-space v-for="(value, index) of item.data" :key="index">
                      <a-input
                        placeholder="请输入"
                        v-model="item.data[index].key"
                        @blur="blurSave(item)"
                      />
                      <a-input
                        placeholder="请输入"
                        v-model="item.data[index].value"
                        @blur="blurSave(item)"
                      />

                      <a-button
                        type="text"
                        size="small"
                        status="danger"
                        @click="removeFrontSql(item, index)"
                        >移除
                      </a-button>
                    </a-space>
                  </a-space>
                </template>
                <template v-else>
                  <div>
                    <span>{{ item.data }}</span>
                  </div>
                </template>
              </a-tab-pane>
            </a-tabs>
          </a-space>
        </div>
      </div>
    </a-card>
  </div>
  <ModalDialog ref="modalDialogRef" :title="apiCaseData.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
          :label="item.label"
          v-for="item of formItems"
          :key="item.key"
        >
          <template v-if="item.type === 'input'">
            <a-input :placeholder="item.placeholder" v-model="item.value" />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'module_name'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="apiCaseData.moduleList"
              :field-names="fieldNames"
              @change="getModuleApi(item.value)"
              value-key="key"
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'api_info'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="apiCaseData.apiList"
              :field-names="fieldNames"
              value-key="key"
              allow-clear
              allow-search
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import { reactive, nextTick, onMounted, ref } from 'vue'
  import { deleted, get, post, put } from '@/api/http'

  import {
    apiCaseDetailed,
    systemEnumEnd,
    systemEnumMethod,
    apiRun,
    userProjectModuleGetAll,
    apiInfoName,
    apiPutCaseSort,
    uiPageStepsDetailedAss,
    apiPutRefreshApiInfo,
  } from '@/api/url'
  import { useRoute } from 'vue-router'
  import { useTestObj } from '@/store/modules/get-test-obj'
  import { getFormItems } from '@/utils/datacleaning'
  import { FormItem, ModalDialogType } from '@/types/components'
  import { fieldNames } from '@/setting'
  import { Message, Modal } from '@arco-design/web-vue'
  import { usePageData } from '@/store/page-data'

  const testObj = useTestObj()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const formModel = ref({})
  const pageData = usePageData()

  const route = useRoute()
  const apiCaseData: any = reactive({
    actionTitle: '新增接口',
    position: 'request',
    disabled: true,
    tabsKey: 0,
    selectDataObj: {},
    data: [],
    selectData: [],
    clientType: [],
    methodType: [],
    moduleList: [],
    apiList: [],
    ass: [],
  })
  const columns = reactive([
    {
      title: '接口名称',
      dataIndex: 'name',
    },

    {
      title: '请求方法',
      dataIndex: 'method',
    },
    {
      title: '端类型',
      dataIndex: 'client',
    },
    {
      title: '测试结果',
      dataIndex: 'status',
    },
    {
      title: '操作',
      dataIndex: 'actions',
      align: 'center',
      width: 220,
    },
  ])
  const formItems: FormItem[] = reactive([
    {
      label: '模块',
      key: 'module_name',
      value: '',
      placeholder: '请选择测试模块',
      required: true,
      type: 'select',
      validator: function () {
        if (!this.value) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '接口',
      key: 'api_info',
      value: '',
      placeholder: '请选择测试模块',
      required: true,
      type: 'select',
      validator: function () {
        if (!this.value) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
  ])

  function clickRadioGroup() {
    for (let key in apiCaseData.selectDataObj) {
      if (key === apiCaseData.position) {
        apiCaseData.selectData = apiCaseData.selectDataObj[key]
        break
      }
    }
  }

  function blurSave(item: any) {
    let data: any = {
      id: apiCaseData.selectDataObj.id,
    }
    if (
      [2, 3, 4, 5].includes(item.key) &&
      typeof item.data !== 'number' &&
      item.data !== null &&
      item.data !== ''
    ) {
      try {
        data[item.name] = JSON.parse(item.data)
        if (data[item.name] && typeof data[item.name] === 'object') {
        } else {
          throw new Error('Invalid JSON data')
        }
      } catch (e) {
        Message.error(`字段：${item.title}，转换JSON失败，请检查数据`)
        return
      }
    } else {
      data[item.name] = item.data
    }
    put({
      url: apiCaseDetailed,
      data: () => {
        return data
      },
    })
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  function removeFrontSql(item: any, index: number) {
    item.data.splice(index, 1)
    blurSave(item)
  }

  function getUiRunSortAss() {
    get({
      url: uiPageStepsDetailedAss,
      data: () => {
        return {}
      },
    })
      .then((res) => {
        apiCaseData.ass = res.data
      })
      .catch(console.log)
  }

  function doMethodType() {
    get({
      url: systemEnumMethod,
    })
      .then((res) => {
        res.data.forEach((item: any) => {
          apiCaseData.methodType.push(item.title)
        })
      })
      .catch(console.log)
  }

  function doClientType() {
    get({
      url: systemEnumEnd,
    })
      .then((res) => {
        res.data.forEach((item: any) => {
          apiCaseData.clientType.push(item.title)
        })
      })
      .catch(console.log)
  }

  function doRefresh(test_suite: any = null) {
    let test_suite_id = route.query.test_suite_id
    if (test_suite) {
      test_suite_id = test_suite
    }
    get({
      url: apiCaseDetailed,
      data: () => {
        return {
          case_id: route.query.case_id,
          test_suite_id: test_suite_id,
        }
      },
    })
      .then((res) => {
        apiCaseData.data = res.data
        if (res.data.length !== 0) {
          apiCaseData.selectDataObj = res.data[0]
          apiCaseData.selectData = res.data[0][apiCaseData.position]
        }
      })
      .catch(console.log)
  }

  function caseRun(case_sort: number | null) {
    Message.loading('用例开始执行中~')
    get({
      url: apiRun,
      data: () => {
        return {
          case_id: route.query.case_id,
          test_obj_id: testObj.selectValue,
          case_sort: case_sort,
          project_id: route.query.project,
        }
      },
    })
      .then((res) => {
        Message.success(res.msg)
        doRefresh(res.data.test_suite)
      })
      .catch(console.log)
  }

  function getProjectModule(projectId: any) {
    get({
      url: userProjectModuleGetAll,
      data: () => {
        return {
          project_id: projectId,
        }
      },
    })
      .then((res) => {
        apiCaseData.moduleList = res.data
      })
      .catch(console.log)
  }

  function getModuleApi(moduleId: number) {
    get({
      url: apiInfoName,
      data: () => {
        return {
          module_id: moduleId,
        }
      },
    })
      .then((res) => {
        apiCaseData.apiList = res.data
      })
      .catch(console.log)
  }

  const handleChange = (_data: any) => {
    apiCaseData.data = _data
    let data: any = []
    apiCaseData.data.forEach((item: any, index: any) => {
      data.push({
        id: item.id,
        case_sort: index,
      })
    })
    put({
      url: apiPutCaseSort,
      data: () => {
        return {
          case_sort_list: data,
        }
      },
    })
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      modalDialogRef.value?.toggle()
      let value = getFormItems(formItems)
      post({
        url: apiCaseDetailed,
        data: () => {
          value['case'] = route.query.case_id
          value['case_sort'] = apiCaseData.data.length
          value['front_sql'] = []
          value['ass_sql'] = []
          value['ass_response_value'] = []
          value['posterior_sql'] = []
          value['posterior_response'] = []
          value['dump_data'] = []
          return value
        },
      })
        .then((res) => {
          Message.success(res.msg)
          doRefresh()
        })
        .catch(console.log)
    }
  }

  function onDelete(data: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此接口？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleted({
          url: apiCaseDetailed,
          data: () => {
            return {
              id: data.id,
              parent_id: route.query.case_id,
            }
          },
        })
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function addApiInfo() {
    apiCaseData.actionTitle = '添加接口到用例'
    modalDialogRef.value?.toggle()
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = ''
      }
    })
  }

  function doResetSearch() {
    window.history.back()
  }

  function refresh(id: number) {
    put({
      url: apiPutRefreshApiInfo,
      data: () => {
        return {
          id: id,
        }
      },
    })
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function select(record: any) {
    apiCaseData.selectDataObj = record
    for (let key in record) {
      if (key === apiCaseData.position) {
        apiCaseData.selectData = record[apiCaseData.position]
      }
    }
  }

  function tabsChange(key: number) {
    apiCaseData.disabled = false
    const list = [10, 30, 32, 40, 41, 50]
    if (!list.includes(key)) {
      apiCaseData.disabled = true
    }
    apiCaseData.tabsKey = key
  }

  function clickAdd() {
    for (let obj of apiCaseData.selectData) {
      if (obj.key === apiCaseData.tabsKey) {
        if ([10, 50].includes(apiCaseData.tabsKey)) {
          obj.data.push('请添加sql语句')
        } else if ([30, 32].includes(apiCaseData.tabsKey)) {
          obj.data.push({ value: '', method: '', expect: '' })
        } else if ([40, 41].includes(apiCaseData.tabsKey)) {
          obj.data.push({ key: '', value: '' })
        }
      }
    }
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      doMethodType()
      doClientType()
      getProjectModule(route.query.project)
      getUiRunSortAss()
    })
  })
</script>

<style>
  .container {
    display: flex; /* 开启flex布局 */
  }

  .left {
    width: 55%; /* 左边区域占据50%的宽度 */
    margin-right: 10px; /* 设置左边盒子的右边距 */
  }

  .right {
    width: 45%; /* 右边区域占据50%的宽度 */
    margin-left: 10px; /* 设置右边盒子的左边距 */
  }
</style>
