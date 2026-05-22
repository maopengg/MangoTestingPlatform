import { ThemeMode } from '@/store/types'
import usePrimaryColor from '@/hooks/usePrimaryColor'
import useTheme from '@/hooks/useTheme'

export type ThemePresetId =
  | 'mango-blue'
  | 'tech-cyan'
  | 'graphite-dark'
  | 'dopamine-pop'
  | 'royal-purple'
  | 'morandi'

export type BaseThemeToken =
  | 'm-bg'
  | 'm-surface'
  | 'm-surface-soft'
  | 'm-border'
  | 'm-border-strong'
  | 'm-text'
  | 'm-text-2'
  | 'm-muted'
  | 'm-primary'
  | 'm-primary-hover'
  | 'm-primary-soft'
  | 'm-primary-border'
  | 'm-success'
  | 'm-danger'
  | 'm-warning'
  | 'm-chart-1'
  | 'm-chart-2'
  | 'm-chart-3'
  | 'm-chart-4'
  | 'm-chart-5'
  | 'm-layout-header-bg'
  | 'm-layout-header-text'
  | 'm-layout-header-border'
  | 'm-layout-sidebar-bg'
  | 'm-layout-sidebar-text'
  | 'm-layout-sidebar-muted'
  | 'm-layout-sidebar-hover-bg'
  | 'm-layout-sidebar-active-bg'
  | 'm-layout-sidebar-active-text'
  | 'm-layout-logo-bg'
  | 'm-layout-logo-text'
  | 'm-shadow'

export type ThemeTokenMap = Record<BaseThemeToken, string>

export interface ThemePreset {
  id: ThemePresetId
  name: string
  description: string
  primary: string
  mode: ThemeMode
  tokens: ThemeTokenMap
}

function withCommonTokens(tokens: ThemeTokenMap, mode: ThemeMode): Record<string, string> {
  const isDark = mode === ThemeMode.DARK
  return {
    ...tokens,
    'color-bg-1': tokens['m-surface'],
    'color-bg-2': tokens['m-surface'],
    'color-bg-3': tokens['m-surface-soft'],
    'color-bg-4': tokens['m-surface-soft'],
    'color-bg-5': tokens['m-bg'],
    'color-fill-1': tokens['m-surface-soft'],
    'color-fill-2': isDark ? '#253247' : tokens['m-primary-soft'],
    'color-fill-3': tokens['m-border'],
    'color-fill-4': tokens['m-border-strong'],
    'color-text-1': tokens['m-text'],
    'color-text-2': tokens['m-text-2'],
    'color-text-3': tokens['m-muted'],
    'color-text-4': tokens['m-muted'],
    'color-border': tokens['m-border'],
    'color-border-1': tokens['m-border'],
    'color-border-2': tokens['m-border'],
    'color-border-3': tokens['m-border-strong'],
    'color-border-4': tokens['m-border-strong'],
    'color-neutral-1': tokens['m-surface-soft'],
    'color-neutral-2': tokens['m-surface-soft'],
    'color-neutral-3': tokens['m-border'],
    'color-neutral-4': tokens['m-border-strong'],
    'color-neutral-5': tokens['m-border-strong'],
    'color-neutral-6': tokens['m-muted'],
    'color-neutral-7': tokens['m-muted'],
    'color-neutral-8': tokens['m-text-2'],
    'color-neutral-9': tokens['m-text'],
    'color-neutral-10': tokens['m-text'],
    'color-white': isDark ? tokens['m-text'] : '#FFFFFF',
    'm-on-primary': isDark ? '#07111F' : '#FFFFFF',
    'm-on-danger': isDark ? '#111827' : '#FFFFFF',
    'm-radius-sm': '4px',
    'm-radius-md': '6px',
    'm-radius-lg': '8px',
    'm-table-header-bg': isDark ? '#1E293B' : tokens['m-surface-soft'],
    'm-table-row-bg': tokens['m-surface'],
    'm-table-row-hover-bg': isDark ? 'rgba(56, 189, 248, 0.1)' : tokens['m-primary-soft'],
    'm-table-border': tokens['m-border'],
    'm-table-text': tokens['m-text-2'],
    'm-form-bg': tokens['m-surface'],
    'm-form-border': tokens['m-border'],
    'm-form-hover-border': tokens['m-border-strong'],
    'm-form-focus-shadow': isDark
      ? '0 0 0 2px rgba(56, 189, 248, 0.18)'
      : `0 0 0 2px ${tokens['m-primary-soft']}`,
    'm-overlay-bg': tokens['m-surface'],
    'm-overlay-border': tokens['m-border'],
    'm-overlay-mask': isDark ? 'rgba(0, 0, 0, 0.64)' : 'rgba(15, 23, 42, 0.36)',
    'm-code-bg': '#2B2B2B',
    'm-code-border': '#3C3F41',
    'm-code-text': '#A9B7C6',
    'm-code-key': '#FFC66D',
    'm-code-function': '#6897BB',
    'm-code-keyword': '#CC7832',
    'm-code-string': '#6A8759',
    'm-code-number': '#6897BB',
    'm-code-boolean': '#CC7832',
    'm-code-null': '#808080',
    'm-code-comment': '#808080',
    'm-code-operator': '#CC7832',
    'm-code-builtin': '#8888C6',
    'm-code-decorator': '#BBB529',
    'm-code-bracket': '#A9B7C6',
    'm-code-line-hover': '#323232',
    'm-scrollbar-track': isDark ? '#111827' : '#F1F5F9',
    'm-scrollbar-thumb': isDark ? '#475569' : '#CBD5E1',
    'm-scrollbar-thumb-hover': isDark ? '#64748B' : '#94A3B8',
  }
}

