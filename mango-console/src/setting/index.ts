import { DeviceType, DisplayDensity } from '@/store/types'

export const projectName = '芒果测试平台'

export default {
  theme: 'light',
  sideTheme: 'white',
  themeColor: '#165dff',
  themePreset: 'mango-blue',
  projectName,
  layoutMode: 'ltr',
  sideWidth: 199,
  displayDensity: DisplayDensity.AUTO,
  pageAnim: 'opacity',
  isFixedNavBar: true,
  deviceType: DeviceType.PC,
  isCollapse: false,
  flexMainHeight: false,
  mainHeight: document.body.clientHeight,
  actionBar: {
    isShowSearch: true,
    isShowMessage: true,
    isShowRefresh: true,
    isShowFullScreen: true,
  },
}

export const DRIVER = 'Mango Actuator'
export const SERVER = 'Mango Server'
export const WEB = 'mango-console'
export const fieldNames = { value: 'key', label: 'title' }
