type ChartLike = {
  getOption: () => unknown
  isDisposed?: () => boolean
  resize: () => void
  setOption: (option: any, ...args: any[]) => unknown
}

type DensityChartRecord = {
  chart: ChartLike
  rawSetOption: ChartLike['setOption']
  scale: number
}

const records = new Set<DensityChartRecord>()
const densityScalarKeys = new Set([
  'barGap',
  'barMaxWidth',
  'barMinWidth',
  'barWidth',
  'borderRadius',
  'borderWidth',
  'fontSize',
  'itemGap',
  'itemHeight',
  'itemWidth',
  'lineHeight',
  'margin',
  'scaleSize',
  'symbolSize',
])
const densityPositionKeys = new Set(['bottom', 'left', 'right', 'top'])
let listenerInstalled = false

export function getDisplayScale() {
  if (typeof document === 'undefined') return 1
  return (
    Number(getComputedStyle(document.documentElement).getPropertyValue('--m-ui-scale').trim()) || 1
  )
}

function scaleNumber(value: number, ratio: number) {
  if (value === 0) return 0
  const scaled = Number((value * ratio).toFixed(2))
  return Math.abs(value) <= 1 ? Math.sign(value) * Math.max(1, Math.abs(scaled)) : scaled
}

function scaleOptionValue(value: any, ratio: number, key = '', parentKey = ''): any {
  if (Array.isArray(value)) {
    if (key === 'padding' || key === 'symbolOffset') {
      return value.map((item) =>
        typeof item === 'number' ? scaleNumber(item, ratio) : scaleOptionValue(item, ratio)
      )
    }
    return value.map((item) => scaleOptionValue(item, ratio, '', key))
  }
  if (!value || typeof value !== 'object') {
    if (typeof value !== 'number') return value
    if (densityScalarKeys.has(key)) return scaleNumber(value, ratio)
    if (densityPositionKeys.has(key) && ['grid', 'legend', 'title'].includes(parentKey)) {
      return scaleNumber(value, ratio)
    }
    if (key === 'width' && ['lineStyle', 'axisLine', 'splitLine'].includes(parentKey)) {
      return scaleNumber(value, ratio)
    }
    return value
  }

  const currentContext = key || parentKey
  return Object.fromEntries(
    Object.entries(value).map(([childKey, childValue]) => [
      childKey,
      scaleOptionValue(childValue, ratio, childKey, currentContext),
    ])
  )
}

function installDensityListener() {
  if (listenerInstalled || typeof window === 'undefined') return
  listenerInstalled = true
  window.addEventListener('mango-density-change', (event) => {
    const nextScale = Number((event as CustomEvent<{ scale?: number }>).detail?.scale) || 1
    records.forEach((record) => {
      if (record.chart.isDisposed?.()) {
        records.delete(record)
        return
      }
      const ratio = nextScale / record.scale
      if (Math.abs(ratio - 1) < 0.001) return
      const currentOption = record.chart.getOption()
      record.scale = nextScale
      record.rawSetOption(scaleOptionValue(currentOption, ratio), { notMerge: true })
      record.chart.resize()
    })
  })
}

export function makeChartDensityAware<T extends ChartLike>(chart: T): T {
  const existing = Array.from(records).find((record) => record.chart === chart)
  if (existing) return chart

  const rawSetOption = chart.setOption.bind(chart)
  const record: DensityChartRecord = {
    chart,
    rawSetOption,
    scale: getDisplayScale(),
  }
  chart.setOption = ((option: any, ...args: any[]) =>
    rawSetOption(scaleOptionValue(option, record.scale), ...args)) as T['setOption']
  records.add(record)
  installDensityListener()
  return chart
}
