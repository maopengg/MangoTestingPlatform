export type GanttZoom = 'day' | 'week'
const DAY_MILLISECONDS = 86400000

// Date-only scheduling uses calendar days, independent of local timezone and DST.
export function ganttCalendarDay(value: string | null | undefined): number | null {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null
  const [year, month, day] = value.split('-').map(Number)
  const date = new Date(0)
  date.setUTCHours(0, 0, 0, 0)
  date.setUTCFullYear(year, month - 1, day)
  if (
    date.getUTCFullYear() !== year ||
    date.getUTCMonth() !== month - 1 ||
    date.getUTCDate() !== day
  )
    return null
  return date.getTime() / DAY_MILLISECONDS
}

export interface GanttScale {
  start: number
  days: number
  unitDays: number
  pixelsPerDay: number
  width: number
  units: Array<{ key: number; label: string; weekend: boolean; width: number }>
}

export function createGanttScale(
  startValue: string | null | undefined,
  endValue: string | null | undefined,
  zoom: GanttZoom,
  sizes: { minimumWidth: number; dayWidth: number; weekWidth: number }
): GanttScale | null {
  const start = ganttCalendarDay(startValue),
    end = ganttCalendarDay(endValue)
  if (start === null || end === null || end < start) return null
  if (!Object.values(sizes).every((value) => Number.isFinite(value) && value > 0)) return null
  const days = end - start + 1,
    unitDays = zoom === 'week' ? 7 : 1
  const pixelsPerDay = Math.max(
    sizes.minimumWidth / days,
    (zoom === 'week' ? sizes.weekWidth : sizes.dayWidth) / unitDays
  )
  return {
    start,
    days,
    unitDays,
    pixelsPerDay,
    width: days * pixelsPerDay,
    units: Array.from({ length: Math.ceil(days / unitDays) }, (_, index) => {
      const offset = index * unitDays,
        date = new Date((start + offset) * DAY_MILLISECONDS)
      return {
        key: start + offset,
        label: `${date.getUTCMonth() + 1}/${date.getUTCDate()}${zoom === 'week' ? ' 起' : ''}`,
        weekend: zoom === 'day' && [0, 6].includes(date.getUTCDay()),
        width: Math.min(unitDays, days - offset) * pixelsPerDay,
      }
    }),
  }
}

export function ganttBarGeometry(
  scale: GanttScale | null,
  startValue: string | null,
  endValue: string | null,
  inset: number
) {
  const start = ganttCalendarDay(startValue),
    end = ganttCalendarDay(endValue)
  if (!scale || start === null || end === null || end < start) return null
  const first = Math.max(0, start - scale.start),
    last = Math.min(scale.days - 1, end - scale.start)
  if (first > last) return null
  const rangeWidth = (last - first + 1) * scale.pixelsPerDay
  const padding = Math.min(Math.max(0, inset), rangeWidth / 4)
  return { left: first * scale.pixelsPerDay + padding, width: rangeWidth - padding * 2 }
}

export function ganttTodayOffset(scale: GanttScale | null, value: string | null | undefined) {
  const today = ganttCalendarDay(value)
  if (!scale || today === null) return null
  const offset = today - scale.start
  return offset >= 0 && offset < scale.days ? (offset + 0.5) * scale.pixelsPerDay : null
}
