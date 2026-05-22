<template>
  <div
    :class="[
      appStore.isCollapse ? 'main-layout-close-status' : 'main-layout-open-status',
      appStore.isFixedNavBar ? 'main-layout_fixed-nav-bar' : 'main-layout',
      !appStore.isFixedNavBar
        ? 'main-layout_padding-top__0'
        : // : isShowTabbar
          // ? 'main-layout_padding-top__all'
          'main-layout_padding-top__logo',
    ]"
    class="mango-main-layout-container mango-scrollbar"
  >
    <section
      :class="[
        appStore.layoutMode == 'ttb'
          ? 'nav-bar-open-status__ttb'
          : !appStore.isCollapse
          ? 'nav-bar-open-status'
          : 'nav-bar-close-status',
        appStore.isFixedNavBar ? 'fixed-nav-bar' : '',
        !showNavBar ? 'tab-bar-top' : '',
      ]"
    >
      <NavBar v-if="showNavBar" />
      <!--      <TabBar v-show="isShowTabbar" />-->
    </section>
    <component
      :is="appStore.isFixedNavBar ? 'Scrollbar' : 'div'"
      :class="[appStore.theme === 'light' ? 'mango-main-base-light-theme' : 'mango-main-base-dark-theme']"
      class="mango-main-base-style"
    >
      <section
        :class="[appStore.flexMainHeight ? 'flex-height' : 'min-height']"
        class="mango-main-section"
      >
        <Main />
      </section>
      <section class="mango-footer-wrapper">
        <Footer />
      </section>
      <a-back-top target-container=".mango-main-base-style" />
    </component>
    <a-back-top target-container=".mango-main-layout-container" />
  </div>
</template>

<script lang="ts">
  import { defineComponent, onMounted } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { useTitle } from '@vueuse/core'
  import { projectName } from '@/setting'
  import useAppConfigStore from '@/store/modules/app-config'

  export default defineComponent({
    name: 'MainLayout',
    props: {
      showNavBar: {
        type: Boolean,
        default: true,
      },
    },
    setup() {
      const appStore = useAppConfigStore()
      // const isShowTabbar = computed(() => true)
      const router = useRouter()
      const route = useRoute()
      router.afterEach(() => {
        useTitle(projectName + ' | ' + (route.meta.title as string))
      })
      onMounted(() => {
        const mainEl = document.querySelector('.mango-main-section') as HTMLDivElement
        appStore.setMainHeight(mainEl.clientHeight || mainEl.offsetHeight)
      })
      return {
        appStore,
        // isShowTabbar,
      }
    },
  })
</script>

<style lang="less" scoped>
  .mango-scrollbar::-webkit-scrollbar {
    width: 0;
  }

  .main-layout-open-status {
    margin-left: @menuWidth;
  }

  .main-layout-close-status {
    margin-left: @minMenuWidth;
  }

  .nav-bar-open-status.fixed-nav-bar {
    width: calc(100% - @menuWidth);
  }

  .nav-bar-close-status.fixed-nav-bar {
    width: calc(100% - @minMenuWidth);
  }

  .nav-bar-open-status__ttb {
    width: 100%;
  }

  :deep(.mango-main-base-style .mango-scrollbar__view) {
    height: 100%;
  }

  .main-layout {
    overflow-y: auto;
  }

  .main-layout_fixed-nav-bar {
    overflow-y: hidden;

    .mango-main-base-style {
      overflow-y: auto;
    }
  }

  .main-layout_padding-top__0 {
    padding-top: 0;
  }

  .main-layout_padding-top__all {
    padding-top: calc(@logoHeight + @tabHeight);
  }

  .main-layout_padding-top__logo {
    padding-top: @logoHeight;
  }

  .mango-main-layout-container {
    height: 100%;
    box-sizing: border-box;
    transition: margin-left @transitionTime;

    .mango-main-base-style {
      height: 100%;
      box-sizing: border-box;
      padding: 6px 8px 8px;
    }

    .mango-main-base-light-theme {
      background: linear-gradient(180deg, var(--m-primary-soft), transparent 260px), var(--m-bg);
    }

    .mango-main-base-dark-theme {
      background-color: var(--m-bg);
    }

    .mango-main-section {
      overflow-x: hidden;
    }

    .flex-height {
      height: calc(100% - @footerHeight - 10px);
    }

    .min-height {
      min-height: calc(100% - @footerHeight - 10px);
    }

    .fixed-nav-bar {
      position: fixed;
      top: 0;
      transition: width @transitionTime;
      z-index: 99;
    }

    .tab-bar-top {
      padding-top: @logoHeight;
    }
  }

  .mango-footer-wrapper {
    margin-top: 6px;
    position: fixed;
    left: 215px;
    right: 5px;
    bottom: 5px;
  }

  .mango-is-mobile {
    .main-layout-open-status,
    .main-layout-close-status {
      margin-left: 0;
      transition: none;
    }

    .nav-bar-open-status,
    .nav-bar-close-status {
      width: 100%;
    }
  }
</style>