export const themePresets: ThemePreset[] = [
  {
    id: 'mango-blue',
    name: 'Mango Blue',
    description: '企业后台默认主题，清晰、紧凑、适合测试排查。',
    primary: '#1E40AF',
    mode: ThemeMode.LIGHT,
    tokens: {
      'm-bg': '#F8FAFC',
      'm-surface': '#FFFFFF',
      'm-surface-soft': '#F1F5F9',
      'm-border': '#DBE3EF',
      'm-border-strong': '#CBD5E1',
      'm-text': '#0F172A',
      'm-text-2': '#334155',
      'm-muted': '#64748B',
      'm-primary': '#1E40AF',
      'm-primary-hover': '#1D4ED8',
      'm-primary-soft': '#DBEAFE',
      'm-primary-border': '#BFDBFE',
      'm-success': '#059669',
      'm-danger': '#DC2626',
      'm-warning': '#D97706',
      'm-chart-1': '#1E40AF',
      'm-chart-2': '#059669',
      'm-chart-3': '#D97706',
      'm-chart-4': '#DC2626',
      'm-chart-5': '#64748B',
      'm-layout-header-bg': '#FFFFFF',
      'm-layout-header-text': '#0F172A',
      'm-layout-header-border': '#DBE3EF',
      'm-layout-sidebar-bg': '#FFFFFF',
      'm-layout-sidebar-text': '#334155',
      'm-layout-sidebar-muted': '#64748B',
      'm-layout-sidebar-hover-bg': '#EFF6FF',
      'm-layout-sidebar-active-bg': '#DBEAFE',
      'm-layout-sidebar-active-text': '#1E40AF',
      'm-layout-logo-bg': '#FFFFFF',
      'm-layout-logo-text': '#0F172A',
      'm-shadow': '0 10px 24px rgba(15, 23, 42, 0.06)',
    },
  },
  {
    id: 'tech-cyan',
    name: 'Tech Cyan',
    description: '数据平台与实时任务主题，偏监控、联动、科技感。',
    primary: '#0891B2',
    mode: ThemeMode.LIGHT,
    tokens: {
      'm-bg': '#F5FBFC',
      'm-surface': '#FFFFFF',
      'm-surface-soft': '#ECFEFF',
      'm-border': '#CDECF3',
      'm-border-strong': '#A5DCE8',
      'm-text': '#0F172A',
      'm-text-2': '#334155',
      'm-muted': '#5F7380',
      'm-primary': '#0891B2',
      'm-primary-hover': '#0E7490',
      'm-primary-soft': '#CFFAFE',
      'm-primary-border': '#A5F3FC',
      'm-success': '#059669',
      'm-danger': '#DC2626',
      'm-warning': '#D97706',
      'm-chart-1': '#0891B2',
      'm-chart-2': '#10B981',
      'm-chart-3': '#F59E0B',
      'm-chart-4': '#EF4444',
      'm-chart-5': '#6366F1',
      'm-layout-header-bg': '#FFFFFF',
      'm-layout-header-text': '#0F172A',
      'm-layout-header-border': '#CDECF3',
      'm-layout-sidebar-bg': '#F8FEFF',
      'm-layout-sidebar-text': '#244152',
      'm-layout-sidebar-muted': '#6B8794',
      'm-layout-sidebar-hover-bg': '#ECFEFF',
      'm-layout-sidebar-active-bg': '#CFFAFE',
      'm-layout-sidebar-active-text': '#0E7490',
      'm-layout-logo-bg': '#F8FEFF',
      'm-layout-logo-text': '#0F172A',
      'm-shadow': '0 10px 24px rgba(8, 145, 178, 0.08)',
    },
  },
  {
    id: 'graphite-dark',
    name: 'Graphite Dark',
    description: '深色排查主题，适合夜间监控和长时间查看报告。',
    primary: '#38BDF8',
    mode: ThemeMode.DARK,
    tokens: {
      'm-bg': '#0F172A',
      'm-surface': '#111827',
      'm-surface-soft': '#1E293B',
      'm-border': '#334155',
      'm-border-strong': '#475569',
      'm-text': '#F8FAFC',
      'm-text-2': '#CBD5E1',
      'm-muted': '#94A3B8',
      'm-primary': '#38BDF8',
      'm-primary-hover': '#7DD3FC',
      'm-primary-soft': 'rgba(56, 189, 248, 0.16)',
      'm-primary-border': 'rgba(56, 189, 248, 0.36)',
      'm-success': '#34D399',
      'm-danger': '#F87171',
      'm-warning': '#FBBF24',
      'm-chart-1': '#38BDF8',
      'm-chart-2': '#34D399',
      'm-chart-3': '#FBBF24',
      'm-chart-4': '#F87171',
      'm-chart-5': '#A78BFA',
      'm-layout-header-bg': '#111827',
      'm-layout-header-text': '#F8FAFC',
      'm-layout-header-border': '#334155',
      'm-layout-sidebar-bg': '#0B1220',
      'm-layout-sidebar-text': '#CBD5E1',
      'm-layout-sidebar-muted': '#94A3B8',
      'm-layout-sidebar-hover-bg': '#1E293B',
      'm-layout-sidebar-active-bg': 'rgba(56, 189, 248, 0.18)',
      'm-layout-sidebar-active-text': '#7DD3FC',
      'm-layout-logo-bg': '#0B1220',
      'm-layout-logo-text': '#F8FAFC',
      'm-shadow': '0 14px 30px rgba(0, 0, 0, 0.28)',
    },
  },
  {
    id: 'dopamine-pop',
    name: 'Dopamine Pop',
    description: '明快活力主题，适合演示、看板和高识别度工作台。',
    primary: '#FF3D68',
    mode: ThemeMode.LIGHT,
    tokens: {
      'm-bg': '#FFF7F8',
      'm-surface': '#FFFFFF',
      'm-surface-soft': '#FFF1F5',
      'm-border': '#FFD6E2',
      'm-border-strong': '#FFB8CB',
      'm-text': '#172033',
      'm-text-2': '#3D475C',
      'm-muted': '#7A879B',
      'm-primary': '#FF3D68',
      'm-primary-hover': '#E11D48',
      'm-primary-soft': '#FFE4EC',
      'm-primary-border': '#FFB8CB',
      'm-success': '#10B981',
      'm-danger': '#EF4444',
      'm-warning': '#F59E0B',
      'm-chart-1': '#FF3D68',
      'm-chart-2': '#14DAF0',
      'm-chart-3': '#F59E0B',
      'm-chart-4': '#8B5CF6',
      'm-chart-5': '#10B981',
      'm-layout-header-bg': '#FFFFFF',
      'm-layout-header-text': '#172033',
      'm-layout-header-border': '#FFD6E2',
      'm-layout-sidebar-bg': '#FFF7F8',
      'm-layout-sidebar-text': '#3D475C',
      'm-layout-sidebar-muted': '#7A879B',
      'm-layout-sidebar-hover-bg': '#FFF1F5',
      'm-layout-sidebar-active-bg': '#FFE4EC',
      'm-layout-sidebar-active-text': '#E11D48',
      'm-layout-logo-bg': '#FFF7F8',
      'm-layout-logo-text': '#172033',
      'm-shadow': '0 10px 24px rgba(255, 61, 104, 0.1)',
    },
  },
  {
    id: 'royal-purple',
    name: 'Royal Purple',
    description: '沉稳紫色主题，适合配置、权限和管理后台场景。',
    primary: '#7C3AED',
    mode: ThemeMode.LIGHT,
    tokens: {
      'm-bg': '#F8F7FF',
      'm-surface': '#FFFFFF',
      'm-surface-soft': '#F3EFFF',
      'm-border': '#DDD6FE',
      'm-border-strong': '#C4B5FD',
      'm-text': '#17122B',
      'm-text-2': '#3F365E',
      'm-muted': '#746A8F',
      'm-primary': '#7C3AED',
      'm-primary-hover': '#6D28D9',
      'm-primary-soft': '#EDE9FE',
      'm-primary-border': '#C4B5FD',
      'm-success': '#059669',
      'm-danger': '#DC2626',
      'm-warning': '#D97706',
      'm-chart-1': '#7C3AED',
      'm-chart-2': '#06B6D4',
      'm-chart-3': '#F59E0B',
      'm-chart-4': '#EC4899',
      'm-chart-5': '#22C55E',
      'm-layout-header-bg': '#FFFFFF',
      'm-layout-header-text': '#17122B',
      'm-layout-header-border': '#DDD6FE',
      'm-layout-sidebar-bg': '#FAF9FF',
      'm-layout-sidebar-text': '#3F365E',
      'm-layout-sidebar-muted': '#746A8F',
      'm-layout-sidebar-hover-bg': '#F3EFFF',
      'm-layout-sidebar-active-bg': '#EDE9FE',
      'm-layout-sidebar-active-text': '#6D28D9',
      'm-layout-logo-bg': '#FAF9FF',
      'm-layout-logo-text': '#17122B',
      'm-shadow': '0 10px 24px rgba(124, 58, 237, 0.09)',
    },
  },
  {
    id: 'morandi',
    name: 'Morandi',
    description: '低饱和莫兰迪主题，柔和、耐看，适合长时间配置和排查。',
    primary: '#7E9387',
    mode: ThemeMode.LIGHT,
    tokens: {
      'm-bg': '#F6F3EF',
      'm-surface': '#FFFEFB',
      'm-surface-soft': '#EFEBE4',
      'm-border': '#DDD5CA',
      'm-border-strong': '#C8BFB2',
      'm-text': '#2F3431',
      'm-text-2': '#59615C',
      'm-muted': '#7B837E',
      'm-primary': '#7E9387',
      'm-primary-hover': '#677A70',
      'm-primary-soft': '#E2E9E3',
      'm-primary-border': '#C5D1C8',
      'm-success': '#6F9B82',
      'm-danger': '#B76E6B',
      'm-warning': '#B58A5C',
      'm-chart-1': '#7E9387',
      'm-chart-2': '#8FA7B3',
      'm-chart-3': '#C0A37E',
      'm-chart-4': '#B76E6B',
      'm-chart-5': '#A89AAF',
      'm-layout-header-bg': '#FFFEFB',
      'm-layout-header-text': '#2F3431',
      'm-layout-header-border': '#DDD5CA',
      'm-layout-sidebar-bg': '#F2EEE8',
      'm-layout-sidebar-text': '#59615C',
      'm-layout-sidebar-muted': '#858D87',
      'm-layout-sidebar-hover-bg': '#E8E3DB',
      'm-layout-sidebar-active-bg': '#E2E9E3',
      'm-layout-sidebar-active-text': '#677A70',
      'm-layout-logo-bg': '#F2EEE8',
      'm-layout-logo-text': '#2F3431',
      'm-shadow': '0 10px 24px rgba(82, 74, 62, 0.08)',
    },
  },
]

export const defaultThemePresetId: ThemePresetId = 'mango-blue'

export function getThemePreset(presetId?: string) {
  return themePresets.find((item) => item.id === presetId) || themePresets[0]
}

export function applyThemePreset(presetId?: string) {
  const preset = getThemePreset(presetId)
  useTheme(preset.mode)
  usePrimaryColor(preset.primary)

  const root = document.documentElement
  Object.entries(withCommonTokens(preset.tokens, preset.mode)).forEach(([key, value]) => {
    root.style.setProperty(`--${key}`, value)
  })
  root.setAttribute('data-theme-preset', preset.id)
  document.body.setAttribute('data-theme-preset', preset.id)
  window.dispatchEvent(new CustomEvent('mango-theme-change', { detail: preset }))
  return preset
}
