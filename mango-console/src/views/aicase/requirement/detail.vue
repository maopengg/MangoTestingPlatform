<template>
  <div class="ai-detail-page">
    <a-page-header :title="reqName" subtitle="需求分析详情" @back="router.back()">
      <template #extra>
        <a-space>
          <a-tag :color="statusColorMap[requirement?.status]">{{ statusLabelMap[requirement?.status] }}</a-tag>
          <a-button v-if="requirement?.status === 2" type="primary" size="small" @click="onGeneratePoints">
            确认拆分并生成测试点
          </a-button>
          <a-button v-if="requirement?.status === 4" type="primary" size="small" @click="onGenerateCases">
            确认测试点并生成用例
          </a-button>
        </a-space>
      </template>
    </a-page-header>

    <a-steps :current="stepCurrent" style="margin: 16px 24px">
      <a-step title="需求拆分" description="AI拆分功能子模块" />
      <a-step title="测试点" description="AI生成测试点" />
      <a-step title="测试用例" description="AI生成详细用例" />
    </a-steps>

    <a-row :gutter="16" style="padding: 0 16px">
      <!-- 左：需求拆分 -->
      <a-col :span="6">
        <a-card title="需求拆分" :bordered="false">
          <template #extra>
            <a-button size="mini" type="text" @click="loadSplits">刷新</a-button>
          </template>
          <a-list :loading="splitLoading">
            <a-list-item v-for="item in splits" :key="item.id"
              :class="{ 'selected-split': selectedSplitId === item.id }"
              style="cursor:pointer" @click="onSelectSplit(item)">
              <a-space>
                <a-tag :color="confirmColorMap[item.is_confirmed]" size="small">
                  {{ confirmLabelMap[item.is_confirmed] }}
                </a-tag>
                <span>{{ item.name }}</span>
              </a-space>
              <template #actions>
                <a-space>
                  <a-button size="mini" type="text" status="success"
                    @click.stop="onConfirmSplit(item, 1)">确认</a-button>
                  <a-button size="mini" type="text" status="danger"
                    @click.stop="onConfirmSplit(item, 2)">忽略</a-button>
                </a-space>
              </template>
            </a-list-item>
          </a-list>
        </a-card>
      </a-col>

      <!-- 中：测试点 -->
      <a-col :span="8">
        <a-card :title="selectedSplitId ? `测试点 - ${selectedSplitName}` : '测试点'" :bordered="false">
          <template #extra>
            <a-button size="mini" type="text" @click="loadPoints">刷新</a-button>
          </template>
          <a-list :loading="pointLoading">
            <a-list-item v-for="item in testPoints" :key="item.id"
              :class="{ 'selected-point': selectedPointId === item.id }"
              style="cursor:pointer" @click="onSelectPoint(item)">
              <a-space direction="vertical" fill>
                <a-space>
                  <a-tag :color="confirmColorMap[item.is_confirmed]" size="small">
                    {{ confirmLabelMap[item.is_confirmed] }}
                  </a-tag>
                  <a-tag :color="pointTypeColorMap[item.test_type]" size="small">
                    {{ pointTypeLabelMap[item.test_type] }}
                  </a-tag>
                  <span>{{ item.name }}</span>
                </a-space>
              </a-space>
              <template #actions>
                <a-space>
                  <a-button size="mini" type="text" status="success"
                    @click.stop="onConfirmPoint(item, 1)">确认</a-button>
                  <a-button size="mini" type="text" status="danger"
                    @click.stop="onConfirmPoint(item, 2)">忽略</a-button>
                </a-space>
              </template>
            </a-list-item>
          </a-list>
        </a-card>
      </a-col>

      <!-- 右：测试用例 -->
      <a-col :span="10">
        <a-card :title="selectedPointId ? `用例 - ${selectedPointName}` : '测试用例'" :bordered="false">
          <template #extra>
            <a-space>
              <a-button size="mini" type="text" @click="loadCases">刷新</a-button>
              <a-button size="mini" status="success" @click="onExport">导出Excel</a-button>
            </a-space>
          </template>
          <a-list :loading="caseLoading">
            <a-list-item v-for="item in testCases" :key="item.id">
              <a-space direction="vertical" fill>
                <a-space>
                  <a-tag size="small">{{ item.case_no }}</a-tag>
                  <a-tag :color="priorityColorMap[item.priority]" size="small">
                    {{ priorityLabelMap[item.priority] }}
                  </a-tag>
                  <a-tag :color="caseTypeColorMap[item.case_type]" size="small">
                    {{ caseTypeLabelMap[item.case_type] }}
                  </a-tag>
                </a-space>
                <span style="font-weight:500">{{ item.title }}</span>
              </a-space>
            </a-list-item>
          </a-list>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import {
  getAiRequirement,
  getAiSplitByRequirement, postAiSplitBatchConfirm,
  getAiTestPointBySplit, postAiTestPointBatchConfirm,
  getAiTestCaseByTestPoint,
  postAiRequirementGeneratePoints, postAiRequirementGenerateCases
} from '@/api/aicase/index'

