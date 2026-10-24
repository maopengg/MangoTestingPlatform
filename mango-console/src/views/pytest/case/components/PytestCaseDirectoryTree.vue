<template>
  <div ref="treeContainerRef" class="mango-pytest-directory-tree">
    <a-input-search v-model="keyword" allow-clear size="small" placeholder="搜索仓库、目录或文件" />
    <div class="mango-pytest-directory-tree__header">
      <span>代码目录</span>
      <a-space size="mini">
        <slot name="actions"></slot>
        <a-button type="text" size="mini" @click="toggleExpansion">
          {{ expandedKeys.length ? '收起' : '定位' }}
        </a-button>
      </a-space>
    </div>
    <mango-panel-spin :loading="loading" class="mango-pytest-directory-tree__spin">
      <a-tree
        v-if="displayTree.length"
        :expanded-keys="expandedKeys"
        :data="displayTree"
        :selected-keys="selectedKey ? [selectedKey] : []"
        block-node
        size="small"
        @expand="onExpand"
        @select="onSelect"
      >
        <template #title="nodeData">
          <span
            class="mango-pytest-directory-tree__node"
            :class="{
              'mango-pytest-directory-tree__node--selected': isSelected(nodeData.key),
            }"
            :aria-current="isSelected(nodeData.key) ? 'true' : undefined"
          >
            <span
              class="mango-pytest-directory-tree__type"
              :class="`mango-pytest-directory-tree__type--${nodeData.type}`"
            >
              <icon-storage v-if="nodeData.type === 'repository'" />
              <icon-apps v-else-if="nodeData.type === 'project'" />
              <icon-folder v-else-if="nodeData.type === 'directory'" />
              <span v-else>PY</span>
            </span>
            <span class="mango-pytest-directory-tree__name" :title="nodeData.title">
              {{ nodeData.title }}
            </span>
            <span
              v-if="nodeData.type === 'file' && fileStateLabel(nodeData)"
              class="mango-pytest-directory-tree__state"
              :class="`mango-pytest-directory-tree__state--${fileStateTone(nodeData)}`"
            >
              {{ fileStateLabel(nodeData) }}
            </span>
            <span v-if="nodeCount(nodeData)" class="mango-pytest-directory-tree__count">
              {{ nodeCount(nodeData) }}
            </span>
          </span>
        </template>
      </a-tree>
      <div v-else-if="!loading" class="mango-empty-state">暂无匹配目录</div>
    </mango-panel-spin>
  </div>
</template>

