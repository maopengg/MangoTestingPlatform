<template>
  <div class="vaw-avatar-container">
    <a-dropdown trigger="hover" size="large" @select="handleSelect">
      <div class="action-wrapper">
        <div class="avatar">
          <a-avatar :size="30">
            <img :src="userStore.avatar" />
          </a-avatar>
        </div>
        <span class="nick-name">
          {{ userStore.nickName }}
        </span>
        <icon-caret-down class="tip" />
      </div>
      <template #content>
        <a-doption v-for="item of options" :key="item.key" :value="item.key">
          <template #icon>
            <component :is="item.icon" />
          </template>
          {{ item.label }}
        </a-doption>
      </template>
    </a-dropdown>
  </div>
</template>

<script lang="ts">
import { Modal, Notification } from '@arco-design/web-vue'
import { defineComponent, onMounted, onBeforeUnmount, ref } from 'vue'
import {
  IconUser as UserOutlined,
  IconPoweroff as LogoutOutlined,
  IconCaretDown as CaretDownOutlined
} from '@arco-design/web-vue/es/icon'
import useUserStore from '@/store/modules/user'
import { useRouter } from 'vue-router'
import { websocket } from '@/utils/socket'
import { webSocketURL } from '@/api/axios.config'
import { SERVER } from '@/setting'

export default defineComponent({
  name: 'VAWavatar',
  components: { UserOutlined, LogoutOutlined, CaretDownOutlined },
  setup() {
    const userStore = useUserStore()
    const options = [
      {
        label: '个人中心',
        key: 'personal-center',
        icon: 'UserOutlined'
      },
      {
        label: '退出登录',
        key: 'logout',
        icon: 'LogoutOutlined'
      }
    ]
    const router = useRouter()

    function personalCenter() {
      router.push('/personal/info')
    }

    function logout() {
      Modal.confirm({
        title: '提示',
        content: '是否要退出当前账号？',
        okText: '退出',
        cancelText: '再想想',
        onOk: () => {
          userStore.logout().then(() => {
            window.localStorage.removeItem('visited-routes')
            window.location.reload()
            localStorage.clear()
            websocket(13213, false)
          })
          // const params = new URLSearchParams(window.location.search)
          // params.delete('redirect')
          // window.history.replaceState(null, null, `/#/login?${params.toString()}`)
        }
      })
    }

    function handleSelect(key: string) {
      switch (key) {
        case 'personal-center':
          personalCenter()
          break
        case 'logout':
          logout()
          break
      }
    }
    const socket = ref<WebSocket | null>(null)

    const connectWebSocket = () => {
      if (socket.value) {
        return // 如果正在连接中，则不执行重复连接操作
      }
      if (!socket.value) {
        socket.value = new WebSocket(webSocketURL + userStore.userName)
      }
      socket.value.binaryType = 'arraybuffer'

      socket.value.onopen = () => {
        // 发送消息
        const message = {
          code: 200,
          func: null,
          user: null,
          msg: `Hi, ${SERVER}, mango-console Request Connection!`,
          data: null,
          end: null
        }
        socket.value?.send(JSON.stringify(message))
      }

      socket.value.onmessage = (event) => {
        // 在这里处理收到的消息
        const res = JSON.parse(event.data)
        if (res.code == 200) {
          Notification.success('消息：' + res.msg)
        } else {
          Notification.error('消息：' + res.msg)
        }
      }

      socket.value.onclose = () => {
        // 在这里执行连接关闭后的操作
        socket.value = null
        retryConnection()
      }

      socket.value.onerror = (error) => {
        console.error('错误:', error)

        socket.value = null
        retryConnection()
        // 在这里处理WebSocket错误
        // }
      }
    }

    const retryConnection = () => {
      if (!socket.value) {
        // 永远重试连接
        setTimeout(() => {
          Notification.warning('正在尝试重新连接服务器......')
          connectWebSocket()
        }, 5000)
      }
    }

    onBeforeUnmount(() => {
      if (socket.value) {
        socket.value.close()
      }
    })
    // 在页面刷新时执行清理操作
    window.addEventListener('beforeunload', () => {
      if (socket.value) {
        socket.value.close()
      }
    })

    onMounted(() => {
      if (!socket.value) {
        connectWebSocket()
      }
    })

    return {
      userStore,
      options,
      handleSelect
    }
  }
})
</script>

<style lang="less" scoped>
.vaw-avatar-container {
  .action-wrapper {
    display: flex;
    align-items: center;

    .avatar {
      display: flex;
      align-items: center;

      & > img {
        border: 1px solid #f6f6f6;
        width: 100%;
        height: 100%;
        object-fit: cover;
        border-radius: 50%;
      }
    }

    .nick-name {
      margin: 0 5px;

      .tip {
        transform: rotate(0);
        transition: transform @transitionTime;
        margin-left: 2px;
      }
    }
  }
}

.vaw-avatar-container:hover {
  cursor: pointer;
  color: var(--primary-color);

  .tip {
    transform: rotate(180deg);
    transition: transform @transitionTime;
  }
}
</style>
