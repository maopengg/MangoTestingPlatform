<template>
  <a-card
    :bodyStyle="{ padding: '0 10px 10px 10px' }"
    :bordered="false"
    class="table-body variable"
  >
    <slot name="header"></slot>
    <slot name="default"></slot>
    <div class="mt-1"></div>
    <slot name="footer"></slot>
  </a-card>
</template>

<script lang="ts">
  import { defineComponent } from 'vue'

  export default defineComponent({
    name: 'TableBody',
  })
</script>

<style lang="less" scoped>
  .table-body {
    display: flex;
    flex-direction: column;
    //height: 100%;
    position: absolute;
    left: 5px;
    right: 5px;
    top: 5px;
    bottom: 55px;
  }
  // 这个样式是不是要写到里面去
  .variable {
    overflow: hidden;
    overflow-y: scroll;
    /* 设置滚动条的样式 */
    &::-webkit-scrollbar {
      width: 3px;
      height: 6px;
    }
    /* 滚动槽 */
    &::-webkit-scrollbar-track {
      border-radius: 3px;
    }
    /* 滚动条滑块 */
    &::-webkit-scrollbar-thumb {
      border-radius: 3px;
      background: rgba(51, 51, 51, 0.4);
    }
  }
</style>
