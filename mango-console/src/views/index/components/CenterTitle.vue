<script lang="tsx">
  import { getNowDate } from '@/utils'
  import { computed, defineComponent, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref } from 'vue'
  import { getSystemSocketAllUserSum } from '@/api/system/socket_api'
  import usePlatformBrandingStore from '@/store/modules/platform-branding'
  import { useHomeSnapshot } from '../composables/use-home-snapshot'

  export default defineComponent({
    setup() {
      const branding = usePlatformBrandingStore()
      const date = ref(getNowDate())
      const dateStr = computed(() => date.value[0])
      const timeStr = computed(() => date.value[1])
      const { snapshot: userSum, loading, loadFailed, reload: getAllUserSum, isAvailable } = useHomeSnapshot({
        read: getSystemSocketAllUserSum, empty: () => 0,
        parse(value: unknown) {
          if (!value || typeof value !== 'object') throw Error('Invalid online count')
          const response = value as Record<string, unknown>
          if (response.code !== 200 || !response.data || typeof response.data !== 'object') throw Error('Invalid online count')
          const count = (response.data as Record<string, unknown>).sum
          if (typeof count !== 'number' || !Number.isInteger(count) || count < 0) throw Error('Invalid online count')
          return count
        },
      })
      let interval: ReturnType<typeof setInterval> | undefined
      function stopClock() {
        if (interval !== undefined) clearInterval(interval)
        interval = undefined
      }
      function syncClock() {
        stopClock()
        if (!isAvailable() || document.visibilityState !== 'visible') return
        date.value = getNowDate()
        interval = setInterval(() => { if (isAvailable()) date.value = getNowDate() }, 1000)
      }
      onMounted(() => {
        syncClock()
        document.addEventListener('visibilitychange', syncClock)
      })
      onActivated(syncClock)
      onDeactivated(stopClock)
      onBeforeUnmount(() => { stopClock(); document.removeEventListener('visibilitychange', syncClock) })
      return () => (
        <div class="title-container">
          <div class="left">
            <div class="date">{dateStr.value}</div>
            <div class="time">{timeStr.value}</div>
          </div>
          <div class="center">{branding.projectName}</div>
          <div class="right" aria-busy={loading.value}>
            {loading.value ? <div>加载中</div> : loadFailed.value
              ? <button class="mango-online-title__retry" onClick={() => getAllUserSum()}>加载失败，重试</button>
              : <div>{userSum.value}</div>}
            <div class="mango-online-title__caption">当前在线人数</div>
          </div>
        </div>
      )
    },
  })
</script>
<style lang="less" scoped>
  .mango-online-title__caption { color: var(--m-muted); font-size: 12px; }
  .mango-online-title__retry { border: 0; background: transparent; color: var(--m-primary); cursor: pointer; }
  .title-container {
    padding: 10px;
    display: flex;
    text-align: center;
    align-items: center;

    .left,
    .right {
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      color: var(--m-primary);
      font-size: 18px;
      font-weight: 500;
    }

    .center {
      flex: 1;
      font-size: 18px;
      display: flex;
      justify-content: center;
      padding: 5px;
      align-items: center;
      font-weight: bold;
      background: var(--m-primary);
      color: var(--m-surface);
      border-radius: var(--m-radius-md);
    }

    .right {
      flex: 1;
    }
  }
</style>
