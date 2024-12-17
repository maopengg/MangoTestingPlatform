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
              <template v-if="node.status === 1">
                <icon-check />
              </template>
              <template v-else>
                <icon-close />
              </template>
            </template>
          </a-tree>
        </a-space>
        <a-space direction="vertical" style="width: 60%">
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
        </a-space>
      </div>
    </a-card>
  </div>
</template>
<script lang="ts" setup>
  import { reactive, onMounted, nextTick, ref } from 'vue'
  import { usePageData } from '@/store/page-data'
  import { strJson } from '@/utils/tools'
  import { getSystemTestSuiteDetails } from '@/api/system/test_sute_details'
  // import { useEnum } from '@/store/modules/get-enum'
  // const enumStore = useEnum()

  const pageData: any = usePageData()

  const data: any = reactive({
    treeData: [],
    summary: [],
    selectData: {},

    apiResult: {},
  })
  const childRef: any = ref(null)

  function click(key: any) {
    if (typeof key[0] === 'number') {
      childRef.value.expandNode(key, true)
      return
    }
    data.selectData = key[0]
  }

  function doResetSearch() {
    window.history.back()
  }

  function doRefresh() {
    getSystemTestSuiteDetails(pageData.record.id)
      .then((res) => {
        res.data.forEach((item: any) => {
          const children: any = {
            title: item.case_name,
            key: item.case_id,
            status: item.status,
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

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
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
