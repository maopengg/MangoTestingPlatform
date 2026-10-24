<template>
  <ProjectProductNavigationWorkbench
    class="mango-product-overview"
    data-navigation-layout="project-groups"
    @search="emit('search')"
    @reset-search="emit('reset-search')"
  >
    <template #navigation>
      <nav class="mango-product-overview__navigation" aria-label="项目定位">
        <header
          ><strong>项目导航</strong><span>{{ groups.length }} 个项目</span></header
        >
        <p>点击定位，不隐藏其他项目</p>
        <div class="mango-product-overview__links">
          <button
            type="button"
            :aria-current="activeProject === '' ? 'location' : undefined"
            @click="locateAll"
          >
            <span>全部项目</span><span>{{ matchedCount }}</span>
          </button>
          <button
            v-for="group in groups"
            :key="group.id"
            type="button"
            :aria-current="activeProject === group.id ? 'location' : undefined"
            @click="locate(group.id)"
          >
            <span :title="group.name">{{ group.name }}</span
            ><span>{{ group.products.length }}</span>
          </button>
        </div>
      </nav>
    </template>
    <template #search><slot name="search" /></template>
    <template #toolbar>
      <a-space wrap>
        <a-button
          v-permission="'config.product:create'"
          type="primary"
          size="small"
          @click="emit('add')"
          >新增产品</a-button
        >
      </a-space>
    </template>
    <div ref="overviewRef" class="mango-product-overview__body">
      <a-alert v-if="error" type="error" class="mango-product-overview__error">
        {{ error }}
        <a-button size="small" type="text" :loading="loading" @click="emit('refresh')">重试</a-button>
      </a-alert>
      <MangoPanelSpin :loading="loading" class="mango-product-overview__spin">
        <div v-if="!groups.length && !loading" class="mango-empty-state"
          >暂无匹配的项目或产品，请调整筛选条件。</div
        >
        <section
          v-for="group in groups"
          :key="group.id"
          :ref="(element) => setSection(group.id, element)"
          class="mango-product-overview__group"
        >
          <header class="mango-product-overview__group-header">
            <button
              type="button"
              :aria-expanded="!collapsed.includes(group.id)"
              :aria-controls="`mango-product-group-${group.id}`"
              @click="toggle(group.id)"
            >
              <span aria-hidden="true">{{ collapsed.includes(group.id) ? '▸' : '▾' }}</span>
              <strong>{{ group.name }}</strong>
              <span>{{
                group.products.length === group.total
                  ? `${group.total} 个产品`
                  : `匹配 ${group.products.length} / 共 ${group.total} 个产品`
              }}</span>
            </button>
          </header>
          <div v-show="!collapsed.includes(group.id)" :id="`mango-product-group-${group.id}`">
            <a-table
              v-if="group.products.length"
              :columns="tableColumns"
              :data="group.products"
              :pagination="false"
              :bordered="false"
              :scroll="{ x: 1280 }"
              row-key="id"
            >
              <template #columns>
                <a-table-column
                  v-for="item in tableColumns"
                  :key="item.key"
                  :data-index="item.key"
                  :title="item.title"
                  :width="item.width"
                  :align="item.align"
                  :fixed="item.fixed"
                  :ellipsis="item.ellipsis"
                  :tooltip="item.tooltip"
                >
                  <template #cell="{ record }">
                    <template v-if="item.key === 'index'">{{ record.id }}</template>
                    <template v-else-if="item.key === 'owners'">
                      <a-space v-if="record.owners?.length" :size="4" wrap>
                        <a-tag v-for="owner in record.owners" :key="owner.id" size="small">{{
                          owner.name || owner.username
                        }}</a-tag> </a-space
                      ><span v-else>-</span>
                    </template>
                    <a-tag
                      v-else-if="item.key === 'ui_client_type'"
                      :color="enumStore.colors[record.ui_client_type]"
                      size="small"
                      >{{ enumTitle(enumStore.drive_type, record.ui_client_type) }}</a-tag
                    >
                    <a-tag
                      v-else-if="item.key === 'api_client_type'"
                      :color="enumStore.colors[record.api_client_type]"
                      size="small"
                      >{{ enumTitle(enumStore.api_client, record.api_client_type) }}</a-tag
                    >
                    <template v-else-if="item.key === 'update_user'">{{
                      record.update_user?.name || record.update_user?.username || '-'
                    }}</template>
                    <MangoTableActions
                      v-else-if="item.key === 'actions'"
                      :actions="[
                        {
                          permission: 'config.product:detail',
                          label: '模块',
                          onClick: () => emit('module', record),
                        },
                        {
                          permission: 'config.product:detail',
                          label: '逻辑数据库',
                          onClick: () => emit('datasource', record),
                        },
                        {
                          permission: 'config.product:edit',
                          label: '编辑',
                          onClick: () => emit('edit', record),
                        },
                        {
                          permission: 'config.product:delete',
                          label: '删除',
                          danger: true,
                          onClick: () => emit('delete', record),
                        },
                      ]"
                    />
                    <template v-else>{{ record[item.key] ?? '-' }}</template>
                  </template>
                </a-table-column>
              </template>
            </a-table>
            <div v-else class="mango-empty-state">该项目暂无产品，可通过页面顶部“新增产品”创建。</div>
          </div>
        </section>
      </MangoPanelSpin>
    </div>
  </ProjectProductNavigationWorkbench>
