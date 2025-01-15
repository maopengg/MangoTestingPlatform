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
          <p>当前状态：{{ enumStore.task_status[pageData.record.status].title }}</p>
        </a-space>
        <a-space direction="vertical" style="width: 42%" />
        <a-space size="large" v-for="item of data.summary" :key="item.name" style="width: 7%">
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
            </template>
          </TableBody>
        </div>
        <div class="divider"></div>
        <div class="right-content">
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
      </div>
    </a-card>
  </div>
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
  }

  function doResetSearch() {
    window.history.back()
  }

  function doRefresh() {
    getSystemTestSuiteDetails(pageData.record.id)
      .then((res) => {
        res.data.forEach((item: any) => {
          const children: any = {
            title: item.case_id + '-' + item.case_name,
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
