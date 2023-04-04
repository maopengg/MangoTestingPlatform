import { AxiosResponse } from 'axios'
import { Message } from '@arco-design/web-vue'
import useUserStore from '@/store/modules/user'

export default function (response: AxiosResponse): AxiosResponse {
  if (response.status === 403) {
    // Message.error('当前用户登录已过期，请重新登录')
    setTimeout(() => {
      const userStore = useUserStore()
      userStore.logout().then(() => {
        window.location.reload()
      })
      // ;(store as any).onLogout && (store as any).onLogout()
    }, 1500)
  }
  return response
}
