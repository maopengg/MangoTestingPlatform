<template>
  <div
    :class="[!appStore.isCollapse ? 'mango-open-status' : 'mango-close-status', bgColor]"
    class="mango-tab-split-side-bar-wrapper"
  >
    <div class="mango-tab-split-tab-wrapper">
      <Logo :show-title="false" class="mango-tab-split-logo-wrapper" />
      <Scrollbar class="mango-tab-split-scrollbar-wrapper">
        <div class="mango-tab-split-content-wrapper">
          <div
            v-for="item of tabs"
            :key="item.fullPath"
            :class="{ 'mango-tab-split-item-is-active': item.checked.value }"
            class="mango-label-item-wrapper"
            @click="changeTab(item)"
          >
            <component :is="item.icon || 'icon-menu'" style="font-size: 18px" />
            <span class="mango-tab-split-title">{{ item.label }}</span>
          </div>
        </div>
      </Scrollbar>
    </div>
    <div class="mango-tab-split-menu-wrapper">
      <Logo :show-logo="false" class="mango-tab-split-logo-wrapper" />
      <ScrollerMenu :routes="routes" />
    </div>
  </div>
</template>

<script lang="ts">
  import { computed, defineComponent, onMounted, ref, shallowReactive, watch } from 'vue'
  import { RouteLocationNormalizedLoaded, RouteRecordRaw, useRoute, useRouter } from 'vue-router'
  import { isExternal } from '../../utils'
  import { IconMenu } from '@arco-design/web-vue/es/icon'
  import usePermissionStore from '@/store/modules/permission'
  import useAppConfigStore from '@/store/modules/app-config'
  import { transformSplitTabMenu } from '@/store/help'
  import { SideTheme, SplitTab } from '@/store/types'

  export default defineComponent({
    name: 'TabSplitSideBar',
    components: { IconMenu },
    props: {
      showLogo: {
        type: Boolean,
        default: true,
      },
    },
    setup() {
      const appStore = useAppConfigStore()
      const permissionStore = usePermissionStore()
      const tabs = shallowReactive<Array<SplitTab>>([])
      const routes = shallowReactive<Array<RouteRecordRaw>>([])
      const route = useRoute()
      const router = useRouter()
      watch(
        () => route.fullPath,
        () => {
          doChangeTab(route)
        }
      )
      onMounted(() => {
        tabs.length = 0
        tabs.push(...transformSplitTabMenu(permissionStore.getPermissionSplitTabs))
        doChangeTab(route)
      })

      function doChangeTab(route: RouteLocationNormalizedLoaded) {
        const matchedRoutes = route.matched
        if (matchedRoutes && matchedRoutes.length > 0) {
          tabs.forEach((it) => {
            if (it.fullPath === matchedRoutes[0].path) {
              it.checked.value = true
              if (it.children) {
                routes.length = 0
                routes.push(...(it.children as Array<RouteRecordRaw>))
              }
            } else {
              it.checked.value = false
            }
          })
        }
      }

      function changeTab(item: SplitTab) {
        tabs.forEach((it) => {
          it.checked.value = it.fullPath === item.fullPath
        })
        findPath(item)
      }

      function findPath(item: SplitTab) {
        if (item.children && item.children.length > 0) {
          const firstItem = item.children[0]
          if (firstItem.children && firstItem.children.length > 0) {
            findPath({
              label: firstItem.meta?.title,
              iconPrefix: firstItem.meta?.iconPrefix,
              icon: firstItem.meta?.icon,
              fullPath: firstItem.path,
              children: firstItem.children,
              checked: ref(false),
            } as SplitTab)
          } else {
            if (isExternal(firstItem.path as string)) {
              routes.length = 0
              routes.push(...(item.children as Array<RouteRecordRaw>))
              window.open(firstItem.path)
            } else {
              router.push(firstItem.path || '/').then((error) => {
                if (error) {
                  if (firstItem.path === route.path || firstItem.path === route.fullPath) {
                    routes.length = 0
                    routes.push(...(item.children as Array<RouteRecordRaw>))
                  }
                }
              })
            }
          }
        }
      }

      const bgColor = computed(() => {
        if (appStore.sideTheme === SideTheme.IMAGE) {
          return 'sidebar-bg-img'
        } else if (appStore.sideTheme === SideTheme.DARK) {
          return 'sidebar-bg-dark'
        } else {
          return 'sidebar-bg-light'
        }
      })
      return {
        appStore,
        tabs,
        routes,
        changeTab,
        findPath,
        bgColor,
      }
    },
  })
