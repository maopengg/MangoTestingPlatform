<template>
  <a-card
    :body-style="{ padding: 0, width: '100%' }"
    :bordered="isBordered"
    class="table-footer-container"
  >
    <div :class="[innerPosition]" class="flex items-center">
      <a-pagination
        v-model:current="pagination.page"
        v-model:pageSize="pagination.pageSize"
        :show-page-size="pagination.showSizePicker"
        :total="pagination?.pageCount || 0"
        show-total
        size="small"
        @change="onChange"
        @page-size-change="onPageSizeChange"
      />
      <a-button
        v-if="showRefresh"
        shape="circle"
        size="small"
        style="margin-left: 10px"
        type="primary"
        @click="refresh"
      >
        <template #icon>
          <IconLoop style="font-size: 14px" />
        </template>
      </a-button>
    </div>
  </a-card>
</template>

<script lang="ts">
  import { computed, defineComponent, toRef, PropType } from 'vue'

  export default defineComponent({
    name: 'TableFooter',
    props: {
      pagination: {
        type: Object,
        default: () => ({}),
        require: true,
      },
      showRefresh: {
        type: Boolean,
        default: true,
      },
      bordered: {
        type: Boolean,
        default: false,
      },
      position: {
        type: String as PropType<'start' | 'center' | 'end'>,
        default: 'end',
      },
    },
    setup(props) {
      const pagination = toRef(props, 'pagination')
      const isBordered = computed(() => props.bordered)
      const innerPosition = computed(() => {
        return 'justify-' + props.position
      })

      function onChange(page: number) {
        ;(pagination as any).value.page = page
        ;(pagination as any).value.onChange()
      }

      function onPageSizeChange(pageSize: number) {
        ;(pagination as any).value.pageSize = pageSize
        ;(pagination as any).value.onChange()
      }

      function refresh() {
        ;(pagination as any).value.onChange()
      }

      return {
        isBordered,
        innerPosition,
        onChange,
        onPageSizeChange,
        refresh,
      }
    },
  })
</script>
<style lang="less" scoped>
  :deep(.arco-pagination-item-active) {
    color: var(--color-white);
  }

  :deep(.arco-pagination-item-active:hover) {
    color: var(--color-white);
  }

  .table-footer-container {
    height: 45px;
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: center;
  }
</style>