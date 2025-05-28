<template>
  <div class="page-processing-details">
    <div class="header">
      <h3>逐页处理结果</h3>
      <div class="stats">
        <el-tag type="info">总页数: {{ pdfInfo.total_pages || 0 }}</el-tag>
        <el-tag type="success">OCR成功: {{ ocrStats.successful_pages || 0 }}/{{ ocrStats.total_pages || 0 }}</el-tag>
        <el-tag type="warning">VLM成功: {{ vlmStats.successful_pages || 0 }}/{{ vlmStats.total_pages || 0 }}</el-tag>
      </div>
    </div>

    <div class="content">
      <!-- 页面列表 -->
      <div class="page-list">
        <h4>页面列表</h4>
        <div class="page-grid">
          <div 
            v-for="pageNum in totalPages" 
            :key="pageNum"
            class="page-item"
            :class="{ 
              'active': selectedPage === pageNum,
              'has-ocr': hasOcrResult(pageNum),
              'has-vlm': hasVlmResult(pageNum),
              'has-error': hasError(pageNum)
            }"
            @click="selectPage(pageNum)"
          >
            <div class="page-number">第{{ pageNum }}页</div>
            <div class="page-status">
              <el-icon v-if="hasOcrResult(pageNum)" class="success-icon"><Check /></el-icon>
              <el-icon v-if="hasVlmResult(pageNum)" class="vlm-icon"><View /></el-icon>
              <el-icon v-if="hasError(pageNum)" class="error-icon"><Warning /></el-icon>
            </div>
          </div>
        </div>
      </div>

      <!-- 页面详情 -->
      <div class="page-detail" v-if="selectedPage">
        <div class="detail-header">
          <h4>第{{ selectedPage }}页详情</h4>

        </div>

        <el-tabs v-model="activeTab" class="detail-tabs">
          <!-- OCR结果 -->
          <el-tab-pane label="OCR识别结果" name="ocr">
            <div v-if="currentPageDetail?.ocr_result" class="result-content">
              <div class="result-meta">
                <el-tag :type="currentPageDetail.ocr_result.success ? 'success' : 'danger'">
                  {{ currentPageDetail.ocr_result.success ? '成功' : '失败' }}
                </el-tag>
                <el-tag type="info">方法: {{ currentPageDetail.ocr_result.method }}</el-tag>
                <el-tag type="info">文本长度: {{ currentPageDetail.ocr_result.text_length }}</el-tag>
              </div>
              
              <div v-if="currentPageDetail.ocr_result.error" class="error-message">
                <el-alert 
                  :title="currentPageDetail.ocr_result.error" 
                  type="error" 
                  show-icon 
                  :closable="false"
                />
              </div>
              
              <div class="text-content">
                <h5>识别文本:</h5>
                <el-input
                  v-model="currentPageDetail.ocr_result.text"
                  type="textarea"
                  :rows="10"
                  readonly
                  placeholder="无识别结果"
                />
              </div>
            </div>
            <div v-else class="no-result">
              <el-empty description="暂无OCR结果" />
            </div>
          </el-tab-pane>

          <!-- VLM结果 -->
          <el-tab-pane label="VLM分析结果" name="vlm">
            <div v-if="currentPageDetail?.vlm_result" class="result-content">
              <div class="result-meta">
                <el-tag :type="currentPageDetail.vlm_result.success ? 'success' : 'danger'">
                  {{ currentPageDetail.vlm_result.success ? '成功' : '失败' }}
                </el-tag>
                <el-tag type="info">方法: {{ currentPageDetail.vlm_result.method }}</el-tag>
                <el-tag type="info">文本长度: {{ currentPageDetail.vlm_result.text_length }}</el-tag>
              </div>
              
              <div v-if="currentPageDetail.vlm_result.error" class="error-message">
                <el-alert 
                  :title="currentPageDetail.vlm_result.error" 
                  type="error" 
                  show-icon 
                  :closable="false"
                />
              </div>
              
              <div class="text-content">
                <h5>分析结果:</h5>
                <el-input
                  v-model="currentPageDetail.vlm_result.text"
                  type="textarea"
                  :rows="10"
                  readonly
                  placeholder="无分析结果"
                />
              </div>
            </div>
            <div v-else class="no-result">
              <el-empty description="暂无VLM结果" />
            </div>
          </el-tab-pane>

          <!-- 对比视图 -->
          <el-tab-pane label="对比视图" name="compare">
            <div class="compare-view">
              <div class="compare-column">
                <h5>OCR识别结果</h5>
                <el-input
                  :value="currentPageDetail?.ocr_result?.text || ''"
                  type="textarea"
                  :rows="15"
                  readonly
                  placeholder="无OCR结果"
                />
              </div>
              <div class="compare-column">
                <h5>VLM分析结果</h5>
                <el-input
                  :value="currentPageDetail?.vlm_result?.text || ''"
                  type="textarea"
                  :rows="15"
                  readonly
                  placeholder="无VLM结果"
                />
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, View, Warning } from '@element-plus/icons-vue'
import api from '../api'

interface Props {
  caseId: string
}

