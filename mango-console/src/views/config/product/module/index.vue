<template>
  <TableBody ref="tableBody" class="mango-detail-workbench-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">{{ productModuleDetailTitle }}</div>
          <div class="mango-detail-subtitle">维护当前产品下的模块结构和模块名称</div>
        </div>
        <a-space class="mango-detail-actions" wrap>
          <a-button size="small" type="primary" @click="doAppend">增加</a-button>
          <a-button size="small" @click="doResetSearch">返回</a-button>
        </a-space>
      </div>
    </template>
    <template #default>
      <div class="mango-module-workbench">
        <aside class="mango-module-sidebar mango-section-card">
          <div class="mango-module-sidebar__head">
            <div>
              <h3>模块导航</h3>
              <p>按层级快速定位模块</p>
            </div>
            <a-tag size="small">{{ filteredModuleData.length }}</a-tag>
          </div>
          <a-input-search
            v-model="filter.treeKeyword"
            allow-clear
            placeholder="搜索模块"
            @clear="resetPage"
            @search="resetPage"
          />
          <div class="mango-module-stats">
            <span>一级 {{ moduleStats.level1 }}</span>
            <span>二级 {{ moduleStats.level2 }}</span>
            <span>模块 {{ moduleStats.total }}</span>
          </div>
          <div class="mango-module-tree">
            <a-tree
              v-model:expanded-keys="expandedTreeKeys"
              v-model:selected-keys="selectedTreeKeys"
              :data="moduleTree"
              block-node
              size="small"
              @select="onTreeSelect"
            />
          </div>
        </aside>

        <section class="mango-module-main mango-section-card">
          <div class="mango-module-main__head">
            <div>
              <h3>{{ currentScopeTitle }}</h3>
              <p>筛选、编辑和删除当前产品下的模块</p>
            </div>
            <a-button size="small" @click="resetFilters">重置筛选</a-button>
          </div>
          <div class="mango-soft-panel mango-module-filter">
            <a-form :model="filter" layout="vertical">
              <a-form-item label="一级模块">
                <a-select
                  v-model="filter.level1"
                  :options="level1Options"
                  allow-clear
                  allow-search
                  placeholder="全部一级模块"
                  @change="onLevel1Change"
                />
              </a-form-item>
              <a-form-item label="二级模块">
                <a-select
                  v-model="filter.level2"
                  :options="level2Options"
                  allow-clear
                  allow-search
                  placeholder="全部二级模块"
                  @change="onLevel2Change"
                />
              </a-form-item>
              <a-form-item label="模块名称">
                <a-input
                  v-model="filter.tableKeyword"
                  allow-clear
                  placeholder="搜索实际模块"
                  @blur="resetPage"
                  @clear="resetPage"
                  @press-enter="resetPage"
                />
              </a-form-item>
            </a-form>
          </div>

          <a-table
            class="mango-module-table"
            :scroll="{ x: 990 }"
            :bordered="false"
            :columns="columns"
            :data="pagedModuleData"
            :loading="tableLoading"
            :pagination="false"
            row-key="id"
            size="small"
          >
            <template #columns>
              <a-table-column
                v-for="item of columns"
                :key="item.dataIndex"
                :align="item.align"
                :data-index="item.dataIndex"
                :ellipsis="item.ellipsis"
                :fixed="item.fixed"
                :title="item.title"
                :tooltip="item.tooltip"
                :width="item.width"
              >
                <template v-if="item.dataIndex === 'superior_module_1'" #cell="{ record }">
                  {{ record.superior_module_1 || '-' }}
                </template>
                <template v-else-if="item.dataIndex === 'superior_module_2'" #cell="{ record }">
                  {{ record.superior_module_2 || '-' }}
                </template>
                <template v-else-if="item.dataIndex === 'actions'" #cell="{ record }">
                  <MangoTableActions
                    :actions="[
                      { label: '编辑', onClick: () => onUpdate(record) },
                      { label: '删除', danger: true, onClick: () => onDelete(record) },
                    ]"
                  />
                </template>
              </a-table-column>
            </template>
          </a-table>
          <div class="mango-module-pagination">
            <a-pagination
              v-model:current="pagination.page"
              v-model:page-size="pagination.pageSize"
              :page-size-options="[20, 50, 100]"
              :total="filteredModuleData.length"
              show-total
              show-page-size
              size="small"
            />
          </div>
        </section>
      </div>
    </template>
  </TableBody>
  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          v-for="item of formItems"
          :key="item.key"
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>
<script lang="ts" setup>
  import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { ModalDialogType } from '@/types/components'
  import { useRoute } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'
  import { columns, formItems } from './config'
  import {
    deleteUserModule,
    getUserModule,
    postUserModule,
    putUserModule,
  } from '@/api/system/module'
  import { useProject } from '@/store/modules/get-project'
  const projectInfo = useProject()
  const route = useRoute()
  const productModuleDetailTitle = computed(() => {
    const id = route.query.id || '-'
    const name = route.query.name || '-'
    return `产品模块配置 / ${id} / ${name}`
  })
  const formModel = ref({})
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const tableLoading = ref(false)
  const selectedTreeKeys = ref<Array<string>>(['all'])
  const expandedTreeKeys = ref<Array<string>>(['all'])
  const filter = reactive({
    treeKeyword: '',
    tableKeyword: '',
    level1: null as string | null,
    level2: null as string | null,
    moduleId: null as number | string | null,
  })
  const pagination = reactive({
    page: 1,
    pageSize: 20,
  })
  const data = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
    data: [],
    caseList: [],
  })

  function normalizeName(value: any) {
    return String(value || '').trim()
  }

  function displayGroupName(value: string, level: 'level1' | 'level2' = 'level1') {
    if (value) return value
    return level === 'level2' ? '无二级模块' : '未分组'
  }

  function getTreeKey(type: string, value: string, parent = '') {
    return `${type}:${encodeURIComponent(parent || '__empty__')}/${encodeURIComponent(value || '__empty__')}`
  }

  function decodeTreeKeyValue(value: string) {
    const [parent = '__empty__', current = '__empty__'] = value.split('/')
    return {
      parent: decodeURIComponent(parent) === '__empty__' ? '' : decodeURIComponent(parent),
      current: decodeURIComponent(current) === '__empty__' ? '' : decodeURIComponent(current),
    }
  }

  function matchFilterValue(source: string, filterValue: string | null | undefined) {
    if (filterValue === null || typeof filterValue === 'undefined') return true
    return source === filterValue
  }

  const level1Options = computed(() =>
    Array.from(
      new Set((data.data as any[]).map((item) => normalizeName(item.superior_module_1)).filter(Boolean))
    ).map((item) => ({ label: item, value: item }))
  )

  const level2Options = computed(() => {
    const list = (data.data as any[]).filter((item) => {
      return filter.level1 === null || normalizeName(item.superior_module_1) === filter.level1
    })
    return Array.from(new Set(list.map((item) => normalizeName(item.superior_module_2)).filter(Boolean))).map(
      (item) => ({ label: item, value: item })
    )
  })

  const filteredModuleData = computed(() => {
    const keyword = filter.tableKeyword.trim().toLowerCase()
    return (data.data as any[]).filter((item) => {
      const level1 = normalizeName(item.superior_module_1)
      const level2 = normalizeName(item.superior_module_2)
      const name = normalizeName(item.name)
      if (filter.moduleId && String(item.id) !== String(filter.moduleId)) return false
      if (!matchFilterValue(level1, filter.level1)) return false
      if (!matchFilterValue(level2, filter.level2)) return false
      if (!keyword) return true
      return [level1, level2, name].some((text) => text.toLowerCase().includes(keyword))
    })
  })

  const pagedModuleData = computed(() => {
    const start = (pagination.page - 1) * pagination.pageSize
    return filteredModuleData.value.slice(start, start + pagination.pageSize)
  })

  const moduleStats = computed(() => {
    const list = data.data as any[]
    return {
      total: list.length,
      level1: new Set(list.map((item) => normalizeName(item.superior_module_1)).filter(Boolean)).size,
      level2: new Set(
        list
          .map((item) =>
            [normalizeName(item.superior_module_1), normalizeName(item.superior_module_2)]
              .filter(Boolean)
              .join('/')
          )
          .filter(Boolean)
      ).size,
    }
  })

  const treeModuleData = computed(() => {
    const keyword = filter.treeKeyword.trim().toLowerCase()
    if (!keyword) return data.data as any[]
    return (data.data as any[]).filter((item) => {
      const level1 = normalizeName(item.superior_module_1)
      const level2 = normalizeName(item.superior_module_2)
      const name = normalizeName(item.name)
      return [level1, level2, name].some((text) => text.toLowerCase().includes(keyword))
    })
  })

  function buildModuleGroups(list: any[]) {
    const groups = new Map<string, Map<string, any[]>>()
    list.forEach((item: any) => {
      const level1 = normalizeName(item.superior_module_1)
      const level2 = normalizeName(item.superior_module_2)
      if (!groups.has(level1)) groups.set(level1, new Map())
      const second = groups.get(level1)!
      if (!second.has(level2)) second.set(level2, [])
      second.get(level2)!.push(item)
    })
    return groups
  }

  const moduleGroups = computed(() => buildModuleGroups(treeModuleData.value))

  const moduleTree = computed(() => {
    const children = Array.from(moduleGroups.value.entries()).map(([level1, second]) => {
      const moduleCount = Array.from(second.values()).reduce((count, modules) => count + modules.length, 0)
      const level2Children = Array.from(second.entries())
        .filter(([level2]) => level2)
        .map(([level2, modules]) => ({
          key: getTreeKey('level2', level2, level1),
          title: `${displayGroupName(level2, 'level2')} (${modules.length})`,
        }))
      return {
        key: getTreeKey('level1', level1),
        title: `${displayGroupName(level1, 'level1')} (${moduleCount})`,
        children: level2Children.length ? level2Children : undefined,
      }
    })
    return [
      {
        key: 'all',
        title: `全部模块 (${treeModuleData.value.length})`,
        children,
      },
    ]
  })

  const allTreeKeys = computed(() => {
    const keys: string[] = []
    const walk = (nodes: any[]) => {
      nodes.forEach((node) => {
        keys.push(node.key)
        if (node.children?.length) {
          walk(node.children)
        }
      })
    }
    walk(moduleTree.value)
    return keys
  })

  const currentScopeTitle = computed(() => {
    if (filter.level1 !== null && filter.level2 !== null) {
      return `${displayGroupName(filter.level1, 'level1')} / ${displayGroupName(filter.level2, 'level2')}`
    }
    if (filter.level1 !== null) return displayGroupName(filter.level1, 'level1')
    return '全部模块'
  })

  function resetPage() {
    pagination.page = 1
  }

  function resetFilters() {
    filter.treeKeyword = ''
    filter.tableKeyword = ''
    filter.level1 = null
    filter.level2 = null
    filter.moduleId = null
    selectedTreeKeys.value = ['all']
    expandedTreeKeys.value = ['all']
    resetPage()
  }

  function onLevel1Change(value?: string) {
    selectedTreeKeys.value = ['all']
    filter.level1 = typeof value === 'undefined' ? null : value
    filter.level2 = null
    filter.moduleId = null
    resetPage()
  }

  function onLevel2Change(value?: string) {
    selectedTreeKeys.value = ['all']
    filter.level2 = typeof value === 'undefined' ? null : value
    filter.moduleId = null
    resetPage()
  }

  function onTreeSelect(keys: Array<string>) {
    const key = keys[0] || 'all'
    selectedTreeKeys.value = [key]
    filter.tableKeyword = ''
    if (key === 'all') {
      filter.level1 = null
      filter.level2 = null
      filter.moduleId = null
      toggleTreeExpanded()
      resetPage()
      return
    }
    const [type, value = ''] = key.split(':')
    const treeValue = decodeTreeKeyValue(value)
    if (type === 'level1') {
      filter.level1 = treeValue.current
      filter.level2 = null
      filter.moduleId = null
    }
    if (type === 'level2') {
      filter.level1 = treeValue.parent
      filter.level2 = treeValue.current
      filter.moduleId = null
    }
    resetPage()
  }

  function toggleTreeExpanded() {
    const expandableKeys = allTreeKeys.value
    if (expandedTreeKeys.value.length >= expandableKeys.length) {
      expandedTreeKeys.value = ['all']
      return
    }
    expandedTreeKeys.value = expandableKeys
  }

  watch(
    () => filteredModuleData.value.length,
    () => {
      const maxPage = Math.max(1, Math.ceil(filteredModuleData.value.length / pagination.pageSize))
      if (pagination.page > maxPage) {
        pagination.page = maxPage
      }
    }
  )

  watch(
    () => filter.treeKeyword,
    (keyword) => {
      if (keyword.trim()) {
        expandedTreeKeys.value = allTreeKeys.value
      }
    }
  )

  function doAppend() {
    data.actionTitle = '新增'
    data.isAdd = true
    modalDialogRef.value?.toggle()
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = ''
      }
    })
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此模块？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteUserModule(record.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function onUpdate(record: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = record.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = record[it.key]
        if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
        } else {
          it.value = propName
        }
      })
    })
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(formItems)
      value['project_product'] = route.query.id
      if (data.isAdd) {
        postUserModule(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            projectInfo.projectPytestName()
            doRefresh()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      } else {
        value['id'] = data.updateId
        putUserModule(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            projectInfo.projectPytestName()
            doRefresh()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      }
    } else {
      modalDialogRef.value?.setConfirmLoading(false)
    }
  }

  function doResetSearch() {
    window.history.back()
  }

  function doRefresh() {
    tableLoading.value = true
    getUserModule({
      project_product: route.query.id,
    })
      .then((res) => {
        data.data = res.data
        nextTick(() => {
          expandedTreeKeys.value = ['all']
        })
        resetPage()
      })
      .catch(console.log)
      .finally(() => {
        tableLoading.value = false
      })
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
    })
  })
