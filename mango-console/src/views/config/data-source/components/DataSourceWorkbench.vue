<template>
  <div class="mango-workbench-scroll-x mango-source-boundary">
    <div class="mango-source-workbench">
      <aside class="mango-source-nav" aria-label="数据源导航">
        <div class="mango-source-toolbar"><strong>连接配置 <small class="mango-source-count">{{ sources.length }}</small></strong>
          <a-button  size="small" type="primary" @click="$emit('add')">新增</a-button></div>
        <a-input v-model="keyword" placeholder="搜索名称、地址或账号" aria-label="搜索连接配置" allow-clear />
        <a-spin :loading="loading" class="mango-source-tree">
          <div v-if="!groups.length" class="mango-empty-state">没有匹配的数据源</div>
          <details v-for="group in groups" :key="group.key" open>
            <summary>{{ typeName(group.key) }} <small class="mango-source-count">{{ group.sources.length }}</small></summary>
            <button v-for="source in group.sources" :key="source.id" type="button"
              :class="['mango-source-leaf', { 'mango-source-leaf--active': selectedId === source.id }]"
              :aria-pressed="selectedId === source.id" @click="selectSource(source.id)">
              <span :title="source.display_name">{{ source.display_name }}</span>
              <small :title="connectionAddress(source)">{{ connectionAddress(source) }}</small>
              <small :title="source.user || '无账号'">账号：{{ source.user || '无账号' }}</small>
            </button>
          </details>
        </a-spin>
      </aside>
      <main class="mango-source-content">
        <div v-if="!selected" class="mango-empty-state">请选择连接配置</div>
        <template v-else>
          <div class="mango-source-toolbar mango-source-heading">
            <div class="mango-source-title">
              <strong :title="selected.display_name">{{ selected.display_name }}</strong>
              <div class="mango-source-meta" aria-label="连接信息">
                <small class="mango-source-muted">ID {{ selected.id }}</small>
                <a-tag :color="enums.colors[selected.db_type]" size="small">{{ typeName(selected.db_type) }}</a-tag>
                <span class="mango-source-meta-address" :title="connectionAddress(selected)">{{ connectionAddress(selected) }}</span>
                <span :title="'账号：' + (selected.user || '无账号')">{{ selected.user || '无账号' }}</span>
                <span :title="'最后修改：' + (selected.update_time || '-')">{{ selected.update_time || '-' }}</span>
              </div>
            </div>
            <a-space>
              <a-button  size="small" :loading="testingIds.includes(selected.id)" @click="$emit('test', selected)">测试连接</a-button>
              <a-button  size="small" @click="$emit('edit', selected)">编辑</a-button>
              <a-button  size="small" status="danger" @click="$emit('remove', selected)">删除</a-button>
            </a-space>
          </div>
          <a-tabs v-model:active-key="activeTab" class="mango-tabs-nav-only mango-source-tabs" @change="loadTab">
            <a-tab-pane key="bindings" title="绑定关系">
              <div class="mango-source-table-pane">
                <a-alert v-if="errors.bindings" type="error">{{ errors.bindings }}</a-alert>
                <div class="mango-source-table-area">
                  <a-table class="mango-native-scroll-table" :columns="bindingColumns" :data="pagedBindings"
                    :loading="bindingLoading" :pagination="false" :scroll="{ x: 960, y: '100%' }" row-key="id">
                    <template #environment="{ record }">{{ environmentName(record.environment) }}</template>
                    <template #target="{ record }">{{ record.database_name || (record.redis_db != null ? 'DB ' + record.redis_db : '未选默认库') }}{{ record.schema_name ? ' / ' + record.schema_name : '' }}</template>
                    <template #read="{ record }">{{ record.db_c_status === 1 ? '允许' : '禁止' }}</template>
                    <template #write="{ record }">{{ record.db_rud_status === 1 ? '允许' : '禁止' }}</template>
                    <template #actions="{ record }"><MangoTableActions :actions="[{ label: '管理绑定', onClick: () => openBindingPage(record) }]" /></template>
                  </a-table>
                </div>
                <TableFooter :pagination="bindingPagination" :show-refresh="false" />
              </div>
            </a-tab-pane>
            <a-tab-pane v-if="relational" key="databases" title="数据库发现">
              <div class="mango-source-table-pane">
                <div class="mango-source-toolbar">
                  <a-input v-model="databaseKeyword" class="mango-source-database-search" size="medium" placeholder="搜索数据库" allow-clear />
                </div>
                <div class="mango-source-table-area"><a-table class="mango-native-scroll-table" :columns="databaseColumns"
                  :data="pagedDatabases" :loading="databaseLoading" :pagination="false" :scroll="{ x: 600, y: '100%' }" row-key="name">
                  <template #query="{ record }"><MangoTableActions :actions="[{ label: '查询', onClick: () => openDatabaseQuery(record) }]" /></template>
                </a-table></div>
                <TableFooter :pagination="databasePagination" :show-refresh="false" />
              </div>
            </a-tab-pane>
          </a-tabs>
        </template>
      </main>
    </div>
  </div>
  <BaseSidePanel v-model:visible="bindingPage.visible" mode="page" title="逻辑数据库">
    <ProductDataSourcePage v-if="bindingPage.visible" embedded :project-product-id="bindingPage.productId"
      :project-product-name="bindingPage.productName" :datasource-id="bindingPage.datasourceId" />
  </BaseSidePanel>
  <DataSourceSqlQueryDrawer v-if="databaseQuery.visible" v-model:visible="databaseQuery.visible"
    :source-id="databaseQuery.sourceId" :source-name="databaseQuery.sourceName" :database-name="databaseQuery.databaseName" />
