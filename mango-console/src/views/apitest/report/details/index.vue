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
          <span>所属项目：{{ pageData.record.project_product?.project?.name }}</span>
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
            测试套结果：{{
              pageData.record.status === 1
                ? '通过'
                : pageData.record.status === 0
                ? '失败'
                : '未测试'
            }}
          </p>
          <p>失败消息：{{ pageData.record.error_message }}</p>
        </a-space>
        <a-space size="large" v-for="item of data.summary" :key="item.name" style="width: 7%">
          <a-statistic :title="item.name" :value="item.value" show-group-separator />
        </a-space>
      </div>
    </a-card>
    <a-card title="测试套数据">
      <div class="container">
        <a-space direction="vertical" style="width: 40%">
          <a-tree blockNode ref="childRef" :data="data.treeData" @select="click">
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
                <p>接口ID：{{ data.apiResult.api_info?.id }}</p>
                <p>接口名称：{{ data.apiResult.api_info?.name }}</p>
                <p>请求方法：{{ data.methodType[data.apiResult.api_info?.method] }}</p>
                <p>请求端：{{ data.clientType[data.apiResult.api_info?.client] }}</p>
                <p>请求url：{{ data.apiResult.url }}</p>
              </a-space>
            </a-tab-pane>
            <a-tab-pane key="2" title="请求头">
              <pre>{{ strJson(data.apiResult.headers) }}</pre>
            </a-tab-pane>
            <a-tab-pane key="3" title="参数">
              <pre>{{ strJson(data.apiResult.params) }}</pre>
            </a-tab-pane>
            <a-tab-pane key="4" title="data">
              <pre>{{ strJson(data.apiResult.data) }}</pre>
            </a-tab-pane>
            <a-tab-pane key="5" title="json">
              <pre>{{ strJson(data.apiResult.json) }}</pre>
            </a-tab-pane>
            <a-tab-pane key="6" title="文件">
              <pre>{{ strJson(data.apiResult.file) }}</pre>
            </a-tab-pane>
            <a-tab-pane key="7" title="响应信息">
              <a-space direction="vertical">
                <p>响应code码：{{ data.apiResult.response_code }}</p>
                <p>响应时间：{{ data.apiResult.response_time }}</p>
                <p :style="{ color: data.apiResult.status === 0 ? 'red' : 'inherit' }">
                  测试结果：{{
                    data.apiResult.status === 1 ? '通过' : data.apiResult.status === 0 ? '失败' : ''
                  }}
                </p>
                <p v-if="data.apiResult.status === 0"
                  >错误提示语：{{ data.apiResult.error_message }}</p
                >
              </a-space>
            </a-tab-pane>
            <a-tab-pane key="8" title="响应头">
              <pre>{{ strJson(data.apiResult.response_headers) }}</pre>
            </a-tab-pane>
            <a-tab-pane key="9" title="响应体">
              <pre>{{ strJson(data.apiResult.response_text) }}</pre>
            </a-tab-pane>
            <a-tab-pane key="10" title="缓存数据">
              <pre>{{ strJson(data.apiResult.all_cache) }}</pre>
            </a-tab-pane>
            <a-tab-pane key="11" title="断言数据">
              <pre>{{ strJson(data.apiResult.assertion) }}</pre>
            </a-tab-pane>
          </a-tabs>
        </a-space>
      </div>
    </a-card>
  </div>
</template>
<script lang="ts" setup>
  import { reactive, onMounted, nextTick, ref } from 'vue'
  import { usePageData } from '@/store/page-data'
  import { strJson } from '@/utils/tools'
  import { getSystemEnumEnd, getSystemEnumMethod } from '@/api/system'
  import { getApiInfoResult, getApiResultSuiteCase } from '@/api/apitest'

  const pageData: any = usePageData()

  const data: any = reactive({
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
    getApiInfoResult(key[0].substring(2))
      .then((res) => {
        data.apiResult = res.data[0]
      })
      .catch(console.log)
  }

  function doResetSearch() {
    window.history.back()
  }

  function doRefresh() {
    getApiResultSuiteCase(pageData.record.id)
      .then((res) => {
        data.treeData = res.data.data
        data.summary = res.data.summary
      })
      .catch(console.log)
  }
  function doMethodType() {
    getSystemEnumMethod()
      .then((res) => {
        res.data.forEach((item: any) => {
          data.methodType.push(item.title)
        })
      })
      .catch(console.log)
  }

  function doClientType() {
    getSystemEnumEnd()
      .then((res) => {
        res.data.forEach((item: any) => {
          data.clientType.push(item.title)
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
  p {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
</style>
