<template>
  <div class="field-configuration-page">
    <el-card class="config-container-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <el-icon><Tools /></el-icon>
          <span>字段提取模板配置</span>
          <el-button type="primary" @click="goBack" icon="ArrowLeft">返回主工作台</el-button>
        </div>
      </template>
      
      <el-row :gutter="20">
        <!-- Editor Column -->
        <el-col :md="24" :lg="14">
          <el-card shadow="never" class="editor-card">
            <template #header>
              <div class="editor-header">
                <span class="editor-title">
                  <el-icon><Edit /></el-icon>
                  {{ editorTitle }}
                </span>
                <div class="editor-actions">
                  <el-button @click="saveAsNewTemplate" :disabled="!isConfigValid">
                    <el-icon><FolderAdd /></el-icon>
                    另存为新模板
                  </el-button>
                  <el-button type="primary" @click="updateSelectedTemplate" :disabled="!isDirty || !selectedTemplate">
                    <el-icon><Select /></el-icon>
                    保存更改
                </el-button>
            </div>
          </div>
            </template>

            <el-form label-position="top">
               <el-form-item label="模板名称">
                    <el-input v-model="activeConfig.name" :disabled="!selectedTemplate" placeholder="请从右侧选择一个模板进行编辑，或新建一个模板"/>
                </el-form-item>
                <el-form-item label="模板描述">
                    <el-input v-model="activeConfig.description" type="textarea" :rows="2" :disabled="!selectedTemplate" placeholder="模板的功能说明"/>
                </el-form-item>
            </el-form>

            <ExtractionConfig 
              ref="extractionConfigRef"
              :modelValue="activeConfig" 
              @update:modelValue="handleConfigUpdate"
                    />
          </el-card>
        </el-col>

        <!-- Template List Column -->
        <el-col :md="24" :lg="10">
          <el-card shadow="never" class="template-list-card">
            <template #header>
                <div class="template-list-header">
                    <span>
                      <el-icon><Files /></el-icon>
                      模板列表
                    </span>
                    <el-button type="success" @click="createNewTemplate" :icon="Plus">
                      新建空白模板
                    </el-button>
                </div>
            </template>
                <el-table 
                  :data="templates" 
              style="width: 100%" 
                  border 
              height="calc(100vh - 420px)"
                  @row-click="handleTemplateRowClick"
                  highlight-current-row
              :row-class-name="tableRowClassName"
                >
              <el-table-column prop="name" label="模板名称" min-width="150" sortable />
              <el-table-column label="默认" width="80" align="center">
                         <template #default="{ row }">
                  <el-tag v-if="row.is_default_bool" type="success" size="small" effect="dark">默认</el-tag>
                  <el-button v-else link type="primary" size="small" @click.stop="setDefaultTemplate(row)">设为默认</el-button>
                        </template>
                    </el-table-column>
              <el-table-column label="操作" width="80" align="center">
                        <template #default="{ row }">
                   <el-popconfirm
                      title="确定删除这个模板吗?"
                      confirm-button-text="确认"
                      cancel-button-text="取消"
                      @confirm="deleteTemplate(row)"
                    >
                      <template #reference>
                        <el-button size="small" type="danger" :icon="Delete" @click.stop />
                        </template>
                    </el-popconfirm>
                        </template>
                    </el-table-column>
                </el-table>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <!-- Save As New Template Dialog -->
    <el-dialog v-model="newTemplateDialogVisible" title="另存为新模板" width="40%">
      <el-form :model="newTemplateData" label-width="80px" ref="newTemplateFormRef" :rules="newTemplateRules">
        <el-form-item label="模板名称" prop="name">
          <el-input v-model="newTemplateData.name" placeholder="输入新模板名称"></el-input>
        </el-form-item>
        <el-form-item label="模板描述" prop="description">
          <el-input v-model="newTemplateData.description" type="textarea" :rows="3" placeholder="输入模板描述 (可选)"></el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="newTemplateDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmSaveAsNewTemplate">确认保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive, computed } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Tools, ArrowLeft, Select, FolderAdd, Edit, Delete, Plus, Files } from '@element-plus/icons-vue';
import { pdfApi } from '../api';
import ExtractionConfig from '../components/ExtractionConfig.vue';
import { cloneDeep, isEqual } from 'lodash-es';

const router = useRouter();
const extractionConfigRef = ref();

// State
const templates = ref([]);
const selectedTemplate = ref(null); // Stores the full template object when a row is clicked
const activeConfig = ref(createEmptyConfig()); // The config currently being edited

const isDirty = computed(() => {
  if (!selectedTemplate.value) {
    // If it's a new template, it's 'dirty' if it's not effectively empty
     return !isEqual(activeConfig.value, createEmptyConfig());
  }
  // Compare active config with the original selected template
  return !isEqual(activeConfig.value, selectedTemplate.value);
});

