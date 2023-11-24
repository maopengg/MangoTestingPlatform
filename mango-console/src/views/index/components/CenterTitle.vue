<script lang="tsx">
import { getNowDate } from '@/utils'
import { defineComponent, onUnmounted, ref, onMounted } from 'vue'
import { get } from '@/api/http'
import { SocketAllUserSum } from '@/api/url'

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
      get({
        url: SocketAllUserSum,
        data: () => {
          return {}
        }
      })
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
        <div class="center">MangoAutoTest 平台管理</div>
        <div class="right">
          <div>{userSum.value}</div>
          <div style={{ color: '#333', fontSize: '12px' }}>当前在线人数</div>
        </div>
      </div>
    )
  }
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
    color: rgb(var(--primary-1));
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
    background: rgba(var(--primary-1), 0.8);
    color: #fff;
    border-radius: 5px;
  }

  .right {
    flex: 1;
  }
}
</style>
