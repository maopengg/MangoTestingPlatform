<template>
  <div class="mango-functional-grid">
    <div class="mango-functional-grid__toolbar">
      <div class="mango-functional-grid__summary">
        <slot name="summary">共 {{ rows.length }} 条</slot>
        <span v-if="showHint" class="mango-functional-grid__hint"
          >拖动框选，支持从 WPS / Excel 复制粘贴</span
        >
      </div>
      <a-space size="small" wrap>
        <a-spin v-if="relationOptionsLoading" :loading="true" />
        <a-button
          v-if="editable && relationOptionsError"
          size="small"
          :loading="relationOptionsLoading"
          @click="retryRelationOptions"
          >重试选项</a-button
        >
        <slot name="toolbar"></slot>
        <a-button
          v-if="activeFilterCount"
          size="small"
          type="outline"
          status="warning"
          @click="clearFilters"
        >
          清除筛选（{{ activeFilterCount }}）
        </a-button>
        <a-popover trigger="click" position="br">
          <a-button size="small">
            <template #icon><icon-settings /></template>
            列设置
          </a-button>
          <template #content>
            <div class="mango-functional-grid__column-panel">
              <div class="mango-functional-grid__column-actions">
                <a-checkbox :model-value="allVisible" @change="toggleAll">全选</a-checkbox>
                <a-button type="text" size="mini" @click="resetColumns">恢复默认</a-button>
              </div>
              <draggable
                v-model="innerColumns"
                item-key="field"
                handle=".mango-functional-grid__drag"
                @end="emitViewChange"
              >
                <template #item="{ element }">
                  <div class="mango-functional-grid__column-item">
                    <icon-drag-dot-vertical class="mango-functional-grid__drag" />
                    <a-checkbox v-model="element.visible" @change="emitViewChange">
                      {{ element.title }}
                    </a-checkbox>
                  </div>
                </template>
              </draggable>
            </div>
          </template>
        </a-popover>
      </a-space>
    </div>

    <div class="mango-functional-grid__sheet-shell">
      <mango-panel-spin
        class="mango-functional-grid__spin"
        :loading="loading || renderLoading || incrementalLoading"
      >
        
        <div v-show="!renderError" ref="container" class="mango-functional-grid__sheet"></div>
      </mango-panel-spin>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import {
    computed,
    nextTick,
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    onMounted,
    ref,
    watch,
  } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { createFunctionalSheet } from '@/plugins/univer-sheets'
  import { scaleDensityPixels } from '@/hooks/useDisplayDensity'
  import { useFunctionalGridOptions } from './composables/useFunctionalGridOptions'
  import type { RelationListOption } from './composables/useFunctionalGridOptions'
  import draggable from 'vuedraggable'
  import { readGridRecord } from './functional-case-grid'
  import type {
    FunctionalGridColumn,
    FunctionalGridCellChange,
    FunctionalGridCellValue,
    FunctionalGridRecord,
  } from './functional-case-grid'

  const props = withDefaults(
    defineProps<{
      rows: object[]
      columns: FunctionalGridColumn[]
      loading?: boolean
      editable?: boolean
      selectable?: boolean
      rowKey?: string
      showHint?: boolean
      filterable?: boolean
      contextKey?: string
    }>(),
    {
      loading: false,
      editable: true,
      selectable: true,
      rowKey: 'id',
      showHint: true,
      filterable: true,
      contextKey: '',
    }
  )

  const emit = defineEmits<{
    (event: 'cell-change', payload: FunctionalGridCellChange): void
    (event: 'selection-change', rows: object[]): void
    (event: 'view-change', columns: FunctionalGridColumn[]): void
    (
      event: 'filter-change',
      payload: { active: boolean; activeColumns: number; filteredOutRows: number[] }
    ): void
    (event: 'load-more'): void
    (event: 'insert-rows', payload: { index: number; count: number }): void
    (event: 'remove-rows', rows: object[]): void
    (event: 'sort-change', payload: { field: string; direction: 'asc' | 'desc' }): void
  }>()

  const container = ref<HTMLElement>()
  const renderLoading = ref(false),
    renderError = ref(false)
  const incrementalLoading = ref(false)
  const defaultColumns = ref<FunctionalGridColumn[]>([])
  const innerColumns = ref<FunctionalGridColumn[]>([])
  const activeFilterCount = ref(0)
  // Univer's dynamic facade/command payloads stay inside this adapter; business rows and emits are typed.
  let univerInstance: any
  let univerAPI: any
  let workbook: any
  let worksheet: any
  let disposables: Array<{ dispose: () => void }> = []
  let rebuildTimer: number | undefined
  let loadMoreFrame: number | undefined
  let gridGeneration = 0
  let componentUnmounted = false
  let componentActive = true,
    componentMounted = false
  let rowUpdateGeneration = 0
  let viewportTimer: number | undefined
  let renderedDensity = 1
  let syncing = false
  let bufferColumnHidden = false
  let lastLoadMoreRowCount = 0
  let retainedFilterCriteria = new Map<string, any>()
  let retainedViewport: { row: number; column: number } | undefined
  let retainedZoom: number | undefined
  const ROW_BUFFER_COUNT = 8
  const COLUMN_BUFFER_COUNT = 1
  const LOAD_MORE_PRELOAD_ROWS = 100
  const DEFAULT_ZOOM_RATIO = 0.9
  const FIXED_COLUMN_COMMANDS = new Set([
    'sheet.command.insert-col',
    'sheet.command.insert-col-by-range',
    'sheet.command.insert-col-before',
    'sheet.command.insert-col-after',
    'sheet.command.insert-multi-cols-before',
    'sheet.command.insert-multi-cols-right',
    'sheet.command.remove-col',
    'sheet.command.remove-col-by-range',
  ])
  const INSERT_ROW_COMMANDS = new Set([
    'sheet.command.insert-row',
    'sheet.command.insert-row-by-range',
    'sheet.command.insert-row-before',
    'sheet.command.insert-row-after',
    'sheet.command.insert-multi-rows-above',
    'sheet.command.insert-multi-rows-after',
  ])
  const REMOVE_ROW_COMMANDS = new Set([
    'sheet.command.remove-row',
    'sheet.command.remove-row-by-range',
  ])
  const COLUMN_WIDTH_COMMANDS = new Set([
    'sheet.command.delta-column-width',
    'sheet.command.set-worksheet-col-width',
  ])
  const READ_ONLY_VIEW_COMMANDS = new Set([
    'sheet.command.scroll-to-cell',
    'sheet.command.scroll-view',
    'sheet.command.scroll-view-reset',
    'sheet.command.set-scroll-relative',
    'sheet.command.set-zoom-ratio',
    'sheet.command.set-filter-criteria',
    'sheet.command.set-filter-range',
    'sheet.command.set-worksheet-activate',
  ])
  const EDIT_MODE_MESSAGE_ID = 'mango-functional-grid-edit-mode-required'
  const {
    productOptions,
    moduleOptions: moduleListOptionsCache,
    loading: relationOptionsLoading,
    error: relationOptionsError,
    prepare: prepareOptions,
    reset: resetOptions,
  } = useFunctionalGridOptions({ current: () => componentActive && !componentUnmounted })
  interface RelationDraft {
    project_product_id: number
    project_product_path: string
    module_id: null
    module_path: string
  }
  const relationDrafts = new Map<object, RelationDraft>()
  const gridRows = computed(() => props.rows.map(readGridRecord))
  const previewRow = (row: FunctionalGridRecord): FunctionalGridRecord => {
    const draft = relationDrafts.get(row)
    return draft ? { ...row, ...draft } : row
  }

  const cloneColumns = (columns: FunctionalGridColumn[]) =>
    columns.map((item) => ({ ...item, visible: item.visible !== false }))
  const visibleColumns = computed(() => innerColumns.value.filter((item) => item.visible !== false))
  const allVisible = computed(() => innerColumns.value.every((item) => item.visible !== false))

  const applyColumns = (columns: FunctionalGridColumn[]) => {
    const normalized = cloneColumns(columns)
    if (!defaultColumns.value.length) defaultColumns.value = normalized.map((item) => ({ ...item }))
    innerColumns.value = normalized
  }

  const normalizeOptionValue = (value: unknown, column: FunctionalGridColumn) =>
    column.valueAliases?.[String(value)] ?? value

  const formatValue = (value: unknown, column: FunctionalGridColumn) => {
    if (column.options) {
      const optionLabel = (itemValue: unknown) => {
        const normalizedValue = normalizeOptionValue(itemValue, column)
        return (
          column.options?.find(
            (item) =>
              item.value === normalizedValue || String(item.value) === String(normalizedValue)
          )?.label ?? normalizedValue
        )
      }
      if (Array.isArray(value)) {
        const labels = value.map(optionLabel).filter((item) => item !== null && item !== undefined)
        return column.multiple ? labels.join(',') : labels.join('、')
      }
      return optionLabel(value) ?? ''
    }
    if (column.field === 'test_steps' && Array.isArray(value)) return `${value.length} 个步骤`
    if (Array.isArray(value)) return value.join('、')
    if (value && typeof value === 'object') return JSON.stringify(value)
    return value ?? ''
  }

  const formatRowValue = (row: FunctionalGridRecord, column: FunctionalGridColumn) => {
    return formatValue(previewRow(row)[column.displayField || column.field], column)
  }

  const parseValue = (value: unknown, column: FunctionalGridColumn): FunctionalGridCellValue => {
    const text = value === null || value === undefined ? '' : String(value).trim()
    if (column.options) {
      if (column.multiple) {
        let selectedLabels: string[] = []
        if (Array.isArray(value)) selectedLabels = value.map(String)
        else if (text) {
          try {
            const parsed = JSON.parse(text)
            selectedLabels = Array.isArray(parsed) ? parsed.map(String) : [text]
          } catch {
            selectedLabels = text
              .split(',')
              .map((item) => item.trim())
              .filter(Boolean)
          }
        }
        const selectedValues = selectedLabels.map((label) => {
          const normalizedLabel = normalizeOptionValue(label, column)
          const option = column.options?.find(
            (item) =>
              item.label === normalizedLabel || String(item.value) === String(normalizedLabel)
          )
          if (!option) throw new Error(`“${column.title}”必须从下拉选项中选择`)
          return option.value
        })
        return selectedValues
      }
      const normalizedText = normalizeOptionValue(text, column)
      const option = column.options.find(
        (item) => item.label === normalizedText || String(item.value) === String(normalizedText)
      )
      if (!option && text) throw new Error(`“${column.title}”必须从下拉选项中选择`)
      return option?.value ?? null
    }
    if (column.editor === 'number') {
      if (!text) return null
      const number = Number(text)
      if (Number.isNaN(number)) throw new Error(`“${column.title}”必须填写数字`)
      return number
    }
    return text
  }

  const valuesEqual = (left: unknown, right: unknown) =>
    Array.isArray(left) || Array.isArray(right)
      ? JSON.stringify(left ?? []) === JSON.stringify(right ?? [])
      : left === right

  const resolveColorToken = (token?: string) => {
    if (!token) return ''
    const containerColor = container.value
      ? getComputedStyle(container.value).getPropertyValue(token).trim()
      : ''
    return (
      containerColor || getComputedStyle(document.documentElement).getPropertyValue(token).trim()
    )
  }

  const parseColor = (color: string) => {
    const hex = color.match(/^#([\da-f]{3}|[\da-f]{6})$/i)?.[1]
    if (hex) {
      const normalized = hex.length === 3 ? [...hex].map((item) => item + item).join('') : hex
      return [0, 2, 4].map((start) => Number.parseInt(normalized.slice(start, start + 2), 16))
    }
    const rgb = color.match(/^rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)/i)
    return rgb ? rgb.slice(1, 4).map(Number) : undefined
  }

  const resolveTagColor = (token?: string) => {
    const accent = parseColor(resolveColorToken(token))
    const surface = parseColor(resolveColorToken('--m-surface'))
    if (!accent || !surface) return resolveColorToken(token)
    const accentWeight = 0.16
    const channels = accent.map((channel, index) =>
      Math.round(channel * accentWeight + surface[index] * (1 - accentWeight))
    )
    return `#${channels.map((channel) => channel.toString(16).padStart(2, '0')).join('')}`
  }

  const cloneFilterCriteria = (criteria: any) =>
    criteria === undefined || criteria === null ? criteria : JSON.parse(JSON.stringify(criteria))

  const captureFilterCriteria = (notify = false) => {
    if (!props.filterable || !worksheet?.getFilter) return
    const filter = worksheet.getFilter()
    if (!filter) {
      retainedFilterCriteria.clear()
      activeFilterCount.value = 0
      if (notify) emit('filter-change', { active: false, activeColumns: 0, filteredOutRows: [] })
      return
    }
    const next = new Map<string, any>()
    visibleColumns.value.forEach((column, columnIndex) => {
      const criteria = filter.getColumnFilterCriteria(columnIndex)
      if (criteria) next.set(column.field, cloneFilterCriteria(criteria))
    })
    retainedFilterCriteria = next
    activeFilterCount.value = next.size
    if (notify) {
      emit('filter-change', {
        active: next.size > 0,
        activeColumns: next.size,
        filteredOutRows: filter.getFilteredOutRows?.() || [],
      })
    }
  }

  const clearFilters = () => {
    retainedFilterCriteria.clear()
    activeFilterCount.value = 0
    const filter = worksheet?.getFilter?.()
    if (filter?.removeFilterCriteria) filter.removeFilterCriteria()
    else emit('filter-change', { active: false, activeColumns: 0, filteredOutRows: [] })
  }

  const buildCellData = () => {
    const data: Record<number, Record<number, { v: ReturnType<typeof formatRowValue> }>> = {
      0: Object.fromEntries(
        visibleColumns.value.map((column, index) => [index, { v: column.title }])
      ),
    }
    gridRows.value.forEach((row, rowIndex) => {
      data[rowIndex + 1] = Object.fromEntries(
        visibleColumns.value.map((column, columnIndex) => [
          columnIndex,
          { v: formatRowValue(row, column) },
        ])
      )
    })
    return data
  }

  const selectedDataRows = (selections: any[] = []) => {
    const indexes = new Set<number>()
    selections.forEach((range) => {
      const start = Math.max(1, Number(range.startRow ?? 0))
      const end = Math.min(props.rows.length, Number(range.endRow ?? range.startRow ?? 0))
      for (let row = start; row <= end; row += 1) indexes.add(row - 1)
    })
    return [...indexes]
      .sort((a, b) => a - b)
      .map((index) => gridRows.value[index])
      .filter(Boolean)
  }

  const commandRanges = (params: any = {}) => {
    const ranges = params.ranges || (params.range ? [params.range] : [])
    return Array.isArray(ranges) ? ranges : []
  }

  const interceptStructureCommand = (event: any) => {
    // 表格初始化、增量加载和回写也会经过命令总线；只拦截真实用户操作。
    if (syncing) return
    if (FIXED_COLUMN_COMMANDS.has(event.id)) {
      event.cancel = true
      Message.info('用例库列由系统固定，支持调整列宽、顺序和显示状态，但不能新增或删除列')
      return
    }
    if (INSERT_ROW_COMMANDS.has(event.id)) {
      event.cancel = true
      if (!props.editable) return
      const range = commandRanges(event.params)[0] || {}
      const startRow = Math.max(1, Number(range.startRow ?? 1))
      const rangeCount = Math.max(1, Number(range.endRow ?? startRow) - startRow + 1)
      const count = Math.max(1, Number(event.params?.value || rangeCount))
      emit('insert-rows', { index: Math.max(0, startRow - 1), count })
      return
    }
    if (REMOVE_ROW_COMMANDS.has(event.id)) {
      event.cancel = true
      if (!props.editable) return
      const ranges = commandRanges(event.params)
      const targets = ranges.length ? selectedDataRows(ranges) : []
      emit('remove-rows', targets)
      return
    }
    if (event.id === 'sheet.command.move-cols') {
      event.cancel = true
      const from = event.params?.fromRange || event.params?.range
      const to = event.params?.toRange
      if (!from || !to) return
      const start = Math.max(0, Number(from.startColumn || 0))
      const count = Math.max(1, Number(from.endColumn ?? start) - start + 1)
      const target = Math.max(0, Number(to.startColumn || 0))
      const reorderedVisible = [...visibleColumns.value]
      const moved = reorderedVisible.splice(start, count)
      const insertAt = target > start ? Math.max(0, target - count) : target
      reorderedVisible.splice(insertAt, 0, ...moved)
      const queue = [...reorderedVisible]
      innerColumns.value = innerColumns.value.map((column) =>
        column.visible === false ? column : queue.shift() || column
      )
      emitViewChange()
      return
    }
    if (event.id === 'sheet.command.move-rows') {
      event.cancel = true
      Message.info('用例顺序由筛选和排序决定，不支持直接拖动正式用例行')
      return
    }
    if (event.id === 'sheet.command.sort-range') {
      event.cancel = true
      const rule = event.params?.orderRules?.[0]
      const column = visibleColumns.value[Number(rule?.colIndex)]
      if (!column) return
      if (
        ['test_types', 'story_refs', 'test_steps', 'scenario_tags', 'automation_bindings'].includes(
          column.field
        )
      ) {
        Message.info(`“${column.title}”是多值字段，暂不支持排序`)
        return
      }
      emit('sort-change', {
        field: column.field,
        direction: rule.type === 'desc' ? 'desc' : 'asc',
      })
      return
    }
    if (
      !props.editable &&
      !COLUMN_WIDTH_COMMANDS.has(event.id) &&
      !READ_ONLY_VIEW_COMMANDS.has(event.id) &&
      /^sheet\.command\.(set-|reset-|merge|cancel-merge|clear-|delete-range|insert-range|move-range|split-text)/.test(
        event.id
      )
    ) {
      event.cancel = true
      Message.info({
        id: EDIT_MODE_MESSAGE_ID,
        content: '请先开启编辑模式',
      })
    }
  }

  const persistNativeColumnWidth = (event: any) => {
    if (!COLUMN_WIDTH_COMMANDS.has(event.id) || !worksheet) return
    visibleColumns.value.forEach((column, index) => {
      const width = worksheet.getColumnWidth?.(index)
      if (Number.isFinite(width) && width > 0) column.width = Math.round(width / renderedDensity)
    })
    emit(
      'view-change',
      innerColumns.value.map((item) => ({ ...item }))
    )
  }

  const restoreCell = (rowIndex: number, columnIndex: number) => {
    const row = gridRows.value[rowIndex - 1]
    const column = visibleColumns.value[columnIndex]
    if (!column || !worksheet) return
    syncing = true
    worksheet
      .getRange(rowIndex, columnIndex)
      .setValue(rowIndex === 0 ? column.title : row ? formatRowValue(row, column) : null)
    syncing = false
  }

  const refreshRowCells = (rowKey: string | number, fields: string[] = []) => {
    const rowIndex =
      gridRows.value.findIndex((row) => String(row[props.rowKey]) === String(rowKey)) + 1
    if (rowIndex <= 0) return
    const fieldSet = new Set(fields)
    visibleColumns.value.forEach((column, columnIndex) => {
      if (!fieldSet.size || fieldSet.has(column.field) || fieldSet.has(column.displayField || '')) {
        restoreCell(rowIndex, columnIndex)
      }
    })
  }

  const syncChangedRanges = (ranges: any[] = []) => {
    if (syncing) return
    const changed = new Set<string>()
    ranges.forEach((range) => {
      const raw = typeof range.getRange === 'function' ? range.getRange() : range
      const startRow = Math.max(0, Number(raw.startRow ?? 0))
      const endRow = Math.max(startRow, Number(raw.endRow ?? raw.startRow ?? 0))
      const startColumn = Math.max(0, Number(raw.startColumn ?? 0))
      const endColumn = Math.min(
        visibleColumns.value.length - 1,
        Number(raw.endColumn ?? raw.startColumn ?? 0)
      )
      for (let rowIndex = startRow; rowIndex <= endRow; rowIndex += 1) {
        for (let columnIndex = startColumn; columnIndex <= endColumn; columnIndex += 1) {
          changed.add(`${rowIndex}:${columnIndex}`)
        }
      }
    })
    changed.forEach((key) => {
      const [rowIndex, columnIndex] = key.split(':').map(Number)
      const row = gridRows.value[rowIndex - 1]
      const column = visibleColumns.value[columnIndex]
      if (!column) return
      if (rowIndex === 0) {
        const currentValue = worksheet?.getRange(rowIndex, columnIndex).getValue()
        if (!valuesEqual(currentValue, column.title)) restoreCell(rowIndex, columnIndex)
        return
      }
      if (!row) return
      if (!props.editable || column.editable === false) {
        const currentValue = worksheet?.getRange(rowIndex, columnIndex).getValue()
        const expectedValue = formatRowValue(row, column)
        if (!valuesEqual(currentValue, expectedValue)) restoreCell(rowIndex, columnIndex)
        return
      }
      const oldValue = row[column.field]
      try {
        const cellValue = worksheet.getRange(rowIndex, columnIndex).getValue()
        if (['project-product', 'module-cascader'].includes(column.editor || '')) {
          const options = relationListOptions(row, column)
          const selected = options.find((item) => item.label === String(cellValue ?? ''))
          if (!selected) throw new Error(`“${column.title}”必须从下拉选项中选择`)
          if (column.editor === 'project-product') {
            if (valuesEqual(Number(selected.value), Number(previewRow(row).project_product_id))) {
              restoreCell(rowIndex, columnIndex)
              return
            }
            if (valuesEqual(Number(selected.value), Number(row.project_product_id)))
              relationDrafts.delete(row)
            else
              relationDrafts.set(row, {
                project_product_id: Number(selected.value),
                project_product_path: selected.path,
                module_id: null,
                module_path: '',
              })
            visibleColumns.value.forEach((item, index) => {
              if (['project-product', 'module-cascader'].includes(item.editor || ''))
                restoreCell(rowIndex, index)
            })
            if (relationDrafts.has(row))
              Message.info('请选择三级模块，选择后将自动保存项目产品和模块')
            void refreshRelationValidationForRow(rowIndex - 1)
          } else {
            if (selected.legacy) {
              restoreCell(rowIndex, columnIndex)
              Message.warning('当前为历史非三级模块，请选择一个三级模块')
              return
            }
            const draft = relationDrafts.get(row)
            const changes: Record<string, FunctionalGridCellValue> = {
              ...(draft
                ? {
                    project_product_id: draft.project_product_id,
                    project_product_path: draft.project_product_path,
                  }
                : {}),
              module_id: Number(selected.value),
              module_path: selected.path,
            }
            relationDrafts.delete(row)
            emitCellChanges(row, rowIndex, column.field, changes)
          }
          return
        }
        const nextValue = parseValue(cellValue, column)
        if (!valuesEqual(nextValue, oldValue)) {
          emitCellChanges(row, rowIndex, column.field, { [column.field]: nextValue })
        }
      } catch (error: unknown) {
        restoreCell(rowIndex, columnIndex)
        Message.warning(error instanceof Error ? error.message : '单元格内容格式不正确')
      }
    })
  }

  const destroyCurrentGrid = () => {
    window.clearTimeout(rebuildTimer)
    rebuildTimer = undefined
    window.cancelAnimationFrame(loadMoreFrame || 0)
    window.clearTimeout(viewportTimer)
    viewportTimer = undefined
    loadMoreFrame = undefined
    try {
      captureFilterCriteria()
      const zoom = worksheet?.getZoom?.()
      if (typeof zoom === 'number' && Number.isFinite(zoom) && zoom >= 0.1 && zoom <= 4)
        retainedZoom = zoom
      const visibleRange = worksheet?.getVisibleRange?.()
      if (visibleRange) {
        retainedViewport = {
          row: Math.max(1, Number(visibleRange.startRow || 1)),
          column: Math.max(0, Number(visibleRange.startColumn || 0)),
        }
      }
    } catch (error) {
      console.warn('保留功能用例表格视图状态失败', error)
    }
    disposables.forEach((item) => {
      try {
        item?.dispose?.()
      } catch {
        console.warn('释放功能用例表格监听失败')
      }
    })
    disposables = []
    const currentUniver = univerInstance
    workbook = null
    worksheet = null
    bufferColumnHidden = false
    univerAPI = null
    univerInstance = null
    syncing = false
    // FUniver 与 Univer 指向同一棵 React 渲染树，只销毁核心实例，避免重复卸载 DOM。
    try {
      currentUniver?.dispose?.()
    } catch {
      console.warn('释放功能用例表格实例失败')
    }
  }

  const disposeGrid = () => {
    gridGeneration += 1
    rowUpdateGeneration += 1
    incrementalLoading.value = false
    destroyCurrentGrid()
  }

  const emitCellChanges = (
    row: FunctionalGridRecord,
    rowIndex: number,
    field: string,
    changes: Record<string, FunctionalGridCellValue>
  ) => {
    const actualChanges = Object.entries(changes).filter(
      ([key, value]) => !valuesEqual(row[key], value)
    )
    if (!actualChanges.length) return
    const persisted: FunctionalGridCellChange['changes'] = {}
    const display: FunctionalGridCellChange['displayChanges'] = {}
    const oldValues: Record<string, unknown> = {}
    for (const [key, value] of actualChanges) {
      const original = row[key]
      oldValues[key] = Array.isArray(original) ? [...original] : original
      if (key === 'project_product_path' || key === 'module_path') {
        if (typeof value === 'string') display[key] = value
      } else persisted[key] = Array.isArray(value) ? [...value] : value
    }
    emit('cell-change', { row, field, changes: persisted, displayChanges: display, oldValues })
    // The owner handles the event synchronously; rejected patches restore the existing record.
    visibleColumns.value.forEach((column, index) => {
      if (actualChanges.some(([key]) => column.field === key || column.displayField === key))
        restoreCell(rowIndex, index)
    })
  }

  const prepareRelationListOptions = async () => {
    if (
      !componentActive ||
      componentUnmounted ||
      !props.editable ||
      !visibleColumns.value.some((column) =>
        ['project-product', 'module-cascader'].includes(column.editor || '')
      )
    )
      return
    const productIds = gridRows.value
      .map((row) => previewRow(row).project_product_id)
      .filter(
        (value): value is string | number => typeof value === 'string' || typeof value === 'number'
      )
    await prepareOptions(productIds)
  }

  const relationListOptions = (
    row: FunctionalGridRecord,
    column: FunctionalGridColumn
  ): RelationListOption[] => {
    if (column.editor === 'project-product') return productOptions.value
    const current = previewRow(row)
    const options = moduleListOptionsCache.get(String(current.project_product_id)) || []
    if (
      current.module_id === null ||
      current.module_id === undefined ||
      options.some((item) => String(item.value) === String(current.module_id))
    ) {
      return options
    }
    const legacyPath = String(current.module_path || '').trim()
    if (!legacyPath || legacyPath === '-') return options
    if (typeof current.module_id !== 'string' && typeof current.module_id !== 'number')
      return options
    return [
      {
        label: legacyPath,
        value: current.module_id,
        path: legacyPath,
        legacy: true,
      },
      ...options,
    ]
  }

  const applyDataValidation = (startDataRow: number, rowCount: number) => {
    if (!worksheet || rowCount <= 0 || !props.editable) return
    visibleColumns.value.forEach((column, columnIndex) => {
      if (['project-product', 'module-cascader'].includes(column.editor || '')) {
        gridRows.value.slice(startDataRow, startDataRow + rowCount).forEach((row, offset) => {
          const options = relationListOptions(row, column)
          if (!options.length) return
          const rule = univerAPI
            .newDataValidation()
            .requireValueInList(
              options.map((item) => item.label),
              false,
              true
            )
            .setOptions({
              allowBlank: true,
              showErrorMessage: true,
              error: `请选择有效的${column.title}`,
              renderMode: univerAPI.Enum.DataValidationRenderMode.ARROW,
            })
            .build()
          worksheet.getRange(startDataRow + offset + 1, columnIndex).setDataValidation(rule)
        })
        return
      }
      if (!column.options?.length || column.editable === false) return
      const rule = univerAPI
        .newDataValidation()
        .requireValueInList(
          column.options.map((item) => item.label),
          column.multiple === true,
          true
        )
        .setOptions({
          allowBlank: true,
          showErrorMessage: true,
          error: `请选择有效的${column.title}`,
        })
        .build()
      const [, formula1] = rule.getCriteriaValues()
      rule.setCriteria(
        rule.getCriteriaType(),
        [
          undefined,
          formula1,
          column.options.map((item) => resolveTagColor(item.colorToken)).join(','),
        ],
        true
      )
      rule.setOptions({ renderMode: univerAPI.Enum.DataValidationRenderMode.CUSTOM })
      worksheet.getRange(startDataRow + 1, columnIndex, rowCount, 1).setDataValidation(rule)
    })
  }

  const refreshRelationValidationForRow = async (dataRow: number) => {
    const targetWorksheet = worksheet,
      targetRow = props.rows[dataRow],
      generation = gridGeneration
    await prepareRelationListOptions()
    if (
      !componentActive ||
      generation !== gridGeneration ||
      props.rows[dataRow] !== targetRow ||
      !targetWorksheet ||
      worksheet !== targetWorksheet
    )
      return
    syncing = true
    try {
      applyDataValidation(dataRow, 1)
    } finally {
      syncing = false
    }
  }

  const retryRelationOptions = async () => {
    const generation = gridGeneration
    await prepareRelationListOptions()
    if (!componentActive || generation !== gridGeneration) return
    if (!worksheet) {
      await createGrid()
      return
    }
    syncing = true
    try {
      applyDataValidation(0, props.rows.length)
    } catch (loadFailure0) {
      void (reportLoadError(loadFailure0, "加载失败，请重试", false), renderError.value = true)
    } finally {
      syncing = false
    }
  }

  const applyBodyStyle = (startDataRow: number, rowCount: number) => {
    if (!worksheet || !container.value || rowCount <= 0 || !visibleColumns.value.length) return
    const containerStyle = getComputedStyle(container.value as HTMLElement)
    const textColor = containerStyle.getPropertyValue('--m-text-2').trim()
    const bodyRange = worksheet.getRange(startDataRow + 1, 0, rowCount, visibleColumns.value.length)
    worksheet.setRowHeights(startDataRow + 1, rowCount, scaleDensityPixels(28))
    bodyRange.setFontFamily(containerStyle.fontFamily)
    bodyRange.setFontSize(scaleDensityPixels(12))
    if (textColor) bodyRange.setFontColor(textColor)
    bodyRange.setVerticalAlignment('middle')
    bodyRange.setBorder(
      univerAPI.Enum.BorderType.ALL,
      univerAPI.Enum.BorderStyleTypes.THIN,
      containerStyle.getPropertyValue('--m-table-border').trim()
    )
    visibleColumns.value.forEach((column, columnIndex) => {
      worksheet
        .getRange(startDataRow + 1, columnIndex, rowCount, 1)
        .setHorizontalAlignment(column.align || (column.options?.length ? 'center' : 'left'))
    })
  }

  const ensureSheetCapacity = (dataRowCount: number) => {
    if (!worksheet) return
    const requiredRows = Math.max(dataRowCount + ROW_BUFFER_COUNT, 60)
    const requiredColumns = Math.max(visibleColumns.value.length + COLUMN_BUFFER_COUNT, 1)
    if (worksheet.getMaxRows() < requiredRows) worksheet.setRowCount(requiredRows)
    if (worksheet.getMaxColumns() < requiredColumns) worksheet.setColumnCount(requiredColumns)
    if (worksheet.getMaxRows() < requiredRows || worksheet.getMaxColumns() < requiredColumns) {
      throw new Error(
        `工作表扩容失败：期望 ${requiredRows} 行/${requiredColumns} 列，实际 ${worksheet.getMaxRows()} 行/${worksheet.getMaxColumns()} 列`
      )
    }
    if (!bufferColumnHidden) {
      worksheet.hideColumns(visibleColumns.value.length, COLUMN_BUFFER_COUNT)
      bufferColumnHidden = true
    }
  }

  const applySheetTheme = () => {
    if (!worksheet || !container.value || !visibleColumns.value.length) return
    const containerStyle = getComputedStyle(container.value as HTMLElement)
    const headerRange = worksheet.getRange(0, 0, 1, visibleColumns.value.length)
    const headerTextColor = containerStyle.getPropertyValue('--m-text').trim()
    headerRange.setFontFamily(containerStyle.fontFamily)
    headerRange.setBorder(
      univerAPI.Enum.BorderType.ALL,
      univerAPI.Enum.BorderStyleTypes.THIN,
      containerStyle.getPropertyValue('--m-table-border').trim()
    )
    headerRange.setFontWeight('bold')
    headerRange.setFontSize(scaleDensityPixels(12))
    if (headerTextColor) headerRange.setFontColor(headerTextColor)
    headerRange.setVerticalAlignment('middle')
    headerRange.setHorizontalAlignment('center')
    const headerBackground = containerStyle.getPropertyValue('--m-table-header-bg').trim()
    if (headerBackground) headerRange.setBackground(headerBackground)
    applyBodyStyle(0, props.rows.length)
  }

  const rebuildFilterRange = () => {
    if (!worksheet || !props.filterable || !visibleColumns.value.length) return
    const criteriaToRestore = new Map(retainedFilterCriteria)
    worksheet.getFilter?.()?.remove?.()
    if (!props.rows.length) return
    const filter = worksheet
      .getRange(0, 0, props.rows.length + 1, visibleColumns.value.length)
      .createFilter()
    const visibleFields = new Set(visibleColumns.value.map((column) => column.field))
    retainedFilterCriteria = new Map(
      [...criteriaToRestore].filter(([field]) => visibleFields.has(field))
    )
    retainedFilterCriteria.forEach((criteria, field) => {
      const columnIndex = visibleColumns.value.findIndex((column) => column.field === field)
      if (columnIndex >= 0) {
        filter?.setColumnFilterCriteria(columnIndex, {
          ...cloneFilterCriteria(criteria),
          colId: columnIndex,
        })
      }
    })
    activeFilterCount.value = retainedFilterCriteria.size
  }

  const setupSheet = () => {
    worksheet = workbook?.getActiveSheet?.()
    if (!worksheet) return
    ensureSheetCapacity(props.rows.length)
    worksheet.setFrozenRows(1)
    const fixedCount = visibleColumns.value.filter((column) => column.fixed === 'left').length
    if (fixedCount) worksheet.setFrozenColumns(fixedCount)
    worksheet.setRowHeight(0, scaleDensityPixels(30))
    visibleColumns.value.forEach((column, index) =>
      worksheet.setColumnWidth(index, scaleDensityPixels(column.width || column.minWidth || 120))
    )
    applySheetTheme()
    applyDataValidation(0, props.rows.length)
    rebuildFilterRange()
    // Keep Univer itself editable and enforce read-only behavior in component events.
    // Native workbook protection opens a misleading "contact the creator" dialog.
    workbook.setEditable(true)
  }

  const appendRowsToSheet = async (startDataRow: number) => {
    if (!componentActive || componentUnmounted) return
    const revision = ++rowUpdateGeneration
    incrementalLoading.value = true
    try {
      const targetWorksheet = worksheet
      if (!targetWorksheet || !visibleColumns.value.length) {
        scheduleRebuild()
        return
      }
      await prepareRelationListOptions()
      if (!componentActive || revision !== rowUpdateGeneration || worksheet !== targetWorksheet)
        return
      const rowCount = props.rows.length - startDataRow
      if (rowCount <= 0) return
      const columnCount = visibleColumns.value.length
      let appendedRange: any
      syncing = true
      try {
        ensureSheetCapacity(props.rows.length)
        appendedRange = targetWorksheet.getRange(startDataRow + 1, 0, rowCount, columnCount)
        targetWorksheet.setRowHeights(startDataRow + 1, rowCount, scaleDensityPixels(28))
        appendedRange.setValues(
          gridRows.value
            .slice(startDataRow)
            .map((row) => visibleColumns.value.map((column) => formatRowValue(row, column)))
        )
      } catch (error) {
        console.error('追加功能用例数据失败', error)
        scheduleRebuild()
        return
      } finally {
        syncing = false
      }
      syncing = true
      try {
        applyBodyStyle(startDataRow, rowCount)
        applyDataValidation(startDataRow, rowCount)
        rebuildFilterRange()
      } catch (error) {
        console.error('补充功能用例表格样式或规则失败', error)
      } finally {
        syncing = false
      }
      scheduleLoadMoreCheck()
    } finally {
      if (componentActive && revision === rowUpdateGeneration) incrementalLoading.value = false
    }
  }

  const replaceRowsInSheet = async (previousRowCount: number) => {
    if (!componentActive || componentUnmounted) return
    const revision = ++rowUpdateGeneration
    incrementalLoading.value = true
    try {
      const targetWorksheet = worksheet
      if (!targetWorksheet || !visibleColumns.value.length) {
        scheduleRebuild()
        return
      }
      await prepareRelationListOptions()
      if (!componentActive || revision !== rowUpdateGeneration || worksheet !== targetWorksheet)
        return
      const rowCount = props.rows.length
      const columnCount = visibleColumns.value.length
      syncing = true
      try {
        ensureSheetCapacity(rowCount)
        if (rowCount) {
          targetWorksheet
            .getRange(1, 0, rowCount, columnCount)
            .setValues(
              gridRows.value.map((row) =>
                visibleColumns.value.map((column) => formatRowValue(row, column))
              )
            )
          applyBodyStyle(0, rowCount)
          applyDataValidation(0, rowCount)
        }
        if (previousRowCount > rowCount) {
          targetWorksheet
            .getRange(rowCount + 1, 0, previousRowCount - rowCount, columnCount)
            .clearContent()
        }
        rebuildFilterRange()
      } catch (error) {
        console.error('更新功能用例表格数据失败', error)
        scheduleRebuild()
        return
      } finally {
        syncing = false
      }
      scheduleLoadMoreCheck()
    } finally {
      if (componentActive && revision === rowUpdateGeneration) incrementalLoading.value = false
    }
  }

  const scheduleLoadMoreCheck = () => {
    if (!componentActive || componentUnmounted) return
    window.cancelAnimationFrame(loadMoreFrame || 0)
    loadMoreFrame = window.requestAnimationFrame(() => {
      loadMoreFrame = undefined
      if (
        !componentActive ||
        componentUnmounted ||
        !props.rows.length ||
        lastLoadMoreRowCount === props.rows.length
      )
        return
      const visibleRange = worksheet?.getVisibleRange?.()
      const visibleEndRow = Number(visibleRange?.endRow ?? 0)
      const triggerRow = Math.max(1, props.rows.length - LOAD_MORE_PRELOAD_ROWS)
      if (visibleEndRow < triggerRow) return
      lastLoadMoreRowCount = props.rows.length
      emit('load-more')
    })
  }

  const createGrid = async () => {
    if (
      !componentActive ||
      !componentMounted ||
      componentUnmounted ||
      !container.value ||
      !visibleColumns.value.length
    )
      return
    const generation = ++gridGeneration
    ++rowUpdateGeneration
    incrementalLoading.value = false
    renderLoading.value = true
    renderError.value = false
    try {
      destroyCurrentGrid()
      await prepareRelationListOptions()
      if (
        componentUnmounted ||
        !componentActive ||
        generation !== gridGeneration ||
        !container.value
      )
        return
      await nextTick()
      if (
        componentUnmounted ||
        !componentActive ||
        generation !== gridGeneration ||
        !container.value
      )
        return
      const targetContainer = container.value
      const result = createFunctionalSheet(targetContainer)
      if (
        componentUnmounted ||
        !componentActive ||
        generation !== gridGeneration ||
        container.value !== targetContainer
      ) {
        result.univer.dispose()
        return
      }
      renderedDensity = scaleDensityPixels(1)
      univerInstance = result.univer
      univerAPI = result.univerAPI
      workbook = univerAPI.createWorkbook({
        name: '功能测试用例',
        sheets: {
          cases: {
            id: 'cases',
            name: '用例',
            zoomRatio: retainedZoom ?? DEFAULT_ZOOM_RATIO,
            defaultRowHeight: scaleDensityPixels(28),
            defaultColumnWidth: scaleDensityPixels(120),
            rowCount: Math.max(props.rows.length + ROW_BUFFER_COUNT, 60),
            columnCount: visibleColumns.value.length + COLUMN_BUFFER_COUNT,
            cellData: buildCellData(),
          },
        },
        sheetOrder: ['cases'],
      })
      setupSheet()
      if (retainedViewport) {
        const viewport = retainedViewport
        retainedViewport = undefined
        viewportTimer = window.setTimeout(() => {
          viewportTimer = undefined
          if (!componentActive || generation !== gridGeneration || !worksheet || !props.rows.length)
            return
          const row = Math.min(viewport.row, props.rows.length)
          const column = Math.min(viewport.column, Math.max(visibleColumns.value.length - 1, 0))
          worksheet.getRange(row, column).activate()
        }, 0)
      }
      // Univer callbacks are an external adapter boundary; disposal alone cannot cancel queued callbacks.
      const listen = (event: unknown, handler: (payload: any) => void) =>
        univerAPI.addEvent(event, (payload: any) => {
          if (componentActive && !componentUnmounted && generation === gridGeneration)
            handler(payload)
        })
      disposables.push(
        listen(univerAPI.Event.SelectionChanged, ({ selections }: any) => {
          emit('selection-change', props.selectable ? selectedDataRows(selections) : [])
        }),
        listen(univerAPI.Event.BeforeSheetEditStart, (event: any) => {
          const column = visibleColumns.value[event.column]
          if (
            !props.editable ||
            event.row === 0 ||
            event.row > props.rows.length ||
            !column ||
            column.editable === false ||
            ['project-product', 'module-cascader'].includes(column.editor || '') ||
            Boolean(column.options?.length)
          )
            event.cancel = true
        }),
        listen(univerAPI.Event.BeforeClipboardPaste, (event: any) => {
          if (!props.editable) event.cancel = true
        }),
        listen(univerAPI.Event.BeforeCommandExecute, interceptStructureCommand),
        listen(univerAPI.Event.CommandExecuted, persistNativeColumnWidth),
        listen(univerAPI.Event.SheetValueChanged, ({ effectedRanges }: any) => {
          syncChangedRanges(effectedRanges)
        }),
        listen(univerAPI.Event.SheetRangeFiltered, () => {
          if (syncing) return
          captureFilterCriteria(true)
        }),
        listen(univerAPI.Event.SheetRangeFilterCleared, () => {
          if (syncing) return
          retainedFilterCriteria.clear()
          activeFilterCount.value = 0
          emit('filter-change', { active: false, activeColumns: 0, filteredOutRows: [] })
        }),
        listen(univerAPI.Event.Scroll, scheduleLoadMoreCheck)
      )
      captureFilterCriteria(true)
      scheduleLoadMoreCheck()
    } catch (loadFailure1) {
      if (componentActive && generation === gridGeneration) {
        destroyCurrentGrid()
        void (reportLoadError(loadFailure1, "加载失败，请重试", false), renderError.value = true)
      }
    } finally {
      if (componentActive && generation === gridGeneration) renderLoading.value = false
    }
  }

  const scheduleRebuild = () => {
    if (!componentMounted || !componentActive || componentUnmounted || !container.value) return
    window.clearTimeout(rebuildTimer)
    rebuildTimer = window.setTimeout(() => {
      void createGrid()
    }, 0)
  }

  const emitViewChange = () => {
    emit(
      'view-change',
      innerColumns.value.map((item) => ({ ...item }))
    )
    scheduleRebuild()
  }
  const toggleAll = (checked: boolean | (string | number | boolean)[]) => {
    const visible = checked === true
    innerColumns.value.forEach((item) => (item.visible = visible))
    if (!visible && innerColumns.value.length) {
      innerColumns.value[0].visible = true
      Message.info('表格至少需要保留一列')
    }
    emitViewChange()
  }
  const resetColumns = () => {
    innerColumns.value = defaultColumns.value.map((item) => ({ ...item }))
    emitViewChange()
  }
  watch(
    () => props.columns,
    (columns) => {
      applyColumns(columns)
      scheduleRebuild()
    },
    { immediate: true, deep: true }
  )
  watch(
    () => props.rows,
    (nextRows, previousRows) => {
      if (!componentActive || componentUnmounted) return
      const appended =
        previousRows.length > 0 &&
        nextRows.length > previousRows.length &&
        previousRows.every(
          (row, index) =>
            readGridRecord(row)[props.rowKey] ===
            (nextRows[index] && readGridRecord(nextRows[index])[props.rowKey])
        )
      if (!appended) {
        lastLoadMoreRowCount = 0
        relationDrafts.clear()
      }
      if (appended) void appendRowsToSheet(previousRows.length)
      else void replaceRowsInSheet(previousRows.length)
    }
  )
  watch(
    () => props.editable,
    (editable) => {
      const hadDraft = relationDrafts.size > 0
      if (!editable) relationDrafts.clear()
      if (!editable && hadDraft) void replaceRowsInSheet(props.rows.length)
      else if (editable) void retryRelationOptions()
    }
  )

  const handleThemeChange = () => scheduleRebuild()
  const handleDensityChange = () => scheduleRebuild()

  watch(
    () => props.contextKey,
    () => {
      resetOptions()
      relationDrafts.clear()
      disposeGrid()
      retainedFilterCriteria.clear()
      retainedViewport = undefined
      retainedZoom = undefined
      activeFilterCount.value = 0
      lastLoadMoreRowCount = 0
      renderLoading.value = false
      renderError.value = false
      scheduleRebuild()
    },
    { flush: 'sync' }
  )

  onMounted(() => {
    componentUnmounted = false
    componentMounted = true
    window.addEventListener('mango-theme-change', handleThemeChange)
    window.addEventListener('mango-density-change', handleDensityChange)
    void createGrid()
  })
  onDeactivated(() => {
    componentActive = false
    relationDrafts.clear()
    resetOptions()
    disposeGrid()
    renderLoading.value = false
    renderError.value = false
  })
  onActivated(() => {
    if (componentActive) return
    componentActive = true
    void createGrid()
  })
  onBeforeUnmount(() => {
    componentUnmounted = true
    componentActive = false
    componentMounted = false
    window.removeEventListener('mango-theme-change', handleThemeChange)
    window.removeEventListener('mango-density-change', handleDensityChange)
    resetOptions()
    disposeGrid()
  })

  defineExpose({
    getColumns: () => innerColumns.value,
    clearFilters,
    refreshRowCells,
    undo: () => univerAPI?.undo?.(),
    redo: () => univerAPI?.redo?.(),
  })