</template>

<script setup lang="ts">
  import { computed, nextTick, ref, watch } from 'vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { tableColumns } from '../config'
  import { groupProducts } from '../overview'
  const props = defineProps<{
    products: any[]
    projects: any[]
    conditions: any[]
    loading: boolean
    error: string
  }>()
  const emit = defineEmits<{
    (event: 'search' | 'reset-search' | 'refresh'): void
    (event: 'add', projectId?: string): void
    (event: 'module' | 'datasource' | 'edit' | 'delete', product: any): void
  }>()
  const enumStore = useEnum()
  const collapsed = ref<string[]>([])
  const activeProject = ref('')
  const overviewRef = ref<HTMLElement>()
  const sections = new Map<string, HTMLElement>()
  const groups = computed(() => groupProducts(props.products, props.projects, props.conditions))
  watch(
    () => props.conditions.map((item) => JSON.stringify(item.value)).join('|'),
    () => {
      collapsed.value = []
      activeProject.value = ''
    }
  )
  const matchedCount = computed(() =>
    groups.value.reduce((sum, group) => sum + group.products.length, 0)
  )
  function enumTitle(options: any[], value: unknown) {
    return options?.find((item) => String(item.key) === String(value))?.title || '-'
  }
  function setSection(id: string, element: any) {
    if (element) sections.set(id, element)
    else sections.delete(id)
  }
  function toggle(id: string) {
    collapsed.value = collapsed.value.includes(id)
      ? collapsed.value.filter((key) => key !== id)
      : [...collapsed.value, id]
  }
  async function locate(id: string) {
    activeProject.value = id
    collapsed.value = collapsed.value.filter((key) => key !== id)
    await nextTick()
    sections.get(id)?.scrollIntoView({ block: 'start', inline: 'nearest' })
  }
  function locateAll() {
    activeProject.value = ''
    overviewRef.value?.scrollIntoView({ block: 'start', inline: 'nearest' })
  }
</script>

<style scoped>
  .mango-product-overview__navigation {
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
    padding: var(--m-card-padding);
    border: 1px solid var(--m-border-strong);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
  }
  .mango-product-overview__navigation header {
    display: flex;
    justify-content: space-between;
    gap: var(--m-space-sm);
  }
  .mango-product-overview__navigation p,
  .mango-product-overview__navigation header span {
    color: var(--m-muted);
    font-size: 12px;
  }
  .mango-product-overview__links {
    min-height: 0;
    overflow-y: auto;
  }
  .mango-product-overview__links button {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--m-space-sm);
    width: 100%;
    padding: 10px;
    border: 0;
    border-radius: var(--m-radius);
    background: transparent;
    color: var(--m-text);
    text-align: left;
    cursor: pointer;
  }
  .mango-product-overview__links button span:first-child {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-product-overview__links button:hover {
    background: var(--m-surface-soft);
  }
  .mango-product-overview__links button[aria-current] {
    background: var(--m-primary-soft);
    color: var(--m-primary);
  }
  .mango-product-overview button:focus-visible {
    outline: 2px solid var(--m-primary);
    outline-offset: -2px;
  }
  .mango-product-overview__body {
    padding: 0;
  }
  .mango-product-overview__spin {
    display: block;
    width: 100%;
    min-height: 160px;
  }
  .mango-product-overview__group {
    min-width: 0;
    margin-bottom: var(--m-page-gap);
    border-bottom: 1px solid var(--m-border);
  }
  .mango-product-overview__group-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--m-space-sm);
    padding: var(--m-space-sm) var(--m-card-padding);
    background: var(--m-surface-soft);
  }
  .mango-product-overview__group-header > button:first-child {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--m-space-sm);
    min-width: 0;
    padding: 0;
    border: 0;
    background: transparent;
    color: var(--m-text);
    cursor: pointer;
    text-align: left;
  }
  .mango-product-overview__group-header strong {
    overflow-wrap: anywhere;
  }
  .mango-product-overview__group-header > button:first-child > span:last-child {
    color: var(--m-muted);
    font-size: 12px;
  }
  .mango-product-overview__error {
    margin-bottom: var(--m-page-gap);
  }
</style>
