type TableScrollbarBinding = {
  table: HTMLElement
  target: HTMLElement
  proxy: HTMLDivElement
  spacer: HTMLDivElement
  resizeObserver: ResizeObserver
  onProxyScroll: () => void
  onTargetScroll: () => void
}

const TABLE_SELECTOR = '.arco-table'
const TARGET_SELECTOR =
  '.arco-table-content.arco-scrollbar-container, .arco-table-body.arco-scrollbar-container, .arco-table-content, .arco-table-body'
const MANAGED_TABLE_SELECTOR =
  '.mango-native-scroll-table, .mango-sticky-horizontal-table, .mango-table-body__content--sticky-horizontal-scroll'

function isManagedByTableComponent(table: HTMLElement) {
  return Boolean(table.closest(MANAGED_TABLE_SELECTOR))
}

function findScrollTarget(table: HTMLElement) {
  const candidates = Array.from(table.querySelectorAll<HTMLElement>(TARGET_SELECTOR))
  return (
    candidates.find(
      (candidate) =>
        !candidate.closest('.arco-table-header') &&
        candidate.scrollWidth > candidate.clientWidth + 1
    ) ||
    candidates.find((candidate) => !candidate.closest('.arco-table-header')) ||
    candidates[0] ||
    null
  )
}

function getVisibleRect(element: HTMLElement) {
  const rect = element.getBoundingClientRect()
  let top = Math.max(rect.top, 0)
  let right = Math.min(rect.right, window.innerWidth)
  let bottom = Math.min(rect.bottom, window.innerHeight)
  let left = Math.max(rect.left, 0)
  let parent = element.parentElement

  while (parent && parent !== document.body && parent !== document.documentElement) {
    const style = window.getComputedStyle(parent)
    if (/(auto|scroll|hidden|clip)/.test(`${style.overflow}${style.overflowX}${style.overflowY}`)) {
      const parentRect = parent.getBoundingClientRect()
      top = Math.max(top, parentRect.top)
      right = Math.min(right, parentRect.right)
      bottom = Math.min(bottom, parentRect.bottom)
      left = Math.max(left, parentRect.left)
    }
    parent = parent.parentElement
  }

  return { top, right, bottom, left }
}

function getStackingLevel(element: HTMLElement) {
  let level = 20
  let current: HTMLElement | null = element
  while (current && current !== document.body) {
    const zIndex = Number.parseInt(window.getComputedStyle(current).zIndex, 10)
    if (Number.isFinite(zIndex)) level = Math.max(level, zIndex + 2)
    current = current.parentElement
  }
  return level
}

export function setupTableStickyScrollbars() {
  const bindings = new Map<HTMLElement, TableScrollbarBinding>()
  let frame = 0

  function removeBinding(table: HTMLElement) {
    const binding = bindings.get(table)
    if (!binding) return
    binding.resizeObserver.disconnect()
    binding.proxy.removeEventListener('scroll', binding.onProxyScroll)
    binding.target.removeEventListener('scroll', binding.onTargetScroll)
    binding.proxy.remove()
    binding.table.classList.remove('mango-table-sticky-scrollbar-active')
    bindings.delete(table)
  }

  function createBinding(table: HTMLElement, target: HTMLElement) {
    const proxy = document.createElement('div')
    const spacer = document.createElement('div')
    proxy.className = 'mango-table-sticky-scrollbar'
    spacer.className = 'mango-table-sticky-scrollbar__spacer'
    proxy.appendChild(spacer)
    document.body.appendChild(proxy)

    let syncing = false
    const onProxyScroll = () => {
      if (syncing) return
      syncing = true
      target.scrollLeft = proxy.scrollLeft
      syncing = false
    }
    const onTargetScroll = () => {
      if (syncing) return
      syncing = true
      proxy.scrollLeft = target.scrollLeft
      syncing = false
    }
    proxy.addEventListener('scroll', onProxyScroll, { passive: true })
    target.addEventListener('scroll', onTargetScroll, { passive: true })

    const resizeObserver = new ResizeObserver(scheduleUpdate)
    resizeObserver.observe(table)
    resizeObserver.observe(target)
    table.classList.add('mango-table-sticky-scrollbar-active')
    bindings.set(table, {
      table,
      target,
      proxy,
      spacer,
      resizeObserver,
      onProxyScroll,
      onTargetScroll,
    })
  }

  function scanTables() {
    const tables = Array.from(document.querySelectorAll<HTMLElement>(TABLE_SELECTOR))
    const currentTables = new Set(tables)
    bindings.forEach((_, table) => {
      if (!currentTables.has(table) || !table.isConnected) removeBinding(table)
    })

    tables.forEach((table) => {
      // 原生滚动表格及公共滚动容器已经自行提供滑块。
      // 全局兜底再次接管会在完整页面加载后生成第二条滑块。
      if (isManagedByTableComponent(table)) {
        removeBinding(table)
        return
      }
      const target = findScrollTarget(table)
      const binding = bindings.get(table)
      if (!target) {
        removeBinding(table)
        return
      }
      if (binding?.target !== target) {
        removeBinding(table)
        createBinding(table, target)
      } else if (!binding) {
        createBinding(table, target)
      }
    })
  }

  function updateBindings() {
    frame = 0
    scanTables()
    bindings.forEach(({ table, target, proxy, spacer }) => {
      const hasHorizontalOverflow = target.scrollWidth > target.clientWidth + 1
      // Arco 在设置 scroll.y 后，`.arco-table` 外壳的布局高度可能只覆盖表头，
      // 实际表体则由内部滚动容器撑满可用区域。同步轨道必须以真正承载
      // 横向滚动的容器为定位基准，否则会错误地贴到表头下方。
      const rect = getVisibleRect(target)
      const visible =
        hasHorizontalOverflow &&
        rect.right - rect.left > 24 &&
        rect.bottom - rect.top > 24 &&
        rect.bottom > 0 &&
        rect.top < window.innerHeight

      if (!visible) {
        proxy.style.display = 'none'
        return
      }

      proxy.style.display = 'block'
      proxy.style.left = `${rect.left}px`
      proxy.style.width = `${rect.right - rect.left}px`
      proxy.style.bottom = `${Math.max(0, window.innerHeight - rect.bottom)}px`
      proxy.style.zIndex = String(getStackingLevel(table))
      spacer.style.width = `${target.scrollWidth}px`
      proxy.scrollLeft = target.scrollLeft
    })
  }

  function scheduleUpdate() {
    if (frame) return
    frame = window.requestAnimationFrame(updateBindings)
  }

  const mutationObserver = new MutationObserver(scheduleUpdate)
  mutationObserver.observe(document.body, { childList: true, subtree: true })
  window.addEventListener('resize', scheduleUpdate, { passive: true })
  document.addEventListener('scroll', scheduleUpdate, true)
  scheduleUpdate()

  return () => {
    if (frame) window.cancelAnimationFrame(frame)
    mutationObserver.disconnect()
    window.removeEventListener('resize', scheduleUpdate)
    document.removeEventListener('scroll', scheduleUpdate, true)
    Array.from(bindings.keys()).forEach(removeBinding)
  }
}
