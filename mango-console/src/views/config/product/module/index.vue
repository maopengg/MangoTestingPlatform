<template>
  <TableBody class="mango-detail-workbench-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">{{ productModuleDetailTitle }}</div>
          <div class="mango-detail-subtitle">维护当前产品下真实的一、二、三级模块树</div>
        </div>
        <a-space class="mango-detail-actions">
          <a-button
            size="small"
            type="primary"
            @click="openModule()"
            data-testid="qa-views-config-product-module-button-增加"
            >增加</a-button
          >
          <a-button
            class="mango-back-button"
            size="small"
            @click="goBack"
            data-testid="qa-views-config-product-module-button-返回"
            >返回</a-button
          >
        </a-space>
      </div>
    </template>

    <template #default>
      <div class="mango-workbench-scroll-x mango-module-workbench-scroll">
        <div class="mango-module-workbench">
          <aside class="mango-module-sidebar mango-section-card">
            <div class="mango-section-title">
              <div class="mango-section-title__main">
                <h2>模块导航</h2>
                <p>点击一级或二级模块查看当前模块及后代</p>
              </div>
              <a-tag size="small">{{ modules.length }}</a-tag>
            </div>
            <div class="mango-soft-panel mango-module-sidebar-filter">
              <a-input-search
                v-model="treeKeyword"
                allow-clear
                placeholder="搜索模块名称"
                data-testid="qa-views-config-product-module-input-search-搜索模块名称"
              />
              <div class="mango-module-stats">
                <span>一级 {{ levelCount(1) }}</span>
                <span>二级 {{ levelCount(2) }}</span>
                <span>三级 {{ levelCount(3) }}</span>
              </div>
            </div>
            <div class="mango-module-tree">
              <a-tree
                v-model:expanded-keys="expandedTreeKeys"
                :selected-keys="selectedTreeKeys"
                :data="displayTree"
                block-node
                size="small"
                @select="onTreeSelect"
              />
            </div>
          </aside>

          <section class="mango-module-main mango-section-card">
            <div class="mango-section-title">
              <div class="mango-section-title__main">
                <h2>{{ currentScopeTitle }}</h2>
                <p>模块父子关系以真实 ID 保存，旧路径字段只用于迁移核对</p>
              </div>
              <div class="mango-section-actions">
                <a-button
                  size="small"
                  @click="resetFilters"
                  data-testid="qa-views-config-product-module-button-重置筛选"
                  >重置筛选</a-button
                >
              </div>
            </div>
            <div class="mango-soft-panel mango-module-filter">
              <a-form :model="filter" layout="inline">
                <a-form-item label="三级模块名称">
                  <a-input
                    v-model="filter.keyword"
                    allow-clear
                    placeholder="请输入三级模块名称"
                    @input="pagination.page = 1"
                    data-testid="qa-views-config-product-module-input-请输入三级模块名称"
                  />
                </a-form-item>
                <a-form-item label="模块层级">
                  <a-select
                    v-model="filter.level"
                    :options="moduleLevelOptions"
                    placeholder="请选择模块层级"
                    @change="pagination.page = 1"
                  />
                </a-form-item>
              </a-form>
            </div>
            <div class="mango-module-content">
              <a-table
                :scroll="{ x: 1430 }"
                :bordered="false"
                :columns="columns"
                :data="pagedModules"
                :loading="loading"
                :pagination="false"
                row-key="id"
              >
                <template #columns>
                  <a-table-column v-for="item of columns" :key="item.dataIndex" v-bind="item">
                    <template v-if="item.dataIndex === 'level_3_name'" #cell="{ record }">
                      {{ moduleLevelName(record, 3) }}
                    </template>
                    <template v-else-if="item.dataIndex === 'level_2_name'" #cell="{ record }">
                      {{ moduleLevelName(record, 2) }}
                    </template>
                    <template v-else-if="item.dataIndex === 'level_1_name'" #cell="{ record }">
                      {{ moduleLevelName(record, 1) }}
                    </template>
                    <template v-else-if="item.dataIndex === 'level'" #cell="{ record }">
                      <a-tag :color="enumStore.colors[Number(record.level || 1) - 1]" size="small">
                        {{ record.level || '-' }}级
                      </a-tag>
                    </template>
                    <template v-else-if="item.dataIndex === 'update_user'" #cell="{ record }">
                      {{ record.update_user?.name || record.update_user?.username || '-' }}
                    </template>
                    <template v-else-if="item.dataIndex === 'actions'" #cell="{ record }">
                      <MangoTableActions
                        :actions="[
                          { permission: 'config.product:edit', label: '编辑', onClick: () => openModule(record) },
                          { permission: 'config.product:delete', label: '删除', danger: true, onClick: () => removeModule(record) },
                        ]"
                      />
                    </template>
                  </a-table-column>
                </template>
              </a-table>
            </div>
            <TableFooter :pagination="pagination" />
          </section>
        </div>
      </div>
    </template>
  </TableBody>

  <ModalDialog
    ref="moduleDialogRef"
    :title="moduleForm.id ? '编辑模块' : '新增模块路径'"
    width="540px"
    @confirm="saveModule"
  >
    <template #content>
      <a-form :model="moduleForm" class="mango-module-form">
        <template v-if="moduleForm.id">
          <a-form-item class="mango-form-item__require" label="模块名称">
            <a-input
              v-model="moduleForm.name"
              :max-length="64"
              placeholder="请输入模块名称"
              data-testid="qa-views-config-product-module-input-请输入模块名称"
            />
          </a-form-item>
        </template>
        <template v-else>
          <div class="mango-module-path-tip">
            一次创建完整三级路径；一级、二级仅作为分类，业务数据只能绑定三级模块。
          </div>
          <a-form-item class="mango-form-item__require" label="一级模块">
            <a-auto-complete
              v-model="moduleForm.level_1_name"
              :data="levelOneNameOptions"
              allow-clear
              placeholder="输入新名称或选择已有一级模块"
              @change="onCreateLevelOneChange"
              data-testid="qa-views-config-product-module-auto-complete-输入新名称或选择已有一级模块"
            />
          </a-form-item>
          <a-form-item class="mango-form-item__require" label="二级模块">
            <a-auto-complete
              v-model="moduleForm.level_2_name"
              :data="levelTwoNameOptions"
              :disabled="!moduleForm.level_1_name"
              allow-clear
              placeholder="输入新名称或选择已有二级模块"
              @change="onCreateLevelTwoChange"
              data-testid="qa-views-config-product-module-auto-complete-输入新名称或选择已有二级模块"
            />
          </a-form-item>
          <a-form-item class="mango-form-item__require" label="三级模块">
            <a-input
              v-model="moduleForm.level_3_name"
              :disabled="!moduleForm.level_2_name"
              :max-length="64"
              placeholder="输入新的三级业务模块名称"
              data-testid="qa-views-config-product-module-input-输入新的三级业务模块名称"
            />
          </a-form-item>
        </template>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import { computed, onMounted, reactive, ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { useRoute } from 'vue-router'
  import ModalDialog from '@/components/overlays/ModalDialog.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { useProject } from '@/store/modules/get-project'
  import { formatModulePath } from '@/utils/business-format'
  import {
    deleteUserModule,
    getUserModule,
    postUserModulePath,
    putUserModule,
  } from '@/api/system/module'
  import { columns } from './config'

  const route = useRoute()
  const enumStore = useEnum()
  const projectStore = useProject()
  const loading = ref(false)
  const moduleDialogRef = ref<InstanceType<typeof ModalDialog> | null>(null)
  const modules = ref<any[]>([])
  const treeKeyword = ref('')
  const selectedTreeKeys = ref<Array<string | number>>(['all'])
  const expandedTreeKeys = ref<Array<string | number>>(['all'])
  const selectedModuleId = ref<number>()
  const moduleForm = reactive<any>({})
  const filter = reactive({ keyword: '', level: 'all' as number | 'all' })
  const moduleLevelOptions = [
    { label: '全部层级', value: 'all' },
    { label: '一级模块', value: 1 },
    { label: '二级模块', value: 2 },
    { label: '三级模块', value: 3 },
  ]
  const pagination = reactive({
    page: 1,
    pageSize: 20,
    pageSizes: [20, 50, 100],
    showSizePicker: true,
    pageCount: 0,
    onChange: loadModules,
  })
  const projectProductId = computed(() => Number(route.query.id) || undefined)
  const productModuleDetailTitle = computed(
    () => `产品模块配置 / ${route.query.id || '-'} / ${route.query.name || '-'}`
  )

  function childIds(moduleId?: number) {
    if (!moduleId) return new Set<number>()
    const result = new Set<number>([moduleId])
    let changed = true
    while (changed) {
      changed = false
      for (const item of modules.value) {
        if (item.parent?.id && result.has(Number(item.parent.id)) && !result.has(Number(item.id))) {
          result.add(Number(item.id))
          changed = true
        }
      }
    }
    return result
  }

  const levelOneNameOptions = computed(() =>
    modules.value.filter((item) => Number(item.level) === 1).map((item) => String(item.name))
  )
  const selectedLevelOne = computed(() =>
    modules.value.find(
      (item) =>
        Number(item.level) === 1 &&
        String(item.name) === String(moduleForm.level_1_name || '').trim()
    )
  )
  const levelTwoNameOptions = computed(() => {
    if (!selectedLevelOne.value) return []
    return modules.value
      .filter(
        (item) =>
          Number(item.level) === 2 && Number(item.parent?.id) === Number(selectedLevelOne.value.id)
      )
      .map((item) => String(item.name))
  })
  const selectedLevelTwo = computed(() => {
    if (!selectedLevelOne.value) return undefined
    return modules.value.find(
      (item) =>
        Number(item.level) === 2 &&
        Number(item.parent?.id) === Number(selectedLevelOne.value.id) &&
        String(item.name) === String(moduleForm.level_2_name || '').trim()
    )
  })
  function buildTree(list: any[]) {
    const map = new Map<number, any>()
    list.forEach((item) =>
      map.set(Number(item.id), { key: item.id, title: item.name, name: item.name, children: [] })
    )
    const roots: any[] = []
    list.forEach((item) => {
      const node = map.get(Number(item.id))
      const parent = map.get(Number(item.parent?.id))
      if (parent) parent.children.push(node)
      else roots.push(node)
    })
    return roots
  }

  function filterTree(nodes: any[], keyword: string): any[] {
    if (!keyword) return nodes
    return nodes.reduce<any[]>((result, node) => {
      const children = filterTree(node.children || [], keyword)
      if (String(node.name).toLowerCase().includes(keyword) || children.length)
        result.push({ ...node, children })
      return result
    }, [])
  }

  const moduleTree = computed(() =>
    buildTree(modules.value.filter((item) => Number(item.level) < 3))
  )
  const displayTree = computed(() => [
    {
      key: 'all',
      title: `全部模块 (${modules.value.length})`,
      children: filterTree(moduleTree.value, treeKeyword.value.trim().toLowerCase()),
    },
  ])
  const currentScopeTitle = computed(() => {
    if (!selectedModuleId.value) return '全部模块'
    return (
      formatModulePath(modules.value.find((item) => Number(item.id) === selectedModuleId.value)) ||
      '当前模块'
    )
  })
  const filteredModules = computed(() => {
    const scope = childIds(selectedModuleId.value)
    const keyword = filter.keyword.trim().toLowerCase()
    return modules.value.filter((item) => {
      if (scope.size && !scope.has(Number(item.id))) return false
      if (filter.level !== 'all' && Number(item.level) !== filter.level) return false
      if (
        keyword &&
        (Number(item.level) !== 3 ||
          !String(item.name || '')
            .toLowerCase()
            .includes(keyword))
      )
        return false
      return true
    })
  })
  const pagedModules = computed(() => {
    const start = (pagination.page - 1) * pagination.pageSize
    return filteredModules.value.slice(start, start + pagination.pageSize)
  })

  function levelCount(level: number) {
    return modules.value.filter((item) => Number(item.level) === level).length
  }

  function moduleLevelName(record: any, targetLevel: number) {
    let current = record
    while (current && Number(current.level) > targetLevel) {
      current = current.parent
    }
    return Number(current?.level) === targetLevel ? current.name || '-' : '-'
  }

  function onTreeSelect(keys: Array<string | number>) {
    const key = keys[0] || 'all'
    selectedTreeKeys.value = [key]
    selectedModuleId.value = key === 'all' ? undefined : Number(key)
    pagination.page = 1
  }

  function resetFilters() {
    selectedModuleId.value = undefined
    selectedTreeKeys.value = ['all']
    filter.keyword = ''
    filter.level = 'all'
    treeKeyword.value = ''
    pagination.page = 1
  }

  function onCreateLevelOneChange() {
    moduleForm.level_2_name = ''
    moduleForm.level_3_name = ''
  }

  function onCreateLevelTwoChange() {
    moduleForm.level_3_name = ''
  }

  function openModule(record?: any) {
    Object.keys(moduleForm).forEach((key) => delete moduleForm[key])
    const selected = modules.value.find((item) => Number(item.id) === selectedModuleId.value)
    const selectedLevel = Number(selected?.level || 0)
    const selectedLevelOneName =
      selectedLevel === 1
        ? selected?.name
        : selectedLevel === 2
        ? selected?.parent?.name
        : selected?.parent?.parent?.name
    const selectedLevelTwoName =
      selectedLevel === 2 ? selected?.name : selectedLevel === 3 ? selected?.parent?.name : ''
    Object.assign(
      moduleForm,
      record
        ? { id: record.id, name: record.name }
        : {
            level_1_name: selectedLevelOneName || '',
            level_2_name: selectedLevelTwoName || '',
            level_3_name: '',
          }
    )
    moduleDialogRef.value?.show()
  }

  async function saveModule() {
    const requiredNames = moduleForm.id
      ? [moduleForm.name]
      : [moduleForm.level_1_name, moduleForm.level_2_name, moduleForm.level_3_name]
    if (requiredNames.some((name) => !String(name || '').trim())) {
      Message.error(moduleForm.id ? '请输入模块名称' : '请完整填写一级、二级、三级模块')
      moduleDialogRef.value?.setConfirmLoading(false)
      return
    }
    try {
      if (moduleForm.id) {
        await putUserModule({
          id: moduleForm.id,
          name: String(moduleForm.name).trim(),
        })
      } else {
        await postUserModulePath({
          project_product: projectProductId.value,
          level_1_name: String(moduleForm.level_1_name).trim(),
          level_2_name: String(moduleForm.level_2_name).trim(),
          level_3_name: String(moduleForm.level_3_name).trim(),
        })
      }
      projectStore.invalidateAllProductModuleTreeCache()
      Message.success('保存成功')
      await moduleDialogRef.value?.close()
      await loadModules()
    } catch {
      return
    } finally {
      moduleDialogRef.value?.setConfirmLoading(false)
    }
  }

  function removeModule(record: any) {
    Modal.confirm({
      title: '删除模块',
      content: `确认删除模块「${record.name}」吗？存在子模块或业务引用时后端会阻止删除。`,
      okText: '删除',
      cancelText: '取消',
      okButtonProps: { status: 'danger' },
      onBeforeOk: async () => {
        try {
          await deleteUserModule(record.id)
          projectStore.invalidateAllProductModuleTreeCache()
          Message.success('删除成功')
          await loadModules()
          return true
        } catch {
          return false
        }
      },
    })
  }

  async function loadModules() {
    loading.value = true
    try {
      const res = await getUserModule({ project_product: projectProductId.value })
      modules.value = res.data || []
      expandedTreeKeys.value = ['all']
    } finally {
      loading.value = false
    }
  }

  function goBack() {
    window.history.back()
  }

  watch(
    () => [filteredModules.value.length, pagination.pageSize],
    () => {
      pagination.pageCount = filteredModules.value.length
      const maxPage = Math.max(1, Math.ceil(filteredModules.value.length / pagination.pageSize))
      if (pagination.page > maxPage) pagination.page = maxPage
    },
    { immediate: true }
  )

  onMounted(async () => {
    await enumStore.getEnum()
    await loadModules()
  })
</script>

<style lang="less" scoped>
  .mango-module-workbench {
    display: grid;
    height: 100%;
    min-height: 0;
    padding-top: var(--m-page-gap);
    box-sizing: border-box;
    grid-template-columns: 280px minmax(0, 1fr);
    gap: var(--m-page-gap);
  }

  .mango-module-workbench-scroll {
    --mango-workbench-min-width: 960px;
    height: 100%;
  }

  .mango-module-workbench-scroll > .mango-module-workbench {
    min-width: var(--mango-workbench-min-width);
  }

  .mango-module-workbench > .mango-section-card + .mango-section-card {
    margin-top: 0;
  }

  .mango-module-sidebar,
  .mango-module-main {
    display: flex;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
    overflow: hidden;
  }

  .mango-module-stats {
    display: flex;
    gap: 6px;
    margin-top: 10px;
  }

  .mango-module-stats span {
    padding: 2px 7px;
    border: 1px solid var(--m-border);
    border-radius: 999px;
    color: var(--m-text-2);
    font-size: 12px;
  }

  .mango-module-tree {
    min-height: 0;
    overflow: auto;
    flex: 1;
  }

  .mango-module-content {
    flex: 1;
    min-height: 0;
    overflow-x: hidden;
    overflow-y: auto;
    scrollbar-color: var(--m-scrollbar-thumb) var(--m-scrollbar-track);
    scrollbar-width: thin;
  }

  .mango-module-content::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }

  .mango-module-content::-webkit-scrollbar-track {
    border-radius: 3px;
    background: var(--m-scrollbar-track);
  }

  .mango-module-content::-webkit-scrollbar-thumb {
    border-radius: 3px;
    background: var(--m-scrollbar-thumb);
  }

  .mango-module-content::-webkit-scrollbar-thumb:hover {
    background: var(--m-scrollbar-thumb-hover);
  }

  .mango-module-sidebar-filter,
  .mango-module-filter {
    margin-bottom: 10px;
    padding: 10px 10px 0;
  }

  .mango-module-sidebar-filter {
    min-height: 76px;
  }

  .mango-module-filter {
    min-height: 76px;
  }

  .mango-module-filter :deep(.arco-form) {
    display: grid;
    grid-template-columns: repeat(2, minmax(280px, 420px));
    gap: 0 10px;
  }

  .mango-module-path-tip {
    margin-bottom: 16px;
    padding: 10px 12px;
    border-radius: 4px;
    background: var(--m-fill-1);
    color: var(--m-text-2);
    font-size: 13px;
    line-height: 1.6;
  }

  @media (max-width: 960px) {
    .mango-module-workbench,
    .mango-module-filter :deep(.arco-form) {
      grid-template-columns: 1fr;
    }
  }
</style>
