import { defineStore } from 'pinia'
import { getSystemCacheDataKeyValue } from '@/api/system/cache_data'

// 参数配置项类型
interface ParameterItem {
  f: string // 字段名
  n: string // 名称
  p: string // 提示信息
  d: boolean // 是否默认
  v: string // 默认值
}

// 子项类型
interface ChildrenItem {
  value: string // 值
  label: string // 标签
  parameter: ParameterItem[] // 参数配置
  sort: number // 排序
}

// 主项类型
interface SelectValueItem {
  label: string // 标签
  value: string // 值
  children: ChildrenItem[] // 子项列表
}

type StateValueType = SelectValueItem[]

interface SlsectValueState {
  data: StateValueType
  dataList: ChildrenItem[]
  webOpe: ChildrenItem[]
  androidOpe: ChildrenItem[]
  assAndroid: (ChildrenItem | SelectValueItem)[]
  assWeb: (ChildrenItem | SelectValueItem)[]
  ass: SelectValueItem[]
}

export const useSelectValueStore = defineStore('get-select-value', {
  state: (): SlsectValueState => ({
    data: [],
    dataList: [],
    webOpe: [],
    androidOpe: [],
    assAndroid: [],
    assWeb: [],
    ass: [],
  }),
  getters: {},
  actions: {
    getSelectValue() {
      getSystemCacheDataKeyValue('select_value')
        .then((res) => {
          this.data = res.data
          this.dataList = [...this.data]
          for (const item of this.dataList) {
            if (item.children) {
              this.dataList.push(...item.children)
            }
          }
          this.webOpe = []
          this.androidOpe = []
          this.assAndroid = []
          this.assWeb = []
          this.ass = []
          this.data.forEach((item: SelectValueItem) => {
            if (item.value === 'web') {
              this.webOpe.push(...item.children)
            } else if (item.value === 'android') {
              this.androidOpe.push(...item.children)
            } else if (item.value === 'ass_android') {
              this.assAndroid.push(...item.children)
            } else if (item.value === 'ass_web') {
              this.assWeb.push(...item.children)
            } else if (item.value.includes('断言')) {
              this.ass.push(item)
              this.assAndroid.push(item)
              this.assWeb.push(item)
            }
          })
        })
        .catch(console.log)
    },
    getSelectLabel(value: string): ChildrenItem[] {
      // 如果数据为空，则调用初始化函数
      if (!this.dataList || this.dataList.length === 0) {
        this.getSelectValue()
      }
      return this.dataList.find((item: any) => item.value === value)?.label
    },
    findItemByValue(value: string): ChildrenItem | undefined {
      // 检查数据是否存在
      if (!this.data || !Array.isArray(this.data)) {
        return undefined
      }

      const findItem = (data: SelectValueItem[], targetValue: string): ChildrenItem | undefined => {
        if (!data || !Array.isArray(data)) {
          return undefined
        }

        for (let i = 0; i < data.length; i++) {
          const item = data[i]
          if (!item) continue

          // 检查children是否存在且为数组
          if (item.children && Array.isArray(item.children)) {
            // 在children中查找
            for (let j = 0; j < item.children.length; j++) {
              const childItem = item.children[j]
              if (childItem && childItem.value === targetValue) {
                return childItem
              }
            }
            // 递归查找子项的children（如果存在）
            const foundChild = findItem(item.children as any, targetValue)
            if (foundChild) {
              return foundChild
            }
          }
        }
        return undefined
      }

      return findItem(this.data, value)
    },

    /**
     * 根据子项的值查找所属的顶级对象的label
     * @param value 子项的值
     * @returns 顶级对象的label，如果未找到则返回undefined
     */
    getTopLevelLabelByValue(value: string): object {
      // 检查数据是否存在
      if (!this.data || !Array.isArray(this.data)) {
        return undefined
      }

      // 遍历所有顶级对象
      for (const topLevelItem of this.data) {
        // 检查当前顶级对象是否匹配
        if (topLevelItem.value === value) {
          return topLevelItem
        }

        // 检查当前顶级对象的子项是否包含目标值
        if (topLevelItem.children && Array.isArray(topLevelItem.children)) {
          // 在子项中查找
          const foundChild = topLevelItem.children.find((child) => child.value === value)
          if (foundChild) {
            return topLevelItem
          }

          // 递归检查嵌套的子项
          const findInNestedChildren = (children: ChildrenItem[]): boolean => {
            for (const child of children) {
              if (child.value === value) {
                return true
              }
              // 如果子项还有自己的子项，继续递归查找
              if (
                child.children &&
                Array.isArray(child.children) &&
                findInNestedChildren(child.children)
              ) {
                return true
              }
            }
            return false
          }

          if (findInNestedChildren(topLevelItem.children)) {
            return topLevelItem
          }
        }
      }

      return undefined
    },
  },
  presist: {
    enable: true,
    resetToState: true,
  },
})
