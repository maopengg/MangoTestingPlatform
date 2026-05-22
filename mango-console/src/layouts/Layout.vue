<template>
  <div
    :class="[appStore.deviceType === 'mobile' && 'mango-is-mobile', appStore.theme]"
    class="mango-layout-container"
  >
    <template v-if="appStore.layoutMode === 'ttb'">
      <VAWHeader />
      <InnerSideBar />
      <MainLayout :show-nav-bar="false" />
    </template>
    <template v-else-if="appStore.layoutMode === 'lcr'">
      <TabSplitSideBar />
      <MainLayout />
    </template>
    <template v-else>
      <SideBar />
      <MainLayout />
    </template>
    <div
      v-if="appStore.deviceType === 'mobile'"
      :class="[appStore.isCollapse ? 'mango-close-shadow' : 'mango-show-shadow']"
      class="mango-mobile-shadow"
      @click="closeMenu"
    ></div>
  </div>
  <Setting ref="settingRef" />
  <SearchContent ref="searchContentRef" />
</template>

<script lang="ts">
  import { defineComponent, onBeforeUnmount, onMounted, ref } from 'vue'
  import useEmit from '@/hooks/useEmit'
  import { AxiosResponse } from 'axios'
  import UserTokenExpiredInterceptor from '@/api/interceptors/UserTokenExpiredInterceptor'
  import useAxios from '@/hooks/useAxios'
  import useAppConfigStore from '@/store/modules/app-config'
  import { useChangeMenuWidth } from '@/hooks/useMenuWidth'
  import { DeviceType } from '@/store/types'
  import CustomRequestInterceptor from '@/api/interceptors/CustomRequestInterceptor'

  export default defineComponent({
    name: 'Layout',
    setup() {
      const settingRef = ref()
      const searchContentRef = ref()
      const appStore = useAppConfigStore()
      useChangeMenuWidth(appStore.sideWidth)
      appStore.applyCurrentThemePreset()
      const emitter = useEmit()
      const axios = useAxios()
      axios.interceptors.request.use((config) => {
        return CustomRequestInterceptor(config)
      })
      axios.interceptors.response.use((response: AxiosResponse): AxiosResponse => {
        return UserTokenExpiredInterceptor(response)
      })
      emitter?.on('show-setting', () => {
        settingRef.value?.openDrawer()
      })
      emitter?.on('show-search', () => {
        searchContentRef.value?.show()
      })
      onMounted(() => {
        handleScreenResize()
        window.addEventListener('resize', handleScreenResize)
      })
      onBeforeUnmount(() => {
        window.removeEventListener('resize', handleScreenResize)
      })

      function handleScreenResize() {
        const width = document.body.clientWidth
        if (width <= 768) {
          appStore.changeDevice(DeviceType.MOBILE)
          appStore.toggleCollapse(true)
        } else if (width < 992 && width > 768) {
          appStore.changeDevice(DeviceType.PAD)
          appStore.toggleCollapse(true)
        } else if (width < 1200 && width >= 992) {
          appStore.changeDevice(DeviceType.PC)
          appStore.toggleCollapse(false)
        } else {
          appStore.changeDevice(DeviceType.PC)
          appStore.toggleCollapse(false)
        }
      }

      function closeMenu() {
        appStore.toggleCollapse(true)
      }

      return {
        settingRef,
        searchContentRef,
        appStore,
        closeMenu,
      }
    },
  })
</script>

<style lang="less">
  .mango-layout-container {
    height: 100%;
    max-width: 100%;
    position: relative;
    overflow-x: hidden;

    .mango-mobile-shadow {
      display: none;
    }

    .mango-layout-mode-ttb {
      margin-top: @logoHeight;
      transition: all @transitionTime;
    }
  }

  .mango-is-mobile {
    .mango-mobile-shadow {
      background-color: var(--m-overlay-mask);
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      z-index: 997;
    }

    .mango-close-shadow {
      display: none;
    }

    .mango-show-shadow {
      display: block;
      opacity: 0.5;
      transition: all @transitionTime;
    }
  }
</style>
