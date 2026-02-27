<template>
  <a-tabs default-active-key="1">
    <template #extra>
      <a-tag v-if="resultData?.test_time">执行时间：{{ resultData?.test_time }}</a-tag>
    </template>
    <a-tab-pane key="1" title="执行过程">
      <a-space direction="vertical" style="width: 100%">
        <TipMessage message="如果不是最新的测试结果，请点击上面的刷新！" />
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
            <div class="collapse-content">
              <div class="info-section">
                <a-space direction="vertical" style="width: 100%">
                  <p>
                    <span class="label">操作类型</span>：{{
                      useSelectValue.getSelectLabel(item.ope_key)
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
              </div>

              <div class="elements-section">
                <div class="elements-scroll-container">
                  <template v-if="item.elements && item.elements.length">
                    <template v-for="(element, index) in item.elements" :key="index">
                      <div class="element-item">
                        <p>
                          <span class="label">定位类型-{{ index + 1 }}</span
                          >：{{
                            enumStore.element_exp.find((item1) => item1.key === element.exp)?.title
                          }}
                        </p>
                        <p class="element-text"
                          ><span class="label">定位元素-{{ index + 1 }}</span
                          >：{{ element.loc }}</p
                        >
                        <p
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
                      </div>
                    </template>
                  </template>

                  <template v-else-if="item?.loc">
                    <div class="element-item">
                      <p>
                        <span class="label">表达式类型</span>：{{
                          enumStore.element_exp.find((item1) => item1.key === item.exp)?.title
                        }}
                      </p>
                      <p class="element-text"
                        ><span class="label">元素表达式</span>：{{ item.loc }}</p
                      >
                      <p><span class="label">元素个数</span>：{{ item.ele_quantity }}</p>
                      <p v-if="item?.element_text"
                        ><span class="label">元素文本</span>：{{ item?.element_text }}</p
                      >
                    </div>
                  </template>

                  <div v-if="!item.elements && !item.loc" class="no-elements"> 暂无元素信息 </div>
                </div>
              </div>
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
          <pre class="cache-data">{{ resultData?.cache_data }}</pre>
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
  import TipMessage from '@/components/TipMessage.vue'

  defineProps({
    resultData: {
      type: Array as () => any,
      required: true,
    },
  })
  const enumStore = useEnum()
  const useSelectValue = useSelectValueStore()

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
    font-weight: 500;
    color: #333;
  }

  .collapse-content {
    display: flex;
    gap: 20px;
  }

  .info-section {
    flex: 1;
    min-width: 0;
  }

  .elements-section {
    flex: 1;
    min-width: 0;
  }

  .elements-scroll-container {
    max-height: 220px;
    overflow-y: auto;
    border: 1px solid #e5e5e5;
    border-radius: 4px;
    padding: 12px;
    background-color: #fafafa;
  }

  .elements-scroll-container::-webkit-scrollbar {
    width: 6px;
  }

  .elements-scroll-container::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 10px;
  }

  .elements-scroll-container::-webkit-scrollbar-thumb {
    background: #c1c1c1;
    border-radius: 10px;
  }

  .elements-scroll-container::-webkit-scrollbar-thumb:hover {
    background: #a8a8a8;
  }

  .element-item {
    padding: 8px 0;
    border-bottom: 1px solid #eee;
  }

  .element-item:last-child {
    border-bottom: none;
  }

  .element-text {
    word-break: break-all;
  }

  .no-elements {
    text-align: center;
    color: #999;
    padding: 20px;
  }

  .error-container {
    display: inline-block;
    max-width: 150px;
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
    max-width: 300px;
  }

  .cache-data {
    background-color: #f5f5f5;
    padding: 10px;
    border-radius: 4px;
    max-height: 200px;
    overflow: auto;
    white-space: pre-wrap;
    word-wrap: break-word;
    margin: 0;
  }

  @media (max-width: 768px) {
    .collapse-content {
      flex-direction: column;
    }

    .elements-scroll-container {
      max-height: 200px;
    }
  }
</style>
