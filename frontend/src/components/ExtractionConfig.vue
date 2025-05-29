<template>
  <div class="extraction-config">
    <el-card class="config-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <el-icon><Setting /></el-icon>
          <span>提取配置</span>
          <div class="header-actions">
            <el-button 
              type="success" 
              size="small" 
              @click="saveAsTemplate"
            >
              保存为模板
            </el-button>
          </div>
        </div>
      </template>

      <!-- 模板选择 -->
      <el-form-item label="选择模板">
        <el-select 
          v-model="selectedTemplate" 
          placeholder="选择已有模板或使用默认配置"
          clearable
          style="width: 100%"
          @change="handleTemplateSelectionChange"
        >
          <el-option
            v-for="template in templates"
            :key="template.id"
            :label="template.name"
            :value="template.id"
          >
            <span>{{ template.name }}</span>
            <span style="float: right; color: #8492a6; font-size: 13px">
              {{ template.description }}
            </span>
          </el-option>
        </el-select>
      </el-form-item>

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

        <div class="fields-list">
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
                  :disabled="extractionFields.length <= 1"
                >
                  <el-icon><Delete /></el-icon>
                </el-button>
              </el-col>
            </el-row>
          </div>
        </div>
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

      <!-- 预览区域 -->
      <el-divider content-position="left">配置预览</el-divider>
      
      <div class="config-preview">
        <el-descriptions title="当前配置" :column="1" border>
          <el-descriptions-item label="提取字段数量">
            {{ extractionFields.length }} 个字段
          </el-descriptions-item>
          <el-descriptions-item label="必填字段">
            {{ extractionFields.filter(f => f.required).length }} 个
          </el-descriptions-item>
          <el-descriptions-item label="自定义提示词">
            {{ customPrompt ? '已设置' : '使用默认' }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-card>

    <!-- 保存模板对话框 -->
    <el-dialog 
      v-model="saveTemplateDialogVisible" 
      title="保存为模板"
      width="500px"
    >
      <el-form :model="newTemplate" label-width="80px">
        <el-form-item label="模板名称" required>
          <el-input v-model="newTemplate.name" placeholder="请输入模板名称" />
        </el-form-item>
        <el-form-item label="模板描述">
          <el-input 
            v-model="newTemplate.description" 
            type="textarea" 
            :rows="3"
            placeholder="请输入模板描述"
          />
        </el-form-item>
        <el-form-item label="设为默认">
          <el-checkbox v-model="newTemplate.isDefault">
            设为默认模板
          </el-checkbox>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="saveTemplateDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmSaveTemplate">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  Setting, 
  Plus, 
  Delete, 
  QuestionFilled 
} from '@element-plus/icons-vue'
import { pdfApi } from '../api'

// Props
const props = defineProps({
  modelValue: {
    type: Object,
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
const templates = ref([])
const selectedTemplate = ref('')
const saveTemplateDialogVisible = ref(false)
const newTemplate = ref({
  name: '',
  description: '',
  isDefault: false
})

// 默认字段模板
const defaultField = () => ({
  key: '',
  label: '',
  type: 'text',
  required: false,
  placeholder: ''
})

// 加载默认配置
const loadDefaultConfig = async () => {
  try {
    const response = await pdfApi.getDefaultConfig()
    extractionFields.value = response.extraction_fields || []
    customPrompt.value = ''
    updateModelValue()
  } catch (error) {
    ElMessage.error('加载默认配置失败')
    console.error(error)
  }
}

// 加载模板列表
const loadTemplates = async () => {
  try {
    const response = await pdfApi.getTemplates()
    templates.value = response || []
  } catch (error) {
    ElMessage.error('加载模板列表失败')
    console.error(error)
  }
}

// 修改: loadTemplate 不再需要检查 selectedTemplate.value, 因为它由 watch 或 change 事件触发
const loadTemplateById = async (templateId) => {
  if (!templateId) { // 如果传入的id为空 (例如清空选择时)
    // 可以选择重置为默认配置或清空当前配置
    // 这里我们选择清空，如果需要重置为系统默认，可以调用 loadDefaultConfig()
    extractionFields.value = [];
    customPrompt.value = '';
    updateModelValue();
    // ElMessage.info('已清空配置'); // 可选提示
    return;
  }
  
  try {
    const template = await pdfApi.getTemplate(templateId)
    extractionFields.value = template.extraction_fields || []
    customPrompt.value = template.custom_prompt || ''
    updateModelValue()
    ElMessage.success(`模板 "${template.name}" 加载成功`)
  } catch (error) {
    ElMessage.error('加载模板失败')
    console.error(error)
  }
}

// 新增: el-select的change事件处理器
const handleTemplateSelectionChange = (templateId) => {
  if (templateId) {
    loadTemplateById(templateId);
  } else {
    // 当选择被清空时，selectedTemplate 会是 null 或 undefined
    // 清空当前配置或加载一个"空"状态
    extractionFields.value = props.modelValue.extraction_fields?.length ? [...props.modelValue.extraction_fields] : [defaultField()];
    customPrompt.value = props.modelValue.custom_prompt || '';
    // 或者，如果希望清空而不是恢复初始/父级状态:
    // extractionFields.value = [defaultField()];
    // customPrompt.value = '';
    updateModelValue();
    ElMessage.info('已取消模板选择，恢复为当前配置');
  }
};

// 添加字段
const addField = () => {
  extractionFields.value.push(defaultField())
  updateModelValue()
}

// 删除字段
const removeField = (index) => {
  extractionFields.value.splice(index, 1)
  updateModelValue()
}

// 保存为模板
const saveAsTemplate = () => {
  if (extractionFields.value.length === 0) {
    ElMessage.warning('请至少添加一个提取字段')
    return
  }
  saveTemplateDialogVisible.value = true
}

// 确认保存模板
const confirmSaveTemplate = async () => {
  if (!newTemplate.value.name.trim()) {
    ElMessage.warning('请输入模板名称')
    return
  }
  
  try {
    const templateData = {
      name: newTemplate.value.name,
      description: newTemplate.value.description,
      extraction_fields: extractionFields.value,
      custom_prompt: customPrompt.value,
      is_default: newTemplate.value.isDefault ? 'true' : 'false'
    }
    
    await pdfApi.createTemplate(templateData)
    ElMessage.success('模板保存成功')
    saveTemplateDialogVisible.value = false
    
    // 重置表单
    newTemplate.value = {
      name: '',
      description: '',
      isDefault: false
    }
    
    // 重新加载模板列表
    loadTemplates()
  } catch (error) {
    ElMessage.error('保存模板失败')
    console.error(error)
  }
}

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
    // 当 selectedTemplate 为空时，我们希望组件反映父组件传入的 modelValue
    // 只有当用户没有主动选择模板时，才同步 modelValue
    if (!selectedTemplate.value) { 
      extractionFields.value = newValue.extraction_fields?.length ? [...newValue.extraction_fields] : [defaultField()];
      customPrompt.value = newValue.custom_prompt || '';
    }
  }
}, { immediate: true, deep: true })

// 组件挂载时加载数据
onMounted(() => {
  loadDefaultConfig()
  loadTemplates()
})
</script>

<style scoped>
.extraction-config {
  width: 100%;
}

.config-card {
  border-radius: 8px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  justify-content: space-between;
}

.header-actions {
  display: flex;
  gap: 8px;
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

.config-preview {
  margin-top: 20px;
}

:deep(.el-descriptions__title) {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 15px;
}
</style> 