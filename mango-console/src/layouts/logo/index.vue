<template>
  <button
    :style="{ 'background-color': bgColor }"
    class="mango-logo-wrapper"
    type="button"
    @click="goHome"
  >
    <svg
      v-if="showLogo"
      :aria-label="projectName"
      class="mango-logo-img"
      role="img"
      viewBox="0 0 64 64"
    >
      <path
        class="mango-logo-symbol"
        d="M9 53V31C9 19 16 11 27 8l5 12 6-11c10 2 17 10 17 22v22H44V32c0-5-2-8-5-11l-7 18-8-18c-3 3-4 7-4 11v21H9Z"
      />
      <path
        class="mango-logo-leaf"
        d="M37 10C43 3 52 3 58 8c-6 6-14 7-21 2Z"
      />
    </svg>
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
  import usePlatformBrandingStore from '@/store/modules/platform-branding'
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
      const branding = usePlatformBrandingStore()
      const router = useRouter()
      const bgColor = computed(() => {
        return 'var(--m-layout-logo-bg)'
      })
      function goHome() {
        router.push('/index/home')
      }
      return {
        appStore,
        projectName: computed(() => branding.projectName),
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
      width: 27px;
    }

    .mango-logo-symbol {
      fill: var(--m-primary);
    }

    .mango-logo-leaf {
      fill: var(--m-warning);
    }

    .mango-logo-title {
      font-size: 16px;
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
