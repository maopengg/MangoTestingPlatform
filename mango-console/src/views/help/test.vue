<template>
  <a-button type="primary" @click="data.drawerVisible = true">Open Drawer</a-button>
  <a-drawer
    :width="800"
    :visible="data.drawerVisible"
    @ok="data.drawerVisible = false"
    @cancel="data.drawerVisible = false"
    unmountOnClose
  >
    <template #title> Title </template>
    <div
      >You can customize modal body text by the current situation. This modal will be closed
      immediately once you press the OK button.
    </div>
  </a-drawer>
</template>

<script setup lang="ts">
  import { ref, reactive } from 'vue'

  const data = reactive({
    drawerVisible: false,
  })
</script>
