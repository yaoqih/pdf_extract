<template>
  <div class="main-workspace">
    <!-- Upload Area -->
    <el-card class="upload-area" shadow="never">
      <div class="upload-controls">
        <div class="upload-section">
          <el-upload
            ref="uploadRef"
            drag
            action="#" 
            :multiple="true"
            :show-file-list="true"
            :before-upload="beforeUpload"
            :http-request="customUploadRequest"
            accept=".pdf"
            class="pdf-uploader"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              将PDF文件拖拽到此处，或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持多个PDF，单个文件不超过50MB
              </div>
            </template>
          </el-upload>
        </div>
      </div>
      <div class="progress-overview" v-if="cases.length > 0">
        <span>处理进度: {{ completedCasesCount }} / {{ cases.length }} 完成</span>
        <el-progress :percentage="completionPercentage" :stroke-width="8" striped />
      </div>
    </el-card>

    <!-- Workspace Area -->
    <div class="workspace-area">
      <!-- Left: PDF Task List -->
      <el-card class="task-list-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><List /></el-icon>
            <span>PDF任务列表</span>
            <div style="margin-left: auto; display: flex; gap: 8px;">
              <el-button 
                type="primary" 
                size="small" 
                @click="manualRefresh"
                :loading="loadingCases"
                icon="Refresh"
                circle
                title="刷新任务列表"
              />
              <el-button 
                type="danger"
                size="small" 
                @click="confirmClearAllCases"
                :loading="clearingAllCases"
                icon="Delete"
                circle
                title="清空所有案例数据"
              />
            </div>
          </div>
        </template>
        <el-scrollbar class="task-list-scrollbar">
          <div v-if="loadingCases" class="loading-container">
            <el-skeleton :rows="5" animated />
          </div>
          <el-empty v-else-if="cases.length === 0" description="暂无PDF任务">
             <el-button type="primary" @click="triggerUpload">上传第一个PDF</el-button>
          </el-empty>
          <el-menu v-else class="task-menu" :default-active="selectedCaseId" @select="handleCaseSelect">
            <el-menu-item v-for="item in cases" :key="item.id" :index="item.id">
              <el-icon><Document /></el-icon>
              <template #title>
                <div class="task-item-title">
                  <span class="filename" :title="item.original_filename">{{ item.original_filename }}</span>
                  <el-tag :type="getStatusType(item.status)" size="small" effect="light">{{ getStatusText(item.status) }}</el-tag>
                </div>
              </template>
            </el-menu-item>
          </el-menu>
        </el-scrollbar>
      </el-card>

      <!-- Center: PDF Preview -->
      <el-card class="pdf-preview-card" shadow="never">
        <template #header>
           <div class="card-header pdf-viewer-header">
              <el-icon><ViewIcon /></el-icon>
              <span>PDF预览 ({{ currentPdfPage }} / {{ totalPdfPages }})</span>
              <div class="viewer-controls">
                  <el-button @click="zoomIn" :icon="ZoomIn" circle size="small" :disabled="!selectedCasePdfUrl" />
                  <el-button @click="zoomOut" :icon="ZoomOut" circle size="small" :disabled="!selectedCasePdfUrl" />
                  <el-button @click="prevPage" :icon="ArrowLeft" circle size="small" :disabled="!selectedCasePdfUrl || currentPdfPage <= 1" />
                  <el-button @click="nextPage" :icon="ArrowRight" circle size="small" :disabled="!selectedCasePdfUrl || currentPdfPage >= totalPdfPages" />
              </div>
              <el-button v-if="selectedCase" type="danger" size="small" @click="confirmDeleteSelectedCase" icon="Delete" circle style="margin-left: auto;"/>
            </div>
        </template>
        <div class="pdf-viewer-container">
          <iframe 
            v-if="selectedCasePdfUrl" 
            :src="selectedCasePdfUrl" 
            class="pdf-iframe"
            @load="handlePdfLoaded"
          />
          <el-empty v-else description="请从左侧选择一个PDF文件进行预览" />
        </div>
      </el-card>

      <!-- Right: Information Extraction & Editing -->
      <el-card class="extraction-editor" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Edit /></el-icon>
            <span>提取信息编辑</span>
            <el-button 
              v-if="selectedCase && selectedCase.extracted_info && displayFields.length > 0" 
              type="primary" 
              size="small" 
              @click="saveChanges(false)"
              :loading="savingChanges"
              style="margin-left: auto;"
            >
              <el-icon><CircleCheckFilled /></el-icon>
              保存
            </el-button>
          </div>
        </template>
        <div class="editor-content">
          <div v-if="!selectedCase" class="empty-form">
            <el-empty description="请选择一个PDF进行编辑" />
          </div>
          <el-form 
              v-else-if="selectedCase && selectedCase.extracted_info"
              :model="editableExtractedInfo" 
              label-position="top"
              class="extracted-form"
              ref="editFormRef"
            >
              <el-scrollbar class="form-scrollbar" max-height="calc(100vh - 120px)">
                <div class="form-content">
                  <template v-if="displayFields.length > 0">
                    <el-form-item 
                      v-for="field in displayFields" 
                      :key="field.key" 
                      :label="field.label"
                      :prop="field.key"
                      :required="field.required"
                    >
                      <el-input 
                        v-if="!field.type || field.type === 'text'"
                        v-model="editableExtractedInfo[field.key]" 
                        :placeholder="field.placeholder || `请输入${field.label}`"
                        @blur="autoSave"
                      />
                      <el-input 
                        v-else-if="field.type === 'textarea'"
                        v-model="editableExtractedInfo[field.key]" 
                        type="textarea" 
                        :rows="3"
                        :placeholder="field.placeholder || `请输入${field.label}`"
                        @blur="autoSave"
                      />
                      <el-date-picker
                        v-else-if="field.type === 'date'"
                        v-model="editableExtractedInfo[field.key]"
                        type="date"
                        :placeholder="field.placeholder || `请选择${field.label}`"
                        format="YYYY-MM-DD"
                        value-format="YYYY-MM-DD"
                        style="width:100%;"
                        @change="autoSave"
                      />
                      <el-date-picker
                        v-else-if="field.type === 'datetime'"
                        v-model="editableExtractedInfo[field.key]"
                        type="datetime"
                        :placeholder="field.placeholder || `请选择${field.label}`"
                        format="YYYY-MM-DD HH:mm:ss"
                        value-format="YYYY-MM-DD HH:mm:ss"
                         style="width:100%;"
                         @change="autoSave"
                      />
                      <el-input-number
                        v-else-if="field.type === 'number'"
                        v-model="editableExtractedInfo[field.key]"
                        :placeholder="field.placeholder || `请输入${field.label}`"
                        style="width: 100%"
                        controls-position="right"
                        @blur="autoSave"
                      />
                    </el-form-item>
                  </template>
                  <el-alert
                    v-else-if="selectedCase.status === 'completed'"
                    title="未配置提取字段或使用旧版提取"
                    description="当前案例可能未关联字段配置，或使用了默认/旧版提取方式。您可以在【字段配置】页面定义标准字段，然后尝试重新处理此案例。"
                    type="info"
                    show-icon
                    :closable="false"
                    style="margin-bottom: 15px;"
                  />
                   <el-form-item label="原始提取JSON (只读)" v-if="selectedCase.status === 'completed' && Object.keys(selectedCase.extracted_info || {}).length > 0 && displayFields.length === 0">
                    <el-input 
                      :model-value="JSON.stringify(selectedCase.extracted_info, null, 2)"
                      type="textarea" 
                      :rows="10"
                      readonly
                    />
                  </el-form-item>
                  <el-empty v-if="selectedCase.status !== 'completed' && Object.keys(selectedCase.extracted_info || {}).length === 0" :description="`案例状态: ${getStatusText(selectedCase.status)}，暂无提取信息`" />
                </div>
              </el-scrollbar>
            </el-form>
            <div v-else-if="selectedCase && selectedCase.status !== 'completed'" class="processing-placeholder">
               <el-icon class="processing-icon is-loading"><Loading /></el-icon>
               <p>案例正在处理中 ({{ getStatusText(selectedCase.status) }})...</p>
               <p v-if="selectedCase.status === 'failed'">错误: {{ selectedCase.error_message }}</p>
               <el-button type="warning" @click="showReprocessDialog(selectedCase)" v-if="selectedCase.status === 'failed'">
                  <el-icon><Refresh /></el-icon>
                  配置并重新处理
               </el-button>
            </div>
        </div>
      </el-card>
    </div>

    <!-- Results Area: Aggregated Data Table -->
    <el-card class="results-area" shadow="never">
       <template #header>
          <div class="card-header">
            <el-icon><Grid /></el-icon>
            <span>汇总数据表格</span>
             <el-input
                v-model="globalSearch"
                placeholder="搜索表格内容..."
                clearable
                style="width: 200px; margin-left: auto; margin-right: 10px;"
                :prefix-icon="Search"
              />
            <el-button 
              type="success"
              :loading="exportingAll"
              @click="exportAllData"
              icon="Download"
            >
              导出到Excel
            </el-button>
          </div>
        </template>
      <el-table :data="filteredCasesForTable" style="width: 100%" height="300px" border>
        <el-table-column prop="original_filename" label="文件名" min-width="180" fixed sortable>
            <template #default="{ row }">
              <el-link type="primary" @click="handleCaseSelect(row.id)">{{ row.original_filename }}</el-link>
            </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120" sortable>
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
            </template>
        </el-table-column>
        
        <!-- Dynamically generate columns based on default/selected config -->
        <el-table-column 
          v-for="field in tableDisplayFields"
          :key="field.key"
          :prop="`extracted_info.${field.key}`"
          :label="field.label"
          min-width="150"
          sortable
        >
          <template #default="{ row }">
            <span>{{ getNestedValue(row, `extracted_info.${field.key}`) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="上传时间" width="160" sortable>
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="processed_at" label="处理完成时间" width="160" sortable>
          <template #default="{ row }">{{ row.processed_at ? formatDate(row.processed_at) : '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="handleCaseSelect(row.id)" icon="View" />
            <el-button 
              v-if="row.status === 'completed' || row.status === 'failed'"
              size="small" 
              type="warning"
              @click="showReprocessDialog(row)" 
              icon="Refresh"
            />
            <el-button size="small" type="danger" @click="confirmDeleteCase(row)" icon="Delete" />
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- Reprocess Dialog -->
    <el-dialog 
      v-model="reprocessDialogVisible" 
      title="配置并重新处理"
      width="60%"
      :close-on-click-modal="false"
    >
      <ExtractionConfig v-if="currentReprocessCase" v-model="reprocessConfig" :initial-case-config="currentReprocessCase" />
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
import { ref, onMounted, computed, watch, nextTick, watchEffect } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { 
  UploadFilled, Setting, Download, List, Document, Edit, Grid, View as ViewIcon, Refresh, Delete, Search, Loading, CircleCheckFilled, EditPen,
  ZoomIn, ZoomOut, ArrowLeft, ArrowRight
} from '@element-plus/icons-vue';
import { pdfApi } from '../api';
import ExtractionConfig from '../components/ExtractionConfig.vue';
import PageProcessingDetails from '../components/PageProcessingDetails.vue'; // Assuming this component is adapted

const router = useRouter();
const uploadRef = ref();

// Cases data
const cases = ref([]);
const loadingCases = ref(false);
const selectedCaseId = ref(null);
const selectedCase = computed(() => cases.value.find(c => c.id === selectedCaseId.value));
const selectedCasePdfUrl = computed(() => {
  if (selectedCase.value && selectedCase.value.file_path) {
    // Assuming backend serves files from 'uploads' at '/user_uploads/'
    const fileName = selectedCase.value.file_path.split(/[\\/]/).pop(); // OS-agnostic path splitting
    return `http://localhost:8000/user_uploads/${fileName}`;
  }
  return null;
});

// PDF Viewer State
const currentPdfPage = ref(1);
const totalPdfPages = ref(0);

// PDF Viewer Controls & Handlers (updated for iframe)
const handlePdfLoaded = () => {
  // For iframe, we can't easily get page count, so we'll use a simple approach
  totalPdfPages.value = 1; // Default to 1 for iframe
  currentPdfPage.value = 1;
};

const handlePdfLoadingFailed = (error) => {
  ElMessage.error('PDF加载失败，请检查文件或网络。');
  console.error('PDF loading failed:', error);
  totalPdfPages.value = 0;
  currentPdfPage.value = 1;
};

const zoomIn = () => {
  // For iframe, we can't control zoom directly
  ElMessage.info('iframe模式下暂不支持缩放控制');
};

const zoomOut = () => {
  // For iframe, we can't control zoom directly
  ElMessage.info('iframe模式下暂不支持缩放控制');
};

const prevPage = () => {
  // For iframe, we can't control page navigation directly
  ElMessage.info('iframe模式下暂不支持页面导航');
};

const nextPage = () => {
  // For iframe, we can't control page navigation directly
  ElMessage.info('iframe模式下暂不支持页面导航');
};

// Watcher to reset PDF viewer state when PDF source changes
watchEffect(() => {
  const currentCase = selectedCase.value; // Depend on selectedCase directly
  let newUrl = null;
  if (currentCase && currentCase.file_path) {
    const fileName = currentCase.file_path.split(/[\\/]/).pop(); // OS-agnostic path splitting
    newUrl = `http://localhost:8000/user_uploads/${fileName}`;
  }

  if (newUrl) {
    currentPdfPage.value = 1; // Reset to first page
    // totalPdfPages will be set by @load event from iframe
  } else {
    // Clear PDF state if no URL (e.g., no case selected or case has no PDF)
    currentPdfPage.value = 1;
    totalPdfPages.value = 0;
  }
});

// Upload
const beforeUpload = (file) => {
  const isPDF = file.type === 'application/pdf';
  const isLt50M = file.size / 1024 / 1024 < 50;
  if (!isPDF) ElMessage.error('只能上传PDF文件!');
  if (!isLt50M) ElMessage.error('上传文件大小不能超过50MB!');
  return isPDF && isLt50M;
};

// customUploadRequest (restoring previous version with progress and immediate list update)
const customUploadRequest = async (options) => {
  const { file, onProgress, onSuccess, onError } = options;

  const handleUploadProgress = (progressEvent) => {
    if (progressEvent.lengthComputable) {
      const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
      onProgress({ percent: percentCompleted });
    }
  };

  try {
    onProgress({ percent: 0 });
    const response = await pdfApi.uploadPDF(file, handleUploadProgress);
    onProgress({ percent: 100 });
    onSuccess(response);

    ElMessage.success(`${file.name} 上传成功，开始处理...`);
    if (response && response.id) {
      const newCase = {
        ...response,
        status: 'uploaded',
        created_at: new Date().toISOString(),
      };
      cases.value.unshift(newCase);
      selectedCaseId.value = response.id;
      nextTick(() => {
        editFormRef.value?.clearValidate();
      });
    }
  } catch (error) {
    onError(error);
    ElMessage.error(`${file.name} 上传失败.`);
    console.error(`Upload error for ${file.name}:`, error);
  }
};

const triggerUpload = () => {
  uploadRef.value?.$el.querySelector('input').click();
};

// Editing
const editableExtractedInfo = ref({});
const originalExtractedInfo = ref({});
const savingChanges = ref(false);
const editFormRef = ref();

// Auto-save functionality
let autoSaveTimer = null;
const autoSave = () => {
  if (!selectedCase.value || savingChanges.value) return;
  
  // Debounce auto-save to avoid too frequent API calls
  if (autoSaveTimer) clearTimeout(autoSaveTimer);
  autoSaveTimer = setTimeout(async () => {
    await saveChanges(true); // Pass true for silent mode (auto-save)
  }, 1000); // Save after 1 second of inactivity
};

// Display fields for editor and table
const defaultExtractionFields = ref([]); // To be fetched or defined
const displayFields = computed(() => {
  // 恢复正确逻辑：优先使用案例自身的字段配置
  if (selectedCase.value?.extraction_fields?.length > 0) {
    return selectedCase.value.extraction_fields;
  }
  // 回退到全局默认配置
  return defaultExtractionFields.value;
});

const tableDisplayFields = computed(() => {
  // The table should also always reflect the current default configuration for consistency.
  return defaultExtractionFields.value;
});


const loadDefaultConfig = async () => {
  try {
    const config = await pdfApi.getDefaultConfig();
    if (config && config.extraction_fields) {
      defaultExtractionFields.value = config.extraction_fields;

      // --- 关键修复：优化数据清理逻辑 ---
      // 仅当当前案例没有自己的字段配置（即依赖于默认模板）时，才进行数据清理
      const isCaseUsingDefault = !selectedCase.value || !selectedCase.value.extraction_fields || selectedCase.value.extraction_fields.length === 0;

      if (isCaseUsingDefault && editableExtractedInfo.value) {
        const newFieldKeys = new Set(config.extraction_fields.map(f => f.key));
        for (const key in editableExtractedInfo.value) {
          if (!newFieldKeys.has(key)) {
            delete editableExtractedInfo.value[key];
          }
        }
      }
    }
    ElMessage.success('已重新开始自动刷新，并同步了最新模板配置。');
  } catch (error) {
    console.error("Failed to load default extraction config:", error);
    // Fallback to a very basic set or leave empty
    defaultExtractionFields.value = [
        { key: "name", label: "姓名", type: "text" },
        { key: "id_number", label: "身份证号", type: "text" },
    ];
    ElMessage.warning('无法加载默认模板配置，已使用备用字段。');
  }
};

// Dynamic validation rules for the edit form
const editFormRules = computed(() => {
  const rules = {};
  if (selectedCase.value && displayFields.value.length > 0) {
    displayFields.value.forEach(field => {
      if (field.required) {
        rules[field.key] = [
          { required: true, message: `${field.label}不能为空`, trigger: 'blur' }
        ];
      }
    });
  }
  return rules;
});

watch(selectedCase, (newCase) => {
  if (newCase && newCase.extracted_info) {
    editableExtractedInfo.value = JSON.parse(JSON.stringify(newCase.extracted_info));
    originalExtractedInfo.value = JSON.parse(JSON.stringify(newCase.extracted_info));
  } else {
    editableExtractedInfo.value = {};
    originalExtractedInfo.value = {};
  }
  // Clear validation when case changes
  nextTick(() => {
    editFormRef.value?.clearValidate();
  });
}, { deep: true });

const saveChanges = async (isAutoSave = false) => {
  if (!selectedCase.value) return;
  
  if (editFormRef.value) {
      try {
          await editFormRef.value.validate();
      } catch (validationError) {
          if (!isAutoSave) ElMessage.error('表单验证失败，请检查输入项。');
          return; // Stop if validation fails
      }
  }

  savingChanges.value = true;
  try {
    await pdfApi.updateCase(selectedCase.value.id, {
      extracted_info: editableExtractedInfo.value
    });
    
    // 根据保存类型显示不同的提示
    if (isAutoSave) {
      // 自动保存时显示轻量提示
      ElMessage({
        message: '编辑已自动保存',
        type: 'success',
        duration: 2000,
        showClose: false,
        center: false
      });
    } else {
      // 手动保存时显示标准提示
      ElMessage.success('修改已保存');
    }
    
    const index = cases.value.findIndex(c => c.id === selectedCase.value.id);
    if (index !== -1) {
      cases.value[index].extracted_info = JSON.parse(JSON.stringify(editableExtractedInfo.value));
    }
  } catch (error) {
    if (!isAutoSave) {
      ElMessage.error('保存失败: ' + (error.message || '未知错误'));
      console.error("Save error:", error);
    }
  } finally {
    savingChanges.value = false;
  }
};

// Data Loading & Management
const loadCases = async () => {
  loadingCases.value = true;
  try {
    const response = await pdfApi.getCases();
    cases.value = response;
    if (!selectedCaseId.value && cases.value.length > 0) {
      // selectedCaseId.value = cases.value[0].id; // Auto-select first case
    } else if (selectedCaseId.value && !cases.value.find(c => c.id === selectedCaseId.value)) {
      selectedCaseId.value = null; // If selected case was deleted
    }
  } catch (error) {
    ElMessage.error('加载PDF任务列表失败');
    console.error(error);
  } finally {
    loadingCases.value = false;
  }
};

const handleCaseSelect = (caseId) => {
  selectedCaseId.value = caseId;
  // Any other actions on case selection, e.g., scroll to top of editor
};

// Reprocessing
const reprocessDialogVisible = ref(false);
const reprocessConfig = ref({}); // Will be { extraction_fields: [], custom_prompt: '' }
const currentReprocessCase = ref(null);
const reprocessing = ref(false);

const showReprocessDialog = (caseItem) => {
  currentReprocessCase.value = caseItem;
  reprocessConfig.value = {
    extraction_fields: caseItem.extraction_fields || defaultExtractionFields.value || [],
    custom_prompt: caseItem.custom_prompt || ''
  };
  reprocessDialogVisible.value = true;
};

const confirmReprocess = async () => {
  if (!currentReprocessCase.value) return;
  reprocessing.value = true;
  try {
    await pdfApi.reprocessCase(currentReprocessCase.value.id, reprocessConfig.value);
    ElMessage.success('已提交重新处理任务，请稍后刷新列表查看状态。');
    reprocessDialogVisible.value = false;
    // Optimistically update status or wait for polling/refresh
    const caseInList = cases.value.find(c => c.id === currentReprocessCase.value.id);
    if(caseInList) caseInList.status = 'processing'; 
    
    // If the reprocessed case is the selected one, clear its extracted info for UI update
    if (selectedCaseId.value === currentReprocessCase.value.id) {
        if (selectedCase.value) {
            selectedCase.value.extracted_info = {}; // Clear old info
            selectedCase.value.status = 'processing';
        }
    }
    // loadCases(); // Or use a more targeted update/polling
  } catch (error) {
    ElMessage.error('重新处理失败: ' + (error.message || '未知错误'));
  } finally {
    reprocessing.value = false;
  }
};

// Deletion
const confirmDeleteCase = (caseItem) => {
  ElMessageBox.confirm(
    `确定要删除PDF "${caseItem.original_filename}" 及其所有数据吗？此操作不可撤销。`,
    '确认删除',
    {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(async () => {
    try {
      await pdfApi.deleteCase(caseItem.id);
      ElMessage.success('删除成功');
      if (selectedCaseId.value === caseItem.id) {
        selectedCaseId.value = null; // Deselect if current
      }
      loadCases(); // Refresh list
    } catch (error) {
      ElMessage.error('删除失败: ' + (error.message || '未知错误'));
    }
  }).catch(() => { /* User cancelled */ });
};

const confirmDeleteSelectedCase = () => {
    if (selectedCase.value) {
        confirmDeleteCase(selectedCase.value);
    }
}

// Navigation
const navigateToConfig = () => {
  router.push('/config');
};

// Export All
const exportingAll = ref(false);
const exportAllData = async () => {
  exportingAll.value = true;
  try {
    const response = await pdfApi.exportAllCasesExcel();
    const contentDisposition = response.headers['content-disposition'];
    let filename = "pdf_extracted_data.xlsx";
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename[^;=\\n]*=((['"])(.*?)\\2|[^;\\n]*)/i);
      if (filenameMatch && filenameMatch[3]) {
        filename = filenameMatch[3];
      }
    }

    const blob = new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
    ElMessage.success('数据已成功导出到Excel');

  } catch (error) {
    if (error.response && error.response.status === 404) {
      ElMessage.warning('没有已完成的案例可供导出。');
    } else {
      ElMessage.error('导出Excel失败: ' + (error.message || '未知错误'));
      console.error("Excel export error:", error);
    }
  } finally {
    exportingAll.value = false;
  }
};

// 一键清空
const clearingAllCases = ref(false);
const confirmClearAllCases = () => {
  ElMessageBox.confirm(
    '此操作将永久删除所有PDF案例及其相关数据，包括已上传的文件和数据库记录。此操作不可撤销，确定要继续吗？',
    '警告：清空所有数据',
    {
      confirmButtonText: '确定清空',
      cancelButtonText: '取消',
      type: 'error',
      draggable: true,
    }
  ).then(async () => {
    clearingAllCases.value = true;
    try {
      const response = await pdfApi.clearAllCases();
      ElMessage.success(response.message || '所有案例数据已成功清空');
      await loadCases(); 
      selectedCaseId.value = null; 
      editableExtractedInfo.value = {}; 
    } catch (error) {
      ElMessage.error('清空数据失败: ' + (error.message || '未知错误'));
      console.error("Clear all cases error:", error);
    }
    finally {
      clearingAllCases.value = false;
    }
  }).catch(() => {
    ElMessage.info('已取消清空操作');
  });
};

// UI Helpers
const getStatusType = (status) => {
  const map = { 'uploaded': 'info', 'processing': 'primary', 'ocr_processing': 'warning', 'vlm_processing': 'warning', 'llm_processing': 'warning', 'completed': 'success', 'failed': 'danger' };
  return map[status] || 'info';
};
const getStatusText = (status) => {
  const map = { 'uploaded': '待处理', 'processing': '处理中', 'ocr_processing': 'OCR识别', 'vlm_processing': 'VLM分析', 'llm_processing': 'LLM提取', 'completed': '已完成', 'failed': '失败' };
  return map[status] || status;
};
const formatDate = (dateString) => dateString ? new Date(dateString).toLocaleString('zh-CN') : '-';

const getNestedValue = (obj, path) => {
  if (!obj || !path) return '-';
  return path.split('.').reduce((acc, part) => acc && acc[part], obj) || '-';
};

// Progress Overview
const completedCasesCount = computed(() => cases.value.filter(c => c.status === 'completed').length);
const completionPercentage = computed(() => cases.value.length > 0 ? Math.round((completedCasesCount.value / cases.value.length) * 100) : 0);

// Aggregated Table Search
const globalSearch = ref('');
const filteredCasesForTable = computed(() => {
  if (!globalSearch.value) {
    return cases.value.filter(c => c.status === 'completed' && c.extracted_info); // Only show completed with info for table
  }
  const searchTerm = globalSearch.value.toLowerCase();
  return cases.value.filter(c => {
    if (c.status !== 'completed' || !c.extracted_info) return false;
    // Search filename
    if (c.original_filename.toLowerCase().includes(searchTerm)) return true;
    // Search extracted info values
    for (const field of tableDisplayFields.value) {
      const val = getNestedValue(c, `extracted_info.${field.key}`);
      if (String(val).toLowerCase().includes(searchTerm)) return true;
    }
    return false;
  });
});


// Lifecycle and Polling
let pollingInterval = null;
let pollingFailureCount = 0; 
const MAX_POLLING_FAILURES = 3; 

const startPolling = () => {
  pollingInterval = setInterval(async () => {
    const processingOrUploadedCases = cases.value.filter(
      c => ['uploaded', 'processing', 'ocr_processing', 'vlm_processing', 'llm_processing'].includes(c.status)
    );
    
    if (processingOrUploadedCases.length > 0) {
      try {
        const response = await pdfApi.getCases();
        response.forEach(serverCase => {
          const localCaseIndex = cases.value.findIndex(c => c.id === serverCase.id);
          if (localCaseIndex !== -1) {
            const localCase = cases.value[localCaseIndex];
            if (localCase.status !== serverCase.status || 
                localCase.processed_at !== serverCase.processed_at ||
                JSON.stringify(localCase.extracted_info) !== JSON.stringify(serverCase.extracted_info)) {
              cases.value[localCaseIndex] = { ...serverCase };
              if (serverCase.status === 'completed' && localCase.status !== 'completed') {
                ElMessage.success(`${serverCase.original_filename} 处理完成`);
              } else if (serverCase.status === 'failed' && localCase.status !== 'failed') {
                ElMessage.error(`${serverCase.original_filename} 处理失败`);
              }
            }
          } else {
            cases.value.push(serverCase);
          }
        });
        cases.value = cases.value.filter(localCase => 
          response.some(serverCase => serverCase.id === localCase.id)
        );
        pollingFailureCount = 0; 
      } catch (error) {
        pollingFailureCount++;
        console.warn(`轮询失败 ${pollingFailureCount}/${MAX_POLLING_FAILURES}:`, error);
        if (pollingFailureCount >= MAX_POLLING_FAILURES) {
          console.error('轮询连续失败，暂停轮询');
          stopPolling();
          ElMessage.warning('网络连接不稳定，已暂停自动刷新。您可以手动刷新页面。');
        }
      }
    }
  }, 5000); 
};

const stopPolling = () => {
  if (pollingInterval) {
    clearInterval(pollingInterval);
    pollingInterval = null;
  }
};

const manualRefresh = async () => {
  await loadDefaultConfig(); // 同步模板
  await loadCases();
  if (!pollingInterval) {
    pollingFailureCount = 0;
    startPolling();
    ElMessage.success('已重新开始自动刷新，并同步了最新模板配置。');
  } else {
    ElMessage.success('列表和表格列已刷新为最新配置。');
  }
};

const handleVisibilityChange = () => {
  if (document.visibilityState === 'visible') {
    manualRefresh();
  }
};

onMounted(async () => {
  if (localStorage.getItem('default_template_updated') === 'true') {
    localStorage.removeItem('default_template_updated');
    await manualRefresh();
  } else {
    await loadDefaultConfig(); // Load default fields first
    await loadCases();
  }
  startPolling();
  if (cases.value.length > 0 && !selectedCaseId.value) {
    // Optionally auto-select first case on load
    selectedCaseId.value = cases.value[0].id;
  }
  document.addEventListener('visibilitychange', handleVisibilityChange);
});

import { onBeforeUnmount } from 'vue';
onBeforeUnmount(() => {
  stopPolling();
  document.removeEventListener('visibilitychange', handleVisibilityChange);
});

</script>

<style scoped>
.main-workspace {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 10px;
  background-color: #f0f2f5;
  min-height: 100vh; /* Allow scrolling, but minimum full height */
}

.upload-area {
  flex-shrink: 0;
}

.upload-controls {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
}
.upload-section {
  flex-grow: 1;
}
.pdf-uploader {
  width:100%;
}
:deep(.pdf-uploader .el-upload-dragger) {
  padding: 10px;
  height: auto;
  min-height: 80px;
}
:deep(.pdf-uploader .el-icon--upload) {
  font-size: 30px;
  margin-bottom: 5px;
}
:deep(.pdf-uploader .el-upload__text) {
  font-size: 13px;
}
:deep(.pdf-uploader .el-upload__tip) {
  font-size: 12px;
  margin-top: 5px;
}

.upload-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}
.progress-overview {
  margin-top: 10px;
  font-size: 13px;
}
.progress-overview .el-progress {
  margin-top: 5px;
}

.workspace-area {
  display: flex;
  gap: 10px;
  height: calc(100vh - 40px); /* Full screen height minus padding */
  min-height: 600px; /* Minimum height for usability */
}

.task-list-card {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}
.task-list-card .el-card__body {
  padding: 0;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  min-height: 0; /* Crucial for nested flex/scroll */
}
.task-list-scrollbar {
  flex-grow: 1;
}
.task-menu {
  border-right: none;
  flex-grow:1;
}
.task-item-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}
.task-item-title .filename {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-right: 8px;
  flex-grow: 1;
}

.pdf-preview-card {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0; /* Crucial for nested flex/scroll */
}
.pdf-preview-card .el-card__body {
  flex-grow:1;
  padding: 5px;
  display: flex; 
  flex-direction: column;
  min-height: 0; /* Crucial for nested flex/scroll */
}
.pdf-viewer-container {
  flex-grow: 1; 
  display: flex;
  flex-direction: column;
  min-height: 90vh; 
}
.pdf-iframe {
  width: 100%;
  border: none;
  flex-grow: 1;
}

.extraction-editor {
  width: 350px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  min-height: 0; /* Crucial for nested flex/scroll */
}
.extraction-editor .el-card__body {
  flex-grow: 1;
  padding: 15px;
  display: flex; 
  flex-direction: column;
  min-height: 0; /* Crucial for nested flex/scroll */
}
.editor-content {
  flex-grow: 1; 
  display: flex;
  flex-direction: column;
  min-height: 90vh; 
}
.extracted-form {
  flex-grow: 1; 
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.form-scrollbar {
  flex-grow: 1;
  min-height: 0; /* Allow scrollbar to shrink if form is small */
}
.form-content {
  padding: 5px;
}
.empty-form, .processing-placeholder {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: #909399;
}
.processing-icon {
    font-size: 24px;
    margin-bottom: 10px;
}

/* 优化滚动条样式 */
:deep(.form-scrollbar .el-scrollbar__bar) {
  background-color: rgba(144, 147, 153, 0.3);
  border-radius: 4px;
}
:deep(.form-scrollbar .el-scrollbar__thumb) {
  background-color: rgba(144, 147, 153, 0.6);
  border-radius: 4px;
}
:deep(.form-scrollbar .el-scrollbar__thumb:hover) {
  background-color: rgba(144, 147, 153, 0.8);
}

.results-area {
  flex-shrink: 0;
  margin-top: 10px; /* Add some space from workspace */
}
.results-area .el-card__body {
  padding:10px;
}

.card-header {
  display: flex;
  align-items: center;
  font-weight: 600;
  gap: 8px;
}
.card-header .el-icon {
  font-size: 16px;
}

.loading-container, .empty-container {
  padding: 20px;
  text-align: center;
}

/* Common card styles */
.el-card {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
}
.el-card.shadow-never {
    box-shadow: none;
}

:deep(.el-menu-item) {
  height: 40px;
  line-height: 40px;
  font-size: 13px;
}
:deep(.el-menu-item .el-icon) {
  margin-right: 5px;
}
:deep(.el-menu-item.is-active) {
  background-color: #ecf5ff;
}

</style> 