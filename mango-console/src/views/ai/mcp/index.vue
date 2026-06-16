<template>
  <TableBody>
    <template #header><TableHeader title="AI / MCP服务" @search="loadServers" /></template>
    <template #default>
      <a-tabs>
        <template #extra>
          <a-space size="mini">
            <div>
              <a-button size="small" type="primary" @click="openServer()">新增 MCP</a-button>
            </div>
            <div>
              <a-button size="small" :loading="refreshLoading" @click="refreshStatus">刷新状态</a-button>
            </div>
          </a-space>
        </template>
      </a-tabs>
      <a-table
        :bordered="false"
        :columns="serverColumns"
        :data="servers"
        :loading="loading"
        :pagination="false"
        :row-key="'id'"
        :scroll="{ x: 1380 }"
      >
        <template #columns>
          <a-table-column v-for="item of serverColumns" :key="item.key" v-bind="item">
            <template v-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="statusColor(record.status)" size="small">
                {{ enumTitle(enumStore.ai_mcp_status, record.status) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'auth_type'" #cell="{ record }">
              <a-tag :color="enumColor(record.auth_type)" size="small">
                {{ enumTitle(enumStore.ai_mcp_auth_type, record.auth_type) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'is_builtin'" #cell="{ record }">
              <a-switch
                :before-change="(newValue) => onModifyBuiltin(newValue, record)"
                :default-checked="!!record.is_builtin"
              />
            </template>
            <template v-else-if="item.key === 'is_connected'" #cell="{ record }">
              <a-tooltip v-if="!record.is_connected && record.last_error" :content="record.last_error">
                <a-tag size="small" :color="statusColor(5)">未连接</a-tag>
              </a-tooltip>
              <a-tag v-else-if="record.is_connected" size="small" :color="statusColor(3)">已连接</a-tag>
              <a-tag v-else size="small" :color="statusColor(0)">未检测</a-tag>
            </template>
            <template v-else-if="item.key === 'prompt'" #cell="{ record }">
              {{ record.prompt || '-' }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { label: '编辑', onClick: () => openServer(record) },
                  { label: '工具', onClick: () => openTools(record) },
                  { label: '删除', danger: true, onClick: () => deleteServer(record) },
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
  <a-modal v-model:visible="visible" title="MCP服务" width="640px" @ok="saveServer">
    <a-form :model="form" layout="vertical">
      <a-form-item label="名称" required><a-input v-model="form.name" /></a-form-item>
      <a-form-item label="服务地址" required><a-input v-model="form.server_url" /></a-form-item>
      <a-form-item label="MCP使用提示词" required>
        <a-textarea
          v-model="form.prompt"
          placeholder="说明这个 MCP 适合做什么、什么时候应该使用、不要用于什么场景。生成自动化时会发送给 AI。"
          :auto-size="{ minRows: 4, maxRows: 8 }"
        />
      </a-form-item>
      <a-form-item label="Transport">
        <a-select v-model="form.transport_type" :options="enumStore.ai_mcp_transport_type" :field-names="fieldNames" />
      </a-form-item>
      <a-form-item label="鉴权方式">
        <a-select v-model="form.auth_type" :options="enumStore.ai_mcp_auth_type" :field-names="fieldNames" />
      </a-form-item>
      <a-form-item v-if="form.auth_type === MCP_AUTH_BEARER" label="Token" required>
        <a-input-password v-model="form.auth_config.token" placeholder="输入 token，系统请求时会自动添加 Bearer 前缀" />
      </a-form-item>
      <template v-if="form.auth_type === MCP_AUTH_API_KEY">
        <a-form-item label="Header 名称" required>
          <a-input v-model="form.auth_config.header_name" placeholder="例如 Authorization 或 X-API-Key" />
        </a-form-item>
        <a-form-item label="Header 前缀">
          <a-input v-model="form.auth_config.prefix" placeholder="例如 Bearer，可留空" />
        </a-form-item>
        <a-form-item label="API Key" required>
          <a-input-password v-model="form.auth_config.api_key" />
        </a-form-item>
      </template>
    </a-form>
  </a-modal>
  <a-drawer v-model:visible="toolVisible" :title="`${selectedServer?.name || ''} / 工具列表`" width="72%">
    <template #title>
      <div class="mango-ai-mcp-tool-title">
        <span>{{ selectedServer?.name || '' }} / 工具列表</span>
        <a-button
          size="small"
          type="primary"
          :loading="selectedServer ? actionLoading === `sync-${selectedServer.id}` : false"
          :disabled="!selectedServer"
          @click="syncSelectedTools"
        >
          同步工具
        </a-button>
      </div>
    </template>
    <div class="mango-ai-mcp-tool-filter">
      <a-radio-group v-model="toolCategory" type="button" size="small">
        <a-radio value="all">全部 {{ tools.length }}</a-radio>
        <a-radio v-for="item in toolCategories" :key="item.key" :value="item.key">
          {{ item.title }} {{ item.count }}
        </a-radio>
      </a-radio-group>
    </div>
    <a-table
      :bordered="false"
      :columns="toolColumns"
      :data="filteredTools"
      :loading="toolLoading"
      :pagination="false"
      :row-key="'id'"
      :scroll="{ x: 920 }"
    >
      <template #columns>
        <a-table-column v-for="item of toolColumns" :key="item.key" v-bind="item">
          <template v-if="item.key === 'category_title'" #cell="{ record }">
            <a-tag size="small">{{ record.category_title || '其他' }}</a-tag>
          </template>
          <template v-else-if="item.key === 'risk_level'" #cell="{ record }">
            <a-tag :color="enumColor(record.risk_level)" size="small">
              {{ enumTitle(enumStore.ai_mcp_tool_risk_level, record.risk_level) }}
            </a-tag>
          </template>
          <template v-else-if="item.key === 'enabled'" #cell="{ record }">
            <a-tag size="small" :color="statusColor(record.enabled ? 1 : 0)">
              {{ record.enabled ? '启用' : '停用' }}
            </a-tag>
          </template>
          <template v-else-if="item.key === 'require_confirm'" #cell="{ record }">
            <a-tag size="small" :color="statusColor(record.require_confirm ? 1 : 0)">
              {{ record.require_confirm ? '需确认' : '无需确认' }}
            </a-tag>
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
    putAiMcpServer,
  } from '@/api/ai'

  const enumStore = useEnum()
  const fieldNames = { value: 'key', label: 'title' }
  const MCP_TRANSPORT_STREAMABLE_HTTP = 0
  const MCP_AUTH_NONE = 0
  const MCP_AUTH_BEARER = 1
  const MCP_AUTH_API_KEY = 2
  const servers = ref<any[]>([])
  const pagination = usePagination(loadServers)
  const tools = ref<any[]>([])
  const selectedServer = ref<any>(null)
  const loading = ref(false)
  const toolLoading = ref(false)
  const visible = ref(false)
  const toolVisible = ref(false)
  const toolCategory = ref('all')
  const refreshLoading = ref(false)
  const actionLoading = ref('')
  const form = reactive<any>({})
  const serverColumns = [
    { title: 'ID', key: 'id', dataIndex: 'id', width: 70 },
    { title: '名称', key: 'name', dataIndex: 'name' },
    { title: '地址', key: 'server_url', dataIndex: 'server_url', ellipsis: true, tooltip: true },
    { title: '提示词', key: 'prompt', dataIndex: 'prompt', ellipsis: true, tooltip: true },
    { title: '状态', key: 'status', dataIndex: 'status', width: 90 },
    { title: '权限', key: 'auth_type', dataIndex: 'auth_type', width: 120 },
    { title: '是否内置', key: 'is_builtin', dataIndex: 'is_builtin', width: 110 },
    { title: '是否已连接', key: 'is_connected', dataIndex: 'is_connected', width: 130 },
    { title: '操作', key: 'actions', dataIndex: 'actions', align: 'center', fixed: 'right', width: 170 },
  ]
  const toolColumns = [
    { title: '分类', key: 'category_title', dataIndex: 'category_title', width: 130 },
    { title: '工具', key: 'name', dataIndex: 'name', ellipsis: true, tooltip: true },
    { title: '风险', key: 'risk_level', dataIndex: 'risk_level', width: 120 },
    { title: '启用', key: 'enabled', dataIndex: 'enabled', width: 90 },
    { title: '确认', key: 'require_confirm', dataIndex: 'require_confirm', width: 90 },
  ]
  const toolCategories = computed(() => {
    const categoryMap = new Map<string, { key: string; title: string; count: number }>()
    tools.value.forEach((tool) => {
      const key = tool.category || 'other'
      const current = categoryMap.get(key) || { key, title: tool.category_title || '其他', count: 0 }
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
  function enumColor(value: any) {
    return enumStore.colors?.[Number(value)]
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
            transport_type: record.transport_type,
            auth_type: record.auth_type,
            auth_config: { ...(record.auth_config || {}) },
            description: record.description,
            prompt: record.prompt,
            status: record.status,
          }
        : { transport_type: MCP_TRANSPORT_STREAMABLE_HTTP, auth_type: MCP_AUTH_NONE, status: 1, auth_config: {} }
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
    await (form.id ? putAiMcpServer(form) : postAiMcpServer(form))
    Message.success('保存成功')
    visible.value = false
    await loadServers()
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
      await postAiMcpServerSyncTools(record.id)
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
    margin-bottom: 12px;
  }
</style>
