import { defineStore } from 'pinia'

import defaultSetting from '@/setting'
import { DeviceType, LayoutMode, PageAnim, SideTheme, ThemeMode } from '../types'

import { useChangeMenuWidth } from '@/hooks/useMenuWidth'
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
