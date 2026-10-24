import { createUniver, defaultTheme, LocaleType, mergeLocales } from '@univerjs/presets'
import { UniverSheetsCorePreset } from '@univerjs/preset-sheets-core'
import UniverPresetSheetsCoreZhCN from '@univerjs/preset-sheets-core/locales/zh-CN'
import { UniverSheetsDataValidationPreset } from '@univerjs/preset-sheets-data-validation'
import UniverPresetSheetsDataValidationZhCN from '@univerjs/preset-sheets-data-validation/locales/zh-CN'
import { UniverSheetsFilterPreset } from '@univerjs/preset-sheets-filter'
import UniverPresetSheetsFilterZhCN from '@univerjs/preset-sheets-filter/locales/zh-CN'
import { UniverSheetsConditionalFormattingPreset } from '@univerjs/preset-sheets-conditional-formatting'
import UniverPresetSheetsConditionalFormattingZhCN from '@univerjs/preset-sheets-conditional-formatting/locales/zh-CN'
import { UniverSheetsFindReplacePreset } from '@univerjs/preset-sheets-find-replace'
import UniverPresetSheetsFindReplaceZhCN from '@univerjs/preset-sheets-find-replace/locales/zh-CN'
import { UniverSheetsHyperLinkPreset } from '@univerjs/preset-sheets-hyper-link'
import UniverPresetSheetsHyperLinkZhCN from '@univerjs/preset-sheets-hyper-link/locales/zh-CN'
import { UniverSheetsSortPreset } from '@univerjs/preset-sheets-sort'
import UniverPresetSheetsSortZhCN from '@univerjs/preset-sheets-sort/locales/zh-CN'

import '@univerjs/preset-sheets-core/lib/index.css'
import '@univerjs/preset-sheets-data-validation/lib/index.css'
import '@univerjs/preset-sheets-filter/lib/index.css'

const FIXED_COLUMN_COMMANDS = [
  'sheet.command.insert-col',
  'sheet.command.insert-col-by-range',
  'sheet.command.insert-col-before',
  'sheet.command.insert-col-after',
  'sheet.command.insert-multi-cols-before',
  'sheet.command.insert-multi-cols-right',
  'sheet.command.remove-col',
  'sheet.command.remove-col-by-range',
]

function token(style, name, fallback) {
  return style.getPropertyValue(name).trim() || fallback
}

function createMangoTheme(container) {
  const style = getComputedStyle(container)
  const surface = token(style, '--m-surface', defaultTheme.white)
  const surfaceSoft = token(style, '--m-surface-soft', defaultTheme.gray[50])
  const border = token(style, '--m-border', defaultTheme.gray[200])
  const borderStrong = token(style, '--m-border-strong', defaultTheme.gray[300])
  const text = token(style, '--m-text', defaultTheme.gray[900])
  const textSecondary = token(style, '--m-text-2', defaultTheme.gray[700])
  const muted = token(style, '--m-muted', defaultTheme.gray[500])
  const primary = token(style, '--m-primary', defaultTheme.primary[600])
  const primaryHover = token(style, '--m-primary-hover', defaultTheme.primary[700])
  const primarySoft = token(style, '--m-primary-soft', defaultTheme.primary[50])
  const primaryBorder = token(style, '--m-primary-border', defaultTheme.primary[200])

  return {
    ...defaultTheme,
    white: surface,
    black: text,
    primary: {
      ...defaultTheme.primary,
      50: primarySoft,
      100: primarySoft,
      200: primaryBorder,
      300: primaryBorder,
      400: primary,
      500: primary,
      600: primary,
      700: primaryHover,
      800: textSecondary,
      900: text,
    },
    gray: {
      ...defaultTheme.gray,
      50: surfaceSoft,
      100: surfaceSoft,
      200: border,
      300: borderStrong,
      400: muted,
      500: muted,
      600: textSecondary,
      700: textSecondary,
      800: text,
      900: text,
    },
  }
}

export function createFunctionalSheet(container) {
  return createUniver({
    theme: createMangoTheme(container),
    darkMode: document.body.getAttribute('arco-theme') === 'dark',
    locale: LocaleType.ZH_CN,
    locales: {
      [LocaleType.ZH_CN]: mergeLocales(
        UniverPresetSheetsCoreZhCN,
        UniverPresetSheetsDataValidationZhCN,
        UniverPresetSheetsFilterZhCN,
        UniverPresetSheetsConditionalFormattingZhCN,
        UniverPresetSheetsFindReplaceZhCN,
        UniverPresetSheetsHyperLinkZhCN,
        UniverPresetSheetsSortZhCN
      ),
    },
    presets: [
      UniverSheetsCorePreset({
        container,
        header: false,
        toolbar: true,
        ribbonType: 'classic',
        formulaBar: true,
        menu: Object.fromEntries(FIXED_COLUMN_COMMANDS.map((id) => [id, { hidden: true }])),
        sheets: {
          disableForceStringAlert: true,
          disableForceStringMark: true,
        },
        footer: { sheetBar: true, statisticBar: true, menus: true, zoomSlider: true },
      }),
      UniverSheetsDataValidationPreset({
        showEditOnDropdown: false,
        showSearchOnDropdown: true,
      }),
      UniverSheetsFilterPreset(),
      UniverSheetsSortPreset(),
      UniverSheetsFindReplacePreset(),
      UniverSheetsConditionalFormattingPreset(),
      UniverSheetsHyperLinkPreset(),
    ],
  })
}