const isConfigValid = computed(() => {
    if (!activeConfig.value || !activeConfig.value.extraction_fields) return false;
    const hasMinOneField = activeConfig.value.extraction_fields.length > 0;
    const hasValidField = activeConfig.value.extraction_fields.some(f => f.key && f.label);
    return hasMinOneField && hasValidField;
});

const editorTitle = computed(() => {
  if (selectedTemplate.value) {
    return `正在编辑: ${selectedTemplate.value.name}`;
  }
  return '新建模板 (未保存)';
});

// New Template Dialog
const newTemplateDialogVisible = ref(false);
const newTemplateData = ref({ name: '', description: '' });
const newTemplateFormRef = ref();
const newTemplateRules = reactive({
    name: [{ required: true, message: '模板名称不能为空', trigger: 'blur' }]
});

// --- Helper Functions ---
function createEmptyConfig() {
    return {
        name: '',
        description: '',
        extraction_fields: [],
        custom_prompt: '',
        is_default: 'false',
        is_default_bool: false,
    };
}

async function createInitialTemplate() {
  try {
    const initialTemplate = {
      name: "默认模板",
      description: "这是一个默认的提取模板，您可以根据需要进行修改或创建新的模板。",
      extraction_fields: [
        { key: 'name', label: '姓名', type: 'text', required: true, placeholder: '请输入姓名' },
        { key: 'case_number', label: '案号', type: 'text', required: false, placeholder: '请输入案号' }
      ],
      custom_prompt: '',
        is_default: 'true'
      };
    await pdfApi.createTemplate(initialTemplate);
    ElMessage.success('已为您自动创建一个默认模板作为开始');
    // Reload templates after creation
    await loadTemplates(); 
  } catch (error) {
    ElMessage.error('自动创建初始模板失败，您可以手动创建一个。');
    console.error('Failed to create initial template:', error);
  }
}

// --- API Calls & Logic ---
async function loadTemplates() {
  try {
    const response = await pdfApi.getTemplates();
    templates.value = response.map(t => ({
        ...t,
        is_default_bool: t.is_default === 'true' || t.is_default === true
    }));
  } catch (error) {
    ElMessage.error('加载模板列表失败');
    console.error(error);
  }
}

async function loadDefaultTemplate() {
    let templateToLoad = templates.value.find(t => t.is_default_bool);

    if (!templateToLoad && templates.value.length > 0) {
        templateToLoad = templates.value[0];
  }
    
    if (templateToLoad) {
        selectTemplate(templateToLoad);
    } else {
        // This should now only be hit if the list is truly empty after all checks.
        createNewTemplate(true); 
    }
}

// --- Event Handlers ---
function handleConfigUpdate(newConfig) {
  // Check for actual changes before mutating to prevent recursive updates.
  const isFieldsEqual = isEqual(activeConfig.value.extraction_fields, newConfig.extraction_fields);
  const isPromptEqual = activeConfig.value.custom_prompt === newConfig.custom_prompt;

  if (!isFieldsEqual || !isPromptEqual) {
    activeConfig.value.extraction_fields = newConfig.extraction_fields;
    activeConfig.value.custom_prompt = newConfig.custom_prompt;
  }
}

async function handleTemplateRowClick(template) {
    if (isDirty.value) {
        try {
            await ElMessageBox.confirm(
                '当前有未保存的更改，切换模板将会丢失这些更改。确定要继续吗？',
                '警告',
                {
                    confirmButtonText: '确定切换',
                    cancelButtonText: '取消',
                    type: 'warning',
                }
            );
            selectTemplate(template);
        } catch (e) {
            ElMessage.info('已取消切换');
        }
    } else {
        selectTemplate(template);
  }
}

function selectTemplate(template) {
    selectedTemplate.value = cloneDeep(template);
    activeConfig.value = cloneDeep(template);
}

function createNewTemplate(force = false) {
    const doCreate = () => {
        selectedTemplate.value = null;
        activeConfig.value = createEmptyConfig();
    };

    if (isDirty.value && !force) {
         ElMessageBox.confirm(
            '当前有未保存的更改，新建模板将会丢失这些更改。确定要继续吗？',
            '警告',
            {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning',
            }
        ).then(() => {
            doCreate();
        }).catch(() => {
            ElMessage.info('已取消新建');
        });
    } else {
        doCreate();
    }
}