const route = useRoute()
const router = useRouter()
const reqId = Number(route.query.id)
const reqName = ref(String(route.query.name || ''))
const requirement = ref<any>(null)

const splits = ref<any[]>([])
const testPoints = ref<any[]>([])
const testCases = ref<any[]>([])
const splitLoading = ref(false)
const pointLoading = ref(false)
const caseLoading = ref(false)
const selectedSplitId = ref<any>(null)
const selectedSplitName = ref('')
const selectedPointId = ref<any>(null)
const selectedPointName = ref('')

const statusLabelMap: Record<number, string> = {
  0: '待分析', 1: '拆分需求中', 2: '待确认拆分',
  3: '生成测试点中', 4: '待确认测试点', 5: '生成用例中', 6: '已完成', 9: '失败'
}
const statusColorMap: Record<number, string> = {
  0: 'gray', 1: 'blue', 2: 'orange', 3: 'blue', 4: 'orange', 5: 'blue', 6: 'green', 9: 'red'
}
const confirmLabelMap: Record<number, string> = { 0: '待确认', 1: '已确认', 2: '已忽略' }
const confirmColorMap: Record<number, string> = { 0: 'gray', 1: 'green', 2: 'red' }
const pointTypeLabelMap: Record<number, string> = { 0: '功能', 1: '边界', 2: '异常', 3: '性能' }
const pointTypeColorMap: Record<number, string> = { 0: 'blue', 1: 'orange', 2: 'red', 3: 'purple' }
const priorityLabelMap: Record<number, string> = { 0: '低', 1: '中', 2: '高', 3: '紧急' }
const priorityColorMap: Record<number, string> = { 0: 'gray', 1: 'blue', 2: 'orange', 3: 'red' }
const caseTypeLabelMap: Record<number, string> = { 0: '正常', 1: '异常', 2: '边界' }
const caseTypeColorMap: Record<number, string> = { 0: 'green', 1: 'red', 2: 'orange' }

const stepCurrent = computed(() => {
  const s = requirement.value?.status
  if (s === undefined || s === null) return 1
  if (s <= 2) return 1
  if (s <= 4) return 2
  return 3
})

function loadRequirement() {
  getAiRequirement({ id: reqId, page: 1, pageSize: 1 }).then((res: any) => {
    if (res.data && res.data.length > 0) requirement.value = res.data[0]
  })
}

function loadSplits() {
  splitLoading.value = true
  getAiSplitByRequirement(reqId).then((res: any) => {
    splits.value = res.data || []
  }).finally(() => { splitLoading.value = false })
}

function onSelectSplit(item: any) {
  selectedSplitId.value = item.id
  selectedSplitName.value = item.name
  selectedPointId.value = null
  testCases.value = []
  loadPoints()
}

function loadPoints() {
  if (!selectedSplitId.value) return
  pointLoading.value = true
  getAiTestPointBySplit(selectedSplitId.value).then((res: any) => {
    testPoints.value = res.data || []
  }).finally(() => { pointLoading.value = false })
}

function onSelectPoint(item: any) {
  selectedPointId.value = item.id
  selectedPointName.value = item.name
  loadCases()
}

function loadCases() {
  if (!selectedPointId.value) return
  caseLoading.value = true
  getAiTestCaseByTestPoint(selectedPointId.value).then((res: any) => {
    testCases.value = res.data || []
  }).finally(() => { caseLoading.value = false })
}

function onConfirmSplit(item: any, status: number) {
  postAiSplitBatchConfirm(reqId, [{ id: item.id, is_confirmed: status }]).then((res: any) => {
    Message.success(res.msg)
    loadSplits()
  })
}

function onConfirmPoint(item: any, status: number) {
  postAiTestPointBatchConfirm(reqId, [{ id: item.id, is_confirmed: status }]).then((res: any) => {
    Message.success(res.msg)
    loadPoints()
  })
}

function onGeneratePoints() {
  postAiRequirementGeneratePoints(reqId).then((res: any) => {
    Message.success(res.msg)
    loadRequirement()
  })
}

function onGenerateCases() {
  postAiRequirementGenerateCases(reqId).then((res: any) => {
    Message.success(res.msg)
    loadRequirement()
  })
}

function onExport() {
  window.open(`/api/ai/test/case/export/excel?requirement_id=${reqId}`, '_blank')
}

onMounted(() => {
  loadRequirement()
  loadSplits()
})
</script>

<style scoped>
.ai-detail-page { background: var(--color-bg-1); min-height: 100%; }
.selected-split { background: var(--color-primary-light-1); border-radius: 4px; }
.selected-point { background: var(--color-success-light-1); border-radius: 4px; }
</style>
