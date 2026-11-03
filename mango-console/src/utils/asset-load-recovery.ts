import { Modal } from '@arco-design/web-vue'
import type { Router } from 'vue-router'
import { reportFrontendError } from './system-error-reporter'

function isModuleLoadError(error: unknown) {
  const message = error instanceof Error ? error.message : String(error || '')
  return /Failed to fetch dynamically imported module|error loading dynamically imported module|Importing a module script failed|Unable to preload CSS|Loading (?:CSS )?chunk [\w-]+ failed/i.test(message)
}

function isAppAsset(target: EventTarget | null) {
  if (!(target instanceof HTMLScriptElement || target instanceof HTMLLinkElement)) return false
  const resource = target instanceof HTMLScriptElement ? target.src : target.href
  try {
    const url = new URL(resource, window.location.origin)
    return url.origin === window.location.origin && /\/assets\/[^/]+[.-][\w-]{6,}\.(?:js|css)$/.test(url.pathname)
  } catch {
    return false
  }
}

export function setupAssetLoadRecovery(router: Pick<Router, 'onError'>) {
  let promptOpen = false
  let lastPromptAt = -Infinity

  function showRecovery() {
    if (promptOpen || Date.now() - lastPromptAt < 60_000) return
    promptOpen = true
    lastPromptAt = Date.now()
    Modal.warning({
      title: '页面资源加载失败',
      content: '平台可能已更新，或网络暂时中断。请先保留当前未保存的内容，再刷新页面重试。',
      okText: '刷新页面',
      hideCancel: true,
      closable: false,
      maskClosable: false,
      escToClose: false,
      onOk: () => window.location.reload(),
      onClose: () => { promptOpen = false },
    })
  }

  router.onError((error) => {
    if (!isModuleLoadError(error)) return
    reportFrontendError(error, 'router:load')
    showRecovery()
  })
  window.addEventListener('error', (event) => {
    if (isAppAsset(event.target)) showRecovery()
  }, true)
  window.addEventListener('unhandledrejection', (event) => {
    if (!isModuleLoadError(event.reason)) return
    reportFrontendError(event.reason, 'module:load')
    showRecovery()
  })
}
