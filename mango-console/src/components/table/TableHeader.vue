<template>
  <div class="mango-table-header">
    <a-card :bordered="isBordered" :title="title" class="mango-table-header__card" size="small">
      <template v-if="showFilter" #extra>
        <a-space>
          <a-button size="small" type="primary" @click="doSearch">搜索</a-button>
          <a-button size="small" @click="doResetSearch">重置</a-button>
        </a-space>
      </template>
      <div v-if="showFilter" class="mango-table-header__filters">
        <slot name="search-content"></slot>
      </div>
      <div class="mango-table-header__config">
        <slot name="table-config"></slot>
      </div>
    </a-card>
  </div>
</template>

<script lang="ts">
  import { computed, defineComponent } from 'vue'

  export default defineComponent({
    name: 'TableHeader',
    props: {
      title: {
        type: String,
        default: '',
      },
      bordered: {
        type: Boolean,
        default: false,
      },
    },
    emits: ['search', 'reset-search'],
    setup(props, { emit, slots }) {
      const showFilter = computed(() => !!slots['search-content'])
      const isBordered = computed(() => props.bordered)

      function doSearch() {
        emit('search')
      }

      function doResetSearch() {
        emit('reset-search')
      }

      return {
        showFilter,
        isBordered,
        doSearch,
        doResetSearch,
      }
    },
  })
