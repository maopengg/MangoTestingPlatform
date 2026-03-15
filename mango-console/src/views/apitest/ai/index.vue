<template>
  <TableBody>
    <template #header>
      <TableHeader :show-filter="false" title="AI 写用例" />
    </template>
    <template #default>
      <div class="ai-page">

        <!-- ① 输入区 -->
        <a-card title="① 粘贴接口信息" :bordered="false" class="ai-card">
          <div class="two-col">
            <div class="col-left">
              <a-form :model="importForm" layout="vertical">
                <a-form-item label="项目 / 产品" required>
                  <a-cascader v-model="importForm.project_product" :options="projectInfo.projectProduct" placeholder="请选择项目产品" allow-clear allow-search @change="onProductChange" />
                </a-form-item>
                <a-form-item label="模块" required>
                  <a-select v-model="importForm.module_id" :field-names="fieldNames" :options="productModule.data" placeholder="请选择模块" allow-clear allow-search />
                </a-form-item>
                <a-form-item label="接口名称（可选，AI 会自动推断）">
                  <a-input v-model="importForm.name" placeholder="留空则由 AI 从文本中提取" />
                </a-form-item>
                <a-form-item>
                  <a-button type="primary" :loading="importing" long @click="onImport">AI 解析并导入接口</a-button>
                </a-form-item>
              </a-form>
            </div>
            <div class="col-right">
              <a-textarea v-model="importForm.text" :auto-size="{minRows:12,maxRows:20}" placeholder="支持：cURL 命令 / 接口文档 / Postman JSON / HAR / 自然语言描述" allow-clear />
            </div>
          </div>
        </a-card>

        <!-- ② 接口信息 -->
        <a-card :bordered="false" class="ai-card" :class="{disabled: !apiInfo.api_info_id}">
          <template #title>
            <a-space>
              <span>② 接口信息</span>
              <a-tag v-if="apiInfo.api_info_id" color="green" size="small">ID: {{ apiInfo.api_info_id }}</a-tag>
              <a-tag v-else color="gray" size="small">待解析</a-tag>
            </a-space>
          </template>
          <template #extra>
            <a-space v-if="apiInfo.api_info_id">
              <a-button v-if="!editingApi" size="small" @click="startEditApi">编辑</a-button>
              <a-button v-else size="small" type="primary" :loading="savingApi" @click="saveApi">保存</a-button>
              <a-button v-if="editingApi" size="small" @click="cancelEditApi">取消</a-button>
            </a-space>
          </template>
          <div v-if="!apiInfo.api_info_id" class="placeholder-tip">完成第①步后，接口信息将展示在此处</div>
          <div v-else class="two-col">
            <div class="col-left">
              <a-form :model="apiForm" layout="vertical">
                <a-form-item label="接口名称"><a-input v-model="apiForm.name" :disabled="!editingApi" /></a-form-item>
                <a-form-item label="URL"><a-input v-model="apiForm.url" :disabled="!editingApi" /></a-form-item>
                <a-form-item label="Method">
                  <a-select v-if="editingApi" v-model="apiForm.method" :field-names="fieldNames" :options="enumStore.method" />
                  <a-tag v-else :color="enumStore.colors?.[apiForm.method]">{{ enumStore.method?.[apiForm.method]?.title || apiForm.method }}</a-tag>
                </a-form-item>
              </a-form>
            </div>
            <div class="col-right">
              <a-form :model="apiForm" layout="vertical">
                <a-form-item label="Query Params"><a-textarea v-model="apiForm.params" :disabled="!editingApi" :auto-size="{minRows:3,maxRows:6}" /></a-form-item>
                <a-form-item label="JSON Body"><a-textarea v-model="apiForm.json" :disabled="!editingApi" :auto-size="{minRows:3,maxRows:8}" /></a-form-item>
                <a-form-item label="Form Data"><a-textarea v-model="apiForm.data" :disabled="!editingApi" :auto-size="{minRows:2,maxRows:6}" /></a-form-item>
              </a-form>
            </div>
          </div>
          <div v-if="apiInfo.api_info_id" class="run-area">
            <div class="run-bar">
              <span class="run-label">当前环境：</span>
              <a-tag v-if="userStore.selected_environment" color="arcoblue">{{ envOptions.find(e => e.value === userStore.selected_environment)?.label || userStore.selected_environment }}</a-tag>
              <span v-else class="env-tip">请先在顶部导航选择测试环境</span>
              <a-button type="outline" :loading="running" :disabled="!userStore.selected_environment" @click="onRunTest">▶ 执行测试</a-button>
            </div>
            <div v-if="testResult" class="result-block">
              <div class="result-row">
                <a-tag color="orange">响应码</a-tag><span>{{ testResult.code }}</span>
                <a-tag color="orange">响应时间</a-tag><span>{{ testResult.time }}</span>
              </div>
              <a-tag color="orange">响应体</a-tag>
              <pre class="code-pre">{{ strJson(testResult.json||testResult.text) }}</pre>
            </div>
          </div>
        </a-card>

        <!-- ③ 前置 / AI 生成用例 / 后置配置 -->
        <a-card title="③ 前置 / AI 生成用例 / 后置" :bordered="false" class="ai-card" :class="{disabled: !apiInfo.api_info_id}">
          <div v-if="!apiInfo.api_info_id" class="placeholder-tip">完成第①步后可配置前置、生成用例、后置</div>
          <div v-else>
            <a-tabs :active-key="prePostTab" @tab-click="(k) => (prePostTab = k)">
              <!-- 前置 Tab -->
              <a-tab-pane key="front" title="用例前置">
                <a-tabs position="left" :active-key="frontSubTab" @tab-click="(k) => (frontSubTab = k)">
                  <a-tab-pane key="front_custom" title="自定义参数">
                    <div class="kv-section">
                      <div class="kv-toolbar"><a-button size="small" type="primary" @click="caseConfig.front_custom.push({key:'',value:''})">+ 增加</a-button></div>
                      <div v-if="!caseConfig.front_custom.length" class="placeholder-tip">暂无自定义参数</div>
                      <div v-for="(item, idx) in caseConfig.front_custom" :key="idx" class="kv-row">
                        <a-input v-model="item.key" placeholder="缓存 key" size="small" />
                        <a-input v-model="item.value" placeholder="value" size="small" />
                        <a-button size="mini" status="danger" type="text" @click="caseConfig.front_custom.splice(idx,1)">删除</a-button>
                      </div>
                    </div>
                  </a-tab-pane>
                  <a-tab-pane key="front_sql" title="SQL 前置">
                    <div class="kv-section">
                      <div class="kv-toolbar"><a-button size="small" type="primary" @click="caseConfig.front_sql.push({key:'',value:''})">+ 增加</a-button></div>
                      <div v-if="!caseConfig.front_sql.length" class="placeholder-tip">暂无前置 SQL</div>
                      <div v-for="(item, idx) in caseConfig.front_sql" :key="idx" class="kv-row">
                        <a-input v-model="item.key" placeholder="缓存 key" size="small" style="flex:0 0 140px" />
                        <a-textarea v-model="item.value" placeholder="SQL 语句" size="small" :auto-size="{minRows:1,maxRows:3}" style="flex:1" />
                        <a-button size="mini" status="danger" type="text" @click="caseConfig.front_sql.splice(idx,1)">删除</a-button>
                      </div>
                    </div>
                  </a-tab-pane>
                  <a-tab-pane key="front_headers" title="默认请求头">
                    <a-space direction="vertical">
                      <TipMessage message="此处请求头会应用到所有接口中" />
                      <a-checkbox-group
                        v-for="item of headersList"
                        :key="item.id"
                        v-model="caseConfig.front_headers"
                        direction="vertical"
                      >
                        <a-checkbox :value="item.id">
                          {{ item.key + ': ' + item.value }}
                        </a-checkbox>
                      </a-checkbox-group>
                      <div v-if="!headersList.length" class="placeholder-tip">暂无可用请求头，请先在接口管理中配置</div>
                    </a-space>
                  </a-tab-pane>
                </a-tabs>
              </a-tab-pane>
              <!-- AI 生成用例 Tab -->
              <a-tab-pane key="ai_cases" title="AI 生成用例">
                <div class="action-bar" style="margin-bottom:16px">
                  <a-select v-model="casePeopleId" :options="userList" :field-names="{value:'key',label:'title'}" placeholder="选择用例责任人" style="width:180px" allow-search />
                  <a-button type="outline" :loading="previewing" :disabled="!casePeopleId" @click="onPreviewCase">AI 推断用例</a-button>
                </div>
                <div v-if="casePreview.cases.length">
                  <a-table :data="casePreview.cases" :pagination="false" :bordered="{cell:true}" size="small">
                    <template #columns>
                      <a-table-column title="#" :width="50"><template #cell="{ rowIndex }">{{ rowIndex + 1 }}</template></a-table-column>
                      <a-table-column title="用例名称" data-index="case_name">
                        <template #cell="{ rowIndex }"><a-input v-model="casePreview.cases[rowIndex].case_name" size="small" /></template>
                      </a-table-column>
                      <a-table-column title="步骤名称" data-index="step_name">
                        <template #cell="{ rowIndex }"><a-input v-model="casePreview.cases[rowIndex].step_name" size="small" /></template>
                      </a-table-column>
                      <a-table-column title="操作" :width="80">
                        <template #cell="{ rowIndex }"><a-button type="text" status="danger" size="mini" @click="removeCase(rowIndex)">删除</a-button></template>
                      </a-table-column>
                    </template>
                  </a-table>
                  <a-button class="add-btn" size="small" @click="addCase">+ 新增用例</a-button>
                </div>
                <div v-else class="placeholder-tip">点击『AI 推断用例』生成用例列表</div>
              </a-tab-pane>
              <!-- 后置 Tab -->
              <a-tab-pane key="posterior" title="用例后置">
                <a-tabs position="left" :active-key="posteriorSubTab" @tab-click="(k) => (posteriorSubTab = k)">
                  <a-tab-pane key="posterior_sql" title="SQL 后置">
                    <div class="kv-section">
                      <div class="kv-toolbar"><a-button size="small" type="primary" @click="caseConfig.posterior_sql.push({key:'',value:''})">+ 增加</a-button></div>
                      <div v-if="!caseConfig.posterior_sql.length" class="placeholder-tip">暂无后置 SQL</div>
                      <div v-for="(item, idx) in caseConfig.posterior_sql" :key="idx" class="kv-row">
                        <a-input v-model="item.key" placeholder="key（可为空）" size="small" style="flex:0 0 140px" />
                        <a-textarea v-model="item.value" placeholder="SQL 语句" size="small" :auto-size="{minRows:1,maxRows:3}" style="flex:1" />
                        <a-button size="mini" status="danger" type="text" @click="caseConfig.posterior_sql.splice(idx,1)">删除</a-button>
                      </div>
                    </div>
                  </a-tab-pane>
                </a-tabs>
              </a-tab-pane>
            </a-tabs>
          </div>
        </a-card>


        <!-- ⑥ 确认写入用例 -->
        <a-card title="⑥ 确认写入用例" :bordered="false" class="ai-card" :class="{disabled: !apiInfo.api_info_id}">
          <div v-if="!apiInfo.api_info_id" class="placeholder-tip">完成前面步骤后可写入</div>
          <div v-else-if="doneResult.created.length">
            <a-result status="success" :title="`成功创建 ${doneResult.created.length} 条用例！`">
              <template #subtitle>
                <span v-for="item in doneResult.created" :key="item.case_id" style="display:block">用例 ID：{{ item.case_id }} — {{ item.case_name }}</span>
              </template>
              <template #extra>
                <a-space>
                  <a-button type="primary" @click="goToCase">查看测试用例</a-button>
                  <a-button @click="resetAll">继续创建</a-button>
                </a-space>
              </template>
            </a-result>
          </div>
          <div v-else>
            <p class="confirm-tip">确认以上用例配置无误后，点击下方按鈕将所有用例写入数据库。前置/后置配置将同步写入每条用例。</p>
            <a-button type="primary" size="large" :loading="confirming" :disabled="!casePreview.cases.length" @click="onConfirmCase">确认写入 {{ casePreview.cases.length }} 条用例</a-button>
          </div>
        </a-card>

      </div>
    </template>
  </TableBody>
