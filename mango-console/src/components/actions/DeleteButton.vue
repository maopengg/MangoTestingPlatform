<template>
  <a-button size="mini" status="danger" @click="onDelete">
    <template #icon>
      <IconDelete />
    </template>
    删除
  </a-button>
</template>

<script lang="ts">
  import { defineComponent } from 'vue'

  export default defineComponent({
    name: 'DeleteButton',
    emits: ['delete'],
    setup(props, { emit }) {
      function onDelete() {
        emit('delete')
      }

      return {
        onDelete,
      }
    },
  })
</script>
