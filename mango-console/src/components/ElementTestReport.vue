<template>
  <a-tabs default-active-key="1">
    <template #extra>
      <a-tag v-if="resultData?.test_time">执行时间：{{ resultData?.test_time }}</a-tag>
    </template>
    <a-tab-pane key="1" title="执行过程">
      <a-space direction="vertical" style="width: 100%">
        <span style="padding-left: 20px"> tips：如果不是最新的测试结果，请点击上面的刷新！</span>
        <a-collapse
          v-for="item of resultData?.element_result_list"
          :bordered="false"
          :key="item.id"
          :default-active-key="
            resultData.element_result_list.filter((i) => i.status === 0).map((i) => i.id)
          "
          destroy-on-hide
        >
          <a-collapse-item :header="item.name" :style="customStyle" :key="item.id">
            <div>
              <a-space direction="vertical" style="width: 50%">
                <p>
                  <span class="label">操作类型</span>：{{
                    item.type
                      ? getLabelByValue(data.ass, item.ope_key)
                      : getLabelByValue(data.ope, item.ope_key)
                  }}
                </p>
                <p>
                  <span class="label">表达式类型</span>：{{
                    enumStore.element_exp.find((item1) => item1.key === item.exp)?.title
                  }}
                </p>
                <p>
                  <span class="label">测试结果</span>：{{
                    item.status === 1 ? '通过' : item.status === 0 ? '失败' : '未测试'
                  }}
                </p>
                <p><span class="label">等待时间</span>：{{ item.sleep ? item.sleep : '-' }}</p>
                <p v-if="item.status === 0 && item?.error_message">
                  <span class="label">错误提示</span>：{{ item.error_message }}
                </p>
                <p v-if="item.ass_msg"><span class="label">预期</span>：{{ item.ass_msg }}</p>
                <p v-if="item.status === 0 && item?.video_path"
                  ><span class="label">视频路径</span>：{{ item.video_path }}</p
                >
              </a-space>
              <a-space direction="vertical" style="width: 50%">
                <p style="word-wrap: break-word"
                  ><span class="label">元素表达式</span>：{{ item.loc }}</p
                >
                <p><span class="label">元素个数</span>：{{ item.ele_quantity }}</p>
                <p><span class="label">元素下标</span>：{{ item.sub ? item.sub : '-' }}</p>
                <p v-if="item?.element_text"
                  ><span class="label">元素文本</span>：{{ item?.element_text }}</p
                >
                <div v-if="item.status === 0 && item?.picture_name">
                  <a-image
                    :src="minioURL + '/mango-file/failed_screenshot/' + item.picture_name"
                    title="失败截图"
                    width="260"
                    style="margin-right: 67px; vertical-align: top"
                  >
                    <template #extra>
                      <div class="actions">
                        <span class="action">
                          <icon-download />
                        </span>
                        <a-tooltip content="失败截图">
                          <span class="action">
                            <icon-info-circle />
                          </span>
                        </a-tooltip>
                      </div>
                    </template>
                  </a-image>
                </div>
              </a-space>
            </div>
          </a-collapse-item>
        </a-collapse>
      </a-space>
    </a-tab-pane>
    <a-tab-pane key="2" title="其他信息">
      <a-space direction="vertical" style="width: 100%">
        <a-space v-if="resultData?.status === 0">
          <span>失败描述：{{ resultData?.error_message || '无' }}</span>
        </a-space>
        <a-space>
          <span>测试对象：{{ resultData?.test_object }}</span>
        </a-space>
        <a-space>
          <span>缓存数据：</span>
          <pre>{{ resultData?.cache_data }}</pre>
        </a-space>
        <a-space v-if="resultData?.video_path">视频路径：{{ resultData?.video_path }}</a-space>
      </a-space>
    </a-tab-pane>
  </a-tabs>
</template>

<script setup lang="ts">
  import { onMounted, reactive } from 'vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { minioURL } from '@/api/axios.config'
  import { getSystemCacheDataKeyValue } from '@/api/system/cache_data'

  defineProps({
    resultData: {
      type: Array as () => any,
      required: true,
    },
  })
  const data: any = reactive({
    ass: [],
    ope: [],
  })
  const enumStore = useEnum()
  // const visible = ref(false)

  const customStyle = reactive({
    borderRadius: '6px',
    marginBottom: '2px',
    border: 'none',
    overflow: 'hidden',
  })

  function getLabelByValue(opeData: any, value: string): string {
    const list = [...opeData]
    for (const item of list) {
      if (item.children) {
        list.push(...item.children)
      }
    }
    return list.find((item: any) => item.value === value)?.label
  }

  function getCacheDataKeyValue() {
    getSystemCacheDataKeyValue('select_value')
      .then((res) => {
        res.data.forEach((item: any) => {
          if (item.value === 'web') {
            data.ope.push(...item.children)
          } else if (item.value === 'android') {
            data.ope.push(...item.children)
          } else if (item.value === 'ass_android') {
            data.ass.push(...item.children)
          } else if (item.value === 'ass_web') {
            data.ass.push(...item.children)
          } else if (item.value.includes('断言')) {
            data.ass.push(item)
          }
        })
      })
      .catch(console.log)
  }

  defineExpose({
    getLabelByValue,
  })
  onMounted(() => {
    getCacheDataKeyValue()
  })
</script>

<style scoped>
  .label {
    display: inline-block;
    width: 80px;
    text-align: right;
    margin-right: 8px;
  }
</style>
