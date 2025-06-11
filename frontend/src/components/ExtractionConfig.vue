<template>
  <div class="extraction-config">
    <!-- 提取字段配置 -->
    <el-divider content-position="left">提取字段配置</el-divider>
    
    <div class="fields-config">
      <div class="fields-header">
        <span>字段列表</span>
        <el-button 
          type="primary" 
          size="small" 
          @click="addField"
        >
          <el-icon><Plus /></el-icon>
          添加字段
        </el-button>
      </div>

      <div class="fields-list" v-if="extractionFields.length > 0">
        <div 
          v-for="(field, index) in extractionFields" 
          :key="index"
          class="field-item"
        >
          <el-row :gutter="10" align="middle">
            <el-col :span="4">
              <el-input 
                v-model="field.key" 
                placeholder="字段键名"
                size="small"
              />
            </el-col>
            <el-col :span="4">
              <el-input 
                v-model="field.label" 
                placeholder="字段标签"
                size="small"
              />
            </el-col>
            <el-col :span="3">
              <el-select 
                v-model="field.type" 
                placeholder="类型"
                size="small"
              >
                <el-option label="文本" value="text" />
                <el-option label="多行文本" value="textarea" />
                <el-option label="日期" value="date" />
                <el-option label="日期时间" value="datetime" />
                <el-option label="数字" value="number" />
              </el-select>
            </el-col>
            <el-col :span="2">
              <el-checkbox v-model="field.required" size="small">
                必填
              </el-checkbox>
            </el-col>
            <el-col :span="8">
              <el-input 
                v-model="field.placeholder" 
                placeholder="占位符文本"
                size="small"
              />
            </el-col>
            <el-col :span="3">
              <el-button 
                type="danger" 
                size="small" 
                @click="removeField(index)"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </el-col>
          </el-row>
        </div>
      </div>
      <el-empty v-else description="请点击“添加字段”开始配置"></el-empty>
    </div>

    <!-- 自定义提示词 -->
    <el-divider content-position="left">自定义提示词</el-divider>
    
    <el-form-item>
      <template #label>
        <span>提示词模板</span>
        <el-tooltip content="使用 {text} 作为文本内容的占位符" placement="top">
          <el-icon><QuestionFilled /></el-icon>
        </el-tooltip>
      </template>
      <el-input 
        v-model="customPrompt" 
        type="textarea" 
        :rows="8"
        placeholder="输入自定义提示词，使用 {text} 作为文本内容的占位符。留空则使用默认提示词。"
      />
    </el-form-item>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Plus, Delete, QuestionFilled } from '@element-plus/icons-vue'
import { cloneDeep } from 'lodash-es';

// Props
const props = defineProps({
  modelValue: {
    type: Object,
    required: true,
    default: () => ({
      extraction_fields: [],
      custom_prompt: ''
    })
  }
})

// Emits
const emit = defineEmits(['update:modelValue'])

// 响应式数据
const extractionFields = ref([])
const customPrompt = ref('')

// 默认字段模板
const defaultField = () => ({
  key: '',
  label: '',
  type: 'text',
  required: false,
  placeholder: ''
})

// 更新父组件的值
const updateModelValue = () => {
  emit('update:modelValue', {
    extraction_fields: extractionFields.value,
    custom_prompt: customPrompt.value
  })
}

// 监听字段变化
watch([extractionFields, customPrompt], () => {
  updateModelValue()
}, { deep: true })

// 监听props变化
watch(() => props.modelValue, (newValue) => {
  if (newValue) {
    // Deep copy to avoid mutating prop directly
    extractionFields.value = cloneDeep(newValue.extraction_fields || []);
    customPrompt.value = newValue.custom_prompt || '';
  }
}, { immediate: true, deep: true })


// 添加字段
const addField = () => {
  extractionFields.value.push(defaultField())
}

// 删除字段
const removeField = (index) => {
  extractionFields.value.splice(index, 1)
}

</script>

<style scoped>
.extraction-config {
  width: 100%;
}

.fields-config {
  margin: 20px 0;
}

.fields-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  font-weight: 600;
}

.fields-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.field-item {
  padding: 10px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background-color: #fafafa;
}
</style> 