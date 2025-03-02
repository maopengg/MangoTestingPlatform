<template>
  <TableBody ref="tableBody">
    <template #header>
      <a-card title="测试报告" :bordered="false">
        <template #extra>
          <a-space>
            <a-button status="danger" size="small" @click="doResetSearch">返回</a-button>
          </a-space>
        </template>
        <div>
          <a-space direction="vertical" style="width: 30%">
            <p>测试套ID：{{ pageData.record.id }}</p>
            <p>任务名称：{{ pageData.record.tasks?.name }}</p>
            <p>执行时间：{{ pageData.record.create_time }}</p>
            <p>测试环境：{{ enumStore.environment_type[pageData.record.test_env].title }}</p>
            <p>执行人：{{ pageData.record.user?.name }}</p>
            <p>是否通知：{{ enumStore.status[pageData.record.is_notice].title }}</p>
          </a-space>
          <a-space size="large">
            <a-statistic title="用例总数" :value="data.summary.count" show-group-separator />
            <a-statistic
              title="成功总数"
              :value="data.summary.success_count"
              :value-style="{ color: '#33ff57' }"
            />
            <a-statistic
              title="失败总数"
              :value="data.summary.fail_count"
              :value-style="{ color: '#ff5733' }"
            />
            <a-statistic
              title="待开始数"
              :value="data.summary.stay_begin_count"
              :value-style="{ color: '#dbff33' }"
            />
            <a-statistic
              title="进行中数"
              :value="data.summary.proceed_count"
              :value-style="{ color: '#ffbd33' }"
            />
            <a-statistic title="UI总数" :value="data.summary.ui_count" />
            <a-statistic title="API总数" :value="data.summary.api_count" />
            <a-statistic title="Pytest总数" :value="data.summary.pytest_count" />
          </a-space>
        </div>
      </a-card>
    </template>
    <template #default>
      <a-card title="测试套详情" :bordered="false">
        <div class="box">
          <div class="left">
            <a-tree blockNode ref="childRef" :data="data.treeData" @select="clickTree">
              <template #icon="{ node }">
                <template v-if="node.status === 1">
                  <icon-check />
                </template>
                <template v-else>
                  <icon-close />
                </template>
              </template>
              <template #title="{ title }">
                <div v-html="title"></div>
              </template>
            </a-tree>
          </div>
          <div class="right">
            <div v-if="data.caseType === 0">
              <a-card :title="data.resultData.name" :bordered="false">
                <ElementTestReport :resultData="data.resultData" />
              </a-card>
            </div>
            <div v-else-if="data.caseType === 1">
              <a-card :title="data.resultData.name" :bordered="false">
                <ApiTestReport :resultData="data.resultData" />
              </a-card>
            </div>
            <div v-else-if="data.caseType === 2">
              <span>pytest</span>
            </div>
          </div>
        </div>
      </a-card>
    </template>
  </TableBody>
</template>
<script lang="ts" setup>
  import { onMounted, reactive, ref } from 'vue'
  import { usePageData } from '@/store/page-data'
  import {
    getSystemTestSuiteDetails,
    getSystemTestSuiteDetailsSummary,
  } from '@/api/system/test_sute_details'
  import { nanoid } from 'nanoid'
  import ElementTestReport from '@/components/ElementTestReport.vue'
  import ApiTestReport from '@/components/ApiTestReport.vue'
  import { useEnum } from '@/store/modules/get-enum'

  const enumStore = useEnum()

  const childRef: any = ref(null)

  const pageData: any = usePageData()

  const data: any = reactive({
    stepName: '',
    treeData: [],
    resultData: {},
    summary: {},
    caseType: null,
  })

  function clickTree(selectedKeys: any, eventData: any) {
    if (eventData.node?.expand) {
      childRef.value.expandNode(selectedKeys, true)
    } else {
      data.caseType = eventData.node.type
      data.resultData = eventData.node.data
    }
  }

  function doResetSearch() {
    window.history.back()
  }

  function doRefresh() {
    getSystemTestSuiteDetails(pageData.record.id)
      .then((res) => {
        res.data.forEach((item: any) => {
          const children: any = {
            title:
              item.status === 0
                ? `<span style="color: #ff5733;">${item.case_name}</span>`
                : `<span>${item.case_name}</span>`,
            key: nanoid(),
            children: [],
            expand: true,
            status: item.status,
          }
          if (item.result_data) {
            item.result_data.forEach((result_data: any) => {
              children['children'].push({
                title:
                  result_data.status === 0
                    ? `<span style="color: #ff5733;">${result_data.name}</span>`
                    : `<span>${result_data.name}</span>`,
                key: nanoid(),
                data: result_data,
                type: item.type,
                status: result_data.status,
                children: [],
              })
            })
          }
          data.treeData.push(children)
        })
      })
      .catch(console.log)
  }

  function doRefreshSummary() {
    getSystemTestSuiteDetailsSummary(pageData.record.id)
      .then((res) => {
        data.summary = res.data
      })
      .catch(console.log)
  }

  onMounted(() => {
    doRefresh()
    doRefreshSummary()
  })
</script>
<style lang="less">
  .box {
    width: 100%;
    margin: 0 auto;
    padding: 5px;
    box-sizing: border-box;
    display: flex;
  }

  .left {
    flex: 4;
    padding: 5px;
  }

  .right {
    flex: 6;
    padding: 5px;
    max-width: 60%; /* 或者根据实际需求调整 */
  }
</style>
