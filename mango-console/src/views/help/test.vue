<template>
  <a-card>
    <h1>编辑代码</h1>
    <h1></h1>
    <codemirror v-model="code" :options="cmOptions" @ready="onCmReady" @input="onCmCodeChange" />
  </a-card>
</template>

<script setup>
  import { ref } from 'vue'
  import { Codemirror } from 'vue-codemirror'
  import { basicSetup } from '@codemirror/basic-setup'
  import { oneDarkTheme } from '@codemirror/theme-one-dark'
  import { python } from '@codemirror/lang-python' // 引入 Python 语言支持

  const code = ref(`# Write your Python code here
def hello_world():
    print("Hello, World!")`)

  const cmOptions = {
    extensions: [
      basicSetup,
      python(), // 添加 Python 语言支持
      oneDarkTheme, // 使用 One Dark 主题
    ],
    tabSize: 4,
    lineNumbers: true,
    line: true,
    indentUnit: 4,
    smartIndent: true,
    matchBrackets: true,
    autoCloseBrackets: true,
    styleActiveLine: true,
    foldGutter: true,
    gutters: ['CodeMirror-linenumbers', 'CodeMirror-foldgutter'],
  }

  const onCmReady = (cm) => {
    console.log('CodeMirror is ready!', cm)
  }

  const onCmCodeChange = (newCode) => {
    console.log('Code changed:', newCode)
    code.value = newCode
  }
</script>

<style>
  .CodeMirror {
    border: 1px solid #ddd;
    height: 500px;
    font-size: 14px;
  }
</style>
