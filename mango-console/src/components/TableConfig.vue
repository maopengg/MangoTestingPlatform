<template>
  <a-space align="center">
    <a-tooltip class="item" content="开启/关闭表格边框" placement="top" trigger="hover">
      <a-button
        :status="border ? 'success' : 'normal'"
        shape="circle"
        size="small"
        @click="updateBorder"
      >
        B
      </a-button>
    </a-tooltip>
    <a-tooltip class="item" content="开启/关闭斑马纹" placement="top" trigger="hover">
      <a-button
        :status="striped ? 'success' : 'normal'"
        shape="circle"
        size="small"
        @click="updateStriped"
      >
        S
      </a-button>
    </a-tooltip>
    <a-tooltip class="item" content="刷新页面" placement="top" trigger="hover">
      <a-button shape="circle" size="small" @click="doRefresh">
        <template #icon>
          <icon-refresh />
        </template>
      </a-button>
    </a-tooltip>
  </a-space>
</template>

<script lang="ts">
  import { defineComponent, ref } from 'vue'

  export default defineComponent({
    name: 'TableConfig',
    emits: ['refresh', 'update-border', 'update-striped'],
    setup(props, { emit }) {
      function doRefresh() {
        emit('refresh')
      }

      const border = ref(false)
      const striped = ref(false)

      function updateBorder() {
        border.value = !border.value
        emit('update-border', border.value)
      }

      function updateStriped() {
        striped.value = !striped.value
        emit('update-striped', striped.value)
      }

      return {
        border,
        striped,
        doRefresh,
        updateBorder,
        updateStriped,
      }
    },
  })
</script>