</template>
<script setup lang="ts">
  import { computed, reactive, ref, watch } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { useEnum } from '@/store/modules/get-enum'
  import { getDataSourceBindings, getDataSourceDatabases } from '@/api/system/data_source'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import ProductDataSourcePage from '@/views/config/product/datasource/index.vue'
  import DataSourceSqlQueryDrawer from './DataSourceSqlQueryDrawer.vue'
  import { usePagination } from '@/hooks/table'
  import { formatProjectProductPath } from '@/utils/business-format'
  import { bindingColumns, databaseColumns } from '../config'
  const props = defineProps<{ sources: any[]; loading: boolean; testingIds: any[] }>()
  defineEmits(['add', 'edit', 'remove', 'test'])
  const enums = useEnum()
  const route = useRoute()
  const router = useRouter()
  const keyword = ref('')
  const selectedId = ref<number>()
  const selected = computed(() => props.sources.find(item => item.id === selectedId.value))
  const firstSourceId = computed(() => [...props.sources].sort((a,b) => a.db_type-b.db_type)[0]?.id)
  const groups = computed(() => {
    const result = new Map<number, any>()
    for (const source of props.sources) {
      if (![source.display_name, source.host, source.user].join(' ').toLowerCase().includes(keyword.value.toLowerCase())) continue
      if (!result.has(source.db_type)) result.set(source.db_type, {key: source.db_type, sources: []})
      result.get(source.db_type).sources.push(source)
    }
    return [...result.values()].sort((a,b) => a.key-b.key)
  })
  const relational = computed(() => [0,1].includes(selected.value?.db_type))
  const activeTab = ref('bindings')
  const bindings = ref<any[]>([])
  const databases = ref<any[]>([])
  const bindingLoading = ref(false)
  const databaseLoading = ref(false)
  const databaseKeyword = ref('')
  const errors = reactive({bindings: '', databases: ''})
  const bindingPagination = usePagination(() => { bindingLoading.value = false }, bindingLoading)
  const databasePagination = usePagination(() => { databaseLoading.value = false }, databaseLoading)
  const filteredDatabases = computed(() => databases.value.filter(item => item.name.toLowerCase().includes(databaseKeyword.value.toLowerCase())))
  const pagedBindings = computed(() => bindings.value.slice((bindingPagination.page-1)*bindingPagination.pageSize, bindingPagination.page*bindingPagination.pageSize))
  const pagedDatabases = computed(() => filteredDatabases.value.slice((databasePagination.page-1)*databasePagination.pageSize, databasePagination.page*databasePagination.pageSize))
  watch(bindings, value => bindingPagination.setTotalSize(value.length))
  watch(filteredDatabases, value => {databasePagination.setTotalSize(value.length); databasePagination.page = 1})
  const bindingPage = reactive({visible: false, productId: '', productName: '', datasourceId: ''})
  const databaseQuery = reactive({visible: false, sourceId: 0, sourceName: '', databaseName: ''})
  function openDatabaseQuery(record: any) {
    if (!selected.value) return
    Object.assign(databaseQuery, {visible: true, sourceId: selected.value.id,
      sourceName: selected.value.display_name, databaseName: record.name})
  }
  function connectionAddress(source: any) {return source.file_path || source.host + ':' + source.port}
  function typeName(value: number) {return enums.data_source_type?.find((item:any) => item.key === value)?.title || String(value)}
  function environmentName(value: number) {return enums.environment_type?.find((item:any) => item.key === value)?.title || String(value)}
  function selectSource(id:number) {selectedId.value=id; router.replace({query: {...route.query, data_source_id: String(id)}})}
  function openBindingPage(record:any) {
    Object.assign(bindingPage, {visible:true, productId:String(record.datasource_alias__project_product_id),
      productName:record.datasource_alias__project_product__name, datasourceId:String(record.datasource_alias_id)})
  }
  async function loadBindings() {
    const id=selectedId.value
    if (!id) return
    bindingLoading.value=true; errors.bindings=''
    try {
      const res=await getDataSourceBindings({data_source_id:id})
      if(id===selectedId.value) bindings.value=(res.data || []).map((record: any) => ({
        ...record,
        project_product_path: formatProjectProductPath({
          name: record.datasource_alias__project_product__name,
          project: {name: record.datasource_alias__project_product__project__name},
        }),
      }))
    }
    catch(error:any) {if(id===selectedId.value) errors.bindings=error?.message || error?.msg || '读取绑定失败'}
    finally {if(id===selectedId.value) bindingLoading.value=false}
  }
  async function loadDatabases(refresh=false) {
    const id=selectedId.value
    if (!id || !relational.value) return
    databaseLoading.value=true; errors.databases=''
    try {const res=await getDataSourceDatabases({data_source_id:id,refresh}); if(id===selectedId.value) databases.value=res.data || []}
    catch(error:any) {if(id===selectedId.value) errors.databases=error?.message || error?.msg || '数据库发现失败'}
    finally {if(id===selectedId.value) databaseLoading.value=false}
  }
  function loadTab() {if(activeTab.value==='databases') loadDatabases(); else loadBindings()}
  watch(() => props.sources.map(item => item.id), ids => {
    if(!ids.includes(selectedId.value)) {
      const requested=Number(route.query.data_source_id)
      selectedId.value=ids.includes(requested)?requested:firstSourceId.value
    }
  }, {immediate:true})
  watch(() => route.query.data_source_id, value => {
    const id=Number(value); selectedId.value=props.sources.some(item=>item.id===id)?id:firstSourceId.value
  })
  watch([selectedId, () => selected.value?.update_time], () => {
    bindings.value=[]; databases.value=[]; errors.bindings=''; errors.databases=''
    bindingLoading.value=false; databaseLoading.value=false; bindingPagination.page=1; databasePagination.page=1
    activeTab.value='bindings'; loadTab()
  }, {immediate:true})