</template>
<script lang="ts" setup>
  import { onMounted, reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { useRouter } from 'vue-router'
  import { useProject } from '@/store/modules/get-project'
  import { useProductModule } from '@/store/modules/project_module'
  import { useEnum } from '@/store/modules/get-enum'
  import { fieldNames } from '@/setting'
  import { strJson } from '@/utils/tools'
  import { getUserName } from '@/api/user/user'
  import useUserStore from '@/store/modules/user'
  import {
    getApiInfoRun,
    postAiConfirmCase,
    postAiImport,
    postAiPreviewCase,
  } from '@/api/apitest/ai'
  import { putApiInfo } from '@/api/apitest/info'
  import { getApiHeaders } from '@/api/apitest/headers'
  import { makeCasePreview, makeImportForm } from './config'
  import TipMessage from '@/components/TipMessage.vue'

  const router = useRouter()
  const projectInfo = useProject()
  const productModule = useProductModule()
  const enumStore = useEnum()
  const userStore = useUserStore()

  const importForm = makeImportForm()
  const importing = ref(false)
  const apiInfo = reactive<any>({ api_info_id: null })
  const apiForm = reactive<any>({ name: '', url: '', method: '', params: '', json: '', data: '' })
  const editingApi = ref(false)
  const savingApi = ref(false)
  const running = ref(false)
  const testResult = ref<any>(null)
  const envOptions = ref<any[]>([])
  const casePeopleId = ref<any>(null)
  const previewing = ref(false)
  const userList = ref<any[]>([])
  const casePreview = makeCasePreview()
  const confirming = ref(false)
  const doneResult = reactive<{
    created: { case_id: number; detailed_id: number; case_name: string }[]
  }>({ created: [] })
  const headersList = ref<any[]>([])

  function loadHeaders(project_product: any) {
    const id = Array.isArray(project_product)
      ? project_product[project_product.length - 1]
      : project_product
    if (!id) {
      headersList.value = []
      return
    }
    getApiHeaders({ page: 1, pageSize: 10000, project_product_id: id })
      .then((res: any) => {
        headersList.value = res.data || []
      })
      .catch(() => {
        headersList.value = []
      })
  }

  function onProductChange(val: any) {
    productModule.getProjectModule(val)
    importForm.module_id = ''
    loadHeaders(val)
  }

  async function onImport() {
    if (!importForm.project_product) return Message.error('请选择项目产品')
    if (!importForm.module_id) return Message.error('请选择模块')
    if (!importForm.text.trim()) return Message.error('请粘贴接口信息')
    importing.value = true
    try {
      const res = await postAiImport({
        text: importForm.text,
        name: importForm.name || undefined,
        project_product_id: Array.isArray(importForm.project_product) ? importForm.project_product[importForm.project_product.length - 1] : importForm.project_product,
        module_id: importForm.module_id,
      })
      Object.assign(apiInfo, res.data)
      Object.assign(apiForm, {
        name: res.data.name,
        url: res.data.url,
        method: res.data.method,
        params: res.data.params || '',
        json: res.data.json || '',
        data: res.data.data || '',
      })
      testResult.value = null
      editingApi.value = false
      Message.success('接口解析并导入成功')
    } catch (e: any) {
      Message.error(e?.msg || '操作失败')
    } finally {
      importing.value = false
    }
  }

  function startEditApi() {
    editingApi.value = true
  }

  function cancelEditApi() {
    editingApi.value = false
  }

  async function saveApi() {
    savingApi.value = true
    try {
      await putApiInfo({
        id: apiInfo.api_info_id,
        name: apiForm.name,
        url: apiForm.url,
        method: apiForm.method,
        params: apiForm.params || null,
        json: apiForm.json || null,
        data: apiForm.data || null,
      })
      Object.assign(apiInfo, apiForm)
      editingApi.value = false
      Message.success('接口信息已保存')
    } catch (e: any) {
      Message.error(e?.msg || '操作失败')
    } finally {
      savingApi.value = false
    }
  }

  async function onRunTest() {
    if (!userStore.selected_environment) return Message.error('请先在顶部导航选择测试环境')
    running.value = true
    testResult.value = null
    try {
      const res = await getApiInfoRun(apiInfo.api_info_id, userStore.selected_environment)
      testResult.value = res.data
      Message.success('执行完成')
    } catch (e: any) {
      Message.error(e?.msg || '操作失败')
    } finally {
      running.value = false
    }
  }

  async function onPreviewCase() {
    if (!casePeopleId.value) return Message.error('请选择用例责任人')
    previewing.value = true
    try {
      const res = await postAiPreviewCase({
        api_info_id: apiInfo.api_info_id,
        case_people_id: casePeopleId.value,
      })
      casePreview.api_info_id = res.data.api_info_id
      casePreview.case_people_id = res.data.case_people_id
      casePreview.cases = res.data.cases || []
      Message.success(`已生成 ${casePreview.cases.length} 条用例配置，可在下方修改后写入`)
    } catch (e: any) {
      Message.error(e?.msg || 'AI ????')
    } finally {
      previewing.value = false
    }
  }

  const prePostTab = ref('front')
  const frontSubTab = ref('front_custom')
  const posteriorSubTab = ref('posterior_sql')
  const caseConfig = reactive({
    front_custom: [] as { key: string; value: string }[],
    front_sql: [] as { key: string; value: string }[],
    front_headers: [] as number[],
    posterior_sql: [] as { key: string; value: string }[],
  })

  function removeCase(idx: number) {
    casePreview.cases.splice(idx, 1)
  }

  function addCase() {
    casePreview.cases.push({ case_name: '', step_name: '' })
  }

  async function onConfirmCase() {
    confirming.value = true
    try {
      const res = await postAiConfirmCase({
        api_info_id: casePreview.api_info_id,
        case_people_id: casePreview.case_people_id,
        cases: casePreview.cases,
        front_custom: caseConfig.front_custom,
        front_sql: caseConfig.front_sql,
        posterior_sql: caseConfig.posterior_sql,
      })
      doneResult.created = res.data.created || []
      Message.success('接口信息已保存')
    } catch (e: any) {
      Message.error(e?.msg || '操作失败')
    } finally {
      confirming.value = false
    }
  }

  function goToCase() {
    router.push({ path: '/apitest/case/index' })
  }

  function resetAll() {
    importForm.project_product = ''
    importForm.module_id = ''
    importForm.name = ''
    importForm.text = ''
    Object.keys(apiInfo).forEach((k) => delete apiInfo[k])
    apiInfo.api_info_id = null
    Object.keys(apiForm).forEach((k) => delete apiForm[k])
    Object.assign(apiForm, { name: '', url: '', method: '', params: '', json: '', data: '' })
    testResult.value = null
    casePeopleId.value = null
    Object.assign(casePreview, makeCasePreview())
    doneResult.created = []
    editingApi.value = false
    caseConfig.front_custom = []
    caseConfig.front_sql = []
    caseConfig.front_headers = []
    caseConfig.posterior_sql = []
    headersList.value = []
  }

  onMounted(async () => {
    productModule.getProjectModule(null)
    try {
      const res = await getUserName()
      userList.value = res.data || []
    } catch (_) {}
    envOptions.value = (enumStore.test_object || []).map((item: any) => ({
      value: item.key,
      label: item.title,
    }))
  })
</script>
<style lang="less" scoped>
  .ai-page {
    padding: 16px 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .ai-card {
    border-radius: 8px;
    border: 1px solid var(--color-border-1);

    :deep(.arco-card-header) {
      border-bottom: 1px solid var(--color-border-1);
      padding: 12px 16px;
      font-size: 14px;
      font-weight: 600;
    }

    :deep(.arco-card-body) {
      padding: 16px;
    }

    &.disabled {
      opacity: 0.55;
      pointer-events: none;
    }
  }

  .two-col {
    display: flex;
    gap: 16px;
    align-items: flex-start;

    .col-left,
    .col-right {
      flex: 1;
      min-width: 0;
    }
  }

  .placeholder-tip {
    color: var(--color-text-3);
    font-size: 13px;
    padding: 12px 0;
  }

  .run-bar {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
    padding: 10px 14px;
    background: var(--color-fill-1);
    border-radius: 6px;
  }

  .run-label {
    font-weight: 600;
    white-space: nowrap;
  }

  .env-tip {
    color: var(--color-text-3);
    font-size: 13px;
  }

  .result-block {
    margin-top: 12px;
    padding: 12px 14px;
    background: var(--color-fill-2);
    border: 1px solid var(--color-border-1);
    border-radius: 6px;
  }

  .result-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }

  .code-pre {
    background: var(--color-fill-2);
    border: 1px solid var(--color-border-1);
    border-radius: 4px;
    padding: 10px 14px;
    font-size: 12px;
    font-family: Consolas, Monaco, monospace;
    line-height: 1.7;
    max-height: 240px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-all;
    margin: 8px 0 0;
    color: var(--color-text-1);
  }

  .action-bar {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }

  .add-btn {
    margin-top: 8px;
    width: 100%;
    border-style: dashed !important;
  }

  .run-area {
    margin-top: 16px;
    border-top: 1px solid var(--color-border-1);
    padding-top: 12px;
  }

  .confirm-tip {
    color: var(--color-text-2);
    margin-bottom: 12px;
    font-size: 13px;
  }

  :deep(.arco-form-item) {
    margin-bottom: 14px;
  }
</style>
