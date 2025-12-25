<template>
  <div class="title-container">
    <span class="line"></span>
    <span class="title">{{ title }}</span>
  </div>
</template>

<script lang="ts">
  import { defineComponent } from 'vue'

  export default defineComponent({
    name: 'Title',
    props: {
      title: {
        type: String,
        default: '',
      },
    },
  })
</script>

<style lang="less" scoped>
  @import './css/title.module.less';
</style>
