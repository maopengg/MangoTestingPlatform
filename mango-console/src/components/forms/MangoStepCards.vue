<template>
  <div class="mango-step-layout" :class="{ 'mango-step-layout--workspace': layout === 'workspace' }">
    <nav v-if="layout === 'workspace'" class="mango-step-navigation" :aria-label="label">
      <button v-for="(step, index) in steps" :key="step.key" type="button"
        class="mango-step-navigation__item" :aria-current="activeStep === step.key ? 'step' : undefined"
        @click="scrollToStep(step.key)">
        <span class="mango-step-navigation__number" aria-hidden="true">{{ index + 1 }}</span>
        <span>{{ step.title }}</span>
      </button>
    </nav>
  <ol ref="panelRef" class="mango-step-cards mango-native-scrollbar" :aria-label="label" role="list" @scroll.passive="handlePanelScroll">
    <li v-for="(step, index) in steps" :ref="element => setSectionElement(step.key, element)" :key="step.key" class="mango-step-cards__step">
      <span class="mango-step-cards__number" aria-hidden="true">{{ index + 1 }}</span>
      <section class="mango-section-card mango-step-cards__card" :aria-label="step.title">
        <div class="mango-section-title mango-step-cards__heading">
          <component :is="layout === 'workspace' ? 'h2' : 'h3'">{{ step.title }}</component>
          <slot :name="`${step.key}-actions`" :step="step" :index="index" />
        </div>
        <slot :name="step.key" :step="step" :index="index" />
      </section>
    </li>
  </ol>
  </div>
</template>
<script setup lang="ts">
  import { nextTick, onMounted, ref, watch } from 'vue'
  const props = withDefaults(
    defineProps<{
      steps: readonly { key: string; title: string }[]
      label?: string
      layout?: 'vertical' | 'workspace'
      initialStep?: string
    }>(),
    { label: '配置步骤', layout: 'vertical' }
  )
  const activeStep = ref('')
  const panelRef = ref<HTMLElement | null>(null)
  const sectionElements = new Map<string, HTMLElement>()
  function setSectionElement(key: string, element: unknown) {
    if (typeof HTMLElement !== 'undefined' && element instanceof HTMLElement) sectionElements.set(key, element)
    else sectionElements.delete(key)
  }
  function scrollToStep(key: string, behavior?: ScrollBehavior) {
    if (!props.steps.some(step => step.key === key)) return
    activeStep.value = key
    const panel = panelRef.value, section = sectionElements.get(key)
    if (!panel || !section || props.layout !== 'workspace') return
    const reducedMotion = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    panel.scrollTo({ top: Math.max(0, panel.scrollTop + section.getBoundingClientRect().top - panel.getBoundingClientRect().top), behavior: behavior || (reducedMotion ? 'auto' : 'smooth') })
  }
  function handlePanelScroll() {
    const panel = panelRef.value
    if (!panel || props.layout !== 'workspace' || !props.steps.length) return
    let key = props.steps[0].key
    const top = panel.getBoundingClientRect().top
    for (const step of props.steps) {
      const section = sectionElements.get(step.key)
      if (section && section.getBoundingClientRect().top - top <= 1) key = step.key
    }
    if (panel.scrollHeight > panel.clientHeight && panel.scrollTop + panel.clientHeight >= panel.scrollHeight - 1)
      key = props.steps[props.steps.length - 1].key
    activeStep.value = key
  }
  watch(() => props.steps.map(step => step.key), keys => {
    if (!keys.includes(activeStep.value)) activeStep.value = keys[0] || ''
  }, { immediate: true })
  watch(() => props.initialStep, async key => {
    await nextTick()
    if (key) scrollToStep(key, 'auto')
  })
  onMounted(async () => {
    await nextTick()
    if (props.initialStep) scrollToStep(props.initialStep, 'auto')
    else handlePanelScroll()
  })
  defineExpose({ scrollToStep })
