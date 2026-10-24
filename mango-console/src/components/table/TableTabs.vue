<template>
  <a-tabs class="mango-table-tabs mango-tabs-nav-only">
    <slot></slot>
    <template #extra>
      <div class="mango-table-tabs__actions">
        <div class="mango-table-tabs__actions-box">
          <slot name="extra"></slot>
        </div>
      </div>
    </template>
  </a-tabs>
</template>

<style lang="less" scoped>
  .mango-table-tabs {
    position: sticky;
    z-index: 20;
    top: 0;
    flex: none;
    width: 100%;
    min-width: 0;
    overflow: hidden;
    background: var(--m-surface);
  }

  .mango-table-tabs__actions {
    display: flex;
    box-sizing: border-box;
    height: 40px;
    align-items: center;
    justify-content: flex-end;
  }

  .mango-table-tabs__actions-box {
    display: flex;
    box-sizing: border-box;
    height: 100%;
    align-items: center;
    justify-content: flex-end;
  }

  .mango-table-tabs :deep(.arco-tabs-nav) {
    min-height: 40px;
  }

  .mango-table-tabs :deep(.arco-tabs-nav-extra) {
    height: 40px;
    align-items: center;
    padding-right: var(--m-page-gap);
    line-height: normal;
  }
</style>
