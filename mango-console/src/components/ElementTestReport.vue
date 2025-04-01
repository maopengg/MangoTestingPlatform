<template>
  <a-tabs default-active-key="1">
    <a-tab-pane key="1" title="执行过程">
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
                操作类型：{{
                  item.type
                    ? getLabelByValue(data.ass, item.ope_key)
                    : getLabelByValue(data.ope, item.ope_key)
                }}
              </p>
              <p>
                表达式类型：{{
                  enumStore.element_exp.find((item1) => item1.key === item.exp)?.title
                }}
              </p>
              <p>
                测试结果：{{ item.status === 1 ? '通过' : item.status === 0 ? '失败' : '未测试' }}
              </p>
              <p>等待时间：{{ item.sleep ? item.sleep : '-' }}</p>
              <p v-if="item.status === 0">错误提示：{{ item.error_message }}</p>
              <p v-if="item.expect">预期：{{ item.expect }}</p>
              <p v-if="item.status === 0">视频路径：{{ item.video_path }}</p>
            </a-space>
            <a-space direction="vertical" style="width: 50%">
              <p style="word-wrap: break-word">元素表达式：{{ item.loc }}</p>
              <p>元素个数：{{ item.ele_quantity }}</p>
              <p>元素下标：{{ item.sub ? item.sub : '-' }}</p>
              <div v-if="item.status === 0">
                <a-image
                  :src="minioURL + '/mango-file/failed_screenshot/' + item.picture_path"
                  title="失败截图"
                  width="260"
                  style="margin-right: 67px; vertical-align: top"
                  :preview-visible="visible"
                  @preview-visible-change="visible = false"
                >
                  <template #extra>
                    <div class="actions">
                      <span class="action" @click="visible = true">
                        <icon-eye />
                      </span>
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
              <p v-if="item.expect">实际：{{ item.actual }}</p>
            </a-space>
          </div>
        </a-collapse-item>
      </a-collapse>
    </a-tab-pane>
    <a-tab-pane key="2" title="其他信息">
      <a-space direction="vertical" size="large">
        <div v-if="resultData?.status === 0">
          <span>失败描述：{{ resultData?.error_message || '无' }}</span>
        </div>

        <div>
          <span
            >测试对象：{{
              resultData?.test_object?.url
                ? resultData?.test_object?.url
                : resultData?.test_object?.package_name
            }}</span
          >
        </div>

        <div>
          <span>缓存数据：</span>
          <pre>{{ resultData?.cache_data }}</pre>
        </div>

        <div>
          <span>浏览器路径：{{ resultData?.equipment?.web_path || '无' }}</span>
        </div>
      </a-space>
    </a-tab-pane>
  </a-tabs>
</template>

<script setup lang="ts">
  import { onMounted, reactive, ref } from 'vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { minioURL } from '@/api/axios.config'
  import {
    getUiPageStepsDetailedAss,
    getUiPageStepsDetailedOpe,
  } from '@/api/uitest/page-steps-detailed'

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
  const visible = ref(false)

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

  function getUiRunSortAss() {
    getUiPageStepsDetailedAss(null)
      .then((res) => {
        data.ass = res.data
      })
      .catch(console.log)
  }

  function getUiRunSortOpe() {
    getUiPageStepsDetailedOpe(null)
      .then((res) => {
        data.ope = res.data
      })
      .catch(console.log)
  }

  defineExpose({
    getLabelByValue,
  })
  onMounted(() => {
    getUiRunSortOpe()
    getUiRunSortAss()
  })
</script>

<style scoped></style>
