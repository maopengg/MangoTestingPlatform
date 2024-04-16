<template>
  <div>
    <a-card title="页面元素详情">
      <template #extra>
        <a-affix :offsetTop="80">
          <a-space>
            <a-button status="danger" size="small" @click="doResetSearch">返回</a-button>
          </a-space>
        </a-affix>
      </template>
      <div class="container">
        <a-space direction="vertical" style="width: 25%">
          <p>接口ID：{{ pageData.record.id }}</p>
          <span>所属项目：{{ pageData.record.project?.name }}</span>
          <span>顶级模块：{{ pageData.record.module_name?.superior_module }}</span>
          <span>所属模块：{{ pageData.record.module_name?.name }}</span>
        </a-space>
        <a-space direction="vertical" style="width: 25%">
          <span>接口名称：{{ pageData.record.name }}</span>
          <span>接口URL：{{ pageData.record.url }}</span>
          <span>接口方法：{{ data.apiMethodType[pageData.record.method] }}</span>
        </a-space>
      </div>
    </a-card>
    <a-card>
      <a-tabs @tab-click="(key) => switchType(key)">
        <template #extra>
          <a-space>
            <a-button type="primary" size="small" @click="doAppend">新增</a-button>
          </a-space>
        </template>
        <a-tab-pane key="0" title="请求头">
          <a-textarea
            placeholder="请输入请求头，字符串形式"
            :model-value="formatJson(pageData.record.header)"
            allow-clear
            auto-size
          />
        </a-tab-pane>
        <a-tab-pane key="1" title="参数">
          <a-textarea
            placeholder="请输入json格式的数据"
            :model-value="formatJson(pageData.record.params)"
            allow-clear
            auto-size
          />
        </a-tab-pane>
        <a-tab-pane key="2" title="表单">
          <a-textarea
            placeholder="请输入json格式的表单"
            :model-value="formatJson(pageData.record.data)"
            allow-clear
            auto-size
          />
        </a-tab-pane>
        <a-tab-pane key="3" title="JSON">
          <a-textarea
            placeholder="请输入json格式的JSON"
            :model-value="formatJson(pageData.record.json)"
            allow-clear
            auto-size
          />
        </a-tab-pane>
        <a-tab-pane key="4" title="文件">
          <a-textarea
            placeholder="请输入json格式的文件上传数据"
            :model-value="formatJson(pageData.record.file)"
            allow-clear
            auto-size
          />
        </a-tab-pane>
      </a-tabs>
    </a-card>
  </div>
  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
          :label="item.label"
          v-for="item of formItems"
          :key="item.key"
        >
          <template v-if="item.type === 'input'">
            <a-input :placeholder="item.placeholder" v-model="item.value" />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'type'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="data.apiParameterType"
              :field-names="fieldNames"
              value-key="key"
              allow-clear
              allow-search
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>
<script lang="ts" setup>
  import { nextTick, onMounted, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { apiInfo, systemEnumApiParameterType, systemEnumMethod } from '@/api/url'
  import { get, post, put } from '@/api/http'
  import { FormItem, ModalDialogType } from '@/types/components'
  import { useRoute } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { usePageData } from '@/store/page-data'
  const pageData: any = usePageData()
  const route = useRoute()
  const formModel = ref({})
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const data: any = reactive({
    id: 0,
    isAdd: false,
    updateId: 0,
    pageType: '0',
    actionTitle: '添加元素',
    apiParameterType: [],
    apiMethodType: [],
  })

  const formItems: FormItem[] = reactive([
    {
      label: '参数类型',
      key: 'type',
      value: null,
      type: 'select',
      required: true,
      placeholder: '请选择参数类型',
      validator: function () {
        if (!this.value && this.value !== 0) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: 'key',
      key: 'key',
      value: '',
      type: 'input',
      required: false,
      placeholder: '请输入key',
      validator: function () {
        return true
      },
    },
    {
      label: 'value',
      key: 'value',
      value: '',
      type: 'input',
      required: false,
      placeholder: '请输入value',
    },
    {
      label: '描述',
      key: 'describe',
      value: '',
      type: 'input',
      required: false,
      placeholder: '请输入参数描述',
    },
  ])

  function switchType(key: any) {
    data.pageType = key
  }

  function doResetSearch() {
    window.history.back()
  }

  function doAppend() {
    data.actionTitle = '添加元素'
    data.isAdd = true
    modalDialogRef.value?.toggle()
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = ''
      }
    })
  }
  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      modalDialogRef.value?.toggle()
      let value = getFormItems(formItems)
      value['api_info_id'] = route.query.id
      if (data.isAdd) {
        post({
          url: apiInfo,
          data: () => {
            return value
          },
        })
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
      } else {
        put({
          url: apiInfo,
          data: () => {
            value['id'] = data.updateId
            return value
          },
        })
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
      }
    }
  }

  function formatJson(items: any) {
    if (items === null) {
      return null
    }
    return JSON.stringify(items, null, 2)
  }
  function enumApiParameterType() {
    get({
      url: systemEnumApiParameterType,
      data: () => {
        return {}
      },
    })
      .then((res) => {
        data.apiParameterType = res.data
      })
      .catch(console.log)
  }

  function doMethod() {
    get({
      url: systemEnumMethod,
      data: () => {
        return {}
      },
    })
      .then((res) => {
        res.data.forEach((item: any) => {
          data.apiMethodType.push(item.title)
        })
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      await doMethod()
      enumApiParameterType()
    })
  })
</script>
