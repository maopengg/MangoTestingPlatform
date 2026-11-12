import { DisplayDensity } from '@/store/types'
import { ref } from 'vue'

const AUTO_DESIGN_VIEWPORT_WIDTH = 1900
const TWO_K_VIEWPORT_WIDTH = 2560
const FOUR_K_VIEWPORT_WIDTH = 3840
const TWO_K_UI_SCALE = 1.15
const FOUR_K_UI_SCALE = 1.35
let autoScale2k = TWO_K_UI_SCALE
let autoScale4k = FOUR_K_UI_SCALE

export function setAutoDisplayScales(twoK: number, fourK: number) {
  autoScale2k = Number.isFinite(twoK) ? clamp(twoK, 1, 3) : TWO_K_UI_SCALE
  autoScale4k = Math.max(autoScale2k, Number.isFinite(fourK) ? clamp(fourK, 1, 3) : FOUR_K_UI_SCALE)
}
// 小屏保留可用下限；4K 及更宽屏幕不再继续放大，避免超宽屏控件和文字失衡。
const MIN_UI_SCALE = 0.5
const MAX_MANUAL_UI_SCALE = 3

const densityDesignWidths: Record<DisplayDensity, number> = {
  [DisplayDensity.AUTO]: AUTO_DESIGN_VIEWPORT_WIDTH,
  [DisplayDensity.COMPACT]: 2100,
  [DisplayDensity.STANDARD]: AUTO_DESIGN_VIEWPORT_WIDTH,
  [DisplayDensity.COMFORTABLE]: 1710,
}

export const displayDensityScale = ref(1)

export function scaleDensityPixels(value: number) {
  return Number((value * displayDensityScale.value).toFixed(4))
}

export function scaleDensityLength(value: unknown) {
  if (typeof value === 'number') return scaleDensityPixels(value)
  if (typeof value !== 'string') return value
  return value.replace(/(-?\d*\.?\d+)px\b/g, (_match, rawValue) => {
    return `${scaleDensityPixels(Number(rawValue))}px`
  })
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max)
}

function interpolateScale(
  viewportWidth: number,
  startWidth: number,
  startScale: number,
  endWidth: number,
  endScale: number
) {
  const progress = (viewportWidth - startWidth) / (endWidth - startWidth)
  return startScale + (endScale - startScale) * progress
}

export function getAutoDisplayScale(viewportWidth: number) {
  if (viewportWidth <= AUTO_DESIGN_VIEWPORT_WIDTH) {
    return clamp(viewportWidth / AUTO_DESIGN_VIEWPORT_WIDTH, MIN_UI_SCALE, 1)
  }
  if (viewportWidth <= TWO_K_VIEWPORT_WIDTH) {
    return interpolateScale(
      viewportWidth,
      AUTO_DESIGN_VIEWPORT_WIDTH,
      1,
      TWO_K_VIEWPORT_WIDTH,
      autoScale2k
    )
  }
  if (viewportWidth <= FOUR_K_VIEWPORT_WIDTH) {
    return interpolateScale(
      viewportWidth,
      TWO_K_VIEWPORT_WIDTH,
      autoScale2k,
      FOUR_K_VIEWPORT_WIDTH,
      autoScale4k
    )
  }
  return autoScale4k
}

function getLayoutViewportWidth() {
  // clientWidth 不包含传统滚动条，避免 Windows 与 macOS 的滚动条策略造成十几像素偏差。
  return document.documentElement.clientWidth || window.innerWidth
}

/**
 * 自动模式使用连续锚点缩放：1900px 为 1，2K 为 1.15，4K 为 1.35。
 * 手动密度模式仍按各自设计宽度计算，便于用户主动调整信息密度。
 */
export function applyDisplayDensity(mode: DisplayDensity): number {
  if (typeof document === 'undefined' || typeof window === 'undefined') return 1

  const designWidth = densityDesignWidths[mode] || AUTO_DESIGN_VIEWPORT_WIDTH
  const viewportWidth = getLayoutViewportWidth()
  const scale = Number(
    (mode === DisplayDensity.AUTO
      ? getAutoDisplayScale(viewportWidth)
      : clamp(viewportWidth / designWidth, MIN_UI_SCALE, MAX_MANUAL_UI_SCALE)
    ).toFixed(4)
  )
  const root = document.documentElement
  const previousScale = Number(root.style.getPropertyValue('--m-ui-scale')) || 1
  const changed = Math.abs(previousScale - scale) >= 0.001

  root.dataset.mangoDensityMode = mode
  root.dataset.mangoDensityScale = String(scale)
  displayDensityScale.value = scale
  root.style.setProperty('--m-ui-scale', String(scale))
  root.style.fontSize = `${Number((16 * scale).toFixed(4))}px`
  root.style.setProperty('--m-design-viewport-width', `${designWidth}px`)

  if (changed) {
    window.requestAnimationFrame(() => {
      // ECharts 与其他尺寸监听组件在全局比例变化后重新计算绘制区域。
      window.dispatchEvent(new CustomEvent('mango-density-change', { detail: { scale } }))
      window.dispatchEvent(new Event('resize'))
    })
  }
  return scale
}