</script>

<style>
  .mango-tab-split-scrollbar-wrapper {
    height: calc(100% - 48px) !important;
  }
</style>

<style lang="less" scoped>
  .sidebar-bg-img {
    background-image: url('../../assets/bg_img.webp') !important;
    background-size: cover;

    :deep(.ant-menu) {
      background: transparent !important;
    }

    :deep(.mango-logo-wrapper .mango-logo-title) {
      color: var(--m-layout-logo-text) !important;
    }

    .mango-tab-split-tab-wrapper {
      .mango-label-item-wrapper {
        color: var(--m-layout-sidebar-text);
      }
    }
  }

  .sidebar-bg-dark {
    :deep(.mango-logo-wrapper .mango-logo-title) {
      color: var(--m-layout-logo-text) !important;
    }

    .mango-tab-split-tab-wrapper {
      background-color: var(--m-layout-sidebar-bg);

      .mango-label-item-wrapper {
        color: var(--m-layout-sidebar-text);
      }
    }
  }

  .sidebar-bg-light {
    background-color: var(--m-layout-sidebar-bg);

    .mango-tab-split-tab-wrapper {
      background-color: var(--m-layout-sidebar-bg);

      .mango-label-item-wrapper {
        color: var(--m-layout-sidebar-text);
      }

      .mango-tab-split-item-is-active {
        color: var(--m-layout-sidebar-active-text);
      }
    }
  }

  .light .sidebar-bg-dark {
    background-color: var(--m-layout-sidebar-bg);
  }

  .dark .sidebar-bg-dark {
    :deep(.ant-menu) {
      background: transparent !important;
    }
  }

  .mango-open-status {
    width: @menuWidth;
    box-shadow: var(--m-shadow);
    transition: all @transitionTime;
  }

  .mango-close-status {
    width: @minMenuWidth;
    box-shadow: none;
    transition: all @transitionTime;
  }

  .mango-tab-split-side-bar-wrapper {
    position: fixed;
    top: 0;
    left: 0;
    overflow: hidden;
    height: 100vh;
    box-sizing: border-box;
    z-index: 999;

    .mango-tab-split-tab-wrapper {
      position: relative;
      top: 0;
      left: 0;
      width: @tabSplitMenuWidth;
      min-width: @tabSplitMenuWidth;
      max-width: @tabSplitMenuWidth;
      overflow: hidden;
      height: 100vh;
      box-sizing: border-box;

      .mango-tab-split-logo-wrapper {
        max-width: @tabSplitMenuWidth;
        min-width: @tabSplitMenuWidth;
      }

      .mango-tab-split-content-wrapper {
        position: relative;

        .after {
          content: '';
          position: absolute;
          left: 5px;
          top: 5px;
          right: 5px;
          bottom: 5px;
          border-radius: 3px;
          z-index: -1;
        }

        .mango-label-item-wrapper {
          position: relative;
          min-height: @logoHeight * 1.2;
          padding: 10px 0;
          display: flex;
          flex-direction: column;
          overflow: hidden;
          align-items: center;
          justify-content: center;
          box-sizing: border-box;
          z-index: 1;

          .mango-tab-split-title {
            display: inline-block;
            width: 80%;
            margin: 0 auto;
            overflow: hidden;
            text-overflow: ellipsis;
            text-align: center;
            font-size: 12px;
            line-height: 14px;
            margin-top: 5px;
          }

          &:hover {
            cursor: pointer;
          }

          &::after {
            .after;
          }
        }

        .mango-label-item-wrapper:hover::after {
          background-color: var(--m-layout-sidebar-hover-bg);
        }

        .mango-tab-split-item-is-active::after {
          background-color: var(--m-layout-sidebar-active-bg);
          .after;
        }
      }
    }

    .mango-tab-split-menu-wrapper {
      position: absolute;
      top: 0;
      right: 0;
      bottom: 0;
      left: @tabSplitMenuWidth;
      overflow-x: hidden;
    }

    .mango-menu-wrapper {
      overflow-x: hidden;
      color: var(--m-layout-sidebar-text);
    }
  }

  .mango-is-mobile {
    .mango-open-status {
      width: @menuWidth;
      transform: translateX(0);
      transition: transform @transitionTime;
    }

    .mango-close-status {
      width: @menuWidth;
      transform: translateX(calc(@menuWidth * -1));
      transition: transform @transitionTime;
      box-shadow: none;
    }
  }
</style>
