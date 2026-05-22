<template>
  <a-drawer
    v-model:visible="opened"
    :width="appStore.deviceType === 'mobile' ? '75%' : '280px'"
    closable
    placement="right"
    title="系统设置"
  >
    <Scrollbar class="mango-setting-wrapper">
      <a-divider dashed>主题风格</a-divider>
      <div class="mango-theme-preset-list">
        <button
          v-for="item in themePresets"
          :key="item.id"
          :class="{ active: appStore.themePreset === item.id }"
          class="mango-theme-preset-card"
          type="button"
          @click="presetClick(item.id)"
        >
          <span class="mango-theme-preset-preview">
            <i :style="{ background: item.tokens['m-layout-sidebar-bg'] }"></i>
            <em :style="{ background: item.tokens['m-layout-header-bg'] }"></em>
            <strong :style="{ background: item.tokens['m-primary'] }"></strong>
          </span>
          <span class="mango-theme-preset-copy">
            <b>{{ item.name }}</b>
            <small>{{ item.description }}</small>
          </span>
        </button>
      </div>
      <div style="height: 20px"></div>
      <a-divider dashed>侧边栏样式</a-divider>
      <div class="flex justify-around pb-8">
        <div
          v-for="(item, index) of sideExampleList"
          :key="index"
          :span="6"
          class="mango-example-wrapper"
        >
          <StyleExample
            :checked="item.checked"
            :left-bg="item.leftBg"
            :right-bottom-bg="item.rightBottomBg"
            :right-top-bg="item.rightTopBg"
            @click="exampleClick(item)"
          />
        </div>
      </div>
      <a-divider dashed>布局模式</a-divider>
      <div class="flex justify-around pb-8">
        <div v-for="(item, index) of layoutExampleList" :key="index" class="mango-example-wrapper">
          <StyleExample
            :checked="item.checked"
            :class="[item.class || '']"
            :left-bg="item.leftBg"
            :right-bottom-bg="item.rightBottomBg"
            :right-top-bg="item.rightTopBg"
            :tip-text="item.tipText"
            @click="layoutExampleClick(item)"
          />
        </div>
      </div>
      <a-divider dashed>菜单设置</a-divider>
      <div class="mango-setting-item-wrapper">
        <span style="width: 100px">菜单宽度</span>
        <a-input-number v-model="menuWidth" :max="400" :min="200" :step="10" size="small" />
      </div>
      <a-divider dashed>页面切换动画</a-divider>
      <div class="mango-setting-item-wrapper">
        <span style="width: 100px">动画效果</span>
        <a-select v-model="appStore.pageAnim" :options="animOptions" @change="onAnimUpdate" />
      </div>
      <a-divider dashed>按钮显示</a-divider>
      <div class="mango-setting-item-wrapper">
        <span>固定顶部导航</span>
        <a-switch v-model="appStore.isFixedNavBar" :disabled="appStore.layoutMode === 'ttb'" />
      </div>
      <div class="mango-setting-item-wrapper">
        <span>搜索</span>
        <a-switch v-model="appStore.actionBar.isShowSearch" />
      </div>
      <div class="mango-setting-item-wrapper">
        <span>消息</span>
        <a-switch v-model="appStore.actionBar.isShowMessage" />
      </div>
      <div class="mango-setting-item-wrapper">
        <span>刷新</span>
        <a-switch v-model="appStore.actionBar.isShowRefresh" />
      </div>
      <div class="mango-setting-item-wrapper">
        <span>全屏</span>
        <a-switch v-model="appStore.actionBar.isShowFullScreen" />
      </div>
      <a-divider />
    </Scrollbar>
  </a-drawer>
</template>

