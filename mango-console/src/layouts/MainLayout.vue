<template>
  <div
    :class="[
      { 'mango-main-layout--without-footer': !showFooter },
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
      :class="[
        appStore.theme === 'light' ? 'mango-main-base-light-theme' : 'mango-main-base-dark-theme',
      ]"
      class="mango-main-base-style"
    >
      <section
        :class="[appStore.flexMainHeight ? 'flex-height' : 'min-height']"
        class="mango-main-section"
      >
        <Main />
      </section>
      <section v-if="showFooter" class="mango-footer-wrapper">
        <Footer />
      </section>
      <a-back-top target-container=".mango-main-base-style" />
    </component>
    <a-back-top target-container=".mango-main-layout-container" />
    <AiAssistantWidget />
  </div>
</template>

<script lang="ts">
  import { computed, defineComponent, onBeforeUnmount, onMounted } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { useTitle } from '@vueuse/core'
  import { projectName } from '@/setting'
  import useAppConfigStore from '@/store/modules/app-config'
  import AiAssistantWidget from '@/components/ai/AiAssistantWidget.vue'

  export default defineComponent({
    name: 'MainLayout',
    components: { AiAssistantWidget },
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
      const showFooter = computed(() => route.meta.hideFooter !== true)
      router.afterEach(() => {
        useTitle(projectName + ' | ' + (route.meta.title as string))
      })
      onMounted(() => {
        const mainEl = document.querySelector('.mango-main-section') as HTMLDivElement
        appStore.setMainHeight(mainEl.clientHeight || mainEl.offsetHeight)
        window.addEventListener('wheel', handleTableWheel, { passive: false })
      })
      onBeforeUnmount(() => {
        window.removeEventListener('wheel', handleTableWheel)
      })

      function findScrollableParent(el: HTMLElement | null) {
        let current = el
        while (current) {
          const style = window.getComputedStyle(current)
          if (
            /(auto|scroll)/.test(style.overflowY) &&
            current.scrollHeight > current.clientHeight
          ) {
            return current
          }
          current = current.parentElement
        }
        return null
      }

      function handleTableWheel(event: WheelEvent) {
        if (event.defaultPrevented) return
        if (!event.deltaY || Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return
        const target = event.target
        if (!(target instanceof HTMLElement)) return
        const table = target.closest('.arco-table')
        if (!(table instanceof HTMLElement)) return
        if (table.classList.contains('arco-table-scroll-y')) return

        const scrollParent = findScrollableParent(table.parentElement)
        if (!scrollParent) return
        const maxScrollTop = scrollParent.scrollHeight - scrollParent.clientHeight
        if (maxScrollTop <= 0) return
        const nextScrollTop = Math.min(
          Math.max(scrollParent.scrollTop + event.deltaY, 0),
          maxScrollTop
        )
        if (nextScrollTop === scrollParent.scrollTop) return

        event.preventDefault()
        scrollParent.scrollTop = nextScrollTop
      }
      return {
        appStore,
        showFooter,
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
    min-width: var(--m-workspace-min-width);
  }

  .main-layout-close-status {
    margin-left: @minMenuWidth;
    min-width: var(--m-workspace-min-width);
  }

  .nav-bar-open-status.fixed-nav-bar {
    width: calc(100% - @menuWidth);
    min-width: var(--m-workspace-min-width);
  }

  .nav-bar-close-status.fixed-nav-bar {
    width: calc(100% - @minMenuWidth);
    min-width: var(--m-workspace-min-width);
  }

  .nav-bar-open-status__ttb {
    width: 100%;
    min-width: var(--m-workspace-min-width);
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
      padding: var(--m-layout-padding-block) var(--m-layout-padding-inline)
        var(--m-layout-padding-inline);
    }

    .mango-main-base-light-theme {
      background: linear-gradient(180deg, var(--m-primary-soft), transparent 260px), var(--m-bg);
    }

    .mango-main-base-dark-theme {
      background-color: var(--m-bg);
    }

    .mango-main-section {
      min-width: 0;
      min-height: 0;
      overflow-x: hidden;
      container-type: inline-size;
    }

    .flex-height {
      height: calc(100% - @footerHeight - var(--m-page-inset-block-start));
    }

    .min-height {
      min-height: calc(100% - @footerHeight - var(--m-page-inset-block-start));
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

  .mango-main-layout-container.mango-main-layout--without-footer {
    .flex-height {
      height: calc(100% - var(--m-page-inset-block-start));
    }

    .min-height {
      min-height: calc(100% - var(--m-page-inset-block-start));
    }
  }

  .mango-footer-wrapper {
    margin-top: var(--m-layout-padding-block);
    position: fixed;
    left: calc(var(--menu-width) + var(--m-page-inset-block-start));
    right: var(--m-page-inset-block-start);
    bottom: var(--m-page-inset-block-start);
  }

  .main-layout-close-status .mango-footer-wrapper {
    left: calc(@minMenuWidth + var(--m-layout-padding-block));
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
