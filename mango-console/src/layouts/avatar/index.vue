<template>
  <div class="mango-avatar-container">
    <a-dropdown size="large" trigger="hover" @select="handleSelect">
      <div class="mango-action-wrapper" :title="avatarTitle">
        <span class="mango-name-avatar-wrap">
          <a-avatar class="mango-name-avatar" :size="27">
            {{ avatarText }}
          </a-avatar>
          <span v-if="isActuatorOnline" class="mango-actuator-online-dot" />
        </span>
        <icon-caret-down class="mango-tip" />
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
  <ContactAuthor v-model:visible="visible" />
</template>

<script lang="ts" setup>
  import { Modal } from '@arco-design/web-vue'
  import { computed, ref } from 'vue'
  import { IconCaretDown } from '@arco-design/web-vue/es/icon'
  import useUserStore from '@/store/modules/user'
  import { useRouter } from 'vue-router'
  import { disconnectWebSocket } from '@/utils/socket'

  // 导入联系作者组件
  import ContactAuthor from '@/views/index/components/ContactAuthor.vue'

  const userStore = useUserStore()
  const router = useRouter()
  const isActuatorOnline = ref(false)
  const displayName = computed(() => userStore.nickName || userStore.userName || '用户')
  const avatarText = computed(() => getNameAvatarText(displayName.value))
  const avatarTitle = computed(
    () => `${displayName.value}${isActuatorOnline.value ? '，执行器在线' : ''}`
  )

  const options = [
    {
      label: '个人中心',
      key: 'personal-center',
      icon: 'UserOutlined',
    },
    {
      label: '退出登录',
      key: 'logout',
      icon: 'LogoutOutlined',
    },
  ]

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
        // 先断开 WebSocket
        disconnectWebSocket()

        // 执行登出逻辑
        userStore.logout().then(() => {
          window.localStorage.removeItem('visited-routes')
          localStorage.clear()
          window.location.reload()
        })
      },
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

  function getNameAvatarText(name: string) {
    const normalizedName = String(name || '').trim()
    if (!normalizedName) return '用'

    const nameParts = normalizedName.split(/\s+/).filter(Boolean)
    if (nameParts.length > 1) {
      return nameParts
        .slice(0, 2)
        .map((item) => Array.from(item)[0] || '')
        .join('')
        .toUpperCase()
    }

    const chars = Array.from(normalizedName)
    const text = chars.slice(0, 2).join('')
    return /[a-z]/i.test(text) ? text.toUpperCase() : text
  }

  const visible = ref(import.meta.env.VITE_IS_INDEX_WINDOW == 'true')
</script>

<style lang="less" scoped>
  .mango-avatar-container {
    .mango-action-wrapper {
      display: flex;
      align-items: center;
      height: 32px;
      padding: 0 4px;
      border: 1px solid transparent;
      border-radius: 999px;
      transition: border-color @transitionTime, background-color @transitionTime;

      .mango-name-avatar-wrap {
        position: relative;
        display: inline-flex;
        flex: 0 0 auto;
      }

      .mango-name-avatar {
        flex: 0 0 auto;
        border: 1px solid var(--m-primary-border);
        color: var(--m-primary);
        font-size: 12px;
        font-weight: 700;
        background: var(--m-primary-soft);
      }

      .mango-actuator-online-dot {
        position: absolute;
        right: -1px;
        bottom: -1px;
        width: 8px;
        height: 8px;
        border: 2px solid var(--m-layout-header-bg);
        border-radius: 50%;
        background: var(--m-success);
      }

      .mango-tip {
        flex: 0 0 auto;
        margin-left: 3px;
        font-size: 12px;
        color: var(--m-muted);
        transform: rotate(0);
        transition: color @transitionTime, transform @transitionTime;
      }
    }
  }

  .mango-avatar-container:hover {
    cursor: pointer;

    .mango-action-wrapper {
      border-color: var(--m-primary-border);
      background: var(--m-surface-soft);
    }

    .mango-name-avatar {
      background: var(--m-surface);
    }

    .mango-tip {
      color: var(--m-primary);
      transform: rotate(180deg);
    }
  }
</style>
