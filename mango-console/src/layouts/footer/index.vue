<template>
  <a-card :bordered="false" class="mango-footer-container">
    Copyright © 芒果味 2022年-{{ currentYear }}年 Version：{{ version }}</a-card
  >
  <!--  禁止修改作者署名-->
</template>

<script lang="ts" setup>
  import { onBeforeUnmount, onMounted, ref } from 'vue'
  import useAppInfo from '@/hooks/useAppInfo'
  const { version } = useAppInfo()
  const currentYear = ref(new Date().getFullYear())
  let timer: ReturnType<typeof setInterval> | undefined
  const updateYear = () => { currentYear.value = new Date().getFullYear() }
  onMounted(() => { timer = setInterval(updateYear, 86400000); document.addEventListener('visibilitychange', updateYear) })
  onBeforeUnmount(() => { if (timer) clearInterval(timer); document.removeEventListener('visibilitychange', updateYear) })
</script>

<style lang="less" scoped>
  .mango-footer-container {
    height: @footerHeight;
    display: flex;
    justify-content: center;
    align-items: center;
    box-sizing: border-box;
    color: var(--m-muted);
    font-size: 12px;
    font-weight: 400;
    line-height: 20px;
    font-variant-numeric: tabular-nums;
  }
</style>
