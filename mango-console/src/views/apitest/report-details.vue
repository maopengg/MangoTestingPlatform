<template>
  <div class="main-container">
    <a-card title="界面测试报告详情">
      <template #extra>
        <a-affix :offsetTop="80">
          <a-space>
            <a-button status="danger" size="small" @click="doResetSearch">返回</a-button>
          </a-space>
        </a-affix>
      </template>
      <div class="container">
        <a-space direction="vertical" style="width: 30%">
          <p>测试套ID：{{ pageData.record.id }}</p>
          <p>所属项目：{{ pageData.record.project?.name }}</p>
          <p>执行时间：{{ pageData.record.create_time }}</p>
          <p>执行状态：{{ pageData.record.run_status === 1 ? '已完成' : '执行中' }}</p>
        </a-space>
        <a-space direction="vertical" style="width: 42%">
          <p>测试对象：{{ pageData.record.test_object?.name }}</p>
          <p
            >是否开启数据库断言：{{
              pageData.record.test_object?.db_status === 1 ? '开启' : '关闭'
            }}</p
          >
          <p :style="{ color: pageData.record.status === 0 ? 'red' : 'inherit' }">
            测试套结果：{{ pageData.record.status === 1 ? '通过' : '失败' }}
          </p>
          <p>失败消息：{{ pageData.record.error_message }}</p>
        </a-space>
        <a-space
          size="large"
          v-for="item of reportDetailsData.summary"
          :key="item.name"
          style="width: 7%"
        >
          <a-statistic :title="item.name" :value="item.value" show-group-separator />
        </a-space>
      </div>
    </a-card>
    <a-card title="测试套数据">
      <div class="container">
        <a-space direction="vertical" style="width: 40%">
          <a-tree blockNode ref="childRef" :data="reportDetailsData.treeData" @select="click">
            <template #icon="{ node }">
              <template v-if="node.status === 1"> <icon-check /> </template>
              <template v-else> <icon-close /> </template>
            </template>
          </a-tree>
        </a-space>
        <a-space direction="vertical" style="width: 60%">
          <a-tabs default-active-key="1">
            <a-tab-pane key="1" title="接口信息">
              <a-space direction="vertical">
                <p>接口ID：{{ reportDetailsData.apiResult.api_info?.id }}</p>
                <p>接口名称：{{ reportDetailsData.apiResult.api_info?.name }}</p>
                <p
                  >请求方法：{{
                    reportDetailsData.methodType[reportDetailsData.apiResult.api_info?.method]
                  }}</p
                >
                <p
                  >请求端：{{
                    reportDetailsData.clientType[reportDetailsData.apiResult.api_info?.client]
                  }}</p
                >
                <p>请求url：{{ reportDetailsData.apiResult.url }}</p>
              </a-space>
            </a-tab-pane>
            <a-tab-pane key="2" title="请求头">
              <pre>{{ strJson(reportDetailsData.apiResult.headers) }}</pre>
            </a-tab-pane>
            <a-tab-pane key="3" title="参数">
              <pre>{{ strJson(reportDetailsData.apiResult.params) }}</pre>
            </a-tab-pane>
            <a-tab-pane key="4" title="data">
              <pre>{{ strJson(reportDetailsData.apiResult.data) }}</pre>
            </a-tab-pane>
            <a-tab-pane key="5" title="json">
              <pre>{{ strJson(reportDetailsData.apiResult.json) }}</pre>
            </a-tab-pane>
            <a-tab-pane key="6" title="文件">
              <pre>{{ strJson(reportDetailsData.apiResult.file) }}</pre>
            </a-tab-pane>
            <a-tab-pane key="7" title="响应信息">
              <a-space direction="vertical">
                <p>响应code码：{{ reportDetailsData.apiResult.response_code }}</p>
                <p>响应时间：{{ reportDetailsData.apiResult.response_time }}</p>
                <p :style="{ color: reportDetailsData.apiResult.status === 0 ? 'red' : 'inherit' }">
                  测试结果：{{ reportDetailsData.apiResult.status === 1 ? '成功' : '失败' }}
                </p>
                <p v-if="reportDetailsData.apiResult.status === 0"
                  >错误提示语：{{ reportDetailsData.apiResult.error_message }}</p
                >
              </a-space>
            </a-tab-pane>
            <a-tab-pane key="8" title="响应头">
              <pre>{{ strJson(reportDetailsData.apiResult.response_headers) }}</pre>
            </a-tab-pane>
            <a-tab-pane key="9" title="响应体">
              <pre>{{ strJson(reportDetailsData.apiResult.response_text) }}</pre>
            </a-tab-pane>
            <a-tab-pane key="10" title="缓存数据">
              <pre>{{ strJson(reportDetailsData.apiResult.all_cache) }}</pre>
            </a-tab-pane>
            <a-tab-pane key="11" title="断言数据">
              <pre>{{ strJson(reportDetailsData.apiResult.all_cache) }}</pre>
            </a-tab-pane>
          </a-tabs>
        </a-space>
      </div>
    </a-card>
  </div>
</template>
<script lang="ts" setup>
  import { reactive, onMounted, nextTick, ref } from 'vue'
  import { apiResultSuiteCase, apiInfoResult, systemEnumMethod, systemEnumEnd } from '@/api/url'
  import { get } from '@/api/http'
  import { usePageData } from '@/store/page-data'
  import { strJson } from '@/utils/tools'

  const pageData: any = usePageData()

  const reportDetailsData: any = reactive({
    treeData: [],
    summary: [],
    apiResult: {},
    clientType: [],
    methodType: [],
  })
  const childRef: any = ref(null)

  function click(key: any) {
    if (key[0][0] === '1') {
      childRef.value.expandNode(key, true) // 调用子组件的方法
      return
    }
    get({
      url: apiInfoResult,
      data: () => {
        return {
          id: key[0].substring(2),
        }
      },
    })
      .then((res) => {
        reportDetailsData.apiResult = res.data[0]
      })
      .catch(console.log)
  }

  function doResetSearch() {
    window.history.back()
  }

  function doRefresh() {
    get({
      url: apiResultSuiteCase,
      data: () => {
        return {
          test_suite_id: pageData.record.id,
        }
      },
    })
      .then((res) => {
        reportDetailsData.treeData = res.data.data
        console.log(res.data.data)

        reportDetailsData.summary = res.data.summary
      })
      .catch(console.log)
  }
  function doMethodType() {
    get({
      url: systemEnumMethod,
    })
      .then((res) => {
        res.data.forEach((item: any) => {
          reportDetailsData.methodType.push(item.title)
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
          reportDetailsData.clientType.push(item.title)
        })
      })
      .catch(console.log)
  }
  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      doMethodType()
      doClientType()
    })
  })
</script>
<style>
  .content-container {
    display: flex;
  }

  .left-content {
    flex: 1;
    padding-right: 10px;
  }

  .right-content {
    flex: 1;
    padding-left: 10px;
  }

  .divider {
    width: 1px;
    background-color: #ccc;
    margin: 0 10px;
    position: relative;
  }

  .divider:before {
    content: '';
    position: absolute;
    top: 0;
    bottom: 0;
    left: -3px;
    border-left: 1px dashed #ccc;
  }

  .span {
    display: block;
    font-size: 16px;
    font-weight: bold;
    margin-top: 10px;
    margin-bottom: 10px;
  }

  .verticallayout > div {
    flex: 1;
  }

  .pppp {
    display: -webkit-box;
    -webkit-line-clamp: 5; /* 设置为盒子高度的百分之80 */
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
</style>