</script>
<style scoped>
  .mango-step-cards {
    display: grid;
    gap: var(--m-page-gap);
    min-width: 0;
    list-style: none;
    margin: 0;
    padding: 0 0 0 34px;
  }
  .mango-step-cards__step {
    position: relative;
    min-width: 0;
  }
  .mango-step-cards__number {
    position: absolute;
    left: -34px;
    top: 10px;
    display: grid;
    place-items: center;
    width: 24px;
    height: 24px;
    border: 1px solid var(--m-primary);
    border-radius: 50%;
    color: var(--m-primary);
    background: var(--m-surface);
    font-weight: 600;
    font-size: 12px;
    line-height: 1;
  }
  .mango-step-cards__step:not(:last-child)::after {
    content: '';
    position: absolute;
    left: -22px;
    top: 36px;
    bottom: calc(-8px - var(--m-page-gap));
    width: 1px;
    background: var(--m-border);
  }
  .mango-step-cards__card {
    min-width: 0;
    margin-top: 0;
    box-shadow: none;
  }
  .mango-step-cards__heading {
    margin: 0 0 12px;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--m-page-gap);
  }
  .mango-step-cards__heading h2,
  .mango-step-cards__heading h3 {
    margin: 0;
    font-size: 14px;
    font-weight: 600;
  }
  .mango-step-cards__card :deep(.arco-form-item:last-child) {
    margin-bottom: 0;
  }
  .mango-step-layout { min-width: 0; }
  .mango-step-layout--workspace {
    display: grid;
    grid-template-columns: 200px minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr);
    height: 100%;
    min-height: 0;
    gap: var(--m-page-gap);
    background: var(--m-bg);
  }
  .mango-step-navigation {
    display: flex;
    flex-direction: column;
    gap: var(--m-space-xs);
    padding: var(--m-page-gap);
    min-width: 0;
    min-height: 0;
    overflow-y: auto;
    background: var(--m-surface-soft);
    border-radius: var(--m-radius-md);
  }
  .mango-step-navigation__item {
    display: flex;
    align-items: center;
    gap: var(--m-space-sm);
    padding: 10px var(--m-page-gap);
    border: 0;
    border-radius: var(--m-radius-sm);
    background: transparent;
    color: var(--m-text-2);
    font: inherit;
    text-align: left;
    line-height: 1.5;
    cursor: pointer;
  }
  .mango-step-navigation__item:hover { background: var(--m-surface); }
  .mango-step-navigation__item[aria-current="step"] { background: var(--m-primary-soft); color: var(--m-primary); font-weight: 600; }
  .mango-step-navigation__item:focus-visible { outline: 2px solid var(--m-primary); outline-offset: -2px; }
  .mango-step-navigation__number { flex-shrink: 0; color: var(--m-muted); font-variant-numeric: tabular-nums; }
  .mango-step-navigation__item[aria-current="step"] .mango-step-navigation__number { color: inherit; }
  .mango-step-layout--workspace .mango-step-cards {
    display: block;
    padding-left: 0;
    background: var(--m-bg);
    min-height: 0;
    height: 100%;
    overflow-y: auto;
    overflow-x: hidden;
    overscroll-behavior: contain;
  }
  .mango-step-layout--workspace .mango-step-cards__step + .mango-step-cards__step { margin-top: var(--m-page-gap); }
  .mango-step-layout--workspace .mango-step-cards__step:last-child { min-height: 100%; }
  .mango-step-layout--workspace .mango-step-cards__number,
  .mango-step-layout--workspace .mango-step-cards__step::after { display: none; }
  .mango-step-layout--workspace .mango-step-cards__card { border: 0; border-radius: var(--m-radius-md); background: var(--m-surface); container-type: inline-size; }
  .mango-step-layout--workspace .mango-step-cards__heading { justify-content: flex-start; gap: var(--m-space-lg); padding-bottom: var(--m-page-gap); border-bottom: 1px solid var(--m-border); }
  .mango-step-layout--workspace .mango-step-cards__heading h2 {
    color: var(--m-text);
    font-size: var(--m-font-subtitle);
    line-height: var(--m-line-subtitle);
    font-weight: 600;
  }
  @container (max-width: 800px) {
    .mango-step-layout--workspace { grid-template-columns: minmax(0, 1fr); grid-template-rows: auto minmax(0, 1fr); }
    .mango-step-navigation { flex-direction: row; flex-wrap: wrap; }
  }
</style>
