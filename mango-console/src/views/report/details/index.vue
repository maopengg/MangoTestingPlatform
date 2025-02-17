<template>
  <TableBody ref="tableBody">
    <template #header>
      <a-card title="测试报告详情" :bordered="false">
        <template #extra>
          <a-space>
            <a-button status="danger" size="small" @click="doResetSearch">返回</a-button>
          </a-space>
        </template>
        <div>
          <a-space direction="vertical" style="width: 30%">
            <p>测试套ID：{{ pageData.record.id }}</p>
            <p>所属项目：{{ pageData.record.project_product?.project?.name }}</p>
            <p>执行时间：{{ pageData.record.create_time }}</p>
            <p>当前状态：{{ enumStore.task_status[pageData.record.status].title }}</p>
            <!--            <p>当前状态：{{ enumStore.test_case_type[pageData.record.type].title }}</p>-->
          </a-space>
          <a-space size="large" v-for="item of data.summary" :key="item.name" style="width: 7%">
            <a-statistic :title="item.name" :value="item.value" show-group-separator />
          </a-space>
        </div>
      </a-card>
    </template>
    <template #default>
      <a-card title="测试套" :bordered="false">
        <div class="box">
          <div class="left">
            <a-tree blockNode ref="childRef" :data="data.treeData" @select="(key) => click(key)">
              <template #icon="{ node }">
                <template v-if="node.status === 1">
                  <icon-check />
                </template>
                <template v-else>
                  <icon-close />
                </template>
              </template>
              <template #title="{ title }">
                <div>
                  <span>{{ getNodeTitle(title) }}</span>
                </div>
              </template>
            </a-tree>
          </div>
          <div class="right">
            <div v-if="data.selectData.type === 0">
              <a-collapse
                :default-active-key="data.eleResultKey"
                v-for="item of data.selectData.element_result_list"
                :bordered="false"
                :key="item.id"
                destroy-on-hide
              >
                <a-collapse-item :header="item.name" :style="customStyle" :key="item.id">
                  <div>
                    <a-space direction="vertical" style="width: 50%">
                      <p
                        >操作类型：{{
                          item.type === 0
                            ? getLabelByValue(data.ope, item.ope_key)
                            : getLabelByValue(data.ass, item.ope_key)
                        }}</p
                      >
                      <p
                        >表达式类型：{{
                          item.exp ? enumStore.element_exp[item.exp].title : item.exp
                        }}</p
                      >
                      <p
                        >测试结果：{{
                          item.status === 1 ? '通过' : item.status === 0 ? '失败' : '未测试'
                        }}</p
                      >
                      <p>等待时间：{{ item.sleep ? item.sleep : '-' }}</p>
                      <p v-if="item.status === 0">错误提示：{{ item.error_message }}</p>
                      <p v-if="item.expect">预期：{{ item.expect }}</p>
                      <p v-if="item.status === 0">视频路径：{{ item.video_path }}</p>
                    </a-space>
                    <a-space direction="vertical" style="width: 50%">
                      <p style="word-wrap: break-word">元素表达式：{{ item.loc }}</p>
                      <p>元素个数：{{ item.ele_quantity }}</p>
                      <p>元素下标：{{ item.sub ? item.sub : '-' }}</p>
                      <div v-if="item.status === 0">
                        <a-image
                          :src="minioURL + '/failed_screenshot/' + item.picture_path"
                          title="失败截图"
                          width="260"
                          style="margin-right: 67px; vertical-align: top"
                          :preview-visible="visible1"
                          @preview-visible-change="
                            () => {
                              visible1 = false
                            }
                          "
                        >
                          <template #extra>
                            <div class="actions">
                              <span
                                class="action"
                                @click="
                                  () => {
                                    visible1 = true
                                  }
                                "
                                ><icon-eye
                              /></span>
                              <span class="action"><icon-download /></span>
                              <a-tooltip content="失败截图">
                                <span class="action"><icon-info-circle /></span>
                              </a-tooltip>
                            </div>
                          </template>
                        </a-image>
                      </div>
                      <p v-if="item.expect">实际：{{ item.actual }}</p>
                    </a-space>
                  </div>
                </a-collapse-item>
              </a-collapse>
            </div>
            <div v-else-if="data.selectData.type === 1">
              <a-tabs default-active-key="1">
                <a-tab-pane key="1" title="接口信息">
                  <a-space direction="vertical">
                    <p>接口ID：{{ data.selectData?.id }}</p>
                    <p>接口名称：{{ data.selectData?.name }}</p>
                    <p>请求方法：{{ data.selectData?.request?.method }}</p>
                    <p>请求url：{{ data.selectData?.request?.url }}</p>
                  </a-space>
                </a-tab-pane>
                <a-tab-pane key="2" title="请求头">
                  <pre>{{ strJson(data.selectData?.request?.headers) }}</pre>
                </a-tab-pane>
                <a-tab-pane key="3" title="参数">
                  <pre>{{ strJson(data.selectData?.request?.params) }}</pre>
                </a-tab-pane>
                <a-tab-pane key="4" title="data">
                  <pre>{{ strJson(data.selectData?.request?.data) }}</pre>
                </a-tab-pane>
                <a-tab-pane key="5" title="json">
                  <pre>{{ strJson(data.selectData?.request?.json) }}</pre>
                </a-tab-pane>
                <a-tab-pane key="6" title="文件">
                  <pre>{{ strJson(data.selectData?.request?.file) }}</pre>
                </a-tab-pane>
                <a-tab-pane key="7" title="响应信息">
                  <a-space direction="vertical">
                    <p>响应code码：{{ data.selectData?.response?.status_code }}</p>
                    <p>响应时间：{{ data.selectData?.response?.response_time }}</p>
                    <p :style="{ color: data.selectData?.status === 0 ? 'red' : 'inherit' }">
                      测试结果：{{
                        data.selectData?.status === 1
                          ? '通过'
                          : data.selectData?.status === 0
                          ? '失败'
                          : ''
                      }}
                    </p>
                    <p v-if="data.selectData?.status === 0"
                      >错误提示语：{{ data.selectData?.error_message }}</p
                    >
                  </a-space>
                </a-tab-pane>
                <a-tab-pane key="8" title="响应头">
                  <pre>{{ strJson(data.selectData?.response?.response_headers) }}</pre>
                </a-tab-pane>
                <a-tab-pane key="9" title="响应体">
                  <pre>{{ strJson(data.selectData?.response?.response_text) }}</pre>
                </a-tab-pane>
                <a-tab-pane key="10" title="缓存数据">
                  <pre>{{ strJson(data.selectData?.cache_data) }}</pre>
                </a-tab-pane>
                <a-tab-pane key="11" title="断言数据">
                  <pre>{{ strJson(data.selectData?.ass) }}</pre>
                </a-tab-pane>
              </a-tabs>
            </div>
            <div v-else-if="data.selectData.type === 2">
              <span>界面pytest</span>
            </div>
            <div v-else>
              <span>接口pytest</span>
            </div>
          </div>
        </div>
      </a-card>
    </template>
  </TableBody>
