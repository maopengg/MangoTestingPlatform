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
          <a-collapse-item
            :header="
              item.name
                ? item.name
                : useSelectValue.getSelectLabel(item.ope_key) ||
                  enumStore.element_ope[item.type]?.title
            "
            :style="customStyle"
            :key="item.id"
          >
            <div>
              <a-space direction="vertical" style="width: 50%">
                <p>
                  <span class="label">操作类型</span>：{{
                    item.type
                      ? useSelectValue.getSelectLabel(item.ope_key)
                      : useSelectValue.getSelectLabel(item.ope_key)
                  }}
                </p>
                <p v-if="item.sub"
                  ><span class="label">元素下标</span>：{{ item.sub ? item.sub : '-' }}</p
                >
                <p><span class="label">等待时间</span>：{{ item.sleep ? item.sleep : '-' }}</p>

                <p>
                  <span class="label">测试结果</span>：{{
                    item.status === 1 ? '通过' : item.status === 0 ? '失败' : '未测试'
                  }}
                </p>
                <div v-if="item.status === 0 && item?.error_message">
                  <span class="label">错误提示</span>：
                  <div class="error-container">
                    <span class="error-message" :title="item.error_message">
                      {{ item.error_message }}
                    </span>
                  </div>
                </div>
                <p v-if="item.ass_msg"><span class="label">断言提示</span>：{{ item.ass_msg }}</p>
                <p v-if="item.status === 0 && item?.video_path"
                  ><span class="label">视频路径</span>：{{ item.video_path }}</p
                >
                <div v-if="item.status === 0 && item?.picture_path">
                  <p
                    ><span class="label">失败截图</span>：
                    <a-image
                      :src="minioURL + '/' + item.picture_path"
                      width="100"
                      style="margin-right: 67px; vertical-align: top"
                    />
                  </p>
                </div>
              </a-space>
              <a-space direction="vertical" id="maopeng2" style="width: 50%">
                <template v-if="item.elements && item.elements.length">
                  <template v-for="(element, index) in item.elements" :key="index">
                    <p>
                      <span class="label">定位类型-{{ index + 1 }}</span
                      >：{{
                        enumStore.element_exp.find((item1) => item1.key === element.exp)?.title
                      }}
                    </p>
                    <p style="word-wrap: break-word"
                      ><span class="label">定位元素-{{ index + 1 }}</span
                      >：{{ element.loc }}</p
                    >
                    <p style="word-wrap: break-word"
                      ><span class="label">元素下标-{{ index + 1 }}</span
                      >：{{ element?.sub }}</p
                    >
                    <p
                      ><span class="label">元素个数-{{ index + 1 }}</span
                      >：{{ element.ele_quantity }}</p
                    >
                    <p v-if="element?.element_text"
                      ><span class="label">元素文本-{{ index + 1 }}</span
                      >：{{ element?.element_text }}</p
                    >
                  </template>
                </template>

                <template v-else-if="item?.loc">
                  <p>
                    <span class="label">表达式类型</span>：{{
                      enumStore.element_exp.find((item1) => item1.key === item.exp)?.title
                    }}
                  </p>
                  <p style="word-wrap: break-word"
                    ><span class="label">元素表达式</span>：{{ item.loc }}</p
                  >
                  <p><span class="label">元素个数</span>：{{ item.ele_quantity }}</p>
                  <p v-if="item?.element_text"
                    ><span class="label">元素文本</span>：{{ item?.element_text }}</p
                  >
                </template>
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
  import { useSelectValueStore } from '@/store/modules/get-ope-value'

  defineProps({
    resultData: {
      type: Array as () => any,
      required: true,
    },
  })
  const enumStore = useEnum()
  const useSelectValue = useSelectValueStore()

  // const visible = ref(false)

  const customStyle = reactive({
    borderRadius: '6px',
    marginBottom: '2px',
    border: 'none',
    overflow: 'hidden',
  })

  onMounted(() => {})
</script>

<style scoped>
  .label {
    display: inline-block;
    width: 80px;
    text-align: right;
  }

  .error-container {
    display: inline-block;
    max-width: 150px; /* 根据实际布局调整 */
    vertical-align: middle;
  }

  .error-message {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    cursor: pointer;
    padding: 2px 4px;
    border-radius: 3px;
  }

  .error-message:hover {
    background-color: #fff2f0;
    white-space: normal;
    word-wrap: break-word;
    position: absolute;
    z-index: 1000;
    background: #fff;
    border: 1px solid #ddd;
    padding: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    max-width: 300px; /* 悬停时最大宽度 */
  }
</style>
