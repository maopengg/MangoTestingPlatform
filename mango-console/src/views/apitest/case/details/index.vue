<template>
  <TableBody ref="tableBody">
    <template #header>
      <a-card :bordered="false" title="组合用例场景">
        <template #extra>
          <a-space>
            <a-button size="small" status="success" @click="caseRun(null)">执行 </a-button>
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
              <a-tab-pane key="1" title="前置数据">
                <a-tabs position="left" @tab-click="(key) => switchSonType(key)">
                  <a-tab-pane key="11" title="自定义变量">
                    <a-space direction="vertical">
                      <a-space
                        v-for="(item, index) of pageData.record.front_custom"
                        :key="item.key"
                      >
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
                          size="small"
                          status="danger"
                          type="text"
                          @click="removeFrontSql1(pageData.record.front_custom, index)"
                          >移除
                        </a-button>
                      </a-space>
                    </a-space>
                  </a-tab-pane>
                  <a-tab-pane key="12" title="sql变量">
                    <a-space direction="vertical">
                      <a-space v-for="(item, index) of pageData.record.front_sql" :key="item.sql">
                        <span>key：</span>
                        <a-input
                          v-model="item.key_list"
                          placeholder="请输入查询结果缓存key，使用英文逗号隔开"
                          @blur="upDataCase"
                        />
                        <span>sql：</span>
                        <a-input
                          v-model="item.sql"
                          placeholder="请输入sql语句"
                          @blur="upDataCase"
                        />
                        <a-button
                          size="small"
                          status="danger"
                          type="text"
                          @click="removeFrontSql1(pageData.record.front_sql, index)"
                          >移除
                        </a-button>
                      </a-space>
                    </a-space>
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
                        <a-button size="mini" type="text" @click="caseRun(record.case_sort)"
                          >执行到此处
                        </a-button>
                        <a-button size="mini" type="text" @click="refresh(record.id)"
                          >刷新
                        </a-button>
                        <a-button size="mini" status="danger" type="text" @click="onDelete(record)"
                          >删除
                        </a-button>
                      </template>
                    </a-table-column>
                  </template>
                </a-table>
              </a-tab-pane>
              <a-tab-pane key="3" title="后置清除">
                <a-tabs position="left" @tab-click="(key) => switchSonType(key)">
                  <a-tab-pane key="31" title="sql清除">
                    <a-space direction="vertical">
                      <a-space
                        v-for="(item, index) of pageData.record.posterior_sql"
                        :key="item.sql"
                      >
                        <span>sql：</span>
                        <a-input
                          v-model="item.sql"
                          placeholder="请输入sql语句"
                          @blur="upDataCase"
                          style="width: 300px"
                        />
                        <a-button
                          size="small"
                          status="danger"
                          type="text"
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
                <a-button size="small" type="primary" @click="addParameter">增加</a-button>
              </a-space>
              <a-space direction="vertical" fill>
                <a-collapse :bordered="false" :default-active-key="[0]" accordion>
                  <a-collapse-item
                    v-for="(item, index) of data.selectDataObj"
                    :key="index"
                    :header="item.name + (item.status === 1 ? '-成功' : '-失败')"
                  >
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
                        @tab-click="(key) => switchApiInfoType(key)"
                      >
                        <a-tab-pane key="0" title="请求配置">
                          <a-tabs :active-key="data.tabsKey" @tab-click="(key) => tabsChange(key)">
                            <a-tab-pane key="00" title="请求头">
                              <div class="m-2">
                                <a-space direction="vertical">
                                  <a-checkbox-group
                                    v-for="header of data.headers_list"
                                    :key="header.id"
                                    v-model="item.header"
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
                                  class="m-2"
                                  v-model="item.params"
                                  allow-clear
                                  auto-size
                                  placeholder="请输入参数，json格式"
                                  @blur="blurSave('params', item.params, item.id)"
                              /></div>
                            </a-tab-pane>
                            <a-tab-pane key="02" title="表单">
                              <div class="m-2">
                                <a-textarea
                                  v-model="item.data"
                                  allow-clear
                                  auto-size
                                  placeholder="请输入表单，json格式"
                                  @blur="blurSave('data', item.data, item.id)"
                              /></div>
                            </a-tab-pane>
                            <a-tab-pane key="03" title="JSON">
                              <div class="m-2">
                                <a-textarea
                                  v-model="item.json"
                                  allow-clear
                                  auto-size
                                  placeholder="请输入JSON，json格式"
                                  @blur="blurSave('json', item.json, item.id)"
                              /></div>
                            </a-tab-pane>
                            <a-tab-pane key="04" title="file">
                              <div class="m-2">
                                <a-textarea
                                  v-model="item.file"
                                  allow-clear
                                  auto-size
                                  placeholder="请输入file，json格式"
                                  @blur="blurSave('file', item.file, item.id)"
                              /></div>
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
                                <a-space direction="vertical" fill>
                                  <a-space v-for="(inputObj, index) of item.front_sql" :key="index">
                                    <a-space>
                                      <a-input
                                        v-model="item.front_sql[index]"
                                        placeholder="请输入前置sql语句"
                                        @blur="blurSave('front_sql', item.front_sql, item.id)"
                                        style="width: 500px"
                                      />
                                      <a-button
                                        size="small"
                                        status="danger"
                                        type="text"
                                        @click="
                                          removeFrontSql(
                                            item.front_sql,
                                            index,
                                            'front_sql',
                                            item.id
                                          )
                                        "
                                        >移除
                                      </a-button>
                                    </a-space>
                                  </a-space>
                                </a-space>
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
                              /></div>
                            </a-tab-pane>
                          </a-tabs>
                        </a-tab-pane>
                        <a-tab-pane key="2" title="响应结果">
                          <a-tabs :active-key="data.tabsKey" @tab-click="(key) => tabsChange(key)">
                            <a-tab-pane key="20" title="基础信息">
                              <div class="m-2">
                                <a-space direction="vertical">
                                  <span>URL：{{ item.result_data?.request?.url }}</span>
                                  <span>响应code：{{ item.result_data?.response?.code }}</span>
                                  <span>响应时间：{{ item.result_data?.response?.time }}</span>
                                  <span>失败原因：{{ item.result_data?.error_message }}</span>
                                </a-space></div
                              >
                            </a-tab-pane>
                            <a-tab-pane key="21" title="请求头">
                              <div class="m-2">
                                <pre>{{ strJson(item.result_data?.request?.headers) }}</pre>
                              </div>
                            </a-tab-pane>
                            <a-tab-pane key="22" title="响应头">
                              <div class="m-2">
                                <pre>{{ strJson(item.result_data?.response?.headers) }}</pre>
                              </div>
                            </a-tab-pane>
                            <a-tab-pane key="23" title="响应JSON">
                              <div class="m-2">
                                <pre>{{ strJson(item.result_data?.response?.json) }}</pre>
                              </div>
                            </a-tab-pane>
                            <a-tab-pane key="24" title="响应文本">
                              <div class="m-2">
                                <pre>{{ strJson(item.result_data?.response?.text) }}</pre>
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
                              /></div>
                            </a-tab-pane>
                            <a-tab-pane key="31" title="jsonpath断言">
                              <div class="m-2">
                                <a-space direction="vertical">
                                  <a-space v-for="(value, index) of item.ass_jsonpath" :key="index">
                                    <a-input
                                      v-model="item.ass_jsonpath[index].actual"
                                      placeholder="请输入jsonpath表达式"
                                      @blur="blurSave('ass_jsonpath', item.ass_jsonpath, item.id)"
                                    />
                                    <a-cascader
                                      v-model="item.ass_jsonpath[index].method"
                                      :default-value="item.ass_jsonpath[index].method"
                                      :options="data.ass"
                                      expand-trigger="hover"
                                      placeholder="请选择断言方法"
                                      value-key="key"
                                      @blur="blurSave('ass_jsonpath', item.ass_jsonpath, item.id)"
                                    />
                                    <a-input
                                      v-model="item.ass_jsonpath[index].expect"
                                      placeholder="请输入想要判断的值"
                                      @blur="blurSave('ass_jsonpath', item.ass_jsonpath, item.id)"
                                    />
                                    <a-button
                                      status="danger"
                                      type="text"
                                      @click="
                                        removeFrontSql(
                                          item.ass_jsonpath,
                                          index,
                                          'ass_jsonpath',
                                          item.id
                                        )
                                      "
                                      >移除
                                    </a-button>
                                  </a-space>
                                </a-space></div
                              >
                            </a-tab-pane>
                            <a-tab-pane key="32" title="sql断言">
                              <div class="m-2">
                                <a-space direction="vertical">
                                  <a-space v-for="(value, index) of item.ass_sql" :key="index">
                                    <a-input
                                      v-model="item.ass_sql[index].actual"
                                      placeholder="请输入sql查询语句，只能查询一个字段"
                                      @blur="blurSave('ass_sql', item.ass_sql, item.id)"
                                    />
                                    <a-cascader
                                      v-model="item.ass_sql[index].method"
                                      :default-value="item.ass_sql[index].method"
                                      :options="data.ass"
                                      expand-trigger="hover"
                                      placeholder="请选择断言方法"
                                      value-key="key"
                                      @blur="blurSave('ass_sql', item.ass_sql, item.id)"
                                    />
                                    <a-input
                                      v-model="item.ass_sql[index].expect"
                                      placeholder="请输入想要判断的值"
                                      @blur="blurSave('ass_sql', item.ass_sql, item.id)"
                                    />
                                    <a-button
                                      status="danger"
                                      type="text"
                                      @click="
                                        removeFrontSql(item.ass_sql, index, 'ass_sql', item.id)
                                      "
                                      >移除
                                    </a-button>
                                  </a-space>
                                </a-space></div
                              >
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
                                <a-space direction="vertical">
                                  <a-space
                                    v-for="(value, index) of item.posterior_response"
                                    :key="index"
                                  >
                                    <a-input
                                      v-model="item.posterior_response[index].key"
                                      placeholder="请输入jsonpath语法"
                                      @blur="
                                        blurSave(
                                          'posterior_response',
                                          item.posterior_response,
                                          item.id
                                        )
                                      "
                                    />
                                    <a-input
                                      v-model="item.posterior_response[index].value"
                                      placeholder="请输入缓存key"
                                      @blur="
                                        blurSave(
                                          'posterior_response',
                                          item.posterior_response,
                                          item.id
                                        )
                                      "
                                    />

                                    <a-button
                                      size="small"
                                      status="danger"
                                      type="text"
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
                              </div>
                            </a-tab-pane>
                            <a-tab-pane key="41" title="后置sql处理">
                              <div class="m-2">
                                <a-space direction="vertical">
                                  <a-space direction="vertical">
                                    <a-space
                                      v-for="(value, index) of item.posterior_sql"
                                      :key="index"
                                    >
                                      <span>key：</span>
                                      <a-input
                                        style="width: 300px"
                                        v-model="item.posterior_sql[index].value"
                                        placeholder="请输入缓存key，多个变量使用英文逗号隔开"
                                        @blur="
                                          blurSave('posterior_sql', item.posterior_sql, item.id)
                                        "
                                      />
                                      <span>sql：</span>

                                      <a-input
                                        v-model="item.posterior_sql[index].key"
                                        placeholder="请输入sql"
                                        @blur="
                                          blurSave('posterior_sql', item.posterior_sql, item.id)
                                        "
                                      />
                                      <a-button
                                        size="small"
                                        status="danger"
                                        type="text"
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
                              /></div>
                            </a-tab-pane>
                          </a-tabs>
                        </a-tab-pane>
                        <a-tab-pane key="5" title="缓存数据">
                          <div class="m-2">
                            <pre>{{ strJson(item.result_data?.cache_data) }}</pre>
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
  import { reactive, nextTick, onMounted, ref } from 'vue'
  import { useRoute } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'
  import { ModalDialogType } from '@/types/components'
  import { fieldNames } from '@/setting'
  import { Message, Modal } from '@arco-design/web-vue'
  import { usePageData } from '@/store/page-data'
  import { formatJson, formatJsonObj, strJson } from '@/utils/tools'
  import { formItems, columns, formParameterItems } from './config'
  import { putApiCase, getApiCaseRun } from '@/api/apitest/case'
  import {
    getApiCaseDetailed,
    deleteApiCaseDetailed,
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
    getApiCaseDetailedParameter,
    postApiCaseDetailedParameter,
    putApiCaseDetailedParameter,
    deleteApiCaseDetailedParameter,
  } from '@/api/apitest/case-detailed-parameter'
  import { getSystemCacheDataKeyValue } from '@/api/system/cache_data'

  const userStore = useUserStore()

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const modalDialogRefParameter = ref<ModalDialogType | null>(null)
  const formModel = ref({})
  const formParameterModel = ref({})
  const pageData: any = usePageData()
  const enumStore = useEnum()

  const route = useRoute()
  const data: any = reactive({
    actionTitle: '新增接口',

    assClickAdd: true,
    results: null,
    selectDataObj: [],
    data: [],
    productModuleName: [],
    apiList: [],
    ass: [],
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
      data.tabsKey = '00'
    } else if (key === '1') {
      data.tabsKey = '10'
    } else if (key === '2') {
      data.tabsKey = '23'
    } else if (key === '3') {
      data.tabsKey = '30'
      data.assClickAdd = false
    } else if (key === '4') {
      data.tabsKey = '40'
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
      item['front_sql'].push('')
    } else if ('31' === data.tabsKey) {
      item['ass_jsonpath'].push({ actual: '', method: '', expect: '' })
    } else if ('32' === data.tabsKey) {
      item['ass_sql'].push({ actual: '', method: '', expect: '' })
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
      pageData.record.front_sql.push({ sql: '', key_list: '' })
    } else if (data.apiSonType === '31') {
      pageData.record.posterior_sql.push({ sql: '' })
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
    putApiCaseDetailedParameter({ id: item.id, header: selectedValues })
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
      'header',
      'posterior_sleep',
      'posterior_func',
      'front_func',
      'ass_text_all',
    ]
    const in_serialize = ['data', 'json', 'data', 'file', 'params', 'ass_json_all']
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

  function getCacheDataKeyValue() {
    getSystemCacheDataKeyValue('select_value')
      .then((res) => {
        res.data.forEach((item: any) => {
          if (item.value === 'ass') {
            data.ass.push(...item.children)
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
        if (res.data.length !== 0) {
          select(res.data[0])
          doRefreshParameter(res.data[0].id)
        }
      })
      .catch(console.log)
  }

  function doRefreshParameter(id: number) {
    getApiCaseDetailedParameter({ case_detailed_id: id })
      .then((res) => {
        if (res.data.length !== 0) {
          data.selectDataObj = res.data
          const formatItemData = (item: any) => {
            const propertiesToFormat = ['ass_json_all', 'data', 'params', 'json', 'file']

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

      postApiCaseDetailed(value, route.query.case_id)
        .then((res) => {
          Message.success(res.msg)
          doRefresh()
        })
        .catch(console.log)
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
    putApiPutRefreshApiInfo(id)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function select(record: any) {
    data.tabelJson = record
    doRefreshParameter(data.tabelJson.id)

    switchApiInfoType(data.caseDetailsTypeKey)
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      doRefreshHeaders()
      onProductModuleName()
      getCacheDataKeyValue()
    })
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
  .main_box {
    width: 100%;
    margin: 0 auto;
    padding: 5px;
    box-sizing: border-box;
    display: flex;
    .left {
      padding: 5px;
      width: 45%;
    }
    .right {
      padding: 5px;
      width: 55%;
    }
  }
</style>
