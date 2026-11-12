import { defineStore } from 'pinia'

import defaultSetting from '@/setting'
import {
  DeviceType,
  DisplayDensity,
  LayoutMode,
  PageAnim,
  SideTheme,
  ThemeMode,
} from '../types'

import { useChangeMenuWidth } from '@/hooks/useMenuWidth'
import { applyDisplayDensity, setAutoDisplayScales } from '@/hooks/useDisplayDensity'
import { normalizeInterfacePreferences } from '@/utils/interface-preferences'
import usePrimaryColor from '@/hooks/usePrimaryColor'
import useTheme from '@/hooks/useTheme'
import { applyThemePreset, getThemePreset, ThemePresetId } from '@/theme/presets'

const useAppConfigStore = defineStore('app-config', {
  state: () => {
    return defaultSetting
  },
  getters: {
    getLayoutMode(state) {
      return state.layoutMode
    },
  },
  actions: {
    applyInterfacePreferences(value: unknown) {
      const preferences = normalizeInterfacePreferences(value)
      this.$patch(preferences)
      const preset = applyThemePreset(preferences.themePreset)
      this.theme = preset.mode
      this.themeColor = preset.primary
      useChangeMenuWidth(preferences.sideWidth)
      setAutoDisplayScales(preferences.autoScale2k, preferences.autoScale4k)
      applyDisplayDensity(preferences.displayDensity)
    },
    changeAutoDisplayScales(twoK: number, fourK: number) {
      const preferences = normalizeInterfacePreferences({ ...this.$state, autoScale2k: twoK, autoScale4k: fourK })
      this.autoScale2k = preferences.autoScale2k
      this.autoScale4k = preferences.autoScale4k
      setAutoDisplayScales(this.autoScale2k, this.autoScale4k)
      applyDisplayDensity(this.displayDensity)
    },
    changeTheme(theme: ThemeMode) {
      this.theme = theme
      useTheme(theme)
    },
    changeLayoutMode(mode: LayoutMode) {
      this.layoutMode = mode
    },
    changeDevice(deviceType: DeviceType) {
      this.deviceType = deviceType
    },
    changeDisplayDensity(displayDensity: DisplayDensity) {
      this.displayDensity = displayDensity
      setAutoDisplayScales(this.autoScale2k, this.autoScale4k)
      applyDisplayDensity(displayDensity)
    },
    changeSideBarTheme(sideTheme: SideTheme) {
      this.sideTheme = sideTheme
    },
    changePageAnim(pageAnim: PageAnim) {
      this.pageAnim = pageAnim
    },
    changePrimaryColor(color: string) {
      this.themeColor = color
      usePrimaryColor(color)
    },
    changeThemePreset(presetId: ThemePresetId) {
      const preset = applyThemePreset(presetId)
      this.themePreset = preset.id
      this.theme = preset.mode
      this.themeColor = preset.primary
      this.sideTheme = preset.mode === ThemeMode.DARK ? SideTheme.DARK : SideTheme.WHITE
    },
    applyCurrentThemePreset() {
      const preset = applyThemePreset(this.themePreset)
      this.themePreset = preset.id
      this.theme = preset.mode
      this.themeColor = preset.primary
      this.sideTheme = preset.mode === ThemeMode.DARK ? SideTheme.DARK : SideTheme.WHITE
    },
    syncThemePresetByColor() {
      const preset = getThemePreset(this.themePreset)
      this.themePreset = preset.id
      this.theme = preset.mode
      this.themeColor = preset.primary
    },
    changeSideWidth(sideWidth: number) {
      this.sideWidth = sideWidth
      useChangeMenuWidth(sideWidth)
    },
    toggleCollapse(isCollapse: boolean) {
      this.isCollapse = isCollapse
    },
    setMainHeight(height: number) {
      this.mainHeight = height
    },
    setFlexMainHeight(isFlex: boolean) {
      this.flexMainHeight = isFlex
    },
  },
  presist: {
    enable: true,
    resetToState: true,
    option: {
      exclude: ['flexMainHeight'],
    },
  },
})

export default useAppConfigStore
