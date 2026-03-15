<template>
  <TableBody>
    <template #header>
      <TableHeader title="AI 生成测试用例" :show-filter="false" />
    </template>
    <template #default>
      <div style="padding: 16px">
        <a-card :bordered="false" style="margin-bottom:16px">
          <template #title><a-space><a-tag color="blue">第一步</a-tag>填写需求信息</a-space></template>
          <a-form :model="formData" layout="vertical">
            <a-row :gutter="16">
              <a-col :span="8"><a-form-item label="项目/产品" required>
                <a-cascader v-model="formData.project_product" :options="projectInfo.projectProduct" placeholder="请选择项目产品" allow-clear allow-search style="width:100%" />
              </a-form-item></a-col>
              <a-col :span="8"><a-form-item label="需求名称" required>
                <a-input v-model="formData.name" placeholder="如：用户登录功能需求" />
              </a-form-item></a-col>
              <a-col :span="8"><a-form-item label="创建人" required>
                <a-select v-model="formData.create_user" :options="userList" :field-names="fieldNames" placeholder="请选择创建人" allow-clear allow-search style="width:100%" />
              </a-form-item></a-col>
            </a-row>
            <a-form-item label="输入方式" required>
              <a-radio-group v-model="formData.input_type" type="button">
                <a-radio :value="0">文本</a-radio><a-radio :value="3">URL链接</a-radio><a-radio :value="1">图片</a-radio><a-radio :value="2">Word文档</a-radio>
              </a-radio-group>
            </a-form-item>
            <a-form-item v-if="formData.input_type === 0" label="需求内容" required>
              <a-textarea v-model="formData.input_content" placeholder="请粘贴需求内容..." :auto-size="{ minRows: 8, maxRows: 20 }" />
            </a-form-item>
            <a-form-item v-else-if="formData.input_type === 3" label="需求文档 URL" required>
              <a-input v-model="formData.input_content" placeholder="请输入可访问的需求文档URL" />
            </a-form-item>
            <a-form-item v-else :label="formData.input_type === 1 ? '上传图片' : '上传 Word'" required>
              <a-upload :limit="1" :custom-request="handleUpload" :accept="formData.input_type === 1 ? 'image/*' : '.doc,.docx'">
                <template #upload-button><a-button><icon-upload /> 点击上传</a-button></template>
              </a-upload>
            </a-form-item>
            <a-form-item><a-button type="primary" :loading="step1Loading" @click="onSubmitStep1">保存并启动AI分析</a-button></a-form-item>
          </a-form>
        </a-card>
        <a-card :bordered="false" style="margin-bottom:16px">
          <template #title><a-space><a-tag color="orange">第二步</a-tag>确认需求拆分<a-tag v-if="currentReqId" :color="statusColorMap[reqStatus]">{{ statusLabelMap[reqStatus] }}</a-tag></a-space></template>
          <template #extra><a-space>
            <a-button size="small" type="text" :disabled="!currentReqId" @click="loadSplits">刷新</a-button>
            <a-button size="small" type="primary" :loading="step2Loading" :disabled="!currentReqId || reqStatus !== 2" @click="onSubmitStep2">确认拆分并生成测试点</a-button>
          </a-space></template>
          <a-spin :loading="splitLoading">
            <a-empty v-if="!currentReqId" description="请先完成第一步" />
            <a-empty v-else-if="splits.length === 0 && !splitLoading" description="暂无拆分结果，请等待AI分析完成后刷新" />
            <a-row v-else :gutter="12">
              <a-col v-for="item in splits" :key="item.id" :span="6" style="margin-bottom:12px">
                <a-card size="small" :bordered="true">
                  <template #title><a-space><a-tag :color="confirmColorMap[item.is_confirmed]" size="small">{{ confirmLabelMap[item.is_confirmed] }}</a-tag><span style="font-size:13px">{{ item.name }}</span></a-space></template>
                  <template #extra><a-space><a-button size="mini" type="text" status="success" @click="onConfirmSplit(item,1)">确认</a-button><a-button size="mini" type="text" status="danger" @click="onConfirmSplit(item,2)">忽略</a-button></a-space></template>
                  <a-typography-text type="secondary" style="font-size:12px">{{ item.description || '暂无描述' }}</a-typography-text>
                </a-card>
              </a-col>
            </a-row>
          </a-spin>
        </a-card>
        <a-card :bordered="false" style="margin-bottom:16px">
          <template #title><a-space><a-tag color="purple">第三步</a-tag>确认测试点</a-space></template>
          <template #extra><a-space>
            <a-button size="small" type="text" :disabled="!currentReqId" @click="loadPoints">刷新</a-button>
            <a-button size="small" type="primary" :loading="step3Loading" :disabled="!currentReqId || reqStatus !== 4" @click="onSubmitStep3">确认测试点并生成用例</a-button>
          </a-space></template>
          <a-spin :loading="pointLoading">
            <a-empty v-if="testPoints.length === 0 && !pointLoading" description="请先完成第二步" />
            <a-row v-else :gutter="12">
              <a-col v-for="item in testPoints" :key="item.id" :span="6" style="margin-bottom:12px">
                <a-card size="small" :bordered="true">
                  <template #title><a-space><a-tag :color="confirmColorMap[item.is_confirmed]" size="small">{{ confirmLabelMap[item.is_confirmed] }}</a-tag><a-tag :color="pointTypeColorMap[item.test_type]" size="small">{{ pointTypeLabelMap[item.test_type] }}</a-tag></a-space></template>
                  <template #extra><a-space><a-button size="mini" type="text" status="success" @click="onConfirmPoint(item,1)">确认</a-button><a-button size="mini" type="text" status="danger" @click="onConfirmPoint(item,2)">忽略</a-button></a-space></template>
                  <span style="font-size:12px">{{ item.name }}</span>
                </a-card>
              </a-col>
            </a-row>
          </a-spin>
        </a-card>
        <a-card :bordered="false">
          <template #title><a-space><a-tag color="green">第四步</a-tag>查看生成用例</a-space></template>
          <template #extra><a-space>
            <a-button size="small" type="text" :disabled="!currentReqId" @click="loadCases">刷新</a-button>
            <a-button size="small" status="success" :disabled="!currentReqId" @click="onExport">导出Excel</a-button>
          </a-space></template>
          <a-spin :loading="caseLoading">
            <a-empty v-if="testCases.length === 0 && !caseLoading" description="请先完成第三步" />
            <a-table v-else :data="testCases" :bordered="false" :pagination="false" size="small">
              <template #columns>
                <a-table-column title="编号" data-index="case_no" :width="90" />
                <a-table-column title="标题" data-index="title" :ellipsis="true" :tooltip="true" />
                <a-table-column title="优先级" :width="80"><template #cell="{ record }"><a-tag :color="priorityColorMap[record.priority]" size="small">{{ priorityLabelMap[record.priority] }}</a-tag></template></a-table-column>
                <a-table-column title="类型" :width="80"><template #cell="{ record }"><a-tag :color="caseTypeColorMap[record.case_type]" size="small">{{ caseTypeLabelMap[record.case_type] }}</a-tag></template></a-table-column>
                <a-table-column title="所属模块" data-index="module_name" :width="140" :ellipsis="true" />
              </template>
            </a-table>
          </a-spin>
        </a-card>
      </div>
    </template>
  </TableBody>
