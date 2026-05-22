<template>
  <a-card :body-style="{ padding: 0 }" :bordered="false">
    <div class="mango-nav-bar-wrapper">
      <Humburger />
      <Breadcrumb v-if="appStore.deviceType !== 'mobile'" />
      <div style="flex: 1"></div>
      <div class="mango-right-wrapper">
        <ActionItems />
      </div>
      <div class="mango-avatar-wrapper">
        <Project />
      </div>
      <div class="mango-avatar-wrapper">
        <TestEnvironment />
      </div>
      <div class="mango-avatar-wrapper">
        <VAWavatar />
      </div>
    </div>
  </a-card>
</template>

<script lang="ts">
  import useAppConfigStore from '@/store/modules/app-config'
  import { defineComponent } from 'vue'
  import TestEnvironment from '@/layouts/avatar/testing-environment.vue'
  import Project from '@/layouts/avatar/project.vue'
  import VAWavatar from '@/layouts/avatar/index.vue'

  export default defineComponent({
    name: 'NavBar',
    components: { VAWavatar, Project, TestEnvironment },
    setup() {
      const appStore = useAppConfigStore()
      return {
        appStore,
      }
    },
  })
</script>

<style lang="less" scoped>
  .mango-nav-bar-wrapper {
    height: @logoHeight;
    max-height: @logoHeight;
    min-height: @logoHeight;
    overflow: hidden;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    color: var(--m-layout-header-text);
    border-bottom: 1px solid var(--m-layout-header-border);
    background: var(--m-layout-header-bg);

    .mango-avatar-wrapper {
      padding-right: 20px;
      margin-left: 10px;
    }

    .mango-right-wrapper {
      height: 100%;
    }
  }
</style>
