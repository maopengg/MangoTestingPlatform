import { ref } from 'vue'

const visible = ref(false)

export function useAiAssistantPanel() {
  function openAiAssistant() {
    visible.value = true
  }

  function closeAiAssistant() {
    visible.value = false
  }

  function toggleAiAssistant() {
    visible.value = !visible.value
  }

  return {
    visible,
    openAiAssistant,
    closeAiAssistant,
    toggleAiAssistant,
  }
}