</script>

<style lang="less" scoped>
  .mango-functional-grid {
    display: flex;
    min-height: 0;
    height: 100%;
    flex-direction: column;
    gap: 8px;
  }

  .mango-functional-grid__toolbar,
  .mango-functional-grid__summary,
  .mango-functional-grid__column-actions,
  .mango-functional-grid__column-item {
    display: flex;
    align-items: center;
  }

  .mango-functional-grid__toolbar {
    flex: none;
    justify-content: space-between;
    min-height: 38px;
    padding: 5px 8px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
    flex-wrap: wrap;
    gap: 8px;
  }

  .mango-functional-grid__summary {
    min-width: 0;
    flex-wrap: wrap;
    gap: 12px;
    color: var(--m-text-2);
    font-size: 13px;
  }

  .mango-functional-grid__hint {
    color: var(--m-text-3);
  }

  .mango-functional-grid__sheet-shell {
    height: 0;
    min-height: 0;
    flex: 1;
    overflow: hidden;
    border: 1px solid var(--m-border-strong);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
    box-shadow: 0 2px 8px color-mix(in srgb, var(--m-text) 6%, transparent);
  }

  .mango-functional-grid__spin,
  .mango-functional-grid__sheet {
    width: 100%;
    height: 100%;
  }

  .mango-functional-grid__sheet {
    height: calc(100% - 8px);
    background: var(--m-surface);
    color: var(--m-text-2);
    font-family: inherit;
  }

  .mango-functional-grid__spin :deep(> .mango-panel-spin__content) {
    height: 100%;
  }

  .mango-functional-grid__column-panel {
    width: 240px;
    max-height: 420px;
    padding: 2px;
    overflow: auto;
  }

  .mango-functional-grid__column-actions {
    justify-content: space-between;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-functional-grid__column-item {
    gap: 6px;
    padding: 6px;
    border-radius: var(--m-radius-sm);
    transition: background-color 120ms ease;

    &:hover {
      background: var(--m-surface-soft);
    }
  }

  .mango-functional-grid__drag {
    color: var(--m-muted);
    cursor: move;
  }

  .mango-functional-grid__sheet :deep([data-u-comp='button']) {
    border-radius: var(--m-radius-sm);
  }

  .mango-functional-grid__sheet :deep([data-u-comp='button']:hover) {
    background: var(--m-primary-soft);
    color: var(--m-primary);
  }
</style>
