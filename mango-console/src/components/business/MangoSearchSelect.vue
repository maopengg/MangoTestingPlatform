<template>
  <span ref="root" class="mango-search-select" @mouseleave="leave">
    <a-select
      v-bind="$attrs"
      :trigger-props="triggerProps"
      tag-nowrap
      @change="changed"
      @blur="blurred"
      @popup-visible-change="popupChanged"
    >
      <template v-for="(_, name) in $slots" #[name]="slotProps">
        <slot :name="name" v-bind="slotProps || {}" />
      </template>
    </a-select>
  </span>
</template>

<script lang="ts">
  export default { inheritAttrs: false }
</script>

<script lang="ts" setup>
  import { computed, getCurrentInstance, nextTick, onBeforeUnmount, onDeactivated, ref, useAttrs } from 'vue'
  import { useDebouncedSearch } from '@/hooks/useDebouncedSearch'

  const emit = defineEmits<{
    (event: 'change', value: unknown): void
    (event: 'popup-visible-change', visible: boolean): void
    (event: 'blur', eventObject: FocusEvent): void
  }>()
  const attrs = useAttrs()
  const root = ref<HTMLElement>()
  const popupClass = `mango-search-select-popup-${getCurrentInstance()!.uid}`
  const triggerProps = computed(() => {
    const original = (attrs.triggerProps || {}) as Record<string, unknown>
    return { ...original, contentClass: [original.contentClass, popupClass] }
  })
  let opened = false
  const search = useDebouncedSearch(() => emit('change', attrs.modelValue), () => attrs.modelValue)

  function pointerMoved(event: MouseEvent) {
    const target = event.target
    if (!(target instanceof Element)) return
    if (root.value?.contains(target) || target.closest(`.${popupClass}`)) search.cancel()
    else search.schedule()
  }
  function detach() {
    document.removeEventListener('mouseover', pointerMoved)
  }
  function popupChanged(visible: boolean) {
    opened = visible
    detach()
    if (visible) {
      search.cancel()
      document.addEventListener('mouseover', pointerMoved)
    } else void nextTick(search.schedule)
    emit('popup-visible-change', visible)
  }
  function changed() {
    if (opened) search.cancel()
    else void nextTick(search.schedule)
  }
  function leave() {
    if (!opened) search.schedule()
  }
  function blurred(event: FocusEvent) {
    if (!opened) void nextTick(search.schedule)
    emit('blur', event)
  }
  onDeactivated(detach)
  onBeforeUnmount(detach)
</script>

<style scoped>
  .mango-search-select {
    display: block;
    width: 100%;
    min-width: 0;
  }
</style>
