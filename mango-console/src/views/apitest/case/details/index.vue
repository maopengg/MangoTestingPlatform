<template>
  <div>
    <a-card title="组合用例场景">
      <template #extra>
        <a-space>
          <a-button type="primary" status="warning" size="small" @click="doResetSearch"
            >返回
          </a-button>
        </a-space>
      </template>
      <div class="container">
        <a-space direction="vertical" style="width: 50%">
          <span>用例ID：{{ pageData.record.id }}</span>
          <span>所属项目：{{ pageData.record.project_product?.project?.name }}</span>
          <span>顶级模块：{{ pageData.record.module?.superior_module }}</span>
          <span>所属模块：{{ pageData.record.module?.name }}</span>
        </a-space>
        <a-space direction="vertical" style="width: 50%">
          <span>用例名称：{{ pageData.record.name }}</span>
          <span>用例负责人：{{ pageData.record.case_people?.name }}</span>
          <span>执行顺序：{{ pageData.record.case_flow }}</span>
        </a-space>
      </div>
    </a-card>
    <a-card>
      <div class="container">
        <div class="left">
          <a-tabs :active-key="data.apiType" @tab-click="(key) => switchType(key)">
            <template #extra>
              <a-space>
                <a-button
                  status="success"
                  size="small"
                  v-if="data.apiType === '2'"
                  @click="caseRun(null)"
                  >全部执行</a-button
                >
                <a-button type="primary" size="small" @click="addData">增加</a-button>
              </a-space>
            </template>
            <a-tab-pane key="1" title="前置数据">
              <a-tabs
                :default-active-key="data.apiSonType"
                @tab-click="(key) => switchSonType(key)"
                position="left"
              >
                <a-tab-pane key="11" title="自定义变量">
                  <a-space direction="vertical">
                    <a-space v-for="(item, index) of pageData.record.front_custom" :key="item.key">
                      <span>key</span>
                      <a-input
                        v-model="item.key"
                        placeholder="请输入key的名称"
                        @blur="upDataCase"
                      />
                      <span>value</span>
                      <a-input
                        v-model="item.value"
                        placeholder="请输入value的名称"
                        @blur="upDataCase"
                      />
                      <a-button
                        type="text"
                        size="small"
                        status="danger"
                        @click="removeFrontSql1(pageData.record.front_custom, index)"
                        >移除
                      </a-button>
                    </a-space>
                  </a-space>
                </a-tab-pane>
                <a-tab-pane key="12" title="sql变量">
                  <a-space direction="vertical">
                    <a-space v-for="(item, index) of pageData.record.front_sql" :key="item.sql">
                      <span>sql语句</span>
                      <a-input v-model="item.sql" placeholder="请输入sql语句" @blur="upDataCase" />
                      <span>key列表</span>
                      <a-input
                        v-model="item.key_list"
                        placeholder="请输入查询结果缓存key"
                        @blur="upDataCase"
                      />
                      <a-button
                        type="text"
                        size="small"
                        status="danger"
                        @click="removeFrontSql1(pageData.record.front_sql, index)"
                        >移除
                      </a-button>
                    </a-space>
                  </a-space>
                </a-tab-pane>
                <a-tab-pane key="13" title="默认请求头">
                  <a-space direction="vertical">
                    <a-checkbox-group
                      direction="vertical"
                      v-model="pageData.record.front_headers"
                      @change="changeHeaders"
                      v-for="item of data.headers_list"
                      :key="item.id"
                    >
                      <a-checkbox :value="item.id">
                        {{ item.key + ': ' + item.value }}
                      </a-checkbox>
                    </a-checkbox-group>
                  </a-space>
                </a-tab-pane>
              </a-tabs>
            </a-tab-pane>

            <a-tab-pane key="2" title="用例步骤">
              <a-table
                :columns="columns"
                :data="data.data"
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
                    <template v-if="item.dataIndex === 'api_name'" #cell="{ record }">
                      {{ record.api_info.name }}
                    </template>
                    <template v-else-if="item.dataIndex === 'name'" #cell="{ record }">
                      <a-tag>{{ record.name }}</a-tag>
                    </template>
                    <template v-else-if="item.dataIndex === 'status'" #cell="{ record }">
                      <a-tag :color="enumStore.status_colors[record.status]" size="small">{{
                        enumStore.task_status[record.status].title
                      }}</a-tag>
                    </template>
                    <template v-else-if="item.dataIndex === 'actions'" #cell="{ record }">
                      <a-button type="text" size="mini" @click="caseRun(record.case_sort)"
                        >执行到此处
                      </a-button>
                      <a-button type="text" size="mini" @click="refresh(record.id)">刷新</a-button>
                      <a-button status="danger" type="text" size="mini" @click="onDelete(record)"
                        >删除
                      </a-button>
                    </template>
                  </a-table-column>
                </template>
              </a-table>
            </a-tab-pane>
            <a-tab-pane key="3" title="后置清除">
              <a-tabs
                :default-active-key="data.apiSonType"
                @tab-click="(key) => switchSonType(key)"
                position="left"
              >
                <a-tab-pane key="31" title="sql清除">
                  <a-space direction="vertical">
                    <a-space v-for="(item, index) of pageData.record.posterior_sql" :key="item.sql">
                      <span>sql语句</span>
                      <a-input v-model="item.sql" placeholder="请输入sql语句" @blur="upDataCase" />
                      <a-button
                        type="text"
                        size="small"
                        status="danger"
                        @click="removeFrontSql1(pageData.record.posterior_sql, index)"
                        >移除
                      </a-button>
                    </a-space>
                  </a-space>
                </a-tab-pane>
              </a-tabs>
            </a-tab-pane>
          </a-tabs>
        </div>
        <div class="right">
          <a-space direction="vertical" fill>
            <a-space style="display: flex; justify-content: flex-end">
              <a-button type="primary" size="small" @click="addData">增加</a-button>
            </a-space>
            <a-collapse
              :default-active-key="[1]"
              accordion
              :bordered="false"
              v-for="item of data.selectDataObj.parameter"
              :key="item.id"
            >
              <a-collapse-item :header="item.name" key="1">
                <div>
                  <a-tabs
                    @tab-click="(key) => switchApiInfoType(key)"
                    :active-key="data.caseDetailsTypeKey"
                    position="left"
                  >
                    <a-tab-pane key="0" title="请求配置">
                      <a-tabs @tab-click="(key) => tabsChange(key)" :active-key="data.tabsKey">
                        <a-tab-pane key="00" title="请求头">
                          <a-space direction="vertical">
                            <a-checkbox-group
                              direction="vertical"
                              v-model="item.header"
                              @change="changeHeadersApi"
                              v-for="header of data.headers_list"
                              :key="header.id"
                            >
                              <a-checkbox :value="header.id">
                                {{ header.key + ': ' + header.value }}
                              </a-checkbox>
                            </a-checkbox-group>
                          </a-space>
                        </a-tab-pane>
                        <a-tab-pane key="01" title="参数">
                          <a-textarea
                            placeholder="请输入参数，json格式"
                            v-model="item.params"
                            allow-clear
                            auto-size
                            @blur="blurSave('params', item.params, item.id)"
                          />
                        </a-tab-pane>
                        <a-tab-pane key="02" title="表单">
                          <a-textarea
                            placeholder="请输入表单，json格式"
                            v-model="item.data"
                            allow-clear
                            auto-size
                            @blur="blurSave('data', item.data, item.id)"
                          />
                        </a-tab-pane>
                        <a-tab-pane key="03" title="JSON">
                          <a-textarea
                            placeholder="请输入JSON，json格式"
                            v-model="item.json"
                            allow-clear
                            auto-size
                            @blur="blurSave('json', item.json, item.id)"
                          />
                        </a-tab-pane>
                        <a-tab-pane key="04" title="file">
                          <a-textarea
                            placeholder="请输入file，json格式"
                            v-model="item.file"
                            allow-clear
                            auto-size
                            @blur="blurSave('file', item.file, item.id)"
                          />
                        </a-tab-pane>
                      </a-tabs>
                    </a-tab-pane>
                    <a-tab-pane key="1" title="前置处理">
                      <a-tabs @tab-click="(key) => tabsChange(key)" :active-key="data.tabsKey">
                        <template #extra>
                          <a-space>
                            <a-button type="primary" size="small" @click="clickAdd">增加</a-button>
                          </a-space>
                        </template>
                        <a-tab-pane key="10" title="前置sql">
                          <a-space direction="vertical" fill>
                            <a-space v-for="(inputObj, index) of item.front_sql" :key="index">
                              <a-space>
                                <a-input
                                  placeholder="请输入前置sql语句"
                                  v-model="item.front_sql[index]"
                                  @blur="blurSave('front_sql', item.front_sql, item.id)"
                                />
                                <a-button
                                  type="text"
                                  size="small"
                                  status="danger"
                                  @click="
                                    removeFrontSql(item.front_sql, index, 'front_sql', item.id)
                                  "
                                  >移除
                                </a-button>
                              </a-space>
                            </a-space>
                          </a-space>
                        </a-tab-pane>
                      </a-tabs>
                    </a-tab-pane>
                    <a-tab-pane key="2" title="响应结果">
                      <a-tabs @tab-click="(key) => tabsChange(key)" :active-key="data.tabsKey">
                        <a-tab-pane key="20" title="基础信息">
                          <a-space direction="vertical">
                            <span>URL：{{ data.result_data?.request?.url }}</span>
                            <span>响应code：{{ data.result_data?.response?.status_code }}</span>
                            <span>响应时间：{{ data.result_data?.response?.response_time }}</span>
                            <span>失败原因：{{ data.result_data?.error_message }}</span>
                          </a-space>
                        </a-tab-pane>
                        <a-tab-pane key="21" title="请求头">
                          <pre>{{ strJson(data.result_data?.request?.headers) }}</pre>
                        </a-tab-pane>
                        <a-tab-pane key="22" title="响应头">
                          <pre>{{ strJson(data.result_data?.response?.response_headers) }}</pre>
                        </a-tab-pane>
                        <a-tab-pane key="23" title="响应体">
                          <pre>{{ strJson(data.result_data?.response?.response_text) }}</pre>
                        </a-tab-pane>
                      </a-tabs>
                    </a-tab-pane>
                    <a-tab-pane key="3" title="接口断言">
                      <a-tabs @tab-click="(key) => tabsChange(key)" :active-key="data.tabsKey">
                        <template #extra>
                          <a-space>
                            <a-button type="primary" size="small" @click="clickAdd">增加</a-button>
                          </a-space>
                        </template>
                        <a-tab-pane key="30" title="响应一致断言">
                          <a-textarea
                            placeholder="请输入全部响应结果，将对响应结果进行字符串一致性断言"
                            v-model="item.ass_response_whole"
                            allow-clear
                            :auto-size="{ minRows: 9, maxRows: 9 }"
                            @blur="blurSave('ass_response_whole', item.ass_response_whole)"
                          />
                        </a-tab-pane>
                        <a-tab-pane key="31" title="响应条件断言">
                          <a-space direction="vertical">
                            <a-space v-for="(value, index) of item.ass_response_value" :key="index">
                              <a-input
                                placeholder="请输入jsonpath表达式"
                                v-model="item.ass_response_value[index].actual"
                                @blur="
                                  blurSave('ass_response_value', item.ass_response_value, item.id)
                                "
                              />
                              <a-cascader
                                v-model="item.ass_response_value[index].method"
                                :options="data.ass"
                                :default-value="item.ass_response_value[index].method"
                                expand-trigger="hover"
                                placeholder="请选择断言方法"
                                value-key="key"
                                @blur="
                                  blurSave('ass_response_value', item.ass_response_value, item.id)
                                "
                              />
                              <a-input
                                placeholder="请输入想要判断的值"
                                v-model="item.ass_response_value[index].expect"
                                @blur="
                                  blurSave('ass_response_value', item.ass_response_value, item.id)
                                "
                              />
                              <a-button
                                type="text"
                                status="danger"
                                @click="
                                  removeFrontSql(
                                    item.ass_response_value,
                                    index,
                                    'ass_response_value',
                                    item.id
                                  )
                                "
                                >移除
                              </a-button>
                            </a-space>
                          </a-space>
                        </a-tab-pane>
                        <a-tab-pane key="32" title="sql条件断言">
                          <a-space direction="vertical">
                            <a-space v-for="(value, index) of item.ass_sql" :key="index">
                              <a-input
                                placeholder="请输入sql查询语句，只能查询一个字段"
                                v-model="item.ass_sql[index].actual"
                                @blur="blurSave('ass_sql', item.ass_sql, item.id)"
                              />
                              <a-cascader
                                v-model="item.ass_sql[index].method"
                                :options="data.ass"
                                :default-value="item.ass_sql[index].method"
                                expand-trigger="hover"
                                placeholder="请选择断言方法"
                                value-key="key"
                                @blur="blurSave('ass_sql', item.ass_sql, item.id)"
                              />
                              <a-input
                                placeholder="请输入想要判断的值"
                                v-model="item.ass_sql[index].expect"
                                @blur="blurSave('ass_sql', item.ass_sql, item.id)"
                              />
                              <a-button
                                type="text"
                                status="danger"
                                @click="removeFrontSql(item.ass_sql, index, 'ass_sql', item.id)"
                                >移除
                              </a-button>
                            </a-space>
                          </a-space>
                        </a-tab-pane>
                      </a-tabs>
                    </a-tab-pane>
                    <a-tab-pane key="4" title="后置处理">
                      <a-tabs @tab-click="(key) => tabsChange(key)" :active-key="data.tabsKey">
                        <template #extra>
                          <a-space>
                            <a-button type="primary" size="small" @click="clickAdd">增加</a-button>
                          </a-space>
                        </template>
                        <a-tab-pane key="40" title="响应结果提取">
                          <a-space direction="vertical">
                            <a-space v-for="(value, index) of item.posterior_response" :key="index">
                              <a-input
                                placeholder="请输入jsonpath语法"
                                v-model="item.posterior_response[index].key"
                                @blur="
                                  blurSave('posterior_response', item.posterior_response, item.id)
                                "
                              />
                              <a-input
                                placeholder="请输入缓存key"
                                v-model="item.posterior_response[index].value"
                                @blur="
                                  blurSave('posterior_response', item.posterior_response, item.id)
                                "
                              />

                              <a-button
                                type="text"
                                size="small"
                                status="danger"
                                @click="
                                  removeFrontSql(
                                    item.posterior_response,
                                    index,
                                    'posterior_response',
                                    item.id
                                  )
                                "
                                >移除
                              </a-button>
                            </a-space>
                          </a-space>
                        </a-tab-pane>
                        <a-tab-pane key="41" title="后置sql处理">
                          <a-space direction="vertical">
                            <a-space direction="vertical">
                              <a-space v-for="(value, index) of item.posterior_sql" :key="index">
                                <a-input
                                  placeholder="请输入sql"
                                  v-model="item.posterior_sql[index].key"
                                  @blur="blurSave('posterior_sql', item.posterior_sql, item.id)"
                                />
                                <a-input
                                  placeholder="请输入缓存key，删除语句则不用"
                                  v-model="item.posterior_sql[index].value"
                                  @blur="blurSave('posterior_sql', item.posterior_sql, item.id)"
                                />

                                <a-button
                                  type="text"
                                  size="small"
                                  status="danger"
                                  @click="
                                    removeFrontSql(
                                      item.posterior_sql,
                                      index,
                                      'posterior_sql',
                                      item.id
                                    )
                                  "
                                  >移除
                                </a-button>
                              </a-space>
                            </a-space>
                          </a-space>
                        </a-tab-pane>
                        <a-tab-pane key="42" title="强制等待">
                          <a-space direction="vertical">
                            <a-space direction="vertical">
                              <a-input
                                placeholder="请输入强制等待时间，单位是秒"
                                v-model="item.posterior_sleep"
                                @blur="blurSave('posterior_sleep', item.posterior_sleep, item.id)"
                                style="width: 300px"
                              />
                            </a-space>
                          </a-space>
                        </a-tab-pane>
                      </a-tabs>
                    </a-tab-pane>
                    <a-tab-pane key="5" title="缓存数据">
                      <pre>{{ strJson(data.result_data?.cache_data) }}</pre>
                    </a-tab-pane>
                  </a-tabs>
                </div>
              </a-collapse-item>
            </a-collapse>
          </a-space>
        </div>
      </div>
    </a-card>
  </div>
  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
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
          <template v-else-if="item.type === 'cascader' && item.key === 'module'">
            <a-cascader
              v-model="item.value"
              @change="getModuleApi(item.value)"
              :placeholder="item.placeholder"
              :options="data.productModuleName"
              allow-search
              allow-clear
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'api_info'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="data.apiList"
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
  import { useRoute } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'
  import { ModalDialogType } from '@/types/components'
  import { fieldNames } from '@/setting'
  import { Message, Modal } from '@arco-design/web-vue'
  import { usePageData } from '@/store/page-data'
  import { formatJson, formatJsonObj, strJson } from '@/utils/tools'
  import { formItems, columns } from './config'
  import { putApiCase, getApiCaseRun } from '@/api/apitest/case'
  import {
    getApiCaseDetailed,
    putApiCaseDetailed,
    deleteApiCaseDetailed,
    postApiCaseDetailed,
    putApiPutCaseSort,
    putApiPutRefreshApiInfo,
  } from '@/api/apitest/case_detailed'
  import { getApiInfoName } from '@/api/apitest/info'
  import { getUiPageStepsDetailedAss } from '@/api/uitest/page-steps-detailed'
  import { getUserProductAllModuleName } from '@/api/system/product'
  import useUserStore from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import { getApiHeaders } from '@/api/apitest/headers'
  import { putApiCaseDetailedParameter } from '@/api/apitest/case-detailed-parameter'

  const userStore = useUserStore()

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const formModel = ref({})
  const pageData: any = usePageData()
  const enumStore = useEnum()

  const route = useRoute()
  const data: any = reactive({
    actionTitle: '新增接口',
    request: {
      headers: null,
      params: null,
      data: null,
      json: null,
      file: null,
    },
    result_data: {},
    results: null,
    selectDataObj: {},
    data: [],
    methodType: [],
    productModuleName: [],
    apiList: [],
    ass: [],
    caseHeadersList: [],
    caseDetailsHeadersList: [],
    apiType: '2',
    apiSonType: '0',
    caseDetailsTypeKey: '0',
    tabsKey: '10',
  })

  function switchType(key: any) {
    if (key === '1') {
      data.apiSonType = '11'
    } else if (key === '3') {
      data.apiSonType = '31'
    }
    data.apiType = key
  }

  function switchApiInfoType(key: any) {
    data.caseDetailsTypeKey = key
    if (key === '0') {
    } else if (key === '1') {
      data.tabsKey = '10'
    } else if (key === '2') {
      data.tabsKey = '23'
    } else if (key === '3') {
      data.tabsKey = '30'
    } else if (key === '4') {
      data.tabsKey = '40'
    } else if (key === '5') {
      data.tabsKey = '50'
    }
  }
  function changeHeaders(selectedValues: any) {
    const value = {
      id: pageData.record.id,
      front_headers: selectedValues,
    }
    putApiCase(value)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }
  function changeHeadersApi(selectedValues: any) {
    if (Object.keys(data.selectDataObj.header).length !== 0) {
      putApiCaseDetailed({ id: data.selectDataObj.id, header: selectedValues }, route.query.case_id)
        .then((res) => {
          Message.success(res.msg)
        })
        .catch(console.log)
    }
  }
  function switchSonType(key: any) {
    data.apiSonType = key
  }

  function addData() {
    if (data.apiType == '2') {
      addApiInfo()
      return
    }
    if (data.apiSonType === '11') {
      pageData.record.front_custom.push({ key: '', value: '' })
    } else if (data.apiSonType === '12') {
      pageData.record.front_sql.push({ sql: '', key_list: '' })
    } else if (data.apiSonType === '31') {
      pageData.record.posterior_sql.push({ sql: '' })
    }
  }

  function removeFrontSql1(item: any, index: number) {
    item.splice(index, 1)

    upDataCase()
  }

  function upDataCase() {
    putApiCase({
      id: pageData.record.id,
      name: pageData.record.name,
      posterior_sql: pageData.record.posterior_sql,
      front_sql: pageData.record.front_sql,
      front_custom: pageData.record.front_custom,
      front_headers: pageData.record.front_headers,
    })
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function blurSave(key: string, item: string | null, id: number) {
    const serialize = ['url', 'header', 'posterior_sleep']
    if (item === '') {
      item = null
    }
    const jsonValue = !serialize.includes(key) ? formatJsonObj(key, item) : item
    if (jsonValue === false) {
      return
    }
    const payload = {
      id: id,
      [key]: jsonValue,
    }
    putApiCaseDetailedParameter(payload)
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
    if (typeof data.selectDataObj.ass_response_whole == 'object') {
      data.selectDataObj['ass_response_whole'] = formatJson(data.selectDataObj.ass_response_whole)
    }
  }

  function removeFrontSql(item: any, index: number, key: string, id: number) {
    item.splice(index, 1)
    blurSave(key, item, id)
  }

  function getUiRunSortAss() {
    getUiPageStepsDetailedAss(null)
      .then((res) => {
        data.ass = res.data
      })
      .catch(console.log)
  }

  function doRefresh() {
    data.caseHeadersList = pageData.record.front_headers
    getApiCaseDetailed(route.query.case_id)
      .then((res) => {
        data.data = res.data
        if (res.data.length !== 0) {
          select(res.data[0])
        }
      })
      .catch(console.log)
  }
  function doRefreshHeaders() {
    const value = {
      page: 1,
      pageSize: 10000,
      project_product_id: route.query.project_product,
    }
    getApiHeaders(value)
      .then((res) => {
        data.headers_list = res.data
      })
      .catch(console.log)
  }

  function caseRun(case_sort: number | null) {
    Message.loading('用例开始执行中~')
    getApiCaseRun(route.query.case_id, userStore.selected_environment, case_sort)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function onProductModuleName() {
    getUserProductAllModuleName(pageData.record.project_product?.project?.id)
      .then((res) => {
        data.productModuleName = res.data
      })
      .catch(console.log)
  }

  function getModuleApi(moduleId: number) {
    getApiInfoName(moduleId)
      .then((res) => {
        data.apiList = res.data
      })
      .catch(console.log)
  }

  const handleChange = (_data: any) => {
    data.data = _data
    let data1: any = []
    data.data.forEach((item: any, index: any) => {
      data1.push({
        id: item.id,
        case_sort: index,
      })
    })
    putApiPutCaseSort(data1)
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      modalDialogRef.value?.toggle()
      let value = getFormItems(formItems)
      value['case'] = route.query.case_id
      value['case_sort'] = data.data.length
      value['front_sql'] = []
      value['ass_sql'] = []
      value['ass_response_value'] = []
      value['posterior_sql'] = []
      value['posterior_response'] = []
      value['header'] = []
      postApiCaseDetailed(value, route.query.case_id)
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
        deleteApiCaseDetailed(data.id, route.query.case_id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function addApiInfo() {
    data.actionTitle = '添加接口到用例'
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
    putApiPutRefreshApiInfo(id)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function select(record: any) {
    if (record) {
      data.selectDataObj = record
      data.result_data = record.result_data
      const formatItemData = (item: any) => {
        const propertiesToFormat = ['ass_response_whole', 'data', 'params', 'json', 'file']

        propertiesToFormat.forEach((prop) => {
          if (typeof item[prop] === 'object') {
            item[prop] = formatJson(item[prop])
          }
        })
      }
      data.selectDataObj.parameter.forEach((item: any) => {
        formatItemData(item)
      })
    }
    switchApiInfoType(data.caseDetailsTypeKey)
  }

  function tabsChange(key: string | any) {
    data.tabsKey = key
  }

  function clickAdd() {
    if ('10' === data.tabsKey) {
      data.selectDataObj.front_sql.push('请添加sql语句')
    } else if ('31' === data.tabsKey) {
      data.selectDataObj.ass_response_value.push({ actual: '', method: '', expect: '' })
    } else if ('32' === data.tabsKey) {
      data.selectDataObj.ass_sql.push({ actual: '', method: '', expect: '' })
    } else if ('40' === data.tabsKey) {
      data.selectDataObj.posterior_response.push({ key: '', value: '' })
    } else if ('41' === data.tabsKey) {
      data.selectDataObj.posterior_sql.push({ key: '', value: '' })
    }
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      doRefreshHeaders()
      onProductModuleName()
      getUiRunSortAss()
    })
  })
</script>

<style>
  .container {
    display: flex; /* 开启flex布局 */
  }

  .left {
    width: 45%; /* 左边区域占据50%的宽度 */
    margin-right: 10px; /* 设置左边盒子的右边距 */
  }

  .right {
    width: 55%; /* 右边区域占据50%的宽度 */
    margin-left: 10px; /* 设置右边盒子的左边距 */
  }
</style>