interface PageData {
  pdf_info: {
    total_pages: number
  }
  ocr_pages: Array<{
    page_num: number
    success: boolean
    text: string
    method: string
    text_length: number
    error?: string
  }>
  vlm_pages: Array<{
    page_num: number
    success: boolean
    text: string
    method: string
    text_length: number
    error?: string
  }>
  ocr_stats: {
    total_pages: number
    successful_pages: number
  }
  vlm_stats: {
    total_pages: number
    successful_pages: number
  }
}

interface PageDetail {
  case_id: string
  page_num: number
  ocr_result?: {
    success: boolean
    text: string
    method: string
    text_length: number
    error?: string
  }
  vlm_result?: {
    success: boolean
    text: string
    method: string
    text_length: number
    error?: string
  }
}

const props = defineProps<Props>()

// 响应式数据
const pagesData = ref<PageData | null>(null)
const selectedPage = ref<number>(1)
const currentPageDetail = ref<PageDetail | null>(null)
const activeTab = ref<string>('ocr')
const isLoading = ref<boolean>(false)

// 计算属性
const pdfInfo = computed(() => pagesData.value?.pdf_info || {})
const ocrPages = computed(() => pagesData.value?.ocr_pages || [])
const vlmPages = computed(() => pagesData.value?.vlm_pages || [])
const ocrStats = computed(() => pagesData.value?.ocr_stats || {})
const vlmStats = computed(() => pagesData.value?.vlm_stats || {})
const totalPages = computed(() => pdfInfo.value.total_pages || 0)

// 方法
function hasOcrResult(pageNum: number): boolean {
  return ocrPages.value.some(p => p.page_num === pageNum && p.success)
}

function hasVlmResult(pageNum: number): boolean {
  return vlmPages.value.some(p => p.page_num === pageNum && p.success)
}

function hasError(pageNum: number): boolean {
  const ocrPage = ocrPages.value.find(p => p.page_num === pageNum)
  const vlmPage = vlmPages.value.find(p => p.page_num === pageNum)
  return (ocrPage && !ocrPage.success) || (vlmPage && !vlmPage.success)
}

function selectPage(pageNum: number): void {
  selectedPage.value = pageNum
  loadPageDetail(pageNum)
}

async function loadPagesData(): Promise<void> {
  if (isLoading.value) return
  
  isLoading.value = true
  try {
    const response = await api.get(`/cases/${props.caseId}/pages`)
    pagesData.value = response.data
    
    // 默认选择第一页
    if (totalPages.value > 0) {
      selectPage(1)
    }
  } catch (error) {
    console.error('加载页面数据失败:', error)
    ElMessage.error('加载页面数据失败')
  } finally {
    isLoading.value = false
  }
}

async function loadPageDetail(pageNum: number): Promise<void> {
  try {
    const response = await api.get(`/cases/${props.caseId}/pages/${pageNum}`)
    currentPageDetail.value = response.data
  } catch (error) {
    console.error('加载页面详情失败:', error)
    currentPageDetail.value = null
  }
}



// 监听caseId变化
watch(() => props.caseId, (newCaseId) => {
  if (newCaseId) {
    loadPagesData()
  }
}, { immediate: true })

onMounted(() => {
  if (props.caseId) {
    loadPagesData()
  }
})
</script>

<style scoped>
.page-processing-details {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #ebeef5;
}

.header h3 {
  margin: 0;
  color: #303133;
}

.stats {
  display: flex;
  gap: 10px;
}

.content {
  display: flex;
  gap: 20px;
  height: 600px;
}

.page-list {
  width: 300px;
  border-right: 1px solid #ebeef5;
  padding-right: 20px;
}

.page-list h4 {
  margin: 0 0 15px 0;
  color: #606266;
}

.page-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  max-height: 550px;
  overflow-y: auto;
}

.page-item {
  border: 2px solid #dcdfe6;
  border-radius: 8px;
  padding: 10px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  background: #fff;
}

.page-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
}

.page-item.active {
  border-color: #409eff;
  background: #ecf5ff;
}

.page-item.has-ocr {
  border-left: 4px solid #67c23a;
}

.page-item.has-vlm {
  border-right: 4px solid #e6a23c;
}

.page-item.has-error {
  border-color: #f56c6c;
  background: #fef0f0;
}

.page-number {
  font-size: 12px;
  font-weight: bold;
  margin-bottom: 5px;
}

.page-status {
  display: flex;
  justify-content: center;
  gap: 5px;
}

.success-icon {
  color: #67c23a;
}

.vlm-icon {
  color: #e6a23c;
}

.error-icon {
  color: #f56c6c;
}

.page-detail {
  flex: 1;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.detail-header h4 {
  margin: 0;
  color: #303133;
}



.detail-tabs {
  height: 500px;
}

.result-content {
  height: 450px;
  overflow-y: auto;
}

.result-meta {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

.error-message {
  margin-bottom: 15px;
}

.text-content h5 {
  margin: 0 0 10px 0;
  color: #606266;
}

.no-result {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 400px;
}

.compare-view {
  display: flex;
  gap: 20px;
  height: 450px;
}

.compare-column {
  flex: 1;
}

.compare-column h5 {
  margin: 0 0 10px 0;
  color: #606266;
}
</style> 