<template>
  <a-modal v-model:visible="showModal" :title="title" class="modal-dialog-wrapper">
    <Scrollbar wrap-class="modal-dialog__wrap">
      <slot name="content"></slot>
    </Scrollbar>
    <template #footer>
      <a-space>
        <a-button @click="onCancel">取消</a-button>
        <a-button v-if="showContinuousSubmit" type="primary" :loading="continuousLoading" @click="onContinuousSubmit">连续提交</a-button>
        <a-button type="primary" :loading="confirmLoading" @click="onConfirm">提交</a-button>
      </a-space>
    </template>
  </a-modal>
</template>

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
        return Promise.resolve(showModal.value)
      }

      function show() {
        showModal.value = true
        return Promise.resolve(true)
      }

      function close() {
        showModal.value = false
        return Promise.resolve(false)
      }

      function onConfirm() {
        confirmLoading.value = true
        // 发出 confirm 事件，父组件需要在处理完异步操作后调用 setConfirmLoading(false)
        emit('confirm')
      }

      function onCancel() {
        showModal.value = false
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
      }
    },
  })
</script>

<style scoped>
  .modal-dialog__wrap {
    max-height: 80vh;
  }
</style>