<script lang="ts">
  import { defineComponent, onMounted, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { ModalDialogType } from '@/types/components'
  import { useMenuWidth } from '@/hooks/useMenuWidth'
  import LeftBg from '@/assets/bg_img.webp'
  import useAppConfigStore from '@/store/modules/app-config'
  import { ThemeMode, ThemePresetId } from '@/store/types'
  import { themePresets } from '@/theme/presets'

  export default defineComponent({
    name: 'Setting',
    setup() {
      const appInfoDialog = ref<ModalDialogType | null>()
      const opened = ref(false)
      const appStore = useAppConfigStore()
      const showContact = ref(false)
      const menuWidth = ref(useMenuWidth())
      const sideExampleList = reactive([
        {
          leftBg: 'var(--m-layout-sidebar-bg)',
          rightTopBg: 'var(--m-layout-header-bg)',
          rightBottomBg: 'var(--m-bg)',
          checked: false,
          themeId: 'dark',
        },
        {
          leftBg: 'var(--m-surface)',
          rightTopBg: 'var(--m-layout-header-bg)',
          rightBottomBg: 'var(--m-bg)',
          checked: false,
          themeId: 'white',
        },
        {
          leftBg: `url(${LeftBg})`,
          rightTopBg: 'var(--m-layout-header-bg)',
          rightBottomBg: 'var(--m-bg)',
          checked: false,
          themeId: 'image',
        },
      ])
      const layoutExampleList = reactive([
        {
          leftBg: 'var(--m-layout-sidebar-bg)',
          rightTopBg: 'var(--m-layout-header-bg)',
          rightBottomBg: 'var(--m-bg)',
          checked: true,
          layoutId: 'ltr',
          tipText: '左右',
        },
        {
          leftBg: 'var(--m-layout-header-bg)',
          rightTopBg: 'var(--m-layout-header-bg)',
          rightBottomBg: 'var(--m-bg)',
          checked: false,
          layoutId: 'ttb',
          class: 'extra-class',
          tipText: '上下',
        },
        {
          leftBg: 'var(--m-layout-sidebar-bg)',
          rightTopBg: 'var(--m-layout-header-bg)',
          rightBottomBg: 'var(--m-bg)',
          checked: false,
          layoutId: 'lcr',
          class: 'extra-class-1',
          tipText: '分栏',
        },
      ])
      const animOptions = reactive([
        {
          label: '渐隐渐现',
          value: 'opacity',
        },
        {
          label: '左右滑动',
          value: 'fade',
        },
        {
          label: '上下滑动',
          value: 'down',
        },
        {
          label: '缩放效果',
          value: 'scale',
        },
      ])
      onMounted(() => {
        sideExampleList.forEach((it) => {
          it.checked = appStore.sideTheme === it.themeId
        })
        layoutExampleList.forEach((it) => {
          it.checked = appStore.layoutMode === it.layoutId
        })
      })

      function openDrawer() {
        opened.value = true
      }

      function exampleClick(item: any) {
        if (appStore.theme === ThemeMode.DARK) {
          Message.error('深色模式下不能更改侧边栏颜色')
          return
        }
        sideExampleList.forEach((it) => {
          it.checked = it === item
        })
        appStore.changeSideBarTheme(item.themeId)
      }

      function layoutExampleClick(item: any) {
        layoutExampleList.forEach((it) => {
          it.checked = it === item
        })
        appStore.changeLayoutMode(item.layoutId)
      }

      function presetClick(presetId: ThemePresetId) {
        appStore.changeThemePreset(presetId)
        sideExampleList.forEach((it) => {
          it.checked = appStore.sideTheme === it.themeId
        })
      }

      function onShowTabbar(val: boolean) {
        // appStore.changeShowTabbar(val)
      }

      function openAppInfo() {
        appInfoDialog.value?.toggle()
      }

      function onAnimUpdate(val: any) {
        appStore.changePageAnim(val)
      }

      watch(
        () => menuWidth.value,
        (newVal) => {
          appStore.changeSideWidth(newVal)
        }
      )
      return {
        appStore,
        appInfoDialog,
        showContact,
        opened,
        sideExampleList,
        layoutExampleList,
        themePresets,
        openDrawer,
        exampleClick,
        onShowTabbar,
        layoutExampleClick,
        onAnimUpdate,
        presetClick,
        openAppInfo,
        animOptions,
        menuWidth,
      }
    },
  })
</script>

<style lang="less">
  .dark {
    .el-drawer {
      background-color: var(--m-overlay-bg) !important;
    }
  }

  .light,
  .dark-side,
  .blue-side {
    .el-drawer {
      background-color: var(--m-overlay-bg) !important;
    }
  }
</style>
<style lang="less" scoped>
  @width: 60px;

  :deep(.mango-scrollbar__bar.mango-is-horizontal) {
    display: none;
  }

  .mango-setting-wrapper {
    margin-top: -16px;

    .close-wrapper {
      text-align: right;
      font-size: 20px;
    }

    .color-wrapper {
      width: 20px;
      height: 20px;
      border-radius: 5px;
      border: 1px solid var(--m-border);
      margin-bottom: 20px;
      box-shadow: var(--m-shadow);
    }

    .mango-theme-preset-list {
      display: grid;
      gap: 10px;
      max-height: 218px;
      overflow-y: auto;
      padding: 0 2px;
      padding-right: 4px;
      scrollbar-width: thin;
    }

    .mango-theme-preset-card {
      display: grid;
      grid-template-columns: 58px minmax(0, 1fr);
      gap: 10px;
      width: 100%;
      padding: 10px;
      border: 1px solid var(--m-border);
      border-radius: 8px;
      background: var(--m-surface);
      cursor: pointer;
      text-align: left;
      transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
    }

    .mango-theme-preset-card:hover,
    .mango-theme-preset-card.active {
      border-color: var(--m-primary);
      box-shadow: var(--m-shadow);
    }

    .mango-theme-preset-card.active {
      transform: translateY(-1px);
    }

    .mango-theme-preset-preview {
      position: relative;
      display: grid;
      grid-template-columns: 18px 1fr;
      width: 58px;
      height: 42px;
      overflow: hidden;
      border: 1px solid var(--m-border);
      border-radius: 6px;
      background: var(--m-surface-soft);
    }

    .mango-theme-preset-preview i,
    .mango-theme-preset-preview em,
    .mango-theme-preset-preview strong {
      display: block;
      font-style: normal;
    }

    .mango-theme-preset-preview i {
      grid-row: span 2;
    }

    .mango-theme-preset-preview strong {
      position: absolute;
      right: 8px;
      bottom: 7px;
      width: 20px;
      height: 6px;
      border-radius: 999px;
    }

    .mango-theme-preset-copy {
      min-width: 0;
    }

    .mango-theme-preset-copy b {
      display: block;
      color: var(--m-text);
      font-size: 13px;
      line-height: 18px;
    }

    .mango-theme-preset-copy small {
      display: -webkit-box;
      overflow: hidden;
      color: var(--m-muted);
      font-size: 12px;
      line-height: 18px;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
    }

    .circle::after {
      content: '';
      display: block;
      margin: 0 auto;
      margin-top: 25px;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: var(--m-success);
      text-align: center;
    }

    .mango-setting-item-wrapper {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px;
      font-size: 14px;
    }
  }
</style>
