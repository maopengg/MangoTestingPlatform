<script lang="ts">
  import { defineComponent, h } from 'vue'
  import ArcoSpin from '@arco-design/web-vue/es/spin'

  // Arco Spin 直接渲染默认插槽；面板布局使用自己拥有的内容层，不依赖库内部节点。
  export default defineComponent({
    name: 'MangoPanelSpin',
    inheritAttrs: false,
    setup(_, { attrs, slots }) {
      return () =>
        h(ArcoSpin, attrs, {
          ...slots,
          default: slots.default
            ? () => h('div', { class: 'mango-panel-spin__content' }, slots.default?.())
            : undefined,
        })
    },
  })
</script>

<style scoped>
  .mango-panel-spin__content {
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
  }
</style>