</template>

<script lang="ts" setup>
import { onMounted, reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useProject } from '@/store/modules/get-project'
import { fieldNames } from '@/setting'
import {
  postAiRequirement, postAiRequirementAnalyze, getAiRequirement,
  getAiSplitByRequirement, postAiSplitBatchConfirm, postAiRequirementGeneratePoints,
  getAiTestPointByRequirement, postAiTestPointBatchConfirm,
  postAiRequirementGenerateCases, getAiTestCaseByRequirement,
} from '@/api/aicase/index'
import { getUserName } from '@/api/user/user'

const projectInfo = useProject()
const userList = ref<any[]>([])
const currentReqId = ref<any>(null)
const reqStatus = ref<number>(0)
const step1Loading = ref(false)
const step2Loading = ref(false)
const step3Loading = ref(false)
const splitLoading = ref(false)
const pointLoading = ref(false)
const caseLoading = ref(false)
const splits = ref<any[]>([])
const testPoints = ref<any[]>([])
const testCases = ref<any[]>([])
const statusLabelMap: Record<number,string> = {
  0:'待分析',1:'拆分需求中',2:'待确认拆分',3:'生成测试点中',4:'待确认测试点',5:'生成用例中',6:'已完成',9:'失败'
}
const statusColorMap: Record<number,string> = {0:'gray',1:'blue',2:'orange',3:'blue',4:'orange',5:'blue',6:'green',9:'red'}
const confirmLabelMap: Record<number,string> = {0:'待确认',1:'已确认',2:'已忽略'}
const confirmColorMap: Record<number,string> = {0:'gray',1:'green',2:'red'}
const pointTypeLabelMap: Record<number,string> = {0:'功能',1:'边界',2:'异常',3:'性能'}
const pointTypeColorMap: Record<number,string> = {0:'blue',1:'orange',2:'red',3:'purple'}
const priorityLabelMap: Record<number,string> = {0:'低',1:'中',2:'高',3:'紧急'}
const priorityColorMap: Record<number,string> = {0:'gray',1:'blue',2:'orange',3:'red'}
const caseTypeLabelMap: Record<number,string> = {0:'正常',1:'异常',2:'边界'}
const caseTypeColorMap: Record<number,string> = {0:'green',1:'red',2:'orange'}
const formData = reactive<any>({project_product:null,name:'',input_type:0,input_content:'',create_user:null})
function loadReqStatus() {
  if (!currentReqId.value) return
  getAiRequirement({id:currentReqId.value,page:1,pageSize:1}).then((res:any) => {
    if (res.data && res.data.length > 0) reqStatus.value = res.data[0].status
  })
}
function loadSplits() {

  if (!currentReqId.value) { console.warn('[loadSplits] currentReqId is null'); return }

  console.log('[loadSplits] req_id=', currentReqId.value)

  splitLoading.value=true; loadReqStatus()

  getAiSplitByRequirement(currentReqId.value).then((res:any) => {

    console.log('[loadSplits] response=', res)

    splits.value=res.data||[]

  }).catch((e:any) => console.error('[loadSplits] error=', e)).finally(()=>{splitLoading.value=false})

}
function loadPoints() {
  if (!currentReqId.value) return
  pointLoading.value=true; loadReqStatus()
  getAiTestPointByRequirement(currentReqId.value).then((res:any) => { testPoints.value=res.data||[] }).finally(()=>{pointLoading.value=false})
}
function loadCases() {
  if (!currentReqId.value) return
  caseLoading.value=true
  getAiTestCaseByRequirement(currentReqId.value).then((res:any) => { testCases.value=res.data||[] }).finally(()=>{caseLoading.value=false})
}
async function onSubmitStep1() {
  if (!formData.name) { Message.error('请填写需求名称'); return }
  if (!formData.create_user) { Message.error('请选择创建人'); return }
  if (formData.input_type!==1&&formData.input_type!==2&&!formData.input_content) {
    Message.error('请填写需求内容或URL'); return
  }
  step1Loading.value=true
  try {
    const payload={...formData}
    if (Array.isArray(payload.project_product)) payload.project_product=payload.project_product[payload.project_product.length-1]
    const res:any=await postAiRequirement(payload)
    currentReqId.value=res.data?.id
    reqStatus.value=0; splits.value=[]; testPoints.value=[]; testCases.value=[]
    await postAiRequirementAnalyze(currentReqId.value)
    Message.success('需求已保存，AI分析已启动，请稍后点击第二步刷新查看结果')
    Object.assign(formData,{project_product:null,name:'',input_type:0,input_content:'',create_user:null})
  } catch(e){console.error(e)} finally{step1Loading.value=false}
}
function onConfirmSplit(item:any,status:number) {
  postAiSplitBatchConfirm(currentReqId.value,[{id:item.id,is_confirmed:status}]).then((res:any) =>{Message.success(res.msg);loadSplits()})
}
function onSubmitStep2() {
  step2Loading.value=true
  postAiRequirementGeneratePoints(currentReqId.value).then((res:any)=>{Message.success(res.msg);reqStatus.value=3}).catch(console.log).finally(()=>{step2Loading.value=false})
}
function onConfirmPoint(item:any,status:number) {
  postAiTestPointBatchConfirm(currentReqId.value,[{id:item.id,is_confirmed:status}]).then((res:any)=>{Message.success(res.msg);loadPoints()})
}
function onSubmitStep3() {
  step3Loading.value=true
  postAiRequirementGenerateCases(currentReqId.value).then((res:any)=>{Message.success(res.msg);reqStatus.value=5}).catch(console.log).finally(()=>{step3Loading.value=false})
}
function onExport() { window.open(`/api/ai/test/case/export/excel?requirement_id=${currentReqId.value}`,'_blank') }
function handleUpload() {}
onMounted(()=> {
  projectInfo.projectProductName()
  getUserName().then((res:any)=>{userList.value=res.data}).catch(console.log)
})
</script>
