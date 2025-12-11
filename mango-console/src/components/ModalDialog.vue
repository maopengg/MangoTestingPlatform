<script lang="ts">
  import { defineComponent, ref } from 'vue'

  export default defineComponent({
    name: 'ModalDialog',
    props: {
      title: {
        type: String,
        default: '操作',
      },
      contentHeight: {
        type: String,
        default: '30vh',
      },
      showContinuousSubmit: {
        type: Boolean,
        default: false,
      },
    },
    emits: ['confirm', 'cancel', 'continuousSubmit'],
    setup(props, { emit }) {
      const showModal = ref(false)
      const confirmLoading = ref(false)
      const continuousLoading = ref(false)

      function toggle() {
        showModal.value = !showModal.value
        // 当模态框关闭时，重置loading状态
        if (!showModal.value) {
          resetLoading()
        }
        return Promise.resolve(showModal.value)
      }

      function show() {
        showModal.value = true
        return Promise.resolve(true)
      }

      function close() {
        showModal.value = false
        // 关闭时重置loading状态
        resetLoading()
        return Promise.resolve(false)
      }

      function onConfirm() {
        confirmLoading.value = true
        // 发出 confirm 事件，父组件需要在处理完异步操作后调用 setConfirmLoading(false)
        emit('confirm')
      }

      function onCancel() {
        showModal.value = false
        // 取消时重置loading状态
        resetLoading()
        emit('cancel')
      }

      function onContinuousSubmit() {
        continuousLoading.value = true
        // 发出 continuousSubmit 事件，父组件需要在处理完异步操作后调用 setContinuousLoading(false)
        emit('continuousSubmit')
      }

      function setConfirmLoading(loading: boolean) {
        confirmLoading.value = loading
      }

      function setContinuousLoading(loading: boolean) {
        continuousLoading.value = loading
      }

      // 添加自动重置 loading 状态的方法
      function resetLoading() {
        confirmLoading.value = false
        continuousLoading.value = false
      }

      function handleKeyDown(event: KeyboardEvent) {
        // 只处理回车键
        if (event.key === 'Enter') {
          handleEnterKey(event);
        }
      }

      function handleEnterKey(event: KeyboardEvent) {
        // 检查是否在特定元素中按回车
        const target = event.target as HTMLElement
        const tagName = target.tagName.toUpperCase()
        
        // 在这些元素中按回车时，通常希望有默认行为（如换行），而不是提交表单
        const ignoreElements = ['TEXTAREA']
        
        // 检查是否有特定的类名需要忽略（比如某些富文本编辑器）
        const ignoreClasses = ['CodeMirror-code', 'ace_editor']
        const hasIgnoreClass = target.classList && ignoreClasses.some(className => target.classList.contains(className))
        
        // 如果在需要忽略的元素中按回车，则不处理
        if (ignoreElements.includes(tagName) || hasIgnoreClass) {
          return
        }
        
        // 阻止默认行为
        event.preventDefault()
        
        // 触发确认操作
        onConfirm()
      }

      return {
        showModal,
        confirmLoading,
        continuousLoading,
        toggle,
        show,
        close,
        onConfirm,
        onCancel,
        onContinuousSubmit,
        setConfirmLoading,
        setContinuousLoading,
        resetLoading,
        handleEnterKey,
        handleKeyDown,
      }
    },
  })
</script>
<template>
  <a-modal v-model:visible="showModal" :title="title" class="modal-dialog-wrapper" @keydown="handleKeyDown">
    <Scrollbar wrap-class="modal-dialog__wrap">
      <slot name="content"></slot>
    </Scrollbar>
    <template #footer>
      <a-space>
        <a-button @click="onCancel">取消</a-button>
        <a-button
          v-if="showContinuousSubmit"
          type="primary"
          :loading="continuousLoading"
          @click="onContinuousSubmit"
          >连续提交</a-button
        >
        <a-button type="primary" :loading="confirmLoading" @click="onConfirm">提交</a-button>
      </a-space>
    </template>
  </a-modal>
</template>

<style scoped>
  .modal-dialog__wrap {
    max-height: 80vh;
  }
</style>