async function updateSelectedTemplate() {
    if (!isDirty.value || !selectedTemplate.value) return;
    try {
        const payload = { ...activeConfig.value };
        delete payload.is_default_bool;
        payload.is_default = selectedTemplate.value.is_default_bool ? 'true' : 'false';

        await pdfApi.updateTemplate(selectedTemplate.value.id, payload);
        ElMessage.success(`模板 "${selectedTemplate.value.name}" 已更新`);
        
        if (selectedTemplate.value.is_default_bool) {
            localStorage.setItem('default_template_updated', 'true');
        }

        const currentlySelectedId = selectedTemplate.value.id;
        await loadTemplates();
        
        const updatedTemplate = templates.value.find(t => t.id === currentlySelectedId);
        if(updatedTemplate) {
            selectTemplate(updatedTemplate);
        }

    } catch (error) {
        ElMessage.error('更新模板失败: ' + (error.response?.data?.detail || error.message));
        console.error(error);
    }
}

function saveAsNewTemplate() {
    if (!isConfigValid.value) {
        ElMessage.warning('请至少配置一个有效的字段（包含键名和标签）。');
        return;
    }
    newTemplateData.value.name = selectedTemplate.value ? `${activeConfig.value.name} (副本)`: '';
    newTemplateData.value.description = activeConfig.value.description || '';
    
    newTemplateDialogVisible.value = true;
}

async function confirmSaveAsNewTemplate() {
    if (!newTemplateFormRef.value) return;
    await newTemplateFormRef.value.validate();
    try {
        const templateData = {
            name: newTemplateData.value.name,
            description: newTemplateData.value.description,
            extraction_fields: activeConfig.value.extraction_fields,
            custom_prompt: activeConfig.value.custom_prompt,
            is_default: 'false'
        };
        const createdTemplate = await pdfApi.createTemplate(templateData);
        ElMessage.success(`模板 "${templateData.name}" 已创建`);
        newTemplateDialogVisible.value = false;
        await loadTemplates(); 
        
        const newTpl = templates.value.find(t => t.id === createdTemplate.id);
        if (newTpl) {
          selectTemplate(newTpl);
        }
        
    } catch (error) {
         ElMessage.error('保存新模板失败: ' + (error.response?.data?.detail || error.message));
         console.error(error);
            }
}

async function setDefaultTemplate(template) {
    try {
        const currentDefault = templates.value.find(t => t.is_default_bool && t.id !== template.id);
        if (currentDefault) {
             const payload = { ...currentDefault, is_default: 'false' };
             delete payload.is_default_bool;
             await pdfApi.updateTemplate(currentDefault.id, payload);
                }
        
        const newDefaultPayload = { ...template, is_default: 'true' };
        delete newDefaultPayload.is_default_bool;
        await pdfApi.updateTemplate(template.id, newDefaultPayload);

        ElMessage.success(`模板 "${template.name}" 已设为默认`);
        localStorage.setItem('default_template_updated', 'true');
        await loadTemplates(); 
    } catch (error) {
        ElMessage.error('设置默认模板失败: ' + (error.response?.data?.detail || error.message));
        await loadTemplates(); // re-sync state on error
    }
}

async function deleteTemplate(template) {
    try {
      await pdfApi.deleteTemplate(template.id);
        ElMessage.success(`模板 "${template.name}" 已删除`);
        
        const wasEditingDeleted = selectedTemplate.value && selectedTemplate.value.id === template.id;
        await loadTemplates();

        if (wasEditingDeleted || templates.value.length === 0) {
            loadDefaultTemplate();
      }

    } catch (error) {
        ElMessage.error('删除模板失败: ' + (error.response?.data?.detail || error.message));
    }
}

// --- UI ---
function tableRowClassName({ row }) {
    if (selectedTemplate.value && row.id === selectedTemplate.value.id) {
        return 'current-selection-row';
    }
    return '';
}

const goBack = () => router.push('/');

// --- Lifecycle ---
onMounted(async () => {
  await loadTemplates();
  if (templates.value.length === 0) {
    await createInitialTemplate();
  }
  await loadDefaultTemplate();
});
</script>

<style scoped>
.field-configuration-page {
  padding: 20px;
  max-width: 1600px;
  margin: 0 auto;
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
.card-header .el-button {
    margin-left: auto;
}

.editor-card, .template-list-card {
    height: calc(100vh - 220px);
    display: flex;
    flex-direction: column;
}

:deep(.editor-card .el-card__body), :deep(.template-list-card .el-card__body) {
    flex-grow: 1;
    overflow-y: auto;
    padding: 20px;
}
:deep(.template-list-card .el-card__body) {
    padding: 0;
}

.editor-header, .template-list-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
}

.editor-title, .template-list-header > span {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-weight: 600;
}

.editor-actions {
    display: flex;
    gap: 10px;
}

:deep(.el-table__row) {
  cursor: pointer;
}

:deep(.el-table .current-selection-row) {
  background-color: var(--el-color-primary-light-9) !important;
}

@media (max-width: 1200px) {
    .el-col-lg-10, .el-col-lg-14 {
        flex: 0 0 100%;
        max-width: 100%;
    }
    .template-list-card {
        margin-top: 20px;
    }
}
</style> 