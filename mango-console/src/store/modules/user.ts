import { defineStore } from 'pinia'
import { UserState } from '../types'
import store from '../pinia'

import Avatar from '@/assets/img_avatar.gif'

const defaultAvatar = Avatar

const useUserStore = defineStore('user-info', {
  state: () => {
    return {
      userId: 0,
      roleId: 0,
      token: '',
      userName: '',
      nickName: '',
      avatar: defaultAvatar,
      password: '',
      selected_project: null,
      selected_environment: null,
      selected_environment_title: '选择测试环境',
    }
  },
  actions: {
    saveUser(userInfo: UserState, password: string) {
      console.log(userInfo)
      return new Promise<UserState>((resolve) => {
        this.userId = userInfo.userId
        this.roleId = userInfo.roleId
        this.token = userInfo.token
        this.userName = userInfo.userName
        this.nickName = userInfo.name
        this.password = password
        this.avatar = userInfo.avatar || defaultAvatar
        this.selected_project = userInfo.selected_project
        this.selected_environment = userInfo.selected_environment
        resolve(userInfo)
      })
    },
    isTokenExpire() {
      return !this.token
    },
    changeNickName(newNickName: string) {
      this.nickName = newNickName
    },
    logout() {
      return new Promise<void>((resolve) => {
        this.$reset()
        localStorage.clear()
        sessionStorage.clear()
        resolve()
      })
    },
  },
  presist: {
    enable: true,
    resetToState: true,
    option: {
      exclude: [],
    },
  },
})

export default useUserStore

export function useUserStoreContext() {
  return useUserStore(store)
}
