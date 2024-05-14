<template>
  <a-dropdown>
    <a-button>Click Me</a-button>
    <template #content>
      <template v-for="item of testObj.data">
        <template v-if="item.children && item.children.length > 0">
          <a-dsubmenu :value="item.label" :key="item.value">
            <template #default>
              {{ item.label }}
            </template>
            <template #content>
              <a-doption v-for="n of item.children" :key="n.value" :value="n.value">
                {{ n.label }}
              </a-doption>
              {{ item.children }}
            </template>
          </a-dsubmenu>
        </template>
        <template v-else>
          <a-doption :key="item.value" :value="item.value" disabled>
            {{ item.label }}
          </a-doption>
        </template>
      </template>
    </template>
  </a-dropdown>
</template>

<script lang="ts" setup>
  import { ref } from 'vue'
  import { useTestObj } from '@/store/modules/get-test-obj'
  const testObj = useTestObj()

  const name = ref('')
  function f() {
    console.log(name.value)
  }
</script>
