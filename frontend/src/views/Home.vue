<template>
  <div class="home">
    <div class="container">
      <!-- 上传区域 -->
      <el-card class="upload-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <el-icon><Upload /></el-icon>
            <span>上传PDF文件</span>
            <el-button 
              type="text" 
              @click="showAdvancedConfig = !showAdvancedConfig"
            >
              {{ showAdvancedConfig ? '隐藏高级配置' : '显示高级配置' }}
            </el-button>
          </div>
        </template>
        
        <!-- 高级配置区域 -->
        <div v-if="showAdvancedConfig" class="advanced-config">
          <ExtractionConfig v-model="extractionConfig" />
          <el-divider />
        </div>
        
        <el-upload
          ref="uploadRef"
          class="upload-dragger"
          drag
          :before-upload="beforeUpload"
          :on-success="onUploadSuccess"
          :on-error="onUploadError"
          :show-file-list="false"
          :http-request="customUpload"
          accept=".pdf"
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            将PDF文件拖拽到此处，或<em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              只能上传PDF文件，且不超过50MB
            </div>
          </template>
        </el-upload>
      </el-card>

      <!-- 案例列表 -->
      <el-card class="cases-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <el-icon><List /></el-icon>
            <span>证据材料列表</span>
            <el-button 
              type="primary" 
              size="small" 
              @click="loadCases"
              :loading="loading"
            >
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </template>

        <div v-if="loading" class="loading-container">
          <el-skeleton :rows="5" animated />
        </div>

        <div v-else-if="cases.length === 0" class="empty-container">
          <el-empty description="暂无证据材料数据">
            <el-button type="primary" @click="$refs.uploadRef.$el.click()">
              上传第一个PDF
            </el-button>
          </el-empty>
        </div>

        <el-table v-else :data="cases" style="width: 100%">
          <el-table-column prop="original_filename" label="文件名" min-width="200">
            <template #default="{ row }">
              <el-link 
                type="primary" 
                @click="viewCase(row.id)"
                :underline="false"
              >
                <el-icon><Document /></el-icon>
                {{ row.original_filename }}
              </el-link>
            </template>
          </el-table-column>
          
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column label="提取字段" width="120">
            <template #default="{ row }">
              <el-tag v-if="row.extraction_fields" type="info" size="small">
                自定义 ({{ row.extraction_fields.length }})
              </el-tag>
              <el-tag v-else type="success" size="small">
                默认配置
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="created_at" label="上传时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          
          <el-table-column prop="processed_at" label="处理完成时间" width="180">
            <template #default="{ row }">
              {{ row.processed_at ? formatDate(row.processed_at) : '-' }}
            </template>
          </el-table-column>
          
          <el-table-column label="操作" width="250" fixed="right">
            <template #default="{ row }">
              <el-button 
                type="primary" 
                size="small" 
                @click="viewCase(row.id)"
              >
                查看详情
              </el-button>
              <el-button 
                v-if="row.status === 'completed'"
                type="warning" 
                size="small" 
                @click="reprocessCase(row)"
              >
                重新处理
              </el-button>
              <el-button 
                type="danger" 
                size="small" 
                @click="deleteCase(row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, UploadFilled, List, Refresh, Document } from '@element-plus/icons-vue'
import { pdfApi } from '../api'
import ExtractionConfig from '../components/ExtractionConfig.vue'

const router = useRouter()
const uploadRef = ref()
const cases = ref([])
const loading = ref(false)
const showAdvancedConfig = ref(false)
const extractionConfig = ref({
  extraction_fields: [],
  custom_prompt: ''
})

// 重新处理相关
const reprocessDialogVisible = ref(false)
const reprocessConfig = ref({
  extraction_fields: [],
  custom_prompt: ''
})
const currentReprocessCase = ref(null)
const reprocessing = ref(false)

// 加载案例列表
const loadCases = async () => {
  loading.value = true
  try {
    const response = await pdfApi.getCases()
    cases.value = response
  } catch (error) {
    ElMessage.error('加载证据材料列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 上传前检查
const beforeUpload = (file) => {
  const isPDF = file.type === 'application/pdf'
  const isLt50M = file.size / 1024 / 1024 < 50

  if (!isPDF) {
    ElMessage.error('只能上传PDF文件!')
    return false
  }
  if (!isLt50M) {
    ElMessage.error('上传文件大小不能超过50MB!')
    return false
  }
  return true
}

// 自定义上传
const customUpload = async (options) => {
  try {
    let response
    
    // 检查是否有自定义配置
    const hasCustomConfig = extractionConfig.value.extraction_fields.length > 0 || 
                           extractionConfig.value.custom_prompt.trim() !== ''
    
    if (hasCustomConfig) {
      // 使用自定义配置上传
      response = await pdfApi.uploadPDFWithConfig(options.file, extractionConfig.value)
    } else {
      // 使用默认配置上传
      response = await pdfApi.uploadPDF(options.file)
    }
    
    options.onSuccess(response)
  } catch (error) {
    options.onError(error)
  }
}

// 上传成功
const onUploadSuccess = (response) => {
  ElMessage.success('文件上传成功，开始处理...')
  loadCases() // 刷新列表
  
  // 重置配置
  if (showAdvancedConfig.value) {
    extractionConfig.value = {
      extraction_fields: [],
      custom_prompt: ''
    }
  }
}

// 上传失败
const onUploadError = (error) => {
  ElMessage.error('文件上传失败')
  console.error(error)
}

// 查看案例详情
const viewCase = (caseId) => {
  router.push(`/case/${caseId}`)
}

// 重新处理案例
const reprocessCase = (caseItem) => {
  currentReprocessCase.value = caseItem
  
  // 初始化重新处理配置
  reprocessConfig.value = {
    extraction_fields: caseItem.extraction_fields || [],
    custom_prompt: caseItem.custom_prompt || ''
  }
  
  reprocessDialogVisible.value = true
}

// 确认重新处理
const confirmReprocess = async () => {
  if (!currentReprocessCase.value) return
  
  reprocessing.value = true
  try {
    await pdfApi.reprocessCase(currentReprocessCase.value.id, reprocessConfig.value)
    ElMessage.success('开始重新处理，请稍候...')
    reprocessDialogVisible.value = false
    loadCases() // 刷新列表
  } catch (error) {
    ElMessage.error('重新处理失败')
    console.error(error)
  } finally {
    reprocessing.value = false
  }
}

// 删除案例
const deleteCase = async (caseItem) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除证据材料 "${caseItem.original_filename}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    await pdfApi.deleteCase(caseItem.id)
    ElMessage.success('删除成功')
    loadCases()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
      console.error(error)
    }
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

// 格式化日期
const formatDate = (dateString) => {
  return new Date(dateString).toLocaleString('zh-CN')
}

onMounted(() => {
  loadCases()
})
</script>

<style scoped>
.home {
  max-width: 1400px;
  margin: 0 auto;
}

.container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.upload-card, .cases-card {
  border-radius: 8px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  justify-content: space-between;
}

.advanced-config {
  margin-bottom: 20px;
}

.upload-dragger {
  width: 100%;
}

.loading-container, .empty-container {
  padding: 40px 0;
}

.el-table {
  border-radius: 8px;
  overflow: hidden;
}

.reprocess-content {
  max-height: 60vh;
  overflow-y: auto;
}

:deep(.el-upload-dragger) {
  border-radius: 8px;
  border: 2px dashed #d9d9d9;
  transition: all 0.3s;
}

:deep(.el-upload-dragger:hover) {
  border-color: #409eff;
}
</style> 