<template>
  <a-breadcrumb class="mango-breadcrumb">
    <a-breadcrumb-item v-for="(item, index) of breadcrumbs" :key="item.key">
      <button
        v-if="item.path && index < breadcrumbs.length - 1"
        class="mango-breadcrumb-link"
        type="button"
        @click="handleSelect(item.path)"
      >
        {{ item.label }}
      </button>
      <span v-else class="mango-breadcrumb-text">{{ item.label }}</span>
    </a-breadcrumb-item>
  </a-breadcrumb>
</template>

<script lang="ts">
  import { defineComponent, onMounted, reactive, watch } from 'vue'
  import { useRoute, useRouter } from 'vue-router'

  interface DropItem {
    label: string
    key: string
    path?: string
  }

  interface BreadcrumbMetaItem {
    title: string
    path?: string
  }

  export default defineComponent({
    name: 'Breadcrumb',
    setup() {
      const breadcrumbs = reactive<Array<DropItem>>([])
      const route = useRoute()
      const router = useRouter()

      function generatorBreadcrumb() {
        breadcrumbs.length = 0
        const matchedPath: DropItem[] = []
        route.matched.forEach((it, index) => {
          const label = (it.meta ? it.meta.title || '' : '') as string
          if (!label) return
          const isLastMatched = index === route.matched.length - 1
          matchedPath.push({
            label,
            key: it.path,
          })
        })
        const currentRoute = route.matched[route.matched.length - 1]
        const extraBreadcrumb = (currentRoute?.meta?.breadcrumb || []) as BreadcrumbMetaItem[]
        const lastItem = matchedPath.pop()
        extraBreadcrumb.forEach((item) => {
          if (!item.title) return
          matchedPath.push({
            label: item.title,
            key: item.path || item.title,
            path: item.path,
          })
        })
        if (lastItem) {
          matchedPath.push({
            ...lastItem,
            path: undefined,
          })
        }
        breadcrumbs.push(
          ...matchedPath.filter((item, index, array) => {
            return item.label && array.findIndex((it) => it.key === item.key) === index
          })
        )
      }

      function handleSelect(path: string) {
        if (!path || path === route.path) return
        router.push(path)
      }

      onMounted(() => {
        generatorBreadcrumb()
      })
      watch(
        () => route.fullPath,
        () => {
          if (
            route.path.startsWith('/redirect') ||
            ['/login', '/404', '/405', '/403'].includes(route.path)
          )
            return
          generatorBreadcrumb()
        }
      )
      return {
        breadcrumbs,
        handleSelect,
      }
    },
  })
</script>

<style lang="less" scoped>
  .mango-breadcrumb {
    display: flex;
    align-items: center;
  }

  .mango-breadcrumb-link {
    padding: 0;
    border: 0;
    background: transparent;
    color: var(--m-muted);
    cursor: pointer;
    font: inherit;
    line-height: inherit;
  }

  .mango-breadcrumb-link:hover {
    color: var(--m-primary);
  }

  .mango-breadcrumb-text {
    color: var(--m-text);
  }
</style>