</script>
<style lang="less" scoped>
  .mango-table-header {
    position: relative;
    z-index: 9;
  }

  :deep(.arco-card) {
    background: var(--m-surface);
    border-color: var(--m-border);
    box-shadow: none;
  }

  :deep(.arco-card-header) {
    min-height: 34px;
    padding: 4px 12px;
    color: var(--m-text);
    border-bottom-color: var(--m-border);
  }

  :deep(.arco-card-header-title) {
    min-width: 0;
    overflow: hidden;
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
    line-height: 22px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  :deep(.arco-card-extra) {
    display: flex;
    align-items: center;
    min-width: 0;
  }

  :deep(.arco-card-extra .arco-space) {
    flex-wrap: wrap;
    justify-content: flex-end;
    row-gap: 4px;
  }

  :deep(.arco-card-extra .arco-btn) {
    height: 24px;
    padding: 0 10px;
    font-size: 12px;
  }

  :deep(.arco-card-body) {
    padding: 4px 10px;
    color: var(--m-text-2);
  }

  .mango-table-header__filters {
    padding-bottom: 0;
  }

  .mango-table-header__filters {
    --table-filter-label-width: 72px;
    --table-filter-control-width: 160px;
    --table-filter-item-width: calc(
      var(--table-filter-label-width) + var(--table-filter-control-width) + 3px
    );

    :deep(.arco-form-layout-inline),
    :deep(.arco-form-inline) {
      display: grid !important;
      grid-template-columns: repeat(auto-fill, var(--table-filter-item-width));
      gap: 8px 10px;
      align-items: start;
      justify-content: start;
    }

    :deep(.arco-form-layout-inline .arco-form-item),
    :deep(.arco-form-item-layout-inline),
    :deep(.arco-form-inline .arco-form-item) {
      display: flex !important;
      width: var(--table-filter-item-width) !important;
      margin: 0 !important;
      align-items: center;
      flex: 0 0 var(--table-filter-item-width) !important;
      max-width: var(--table-filter-item-width) !important;
      height: 30px;
      min-height: 30px;
      max-height: 30px;
    }

    :deep(.arco-form-layout-inline .arco-form-item-label-col),
    :deep(.arco-form-item-layout-inline .arco-form-item-label-col),
    :deep(.arco-form-inline .arco-form-item-label-col) {
      display: flex;
      flex: 0 0 var(--table-filter-label-width) !important;
      justify-content: flex-start !important;
      width: var(--table-filter-label-width) !important;
      min-width: var(--table-filter-label-width) !important;
      max-width: var(--table-filter-label-width) !important;
      padding-right: 0 !important;
      text-align: left;
      line-height: 30px !important;
    }

    :deep(.arco-form-layout-inline .arco-form-item-label),
    :deep(.arco-form-item-layout-inline .arco-form-item-label),
    :deep(.arco-form-inline .arco-form-item-label) {
      display: block;
      width: 100%;
      overflow: hidden;
      color: var(--m-text-2);
      font-size: 13px;
      line-height: 30px;
      text-align: left;
      text-overflow: ellipsis;
      white-space: nowrap !important;
    }

    :deep(.arco-form-layout-inline .arco-form-item-wrapper-col),
    :deep(.arco-form-layout-inline .arco-form-item-content-wrapper),
    :deep(.arco-form-item-layout-inline .arco-form-item-wrapper-col),
    :deep(.arco-form-item-layout-inline .arco-form-item-content-wrapper),
    :deep(.arco-form-inline .arco-form-item-wrapper-col),
    :deep(.arco-form-inline .arco-form-item-content-wrapper) {
      flex: 0 0 var(--table-filter-control-width) !important;
      width: var(--table-filter-control-width) !important;
      min-width: var(--table-filter-control-width) !important;
      max-width: var(--table-filter-control-width) !important;
      min-height: 30px !important;
      max-height: 30px !important;
    }

    :deep(.arco-form-layout-inline .arco-form-item-content),
    :deep(.arco-form-item-layout-inline .arco-form-item-content),
    :deep(.arco-form-inline .arco-form-item-content) {
      width: 100% !important;
      min-width: 0;
      min-height: 30px !important;
      max-height: 30px !important;
    }

    :deep(.arco-form-layout-inline .arco-input-wrapper),
    :deep(.arco-form-layout-inline .arco-select),
    :deep(.arco-form-layout-inline .arco-select-view),
    :deep(.arco-form-layout-inline .arco-cascader),
    :deep(.arco-form-layout-inline .arco-picker),
    :deep(.arco-form-layout-inline .arco-input-number),
    :deep(.arco-form-layout-inline .arco-input-tag),
    :deep(.arco-form-item-layout-inline .arco-input-wrapper),
    :deep(.arco-form-item-layout-inline .arco-select),
    :deep(.arco-form-item-layout-inline .arco-select-view),
    :deep(.arco-form-item-layout-inline .arco-cascader),
    :deep(.arco-form-item-layout-inline .arco-picker),
    :deep(.arco-form-item-layout-inline .arco-input-number),
    :deep(.arco-form-item-layout-inline .arco-input-tag),
    :deep(.arco-form-inline .arco-input-wrapper),
    :deep(.arco-form-inline .arco-select),
    :deep(.arco-form-inline .arco-select-view),
    :deep(.arco-form-inline .arco-cascader),
    :deep(.arco-form-inline .arco-picker),
    :deep(.arco-form-inline .arco-input-number),
    :deep(.arco-form-inline .arco-input-tag) {
      width: var(--table-filter-control-width) !important;
      min-width: 0;
    }

    :deep(.arco-form-layout-inline .arco-input),
    :deep(.arco-form-layout-inline .arco-select-view-single),
    :deep(.arco-form-layout-inline .arco-cascader-view),
    :deep(.arco-form-inline .arco-input),
    :deep(.arco-form-inline .arco-select-view-single),
    :deep(.arco-form-inline .arco-cascader-view) {
      height: 28px;
      line-height: 28px;
    }
  }

  .mango-table-header__config {
    display: flex;
    justify-content: flex-end;
    min-height: 0;

    :deep(.arco-space) {
      flex-wrap: wrap;
      justify-content: flex-end;
      row-gap: 4px;
    }

    :deep(.arco-btn) {
      height: 24px;
      padding: 0 10px;
      font-size: 12px;
    }
  }

  @media (max-width: 768px) {
    .mango-table-header__filters {
      --table-filter-label-width: 70px;
      --table-filter-control-width: calc(100vw - 150px);
      --table-filter-item-width: minmax(0, 1fr);

      :deep(.arco-form-layout-inline),
      :deep(.arco-form-inline) {
        grid-template-columns: minmax(0, 1fr);
      }

      :deep(.arco-form-layout-inline .arco-form-item),
      :deep(.arco-form-item-layout-inline),
      :deep(.arco-form-inline .arco-form-item) {
        width: 100%;
      }
    }
  }
</style>
