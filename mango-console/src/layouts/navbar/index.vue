<template>
  <a-card :body-style="{ padding: 0 }" :bordered="false">
    <div class="vaw-nav-bar-wrapper">
      <Humburger />
      <Breadcrumb v-if="appStore.deviceType !== 'mobile'" />
      <div style="flex: 1"></div>
      <div class="right-wrapper">
        <ActionItems />
      </div>
      <div class="avatar-wrapper">
        <Project />
      </div>
      <div class="avatar-wrapper">
        <TestEnvironment />
      </div>
      <div class="avatar-wrapper">
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
  .vaw-nav-bar-wrapper {
    height: @logoHeight;
    max-height: @logoHeight;
    min-height: @logoHeight;
    overflow: hidden;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    border-bottom: 1px solid var(--color-border);

    .avatar-wrapper {
      padding-right: 20px;
      margin-left: 10px;
    }

    .right-wrapper {
      height: 100%;
    }
  }
</style>
