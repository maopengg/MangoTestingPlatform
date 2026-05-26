<template>
  <section class="mango-section-card manual-page">
    <div class="mango-section-title">
      <div>
        <h2>使用手册</h2>
        <p>快速定位平台常用模块说明</p>
      </div>
    </div>
    <div class="manual-layout">
      <nav class="manual-nav">
        <a href="#UI自动化">UI自动化</a>
        <a href="#接口自动化">接口自动化</a>
        <a href="#系统设置">系统设置</a>
      </nav>

      <div class="manual-content">
        <h1 id="UI自动化">UI自动化</h1>
        <p> 的呢啊我能打文凭佛呢我发发呢啊我贫困的哇破倒卖瓦尔v大二偶的卡位【的口味 </p>
        <h1 id="接口自动化">接口自动化</h1>
        <p> 的呢啊我能打文凭佛呢我发发呢啊我贫困的哇破倒卖瓦尔v大二偶的卡位【的口味 </p>
        <h1 id="系统设置">系统设置</h1>
        <p> 的呢啊我能打文凭佛呢我发发呢啊我贫困的哇破倒卖瓦尔v大二偶的卡位【的口味 </p>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup></script>
<style scoped>
  .manual-page {
    height: 100%;
    min-height: 0;
    overflow: auto;
  }

  .manual-layout {
    display: grid;
    grid-template-columns: 180px minmax(0, 1fr);
    gap: 16px;
  }

  .manual-nav {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }

  .manual-nav a {
    color: var(--m-text-2);
  }

  .manual-content {
    min-width: 0;
    color: var(--m-text-2);
  }

  .manual-content h1 {
    margin: 0 0 8px;
    color: var(--m-text);
    font-size: 18px;
    line-height: 26px;
  }

  .manual-content p + h1 {
    margin-top: 18px;
  }

  @media (max-width: 1px) {
    .manual-layout {
      grid-template-columns: 1fr;
    }
  }
</style>