</script>
<style lang="less" scoped>
  .mango-module-workbench {
    display: grid;
    height: 100%;
    min-height: 0;
    padding-top: 8px;
    box-sizing: border-box;
    grid-template-columns: minmax(260px, 320px) minmax(0, 1fr);
    gap: 12px;
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

  .mango-module-sidebar__head,
  .mango-module-main__head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 10px;
  }

  .mango-module-sidebar__head h3,
  .mango-module-main__head h3 {
    margin: 0;
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 20px;
  }

  .mango-module-sidebar__head p,
  .mango-module-main__head p {
    margin: 2px 0 0;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 17px;
  }

  .mango-module-stats {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 10px 0;
  }

  .mango-module-stats span {
    padding: 2px 7px;
    border: 1px solid var(--m-border);
    border-radius: 999px;
    background: var(--m-surface-soft);
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-module-tree {
    flex: 1;
    min-height: 0;
    overflow: auto;
  }

  .mango-module-tree :deep(.arco-tree-node-title) {
    max-width: 220px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-module-filter {
    margin-bottom: 10px;
    padding: 10px 10px 0;
  }

  .mango-module-filter :deep(.arco-form) {
    display: grid;
    grid-template-columns: repeat(3, minmax(160px, 1fr));
    gap: 0 10px;
  }

  .mango-module-filter :deep(.arco-form-item) {
    margin-bottom: 10px;
  }

  .mango-module-table {
    flex: none;
    min-height: 0;
  }

  .mango-module-pagination {
    display: flex;
    flex: none;
    justify-content: flex-end;
    padding-top: 10px;
  }

  @media (max-width: 960px) {
    .mango-module-workbench {
      grid-template-columns: 1fr;
    }

    .mango-module-sidebar {
      min-height: 260px;
    }

    .mango-module-filter :deep(.arco-form) {
      grid-template-columns: 1fr;
    }
  }
</style>
