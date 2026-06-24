<template>
  <div class="mango-avatar-container">
    <a-cascader
      :model-value="project.scopeValue"
      :options="scopeOptions"
      :style="{ width: '190px' }"
      allow-clear
      allow-search
      :bordered="false"
      check-strictly
      class="mango-project-scope"
      placeholder="选择项目/产品"
      @change="handleSelect"
    />
  </div>
</template>

<script lang="ts" setup>
  import { computed, onMounted } from 'vue'
  import { useProject } from '@/store/modules/get-project'
  import { useDebounceFn } from '@vueuse/core'
  import { useRoute, useRouter } from 'vue-router'
  import { useProductModule } from '@/store/modules/project_module'

  const project = useProject()
  const productModule = useProductModule()

  const router = useRouter()
  const route = useRoute()

  const scopeOptions = computed(() => {
    return (project.projectProduct || []).map((item: any) => ({
      value: `project:${item.value}`,
      label: item.label,
      raw_id: item.value,
      node_type: 'project',
      children: (item.children || []).map((child: any) => ({
        value: `project_product:${child.value}`,
        label: child.label,
        raw_id: child.value,
        node_type: 'project_product',
        full_title: `${item.label} / ${child.label}`,
      })),
    }))
  })

  function findScopeNode(options: any[], value: string): any {
    for (const item of options) {
      if (item.value === value) return item
      const child = findScopeNode(item.children || [], value)
      if (child) return child
    }
    return null
  }

  function handleSelect(value: any) {
    if (!value) {
      project.clearScope()
      productModule.getProjectModule().finally(() => {
        debouncedFn()
      })
      return
    }
    const node = findScopeNode(scopeOptions.value, String(value))
    if (!node) {
      project.clearScope()
      return
    }
    project.setScope({
      type: node.node_type,
      id: Number(node.raw_id),
      value: node.value,
      title: node.full_title || node.label,
    })
    const moduleProjectProductId = project.scopeType === 'project_product' ? project.scopeId : null
    productModule.getProjectModule(moduleProjectProductId).finally(() => {
      debouncedFn()
    })
  }

  const debouncedFn = useDebounceFn(() => {
    router.replace({ path: '/redirect' + route.path, query: route.query })
  }, 200)

  onMounted(async () => {
    project.projectProductName()
    project.projectPytestName()
  })
</script>

<style lang="less" scoped>
  .mango-avatar-container {
    min-width: 190px;
    height: 100%;
    display: flex;
    align-items: center;
  }

  .mango-project-scope {
    height: 100%;

    :deep(.arco-select-view-single) {
      height: 100%;
      color: var(--m-layout-header-text);
      background: transparent;
      border: 0;
      box-shadow: none;
      cursor: pointer;
      transition: color 0.2s ease, background-color 0.2s ease;
    }

    :deep(.arco-select-view-single:hover),
    :deep(.arco-select-view-opened) {
      color: var(--m-layout-sidebar-active-text);
      background-color: var(--m-layout-sidebar-hover-bg);
    }

    :deep(.arco-select-view-value),
    :deep(.arco-select-view-input),
    :deep(.arco-select-view-placeholder) {
      color: inherit;
      font-size: 14px;
    }

    :deep(.arco-select-view-value) {
      padding-left: 10px;
    }

    :deep(.arco-select-view-input) {
      cursor: pointer;
    }

    :deep(.arco-select-view-icon) {
      color: inherit;
    }

    :deep(.arco-select-view-clear-btn) {
      color: inherit;
    }
  }
</style>
