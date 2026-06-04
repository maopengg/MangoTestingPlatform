<template>
  <TableBody ref="tableBody" class="mango-detail-workbench-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">{{ apiCaseDetailTitle }}</div>
          <div class="mango-detail-subtitle">维护用例前后置、接口编排、断言和执行结果</div>
        </div>
        <a-space class="mango-detail-actions" wrap>
          <a-button
            size="small"
            status="success"
            :loading="caseRunning"
            :disabled="caseRunning"
            @click="caseRun(null)"
          >
            执行
          </a-button>
          <a-button size="small" @click="doResetSearch">返回</a-button>
        </a-space>
      </div>
    </template>
    <template #default>
      <div class="api-case-workbench mango-detail-workbench">
        <section class="api-case-panel api-case-left">
          <div class="api-case-panel-head">
            <div>
              <div class="api-case-panel-title">用例编排</div>
              <div class="api-case-panel-subtitle"> 前置处理、接口步骤和用例后置配置 </div>
            </div>
            <a-tag size="small" color="arcoblue">{{ data.data.length || 0 }} 个步骤</a-tag>
          </div>
          <div class="api-case-panel-body">
            <a-tabs :active-key="data.apiType" @tab-click="(key) => switchType(key)">
              <template #extra>
                <a-space v-if="showCaseAddButton">
                  <a-button size="small" type="primary" @click="addData">增加</a-button>
                </a-space>
              </template>
              <a-tab-pane key="1" title="用例前置">
                <a-tabs position="left" @tab-click="(key) => switchSonType(key)">
                  <a-tab-pane key="11" title="自定义参数">
                    <KeyValueList
                      :data-list="pageData.record.front_custom"
                      :field-config="[
                        { field: 'key', label: 'Key', placeholder: '请输入缓存key' },
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
                          placeholder: '请输入缓存key,示例：key1,key2',
                        },
                        sqlDatasourceField,
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
                  <a-tab-pane key="14" title="数据工厂">
                    <DataFactoryCaseConfigPanel
                      v-if="data.apiType === '1' && data.apiSonType === '14'"
                      ref="dataFactoryPanelRef"
                      :case-id="route.query.case_id as string"
                      :project-product-id="route.query.project_product as string"
                      :source-type="1"
                    />
                  </a-tab-pane>
                  <a-tab-pane key="13" title="默认请求头">
                    <a-space direction="vertical">
                      <TipMessage message="此处请求头会应用到所有场景扩展中" />
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
                  :bordered="false"
                  :columns="columns"
                  :data="data.data"
                  :loading="stepTableLoading"
                  :draggable="{ type: 'handle', width: 40 }"
                  :pagination="false"
                  :scroll="{ x: 760 }"
                  @change="handleChange"
                  @row-click="select"
                >
                  <template #columns>
                    <a-table-column
                      v-for="item of columns"
                      :key="item.key"
                      :align="item.align"
                      :data-index="item.dataIndex"
                      :ellipsis="item.ellipsis"
                      :fixed="item.fixed"
                      :title="item.title"
                      :tooltip="item.tooltip"
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
                          >{{ enumStore.task_status[record.status]?.title || '-' }}
                        </a-tag>
                      </template>
                      <template v-else-if="item.dataIndex === 'actions'" #cell="{ record }">
                        <MangoTableActions
                          :actions="[
                            {
                              label: '执行到这',
                              loading: caseRunning,
                              onClick: () => caseRun(record.case_sort),
                            },
                            { label: '同步', onClick: () => refresh(record.id) },
                            { label: '删除', danger: true, onClick: () => onDelete(record) },
                          ]"
                        />
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
                        sqlDatasourceField,
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
        </section>
        <section class="api-case-panel api-case-right">
          <div class="api-case-panel-head">
            <div>
              <div class="api-case-panel-title">场景扩展</div>
              <div class="api-case-panel-subtitle">{{ selectedStepSummary }}</div>
            </div>
            <a-space wrap>
              <a-button size="small" type="primary" @click="addParameter">增加场景</a-button>
            </a-space>
          </div>
          <div class="api-case-panel-body">
            <a-space direction="vertical" fill>
              <a-space direction="vertical" fill>
                <a-spin
                  :loading="data.collapseLoading"
                  tip="场景数据加载中..."
                  class="scenario-loading-spin full-width"
                >
                  <a-collapse
                    :bordered="false"
                    :active-key="data.activeCollapseKey"
                    accordion
                    @change="onCollapseChange"
                  >
                    <a-collapse-item v-for="(item, index) of data.selectDataObj" :key="index">
                      <template #header>
                        <div class="custom-header">
                          <span class="custom-header__name">{{ '场景名称：' + item.name }}</span>
                          <div class="custom-header__tags">
                            <a-tag :color="enumStore.status_colors[item.status]">
                              {{ enumStore.task_status[item.status]?.title || '-' }}
                            </a-tag>
                            <a-tag color="purple">
                              {{
                                item.error_retry
                                  ? `重试 ${item.error_retry} 次 / ${
                                      item.retry_interval ? item.retry_interval : 0
                                    }s`
                                  : '不重试'
                              }}
                            </a-tag>
                          </div>
                        </div>
                      </template>
                      <template #extra>
                        <a-button size="mini" type="text" @click.stop="parameterEditing(item)"
                          >编辑
                        </a-button>
                        <a-button size="mini" type="text" @click.stop="parameterCopy(item)"
                          >复制
                        </a-button>
                        <a-button
                          size="mini"
                          status="danger"
                          type="text"
                          @click.stop="parameterDelete(item)"
                          >删除
                        </a-button>
                      </template>
                      <div
                        v-if="isMountedCollapseItem(index)"
                        v-show="isActiveCollapseItem(index)"
                        class="scenario-expand-body"
                      >
                        <a-spin
                          :loading="data.caseDetailTabLoading"
                          tip="页签内容加载中..."
                          class="scenario-tab-loading-spin"
                        >
                          <a-tabs
                            :active-key="data.caseDetailsTypeKey"
                            position="left"
                            @tab-click="(key) => switchApiInfoType(key, item)"
                          >
                            <a-tab-pane key="1" title="前置处理">
                            <a-tabs
                              :active-key="data.tabsKey"
                              @tab-click="(key) => tabsChange(key, item)"
                            >
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
                                        placeholder: '请输入缓存key',
                                      },
                                      sqlDatasourceField,
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
                                  <CodeEditor
                                    v-model="item.front_func"
                                    :line-height="280"
                                    :code-style="{ width: '100%' }"
                                    placeholder="根据帮助文档，输入自定义前置函数"
                                    @focus="
                                      recordCodeSnapshot('front_func', item.front_func, item.id)
                                    "
                                    @blur="
                                      saveCodeIfChanged('front_func', item.front_func, item.id)
                                    "
                                  />
                                </div>
                              </a-tab-pane>
                              <a-tab-pane key="12" title="数据工厂">
                                <div class="m-2">
                                  <DataFactoryCaseConfigPanel
                                    v-if="isActiveCaseDetailTab('1', '12')"
                                    :ref="(el) => setParameterDataFactoryPanelRef(item.id, el)"
                                    :case-id="item.id"
                                    :project-product-id="route.query.project_product as string"
                                    :source-type="3"
                                  />
                                </div>
                              </a-tab-pane>
                            </a-tabs>
                            </a-tab-pane>
                            <a-tab-pane key="0" title="请求配置">
                            <a-tabs
                              :active-key="data.tabsKey"
                              @tab-click="(key) => tabsChange(key, item)"
                            >
                              <a-tab-pane key="00" title="请求头">
                                <div class="request-header-panel">
                                  <TipMessage
                                    message="只要勾选，就会放弃使用用例前置中所有已勾选的请求头"
                                  />
                                  <a-space direction="vertical" class="full-width">
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
                                  <div class="request-editor-actions">
                                    <a-button
                                      size="small"
                                      type="outline"
                                      @click="openJsonEditDrawer('params', '参数', item)"
                                    >
                                      展开编辑
                                    </a-button>
                                  </div>
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
                                  <div class="request-editor-actions">
                                    <a-button
                                      size="small"
                                      type="outline"
                                      @click="openJsonEditDrawer('data', '表单', item)"
                                    >
                                      展开编辑
                                    </a-button>
                                  </div>
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
                                  <div class="request-editor-actions">
                                    <a-button
                                      size="small"
                                      type="outline"
                                      @click="openJsonEditDrawer('json', 'JSON', item)"
                                    >
                                      展开编辑
                                    </a-button>
                                  </div>
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
                                  <div class="request-editor-actions">
                                    <a-button
                                      size="small"
                                      type="outline"
                                      @click="openJsonEditDrawer('file', '文件', item)"
                                    >
                                      展开编辑
                                    </a-button>
                                  </div>
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
                            <a-tab-pane key="2" title="响应结果">
                            <a-tabs
                              :active-key="data.tabsKey"
                              @tab-click="(key) => tabsChange(key, item)"
                            >
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
                                    <a-tooltip
                                      v-if="item.result_data?.error_message"
                                      :content="item.result_data?.error_message"
                                      position="top"
                                      mini
                                    >
                                      <span class="api-case-failure-reason">
                                        失败原因：{{ item.result_data?.error_message }}
                                      </span>
                                    </a-tooltip>
                                  </a-space>
                                </div>
                              </a-tab-pane>
                              <a-tab-pane key="21" title="请求头">
                                <div class="m-2">
                                  <JsonDisplay
                                    v-if="isActiveCaseDetailTab('2', '21')"
                                    :data="item.result_data?.request?.headers"
                                  />
                                </div>
                              </a-tab-pane>
                              <a-tab-pane key="25" title="请求数据">
                                <div class="m-2" v-if="item.result_data?.request?.data">
                                  <JsonDisplay
                                    v-if="isActiveCaseDetailTab('2', '25')"
                                    :data="item.result_data?.request?.data"
                                  />
                                </div>
                                <div class="m-2" v-if="item.result_data?.request?.json">
                                  <JsonDisplay
                                    v-if="isActiveCaseDetailTab('2', '25')"
                                    :data="item.result_data?.request?.json"
                                  />
                                </div>
                                <div class="m-2" v-if="item.result_data?.request?.params">
                                  <JsonDisplay
                                    v-if="isActiveCaseDetailTab('2', '25')"
                                    :data="item.result_data?.request?.params"
                                  />
                                </div>
                                <div class="m-2" v-if="item.result_data?.request?.file">
                                  <JsonDisplay
                                    v-if="isActiveCaseDetailTab('2', '25')"
                                    :data="item.result_data?.request?.file"
                                  />
                                </div>
                              </a-tab-pane>
                              <a-tab-pane key="22" title="响应头">
                                <div class="m-2">
                                  <JsonDisplay
                                    v-if="isActiveCaseDetailTab('2', '22')"
                                    :data="item.result_data?.response?.headers"
                                    :default-expanded="false"
                                  />
                                </div>
                              </a-tab-pane>
                              <a-tab-pane key="23" title="响应JSON">
                                <div class="m-2">
                                  <JsonDisplay
                                    v-if="isActiveCaseDetailTab('2', '23')"
                                    :data="item.result_data?.response?.json"
                                    :jsonpath="true"
                                  />
                                </div>
                              </a-tab-pane>
                              <a-tab-pane key="24" title="响应文本">
                                <div class="m-2">
                                  <JsonDisplay
                                    v-if="isActiveCaseDetailTab('2', '24')"
                                    :data="item.result_data?.response?.text"
                                  />
                                </div>
                              </a-tab-pane>
                            </a-tabs>
                            </a-tab-pane>
                            <a-tab-pane key="4" title="后置处理">
                            <a-tabs
                              :active-key="data.tabsKey"
                              @tab-click="(key) => tabsChange(key, item)"
                            >
                              <template #extra>
                                <a-space v-if="data.assClickAdd">
                                  <a-button size="small" type="primary" @click="clickAdd(item)"
                                    >增加
                                  </a-button>
                                </a-space>
                              </template>
                              <a-tab-pane key="40" title="响应JSON提取">
                                <div class="m-2">
                                  <TipMessage
                                    message="从响应json中提取，请输入jsonpath语法的表达式，并点击测试按钮进行测试"
                                  />
                                  <KeyValueList
                                    :data-list="item.posterior_response"
                                    :field-config="[
                                      {
                                        field: 'value',
                                        label: 'jsonpath语法',
                                        placeholder: '请输入jsonpath语法',
                                      },
                                      { field: 'key', label: 'Key', placeholder: '请输入缓存key' },
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
                                        @click="testExtractResponseAfter('jsonpath', item, index)"
                                        class="mango-test-btn"
                                      >
                                        测试
                                      </a-button>
                                    </template>
                                  </KeyValueList>
                                </div>
                              </a-tab-pane>
                              <a-tab-pane key="44" title="响应文本提取">
                                <div class="m-2">
                                  <TipMessage
                                    message="从响应文本中提取，请输入正则表达式，并点击测试按钮进行测试"
                                  />
                                  <KeyValueList
                                    :data-list="item.posterior_response_text"
                                    :field-config="[
                                      {
                                        field: 'value',
                                        label: '正则语法',
                                        placeholder: '请输入正则语法',
                                      },
                                      { field: 'key', label: 'Key', placeholder: '请输入缓存key' },
                                    ]"
                                    :on-delete-item="
                                      (index) =>
                                        removeFrontSql(
                                          item.posterior_response_text,
                                          index,
                                          'posterior_response_text',
                                          item.id
                                        )
                                    "
                                    :on-save="
                                      () =>
                                        blurSave(
                                          'posterior_response_text',
                                          item.posterior_response_text,
                                          item.id
                                        )
                                    "
                                    @update:item="
                                      (index, value) =>
                                        updateArrayItem(
                                          item.posterior_response_text,
                                          index,
                                          value,
                                          item,
                                          'posterior_response_text',
                                          () =>
                                            blurSave(
                                              'posterior_response_text',
                                              item.posterior_response_text,
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
                                        @click="testExtractResponseAfter('re', item, index)"
                                        class="mango-test-btn"
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
                                        placeholder: '请输入缓存key，示例：key1,key2',
                                      },
                                      sqlDatasourceField,
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
                                          () =>
                                            blurSave('posterior_sql', item.posterior_sql, item.id)
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
                                        class="sleep-input"
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
                                  <CodeEditor
                                    v-model="item.posterior_func"
                                    :line-height="280"
                                    :code-style="{ width: '100%' }"
                                    placeholder="根据帮助文档，输入自定义后置函数"
                                    @focus="
                                      recordCodeSnapshot(
                                        'posterior_func',
                                        item.posterior_func,
                                        item.id
                                      )
                                    "
                                    @blur="
                                      saveCodeIfChanged(
                                        'posterior_func',
                                        item.posterior_func,
                                        item.id
                                      )
                                    "
                                  />
                                </div>
                              </a-tab-pane>
                            </a-tabs>
                            </a-tab-pane>
                            <a-tab-pane key="3" title="接口断言">
                            <a-tabs
                              :active-key="data.tabsKey"
                              @tab-click="(key) => tabsChange(key)"
                            >
                              <template #extra>
                                <a-space v-if="data.assClickAdd">
                                  <a-button size="small" type="primary" @click="clickAdd(item)">
                                    增加
                                  </a-button>
                                </a-space>
                              </template>
                              <a-tab-pane key="30" title="json一致断言">
                                <div class="m-2">
                                  <TipMessage
                                    message="注意以你输入的断言json的key和value为主，你没有输入响应中key和value则不断言"
                                  />
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
                                  <TipMessage
                                    message="只能输入jsonpath语法提取响应的json进行断言"
                                  />
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
                                        visible: shouldShowJsonpathExpect,
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
                                  <TipMessage message="响应的text全匹配断言" />
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
                                  <TipMessage
                                    message="支持任意类型断言，实际值和预期值均可输入缓存变量"
                                  />
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
                                            @blur="
                                              blurSave('ass_general', item.ass_general, item.id)
                                            "
                                          />
                                        </div>
                                      </div>
                                    </template>
                                  </KeyValueList>
                                </div>
                              </a-tab-pane>
                              <a-tab-pane key="34" title="结构化断言">
                                <div class="m-2">
                                  <a-space>
                                    <TipMessage
                                      message="如果接口管理中开启了则会默认使用进行断言，如果你输入了则会覆盖"
                                    />
                                    <a-button
                                      size="mini"
                                      type="primary"
                                      :loading="schemaLoadingId === item.id"
                                      @click="setSchema(item.id)"
                                      >自动生成</a-button
                                    >
                                  </a-space>
                                  <a-textarea
                                    v-model="item.ass_schema"
                                    :auto-size="{ minRows: 9, maxRows: 9 }"
                                    allow-clear
                                    placeholder="请输入响应的结构化类型"
                                    @blur="blurSave('ass_schema', item.ass_schema, item.id)"
                                  />
                                </div>
                              </a-tab-pane>
                            </a-tabs>
                            </a-tab-pane>
                            <a-tab-pane key="5" title="缓存数据">
                            <div class="m-2">
                              <JsonDisplay
                                v-if="data.caseDetailsTypeKey === '5'"
                                :data="item.result_data?.cache_data"
                              />
                            </div>
                            </a-tab-pane>
                            <a-tab-pane key="7" title="数据工厂">
                            <div class="m-2">
                              <JsonDisplay
                                v-if="data.caseDetailsTypeKey === '7'"
                                :data="item.result_data?.data_factory_cache_data"
                              />
                            </div>
                            </a-tab-pane>
                            <a-tab-pane key="6" title="断言结果">
                            <div class="m-2">
                              <AssertionResult
                                v-if="data.caseDetailsTypeKey === '6'"
                                :data="item.result_data?.ass"
                              />
                            </div>
                            </a-tab-pane>
                          </a-tabs>
                        </a-spin>
                      </div>
                      <div v-else-if="isActiveCollapseItem(index)" class="collapse-content-loading">
                        <a-spin tip="内容加载中..." />
                      </div>
                    </a-collapse-item>
                  </a-collapse>
                </a-spin>
              </a-space>
            </a-space>
          </div>
        </section>
      </div>
    </template>
  </TableBody>
  <MangoJsonEditDrawer
    v-model:visible="jsonEditDrawer.visible"
    v-model="jsonEditDrawer.value"
    :title="jsonEditDrawer.title"
    :description="`当前编辑内容会保存到所选场景的 ${jsonEditDrawer.label} 配置中。`"
    :saving="jsonEditSaving"
    @save="saveJsonEditDrawer"
  />
  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          v-for="item of formItems"
          :key="item.key"
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
          <template v-else-if="item.type === 'cascader' && item.key === 'module'">
            <ProductModuleSelect
              v-model="item.value"
              :project-product-id="pageData.record.project_product?.id || route.query.project_product"
              :placeholder="item.placeholder"
              @change="getModuleApi"
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
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
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
  import { computed, nextTick, onMounted, reactive, ref } from 'vue'
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
  import useUserStore from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import { getApiHeaders } from '@/api/apitest/headers'
  import {
    deleteApiCaseDetailedParameter,
    getApiCaseDetailedParameter,
    postApiCaseDetailedParameter,
    postApiCaseDetailedParameterCopy,
    postCaseDetailedParameterTestExtractResponseAfter,
    putApiCaseDetailedParameter,
    putSetSchema,
  } from '@/api/apitest/case-detailed-parameter'
  import { getSystemCacheDataKeyValue } from '@/api/system/cache_data'
  import KeyValueList from '@/components/forms/KeyValueList.vue' // 引入新组件
  import AssertionResult from '@/components/feedback/AssertionResult.vue'
  import TipMessage from '@/components/feedback/TipMessage.vue' // 引入断言结果组件
  import DataFactoryCaseConfigPanel from '@/components/DataFactory/CaseConfigPanel.vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { getDataFactoryCaseConfig, getDataFactoryDatasourceAlias } from '@/api/data-factory'

  const userStore = useUserStore()
  const FRONT_FUNC_TEMPLATE = `def func(self, request):
    print(request.model_dump_json())
    # 可以从request中获取值，然后修改完成之后重新赋值给request，最后进行返回
    method = request.method  # 获取请求方法
    url = request.url  # 获取请求的url
    headers = request.headers  # 获取headers
    params = request.params  # 获取参数
    data = request.data  # 获取表单
    json = request.json  # 获取json
    file = request.file  # 获取file
    return request`

  const POSTERIOR_FUNC_TEMPLATE = `def func(self, response):
    print(response.model_dump_json())
    # 可以从response中获取值，然后修改完成之后重新赋值给response，最后进行返回
    code = response.code  # 获取响应code码
    time = response.time  # 获取响应时间
    headers = response.headers  # 获取响应头
    print(response.headers.get('Set-Cookie'))
    json = response.json  # 获取响应的json
    text = response.text  # 获取响应的文本
    return response`

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const modalDialogRefParameter = ref<ModalDialogType | null>(null)
  const dataFactoryPanelRef = ref<InstanceType<typeof DataFactoryCaseConfigPanel> | null>(null)
  const parameterDataFactoryPanelRefs = new Map<
    number,
    InstanceType<typeof DataFactoryCaseConfigPanel>
  >()
  const formModel = ref({})
  const formParameterModel = ref({})
  const pageData: any = usePageData()
  const enumStore = useEnum()
  const jsonEditDrawer = reactive({
    visible: false,
    field: '',
    label: '',
    title: '',
    value: '',
    item: null as any,
  })

  const route = useRoute()
  const data: any = reactive({
    actionTitle: '新增',

    assClickAdd: true,
    results: null,
    selectDataObj: [],
    data: [],
    apiList: [],
    ass: [],
    textAss: [],
    caseHeadersList: [],
    caseDetailsHeadersList: [],
    apiType: '2',
    apiSonType: '0',
    caseDetailsTypeKey: '2',
    tabsKey: '10',

    actionParameterTitle: '新增接口场景',
    isAdd: true,
    isCopy: false,
    copyParameterId: null,
    updateId: null,
    activeCollapseKey: [0],
    mountedCollapseKeys: [],
    collapseLoading: false, // 列表整体 loading
    caseDetailTabLoading: false,
    expandingIndex: -1, // 正在展开中的 item index，-1 表示无
    datasourceAliasOptions: [],
  })

  const caseRunning = ref(false)
  const stepTableLoading = ref(false)
  const schemaLoadingId = ref<number | null>(null)
  const jsonEditSaving = ref(false)
  const showCaseAddButton = computed(() => !(data.apiType === '1' && data.apiSonType === '13'))
  const apiCaseDetailTitle = computed(() => {
    const id = pageData.record?.id || route.query.case_id || route.query.id || '-'
    const name = pageData.record?.name || '-'
    return `组合用例场景配置 / ${id} / ${name}`
  })
  const selectedStepSummary = computed(() => {
    const step = data.tabelJson
    if (!step?.api_info) {
      return '从左侧选择接口后，可为同一个接口扩展多组场景参数、断言和执行结果'
    }
    const method = formatMethodTitle(step.api_info.method)
    const url = step.api_info.url || '-'
    const name = step.api_info.name || '未命名接口'
    return `${name} / ${method} ${url} / 可扩展多组场景参数、前后置处理、断言和结果`
  })
  const dataFactoryConfigCache = new Map<number, boolean>()
  const codeEditorSnapshots = new Map<string, string>()

  const sqlDatasourceField = computed(() => ({
    field: 'datasource_alias',
    label: '数据源',
    type: 'select',
    placeholder: '单库可不选',
    options: data.datasourceAliasOptions,
  }))

  function formatMethodTitle(method: any) {
    const methods = Array.isArray(enumStore.method) ? enumStore.method : []
    const found = methods.find((item: any) => item.key === method)
    return found?.title || method || '-'
  }

  function codeSnapshotKey(id: number, key: string) {
    return `${id}:${key}`
  }

  function normalizeCodeValue(value: string | null | undefined) {
    return value || ''
  }

  function recordCodeSnapshot(key: string, value: string | null | undefined, id: number) {
    codeEditorSnapshots.set(codeSnapshotKey(id, key), normalizeCodeValue(value))
  }

  function saveCodeIfChanged(key: string, value: string | null | undefined, id: number) {
    const snapshotKey = codeSnapshotKey(id, key)
    const currentValue = normalizeCodeValue(value)
    const previousValue = codeEditorSnapshots.get(snapshotKey) ?? currentValue
    if (currentValue === previousValue) {
      return
    }
    codeEditorSnapshots.set(snapshotKey, currentValue)
    blurSave(key, value || null, id)
  }

  function isActiveCollapseItem(index: number) {
    return data.activeCollapseKey.some((key: string | number) => String(key) === String(index))
  }

  function isMountedCollapseItem(index: number) {
    return data.mountedCollapseKeys.some((key: string | number) => String(key) === String(index))
  }

  function mountCollapseItem(index: number) {
    if (!isMountedCollapseItem(index)) {
      data.mountedCollapseKeys.push(index)
    }
  }

  function deferMountCollapseItem(index: number) {
    data.expandingIndex = index
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (!isActiveCollapseItem(index)) {
          return
        }
        mountCollapseItem(index)
        data.expandingIndex = -1
      })
    })
  }

  function isActiveCaseDetailTab(caseDetailsTypeKey: string, tabsKey: string) {
    return data.caseDetailsTypeKey === caseDetailsTypeKey && data.tabsKey === tabsKey
  }

  function setParameterDataFactoryPanelRef(id: number, el: any) {
    if (el) {
      parameterDataFactoryPanelRefs.set(id, el)
    } else {
      parameterDataFactoryPanelRefs.delete(id)
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

  function switchType(key: any) {
    if (key === '1') {
      data.apiSonType = '11'
    } else if (key === '3') {
      data.apiSonType = '31'
    }
    data.apiType = key
  }

  function waitFrame() {
    return new Promise<void>((resolve) => {
      requestAnimationFrame(() => resolve())
    })
  }

  function delay(ms: number) {
    return new Promise<void>((resolve) => {
      window.setTimeout(resolve, ms)
    })
  }

  async function runCaseDetailTabLoading(task: () => void | Promise<void>) {
    let finished = false
    const loadingTimer = window.setTimeout(() => {
      if (!finished) {
        data.caseDetailTabLoading = true
      }
    }, 180)
    try {
      await task()
      await nextTick()
      await waitFrame()
      await waitFrame()
      if (data.caseDetailTabLoading) {
        await delay(120)
      }
    } finally {
      finished = true
      window.clearTimeout(loadingTimer)
      data.caseDetailTabLoading = false
    }
  }

  function hasConfigValue(value: any) {
    if (value === undefined || value === null) return false
    if (typeof value === 'string') {
      const text = value.trim()
      return text !== '' && text !== '{}' && text !== '[]'
    }
    if (Array.isArray(value)) return value.length > 0
    if (typeof value === 'object') return Object.keys(value).length > 0
    return Boolean(value)
  }

  async function switchApiInfoType(key: any, item: any) {
    if (data.caseDetailTabLoading) {
      return
    }
    await runCaseDetailTabLoading(async () => {
      data.caseDetailsTypeKey = key
      if (key === '0') {
        if (hasConfigValue(item?.headers)) {
          data.tabsKey = '00'
        } else if (hasConfigValue(item?.params)) {
          data.tabsKey = '01'
        } else if (hasConfigValue(item?.data)) {
          data.tabsKey = '02'
        } else if (hasConfigValue(item?.json)) {
          data.tabsKey = '03'
        } else if (hasConfigValue(item?.file)) {
          data.tabsKey = '04'
        } else {
          data.tabsKey = '03'
        }
      } else if (key === '1') {
        await switchFrontProcessTab(item)
      } else if (key === '2') {
        data.tabsKey = '23'
      } else if (key === '3') {
        if (item.ass_general && item.ass_general.length > 0) {
          data.tabsKey = '32'
          data.assClickAdd = true
        } else if (item.ass_jsonpath && item.ass_jsonpath.length > 0) {
          data.tabsKey = '31'
          data.assClickAdd = false
        } else if (item.ass_text_all) {
          data.tabsKey = '33'
          data.assClickAdd = false
        } else if (item.ass_schema) {
          data.tabsKey = '34'
          data.assClickAdd = false
        } else {
          data.tabsKey = '30'
          data.assClickAdd = false
        }
      } else if (key === '4') {
        if (item.posterior_sql && item.posterior_sql.length > 0) {
          data.tabsKey = '41'
        } else if (item.posterior_func && item.posterior_func.length > 0) {
          data.tabsKey = '43'
        } else if (item.posterior_response_text) {
          data.tabsKey = '44'
        } else if (item.posterior_sleep) {
          data.tabsKey = '42'
        } else {
          data.tabsKey = '40'
        }
        data.assClickAdd = true
      } else if (key === '5') {
        data.tabsKey = '50'
      }
    })
  }

  async function switchFrontProcessTab(item: any) {
    if (item?.front_sql && item.front_sql.length > 0) {
      data.tabsKey = '10'
      data.assClickAdd = true
      return
    }
    if (item?.front_func) {
      data.tabsKey = '11'
      data.assClickAdd = false
      return
    }
    try {
      let hasDataFactoryConfig = dataFactoryConfigCache.get(item.id)
      if (hasDataFactoryConfig === undefined) {
        const res = await getDataFactoryCaseConfig({ source_type: 3, source_id: item.id })
        hasDataFactoryConfig = Boolean(res.data && res.data.length > 0)
        dataFactoryConfigCache.set(item.id, hasDataFactoryConfig)
      }
      if (hasDataFactoryConfig) {
        data.tabsKey = '12'
        data.assClickAdd = true
        return
      }
    } catch (error) {
      console.log(error)
    }
    data.tabsKey = '10'
    data.assClickAdd = true
  }

  function switchSonType(key: any) {
    data.apiSonType = key
  }

  function fillDefaultFunc(item: any, key: string | number) {
    if (!item) return
    if (key === '11' && !item.front_func) {
      item.front_func = FRONT_FUNC_TEMPLATE
      recordCodeSnapshot('front_func', item.front_func, item.id)
    } else if (key === '43' && !item.posterior_func) {
      item.posterior_func = POSTERIOR_FUNC_TEMPLATE
      recordCodeSnapshot('posterior_func', item.posterior_func, item.id)
    }
  }

  async function tabsChange(key: string | number, item: any = null) {
    if (data.caseDetailTabLoading) {
      return
    }
    await runCaseDetailTabLoading(() => {
      data.tabsKey = key
      fillDefaultFunc(item, key)
      data.assClickAdd = !(
        key === '30' ||
        key === '42' ||
        key === '33' ||
        key === '43' ||
        key === '11'
      )
    })
  }

  function clickAdd(item: any = null) {
    if ('10' === data.tabsKey) {
      item['front_sql'].push({ key: '', value: '', datasource_alias: null })
    } else if ('31' === data.tabsKey) {
      item['ass_jsonpath'].push({ actual: '', method: '', expect: null })
    } else if ('32' === data.tabsKey) {
      item['ass_general'].push({ method: '', value: {} })
    } else if ('40' === data.tabsKey) {
      item['posterior_response'].push({ key: '', value: '' })
    } else if ('41' === data.tabsKey) {
      item['posterior_sql'].push({ key: '', value: '', datasource_alias: null })
    } else if ('44' === data.tabsKey) {
      item['posterior_response_text'].push({ key: '', value: '' })
    } else if ('12' === data.tabsKey) {
      parameterDataFactoryPanelRefs.get(item.id)?.open()
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
      pageData.record.front_sql.push({ key: '', value: '', datasource_alias: null })
    } else if (data.apiSonType === '14') {
      dataFactoryPanelRef.value?.open()
    } else if (data.apiSonType === '31') {
      pageData.record.posterior_sql.push({ key: '', value: '', datasource_alias: null })
    }
  }

  function doResetSearch() {
    window.history.back()
  }

  function setSchema(id: number) {
    if (schemaLoadingId.value) return
    schemaLoadingId.value = id
    putSetSchema(id)
      .then((res) => {
        Message.success(res.msg)
        doRefreshParameter(data.tabelJson.id)
      })
      .catch(console.log)
      .finally(() => {
        schemaLoadingId.value = null
      })
  }

  function parameterEditing(item: any) {
    data.actionParameterTitle = '编辑接口场景名称'
    data.isAdd = false
    data.isCopy = false
    data.copyParameterId = null
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

  function parameterCopy(item: any) {
    data.actionParameterTitle = '复制接口场景'
    data.isAdd = false
    data.isCopy = true
    data.copyParameterId = item.id
    data.updateId = null
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
      onBeforeOk: () => {
        return deleteApiCaseDetailedParameter(item.id)
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

  function openJsonEditDrawer(field: string, label: string, item: any) {
    jsonEditDrawer.visible = true
    jsonEditDrawer.field = field
    jsonEditDrawer.label = label
    jsonEditDrawer.title = `${label} JSON 编辑`
    jsonEditDrawer.item = item
    jsonEditDrawer.value = item?.[field] || ''
  }

  function saveJsonEditDrawer(value = jsonEditDrawer.value) {
    const item = jsonEditDrawer.item
    const field = jsonEditDrawer.field
    if (!item || !field) return
    if (jsonEditSaving.value) return
    jsonEditSaving.value = true
    item[field] = value
    const saveTask = blurSave(field, value, item.id)
    if (!saveTask) {
      jsonEditSaving.value = false
      return
    }
    saveTask
      .then(() => {
        jsonEditDrawer.visible = false
      })
      .finally(() => {
        jsonEditSaving.value = false
      })
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
    const in_serialize = ['file', 'ass_json_all', 'ass_schema']
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
        return null
      } else {
        payload[key] = formatJsonObj(key, item)
      }
    } else {
      payload[key] = item
    }

    return putApiCaseDetailedParameter(payload)
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  function removeFrontSql(item: any, index: number, key: string, id: number) {
    item.splice(index, 1)
    blurSave(key, item, id)
  }

  function testExtractResponseAfter(type: string, item: any, index: number) {
    // 1. 验证 result_data 是否存在
    if (!item.result_data) {
      Message.error('测试数据不存在：result_data 为空！')
      return
    }

    // 2. 验证 response 是否存在
    if (!item.result_data.response) {
      Message.error('响应数据不存在：response 为空！')
      return
    }

    // 3. 验证 json/text 是否存在且格式正确
    if (type === 'jsonpath') {
      if (item.result_data.response.json === null) {
        Message.error('响应JSON是空，无法进行测试！')
        return
      }
      if (
        typeof item.result_data.response.json !== 'object' &&
        !Array.isArray(item.result_data.response.json)
      ) {
        Message.error('响应JSON格式不正确，无法进行测试！')
        return
      }
    } else {
      if (!item.result_data.response.text) {
        Message.error('响应文本为空，无法进行测试！')
        return
      }
    }

    // 4. 验证后置响应数据是否存在
    if (type === 'jsonpath') {
      if (!item.posterior_response || !item.posterior_response[index]) {
        Message.error('后置响应数据不存在！')
        return
      }
    } else {
      if (!item.posterior_response_text || !item.posterior_response_text[index]) {
        Message.error('后置响应文本数据不存在！')
        return
      }
    }

    postCaseDetailedParameterTestExtractResponseAfter(
      type,
      type === 'jsonpath' ? item.posterior_response[index] : item.posterior_response_text[index],
      type === 'jsonpath' ? item.result_data.response.json : item.result_data.response.text
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
          if (item.value === '自定义断言') {
            data.textAss.push(...item.children)
          }
        })
      })
      .catch(console.log)
  }

  function doRefresh() {
    stepTableLoading.value = true
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
      .finally(() => {
        stepTableLoading.value = false
      })
  }

  function doRefreshParameter(id: number) {
    data.collapseLoading = true
    dataFactoryConfigCache.clear()
    parameterDataFactoryPanelRefs.clear()
    data.mountedCollapseKeys = []
    data.expandingIndex = -1
    return getApiCaseDetailedParameter({ case_detailed_id: id })
      .then((res) => {
        // 先清空，解除旧数据的响应式绑定，让 Vue 立即释放旧 DOM
        data.selectDataObj = []
        if (!res.data || res.data.length === 0) {
          data.collapseLoading = false
          return
        }

        const BATCH_SIZE = 5 // 每帧渲染条数，可按实际数据量调整
        let index = 0

        function writeBatch() {
          const end = Math.min(index + BATCH_SIZE, res.data.length)
          for (; index < end; index++) {
            data.selectDataObj.push(formatParameterJsonFields(res.data[index]))
          }
          if (index < res.data.length) {
            // 还有数据，下一帧继续写入，让浏览器有机会响应用户操作
            requestAnimationFrame(writeBatch)
          } else {
            data.collapseLoading = false
          }
        }

        requestAnimationFrame(writeBatch)
      })
      .catch((e) => {
        data.collapseLoading = false
      })
  }

  function formatParameterJsonFields(item: any) {
    const propertiesToFormat = ['ass_json_all', 'file', 'ass_schema']
    propertiesToFormat.forEach((prop) => {
      if (item && typeof item[prop] === 'object' && item[prop] !== null) {
        item[prop] = formatJson(item[prop])
      }
    })
    item.__formatted = true
    return item
  }

  // 在 collapse 展开时懒格式化当前 item，避免首次渲染时阻塞主线程
  function onCollapseChange(keys: any[]) {
    if (keys.length === 0) {
      data.activeCollapseKey = []
      data.expandingIndex = -1
      return
    }
    const idx = Number(keys[keys.length - 1])
    data.activeCollapseKey = keys
    if (!isMountedCollapseItem(idx)) {
      deferMountCollapseItem(idx)
    } else {
      data.expandingIndex = -1
    }
    // 懒格式化当前 item
    const item = data.selectDataObj[idx]
    if (item && !item.__formatted) {
      formatParameterJsonFields(item)
    }
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

  function getModuleApi(moduleId: number) {
    getApiInfoName(moduleId)
      .then((res) => {
        data.apiList = res.data
      })
      .catch(console.log)
  }

  function loadDatasourceAliases() {
    getDataFactoryDatasourceAlias({
      project_product: route.query.project_product,
      status: 1,
    })
      .then((res) => {
        data.datasourceAliasOptions = (res.data || []).map((item: any) => ({
          label: item.name,
          value: item.id,
        }))
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
      if (data.isCopy) {
        value['id'] = data.copyParameterId
        postApiCaseDetailedParameterCopy(value)
          .then((res) => {
            Message.success(res.msg)
            data.isCopy = false
            data.copyParameterId = null
            doRefreshParameter(data.tabelJson.id)
          })
          .catch(console.log)
      } else if (data.isAdd) {
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
      onBeforeOk: () => {
        return deleteApiCaseDetailed(record.id, route.query.case_id)
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
    data.isCopy = false
    data.copyParameterId = null
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
      onBeforeOk: () => {
        return putApiPutRefreshApiInfo(id)
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
      onCollapseChange([0])
    })
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      doRefreshHeaders(route.query.project_product)
      getCacheDataKeyValue()
      loadDatasourceAliases()
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
    const inputItem = findItemByValue(data.textAss, value)
    if (inputItem && !jsonpathMethodUsesExpect(inputItem)) {
      item[index].expect = null
    }
    blurSave('ass_jsonpath', item, item1.id)
  }

  function shouldShowJsonpathExpect(item: any) {
    if (!item?.method) {
      return true
    }
    const inputItem = findItemByValue(data.textAss, item?.method)
    if (!inputItem) {
      return true
    }
    return jsonpathMethodUsesExpect(inputItem)
  }

  function jsonpathMethodUsesExpect(methodItem: any) {
    const parameters = Array.isArray(methodItem?.parameter) ? methodItem.parameter : []
    return parameters.some((param: any) => param.f === 'expect')
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
</script>

<style scoped>
  .api-case-workbench {
    display: grid;
    grid-template-columns: minmax(430px, 0.95fr) minmax(520px, 1.05fr);
    gap: 12px;
    height: calc(100vh - 166px);
    min-height: 0;
  }

  .api-case-panel {
    display: flex;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    flex-direction: column;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .api-case-panel-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-height: 58px;
    padding: 10px 12px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface);
  }

  .api-case-panel-title {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }

  .api-case-panel-subtitle {
    overflow: hidden;
    max-width: 680px;
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .api-case-panel-body {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: 12px;
  }

  .api-case-panel-body :deep(.arco-tabs-content) {
    min-height: 0;
  }

  .api-case-failure-reason {
    display: -webkit-box;
    overflow: hidden;
    color: var(--m-text-2);
    line-height: 22px;
    word-break: break-word;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 3;
  }

  .scenario-actions {
    margin-bottom: 8px;
  }

  .full-width {
    width: 100%;
  }

  .scenario-loading-spin {
    min-height: min(520px, calc(100vh - 300px));
    border-radius: var(--m-radius-md);
  }

  .scenario-loading-spin :deep(.arco-spin-children) {
    min-height: min(520px, calc(100vh - 300px));
  }

  .scenario-loading-spin :deep(.arco-spin-mask) {
    border-radius: var(--m-radius-md);
    background: color-mix(in srgb, var(--m-surface) 82%, transparent);
  }

  .scenario-loading-spin :deep(.arco-spin) {
    color: var(--m-primary);
  }

  .scenario-loading-spin :deep(.arco-spin-tip) {
    margin-top: 10px;
    color: var(--m-muted);
    font-size: 13px;
  }

  .scenario-tab-loading-spin {
    display: block;
    min-height: 360px;
  }

  .scenario-tab-loading-spin :deep(.arco-spin),
  .scenario-tab-loading-spin :deep(.arco-spin-children) {
    width: 100%;
    min-height: 360px;
  }

  .scenario-tab-loading-spin :deep(.arco-spin-mask) {
    border-radius: var(--m-radius-md);
    background: color-mix(in srgb, var(--m-surface) 86%, transparent);
  }

  .scenario-tab-loading-spin :deep(.arco-spin-tip) {
    color: var(--m-muted);
    font-size: 13px;
  }

  .request-header-panel {
    height: 220px;
    margin: 8px;
    overflow-y: auto;
  }

  .request-editor-actions {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 8px;
  }

  .scenario-expand-body {
    max-height: min(620px, calc(100vh - 200px));
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 4px;
  }

  .sleep-input {
    width: min(300px, 100%);
  }

  /* ── Collapse header ─────────────────────────────────────────────── */
  /* 强制 arco collapse header 插槽撑满整行 */
  :deep(.arco-collapse-item-header-title) {
    flex: 1;
    min-width: 0;
    overflow: hidden;
  }

  .custom-header {
    display: flex;
    align-items: center;
    gap: 0;
    width: 100%;
    overflow: hidden;
  }

  .custom-header__name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 13px;
    font-weight: 500;
    color: var(--m-text);
  }

  .custom-header__tags {
    display: flex;
    flex-direction: row;
    align-items: center;
    flex-shrink: 0;
    gap: 6px;
    /* 固定宽度保证所有行 tag 起始位置对齐 */
    width: 200px;
  }

  .assertion-parameters-inline {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    flex: 2;
    min-width: 300px;
  }

  .parameter-item-inline {
    display: flex;
    flex-direction: column;
    gap: 4px;
    flex: 1;
    min-width: 140px;
  }

  .parameter-label-inline {
    font-size: 12px;
    color: var(--m-muted);
    font-weight: 500;
  }

  .parameter-input-inline {
    width: 100%;
  }

  /* ── Deep 样式穿透 ───────────────────────────────────────────────── */
  :deep(.mango-test-btn) {
    flex-shrink: 0;
    margin-top: 18px;
    min-width: fit-content;
  }

  .collapse-content-loading {
    min-height: 120px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--m-muted);
  }

  :deep(.assertion-parameters-inline) {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    flex: 2;
    min-width: 300px;
    margin-top: 0;
  }

  /* ── 响应式 ──────────────────────────────────────────────────────── */
  @media (max-width: 1px) {
    .api-case-workbench {
      grid-template-columns: 1fr;
      height: auto;
    }

    .api-case-panel {
      min-height: 560px;
    }
  }

  @media (max-width: 1px) {
    :deep(.mango-test-btn) {
      margin-top: 0;
      align-self: center;
    }
  }
</style>
