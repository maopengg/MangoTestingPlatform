import type { AppConfigState } from '@/store/types'
import { DisplayDensity, LayoutMode, PageAnim, SideTheme } from '@/store/types'
import type { ThemePresetId } from '@/theme/presets'

export interface InterfacePreferences {
  themePreset: ThemePresetId
  sideTheme: SideTheme
  layoutMode: LayoutMode
  displayDensity: DisplayDensity
  autoScale2k: number
  autoScale4k: number
  sideWidth: number
  pageAnim: PageAnim
  isFixedNavBar: boolean
  actionBar: AppConfigState['actionBar']
}

const presets = [
  'mango-blue',
  'tech-cyan',
  'graphite-dark',
  'dopamine-pop',
  'royal-purple',
  'morandi',
  'slate-indigo',
  'forest-console',
  'ocean-graphite',
]
export function normalizeInterfacePreferences(value: unknown): InterfacePreferences {
  const data = value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
  const bar =
    data.actionBar && typeof data.actionBar === 'object'
      ? (data.actionBar as Record<string, unknown>)
      : {}
  const pick = <T extends string>(value: unknown, options: readonly T[], fallback: T): T =>
    options.includes(value as T) ? (value as T) : fallback
  const bool = (value: unknown) => (typeof value === 'boolean' ? value : true)
  const scale = (value: unknown, fallback: number) =>
    typeof value === 'number' && Number.isFinite(value) && value >= 1 && value <= 3
      ? value
      : fallback
  const autoScale2k = scale(data.autoScale2k, 1.15)
  const autoScale4k = Math.max(autoScale2k, scale(data.autoScale4k, 1.35))
  return {
    themePreset: pick(data.themePreset, presets, 'mango-blue') as ThemePresetId,
    sideTheme: pick(data.sideTheme, Object.values(SideTheme), SideTheme.WHITE),
    layoutMode: pick(data.layoutMode, Object.values(LayoutMode), LayoutMode.LTR),
    displayDensity: pick(data.displayDensity, Object.values(DisplayDensity), DisplayDensity.AUTO),
    autoScale2k,
    autoScale4k,
    sideWidth:
      typeof data.sideWidth === 'number' &&
      Number.isInteger(data.sideWidth) &&
      data.sideWidth >= 168 &&
      data.sideWidth <= 280
        ? data.sideWidth
        : 200,
    pageAnim: pick(data.pageAnim, Object.values(PageAnim), PageAnim.OPACITY),
    isFixedNavBar: bool(data.isFixedNavBar),
    actionBar: {
      isShowSearch: bool(bar.isShowSearch),
      isShowMessage: bool(bar.isShowMessage),
      isShowRefresh: bool(bar.isShowRefresh),
      isShowFullScreen: bool(bar.isShowFullScreen),
    },
  }
}

export function readUserInterfacePreferences(response: {
  code: number
  data: unknown
}): InterfacePreferences {
  if (response.code !== 200 || !Array.isArray(response.data))
    throw new Error('Invalid user config response')
  const item = response.data.find((item) => item?.key === 'interface')
  return normalizeInterfacePreferences(item?.value)
}

export function readUserSelectedEnvironment(response: {
  code: number
  data: unknown
}): number | null {
  if (response.code !== 200 || !Array.isArray(response.data))
    throw new Error('Invalid user config response')
  const item = response.data.find((item) => item?.key === 'selected_environment')
  const value = item ? item.value : null
  if (
    response.code !== 200 ||
    (value !== null && (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0))
  )
    throw new Error('Invalid user environment response')
  return value as number | null
}