<script lang="ts" setup>
  import { computed, nextTick, ref, watch } from 'vue'

  export type PytestDirectoryNode = {
    key: string
    case_id?: number
    title: string
    type: 'repository' | 'project' | 'directory' | 'file'
    path: string
    breadcrumb: string[]
    repository_id: number | null
    pytest_project_id?: number
    case_count: number
    count?: number
    source_status?: number
    asset_status?: number
    children?: PytestDirectoryNode[]
  }

  const props = withDefaults(
    defineProps<{
      data?: PytestDirectoryNode[]
      loading?: boolean
      selectedKey?: string
      expandSelected?: boolean
    }>(),
    {
      data: () => [],
      loading: false,
      selectedKey: '',
      expandSelected: false,
    }
  )
  const emit = defineEmits<{
    (event: 'select', node: PytestDirectoryNode | null): void
    (event: 'directory-toggle', node: PytestDirectoryNode): void
  }>()

  const keyword = ref('')
  const expandedKeys = ref<string[]>([])
  const treeContainerRef = ref<HTMLElement | null>(null)

  function filterNodes(nodes: PytestDirectoryNode[], search: string): PytestDirectoryNode[] {
    return nodes.reduce<PytestDirectoryNode[]>((result, node) => {
      const children = filterNodes(node.children || [], search)
      if (node.title.toLocaleLowerCase().includes(search) || children.length) {
        result.push({ ...node, children })
      }
      return result
    }, [])
  }

  const displayTree = computed(() => {
    const search = keyword.value.trim().toLocaleLowerCase()
    return search ? filterNodes(props.data, search) : props.data
  })

  function collectExpandableKeys(nodes: PytestDirectoryNode[]): string[] {
    return nodes.flatMap((node) => [
      ...((node.children || []).length ? [node.key] : []),
      ...collectExpandableKeys(node.children || []),
    ])
  }

  function findNode(nodes: PytestDirectoryNode[], key: string): PytestDirectoryNode | null {
    for (const node of nodes) {
      if (node.key === key) return node
      const child = findNode(node.children || [], key)
      if (child) return child
    }
    return null
  }

  function findAncestorKeys(
    nodes: PytestDirectoryNode[],
    key: string,
    ancestors: string[] = []
  ): string[] | null {
    for (const node of nodes) {
      if (node.key === key) return ancestors
      const childAncestors = findAncestorKeys(node.children || [], key, [...ancestors, node.key])
      if (childAncestors) return childAncestors
    }
    return null
  }

  function isSelected(key: string) {
    return Boolean(props.selectedKey) && key === props.selectedKey
  }

  function nodeCount(node: PytestDirectoryNode) {
    return Number(node.count ?? node.case_count ?? 0)
  }

  function fileStateLabel(node: PytestDirectoryNode) {
    const sourceLabels: Record<number, string> = { 1: '已更新', 2: '缺失', 3: '解析失败', 4: '冲突' }
    const assetLabels: Record<number, string> = { 2: '停用', 3: '归档', 4: '忽略' }
    return sourceLabels[Number(node.source_status)] || assetLabels[Number(node.asset_status)] || ''
  }

  function fileStateTone(node: PytestDirectoryNode) {
    if ([2, 3, 4].includes(Number(node.source_status))) return 'danger'
    if ([2, 3, 4].includes(Number(node.asset_status))) return 'muted'
    return 'warning'
  }

  function revealSelectedNode() {
    const targetKey = props.selectedKey
    if (!targetKey) {
      if (!keyword.value.trim()) expandedKeys.value = []
      return
    }
    const ancestors = findAncestorKeys(props.data, targetKey) || []
    const selectedNode = findNode(props.data, targetKey)
    const selectedExpansion =
      props.expandSelected && (selectedNode?.children || []).length ? [targetKey] : []
    expandedKeys.value = keyword.value.trim()
      ? Array.from(new Set([...expandedKeys.value, ...ancestors, ...selectedExpansion]))
      : [...ancestors, ...selectedExpansion]
    nextTick(() => {
      const selectedNode = treeContainerRef.value?.querySelector(
        '.mango-pytest-directory-tree__node--selected'
      )
      if (!selectedNode) return
      const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
      selectedNode.scrollIntoView({ block: 'nearest', behavior: reduceMotion ? 'auto' : 'smooth' })
    })
  }

  function onSelect(keys: string[]) {
    const key = keys[0]
    if (!key) return
    const node = findNode(props.data, key)
    if (!node) return
    if (node.type !== 'file') {
      toggleDirectory(node)
      emit('directory-toggle', node)
      return
    }
    emit('select', node)
  }

  function toggleDirectory(node: PytestDirectoryNode) {
    const targetKey = String(node.key)
    const isExpanded = expandedKeys.value.includes(targetKey)
    if (keyword.value.trim()) {
      expandedKeys.value = isExpanded
        ? expandedKeys.value.filter((key) => key !== targetKey)
        : Array.from(new Set([...expandedKeys.value, targetKey]))
      return
    }
    const ancestors = findAncestorKeys(props.data, targetKey) || []
    expandedKeys.value = isExpanded ? ancestors : [...ancestors, targetKey]
  }

  function onExpand(
    keys: Array<string | number>,
    event: { expanded?: boolean; node?: PytestDirectoryNode }
  ) {
    if (keyword.value.trim()) {
      expandedKeys.value = keys.map(String)
      return
    }
    const targetKey = String(event.node?.key || '')
    if (!targetKey) return
    const ancestors = findAncestorKeys(props.data, targetKey) || []
    expandedKeys.value = event.expanded ? [...ancestors, targetKey] : ancestors
  }

  function toggleExpansion() {
    if (expandedKeys.value.length) {
      expandedKeys.value = []
      return
    }
    revealSelectedNode()
  }

  watch(keyword, (value) => {
    if (value.trim()) {
      expandedKeys.value = collectExpandableKeys(displayTree.value)
      revealSelectedNode()
    } else {
      revealSelectedNode()
    }
  })

  watch(
    () => props.data,
    () => {
      revealSelectedNode()
    },
    { immediate: true }
  )

  watch(() => props.selectedKey, revealSelectedNode)
</script>

