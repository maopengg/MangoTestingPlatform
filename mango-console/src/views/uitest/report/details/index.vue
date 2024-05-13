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
          <p>所属项目：{{ pageData.record.project_product?.project?.name }}</p>
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
    <a-card>
      <div class="content-container">
        <div class="left-content">
          <span class="span">测试套</span>
          <TableBody ref="tableBody">
            <template #header>
              <a-tree
                blockNode
                ref="childRef"
                :data="reportDetailsData.treeData"
                @select="(key) => click(key[0])"
              >
                <template #icon="{ node }">
                  <template v-if="node.status === 1"> <icon-check /> </template>
                  <template v-else> <icon-close /> </template>
                </template>
              </a-tree>
            </template>
          </TableBody>
        </div>
        <div class="divider"></div>
        <div class="right-content">
          <div>
            <span class="span">{{ reportDetailsData.stepName }}</span>
          </div>
          <div v-if="reportDetailsData.stepName">
            <a-collapse
              :default-active-key="reportDetailsData.eleResultKey"
              v-for="item of reportDetailsData.eleResult"
              :bordered="false"
              :key="item.id"
              destroy-on-hide
            >
              <a-collapse-item :header="item.ele_name" :style="customStyle" :key="item.id">
                <div>
                  <a-space direction="vertical" style="width: 50%">
                    <p
                      >输入类型：{{
                        item.ope_type ? getLabelByValue(reportDetailsData.ope, item.ope_type) : '-'
                      }}</p
                    >
                    <p
                      >断言类型：{{
                        item.ass_type ? getLabelByValue(reportDetailsData.ass, item.ass_type) : '-'
                      }}</p
                    >
                    <p
                      >表达式类型：{{
                        item.exp ? reportDetailsData.eleExp[item.exp].title : item.exp
                      }}</p
                    >
                    <p>测试结果：{{ item.status === 1 ? '成功' : '失败' }}</p>
                    <p>等待时间：{{ item.sleep ? item.sleep : '-' }}</p>
                    <p v-if="item.status === 0">错误提示：{{ item.error_message }}</p>
                    <p v-if="item.expect">预期：{{ item.expect }}</p>
                  </a-space>
                  <a-space direction="vertical" style="width: 50%">
                    <p>输入值：{{ item.ope_value ? item.ope_value : '-' }}</p>
                    <p style="word-wrap: break-word">元素表达式：{{ item.loc }}</p>
                    <p>断言值：{{ item.ass_value ? item.ass_value : '-' }}</p>
                    <p>元素个数：{{ item.ele_quantity }}</p>
                    <p>元素下标：{{ item.sub ? item.sub : '-' }}</p>
                    <p v-if="item.status === 0">失败截图：{{ item.picture_path }}</p>
                    <p v-if="item.expect">实际：{{ item.actual }}</p>
                  </a-space>
                </div>
              </a-collapse-item>
            </a-collapse>
          </div>
        </div>
      </div>
    </a-card>
  </div>
</template>
<script lang="ts" setup>
  import { reactive, onMounted, nextTick, ref } from 'vue'
  import {
    systemEnumExp,
    uiCaseResultSuiteGetCase,
    uiEleResultEle,
    uiPageStepsDetailedAss,
    uiPageStepsDetailedOpe,
  } from '@/api/url'
  import { get } from '@/api/http'
  import { usePageData } from '@/store/page-data'
  import { useRoute } from 'vue-router'
  const childRef: any = ref(null)

  const pageData: any = usePageData()
  const route = useRoute()

  const reportDetailsData: any = reactive({
    stepName: '',
    treeData: [],
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

  function click(key: string) {
    childRef.value.expandNode(key, true) // 调用子组件的方法
    let obj = JSON.parse(key)
    reportDetailsData.treeData.forEach((item: any) => {
      if (item.children.length !== 0) {
        item.children.forEach((i: any) => {
          if (i.key == key) {
            reportDetailsData.stepName = i.title
            return
          }
        })
      }
      if (item.key == key) {
        reportDetailsData.stepName = item.title
        return
      }
    })
    if (obj.page_steps_result) {
      get({
        url: uiEleResultEle,
        data: () => {
          return {
            test_suite_id: obj.test_suite_id,
            page_step_id: obj.page_step_id,
            case_id: obj.case_id,
          }
        },
      })
        .then((res) => {
          reportDetailsData.eleResult = res.data
          res.data.forEach((item: any) => {
            if (item.status === 0) {
              reportDetailsData.eleResultKey.push(item.id)
            }
          })
          console.log(reportDetailsData.eleResultKey)
        })
        .catch(console.log)
    } else {
      reportDetailsData.eleResult = []
    }
  }

  function doResetSearch() {
    window.history.back()
  }

  function doRefresh() {
    get({
      url: uiCaseResultSuiteGetCase,
      data: () => {
        return {
          test_suite_id: route.query.id,
        }
      },
    })
      .then((res) => {
        reportDetailsData.treeData = res.data.data
        reportDetailsData.summary = res.data.summary
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

  function getEleExp() {
    get({
      url: systemEnumExp,
      data: () => {
        return {}
      },
    })
      .then((res) => {
        reportDetailsData.eleExp = res.data
      })
      .catch(console.log)
  }

  function getUiRunSortAss() {
    get({
      url: uiPageStepsDetailedAss,
      data: () => {
        return {}
      },
    })
      .then((res) => {
        reportDetailsData.ass = res.data
      })
      .catch(console.log)
  }

  function getUiRunSortOpe() {
    get({
      url: uiPageStepsDetailedOpe,
      data: () => {
        return {}
      },
    })
      .then((res) => {
        reportDetailsData.ope = res.data
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      getEleExp()
      getUiRunSortOpe()
      getUiRunSortAss()
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
