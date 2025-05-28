<template>
  <div class="case-detail">
    <div class="container">
      <!-- 返回按钮 -->
      <el-button 
        type="primary" 
        @click="$router.push('/')"
        class="back-button"
      >
        <el-icon><ArrowLeft /></el-icon>
        返回列表
      </el-button>

      <!-- 案例基本信息 -->
      <el-card class="info-card" shadow="hover" v-if="caseData">
        <template #header>
          <div class="card-header">
            <el-icon><Document /></el-icon>
            <span>{{ caseData.original_filename }}</span>
            <el-tag :type="getStatusType(caseData.status)">
              {{ getStatusText(caseData.status) }}
            </el-tag>
          </div>
        </template>

        <el-descriptions :column="2" border>
          <el-descriptions-item label="文件名">
            {{ caseData.original_filename }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(caseData.status)">
              {{ getStatusText(caseData.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="上传时间">
            {{ formatDate(caseData.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="处理完成时间">
            {{ caseData.processed_at ? formatDate(caseData.processed_at) : '未完成' }}
          </el-descriptions-item>
          <el-descriptions-item label="提取配置">
            <el-tag v-if="caseData.extraction_fields" type="info" size="small">
              自定义配置 ({{ caseData.extraction_fields.length }} 个字段)
            </el-tag>
            <el-tag v-else type="success" size="small">
              默认配置
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="自定义提示词">
            <el-tag v-if="caseData.custom_prompt" type="warning" size="small">
              已设置
            </el-tag>
            <el-tag v-else type="info" size="small">
              使用默认
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <div class="actions" v-if="caseData.status === 'completed'">
          <el-button type="success" @click="exportCase">
            <el-icon><Download /></el-icon>
            导出Excel
          </el-button>
          <el-button type="warning" @click="showReprocessDialog">
            <el-icon><Refresh /></el-icon>
            重新处理
          </el-button>
        </div>
      </el-card>

      <!-- 处理中状态 -->
      <el-card v-if="caseData && caseData.status !== 'completed' && caseData.status !== 'failed'" class="processing-card">
        <div class="processing-content">
          <el-icon class="processing-icon"><Loading /></el-icon>
          <h3>正在处理中...</h3>
          <p>{{ getProcessingMessage(caseData.status) }}</p>
          <el-progress 
            :percentage="getProcessingPercentage(caseData.status)" 
            :status="caseData.status === 'failed' ? 'exception' : 'success'"
          />
        </div>
      </el-card>

      <!-- 错误信息 -->
      <el-card v-if="caseData && caseData.status === 'failed'" class="error-card">
        <el-alert
          title="处理失败"
          :description="caseData.error_message || '未知错误'"
          type="error"
          show-icon
          :closable="false"
        />
        <div class="error-actions">
          <el-button type="warning" @click="showReprocessDialog">
            <el-icon><Refresh /></el-icon>
            重新处理
          </el-button>
        </div>
      </el-card>

      <!-- 提取的证据材料信息 -->
      <el-card 
        v-if="caseData && caseData.extracted_info && caseData.status === 'completed'" 
        class="extracted-info-card"
        shadow="hover"
      >
        <template #header>
          <div class="card-header">
            <el-icon><Edit /></el-icon>
            <span>提取的证据材料信息</span>
            <el-button 
              type="primary" 
              size="small" 
              @click="toggleEditMode"
            >
              {{ editMode ? '保存修改' : '编辑信息' }}
            </el-button>
          </div>
        </template>

        <el-form 
          :model="extractedInfo" 
          label-width="120px"
          class="extracted-form"
        >
          <!-- 动态渲染字段 -->
          <template v-if="displayFields.length > 0">
            <div v-for="field in displayFields" :key="field.key" class="field-group">
              <el-form-item :label="field.label">
                <!-- 文本输入 -->
                <el-input 
                  v-if="field.type === 'text'"
                  v-model="extractedInfo[field.key]" 
                  :readonly="!editMode"
                  :placeholder="field.placeholder || `请输入${field.label}`"
                />
                
                <!-- 多行文本 -->
                <el-input 
                  v-else-if="field.type === 'textarea'"
                  v-model="extractedInfo[field.key]" 
                  type="textarea" 
                  :rows="3"
                  :readonly="!editMode"
                  :placeholder="field.placeholder || `请输入${field.label}`"
                />
                
                <!-- 日期 -->
                <el-date-picker
                  v-else-if="field.type === 'date'"
                  v-model="extractedInfo[field.key]"
                  type="date"
                  :disabled="!editMode"
                  :placeholder="field.placeholder || `请选择${field.label}`"
                  format="YYYY-MM-DD"
                  value-format="YYYY-MM-DD"
                />
                
                <!-- 日期时间 -->
                <el-date-picker
                  v-else-if="field.type === 'datetime'"
                  v-model="extractedInfo[field.key]"
                  type="datetime"
                  :disabled="!editMode"
                  :placeholder="field.placeholder || `请选择${field.label}`"
                  format="YYYY-MM-DD HH:mm:ss"
                  value-format="YYYY-MM-DD HH:mm:ss"
                />
                
                <!-- 数字 -->
                <el-input-number
                  v-else-if="field.type === 'number'"
                  v-model="extractedInfo[field.key]"
                  :disabled="!editMode"
                  :placeholder="field.placeholder || `请输入${field.label}`"
                  style="width: 100%"
                />
                
                <!-- 默认文本 -->
                <el-input 
                  v-else
                  v-model="extractedInfo[field.key]" 
                  :readonly="!editMode"
                  :placeholder="field.placeholder || `请输入${field.label}`"
                />
              </el-form-item>
            </div>
          </template>
          
          <!-- 如果没有配置字段，显示原始JSON -->
          <template v-else>
            <el-alert
              title="未配置提取字段"
              description="该证据材料使用了旧版本的提取方式，显示原始提取结果"
              type="info"
              show-icon
              :closable="false"
            />
            <el-form-item label="原始提取结果">
              <el-input 
                :model-value="JSON.stringify(extractedInfo, null, 2)"
                type="textarea" 
                :rows="10"
                readonly
              />
            </el-form-item>
          </template>
        </el-form>

        <div class="form-actions" v-if="editMode">
          <el-button @click="cancelEdit">取消</el-button>
          <el-button type="primary" @click="saveChanges">保存修改</el-button>
        </div>
      </el-card>

      <!-- 提取配置信息 -->
      <el-card 
        v-if="caseData && (caseData.extraction_fields || caseData.custom_prompt)" 
        class="config-card"
        shadow="hover"
      >
        <template #header>
          <div class="card-header">
            <el-icon><Setting /></el-icon>
            <span>提取配置信息</span>
          </div>
        </template>

        <el-tabs>
          <el-tab-pane label="字段配置" v-if="caseData.extraction_fields">
            <el-table :data="caseData.extraction_fields" style="width: 100%">
              <el-table-column prop="key" label="字段键名" width="120" />
              <el-table-column prop="label" label="字段标签" width="120" />
              <el-table-column prop="type" label="字段类型" width="100" />
              <el-table-column prop="required" label="是否必填" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.required ? 'danger' : 'info'" size="small">
                    {{ row.required ? '必填' : '可选' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="placeholder" label="占位符" />
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="自定义提示词" v-if="caseData.custom_prompt">
            <el-input 
              :model-value="caseData.custom_prompt" 
              type="textarea" 
              :rows="8"
              readonly
              class="custom-prompt"
            />
          </el-tab-pane>
        </el-tabs>
      </el-card>

      <!-- OCR和VLM原始结果 -->
      <el-card 
        v-if="caseData && (caseData.ocr_text || caseData.vlm_text)" 
        class="raw-text-card"
        shadow="hover"
      >
        <template #header>
          <div class="card-header">
            <el-icon><View /></el-icon>
            <span>原始识别结果</span>
          </div>
        </template>

        <el-tabs>
          <el-tab-pane label="OCR识别结果" v-if="caseData.ocr_text">
            <el-input 
              :model-value="caseData.ocr_text" 
              type="textarea" 
              :rows="100"
              readonly
              class="raw-text"
            />
          </el-tab-pane>
          <el-tab-pane label="VLM分析结果" v-if="caseData.vlm_text">
            <el-input 
              :model-value="caseData.vlm_text" 
              type="textarea" 
              :rows="100"
              readonly
              class="raw-text"
            />
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </div>

    <!-- 重新处理对话框 -->
    <el-dialog 
      v-model="reprocessDialogVisible" 
      title="重新处理证据材料"
      width="80%"
      :close-on-click-modal="false"
    >
      <div class="reprocess-content">
        <p>您可以修改提取配置后重新处理该证据材料：</p>
        <ExtractionConfig v-model="reprocessConfig" />
      </div>
      
      <template #footer>
        <el-button @click="reprocessDialogVisible = false">取消</el-button>
        <el-button 
          type="primary" 
          @click="confirmReprocess"
          :loading="reprocessing"
        >
          开始重新处理
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  ArrowLeft, 
  Document, 
  Download, 
  Loading, 
  Edit, 
  View,
  Setting,
  Refresh
} from '@element-plus/icons-vue'
import { pdfApi } from '../api'
import ExtractionConfig from '../components/ExtractionConfig.vue'

const route = useRoute()
const caseData = ref(null)
const extractedInfo = ref({})
const editMode = ref(false)
const originalExtractedInfo = ref({})
const loading = ref(false)

// 重新处理相关
const reprocessDialogVisible = ref(false)
const reprocessConfig = ref({
  extraction_fields: [],
  custom_prompt: ''
})
const reprocessing = ref(false)

// 计算显示字段
const displayFields = computed(() => {
  if (caseData.value && caseData.value.extraction_fields) {
    return caseData.value.extraction_fields
  }
  return []
})

// 获取案例详情
const loadCaseDetail = async () => {
  loading.value = true
  try {
    const response = await pdfApi.getCase(route.params.id)
    caseData.value = response
    if (response.extracted_info) {
      extractedInfo.value = { ...response.extracted_info }
      originalExtractedInfo.value = { ...response.extracted_info }
    }
  } catch (error) {
    ElMessage.error('加载证据材料详情失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 切换编辑模式
const toggleEditMode = () => {
  if (editMode.value) {
    saveChanges()
  } else {
    editMode.value = true
  }
}

// 保存修改
const saveChanges = async () => {
  try {
    await pdfApi.updateCase(route.params.id, {
      extracted_info: extractedInfo.value
    })
    ElMessage.success('保存成功')
    editMode.value = false
    originalExtractedInfo.value = { ...extractedInfo.value }
    // 重新加载数据
    loadCaseDetail()
  } catch (error) {
    ElMessage.error('保存失败')
    console.error(error)
  }
}

// 取消编辑
const cancelEdit = () => {
  extractedInfo.value = { ...originalExtractedInfo.value }
  editMode.value = false
}

// 显示重新处理对话框
const showReprocessDialog = () => {
  reprocessConfig.value = {
    extraction_fields: caseData.value.extraction_fields || [],
    custom_prompt: caseData.value.custom_prompt || ''
  }
  reprocessDialogVisible.value = true
}

// 确认重新处理
const confirmReprocess = async () => {
  reprocessing.value = true
  try {
    await pdfApi.reprocessCase(route.params.id, reprocessConfig.value)
    ElMessage.success('开始重新处理，请稍候...')
    reprocessDialogVisible.value = false
    loadCaseDetail() // 刷新数据
  } catch (error) {
    ElMessage.error('重新处理失败')
    console.error(error)
  } finally {
    reprocessing.value = false
  }
}

// 导出案例
const exportCase = async () => {
  try {
    const response = await pdfApi.exportCase(route.params.id)
    // 这里可以实现实际的Excel下载逻辑
    ElMessage.success('导出功能开发中...')
    console.log('导出数据:', response)
  } catch (error) {
    ElMessage.error('导出失败')
    console.error(error)
  }
}

// 获取状态类型
const getStatusType = (status) => {
  const statusMap = {
    'uploaded': 'info',
    'processing': 'warning',
    'ocr_processing': 'warning',
    'vlm_processing': 'warning',
    'llm_processing': 'warning',
    'completed': 'success',
    'failed': 'danger'
  }
  return statusMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const statusMap = {
    'uploaded': '已上传',
    'processing': '处理中',
    'ocr_processing': 'OCR识别中',
    'vlm_processing': 'VLM分析中',
    'llm_processing': 'LLM提取中',
    'completed': '已完成',
    'failed': '处理失败'
  }
  return statusMap[status] || status
}

// 获取处理进度
const getProcessingPercentage = (status) => {
  const progressMap = {
    'uploaded': 10,
    'processing': 20,
    'ocr_processing': 40,
    'vlm_processing': 60,
    'llm_processing': 80,
    'completed': 100,
    'failed': 0
  }
  return progressMap[status] || 0
}

// 获取处理消息
const getProcessingMessage = (status) => {
  const messageMap = {
    'uploaded': '文件已上传，等待处理...',
    'processing': '开始处理文件...',
    'ocr_processing': '正在进行OCR文字识别...',
    'vlm_processing': '正在进行VLM视觉分析...',
    'llm_processing': '正在使用LLM提取信息...',
    'completed': '处理完成！',
    'failed': '处理失败'
  }
  return messageMap[status] || '处理中...'
}

// 格式化日期
const formatDate = (dateString) => {
  return new Date(dateString).toLocaleString('zh-CN')
}

// 定时刷新处理中的案例
let refreshInterval = null

const startAutoRefresh = () => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  
  refreshInterval = setInterval(() => {
    if (caseData.value && 
        caseData.value.status !== 'completed' && 
        caseData.value.status !== 'failed') {
      loadCaseDetail()
    } else {
      clearInterval(refreshInterval)
    }
  }, 3000) // 每3秒刷新一次
}

watch(() => caseData.value?.status, (newStatus) => {
  if (newStatus === 'completed' || newStatus === 'failed') {
    if (refreshInterval) {
      clearInterval(refreshInterval)
    }
  }
})

onMounted(() => {
  loadCaseDetail()
  startAutoRefresh()
})

// 组件卸载时清理定时器
onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.case-detail {
  max-width: 1400px;
  margin: 0 auto;
}

.container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.back-button {
  align-self: flex-start;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  justify-content: space-between;
}

.actions {
  margin-top: 20px;
  text-align: center;
  display: flex;
  gap: 10px;
  justify-content: center;
}

.error-actions {
  margin-top: 15px;
  text-align: center;
}

.processing-card {
  text-align: center;
}

.processing-content {
  padding: 40px 20px;
}

.processing-icon {
  font-size: 48px;
  color: #409eff;
  margin-bottom: 20px;
  animation: spin 2s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.extracted-form {
  margin-top: 20px;
}

.field-group {
  margin-bottom: 20px;
}

.form-actions {
  margin-top: 30px;
  text-align: center;
  padding-top: 20px;
  border-top: 1px solid #e4e7ed;
}

.raw-text, .custom-prompt {
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.reprocess-content {
  max-height: 60vh;
  overflow-y: auto;
}

:deep(.el-descriptions__label) {
  font-weight: 600;
}

:deep(.el-form-item__label) {
  font-weight: 600;
}
</style> 