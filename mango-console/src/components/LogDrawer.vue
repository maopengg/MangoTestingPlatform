<template>
  <a-drawer
    :width="1000"
    :visible="visible"
    placement="right"
    @cancel="handleCancel"
    unmountOnClose
    :footer="false"
  >
    <template #title>
      <div class="log-drawer-title">
        <span>{{ title }}</span>
      </div>
    </template>
    <div class="log-drawer-content">
      <div class="log-drawer-body">
        <CodeEditor
          ref="logEditorRef"
          v-model="codeText"
          placeholder="日志内容"
          :codeStyle="{ height: '100%' }"
          :dark="true"
        />
      </div>
      <div class="log-drawer-footer">
        <a-space>
          <a-button size="small" @click="handleCancel" status="normal" type="secondary">关闭</a-button>
          <a-button size="small" @click="handleDownload">下载</a-button>
          <a-button size="small" type="primary" @click="handleRefresh">刷新</a-button>
        </a-space>
      </div>
    </div>
  </a-drawer>
</template>

<script lang="ts" setup>
import { ref, nextTick, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import CodeEditor from '@/components/CodeEditor.vue'
import { downloadMonitoringTaskLog, getMonitoringTaskLogs } from '@/api/monitoring/task'

// 定义props
interface Props {
  visible: boolean
  title?: string
  taskId?: number
}

const props = withDefaults(defineProps<Props>(), {
  title: '任务日志',
  taskId: 0
})

// 定义emit
const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'cancel'): void
}>()

// 响应式数据
const codeText = ref('')
const logEditorRef = ref<any>(null)

// 方法
function handleCancel() {
  emit('update:visible', false)
  emit('cancel')
}

function scrollToBottom() {
  nextTick(() => {
    setTimeout(() => {
      // 方法1: 使用 CodeEditor 暴露的 scrollToBottom 方法
      if (logEditorRef.value && logEditorRef.value.scrollToBottom) {
        logEditorRef.value.scrollToBottom()
        return
      }
      // 方法2: 通过 ref 访问 CodeMirror 实例
      if (logEditorRef.value) {
        const codemirrorInstance = logEditorRef.value.codemirror
        if (codemirrorInstance && codemirrorInstance.scrollDOM) {
          codemirrorInstance.scrollDOM.scrollTop = codemirrorInstance.scrollDOM.scrollHeight
          return
        }
      }
      // 方法3: 通过 DOM 查询直接访问滚动容器
      const scrollContainer = document.querySelector('.log-drawer-body .cm-scroller')
      if (scrollContainer) {
        ;(scrollContainer as HTMLElement).scrollTop = (
          scrollContainer as HTMLElement
        ).scrollHeight
      }
    }, 300)
  })
}

function fetchLogs() {
  if (!props.taskId) return
  getMonitoringTaskLogs(props.taskId, 300)
    .then((res) => {
      codeText.value = (res.data || []).join('')
      scrollToBottom()
    })
    .catch(console.log)
}

function handleRefresh() {
  fetchLogs()
}

function handleDownload() {
  if (!props.taskId) {
    Message.warning('请先选择任务')
    return
  }
  downloadMonitoringTaskLog(props.taskId)
    .then((res: any) => {
      // 后端返回的是文件流
      const blob = new Blob([res.data], { type: 'text/plain;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `任务日志_${props.taskId}_${new Date().getTime()}.log`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      Message.success('日志下载成功')
    })
    .catch((error) => {
      console.log(error)
      Message.error('下载失败')
    })
}

// 监听抽屉打开状态
watch(
  () => props.visible,
  (visible) => {
    if (visible && props.taskId) {
      // drawer 打开后再加载日志，确保滚动功能正常
      nextTick(() => {
        fetchLogs()
      })
    }
  }
)

// 监听日志内容变化，自动滚动到底部
watch(
  () => codeText.value,
  () => {
    if (props.visible) {
      scrollToBottom()
    }
  }
)

defineExpose({
  fetchLogs,
  handleRefresh,
  handleDownload
})
</script>

<style scoped lang="less">
.log-drawer-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  gap: 8px;
}

.log-drawer-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.log-drawer-body {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: 100%;

  :deep(.cm-editor) {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;

    .cm-scroller {
      flex: 1;
      overflow-y: auto !important;
      height: auto !important;
    }
  }
}

.log-drawer-footer {
  margin-top: 12px;
  padding-bottom: 12px;
  display: flex;
  justify-content: flex-start;
}

/* 自定义滚动条样式 */
:deep(.log-drawer-body)::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

:deep(.log-drawer-body)::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

:deep(.log-drawer-body)::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

:deep(.log-drawer-body)::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* CodeMirror编辑器的滚动条 */
:deep(.cm-scroller)::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

:deep(.cm-scroller)::-webkit-scrollbar-track {
  background: #f8f8f8;
  border-radius: 4px;
}

:deep(.cm-scroller)::-webkit-scrollbar-thumb {
  background: #ddd;
  border-radius: 4px;
}

:deep(.cm-scroller)::-webkit-scrollbar-thumb:hover {
  background: #bbb;
}

:deep(.arco-drawer-body) {
  padding: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: calc(100vh - 60px) !important;
}
</style>