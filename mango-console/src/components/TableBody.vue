<template>
  <a-card :bodyStyle="{ padding: '0 10px 10px 10px' }" :bordered="false" class="table-body">
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
    height: 100%;
  }
</style>
