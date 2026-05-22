<template>
  <div
    :class="[!appStore.isCollapse ? 'mango-open-status' : 'mango-close-status', bgColor]"
    :style="{ borderRadius: '0px' }"
    class="mango-inner-side-bar-wrapper"
  >
    <ScrollerMenu :routes="routes" />
    <div class="mango-humburger-wrapper">
      <Humburger />
    </div>
  </div>
</template>

<script lang="ts">
  import useAppConfigStore from '@/store/modules/app-config'
  import usePermissionStore from '@/store/modules/permission'
  import { SideTheme, ThemeMode } from '@/store/types'
  import { computed, defineComponent, ref, watch } from 'vue'
  import { RouteRecordRaw, useRoute } from 'vue-router'

  export default defineComponent({
    name: 'InnerSideBar',
    setup() {
      const permissionStore = usePermissionStore()
      const appStore = useAppConfigStore()
      const route = useRoute()
      const routes = ref<RouteRecordRaw[]>([])
      const bgColor = computed(() => {
        if (appStore.layoutMode !== 'ttb') {
          if (appStore.sideTheme === SideTheme.IMAGE) {
            return 'sidebar-bg-img'
          } else if (appStore.sideTheme === SideTheme.DARK) {
            return 'sidebar-bg-dark'
          } else {
            return 'sidebar-bg-light'
          }
        } else {
          return appStore.theme === ThemeMode.DARK ? 'sidebar-bg-dark' : 'sidebar-bg-light'
        }
      })
      watch(
        () => route.fullPath,
        () => {
          const firstMatchPath = route.matched[0].path
          const item = permissionStore.getPermissionSideBar.find((it) => it.path === firstMatchPath)
          routes.value = item?.children || []
        },
        {
          immediate: true,
        }
      )
      return {
        appStore,
        permissionStore,
        routes,
        bgColor,
      }
    },
  })
</script>

<style lang="less" scoped>
  .sidebar-bg-img {
    background-image: url('../../assets/bg_img.webp') !important;
    background-size: cover;

    :deep(.mango-logo-wrapper .mango-logo-title) {
      color: var(--m-layout-logo-text) !important;
    }

    :deep(.arco-menu) {
      background-color: transparent !important;
    }

    :deep(.arco-menu-inline-header) {
      background-color: transparent !important;
    }

    :deep(.arco-menu-dark .arco-menu-pop-header) {
      background-color: transparent !important;
    }

    :deep(.arco-menu-item) {
      background-color: transparent !important;
    }

    :deep(.arco-menu-dark .arco-menu-item.arco-menu-selected) {
      color: var(--m-layout-sidebar-active-text);

      & .arco-menu-icon {
        color: var(--m-layout-sidebar-active-text) !important;

        & .arco-icon {
          color: currentColor !important;
        }
      }
    }

    :deep(
        .arco-menu-dark .arco-menu-item:hover,
        .arco-menu-dark .arco-menu-group-title:hover,
        .arco-menu-dark .arco-menu-pop-header:hover,
        .arco-menu-dark .arco-menu-inline-header:hover
      ) {
      color: var(--m-layout-sidebar-active-text) !important;

      & .arco-menu-icon {
        color: var(--m-layout-sidebar-active-text) !important;

        & .arco-icon {
          color: currentColor !important;
        }
      }
    }

    :deep(.arco-menu-dark .arco-menu-inline-header:hover) {
      color: var(--m-layout-sidebar-active-text) !important;

      & .arco-menu-icon {
        color: var(--m-layout-sidebar-active-text) !important;

        & .arco-icon {
          color: currentColor !important;
        }
      }
    }

    :deep(.arco-menu-dark .arco-menu-pop-header:hover) {
      color: var(--m-layout-sidebar-active-text) !important;

      & .arco-menu-icon {
        color: var(--m-layout-sidebar-active-text) !important;

        & .arco-icon {
          color: currentColor !important;
        }
      }
    }
  }

  .sidebar-bg-dark {
    background-color: var(--m-layout-sidebar-bg);

    :deep(.mango-logo-wrapper .mango-logo-title) {
      color: var(--m-layout-logo-text) !important;
    }

    :deep(.arco-menu-dark .arco-menu-item.arco-menu-selected) {
      color: var(--m-layout-sidebar-active-text);
      background-color: var(--m-layout-sidebar-active-bg);

      & .arco-menu-icon {
        color: var(--m-layout-sidebar-active-text) !important;

        & .arco-icon {
          color: currentColor !important;
        }
      }
    }

    :deep(
        .arco-menu-dark .arco-menu-item:hover,
        .arco-menu-dark .arco-menu-group-title:hover,
        .arco-menu-dark .arco-menu-pop-header:hover,
        .arco-menu-dark .arco-menu-inline-header:hover
      ) {
      color: var(--m-layout-sidebar-active-text) !important;
      background-color: var(--m-layout-sidebar-hover-bg);

      & .arco-menu-icon {
        color: var(--m-layout-sidebar-active-text) !important;

        & .arco-icon {
          color: currentColor !important;
        }
      }
    }

    :deep(.arco-menu-dark .arco-menu-inline-header:hover) {
      color: var(--m-layout-sidebar-active-text) !important;

      & .arco-menu-icon {
        color: var(--m-layout-sidebar-active-text) !important;

        & .arco-icon {
          color: currentColor !important;
        }
      }
    }

    :deep(.arco-menu-dark .arco-menu-pop-header:hover) {
      color: var(--m-layout-sidebar-active-text) !important;

      & .arco-menu-icon {
        color: var(--m-layout-sidebar-active-text) !important;

        & .arco-icon {
          color: currentColor !important;
        }
      }
    }
  }

  .sidebar-bg-light {
    background-color: var(--m-layout-sidebar-bg);

    :deep(.arco-menu) {
      color: var(--m-layout-sidebar-text);
      background-color: transparent;
    }

    :deep(.arco-menu-light .arco-menu-item:hover),
    :deep(.arco-menu-light .arco-menu-inline-header:hover) {
      color: var(--m-layout-sidebar-active-text);
      background-color: var(--m-layout-sidebar-hover-bg);
    }

    :deep(.arco-menu-light .arco-menu-item.arco-menu-selected) {
      position: relative;
      color: var(--m-layout-sidebar-active-text);
      background-color: var(--m-layout-sidebar-active-bg);

      &::after {
        position: absolute;
        top: 0;
        right: 0;
        content: '';
        display: block;
        border-radius: 3px;
        width: 3px;
        height: 100%;
        background-color: var(--m-primary);
      }
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

  .mango-inner-side-bar-wrapper {
    position: absolute;
    top: @logoHeight;
    left: 0;
    overflow-x: hidden;
    bottom: 0;
    box-sizing: border-box;
    z-index: 999;

    .mango-menu-wrapper {
      overflow-x: hidden;
      color: var(--m-layout-sidebar-text);
    }

    .mango-humburger-wrapper {
      position: absolute;
      bottom: 5%;
      right: 2%;
      width: 30px;
      height: 30px;
      display: flex;
      justify-content: center;
      align-items: center;
      border-radius: 50%;
      background-color: var(--m-surface-soft);
      color: var(--m-text);
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
      @negativeMenuWidth: calc(@menuWidth * -1);
      transform: translateX(@negativeMenuWidth);
      transition: transform @transitionTime;
      box-shadow: none;
    }
  }
</style>