</script>
<style scoped>
  .mango-source-alias-row {
    display: flex;
    align-items: center;
    gap: var(--m-space-sm);
    min-width: 0;
  }
  .mango-source-alias-row > span {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-source-alias-row :deep(.arco-input-wrapper) {
    flex: 1;
    min-width: 0;
  }
  .mango-source-alias-row :deep(.arco-btn) {
    flex-shrink: 0;
  }
  .mango-source-alias-error {
    color: var(--m-danger);
    font-size: 12px;
    margin: var(--m-space-xs) 0;
  }
  .mango-source-boundary {
    --mango-workbench-min-width: 0px;
    height: 100%;
    min-height: 0;
  }
  .mango-source-workbench {
    display: grid;
    grid-template-columns: 380px minmax(0, 1fr);
    height: 100%;
    min-height: 0;
    background: var(--m-surface);
  }
  .mango-source-nav {
    display: flex;
    flex-direction: column;
    padding: var(--m-space-md);
    border-right: 1px solid var(--m-border);
    background: var(--m-surface-soft);
    min-width: 0;
    min-height: 0;
  }
  .mango-source-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--m-page-gap);
    margin-bottom: var(--m-space-md);
    flex-wrap: wrap;
  }
  .mango-source-database-search {
    width: 240px;
    max-width: 100%;
  }
  .mango-source-tree {
    display: block;
    margin-top: var(--m-space-sm);
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
    scrollbar-gutter: stable;
  }
  .mango-source-tree summary {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
    cursor: pointer;
    padding: 6px 0;
    font-weight: 600;
    list-style: none;
  }
  .mango-source-count {
    color: var(--m-muted);
    font-size: var(--m-font-caption);
    font-weight: 400;
    margin-left: var(--m-space-xs);
  }
  .mango-source-tree summary::-webkit-details-marker {
    display: none;
  }
  .mango-source-tree summary::before {
    content: '▶';
    flex: 0 0 24px;
    font-size: 16px;
    line-height: 28px;
    color: var(--m-muted);
    text-align: center;
  }
  .mango-source-tree details[open] > summary::before {
    content: '▼';
  }
  .mango-source-instance-label {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-source-tree .mango-source-instance {
    padding-left: 0;
    font-weight: 400;
    font-size: 12px;
    color: var(--m-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    overflow-wrap: normal;
  }
  .mango-source-leaf {
    display: flex;
    flex-direction: column;
    gap: 3px;
    width: 100%;
    text-align: left;
    padding: 8px 12px;
    border: 0;
    border-radius: var(--m-radius-sm);
    background: transparent;
    color: var(--m-text);
    cursor: pointer;
    font: inherit;
  }
  .mango-source-leaf span,
  .mango-source-leaf small {
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-source-leaf small {
    color: var(--m-muted);
  }
  .mango-source-leaf:hover:not(.mango-source-leaf--active) {
    background: var(--m-surface);
  }
  .mango-source-leaf--active {
    background: var(--m-primary-soft);
    color: var(--m-primary);
  }
  .mango-source-leaf:focus-visible {
    outline: 2px solid var(--m-primary);
    outline-offset: -2px;
  }
  .mango-source-content {
    min-width: 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow-y: hidden;
    overflow-x: hidden;
    container-type: inline-size;
    padding: var(--m-space-md);
    background: var(--m-surface);
  }
  .mango-source-heading {
    flex: none;
    align-items: flex-start;
  }
  .mango-source-heading :deep(.arco-space) {
    flex: none;
  }
  .mango-source-overview-section {
    flex: 0 1 auto;
    min-height: 0;
    max-height: 40%;
    overflow-y: auto;
    margin-bottom: var(--m-space-sm);
  }
  .mango-source-tabs {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }
  .mango-source-tabs :deep(.arco-tabs-content) {
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }
  .mango-source-tabs :deep(.arco-tabs-nav) {
    flex: none;
  }
  .mango-source-tabs :deep(.arco-tabs-content-list),
  .mango-source-tabs :deep(.arco-tabs-content-item-active),
  .mango-source-tabs :deep(.arco-tabs-pane) {
    height: 100%;
    min-height: 0;
  }
  .mango-source-tabs :deep(.arco-tabs-pane) {
    overflow: hidden;
  }
  .mango-source-table-pane {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    gap: var(--m-page-gap);
  }
  .mango-source-table-pane > :not(.mango-source-table-area) {
    flex: none;
  }
  .mango-source-table-area {
    flex: 1;
    min-height: 0;
  }
  .mango-source-table-pane > .mango-source-toolbar {
    margin-bottom: 0;
  }
  .mango-source-table-pane > p {
    margin: 0;
  }
  .mango-source-table-pane .mango-source-results {
    max-height: 140px;
    overflow-y: auto;
  }
  .mango-source-tree > details + details {
    border-top: 1px solid var(--m-border);
    margin-top: var(--m-space-sm);
  }
  .mango-source-tree details > details {
    margin-left: var(--m-space-xs);
    border-left: 1px solid var(--m-border);
  }
  .mango-source-overview {
    display: grid;
    grid-template-columns: minmax(0, 2fr) minmax(0, 1fr) minmax(0, 1fr);
    gap: var(--m-space-sm) var(--m-space-lg);
    margin: 0 0 var(--m-space-sm);
  }
  .mango-source-overview-row {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    align-items: baseline;
    gap: var(--m-space-sm);
    padding: var(--m-space-xs) 0;
  }
  .mango-source-overview dt {
    color: var(--m-muted);
    white-space: nowrap;
  }
  .mango-source-overview dd {
    margin: 0;
    color: var(--m-text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  @container (max-width: 780px) {
    .mango-source-overview {
      grid-template-columns: minmax(0, 1fr);
    }
  }
  @media (max-width: 800px) {
    .mango-source-workbench {
      grid-template-columns: minmax(0, 1fr);
      grid-template-rows: minmax(160px, 30%) minmax(0, 1fr);
    }
    .mango-source-nav {
      border-right: 0;
      border-bottom: 1px solid var(--m-border);
    }
  }
  .mango-source-title {
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-width: 0;
    flex: 1;
  }
  .mango-source-title strong {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 16px;
  }
  .mango-source-meta {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--m-space-sm);
    min-width: 0;
    color: var(--m-muted);
    font-size: var(--m-font-caption);
  }
  .mango-source-meta > span {
    display: inline-flex;
    align-items: center;
    gap: var(--m-space-sm);
    min-width: 0;
    overflow-wrap: anywhere;
  }
  .mango-source-meta > span + span::before {
    content: '·';
    flex: none;
  }
  .mango-source-meta-address {
    max-width: 100%;
  }
  .mango-source-meta small {
    flex: none;
    font-size: var(--m-font-caption);
  }
  .mango-source-meta :deep(.arco-tag) {
    flex: none;
  }
  .mango-source-title span {
    overflow-wrap: anywhere;
  }
  .mango-source-muted {
    color: var(--m-muted);
    font-size: 12px;
  }
  .mango-source-search {
    width: 260px;
    max-width: 100%;
  }
  .mango-source-results {
    margin-top: 16px;
    padding: 12px;
    background: var(--m-bg);
    border-radius: var(--m-radius-sm);
    overflow-wrap: anywhere;
  }
</style>
