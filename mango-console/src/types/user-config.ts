import type { InterfacePreferences } from '@/utils/interface-preferences'

export type UserConfigUpdate = Array<
  | {
      key: 'interface'
      value: Partial<Omit<InterfacePreferences, 'actionBar'>> & {
        actionBar?: Partial<InterfacePreferences['actionBar']>
      }
    }
  | { key: 'selected_environment'; value: number | null }
>
