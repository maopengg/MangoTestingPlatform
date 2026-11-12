<template>
  <a-drawer
    v-model:visible="opened"
    :width="appStore.deviceType === 'mobile' ? '75%' : '17.5rem'"
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
      <div class="mango-setting-section-spacer"></div>
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
      <a-divider dashed>显示密度</a-divider>
      <div class="mango-setting-item-wrapper">
        <span class="mango-setting-item-label">页面密度</span>
        <a-select
          v-model="appStore.displayDensity"
          :options="densityOptions"
          size="small"
          @change="onDensityUpdate"
        />
      </div>
      <p class="mango-setting-help"
        >自动模式会按当前浏览器宽度连续缩放，使不同屏幕保持接近的布局比例。</p
      >
      <div class="mango-setting-item-wrapper">
        <span class="mango-setting-item-label">2K 缩放比例</span>
        <a-input-number :model-value="appStore.autoScale2k" :min="1" :max="3" :step="0.05"
          :precision="2" aria-label="2K 缩放比例" model-event="input" @update:model-value="changeTwoK" />
      </div>
      <div class="mango-setting-item-wrapper">
        <span class="mango-setting-item-label">4K 缩放比例</span>
        <a-input-number :model-value="appStore.autoScale4k" :min="appStore.autoScale2k" :max="3" :step="0.05"
          :precision="2" aria-label="4K 缩放比例" model-event="input" @update:model-value="changeFourK" />
      </div>
      <p class="mango-setting-help">1.15 表示 115%，仅自动密度模式生效。</p>
      <a-divider dashed>菜单设置</a-divider>
      <div class="mango-setting-item-wrapper">
        <span class="mango-setting-item-label">菜单宽度</span>
        <a-input-number v-model="menuWidth" :max="280" :min="168" :step="7" size="small" />
      </div>
      <a-divider dashed>页面切换动画</a-divider>
      <div class="mango-setting-item-wrapper">
        <span class="mango-setting-item-label">动画效果</span>
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
      <div class="mango-setting-item-wrapper" aria-live="polite">
        <span class="mango-setting-help">{{ preferenceStatus }}</span>
        <a-button v-if="preferences.failed" size="small" :loading="preferences.loading || preferences.saving"
          @click="preferences.retry()">重试</a-button>
      </div>
    </Scrollbar>
  </a-drawer>
</template>

<script lang="ts">
  import { computed, defineComponent, onMounted, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { ModalDialogType } from '@/types/components'
  import LeftBg from '@/assets/bg_img.webp'
  import useAppConfigStore from '@/store/modules/app-config'
  import useUserPreferencesStore from '@/store/modules/user-preferences'
  import { DisplayDensity, ThemeMode, ThemePresetId } from '@/store/types'
  import { themePresets } from '@/theme/presets'

  export default defineComponent({
    name: 'Setting',
    setup() {
      const appInfoDialog = ref<ModalDialogType | null>()
      const opened = ref(false)
      const appStore = useAppConfigStore()
      const preferences = useUserPreferencesStore()
      const preferenceStatus = computed(() => preferences.loading ? '正在读取个人配置…'
        : preferences.saving ? '正在保存…' : preferences.failed ? '配置同步失败，可重试'
        : preferences.dirty ? '等待保存…' : preferences.ready ? '个人配置已同步' : '')
      const changeTwoK = (value: number | undefined) => {
        if (value !== undefined) appStore.changeAutoDisplayScales(value, appStore.autoScale4k)
      }
      const changeFourK = (value: number | undefined) => {
        if (value !== undefined) appStore.changeAutoDisplayScales(appStore.autoScale2k, value)
      }
      const showContact = ref(false)
      const menuWidth = computed({ get: () => appStore.sideWidth, set: value => appStore.changeSideWidth(value) })
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
      const densityOptions = [
        { label: '自动（推荐）', value: DisplayDensity.AUTO },
        { label: '紧凑', value: DisplayDensity.COMPACT },
        { label: '标准', value: DisplayDensity.STANDARD },
        { label: '宽屏舒适', value: DisplayDensity.COMFORTABLE },
      ]
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

      function onShowTabbar(_val: boolean) {
        // appStore.changeShowTabbar(val)
      }

      function openAppInfo() {
        appInfoDialog.value?.toggle()
      }

      function onAnimUpdate(val: any) {
        appStore.changePageAnim(val)
      }

      function onDensityUpdate(val: DisplayDensity) {
        appStore.changeDisplayDensity(val)
      }

      watch(() => [appStore.sideTheme, appStore.layoutMode], () => {
        sideExampleList.forEach(it => { it.checked = appStore.sideTheme === it.themeId })
        layoutExampleList.forEach(it => { it.checked = appStore.layoutMode === it.layoutId })
      })
      return {
        preferences,
        preferenceStatus,
        changeTwoK,
        changeFourK,
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
        densityOptions,
        onDensityUpdate,
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
      padding: 2px 4px 2px 2px;
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
      outline: 1px solid color-mix(in srgb, var(--m-primary) 18%, transparent);
      outline-offset: -2px;
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

    .mango-setting-item-label {
      width: 100px;
      flex: 0 0 auto;
      white-space: nowrap;
    }

    .mango-setting-section-spacer {
      height: 20px;
    }

    .mango-setting-help {
      margin: -4px 10px 8px;
      color: var(--m-muted);
      font-size: var(--m-font-caption);
      line-height: var(--m-line-caption);
    }
  }
</style>