<style lang="less" scoped>
  .mango-pytest-directory-tree {
    display: flex;
    height: 100%;
    min-height: 0;
    flex-direction: column;
    gap: 8px;
  }

  .mango-pytest-directory-tree__header {
    display: flex;
    min-height: 26px;
    align-items: center;
    justify-content: space-between;
    padding: 0 4px;
    color: var(--m-muted);
    font-size: 11px;
    font-weight: 600;
  }

  .mango-pytest-directory-tree__spin {
    min-height: 0;
    flex: 1;
    overflow: auto;

    :deep(> .mango-panel-spin__content) {
      min-height: 100%;
    }

    :deep(.arco-tree) {
      min-width: 100%;
      width: max-content;
    }
  }

  .mango-pytest-directory-tree__node {
    position: relative;
    display: flex;
    width: 100%;
    min-width: 0;
    min-height: 28px;
    align-items: center;
    gap: 6px;
    padding: 3px 7px;
    border-radius: var(--m-radius-sm);
    cursor: pointer;
    transition: color 0.16s ease, background-color 0.16s ease;
  }

  .mango-pytest-directory-tree__node:hover {
    background: var(--m-surface-soft);
  }

  .mango-pytest-directory-tree__node--selected,
  .mango-pytest-directory-tree__node--selected:hover {
    color: var(--m-primary);
    background: var(--m-primary-soft);
    box-shadow: inset 3px 0 0 var(--m-primary);
  }

  .mango-pytest-directory-tree__node--selected .mango-pytest-directory-tree__name {
    color: var(--m-primary);
    font-weight: 600;
  }

  .mango-pytest-directory-tree__type {
    display: inline-flex;
    width: 20px;
    height: 18px;
    align-items: center;
    justify-content: center;
    flex: 0 0 auto;
    border-radius: var(--m-radius-sm);
    color: var(--m-text-2);
    background: var(--m-surface-soft);
    font-size: 9px;
    font-weight: 700;
  }

  .mango-pytest-directory-tree__type :deep(svg) {
    width: 13px;
    height: 13px;
  }

  .mango-pytest-directory-tree__type--repository {
    color: var(--m-primary);
    background: var(--m-primary-soft);
  }

  .mango-pytest-directory-tree__type--project {
    color: var(--m-primary);
    background: var(--m-primary-soft);
  }

  .mango-pytest-directory-tree__type--file {
    color: var(--m-success);
    background: color-mix(in srgb, var(--m-success) 10%, var(--m-surface));
  }

  .mango-pytest-directory-tree__name {
    min-width: 0;
    max-width: 170px;
    overflow: hidden;
    color: var(--m-text-2);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-pytest-directory-tree__count {
    min-width: 18px;
    margin-left: auto;
    padding: 0 5px;
    border-radius: 9px;
    color: var(--m-muted);
    background: var(--m-fill-2);
    font-size: 10px;
    line-height: 18px;
    text-align: center;
  }

  .mango-pytest-directory-tree__state {
    flex: 0 0 auto;
    padding: 1px 4px;
    border-radius: var(--m-radius-sm);
    font-size: 9px;
    line-height: 16px;
  }

  .mango-pytest-directory-tree__state--danger {
    color: var(--m-danger);
    background: color-mix(in srgb, var(--m-danger) 10%, var(--m-surface));
  }

  .mango-pytest-directory-tree__state--warning {
    color: var(--m-warning);
    background: color-mix(in srgb, var(--m-warning) 10%, var(--m-surface));
  }

  .mango-pytest-directory-tree__state--muted {
    color: var(--m-muted);
    background: var(--m-fill-2);
  }

  .mango-pytest-directory-tree__node--selected .mango-pytest-directory-tree__count {
    color: var(--m-primary);
    background: var(--m-surface);
  }

  :deep(.arco-tree-node-title) {
    padding: 0;
    background: transparent;
  }

  :deep(.arco-tree-node-title-text) {
    display: flex;
    min-width: 0;
    flex: 1;
  }

  :deep(.arco-tree-node-title:hover) {
    background: transparent;
  }

  :deep(.arco-tree-node-selected .arco-tree-node-title) {
    background: transparent;
  }

  :deep(.arco-tree-node-title:focus-visible) {
    outline: 2px solid var(--m-primary);
    outline-offset: 1px;
  }

  @media (prefers-reduced-motion: reduce) {
    .mango-pytest-directory-tree__node {
      transition: none;
    }
  }
</style>
