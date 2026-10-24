<template>
  <a-sub-menu :key="menuInfo.key">
    <template #title>
      <span class="mango-sub-menu-label">
        <span class="mango-sub-menu-label__text">{{ menuInfo.label }}</span>
        <MenuStatusBadge v-if="menuInfo.isBeta" value="Beta" />
      </span>
    </template>
    <template #icon>
      <component
        :is="menuInfo.icon || 'icon-menu'"
        style="font-size: 16px; vertical-align: middle"
      />
    </template>
    <template v-for="item in menuInfo.children" :key="item.key">
      <template v-if="!item.children">
        <a-menu-item :key="item.key">
          <template #icon>
            <component :is="item.icon || 'icon-menu'" />
          </template>
          <span class="mango-sub-menu-label">
            <span class="mango-sub-menu-label__text">{{ item.label }}</span>
            <MenuStatusBadge v-if="item.isBeta" value="Beta" />
          </span>
        </a-menu-item>
      </template>
      <template v-else>
        <SubMenu :key="item.key" :menu-info="item" />
      </template>
    </template>
  </a-sub-menu>
</template>

<script lang="ts">
  import { defineComponent } from 'vue'
  import MenuStatusBadge from './MenuStatusBadge.vue'

  export default defineComponent({
    name: 'SubMenu',
    components: { MenuStatusBadge },
    props: {
      menuInfo: {
        type: Object,
        default: () => ({}),
      },
    },
  })
</script>
<style scoped>
  .mango-sub-menu-label {
    display: flex;
    width: 100%;
    max-width: 100%;
    min-width: 0;
    align-items: center;
    gap: 4px;
    margin-left: 2px;
    padding-right: 3px;
  }

  .mango-sub-menu-label__text {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
