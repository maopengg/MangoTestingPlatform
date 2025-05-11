<template>
  <a-card :bordered="false" class="footer-container">
    Copyright © 芒果味 2022-至今 Version：{{ version }}</a-card
  >
  <!--  禁止修改作者署名-->
</template>

<script lang="ts" setup>
  import useAppInfo from '@/hooks/useAppInfo'
  const { version } = useAppInfo()
</script>

<style lang="less" scoped>
  .footer-container {
    height: @footerHeight;
    display: flex;
    justify-content: center;
    align-items: center;
    box-sizing: border-box;
  }
</style>
