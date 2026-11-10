import { nextTick, onBeforeUnmount, onDeactivated, onMounted, watch, type Ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import printJS from 'print-js'
import { toPng } from 'html-to-image'
import { chartHtml } from '../chart-boundary'
import { effectivenessPrintStyle, reportFileName } from '../export-layout'

interface Options {
  contextKey(): string
  available(): boolean
  loading(): boolean
  title(): string
  printing: Ref<boolean>
  imageExporting: Ref<boolean>
  reportMode: Ref<boolean>
  filterVisible: Ref<boolean>
}
interface ExportJob {
  key: string
  kind: 'image' | 'print'
  title: string
  previousMode: boolean
  cancelled: boolean
  rasterizing: boolean
  abort: AbortController
  frameId: string
}
let exportSequence = 0

export function useEffectivenessExport(options: Options) {
  let job: ExportJob | null = null, imageOwner: ExportJob | null = null, disposed = false
  const current = (value: ExportJob) => !disposed && job === value && !value.cancelled && options.available() && !options.loading() && value.key === options.contextKey()
  function removePrintFrame(value: ExportJob) {
    const frame = document.getElementById(value.frameId)
    if (frame) { frame.onload = null; frame.remove() }
  }
  function finish(value: ExportJob) {
    if (job !== value) return
    job = null
    value.cancelled = true; value.abort.abort()
    if (value.kind === 'print') {
      options.printing.value = false
      removePrintFrame(value)
      options.reportMode.value = value.previousMode
    } else if (!value.rasterizing && imageOwner === value) { imageOwner = null; options.imageExporting.value = false }
  }
  function invalidate() { if (job) finish(job) }
  function start(kind: ExportJob['kind']): ExportJob | null {
    if (disposed || !options.available()) return null
    if (options.loading() || options.printing.value || options.imageExporting.value) {
      Message.warning('请等待全部加载完成'); return null
    }
    const previousMode = options.reportMode.value
    if (kind === 'print') options.reportMode.value = true
    const value: ExportJob = { key: options.contextKey(), kind, title: options.title(), previousMode, cancelled: false, rasterizing: false, abort: new AbortController(), frameId: `mango-effectiveness-print-${++exportSequence}` }
    job = value
    options.filterVisible.value = false
    if (kind === 'print') options.printing.value = true
    else { imageOwner = value; options.imageExporting.value = true }
    return value
  }
  function waitForFrame(signal: AbortSignal): Promise<void> {
    if (signal.aborted) return Promise.resolve()
    return new Promise(resolve => {
      let frame = 0
      const done = () => { signal.removeEventListener('abort', cancel); resolve() }
      const cancel = () => { cancelAnimationFrame(frame); done() }
      signal.addEventListener('abort', cancel, { once: true })
      frame = requestAnimationFrame(done)
    })
  }
  async function waitForReport(value: ExportJob): Promise<boolean> {
    await nextTick()
    if (!current(value)) return false
    window.dispatchEvent(new Event('resize'))
    const fonts = document.fonts?.ready
    if (fonts) await new Promise<void>((resolve, reject) => {
      const signal = value.abort.signal
      const cancel = () => { signal.removeEventListener('abort', cancel); resolve() }
      if (signal.aborted) return resolve()
      signal.addEventListener('abort', cancel, { once: true })
      Promise.resolve(fonts).then(() => { signal.removeEventListener('abort', cancel); resolve() }, error => { signal.removeEventListener('abort', cancel); reject(error) })
    })
    if (!current(value)) return false
    await waitForFrame(value.abort.signal)
    if (!current(value)) return false
    await waitForFrame(value.abort.signal)
    return current(value)
  }
  async function printReport(): Promise<void> {
    const value = start('print')
    if (!value) return
    try {
      if (!await waitForReport(value)) return
      if (!document.getElementById('mango-effectiveness-report-image')) throw new Error('Missing report')
      printJS({
        printable: 'mango-effectiveness-report-image', type: 'html', targetStyles: ['*'], scanStyles: true,
        maxWidth: 10000, font_size: '', style: effectivenessPrintStyle, frameId: value.frameId,
        documentTitle: chartHtml(reportFileName(value.title, '').replace(/\.$/, '')),
        onPrintDialogClose: () => finish(value),
        onError: () => { if (current(value)) Message.error('打印报告失败，请重试'); finish(value) },
      })
    } catch {
      if (current(value)) Message.error('打印报告失败，请重试')
      finish(value)
    } finally {
      if (!current(value)) finish(value)
    }
  }
  async function downloadReportImage(): Promise<void> {
    const value = start('image')
    if (!value) return
    try {
      if (!await waitForReport(value)) return
      const report = document.getElementById('mango-effectiveness-report-image')
      if (!report) throw new Error('Missing report')
      const width = Math.ceil(report.scrollWidth), height = Math.ceil(report.scrollHeight)
      if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) throw new Error('Invalid report size')
      const pixelRatio = Math.max(1, Math.min(3, 30000 / height, 30000 / width))
      const backgroundColor = getComputedStyle(report).backgroundColor || getComputedStyle(document.documentElement).getPropertyValue('--m-surface').trim()
      value.rasterizing = true
      const dataUrl = await toPng(report, { width, height, pixelRatio, cacheBust: true, backgroundColor, style: { margin: '0', transform: 'none', boxShadow: 'none' } })
      if (!current(value)) return
      const link = document.createElement('a')
      link.download = reportFileName(value.title, 'png'); link.href = dataUrl
      try { link.click() } finally { link.remove() }
      Message.success(`高清图片已生成（${pixelRatio.toFixed(1)} 倍清晰度）`)
    } catch { if (current(value)) Message.error('高清图片生成失败，请稍后重试') }
    finally {
      // html-to-image has no cancellation API; retain its physical lock until it actually settles.
      if (imageOwner === value) { imageOwner = null; options.imageExporting.value = false }
      value.rasterizing = false
      finish(value)
    }
  }
  watch(() => [options.contextKey(), options.loading()], () => { if (job && !current(job)) invalidate() }, { flush: 'sync' })
  function visibilityChanged() { if (document.visibilityState !== 'visible') invalidate() }
  onMounted(() => document.addEventListener('visibilitychange', visibilityChanged))
  onDeactivated(invalidate)
  onBeforeUnmount(() => { disposed = true; invalidate(); document.removeEventListener('visibilitychange', visibilityChanged) })
  return { printReport, downloadReportImage }
}
