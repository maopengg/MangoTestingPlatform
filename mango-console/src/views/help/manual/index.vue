<template>
  <section ref="pageElement" class="mango-section-card mango-manual-page" aria-labelledby="mango-manual-title">
    <div class="mango-section-title">
      <div>
        <h2 id="mango-manual-title">使用手册</h2>
        <p>快速定位平台常用模块说明</p>
      </div>
    </div>
    <div class="mango-manual-layout">
      <nav class="mango-manual-nav" aria-label="手册目录">
        <button
          v-for="section in manualSections"
          :key="section.id"
          type="button"
          :aria-controls="`mango-manual-${section.id}`"
          :data-testid="section.testId"
          @click="scrollToSection(section.id)"
        >{{ section.title }}</button>
      </nav>
      <div class="mango-manual-content">
        <section v-for="section in manualSections" :key="section.id" :aria-labelledby="`mango-manual-${section.id}`">
          <h3 :id="`mango-manual-${section.id}`" tabindex="-1">{{ section.title }}</h3>
          <p>{{ section.description }}</p>
        </section>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
  import { ref } from 'vue'
  import { manualSections, type ManualSectionId } from './config'

  const pageElement = ref<HTMLElement | null>(null)

  function scrollToSection(id: ManualSectionId) {
    const page = pageElement.value
    const heading = page?.querySelector<HTMLElement>(`#mango-manual-${id}`)
    if (!page || !heading) return
    const top = page.scrollTop + heading.getBoundingClientRect().top - page.getBoundingClientRect().top - page.clientTop
    page.scrollTo({ top: Math.max(0, top), behavior: 'auto' })
    heading.focus({ preventScroll: true })
  }
</script>

<style scoped>
  .mango-manual-page {
    box-sizing: border-box;
    height: 100%;
    min-height: 0;
    min-width: 0;
    overflow: auto;
    padding: var(--m-page-gap);
  }

  .mango-manual-layout {
    display: grid;
    grid-template-columns: 180px minmax(0, 1fr);
    gap: var(--m-page-gap);
    align-items: start;
  }

  .mango-manual-nav {
    position: sticky;
    top: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }

  .mango-manual-nav button {
    padding: 6px 8px;
    border: 0;
    border-radius: var(--m-radius-md);
    background: transparent;
    color: var(--m-text-2);
    font: inherit;
    text-align: left;
    cursor: pointer;
  }

  .mango-manual-nav button:hover,
  .mango-manual-nav button:focus-visible {
    background: var(--m-primary-soft);
    color: var(--m-primary);
    outline: 1px solid var(--m-primary-border);
  }

  .mango-manual-content {
    min-width: 0;
    color: var(--m-text-2);
    overflow-wrap: anywhere;
  }

  .mango-manual-content h3 {
    margin: 0 0 8px;
    color: var(--m-text-2);
    font-size: 14px;
    font-weight: 600;
    line-height: 22px;
  }

  .mango-manual-content p {
    margin: 0;
    color: var(--m-muted);
    font-size: 13px;
    line-height: 22px;
  }

  .mango-manual-content section + section {
    margin-top: 18px;
    padding-top: 18px;
    border-top: 1px solid var(--m-border);
  }
</style>
