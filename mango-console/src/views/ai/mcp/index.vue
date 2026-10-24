<template>
  <TableBody content-flush>
    <template #header><TableHeader title="AI / MCP服务" @search="loadServers" /></template>
    <template #default>
      <TableTabs>
        <template #extra>
          <a-space>
            <div>
              <a-button v-permission="'ai.mcp:create'"
                size="small"
                type="primary"
                @click="openServer()"
                data-testid="qa-views-ai-mcp-button-新增-mcp"
                >新增 MCP</a-button
              >
            </div>
            <div>
              <a-button
                size="small"
                :loading="refreshLoading"
                @click="refreshStatus"
                data-testid="qa-views-ai-mcp-button-刷新状态"
                >刷新状态</a-button
              >
            </div>
          </a-space>
        </template>
      </TableTabs>
      <a-table
        :bordered="false"
        :columns="serverColumns"
        :data="servers"
        :loading="loading"
        :pagination="false"
        :row-key="'id'"
        :scroll="{ x: serverTableScrollX }"
      >
        <template #columns>
          <a-table-column v-for="item of serverColumns" :key="item.key" v-bind="item">
            <template v-if="item.key === 'status'" #cell="{ record }">
              <a-switch v-permission="'ai.mcp:status'"
                size="small"
                :before-change="(newValue) => onModifyStatus(newValue, record)"
                :default-checked="record.status === 1"
              />
            </template>
            <template v-else-if="item.key === 'auth_type'" #cell="{ record }">
              <a-tag :color="enumColor(enumStore.ai_mcp_auth_type, record.auth_type)" size="small">
                {{ enumTitle(enumStore.ai_mcp_auth_type, record.auth_type) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'type'" #cell="{ record }">
              <a-tag :color="enumColor(enumStore.ai_mcp_use_type, record.type)" size="small">
                {{ enumTitle(enumStore.ai_mcp_use_type, record.type) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ formatProjectProductPath(record.project_product) }}
            </template>
            <template v-else-if="item.key === 'module'" #cell="{ record }">
              {{ record.module?.name || '-' }}
            </template>
            <template v-else-if="item.key === 'is_builtin'" #cell="{ record }">
              <a-switch v-permission="'ai.mcp:status'"
                size="small"
                :before-change="(newValue) => onModifyBuiltin(newValue, record)"
                :default-checked="!!record.is_builtin"
              />
            </template>
            <template v-else-if="item.key === 'is_connected'" #cell="{ record }">
              <a-tag v-if="record.status !== 1" size="small" color="gray">已停用</a-tag>
              <a-tooltip
                v-else-if="!record.is_connected && record.last_error"
                :content="record.last_error"
              >
                <a-tag size="small" color="gray">未连接</a-tag>
              </a-tooltip>
              <a-tag v-else-if="record.is_connected" size="small" color="green">已连接</a-tag>
              <a-tag v-else size="small" color="gold">未检测</a-tag>
            </template>
            <template v-else-if="item.key === 'prompt'" #cell="{ record }">
              {{ record.prompt || '-' }}
            </template>
            <template v-else-if="item.key === 'update_user'" #cell="{ record }">
              {{ record.update_user?.name || record.update_user?.username || '-' }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { permission: 'ai.mcp:edit', label: '编辑', onClick: () => openServer(record) },
                  { permission: 'ai.mcp:detail', label: '工具', onClick: () => openTools(record) },
                  { permission: 'ai.mcp:delete', label: '删除', danger: true, onClick: () => deleteServer(record) },
                ]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>
    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>
  <a-modal
    v-model:visible="visible"
    title="MCP服务"
    width="640px"
    :ok-loading="saving"
    @ok="saveServer"
  >
    <a-form :model="form" layout="vertical">
      <a-form-item label="名称" required><a-input v-model="form.name" /></a-form-item>
      <a-form-item label="服务地址" required><a-input v-model="form.server_url" /></a-form-item>
      <a-form-item label="使用范围">
        <a-select
          v-model="form.type"
          :options="enumStore.ai_mcp_use_type"
          :field-names="fieldNames"
        />
      </a-form-item>
      <a-form-item label="项目/产品">
        <ProjectProductSelect
          v-model="form.project_product"
          allow-clear
          @change="form.module = undefined"
        />
      </a-form-item>
      <a-form-item label="模块">
        <ProductModuleSelect
          v-model="form.module"
          :project-product-id="form.project_product"
          allow-clear
        />
      </a-form-item>
      <a-form-item label="MCP使用提示词" required>
        <a-textarea
          v-model="form.prompt"
          placeholder="说明这个 MCP 适合做什么、什么时候应该使用、不要用于什么场景。生成自动化时会发送给 AI。"
          :auto-size="{ minRows: 4, maxRows: 8 }"
          data-testid="qa-views-ai-mcp-textarea-说明这个-mcp-适合做什么-什么时候应该使用-不要用于什么场景-生成自动化时会发送给-ai"
        />
      </a-form-item>
      <a-form-item label="Transport">
        <a-select
          v-model="form.transport_type"
          :options="enumStore.ai_mcp_transport_type"
          :field-names="fieldNames"
        />
      </a-form-item>
      <a-form-item label="鉴权方式">
        <a-select
          v-model="form.auth_type"
          :options="enumStore.ai_mcp_auth_type"
          :field-names="fieldNames"
        />
      </a-form-item>
      <a-form-item v-if="form.auth_type === MCP_AUTH_BEARER" label="Token" required>
        <a-input-password
          v-model="form.auth_config.token"
          placeholder="输入 token，系统请求时会自动添加 Bearer 前缀"
          data-testid="qa-views-ai-mcp-input-password-输入-token-系统请求时会自动添加-bearer-前缀"
        />
      </a-form-item>
      <template v-if="form.auth_type === MCP_AUTH_API_KEY">
        <a-form-item label="Header 名称" required>
          <a-input
            v-model="form.auth_config.header_name"
            placeholder="例如 Authorization 或 X-API-Key"
            data-testid="qa-views-ai-mcp-input-例如-authorization-或-x-api-key"
          />
        </a-form-item>
        <a-form-item label="Header 前缀">
          <a-input
            v-model="form.auth_config.prefix"
            placeholder="例如 Bearer，可留空"
            data-testid="qa-views-ai-mcp-input-例如-bearer-可留空"
          />
        </a-form-item>
        <a-form-item label="API Key" required>
          <a-input-password v-model="form.auth_config.api_key" />
        </a-form-item>
      </template>
    </a-form>
  </a-modal>
  <a-drawer
    v-model:visible="toolVisible"
    :title="`${selectedServer?.name || ''} / 工具列表`"
    width="72%"
  >
    <template #title>
      <div class="mango-ai-mcp-tool-title">
        <span>{{ selectedServer?.name || '' }} / 工具列表</span>
        <a-button v-permission="'ai.mcp:edit'"
          size="small"
          type="primary"
          :loading="selectedServer ? actionLoading === `sync-${selectedServer.id}` : false"
          :disabled="!selectedServer || selectedServer.status !== 1"
          @click="syncSelectedTools"
          data-testid="qa-views-ai-mcp-button-同步工具"
        >
          同步工具
        </a-button>
      </div>
    </template>
    <div class="mango-ai-mcp-tool-filter">
      <a-radio-group v-model="toolCategory" type="button" size="small">
        <a-radio value="all" data-testid="qa-views-ai-mcp-radio-全部"
          >全部 {{ tools.length }}</a-radio
        >
        <a-radio v-for="item in toolCategories" :key="item.key" :value="item.key">
          {{ item.title }} {{ item.count }}
        </a-radio>
      </a-radio-group>
      <a-select
        v-model="syncTestEnv"
        :options="enumStore.environment_type"
        :field-names="fieldNames"
        allow-clear
        placeholder="同步环境"
        size="small"
        class="mango-ai-mcp-sync-env"
        data-testid="qa-views-ai-mcp-select-同步环境"
      />
    </div>
    <a-table
      :bordered="false"
      :columns="toolColumns"
      :data="filteredTools"
      :loading="toolLoading"
      :pagination="false"
      :row-key="'id'"
      :scroll="{ x: toolTableScrollX }"
    >
      <template #columns>
        <a-table-column v-for="item of toolColumns" :key="item.key" v-bind="item">
          <template v-if="item.key === 'category_title'" #cell="{ record }">
            <a-tag size="small">{{ record.category_title || '其他' }}</a-tag>
          </template>
          <template v-else-if="item.key === 'risk_level'" #cell="{ record }">
            <a-tag
              :color="enumColor(enumStore.ai_mcp_tool_risk_level, record.risk_level)"
              size="small"
            >
              {{ enumTitle(enumStore.ai_mcp_tool_risk_level, record.risk_level) }}
            </a-tag>
          </template>
          <template v-else-if="item.key === 'enabled'" #cell="{ record }">
            <a-tag size="small" :color="statusColor(record.enabled ? 1 : 0)">
              {{ record.enabled ? '启用' : '停用' }}
            </a-tag>
          </template>
          <template v-else-if="item.key === 'require_confirm'" #cell="{ record }">
            <a-tag size="small" :color="record.require_confirm ? 'orange' : 'gray'">
              {{ record.require_confirm ? '需确认' : '无需确认' }}
            </a-tag>
          </template>
          <template v-else-if="item.key === 'type'" #cell="{ record }">
            <a-tag :color="enumColor(enumStore.ai_mcp_use_type, record.type)" size="small">
              {{ enumTitle(enumStore.ai_mcp_use_type, record.type) }}
            </a-tag>
          </template>
          <template v-else-if="item.key === 'actions'" #cell="{ record }">
            <MangoTableActions
              :actions="[
                {
                  label: record.api_info_binding ? '已导入' : '导入API',
                  loading: actionLoading === `import-${record.id}`,
                  disabled: !!record.api_info_binding || record.tool_type !== 'tool',
                  onClick: () => importToolToApi(record),
                },
              ]"
            />
          </template>
        </a-table-column>
      </template>
    </a-table>
  </a-drawer>
</template>

<script setup lang="ts">
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, onMounted, reactive, ref } from 'vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { usePagination } from '@/hooks/table'
  import {
    deleteAiMcpServer,
    getAiMcpServer,
    getAiMcpTool,
    postAiMcpServer,
    postAiMcpServerBuiltin,
    postAiMcpServerRefreshStatus,
    postAiMcpServerSyncTools,
    postAiMcpToolImportApiInfo,
    putAiMcpServer,
  } from '@/api/ai'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import TableTabs from '@/components/table/TableTabs.vue'
  import { formatProjectProductPath, getEnumTagColor, getOptionId } from '@/utils/business-format'
  import { serverColumns, serverTableScrollX, toolColumns, toolTableScrollX } from './config'

  const enumStore = useEnum()
  const fieldNames = { value: 'key', label: 'title' }
  const MCP_TRANSPORT_STREAMABLE_HTTP = 0
  const MCP_AUTH_NONE = 0
  const MCP_AUTH_BEARER = 1
  const MCP_AUTH_API_KEY = 2
  const servers = ref<any[]>([])
  const pagination = usePagination(loadServers, () => loading)
  const tools = ref<any[]>([])
  const selectedServer = ref<any>(null)
  const loading = ref(false)
  const toolLoading = ref(false)
  const visible = ref(false)
  const toolVisible = ref(false)
  const toolCategory = ref('all')
  const syncTestEnv = ref<any>()
  const refreshLoading = ref(false)
  const saving = ref(false)
  const actionLoading = ref('')
  const form = reactive<any>({})
  const toolCategories = computed(() => {
    const categoryMap = new Map<string, { key: string; title: string; count: number }>()
    tools.value.forEach((tool) => {
      const key = tool.category || 'other'
      const current = categoryMap.get(key) || {
        key,
        title: tool.category_title || '其他',
        count: 0,
      }
      current.count += 1
      categoryMap.set(key, current)
    })
    return Array.from(categoryMap.values()).sort((a, b) => b.count - a.count)
  })
  const filteredTools = computed(() => {
    if (toolCategory.value === 'all') return tools.value
    return tools.value.filter((tool) => (tool.category || 'other') === toolCategory.value)
  })
  function enumTitle(options: any[] = [], value: any) {
    return options.find((item) => item.key === value)?.title || value || '-'
  }
  function enumColor(options: any[], value: any) {
    return getEnumTagColor(options, value, enumStore.colors)
  }
  function statusColor(value: any) {
    return enumStore.status_colors?.[Number(value)]
  }
  async function loadServers() {
    loading.value = true
    try {
      const res = await getAiMcpServer({ page: pagination.page, pageSize: pagination.pageSize })
      servers.value = res.data || []
      pagination.setTotalSize((res as any).totalSize || servers.value.length)
    } finally {
      loading.value = false
    }
  }
  async function loadTools(record: any) {
    selectedServer.value = record
    toolCategory.value = 'all'
    toolLoading.value = true
    try {
      tools.value = (await getAiMcpTool({ server: record.id })).data || []
    } finally {
      toolLoading.value = false
    }
  }
  function openTools(record: any) {
    toolVisible.value = true
    loadTools(record)
  }
  function openServer(record?: any) {
    Object.keys(form).forEach((key) => delete form[key])
    Object.assign(
      form,
      record
        ? {
            id: record.id,
            name: record.name,
            server_url: record.server_url,
            project_product: record.project_product?.id || record.project_product,
            module: record.module?.id || record.module,
            type: record.type,
            transport_type: record.transport_type,
            auth_type: record.auth_type,
            auth_config: { ...(record.auth_config || {}) },
            description: record.description,
            prompt: record.prompt,
            status: record.status,
          }
        : {
            transport_type: MCP_TRANSPORT_STREAMABLE_HTTP,
            auth_type: MCP_AUTH_NONE,
            status: 1,
            type: 0,
            auth_config: {},
          }
    )
    ensureAuthConfig()
    visible.value = true
  }
  async function saveServer() {
    ensureAuthConfig()
    if (!String(form.prompt || '').trim()) {
      Message.warning('请填写MCP使用提示词')
      return
    }
    form.prompt = String(form.prompt).trim()
    const payload = {
      ...form,
      project_product: getOptionId(form.project_product),
      module: getOptionId(form.module),
    }
    saving.value = true
    try {
      await (form.id ? putAiMcpServer(payload) : postAiMcpServer(payload))
      Message.success('保存成功')
      visible.value = false
      await loadServers()
    } finally {
      saving.value = false
    }
  }
  function ensureAuthConfig() {
    form.auth_config = form.auth_config || {}
    if (form.auth_type === MCP_AUTH_API_KEY) {
      form.auth_config.header_name = form.auth_config.header_name || 'Authorization'
    }
  }
  async function refreshStatus() {
    refreshLoading.value = true
    try {
      await postAiMcpServerRefreshStatus()
      await loadServers()
      Message.success('状态已刷新')
    } finally {
      refreshLoading.value = false
    }
  }
  async function onModifyStatus(newValue: any, record: any) {
    try {
      const status = newValue ? 1 : 0
      const res: any = await putAiMcpServer({ id: record.id, status })
      record.status = status
      if (!newValue) record.is_connected = false
      Message.success(
        res.msg ||
          (newValue ? 'MCP服务已启用，刷新状态时将尝试连接' : 'MCP服务已停用，不再尝试连接')
      )
      return true
    } catch (error) {
      return false
    }
  }
  async function onModifyBuiltin(newValue: any, record: any) {
    actionLoading.value = `builtin-${record.id}`
    try {
      await postAiMcpServerBuiltin({ id: record.id, is_builtin: !!newValue })
      Message.success(newValue ? '已设为内置 MCP，其他 MCP 已自动取消内置' : '已取消内置 MCP')
      await loadServers()
      return true
    } catch (error) {
      return false
    } finally {
      actionLoading.value = ''
    }
  }
  function deleteServer(record: any) {
    Modal.warning({
      title: '删除 MCP',
      content: `确认删除 MCP「${record.name || record.id}」吗？`,
      hideCancel: false,
      onOk: async () => {
        await deleteAiMcpServer(record.id)
        Message.success('删除成功')
        await loadServers()
      },
    })
  }
  async function syncTools(record: any) {
    actionLoading.value = `sync-${record.id}`
    try {
      await postAiMcpServerSyncTools({ id: record.id, test_env: syncTestEnv.value })
      Message.success('同步完成')
      if (toolVisible.value && selectedServer.value?.id === record.id) {
        await loadTools(record)
      }
    } finally {
      actionLoading.value = ''
    }
  }
  async function syncSelectedTools() {
    if (!selectedServer.value) return
    await syncTools(selectedServer.value)
  }
  async function importToolToApi(record: any) {
    actionLoading.value = `import-${record.id}`
    try {
      await postAiMcpToolImportApiInfo({ tool_id: record.id })
      Message.success('导入成功')
      if (selectedServer.value) await loadTools(selectedServer.value)
    } finally {
      actionLoading.value = ''
    }
  }
  onMounted(async () => {
    await enumStore.getEnum()
    loadServers()
  })
</script>

<style scoped>
  .mango-ai-mcp-tool-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
  }

  .mango-ai-mcp-tool-filter {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }

  .mango-ai-mcp-sync-env {
    width: 150px;
  }
</style>
