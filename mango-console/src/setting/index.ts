import { DeviceType } from '@/store/types'

export const projectName = 'MangoAutoTest'

export default {
  theme: 'light',
  sideTheme: 'white',
  themeColor: '#165dff',
  projectName,
  layoutMode: 'ltr',
  sideWidth: 210,
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
    isShowFullScreen: true
  }
}

export const DRIVER = 'Mango Actuator'
export const SERVER = 'Mango Server'
export const WEB = 'mango-console'
export const environment = 8
