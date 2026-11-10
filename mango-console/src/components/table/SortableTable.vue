<template>
  <a-popover
    v-model:popup-visible="popupVisible"
    class="mango-sortable-table-popover"
    trigger="click"
    @popup-visible-change="onPopVisibleChange"
  >
    <template #content>
      <div class="mango-sortable-table-header">
        <a-checkbox v-model="allChecked" @change="onAllChange" data-testid="qa-components-table-sortabletable-checkbox-全选"> 全选</a-checkbox>
        <a-button type="text" @click="onReset" data-testid="qa-components-table-sortabletable-button-重置"> 重置</a-button>
      </div>
      <div ref="sortColumnWrapper" class="mango-sortable-table-list">
        <div v-for="item of innerTableProps" :key="item.key" class="mango-column-item">
          <a-checkbox v-model="item.checked" :label="item.title" @change="onChange">
            {{ item.title }}
          </a-checkbox>
          <icon-menu class="mango-handle-icon" />
        </div>
      </div>
    </template>
    <a-button shape="circle" size="small" type="primary">
      <template #icon>
        <icon-settings />
      </template>
    </a-button>
  </a-popover>
</template>

<script lang="ts">
  import { TablePropsType } from '@/types/components'
  import { defineComponent, PropType, reactive, ref, toRef, nextTick, onDeactivated, onBeforeUnmount } from 'vue'
  import Sortable from 'sortablejs'
  import { cloneDeep, isUndefined } from 'lodash-es'

  export default defineComponent({
    name: 'SortableTable',
    props: {
      columns: {
        type: Array as PropType<TablePropsType[]>,
        require: true,
      },
    },
    emits: ['update'],
    setup(props, { emit }) {
      const sortColumnWrapper = ref<HTMLElement | null>(null)
      const popupVisible = ref(false)
      let sortable: Sortable | null = null
      let popupGeneration = 0
      function disposeSortable() {
        popupGeneration += 1
        sortable?.destroy()
        sortable = null
      }
      function closePopup() {
        popupVisible.value = false
        disposeSortable()
      }
      onDeactivated(closePopup)
      onBeforeUnmount(closePopup)
      const tempTableProps = toRef(props, 'columns')
      const originColumns = cloneDeep<TablePropsType[]>(tempTableProps.value!)
      const tempArray =
        tempTableProps.value
          ?.filter((it) => !!it.key)
          .map((it) => {
            return {
              ...it,
              checked: true,
            } as TablePropsType
          }) || []
      const innerTableProps = reactive<TablePropsType[]>(tempArray)
      const isIndeterminate = ref(
        innerTableProps.filter((it) => it.checked).length !== innerTableProps.length
      )
      const allChecked = ref(innerTableProps.every((it) => it.checked))

      function onAllChange(value: any) {
        innerTableProps.forEach((it) => (it.checked = value))
        onUpdateValue(innerTableProps.filter((it) => it.checked))
      }

      const onChange = () => {
        const checkedItems = innerTableProps.filter((it) => it.checked)
        allChecked.value = checkedItems.length === innerTableProps.length
        isIndeterminate.value =
          checkedItems.length > 0 && checkedItems.length !== innerTableProps.length
        onUpdateValue(checkedItems)
      }
      const onReset = () => {
        innerTableProps.length = 0
        innerTableProps.push(...originColumns)
        innerTableProps.forEach((it) => (it.checked = true))
        allChecked.value = true
        onUpdateValue(innerTableProps)
      }

      function onUpdateValue(columns: TablePropsType[]) {
        emit(
          'update',
          columns.filter((it) => it.checked)
        )
      }

      function onPopVisibleChange(visible: boolean) {
        popupVisible.value = visible
        disposeSortable()
        if (visible) {
          const generation = popupGeneration
          nextTick(() => {
            if (generation !== popupGeneration || !sortColumnWrapper.value) return
            sortable = new Sortable(sortColumnWrapper.value, {
              handle: '.mango-handle-icon',
              animation: 150,
              dataIdAttr: '',
              onEnd({ newIndex, oldIndex }) {
                if (generation !== popupGeneration) return
                if (isUndefined(newIndex) || isUndefined(oldIndex)) {
                  return
                }
                if (newIndex < 0 || oldIndex < 0 || newIndex >= innerTableProps.length || oldIndex >= innerTableProps.length) return
                const originItem = innerTableProps[oldIndex]
                if (newIndex > oldIndex) {
                  innerTableProps.splice(newIndex + 1, 0, originItem)
                  innerTableProps.splice(oldIndex, 1)
                } else {
                  innerTableProps.splice(newIndex, 0, originItem)
                  innerTableProps.splice(oldIndex + 1, 1)
                }
                onUpdateValue(innerTableProps)
              },
            })
          })
        }
      }

      return {
        popupVisible,
        sortColumnWrapper,
        innerTableProps,
        isIndeterminate,
        allChecked,
        onAllChange,
        onChange,
        onReset,
        onUpdateValue,
        onPopVisibleChange,
      }
    },
  })
</script>

<style lang="less" scoped>
  :deep(.mango-sortable-table-popover) {
    width: 200px;
  }

  .mango-sortable-table-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--m-border);
    color: var(--m-text);
  }

  .mango-sortable-table-list {
    padding: 8px 0;
  }

  .mango-column-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px;
    color: var(--m-text-2);
    border-radius: var(--m-radius-sm);
    transition: background-color 0.16s ease;

    &:hover {
      background: var(--m-table-row-hover);
    }

    .mango-handle-icon {
      flex: none;
      color: var(--m-muted);

      &:hover {
        cursor: move;
        color: var(--m-primary);
      }
    }
  }
</style>
