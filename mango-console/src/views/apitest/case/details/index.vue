<template>
  <TableBody ref="tableBody">
    <template #header>
      <a-card :bordered="false" title="组合用例场景">
        <template #extra>
          <a-space>
            <a-button
              size="small"
              status="success"
              :loading="caseRunning"
              :disabled="caseRunning"
              @click="caseRun(null)"
            >
              执行
            </a-button>
            <a-button size="small" status="warning" type="primary" @click="doResetSearch"
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
    </template>
    <template #default>
      <a-card :bordered="false">
        <div class="main_box">
          <div class="left">
            <a-tabs :active-key="data.apiType" @tab-click="(key) => switchType(key)">
              <template #extra>
                <a-space>
                  <a-button size="small" type="primary" @click="addData">增加</a-button>
                </a-space>
              </template>
              <a-tab-pane key="1" title="用例前置">
                <a-tabs position="left" @tab-click="(key) => switchSonType(key)">
                  <a-tab-pane key="11" title="自定义参数">
                    <KeyValueList
                      :data-list="pageData.record.front_custom"
                      :field-config="[
                        { field: 'key', label: 'Key', placeholder: '请输入key' },
                        { field: 'value', label: 'Value', placeholder: '请输入value' },
                      ]"
                      :on-delete-item="
                        (index) => removeFrontSql1(pageData.record.front_custom, index)
                      "
                      :on-save="upDataCase"
                      @update:item="
                        (index, value) =>
                          updateArrayItem(
                            pageData.record.front_custom,
                            index,
                            value,
                            pageData.record,
                            'front_custom',
                            upDataCase
                          )
                      "
                    />
                  </a-tab-pane>
                  <a-tab-pane key="12" title="sql参数">
                    <KeyValueList
                      :data-list="pageData.record.front_sql"
                      :field-config="[
                        {
                          field: 'key',
                          label: 'Key',
                          placeholder: '请输入key,示例：key1,key2',
                        },
                        { field: 'value', label: 'Sql语句', placeholder: '请输入sql语句' },
                      ]"
                      :on-delete-item="(index) => removeFrontSql1(pageData.record.front_sql, index)"
                      :on-save="upDataCase"
                      @update:item="
                        (index, value) =>
                          updateArrayItem(
                            pageData.record.front_sql,
                            index,
                            value,
                            pageData.record,
                            'front_sql',
                            upDataCase
                          )
                      "
                    />
                  </a-tab-pane>
                  <a-tab-pane key="13" title="默认请求头">
                    <a-space direction="vertical">
                      <a-checkbox-group
                        v-for="item of data.headers_list"
                        :key="item.id"
                        v-model="pageData.record.front_headers"
                        direction="vertical"
                        @change="changeHeaders"
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
                  :bordered="true"
                  :columns="columns"
                  :data="data.data"
                  :draggable="{ type: 'handle', width: 40 }"
                  :pagination="false"
                  @change="handleChange"
                  @row-click="select"
                >
                  <template #columns>
                    <a-table-column
                      v-for="item of columns"
                      :key="item.key"
                      :align="item.align"
                      :data-index="item.dataIndex"
                      :fixed="item.fixed"
                      :title="item.title"
                      :width="item.width"
                    >
                      <template v-if="item.dataIndex === 'api_name'" #cell="{ record }">
                        {{ record.api_info.name }}
                      </template>
                      <template v-else-if="item.dataIndex === 'name'" #cell="{ record }">
                        <a-tag>{{ record.name }}</a-tag>
                      </template>
                      <template v-else-if="item.dataIndex === 'status'" #cell="{ record }">
                        <a-tag :color="enumStore.status_colors[record.status]" size="small"
                          >{{ enumStore.task_status[record.status].title }}
                        </a-tag>
                      </template>
                      <template v-else-if="item.dataIndex === 'actions'" #cell="{ record }">
                        <a-button
                          size="mini"
                          type="text"
                          :loading="caseRunning"
                          @click="caseRun(record.case_sort)"
                          class="custom-mini-btn"
                        >
                          执行到这
                        </a-button>
                        <a-button
                          size="mini"
                          type="text"
                          @click="refresh(record.id)"
                          class="custom-mini-btn"
                        >
                          同步
                        </a-button>
                        <a-button
                          size="mini"
                          status="danger"
                          type="text"
                          @click="onDelete(record)"
                          class="custom-mini-btn"
                        >
                          删除
                        </a-button>
                      </template>
                    </a-table-column>
                  </template>
                </a-table>
              </a-tab-pane>
              <a-tab-pane key="3" title="用例后置">
                <a-tabs position="left" @tab-click="(key) => switchSonType(key)">
                  <a-tab-pane key="31" title="sql参数">
                    <KeyValueList
                      :data-list="pageData.record.posterior_sql"
                      :field-config="[
                        {
                          field: 'key',
                          label: 'Key（不会显示到缓存数据中）',
                          placeholder: '请输入key，可以为空',
                        },
                        { field: 'value', label: 'Sql语句', placeholder: '请输入sql语句' },
                      ]"
                      :on-delete-item="
                        (index) => removeFrontSql1(pageData.record.posterior_sql, index)
                      "
                      :on-save="upDataCase"
                      empty-text='暂无sql参数语句，点击上方"增加"按钮添加'
                      @update:item="
                        (index, value) =>
                          updateArrayItem(
                            pageData.record.posterior_sql,
                            index,
                            value,
                            pageData.record,
                            'posterior_sql',
                            upDataCase
                          )
                      "
                    />
                  </a-tab-pane>
                </a-tabs>
              </a-tab-pane>
            </a-tabs>
          </div>
          <div class="right">
            <a-space direction="vertical" fill>
              <a-space style="display: flex; justify-content: flex-end">
                <a-button size="small" type="primary" @click="addParameter">增加</a-button>
              </a-space>
              <a-space direction="vertical" fill>
                <a-collapse :bordered="false" :default-active-key="[0]" accordion>
                  <a-collapse-item v-for="(item, index) of data.selectDataObj" :key="index">
                    <template #header>
                      <div class="custom-header">
                        <span>{{ '场景名称：' + item.name }}</span>
                        <span style="width: 20px"></span>
                        <a-tag :color="enumStore.status_colors[item.status]"
                          >{{ enumStore.task_status[item.status].title }}
                        </a-tag>
                        <a-tag color="purple">
                          {{
                            item.error_retry
                              ? `重试 ${item.error_retry} 次，每次间隔 ${
                                  item.retry_interval ? item.retry_interval : 0
                                } 秒`
                              : '不重试'
                          }}
                        </a-tag>
                      </div>
                    </template>
                    <template #extra>
                      <a-button size="mini" type="text" @click.stop="parameterEditing(item)"
                        >编辑
                      </a-button>
                      <a-button
                        size="mini"
                        status="danger"
                        type="text"
                        @click.stop="parameterDelete(item)"
                        >删除
                      </a-button>
                    </template>
                    <div>
                      <a-tabs
                        :active-key="data.caseDetailsTypeKey"
                        position="left"
                        @tab-click="(key) => switchApiInfoType(key, item)"
                      >
                        <a-tab-pane key="0" title="请求配置">
                          <a-tabs :active-key="data.tabsKey" @tab-click="(key) => tabsChange(key)">
                            <a-tab-pane key="00" title="请求头">
                              <div class="m-2" style="height: 180px; overflow-y: auto">
                                <a-space direction="vertical" style="width: 100%">
                                  <a-checkbox-group
                                    v-for="header of data.parameter_headers_list"
                                    :key="header.id"
                                    v-model="item.headers"
                                    direction="vertical"
                                    @change="
                                      (selectedValues) => changeHeadersApi(selectedValues, item)
                                    "
                                  >
                                    <a-checkbox :value="header.id">
                                      {{ header.key + ': ' + header.value }}
                                    </a-checkbox>
                                  </a-checkbox-group>
                                </a-space>
                              </div>
                            </a-tab-pane>
                            <a-tab-pane key="01" title="参数">
                              <div class="m-2">
                                <a-textarea
                                  v-model="item.params"
                                  allow-clear
                                  :auto-size="{ minRows: 6 }"
                                  placeholder="请输入参数"
                                  @blur="blurSave('params', item.params, item.id)"
                                />
                              </div>
                            </a-tab-pane>
                            <a-tab-pane key="02" title="表单">
                              <div class="m-2">
                                <a-textarea
                                  v-model="item.data"
                                  allow-clear
                                  :auto-size="{ minRows: 6 }"
                                  placeholder="请输入表单"
                                  @blur="blurSave('data', item.data, item.id)"
                                />
                              </div>
                            </a-tab-pane>
                            <a-tab-pane key="03" title="JSON">
                              <div class="m-2">
                                <a-textarea
                                  v-model="item.json"
                                  allow-clear
                                  :auto-size="{ minRows: 6 }"
                                  placeholder="请输入JSON"
                                  @blur="blurSave('json', item.json, item.id)"
                                />
                              </div>
                            </a-tab-pane>
                            <a-tab-pane key="04" title="文件">
                              <div class="m-2">
                                <a-textarea
                                  v-model="item.file"
                                  allow-clear
                                  :auto-size="{ minRows: 6 }"
                                  placeholder="请输入file，json格式数据"
                                  @blur="blurSave('file', item.file, item.id)"
                                />
                              </div>
                            </a-tab-pane>
                          </a-tabs>
                        </a-tab-pane>
                        <a-tab-pane key="1" title="前置处理">
                          <a-tabs :active-key="data.tabsKey" @tab-click="(key) => tabsChange(key)">
                            <template #extra>
                              <a-space v-if="data.assClickAdd">
                                <a-button size="small" type="primary" @click="clickAdd(item)"
                                  >增加
                                </a-button>
                              </a-space>
                            </template>
                            <a-tab-pane key="10" title="前置sql">
                              <div class="m-2">
                                <KeyValueList
                                  :data-list="item.front_sql"
                                  :field-config="[
                                    {
                                      field: 'key',
                                      label: 'Key',
                                      placeholder: '请输入key',
                                    },
                                    {
                                      field: 'value',
                                      label: 'Sql语句',
                                      placeholder: '请输入sql语句',
                                    },
                                  ]"
                                  :on-delete-item="
                                    (index) =>
                                      removeFrontSql(item.front_sql, index, 'front_sql', item.id)
                                  "
                                  :on-save="() => blurSave('front_sql', item.front_sql, item.id)"
                                  @update:item="
                                    (index, value) =>
                                      updateArrayItem(
                                        item.front_sql,
                                        index,
                                        value,
                                        item,
                                        'front_sql',
                                        () => blurSave('front_sql', item.front_sql, item.id)
                                      )
                                  "
                                  empty-text='暂无前置sql语句，点击上方"增加"按钮添加'
                                />
                              </div>
                            </a-tab-pane>
                            <a-tab-pane key="11" title="前置函数">
                              <div class="m-2">
                                <a-textarea
                                  v-model="item.front_func"
                                  :auto-size="{ minRows: 10, maxRows: 10 }"
                                  allow-clear
                                  placeholder="根据帮助文档，输入自定义前置函数"
                                  @blur="blurSave('front_func', item.front_func, item.id)"
                                />
                              </div>
                            </a-tab-pane>
                          </a-tabs>
                        </a-tab-pane>
                        <a-tab-pane key="2" title="响应结果">
                          <a-tabs :active-key="data.tabsKey" @tab-click="(key) => tabsChange(key)">
                            <a-tab-pane key="20" title="基础信息">
                              <div class="m-2">
                                <a-space direction="vertical">
                                  <span>URL：{{ item.result_data?.request?.url }}</span>
                                  <span>请求方法：{{ item.result_data?.request?.method }}</span>
                                  <span>响应code：{{ item.result_data?.response?.code }}</span>
                                  <span>测试时间：{{ item.result_data?.test_time }}</span>
                                  <span
                                    >响应时间：{{
                                      item.result_data?.response?.time.toFixed(2)
                                    }}
                                    秒</span
                                  >
                                  <span v-if="item.result_data?.error_message"
                                    >失败原因：{{ item.result_data?.error_message }}</span
                                  >
                                </a-space>
                              </div>
                            </a-tab-pane>
                            <a-tab-pane key="21" title="请求头">
                              <div class="m-2">
                                <JsonDisplay :data="item.result_data?.request?.headers" />
                              </div>
                            </a-tab-pane>
                            <a-tab-pane key="25" title="请求数据">
                              <div class="m-2" v-if="item.result_data?.request?.data">
                                <JsonDisplay :data="item.result_data?.request?.data" />
                              </div>
                              <div class="m-2" v-if="item.result_data?.request?.json">
                                <JsonDisplay :data="item.result_data?.request?.json" />
                              </div>
                              <div class="m-2" v-if="item.result_data?.request?.params">
                                <JsonDisplay :data="item.result_data?.request?.params" />
                              </div>
                              <div class="m-2" v-if="item.result_data?.request?.file">
                                <JsonDisplay :data="item.result_data?.request?.file" />
                              </div>
                            </a-tab-pane>
                            <a-tab-pane key="22" title="响应头">
                              <div class="m-2">
                                <JsonDisplay :data="item.result_data?.response?.headers" />
                              </div>
                            </a-tab-pane>
                            <a-tab-pane key="23" title="响应JSON">
                              <div class="m-2">
                                <JsonDisplay
                                  :data="item.result_data?.response?.json"
                                  :jsonpath="true"
                                />
                              </div>
                            </a-tab-pane>
                            <a-tab-pane key="24" title="响应文本">
                              <div class="m-2">
                                <pre v-if="item.result_data?.response?.text">{{ formatResponseText(item.result_data?.response?.text) }}</pre>
                                <span v-else>{{ item.result_data?.response?.text }}</span>
                              </div>
                            </a-tab-pane>
                          </a-tabs>
                        </a-tab-pane>
                        <a-tab-pane key="3" title="接口断言">
                          <a-tabs :active-key="data.tabsKey" @tab-click="(key) => tabsChange(key)">
                            <template #extra>
                              <a-space v-if="data.assClickAdd">
                                <a-button size="small" type="primary" @click="clickAdd(item)">
                                  增加
                                </a-button>
                              </a-space>
                            </template>
                            <a-tab-pane key="30" title="json一致断言">
                              <div class="m-2">
                                <a-textarea
                                  v-model="item.ass_json_all"
                                  :auto-size="{ minRows: 9, maxRows: 9 }"
                                  allow-clear
                                  placeholder="请输入全部响应结果，将对响应结果进行字符串一致性断言"
                                  @blur="blurSave('ass_json_all', item.ass_json_all, item.id)"
                                />
                              </div>
                            </a-tab-pane>
                            <a-tab-pane key="31" title="jsonpath断言">
                              <div class="m-2">
                                <KeyValueList
                                  :data-list="item.ass_jsonpath"
                                  :field-config="[
                                    {
                                      field: 'actual',
                                      label: '实际值',
                                      placeholder: '请输入jsonpath提取的实际结果',
                                    },
                                    {
                                      field: 'method',
                                      label: '断言方法',
                                      type: 'cascader',
                                      options: data.textAss,
                                      placeholder: '请选择断言方法',
                                      expandTrigger: 'hover',
                                      valueKey: 'key',
                                      onChange: (value, currentItem, currentIndex) =>
                                        handleJsonpathMethodChange(
                                          value,
                                          currentItem,
                                          currentIndex,
                                          item
                                        ),
                                    },
                                    {
                                      field: 'expect',
                                      label: '预期值',
                                      placeholder: '请输入预期值',
                                    },
                                  ]"
                                  :on-delete-item="
                                    (index) =>
                                      removeFrontSql(
                                        item.ass_jsonpath,
                                        index,
                                        'ass_jsonpath',
                                        item.id
                                      )
                                  "
                                  :on-save="
                                    () => blurSave('ass_jsonpath', item.ass_jsonpath, item.id)
                                  "
                                  @update:item="
                                    (index, value) =>
                                      updateArrayItem(
                                        item.ass_jsonpath,
                                        index,
                                        value,
                                        item,
                                        'ass_jsonpath',
                                        () => blurSave('ass_jsonpath', item.ass_jsonpath, item.id)
                                      )
                                  "
                                  empty-text='暂无jsonpath断言，点击上方"增加"按钮添加'
                                />
                              </div>
                            </a-tab-pane>
                            <a-tab-pane key="33" title="文本一致断言">
                              <div class="m-2">
                                <a-textarea
                                  v-model="item.ass_text_all"
                                  :auto-size="{ minRows: 9, maxRows: 9 }"
                                  allow-clear
                                  placeholder="请输入全部响应结果，将对响应结果进行字符串一致性断言"
                                  @blur="blurSave('ass_text_all', item.ass_text_all, item.id)"
                                />
                              </div>
                            </a-tab-pane>
                            <a-tab-pane key="32" title="通用断言">
                              <div class="m-2">
                                <KeyValueList
                                  :data-list="item.ass_general"
                                  :field-config="[
                                    {
                                      field: 'method',
                                      label: '断言方法',
                                      type: 'cascader',
                                      options: data.ass,
                                      placeholder: '请选择断言方法',
                                      expandTrigger: 'hover',
                                      valueKey: 'key',
                                      onChange: (value, currentItem, currentIndex) =>
                                        handleGeneralMethodChange(
                                          value,
                                          currentItem,
                                          currentIndex,
                                          item
                                        ),
                                    },
                                  ]"
                                  :on-delete-item="
                                    (index) =>
                                      removeFrontSql(
                                        item.ass_general,
                                        index,
                                        'ass_general',
                                        item.id
                                      )
                                  "
                                  :on-save="
                                    () => blurSave('ass_general', item.ass_general, item.id)
                                  "
                                  @update:item="
                                    (index, value) =>
                                      updateArrayItem(
                                        item.ass_general,
                                        index,
                                        value,
                                        item,
                                        'ass_general',
                                        () => blurSave('ass_general', item.ass_general, item.id)
                                      )
                                  "
                                  empty-text='暂无通用断言，点击上方"增加"按钮添加'
                                >
                                  <template #extra="{ index, item: assItem }">
                                    <div
                                      v-if="assItem?.value && assItem?.value?.parameter"
                                      class="assertion-parameters-inline"
                                    >
                                      <div
                                        v-for="(param, pIdx) in assItem.value.parameter"
                                        :key="param.f"
                                        class="parameter-item-inline"
                                      >
                                        <span class="parameter-label-inline">{{ param.n }}:</span>
                                        <a-textarea
                                          v-model="assItem.value.parameter[pIdx].v"
                                          :placeholder="param.p"
                                          :required="param.d"
                                          :auto-size="{ minRows: 1, maxRows: 2 }"
                                          class="parameter-input-inline"
                                          @blur="blurSave('ass_general', item.ass_general, item.id)"
                                        />
                                      </div>
                                    </div>
                                  </template>
                                </KeyValueList>
                              </div>
                            </a-tab-pane>
                          </a-tabs>
                        </a-tab-pane>
                        <a-tab-pane key="4" title="后置处理">
                          <a-tabs :active-key="data.tabsKey" @tab-click="(key) => tabsChange(key)">
                            <template #extra>
                              <a-space v-if="data.assClickAdd">
                                <a-button size="small" type="primary" @click="clickAdd(item)"
                                  >增加
                                </a-button>
                              </a-space>
                            </template>
                            <a-tab-pane key="40" title="响应结果提取">
                              <div class="m-2">
                                <KeyValueList
                                  :data-list="item.posterior_response"
                                  :field-config="[
                                    {
                                      field: 'value',
                                      label: 'jsonpath语法',
                                      placeholder: '请输入jsonpath语法',
                                    },
                                    { field: 'key', label: 'Key', placeholder: '请输入key' },
                                  ]"
                                  :on-delete-item="
                                    (index) =>
                                      removeFrontSql(
                                        item.posterior_response,
                                        index,
                                        'posterior_response',
                                        item.id
                                      )
                                  "
                                  :on-save="
                                    () =>
                                      blurSave(
                                        'posterior_response',
                                        item.posterior_response,
                                        item.id
                                      )
                                  "
                                  @update:item="
                                    (index, value) =>
                                      updateArrayItem(
                                        item.posterior_response,
                                        index,
                                        value,
                                        item,
                                        'posterior_response',
                                        () =>
                                          blurSave(
                                            'posterior_response',
                                            item.posterior_response,
                                            item.id
                                          )
                                      )
                                  "
                                  empty-text='暂无响应结果提取，点击上方"增加"按钮添加'
                                >
                                  <template #extra="{ index }">
                                    <a-button
                                      size="small"
                                      status="success"
                                      @click="jsonpathTest(item, index)"
                                      class="test-btn"
                                    >
                                      测试
                                    </a-button>
                                  </template>
                                </KeyValueList>
                              </div>
                            </a-tab-pane>
                            <a-tab-pane key="41" title="后置sql处理">
                              <div class="m-2">
                                <KeyValueList
                                  :data-list="item.posterior_sql"
                                  :field-config="[
                                    {
                                      field: 'key',
                                      label: 'Key',
                                      placeholder: '请输入key，示例：key1,key2',
                                    },
                                    {
                                      field: 'value',
                                      label: 'Sql语句',
                                      placeholder: '请输入sql语句',
                                    },
                                  ]"
                                  :on-delete-item="
                                    (index) =>
                                      removeFrontSql(
                                        item.posterior_sql,
                                        index,
                                        'posterior_sql',
                                        item.id
                                      )
                                  "
                                  :on-save="
                                    () => blurSave('posterior_sql', item.posterior_sql, item.id)
                                  "
                                  @update:item="
                                    (index, value) =>
                                      updateArrayItem(
                                        item.posterior_sql,
                                        index,
                                        value,
                                        item,
                                        'posterior_sql',
                                        () => blurSave('posterior_sql', item.posterior_sql, item.id)
                                      )
                                  "
                                  empty-text='暂无后置sql处理语句，点击上方"增加"按钮添加'
                                />
                              </div>
                            </a-tab-pane>
                            <a-tab-pane key="42" title="强制等待">
                              <div class="m-2">
                                <a-space direction="vertical">
                                  <a-space direction="vertical">
                                    <a-input
                                      v-model="item.posterior_sleep"
                                      placeholder="请输入强制等待时间，单位是秒"
                                      style="width: 300px"
                                      @blur="
                                        blurSave('posterior_sleep', item.posterior_sleep, item.id)
                                      "
                                    />
                                  </a-space>
                                </a-space>
                              </div>
                            </a-tab-pane>
                            <a-tab-pane key="43" title="后置函数">
                              <div class="m-2">
                                <a-textarea
                                  v-model="item.posterior_func"
                                  :auto-size="{ minRows: 10, maxRows: 10 }"
                                  allow-clear
                                  placeholder="根据帮助文档，输入自定义后置函数"
                                  @blur="blurSave('posterior_func', item.posterior_func, item.id)"
                                />
                              </div>
                            </a-tab-pane>
                          </a-tabs>
                        </a-tab-pane>
                        <a-tab-pane key="5" title="缓存数据">
                          <div class="m-2">
                            <JsonDisplay :data="item.result_data?.cache_data" />
                          </div>
                        </a-tab-pane>
                        <a-tab-pane key="6" title="断言结果">
                          <div class="m-2">
                            <AssertionResult :data="item.result_data?.ass" />
                          </div>
                        </a-tab-pane>
                      </a-tabs>
                    </div>
                  </a-collapse-item>
                </a-collapse>
              </a-space>
            </a-space>
          </div>
        </div>
      </a-card>
    </template>
  </TableBody>
  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
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
          <template v-else-if="item.type === 'cascader' && item.key === 'module'">
            <a-cascader
              v-model="item.value"
              :options="data.productModuleName"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              @change="getModuleApi(item.value)"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'api_info'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="data.apiList"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
  <ModalDialog
    ref="modalDialogRefParameter"
    :title="data.actionParameterTitle"
    @confirm="onDataFormParameter"
  >
    <template #content>
      <a-form :model="formParameterModel">
        <a-form-item
          v-for="item of formParameterItems"
          :key="item.key"
          :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import { nextTick, onMounted, reactive, ref } from 'vue'
  import { useRoute } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'
  import { ModalDialogType } from '@/types/components'
  import { fieldNames } from '@/setting'
  import { Message, Modal } from '@arco-design/web-vue'
  import { usePageData } from '@/store/page-data'
  import { formatJson, formatJsonObj } from '@/utils/tools'
  import { columns, formItems, formParameterItems } from './config'
  import { getApiCaseRun, putApiCase } from '@/api/apitest/case'
  import {
    deleteApiCaseDetailed,
    getApiCaseDetailed,
    postApiCaseDetailed,
    putApiPutCaseSort,
    putApiPutRefreshApiInfo,
  } from '@/api/apitest/case_detailed'
  import { getApiInfoName } from '@/api/apitest/info'
  import { getUserProductAllModuleName } from '@/api/system/product'
  import useUserStore from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import { getApiHeaders } from '@/api/apitest/headers'
  import {
    deleteApiCaseDetailedParameter,
    getApiCaseDetailedParameter,
    postApiCaseDetailedParameter,
    postCaseDetailedParameterTestJsonpath,
    putApiCaseDetailedParameter,
  } from '@/api/apitest/case-detailed-parameter'
  import { getSystemCacheDataKeyValue } from '@/api/system/cache_data'
  import KeyValueList from '@/components/KeyValueList.vue' // 引入新组件
  import AssertionResult from '@/components/AssertionResult.vue' // 引入断言结果组件
  // import CacheDataDisplay from '@/components/CacheDataDisplay.vue' // 引入缓存数据展示组件

  const userStore = useUserStore()

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const modalDialogRefParameter = ref<ModalDialogType | null>(null)
  const formModel = ref({})
  const formParameterModel = ref({})
  const pageData: any = usePageData()
  const enumStore = useEnum()

  const route = useRoute()
  const data: any = reactive({
    actionTitle: '新增',

    assClickAdd: true,
    results: null,
    selectDataObj: [],
    data: [],
    productModuleName: [],
    apiList: [],
    ass: [],
    textAss: [],
    caseHeadersList: [],
    caseDetailsHeadersList: [],
    apiType: '2',
    apiSonType: '0',
    caseDetailsTypeKey: '0',
    tabsKey: '10',

    actionParameterTitle: '新增接口场景',
    isAdd: true,
    updateId: null,
  })

  const caseRunning = ref(false)

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

  function switchType(key: any) {
    if (key === '1') {
      data.apiSonType = '11'
    } else if (key === '3') {
      data.apiSonType = '31'
    }
    data.apiType = key
  }

  function switchApiInfoType(key: any, item: any) {
    data.caseDetailsTypeKey = key
    if (key === '0') {
      if (item?.params) {
        data.tabsKey = '01'
      } else if (item?.data) {
        data.tabsKey = '02'
      } else if (item?.json) {
        data.tabsKey = '03'
      } else if (item?.file) {
        data.tabsKey = '04'
      } else {
        data.tabsKey = '00'
      }
    } else if (key === '1') {
      data.tabsKey = '10'
      data.assClickAdd = true
    } else if (key === '2') {
      data.tabsKey = '23'
    } else if (key === '3') {
      if (item.ass_general && item.ass_general.length > 0) {
        data.tabsKey = '32'
      } else if (item.ass_jsonpath && item.ass_jsonpath.length > 0) {
        data.tabsKey = '31'
      } else if (item.ass_text_all) {
        data.tabsKey = '33'
      } else {
        data.tabsKey = '30'
      }
      data.assClickAdd = false
    } else if (key === '4') {
      if (item.posterior_sql && item.posterior_sql.length > 0) {
        data.tabsKey = '41'
      } else if (item.posterior_func && item.posterior_func.length > 0) {
        data.tabsKey = '43'
      } else if (item.posterior_sleep) {
        data.tabsKey = '42'
      } else {
        data.tabsKey = '40'
      }
      data.assClickAdd = true
    } else if (key === '5') {
      data.tabsKey = '50'
    }
  }

  function switchSonType(key: any) {
    data.apiSonType = key
  }

  function tabsChange(key: string | number) {
    data.tabsKey = key
    data.assClickAdd = !(
      key === '30' ||
      key === '42' ||
      key === '33' ||
      key === '43' ||
      key === '11'
    )
  }

  function clickAdd(item: any = null) {
    if ('10' === data.tabsKey) {
      item['front_sql'].push({ key: '', value: '' })
    } else if ('31' === data.tabsKey) {
      item['ass_jsonpath'].push({ actual: '', method: '', expect: '' })
    } else if ('32' === data.tabsKey) {
      item['ass_general'].push({ method: '', value: {} })
    } else if ('40' === data.tabsKey) {
      item['posterior_response'].push({ key: '', value: '' })
    } else if ('41' === data.tabsKey) {
      item['posterior_sql'].push({ key: '', value: '' })
    }
  }

  function addData() {
    if (data.apiType == '2') {
      addApiInfo()
      return
    }
    if (data.apiSonType === '11') {
      pageData.record.front_custom.push({ key: '', value: '' })
    } else if (data.apiSonType === '12') {
      pageData.record.front_sql.push({ key: '', value: '' })
    } else if (data.apiSonType === '31') {
      pageData.record.posterior_sql.push({ key: '', value: '' })
    }
  }

  function doResetSearch() {
    window.history.back()
  }

  function parameterEditing(item: any) {
    data.actionParameterTitle = '编辑接口场景名称'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRefParameter.value?.toggle()
    nextTick(() => {
      formParameterItems.forEach((it) => {
        const propName = item[it.key]
        if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
        } else {
          it.value = propName
        }
      })
    })
  }

  function parameterDelete(item: any) {
    Modal.confirm({
      title: '提示',
      content: '确定要删除此数据吗？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteApiCaseDetailedParameter(item.id)
          .then((res) => {
            Message.success(res.msg)
            doRefreshParameter(data.tabelJson.id)
          })
          .catch(console.log)
      },
    })
  }

  function removeFrontSql1(item: any, index: number) {
    item.splice(index, 1)

    upDataCase()
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

  function changeHeadersApi(selectedValues: any, item: any) {
    putApiCaseDetailedParameter({ id: item.id, headers: selectedValues })
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
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
    const not_serialize = [
      'url',
      'headers',
      'posterior_sleep',
      'posterior_func',
      'front_func',
      'ass_text_all',
      'data',
      'json',
      'params',
    ]
    const in_serialize = ['file', 'ass_json_all']
    const payload: any = {
      id: id,
      [key]: null,
    }
    if (not_serialize.includes(key)) {
      if (item === '') {
        payload[key] = null
      } else {
        payload[key] = item
      }
    } else if (in_serialize.includes(key)) {
      if (formatJsonObj(key, item) === false) {
        return
      } else {
        payload[key] = formatJsonObj(key, item)
      }
    } else {
      payload[key] = item
    }

    putApiCaseDetailedParameter(payload)
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  function removeFrontSql(item: any, index: number, key: string, id: number) {
    item.splice(index, 1)
    blurSave(key, item, id)
  }

  function jsonpathTest(item: any, index: number) {
    if (
      item.result_data?.response?.json === null ||
      (typeof item.result_data?.response?.json !== 'object' &&
        !Array.isArray(item.result_data?.response?.json))
    ) {
      Message.error('响应JSON是空或者不是JSON格式，无法进行测试！')
      return
    }
    postCaseDetailedParameterTestJsonpath(
      item.posterior_response[index],
      item.result_data?.response?.json
    )
      .then((res) => {
        Message.success(
          '测试成功，key：【' + res.data.key + '】，value：【' + res.data.value + '】'
        )
      })
      .catch(console.log)
  }

  // 通用断言测试方法
  /*
function testGeneralAssertion(item: any, index: number) {
// 这里可以添加通用断言的测试逻辑
Message.info('通用断言测试功能待实现')
}

// 通用断言保存方法
function saveGeneralAssertion(item: any, index: number) {
blurSave('ass_general', item.ass_general, item.id)
}

// 通用断言删除方法
function removeGeneralAssertion(item: any, index: number) {
removeFrontSql(item.ass_general, index, 'ass_general', item.id)
}
*/

  function getCacheDataKeyValue() {
    getSystemCacheDataKeyValue('ass_select_value')
      .then((res) => {
        res.data.forEach((item: any) => {
          if (item.value.includes('断言')) {
            data.ass.push(item)
          }
          if (item.value === '内容断言') {
            data.textAss.push(...item.children)
          }
        })
      })
      .catch(console.log)
  }

  function doRefresh() {
    data.caseHeadersList = pageData.record.front_headers
    getApiCaseDetailed(route.query.case_id)
      .then((res) => {
        data.data = res.data
        if (data.tabelJson && res.data) {
          res.data.forEach((item: any) => {
            if (item.id === data.tabelJson.id) {
              select(item)
            }
          })
        } else if (res.data) {
          select(res.data[0])
        }
      })
      .catch(console.log)
  }

  function doRefreshParameter(id: number) {
    return getApiCaseDetailedParameter({ case_detailed_id: id })
      .then((res) => {
        if (res.data.length !== 0) {
          data.selectDataObj = res.data
          const formatItemData = (item: any) => {
            const propertiesToFormat = ['ass_json_all', 'file']
            propertiesToFormat.forEach((prop) => {
              if (typeof item[prop] === 'object') {
                item[prop] = formatJson(item[prop])
              }
            })
          }
          data.selectDataObj.forEach((item: any) => {
            formatItemData(item)
          })
        } else {
          data.selectDataObj = []
        }
      })
      .catch(console.log)
  }

  function doRefreshHeaders(project_product_id: any, is_parameter = false) {
    const value = {
      page: 1,
      pageSize: 10000,
      project_product_id: project_product_id,
    }
    getApiHeaders(value)
      .then((res) => {
        if (is_parameter) {
          data.parameter_headers_list = res.data
        } else {
          data.headers_list = res.data
        }
      })
      .catch(console.log)
  }

  const caseRun = async (param) => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (caseRunning.value) return
    caseRunning.value = true
    try {
      const res = await getApiCaseRun(route.query.case_id, userStore.selected_environment, param)
      Message.success(res.msg)
    } catch (e) {
    } finally {
      caseRunning.value = false
      doRefresh()
    }
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
      let value = getFormItems(formItems)
      value['case'] = route.query.case_id
      value['case_sort'] = data.data.length
      postApiCaseDetailed(value, route.query.case_id)
        .then((res) => {
          modalDialogRef.value?.toggle()
          Message.success(res.msg)
          doRefresh()
        })
        .catch((error) => {
          console.log(error)
        })
        .finally(() => {
          modalDialogRef.value?.setConfirmLoading(false)
        })
    } else {
      modalDialogRef.value?.setConfirmLoading(false)
    }
  }

  function onDataFormParameter() {
    if (formParameterItems.every((it) => (it.validator ? it.validator() : true))) {
      modalDialogRefParameter.value?.toggle()
      let value = getFormItems(formParameterItems)
      if (data.isAdd) {
        value['case_detailed'] = data.tabelJson.id
        value['api_info'] = data.tabelJson.api_info.id
        postApiCaseDetailedParameter(value)
          .then((res) => {
            Message.success(res.msg)
            doRefreshParameter(data.tabelJson.id)
          })
          .catch(console.log)
      } else {
        value['id'] = data.updateId
        putApiCaseDetailedParameter(value)
          .then((res) => {
            Message.success(res.msg)
            doRefreshParameter(data.tabelJson.id)
          })
          .catch(console.log)
      }
    }
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此接口？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteApiCaseDetailed(record.id, route.query.case_id)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
          .finally(() => {
            doRefresh()
          })
      },
    })
  }

  function addApiInfo() {
    data.actionTitle = '新增'
    modalDialogRef.value?.toggle()
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = ''
      }
    })
  }

  function addParameter() {
    data.actionParameterTitle = '增加接口场景'
    data.isAdd = true
    modalDialogRefParameter.value?.toggle()
    formParameterItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = ''
      }
    })
  }

  function refresh(id: number) {
    Modal.confirm({
      title: '提示',
      content: '是否确实从接口管理中同步接口数据？点击确认后，原始数据会丢失！',
      cancelText: '取消',
      okText: '同步',
      onOk: () => {
        putApiPutRefreshApiInfo(id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function select(record: any) {
    data.tabelJson = record
    doRefreshHeaders(record.api_info.project_product, true)
    doRefreshParameter(data.tabelJson.id).then(() => {
      switchApiInfoType(data.caseDetailsTypeKey, data.selectDataObj[0])
    })
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      doRefreshHeaders(route.query.project_product)
      onProductModuleName()
      getCacheDataKeyValue()
    })
  })

  function updateArrayItem(
    array: any[],
    index: number,
    value: any,
    item: any,
    fieldName: string,
    saveCallback?: () => void
  ) {
    // 更新数组元素
    if (array && index < array.length) {
      array[index] = value
    }
    // 如果提供了保存回调，则执行保存
    if (saveCallback) {
      saveCallback()
    }
  }

  function handleJsonpathMethodChange(value: any, item: any, index: number, item1) {
    blurSave('ass_jsonpath', item, item1.id)
  }

  function handleGeneralMethodChange(
    value: any,
    currentItem: any,
    currentIndex: number,
    item: any
  ) {
    const inputItem = findItemByValue(data.ass, value)
    if (inputItem && Array.isArray(inputItem.parameter)) {
      inputItem.parameter.forEach((param) => {
        if (typeof param.v === 'object' && param.v !== null) {
          try {
            param.v = JSON.stringify(param.v)
          } catch {
            param.v = ''
          }
        }
      })
    }
    item.ass_general[currentIndex].value = inputItem
    // 保存更改
    blurSave('ass_general', item.ass_general, item.id)
  }

  // 添加 formatResponseText 方法到 setup 函数内部的正确位置
  function formatResponseText(text) {
    // 如果text是一个对象（可能是JSON），将其转换为格式化的字符串
    if (typeof text === 'object' && text !== null) {
      try {
        return JSON.stringify(text, null, 2);
      } catch (e) {
        return String(text);
      }
    }
    // 如果text是字符串，直接返回
    return String(text);
  }
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

  .main_box {
    width: 100%;
    margin: 0 auto;
    padding: 5px;
    box-sizing: border-box;
    display: flex;
  }

  .left {
    padding: 5px;
    width: 45%;
  }

  .right {
    padding: 5px;
    width: 55%;
  }

  .custom-header {
    display: flex;
    align-items: center;
    gap: 12px; /* 控制标签间距 */
    font-size: 14px;
  }

  /* 通用断言样式 */
  .assertion-parameters {
    flex: 2;
    min-width: 300px;
  }

  .parameter-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 12px;
  }

  .parameter-label {
    font-size: 12px;
    color: #666;
    font-weight: 500;
  }

  .parameter-input {
    width: 100%;
  }

  /* 通用断言行内样式 */
  .assertion-parameters-inline {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    flex: 2;
    min-width: 300px;
    margin-top: 0;
  }

  .parameter-item-inline {
    display: flex;
    flex-direction: column;
    gap: 4px;
    flex: 1;
    min-width: 150px;
  }

  .parameter-label-inline {
    font-size: 12px;
    color: #666;
    font-weight: 500;
  }

  .parameter-input-inline {
    width: 100%;
  }

  /* 确保KeyValueList中的所有元素都在一行 */
  :deep(.key-value-row) {
    flex-wrap: nowrap;
    align-items: flex-start;
    width: 100%;
    min-width: 0; /* 允许子元素收缩 */
    overflow-x: hidden; /* 防止水平滚动 */
  }

  :deep(.key-value-field) {
    flex: 1;
    min-width: 100px; /* 减小最小宽度 */
    overflow: hidden; /* 防止内容溢出 */
  }

  :deep(.button-container) {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    flex-shrink: 0;
    white-space: nowrap; /* 防止按钮内文字换行 */
    min-width: fit-content; /* 确保按钮容器不会收缩 */
  }

  :deep(.remove-btn) {
    flex-shrink: 0;
    margin-top: 18px;
  }

  :deep(.test-btn) {
    flex-shrink: 0;
    margin-top: 18px;
    min-width: fit-content; /* 确保按钮不会收缩 */
  }

  :deep(.assertion-parameters-inline) {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    flex: 2;
    min-width: 300px;
    margin-top: 0;
  }

  /* 响应式处理：在小屏幕上允许换行，但保持按钮在同一行 */
  @media (max-width: 768px) {
    :deep(.key-value-row) {
      flex-wrap: wrap;
    }

    :deep(.key-value-field) {
      min-width: 120px;
    }

    :deep(.button-container) {
      width: 100%;
      justify-content: flex-end;
      margin-top: 8px;
    }

    :deep(.remove-btn) {
      margin-top: 0;
      align-self: center;
    }

    :deep(.test-btn) {
      margin-top: 0;
      align-self: center;
    }

    .main_box {
      flex-direction: column;
    }

    .left,
    .right {
      width: 100%;
    }
  }
</style>
