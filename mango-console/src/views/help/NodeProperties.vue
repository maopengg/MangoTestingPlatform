<template>
  <div class="node-properties">
    <div class="form-group">
      <label>节点名称</label>
      <input type="text" v-model="localNode.data.label" @input="updateNode" />
    </div>

    <div class="form-group" v-if="localNode.type === 'task'">
      <label>处理类型</label>
      <select v-model="localNode.data.handler" @change="updateNode">
        <option value="auto">自动处理</option>
        <option value="manual">人工处理</option>
      </select>
    </div>

    <div class="form-group" v-if="localNode.type === 'decision'">
      <label>条件表达式</label>
      <textarea
        v-model="localNode.data.condition"
        @input="updateNode"
        placeholder="例如: amount > 1000"
      ></textarea>
    </div>

    <div class="form-group" v-if="localNode.type === 'task'">
      <label>超时时间(秒)</label>
      <input type="number" v-model="localNode.data.timeout" @input="updateNode" />
    </div>

    <div class="form-group">
      <label>描述</label>
      <textarea
        v-model="localNode.data.description"
        @input="updateNode"
        placeholder="节点功能描述"
      ></textarea>
    </div>
  </div>
</template>

<script setup>
  import { ref, watch } from 'vue'

  const props = defineProps({
    node: Object,
  })

  const emit = defineEmits(['update:node'])

  const localNode = ref(JSON.parse(JSON.stringify(props.node)))

  watch(
    () => props.node,
    (newVal) => {
      localNode.value = JSON.parse(JSON.stringify(newVal))
    },
    { deep: true }
  )

  const updateNode = () => {
    emit('update:node', localNode.value)
  }
</script>

<style scoped>
  .node-properties {
    padding: 10px;
  }

  .form-group {
    margin-bottom: 15px;
  }

  .form-group label {
    display: block;
    margin-bottom: 5px;
    font-weight: bold;
  }

  .form-group input,
  .form-group select,
  .form-group textarea {
    width: 100%;
    padding: 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
  }

  .form-group textarea {
    height: 80px;
    resize: vertical;
  }
</style>
