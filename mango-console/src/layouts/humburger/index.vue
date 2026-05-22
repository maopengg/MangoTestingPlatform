<template>
  <span
    :class="[appStore.isCollapse ? 'mango-fold-open-status' : 'mango-fold-close-status']"
    class="mango-fold-wrapper"
    @click="toggleFold"
  >
    <MenuFoldOutlined />
  </span>
</template>

<script lang="ts">
  import { defineComponent } from 'vue'
  import { IconMenuFold as MenuFoldOutlined } from '@arco-design/web-vue/es/icon'
  import useAppConfigStore from '@/store/modules/app-config'

  export default defineComponent({
    name: 'Humburger',
    components: { MenuFoldOutlined },
    setup() {
      const appStore = useAppConfigStore()

      function toggleFold() {
        appStore.toggleCollapse(!appStore.isCollapse)
      }

      return {
        appStore,
        toggleFold,
      }
    },
  })
</script>

<style lang="less" scoped>
  .mango-fold-open-status {
    transform: rotate(180deg);
  }

  .mango-fold-close-status {
    transform: rotate(0);
  }

  .mango-fold-wrapper {
    box-sizing: border-box;
    display: inline-flex;
    line-height: @logoHeight;
    text-align: center;
    padding: 0 10px;
    font-size: 18px;
    transition: transform @transitionTime;
  }

  .mango-fold-wrapper:hover {
    color: var(--m-primary);
    cursor: pointer;
  }
</style>
