import { createApp } from 'vue'
import App from './App.vue'
import router, { setupRouter } from './router'
import './styles'
import { setupGlobalComponent } from '@/layouts'
import { setupPinia } from '@/store/pinia'
import setupRouterGuard from './router/guard'
import { applyDisplayDensity } from '@/hooks/useDisplayDensity'
import { DisplayDensity } from '@/store/types'
import { setupFrontendErrorReporting } from '@/utils/system-error-reporter'
import { setupAssetLoadRecovery } from '@/utils/asset-load-recovery'
// import 'default-passive-events'
// 如果需要对接正式的接口，需要下面代码注释或者删除
// import { setupMock } from '../mock'

function setup() {
  // 首次绘制前先应用自动设计视口，持久化的手动偏好会在 Layout 初始化时覆盖。
  applyDisplayDensity(DisplayDensity.AUTO)
  const app = createApp(App)
  setupPinia(app)
  setupFrontendErrorReporting(app)
  setupAssetLoadRecovery(router)
  setupRouter(app)
  setupRouterGuard()
  setupGlobalComponent(app)
  // 如果需要对接正式的接口，需要下面代码注释或者删除
  // setupMock()
  app.mount('#app')
}

// 启动项目
setup()
