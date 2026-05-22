<template>
  <div :class="{ 'mango-circle-tip': checked }" class="mango-style-example-container">
    <div :style="{ background: leftBg, backgroundSize: 'cover' }" class="mango-style-left"></div>
    <div class="mango-style-right">
      <div :style="{ backgroundColor: rightTopBg }" class="mango-style-right-top"></div>
      <div :style="{ backgroundColor: rightBottomBg }" class="mango-style-right-bottom"></div>
    </div>
    <div v-if="tipText" style="font-size: 12px; text-align: center">
      {{ tipText }}
    </div>
  </div>
</template>

<script lang="ts">
  import { defineComponent } from 'vue'

  export default defineComponent({
    name: 'StyleExample',
    props: {
      leftBg: {
        type: String,
        default: 'var(--m-layout-sidebar-bg)',
      },
      rightTopBg: {
        type: String,
        default: 'var(--m-layout-header-bg)',
      },
      rightBottomBg: {
        type: String,
        default: 'var(--m-bg)',
      },
      checked: {
        type: Boolean,
        default: false,
      },
      tipText: {
        type: String,
        default: null,
      },
    },
  })
</script>

<style lang="less" scoped>
  @border-radius: 4px;
  .mango-style-example-container {
    width: 50px;
    height: 40px;
    margin: 0 auto;
    border-radius: @border-radius;
    background-color: transparent;
    box-shadow: var(--m-shadow);

    .mango-style-left {
      border-top-left-radius: @border-radius;
      border-bottom-left-radius: @border-radius;
      display: inline-block;
      width: 30%;
      height: 100%;
    }

    .mango-style-right {
      border-top-right-radius: @border-radius;
      border-bottom-right-radius: @border-radius;
      display: inline-block;
      width: 70%;
      height: 100%;

      .mango-style-right-top {
        height: 20%;
        border-top-right-radius: @border-radius;
      }

      .mango-style-right-bottom {
        height: 80%;
        border-bottom-right-radius: @border-radius;
      }
    }
  }

  .mango-circle-tip::after {
    content: '';
    display: block;
    margin: 0 auto;
    margin-top: 5px;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: var(--m-success);
    text-align: center;
  }

  .extra-class {
    .mango-style-right {
      width: 100%;

      .mango-style-right-top {
        border-top-left-radius: @border-radius;
        border-top-right-radius: @border-radius;
      }

      .mango-style-right-bottom {
        border-bottom-left-radius: @border-radius;
        border-bottom-right-radius: @border-radius;
      }
    }

    .mango-style-left {
      width: 0;
    }
  }

  .extra-class-1 {
    .mango-style-left {
      width: 30%;
    }

    .mango-style-left::after {
      position: relative;
      background-color: var(--m-border-strong);
      top: 0;
      left: 5px;
      content: '';
      display: inline-block;
      width: 10px;
      height: 100%;
    }
  }
</style>
