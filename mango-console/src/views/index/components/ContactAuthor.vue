<template>
  <a-modal v-model:visible="visible" @cancel="handleCancel" @ok="handleOk" :width="500">
    <template #title>联系作者</template>
    <div class="contact-author">
      <p>进群需要GitHub点Starred（点点星）</p>
      <div class="contact-author__grid">
        <div class="mango-soft-panel contact-author__item">
          <p>作者微信</p>
          <img alt="作者微信" src="/static/images/author.jpg" />
        </div>
        <div class="mango-soft-panel contact-author__item">
          <p>交流群</p>
          <img alt="交流群" src="/static/images/group.jpg" />
        </div>
      </div>
    </div>
  </a-modal>
</template>

<script lang="ts" setup>
  const visible = defineModel<boolean>('visible', { default: false })

  function handleCancel() {
    visible.value = false
  }

  function handleOk() {
    visible.value = false
  }
</script>
<style scoped>
  .contact-author {
    min-height: 380px;
    text-align: center;
  }

  .contact-author__grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    margin-top: 12px;
  }

  .contact-author__item img {
    width: 100%;
    max-width: 180px;
    border-radius: var(--m-radius-md);
  }
</style>
