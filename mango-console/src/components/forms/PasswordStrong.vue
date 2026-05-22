<template>
  <div class="mango-password-strength">
    <span
      v-for="(item, index) of stronger"
      :key="index"
      :class="[item.status]"
      class="mango-password-strength__bar"
    ></span>
    <span class="mango-password-strength__text">{{ tipValue }}</span>
  </div>
</template>

<script lang="ts" setup>
  import { reactive } from 'vue'
  import { watch, ref } from 'vue'

  interface StrongTip {
    status: 'normal' | 'low' | 'middle' | 'strong'
  }

  const props = defineProps({
    inputValue: {
      type: String,
      default: '',
    },
    lowReg: {
      type: RegExp,
      default: /^[0-9]{6,16}$|^[a-zA-Z]{6,16}$/,
    },
    middleReg: {
      type: RegExp,
      default: /^[A-Za-z0-9]{6,16}$/,
    },
    strongReg: {
      type: RegExp,
      default: /^\w{6,16}$/,
    },
  })
  const stronger = reactive<StrongTip[]>([
    {
      status: 'normal',
    },
    {
      status: 'normal',
    },
    {
      status: 'normal',
    },
  ])
  const tipValue = ref('弱')
  watch(
    () => props.inputValue,
    () => {
      if (props.lowReg.test(props.inputValue)) {
        stronger[0].status = 'low'
        stronger[1].status = 'normal'
        stronger[2].status = 'normal'
        tipValue.value = '弱'
      } else if (props.middleReg.test(props.inputValue)) {
        stronger[0].status = 'low'
        stronger[1].status = 'middle'
        stronger[2].status = 'normal'
        tipValue.value = '中'
      } else if (props.strongReg.test(props.inputValue)) {
        stronger[0].status = 'low'
        stronger[1].status = 'middle'
        stronger[2].status = 'strong'
        tipValue.value = '强'
      } else {
        stronger.forEach((it) => (it.status = 'normal'))
      }
    }
  )
</script>
<style lang="less" scoped>
  .mango-password-strength {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    margin-top: 6px;
  }

  .mango-password-strength__bar {
    flex: 1;
    height: 10px;
    border-radius: 2px;
    background-color: var(--m-surface);
  }

  .normal {
    background-color: var(--m-border);
  }

  .low {
    background-color: var(--m-danger);
  }

  .middle {
    background-color: var(--m-warning);
  }

  .strong {
    background-color: var(--m-success);
  }

  .mango-password-strength__text {
    flex: none;
    min-width: 18px;
    color: var(--m-muted);
  }
</style>
