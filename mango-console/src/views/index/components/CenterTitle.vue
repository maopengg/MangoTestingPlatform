<script lang="tsx">
  import { getNowDate } from '@/utils'
  import { defineComponent, onMounted, onUnmounted, ref } from 'vue'
  import { getSystemSocketAllUserSum } from '@/api/system/socket_api'

  export default defineComponent({
    setup() {
      const date = getNowDate()
      const dateStr = date[0]
      const timeStr = ref(date[1])
      const interval = setInterval(() => {
        timeStr.value = getNowDate()[1]
      })
      onUnmounted(() => {
        clearInterval(interval)
      })
      let userSum = ref(0)

      function getAllUserSum() {
        getSystemSocketAllUserSum()
          .then((res) => {
            userSum.value = res.data['sum']
          })
          .catch(console.log)
      }

      onMounted(() => {
        setTimeout(getAllUserSum, 500)
      })
      return () => (
        <div class="title-container">
          <div class="left">
            <div class="date">{dateStr}</div>
            <div class="time">{timeStr.value}</div>
          </div>
          <div class="center">芒果测试平台</div>
          <div class="right">
            <div>{userSum.value}</div>
            <div style={{ color: 'var(--m-muted)', fontSize: '12px' }}>当前在线人数</div>
          </div>
        </div>
      )
    },
  })
</script>
<style lang="less" scoped>
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
      font-size: 16px;
      font-weight: 500;
    }

    .center {
      flex: 1;
      font-size: 16px;
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
