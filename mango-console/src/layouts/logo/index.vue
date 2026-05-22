<template>
  <button
    :style="{ 'background-color': bgColor }"
    class="mango-logo-wrapper"
    type="button"
    @click="goHome"
  >
    <img v-if="showLogo" class="mango-logo-img" src="../../assets/logo.png" />
    <div
      v-if="showTitle"
      :class="[!appStore.isCollapse || alwaysShow ? 'mango-show-title' : 'mango-close-title']"
    >
      <span class="mango-logo-title">{{ projectName }}</span>
    </div>
  </button>
</template>

<script lang="ts">
  import { computed, defineComponent } from 'vue'
  import { useRouter } from 'vue-router'
  import { projectName } from '../../setting'
  import useAppConfigStore from '@/store/modules/app-config'

  export default defineComponent({
    name: 'Logo',
    props: {
      showTitle: {
        type: Boolean,
        default: true,
      },
      showLogo: {
        type: Boolean,
        default: true,
      },
      alwaysShow: {
        type: Boolean,
        default: false,
      },
    },
    setup() {
      const appStore = useAppConfigStore()
      const router = useRouter()
      const bgColor = computed(() => {
        return 'var(--m-layout-logo-bg)'
      })
      function goHome() {
        router.push('/index/home')
      }
      return {
        appStore,
        projectName,
        bgColor,
        goHome,
      }
    },
  })
</script>
<style lang="less" scoped>
  .mango-logo-wrapper {
    height: @logoHeight;
    display: flex;
    justify-content: center;
    align-items: center;
    color: var(--m-layout-logo-text);
    width: 100%;
    padding: 0;
    border: 0;
    border-bottom: 1px dashed var(--m-layout-header-border);
    cursor: pointer;

    &:hover {
      color: var(--m-primary);
    }

    .mango-logo-img {
      width: 30px;
    }

    .mango-logo-title {
      font-weight: bold;
    }

    .mango-show-title {
      transform: scale(1);
      width: auto;
      transition: transform 0.2s ease-in;
    }

    .mango-close-title {
      transform: scale(0);
      width: 0;
    }
  }
</style>