</template>
<script lang="ts" setup>
  import { nextTick, onMounted, reactive, ref } from 'vue'
  import { usePageData } from '@/store/page-data'
  import {
    getUiPageStepsDetailedAss,
    getUiPageStepsDetailedOpe,
  } from '@/api/uitest/page-steps-detailed'
  import { getSystemTestSuiteDetails } from '@/api/system/test_sute_details'
  import { minioURL } from '@/api/axios.config'
  import { useEnum } from '@/store/modules/get-enum'
  import { strJson } from '@/utils/tools'

  const childRef: any = ref(null)
  const enumStore = useEnum()

  const pageData: any = usePageData()

  const data: any = reactive({
    stepName: '',
    treeData: [],
    selectData: {},
    summary: [],
    eleResult: [],
    eleResultKey: [],
    eleExp: [],
    ass: [],
    ope: [],
  })
  const customStyle = reactive({
    borderRadius: '6px',
    marginBottom: '2px',
    border: 'none',
    overflow: 'hidden',
  })
  const visible1 = ref(false)

  function click(key: any) {
    if (typeof key[0] === 'number') {
      childRef.value.expandNode(key, true)
      return
    }
    data.selectData = key[0]
    console.log(data.selectData)
  }

  function doResetSearch() {
    window.history.back()
  }

  function doRefresh() {
    getSystemTestSuiteDetails(pageData.record.id)
      .then((res) => {
        res.data.forEach((item: any) => {
          const children: any = {
            title: `用例ID：${item.case_id}--用例名称：${item.case_name}`,
            key: item.case_id,
            status: item.status,
            error_msg: item.error_message,
            children: [],
          }
          if (item.result_data) {
            item.result_data.forEach((item1: any) => {
              children['children'].push({
                title: item1.name,
                key: item1,
                status: item1.status,
                children: [],
              })
            })
          }
          data.treeData.push(children)
        })
      })
      .catch(console.log)
  }

  function getLabelByValue(data: any, value: string): string {
    const list = [...data]
    for (const item of list) {
      if (item.children) {
        list.push(...item.children)
      }
    }
    return list.find((item: any) => item.value === value)?.label
  }

  function getUiRunSortAss() {
    getUiPageStepsDetailedAss(null)
      .then((res) => {
        data.ass = res.data
      })
      .catch(console.log)
  }

  function getUiRunSortOpe() {
    getUiPageStepsDetailedOpe(null)
      .then((res) => {
        data.ope = res.data
      })
      .catch(console.log)
  }

  function getNodeTitle(title: string) {
    for (const item of data.treeData) {
      if (item.title == title && item.error_msg) {
        return title + '-' + item.error_msg
      }
    }
    return title
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      getUiRunSortOpe()
      getUiRunSortAss()
    })
  })
</script>
<style lang="less"></style>
