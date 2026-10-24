<template>
  <div class="mango-action-items-wrapper">
    <span v-if="appStore.actionBar.isShowSearch" class="mango-action-item" @click="onShowSearch">
      <SearchIcon />
    </span>
    <a-popover
      :width="440"
      placement="bottom"
      trigger="click"
      @popup-visible-change="onNotificationVisibleChange"
    >
      <button
        v-if="appStore.actionBar.isShowMessage"
        type="button"
        class="mango-action-item"
        aria-label="打开风险待办与消息中心"
      >
        <a-badge :count="notificationMessage.totalBadgeValue" :max-count="99">
          <NotificationsIcon />
        </a-badge>
      </button>
      <template #content>
        <NotificationCenter />
      </template>
    </a-popover>
    <span v-if="appStore.actionBar.isShowRefresh" class="mango-action-item" @click="onRefrehRoute">
      <RefreshIcon />
    </span>
    <span
      v-if="appStore.actionBar.isShowFullScreen && appStore.deviceType !== 'mobile'"
      class="mango-action-item"
      @click="onScreenFull"
    >
      <ExpandIcon />
    </span>
    <span class="mango-action-item" @click="onShowSetting">
      <SettingIcon />
    </span>
  </div>
</template>

<script lang="ts">
  import { defineComponent, onBeforeUnmount, onMounted, ref } from 'vue'
  import { Message, Notification } from '@arco-design/web-vue'
  import { useRoute, useRouter } from 'vue-router'
  import {
    IconSettings as SettingIcon,
    IconSearch as SearchIcon,
    IconFullscreen as ExpandIcon,
    IconRefresh as RefreshIcon,
    IconNotification as NotificationsIcon,
  } from '@arco-design/web-vue/es/icon'
  import { useDebounceFn, useFullscreen } from '@vueuse/core'
  import useEmit from '@/hooks/useEmit'
  import useAppConfigStore from '@/store/modules/app-config'
  import { useNotificationMessage } from '@/store/modules/notification-message'
  import { getSystemWorkbenchTodos } from '@/api/system'
  import NotificationCenter from '@/components/feedback/NotificationCenter.vue'

  const TODO_REMINDER_INTERVAL = 30 * 60 * 1000
  const TODO_REMINDER_STORAGE_KEY = 'mango-risk-todo-reminder-at'

  export default defineComponent({
    name: 'ActionItems',
    components: {
      SearchIcon,
      SettingIcon,
      ExpandIcon,
      NotificationsIcon,
      RefreshIcon,
      NotificationCenter,
    },
    setup() {
      const showSearchContent = ref(false)
      const searchContent = ref('')
      const settingRef = ref()
      const notificationMessage = useNotificationMessage()
      const appStore = useAppConfigStore()
      const router = useRouter()
      const route = useRoute()
      const emitter = useEmit()
      let todoRefreshTimer: ReturnType<typeof setInterval> | undefined
      let lastTodoReminderAt = 0

      try {
        lastTodoReminderAt = Number(sessionStorage.getItem(TODO_REMINDER_STORAGE_KEY) || 0)
      } catch {
        lastTodoReminderAt = 0
      }

      function saveTodoReminderTime(value: number) {
        lastTodoReminderAt = value
        try {
          if (value > 0) sessionStorage.setItem(TODO_REMINDER_STORAGE_KEY, String(value))
          else sessionStorage.removeItem(TODO_REMINDER_STORAGE_KEY)
        } catch {
          // 浏览器禁用会话存储时，当前页面内的计时仍然有效。
        }
      }

      function showTodoReminder(pendingCount: number, initial = false) {
        Notification.warning({
          title: initial ? '您有未处理的风险待办' : '风险待办仍未处理',
          content: `还有 ${pendingCount} 项未处理，点击右上角铃铛查看。`,
          class: 'mango-risk-todo-notification',
          closable: true,
          duration: 8000,
        })
        saveTodoReminderTime(Date.now())
      }

      function checkTodoReminder(pendingCount: number, remindImmediately = false) {
        if (pendingCount <= 0) {
          saveTodoReminderTime(0)
          return
        }
        const now = Date.now()
        if (remindImmediately) {
          showTodoReminder(pendingCount, true)
          return
        }
        if (!lastTodoReminderAt) {
          saveTodoReminderTime(now)
          return
        }
        if (
          now - lastTodoReminderAt < TODO_REMINDER_INTERVAL ||
          document.visibilityState !== 'visible'
        ) {
          return
        }
        showTodoReminder(pendingCount)
      }

      async function refreshTodoCount(remindImmediately = false) {
        try {
          const res = await getSystemWorkbenchTodos({
            page: 1,
            pageSize: 1,
            status: 'pending',
          })
          const payload = res.data || {}
          const pendingCount = Number(payload.summary?.pending ?? payload.count ?? 0)
          notificationMessage.setTodoPendingCount(pendingCount)
          checkTodoReminder(pendingCount, remindImmediately)
        } catch {
          // 计数刷新失败时保留上一次结果，避免短暂网络异常将风险角标清零。
        }
      }

      function onNotificationVisibleChange(visible: boolean) {
        if (visible) {
          saveTodoReminderTime(Date.now())
          refreshTodoCount()
        }
      }

      onMounted(() => {
        refreshTodoCount(true)
        todoRefreshTimer = setInterval(refreshTodoCount, 60_000)
      })

      onBeforeUnmount(() => {
        if (todoRefreshTimer) clearInterval(todoRefreshTimer)
      })

      function onShowSearch() {
        emitter?.emit('show-search')
      }

      const { isSupported, enter, isFullscreen, exit } = useFullscreen(document.documentElement)

      function onScreenFull() {
        if (!isSupported) {
          Message.error('当前浏览器不支持全屏操作')
          return false
        }
        if (isFullscreen.value) {
          exit()
        } else {
          enter()
        }
      }

      const debouncedFn = useDebounceFn(() => {
        router.replace({ path: '/redirect' + route.path, query: route.query })
      }, 200)

      function onRefrehRoute() {
        debouncedFn()
      }

      function onShowSetting() {
        emitter?.emit('show-setting')
      }

      return {
        settingRef,
        showSearchContent,
        searchContent,
        notificationMessage,
        appStore,
        onShowSearch,
        onScreenFull,
        onRefrehRoute,
        onShowSetting,
        onNotificationVisibleChange,
      }
    },
  })
</script>

<style lang="less" scoped>
  .mango-action-items-wrapper {
    position: relative;
    height: 100%;
    display: flex;
    align-items: center;
    z-index: 1;

    .mango-action-item {
      padding: 0;
      border: 0;
      min-width: 36px;
      display: flex;
      justify-content: center;
      align-items: center;
      font-size: 18px;
      height: 100%;
      color: var(--m-layout-header-text);
      background: transparent;

      &:hover {
        cursor: pointer;
        color: var(--m-layout-sidebar-active-text);
        background-color: var(--m-layout-sidebar-hover-bg);
      }

      :deep(.arco-badge-number),
      :deep(.arco-badge-text) {
        min-width: 14px;
        height: 14px;
        padding: 0 4px;
        font-size: 12px;
        line-height: 14px;
        border-radius: 999px;
        transform: translate(50%, -50%);
        box-shadow: 0 0 0 1px var(--m-layout-header-bg);
      }

      :deep(.arco-badge-dot),
      :deep(.arco-badge-custom-dot) {
        width: 6px;
        height: 6px;
        transform: translate(50%, -50%);
      }
    }
  }
</style>
