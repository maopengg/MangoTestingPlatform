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
      <div class="file-drawer-title">
        <span>{{ title }}</span>
      </div>
    </template>
    <div class="file-drawer-content">
      <div class="file-drawer-body">
        <CodeEditor
          ref="fileEditorRef"
          v-model="codeText"
          placeholder="脚本内容"
          :codeStyle="{ height: '100%' }"
          :dark="true"
        />
      </div>
      <div class="file-drawer-footer">
        <a-space>
          <a-button size="small" @click="handleCancel" status="normal" type="secondary">关闭</a-button>
          <a-button size="small" @click="handleCancel" status="normal">取消</a-button>
          <a-button size="small" type="primary" @click="handleSave">保存</a-button>
        </a-space>
      </div>
    </div>
  </a-drawer>
</template>

<script lang="ts" setup>
import { ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import CodeEditor from '@/components/CodeEditor.vue'
import { getMonitoringTaskDetail } from '@/api/monitoring/task'

// 定义props
interface Props {
  visible: boolean
  title?: string
  taskId?: number
  task?: any
}

const props = withDefaults(defineProps<Props>(), {
  title: '任务文件',
  taskId: 0,
  task: undefined
})

// 定义emit
const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'update:codeText', value: string): void
  (e: 'cancel'): void
  (e: 'save'): void
}>()

// 响应式数据
const codeText = defineModel<string>('codeText', { required: true })
const fileEditorRef = ref<any>(null)

// 方法
function handleCancel() {
  emit('update:visible', false)
  emit('cancel')
}

function handleSave() {
  if (!props.taskId || !props.task) {
    Message.warning('未选择任务')
    return
  }
  emit('save')
}

// 监听抽屉打开状态
import { watch } from 'vue'
watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      // 如果 props.task 中已经有 script_content，直接使用
      if (props.task && props.task.script_content) {
        codeText.value = props.task.script_content
      } else if (props.taskId) {
        // 否则从后端获取任务详情
        getMonitoringTaskDetail(props.taskId)
          .then((res: any) => {
            if (res.data && res.data.script_content) {
              codeText.value = res.data.script_content
            } else {
              codeText.value = '暂无脚本内容'
            }
          })
          .catch((error) => {
            console.log(error)
            Message.error('获取文件内容失败')
            codeText.value = '获取文件内容失败'
          })
      }
    }
  }
)

defineExpose({
  handleCancel,
  handleSave
})
</script>

<style scoped lang="less">
.file-drawer-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  gap: 8px;
}

.file-drawer-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.file-drawer-body {
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

.file-drawer-footer {
  margin-top: 12px;
  padding-bottom: 12px;
  display: flex;
  justify-content: flex-start;
}

/* 自定义滚动条样式 */
:deep(.file-drawer-body)::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

:deep(.file-drawer-body)::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

:deep(.file-drawer-body)::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

:deep(.file-drawer-body)::-webkit-scrollbar-thumb:hover {
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