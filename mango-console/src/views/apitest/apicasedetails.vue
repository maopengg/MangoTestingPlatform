<template>
  <div class="main-container">
    <a-card
      title="接口请求控制台"
      :bodyStyle="{ padding: '20px' }"
      :headStyle="{ padding: '0 10px' }"
      size="small"
      :bordered="false"
      class="card-border-radius"
    >
      <template #extra>
        <a-space>
          <a-button type="primary" size="small" @click="caseRun">执行</a-button>
          <a-button status="danger" size="small" @click="doResetSearch">返回</a-button>
        </a-space>
      </template>
      <div class="flex">
        <div class="text-lg flex-sub">
          <span> 查询依赖数据： </span>
          <a-space>
            <a-input :style="{ width: '200px' }" placeholder="请输入函数名称" v-model="input" va allow-clear />
          </a-space>
          <a-space>
            <a-button type="primary" status="warning" size="small" @click="obtain">查看</a-button>
          </a-space>
        </div>
        <div class="flex-sub">
          <a-descriptions title="响应基础信息" :data="apiData.responseData" size="small" :column="1" />
        </div>
        <div class="flex-sub">
          <a-descriptions title="响应基础信息" :data="apiData.responseData" size="small" :column="1" />
        </div>
      </div>
    </a-card>
    <div class="mt-2"></div>
    <a-collapse :default-active-key="['1', '2']" :bordered="true">
      <a-collapse-item header="请求信息" key="1">
        <div>
          <a-tabs>
            <a-tab-pane key="0" title="基础信息">
              <a-descriptions style="margin-top: 20px" :data="apiData.requestData" size="small" :column="1" />
            </a-tab-pane>
            <a-tab-pane key="1" title="请求体">{{ apiData.apiRequestBody }}</a-tab-pane>
            <a-tab-pane key="2" title="请求头">{{ apiData.apiRequestHead }}</a-tab-pane>
          </a-tabs>
        </div>
      </a-collapse-item>
      <a-collapse-item header="响应信息" key="2">
        <div>
          <a-tabs>
            <a-tab-pane key="0" title="响应体">{{ apiData.apiResponseBody }}</a-tab-pane>
            <a-tab-pane key="1" title="请求头">{{ apiData.apiResponseHead }}</a-tab-pane>
          </a-tabs>
        </div>
      </a-collapse-item>
      <a-collapse-item header="前置依赖关系" key="3">
        <div>Beijing Toutiao Technology Co., Ltd.</div>
      </a-collapse-item>
      <a-collapse-item header="后置结果处理" key="4">
        <div>Beijing Toutiao Technology Co., Ltd.</div>
      </a-collapse-item>
      <a-collapse-item header="接口断言验证" key="5">
        <div>Beijing Toutiao Technology Co., Ltd.</div>
      </a-collapse-item>
      <a-collapse-item header="后置数据清除" key="6">
        <div>Beijing Toutiao Technology Co., Ltd.</div>
      </a-collapse-item>
    </a-collapse>
  </div>
</template>

<script lang="ts" setup>
import { onMounted, ref, reactive, nextTick } from 'vue'
import { Message, Notification } from '@arco-design/web-vue'
import { get } from '@/api/http'
import { ApiRun, ApiCase, getRandomData, GetHeader } from '@/api/url'
import { useRoute } from 'vue-router'

const route = useRoute()

const apiData = reactive({
  apiRequestType: '0',
  apiRequestBody: '-',
  apiRequestHead: '-',
  apiResponseType: '0',
  apiResponseBody: '-',
  apiResponseHead: '-',
  requestData: [
    {
      label: '用例ID',
      value: '-',
      key: 'id'
    },
    {
      label: '用例名称',
      value: '-',
      key: 'name'
    },
    {
      label: '请求方法',
      value: '-',
      key: 'method'
    },
    {
      label: 'body类型',
      value: '-',
      key: 'body_type'
    },
    {
      label: '用例URL',
      value: '-',
      key: 'url'
    }
  ],
  responseData: [
    {
      label: '响应时间',
      value: '-',
      key: 'response_time'
    },
    {
      label: '状态码',
      value: '-',
      key: 'code'
    },
    {
      label: '测试环境',
      value: '-',
      key: 'environment'
    },
    {
      label: '断言结果',
      value: '-',
      key: 'assertion'
    },
    {
      label: '测试人',
      value: '-',
      key: 'testedBy'
    }
  ]
})

function doResetSearch() {
  window.history.back()
}

function caseRun() {
  Message.info('正在执行用例请稍后~')
  get({
    url: ApiRun,
    data: () => {
      return {
        id: route.query.id,
        project: route.query.project,
        environment: 1
      }
    }
  })
    .then((res) => {
      apiData.responseData.forEach(function (i) {
        i.value = res.data[i.key]
      })
      apiData.apiResponseBody = res.data.response
      apiData.apiResponseHead = res.data.header
      Message.success(res.msg)
    })
    .catch(console.log)
}

const input = ref('')

function obtain() {
  if (input.value == '') {
    Message.error('请输入数据后查询~')
  } else {
    get({
      url: getRandomData,
      data: () => {
        return {
          name: input.value
        }
      }
    })
      .then((res) => {
        Notification.success(res.data)
      })
      .catch()
  }
}

function getHead() {
  get({
    url: GetHeader,
    data: () => {
      return {
        end: 0
      }
    }
  })
    .then((res) => {
      apiData.apiRequestHead = res.data[0].value
    })
    .catch()
}

function getCaseData() {
  get({
    url: ApiCase,
    data: () => {
      return {
        id: route.query.id
      }
    }
  })
    .then((res) => {
      apiData.requestData.forEach(function (i) {
        if (i.key === 'method') {
          i.value = ['GET', 'POST', 'PUT', 'DELETE'][res.data[0].method]
        } else if (i.key === 'body_type') {
          i.value = ['-', 'JSON'][res.data[0].body_type]
        } else {
          i.value = res.data[0][i.key]
        }
      })
      apiData.apiRequestBody = res.data[0].body
    })
    .catch(console.log)
}

onMounted(() => {
  nextTick(async () => {
    getCaseData()
    getHead()
  })
})
</script>

<style>
.flex {
  display: flex;
}

.flex-sub {
  flex: 1;
}
</style>
