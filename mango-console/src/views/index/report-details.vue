<template>
  <div class="main-container">
    <a-card>
      <template #title>
        <div class="title-container">
          <span>测试套ID：{{ route.query.id }}</span>
          <a-button status="danger" size="small" @click="doResetSearch">返回</a-button>
        </div>
      </template>
      <div class="xxxxx">
        <div class="stats-container">
          <a-space size="large" v-for="item of reportDetailsData.summary" :key="item.name">
            <a-statistic :title="item.name" :value="item.value" :class="{ header: item.name === '失败' }" show-group-separator />
          </a-space>
        </div>
        <div class="content-container">
          <div class="left-content">
            <span class="span">测试套</span>
            <TableBody ref="tableBody">
              <template #header>
                <a-tree blockNode :data="reportDetailsData.treeData" @select="(key) => click(key[0])">
                  <template #icon>
                    <IconStar />
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
                <a-collapse-item
                  :header="item.ele_name_a"
                  :style="customStyle"
                  :key="item.id"
                  :class="{ 'red-header': item.status !== 1 }"
                >
                  <div class="verticallayout">
                    <div>
                      <div>测试结果：{{ item.status === 1 ? '成功' : '失败' }}</div>
                      <div>元素个数：{{ item.ele_quantity }}</div>
                      <div>元素表达式：{{ item.loc }}</div>
                      <div>表达式类型：{{ item.exp }}</div>
                      <div>等待时间：{{ item.sleep ? item.sleep : '-' }}</div>
                      <div v-if="item.status === 0">错误提示：{{ item.msg }}</div>
                    </div>
                    <div>
                      <div>元素下标：{{ item.sub ? item.sub : '-' }}</div>
                      <div>输入类型：{{ item.ope_type ? item.ope_type : '-' }}</div>
                      <div>输入值：{{ item.ope_value ? item.ope_value : '-' }}</div>
                      <div>断言类型：{{ item.ass_type ? item.ass_type : '-' }}</div>
                      <div>断言值：{{ item.ass_value ? item.ass_value : '-' }}</div>
                      <div v-if="item.status === 0">失败截图：{{ item.picture_path }}</div>
                    </div>
                  </div>
                </a-collapse-item>
              </a-collapse>
            </div>
          </div>
        </div>
      </div>
    </a-card>
  </div>
</template>
<script lang="ts" setup>
import { reactive, onMounted, nextTick } from 'vue'
import { Message } from '@arco-design/web-vue'
import { uiCaseResultSuiteGetCase, uiEleResultEle } from '@/api/url'
import { get } from '@/api/http'
import { useRoute } from 'vue-router'

const route = useRoute()

const reportDetailsData = reactive({
  stepName: '',
  treeData: [],
  summary: [],
  eleResult: [],
  eleResultKey: []
})
const customStyle = reactive({
  borderRadius: '6px',
  marginBottom: '2px',
  border: 'none',
  overflow: 'hidden'
})

function click(key: string) {
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
  // reportDetailsData.stepName = key
  if (obj.page_steps_result) {
    get({
      url: uiEleResultEle,
      data: () => {
        return {
          test_suite_id: obj.test_suite_id,
          page_step_id: obj.page_step_id,
          case_id: obj.case_id
        }
      }
    })
      .then((res) => {
        reportDetailsData.eleResult = res.data
        reportDetailsData.eleResultKey = res.data.map((item: any) => item.id)
        // Message.success(res.msg)
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
        test_suite_id: route.query.id
      }
    }
  })
    .then((res) => {
      reportDetailsData.treeData = res.data.data
      reportDetailsData.summary = res.data.summary
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
.title-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.content-container {
  display: flex;
}

.xxxxx {
  display: flex;
  flex-direction: column;
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

.stats-container {
  display: flex;
  justify-content: space-between;
  width: 20%;
}
.header {
  color: red;
}

.verticallayout {
  display: flex;
  flex-direction: row;
}
.verticallayout > div {
  flex: 1;
}
</style>
