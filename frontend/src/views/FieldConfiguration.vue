<template>
  <div class="field-configuration-page">
    <el-card class="config-container-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <el-icon><Tools /></el-icon>
          <span>全局字段配置与模板管理</span>
          <el-button type="primary" @click="goBack" icon="ArrowLeft">返回主工作台</el-button>
        </div>
      </template>
      
      <el-tabs v-model="activeTab">
        <el-tab-pane label="默认提取字段" name="defaultConfig">
          <div class="config-section">
            <p class="section-description">
              此处配置的字段将作为新上传PDF时的默认提取目标。您也可以在下方管理和创建模板，并在上传或重新处理时选用特定模板。
            </p>
            <ExtractionConfig 
              ref="defaultConfigRef"
              :modelValue="currentDefaultConfig" 
              @update:modelValue="handleDefaultConfigUpdate"
              :is-global-default-config="true"
            />
            <div class="actions-bar">
                <el-button type="primary" @click="saveDefaultConfig" :loading="savingDefaultConfig">
                    <el-icon><Select /></el-icon>
                    保存默认配置
                </el-button>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="提取模板管理" name="templates">
           <div class="config-section">
            <p class="section-description">
              管理您的提取模板。模板可以包含一组预定义的字段和自定义提示词，方便快速应用于不同类型的案件材料。
            </p>
            <div class="template-management">
                <div class="template-actions">
                    <el-input 
                        v-model="newTemplateName"
                        placeholder="输入新模板名称..."
                        style="width: 250px; margin-right: 10px;"
                    />
                    <el-button type="success" @click="saveCurrentAsNewTemplate" :loading="savingNewTemplate" :disabled="!newTemplateName">
                        <el-icon><FolderAdd /></el-icon>
                        将当前默认配置存为新模板
                    </el-button>
                </div>

                <el-table 
                  :data="templates" 
                  style="width: 100%; margin-top:20px;" 
                  border 
                  height="calc(100vh - 450px)"
                  @row-click="handleTemplateRowClick"
                  highlight-current-row
                >
                    <el-table-column prop="name" label="模板名称" width="200" sortable />
                    <el-table-column prop="description" label="描述" min-width="250">
                         <template #default="{ row }">
                            <el-input 
                              v-if="editingTemplate && editingTemplate.id === row.id" 
                              v-model="editingTemplate.description" 
                              type="textarea" 
                              :rows="1" 
                              @blur="handleDescriptionBlur(row)"
                            />
                            <span v-else>{{ row.description || '-' }}</span>
                        </template>
                    </el-table-column>
                    <el-table-column label="字段数" width="100" align="center">
                        <template #default="{ row }">
                        {{ row.extraction_fields ? row.extraction_fields.length : 0 }}
                        </template>
                    </el-table-column>
                    <el-table-column label="自定义提示词" width="120" align="center">
                        <template #default="{ row }">
                        <el-tag :type="row.custom_prompt ? 'success' : 'info'" size="small">
                            {{ row.custom_prompt ? '已设置' : '未设置' }}
                        </el-tag>
                        </template>
                    </el-table-column>
                     <el-table-column label="默认模板" width="100" align="center">
                        <template #default="{ row }">
                            <el-switch 
                                v-model="row.is_default_bool"
                                @change="(value) => handleSetDefaultTemplate(row, value)"
                                :loading="updatingDefaultStatus[row.id]"
                            />
                        </template>
                    </el-table-column>
                    <el-table-column prop="created_at" label="创建时间" width="160" sortable>
                        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
                    </el-table-column>
                    <el-table-column label="操作" width="150" fixed="right" align="center"> <template #default="{ row }">
                             <el-button size="small" @click.stop="startEditTemplate(row)" :icon="Edit" type="primary" plain>编辑描述</el-button>
                             <el-button size="small" type="danger" @click.stop="deleteTemplate(row)" :icon="Delete" />
                        </template>
                    </el-table-column>
                </el-table>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Tools, ArrowLeft, Select, FolderAdd, Edit, Delete } from '@element-plus/icons-vue';
import { pdfApi } from '../api';
import ExtractionConfig from '../components/ExtractionConfig.vue';

const router = useRouter();
const activeTab = ref('defaultConfig');
const defaultConfigRef = ref();

const currentDefaultConfig = ref({
  extraction_fields: [],
  custom_prompt: ''
});
const savingDefaultConfig = ref(false);

const templates = ref([]);
const newTemplateName = ref('');
const savingNewTemplate = ref(false);
const editingTemplate = ref(null);
const originalDescriptionBeforeEdit = ref('');
const debouncedSaveTimeout = ref(null);
const updatingDefaultStatus = reactive({});

const loadCurrentDefaultConfig = async () => {
  try {
    const response = await pdfApi.getDefaultConfig(); 
    currentDefaultConfig.value = {
      extraction_fields: response.extraction_fields || [],
      custom_prompt: response.custom_prompt || ''
    };
  } catch (error) {
    ElMessage.error('加载当前默认配置失败');
    console.error(error);
    currentDefaultConfig.value = { extraction_fields: [], custom_prompt: '' };
  }
};

const handleDefaultConfigUpdate = (newConfig) => {
  currentDefaultConfig.value = newConfig;
};

const saveDefaultConfig = async () => {
  savingDefaultConfig.value = true;
  try {
    const dataToSave = {
        extraction_fields: currentDefaultConfig.value.extraction_fields,
        custom_prompt: currentDefaultConfig.value.custom_prompt,
    };

    let defaultTemplateToUpdate = templates.value.find(t => t.is_default === 'true' || t.is_default === true);
    let finalDefaultTemplateId; 

    if (defaultTemplateToUpdate) {
      const payload = {
        name: defaultTemplateToUpdate.name,
        description: defaultTemplateToUpdate.description,
        ...dataToSave,
        is_default: 'true'
      };
      await pdfApi.updateTemplate(defaultTemplateToUpdate.id, payload);
      finalDefaultTemplateId = defaultTemplateToUpdate.id;
      await loadTemplates(); 
    } else {
      const payload = {
        name: "系统默认配置",
        description: "系统全局默认提取配置",
        ...dataToSave,
        is_default: 'true'
      };
      const createdTemplate = await pdfApi.createTemplate(payload);
      if (createdTemplate && createdTemplate.id) {
        finalDefaultTemplateId = createdTemplate.id;
        await loadTemplates();
      } else {
        await loadTemplates(); 
        const found = templates.value.find(t => t.name === "系统默认配置" && (t.is_default === 'true' || t.is_default === true));
        if (found) {
          finalDefaultTemplateId = found.id;
        } else {
          ElMessage.error('创建新默认模板后无法确认其ID。');
          throw new Error('Could not find the newly created default template by name after creation.');
        }
      }
    }

    for (const t of templates.value) {
      if (t.id !== finalDefaultTemplateId && (t.is_default === 'true' || t.is_default === true)) {
        await pdfApi.updateTemplate(t.id, { 
          name: t.name, 
          description: t.description,
          extraction_fields: t.extraction_fields, 
          custom_prompt: t.custom_prompt,
          is_default: 'false' 
        });
      }
    }

    ElMessage.success('默认配置已保存');
    await loadTemplates(); 
    await loadCurrentDefaultConfig(); 

  } catch (error) {
    ElMessage.error('保存默认配置失败: ' + (error.response?.data?.detail || error.message || '未知错误'));
    console.error(error);
  } finally {
    savingDefaultConfig.value = false;
  }
};

const loadTemplates = async () => {
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
};

const saveCurrentAsNewTemplate = async () => {
  if (!newTemplateName.value.trim()) {
    ElMessage.warning('请输入新模板名称');
    return;
  }
  savingNewTemplate.value = true;
  try {
    const templateData = {
      name: newTemplateName.value,
      description: '新创建的模板', 
      extraction_fields: currentDefaultConfig.value.extraction_fields,
      custom_prompt: currentDefaultConfig.value.custom_prompt,
      is_default: 'false'
    };
    await pdfApi.createTemplate(templateData);
    ElMessage.success(`模板 "${newTemplateName.value}" 保存成功`);
    newTemplateName.value = '';
    loadTemplates();
  } catch (error) {
    ElMessage.error('保存新模板失败: ' + (error.response?.data?.detail || error.message || '未知错误'));
  } finally {
    savingNewTemplate.value = false;
  }
};

const handleTemplateRowClick = (template) => {
    if (editingTemplate.value && editingTemplate.value.id !== template.id && editingTemplate.value.description !== originalDescriptionBeforeEdit.value) {
      if (debouncedSaveTimeout.value) clearTimeout(debouncedSaveTimeout.value);
      saveEditedTemplate({ ...editingTemplate.value }, true);
    }
    editingTemplate.value = null; 

    currentDefaultConfig.value = {
        extraction_fields: JSON.parse(JSON.stringify(template.extraction_fields)),
        custom_prompt: template.custom_prompt || ''
    };
    ElMessage.success(`模板 "${template.name}" 已载入当前配置`);
    activeTab.value = 'defaultConfig'; 
};

const startEditTemplate = async (template) => {
    if (editingTemplate.value && editingTemplate.value.id !== template.id) {
        if (editingTemplate.value.description !== originalDescriptionBeforeEdit.value) {
            if (debouncedSaveTimeout.value) {
                clearTimeout(debouncedSaveTimeout.value);
                debouncedSaveTimeout.value = null;
            }
            ElMessage.info(`正在保存对模板 "${editingTemplate.value.name}" 的先前更改...`);
            await saveEditedTemplate({ ...editingTemplate.value }); 
        }
    }
    editingTemplate.value = JSON.parse(JSON.stringify(template));
    originalDescriptionBeforeEdit.value = template.description || '';
};

const saveEditedTemplate = async (templateDataToSave, isFinalSave = false) => {
    if (!templateDataToSave || !templateDataToSave.id) {
        console.warn('saveEditedTemplate called with invalid data');
        return;
    }
    try {
        const { id, name, description, extraction_fields, custom_prompt, is_default_bool } = templateDataToSave;
        const payload = {
            name,
            description, 
            extraction_fields, 
            custom_prompt, 
            is_default: is_default_bool ? 'true' : 'false'
        };
        await pdfApi.updateTemplate(id, payload);
        if (!isFinalSave) {
          ElMessage.success(`模板 "${name}" 描述已自动更新`);
        }
        await loadTemplates(); 
        if (editingTemplate.value && editingTemplate.value.id === id) {
            originalDescriptionBeforeEdit.value = description;
        }
    } catch (error) {
        ElMessage.error('更新模板描述失败: ' + (error.response?.data?.detail || error.message || '未知错误'));
    }
};

watch(
    () => editingTemplate.value?.description,
    (newVal) => {
        if (editingTemplate.value && newVal !== undefined && newVal !== originalDescriptionBeforeEdit.value) {
            if (debouncedSaveTimeout.value) {
                clearTimeout(debouncedSaveTimeout.value);
            }
            debouncedSaveTimeout.value = setTimeout(async () => {
                if (editingTemplate.value && editingTemplate.value.description === newVal) { 
                    await saveEditedTemplate({ ...editingTemplate.value }); 
                }
            }, 1000);
        }
    }
);

const handleDescriptionBlur = (row) => {
  if (editingTemplate.value && editingTemplate.value.id === row.id && editingTemplate.value.description !== originalDescriptionBeforeEdit.value) {
    if (debouncedSaveTimeout.value) {
      clearTimeout(debouncedSaveTimeout.value);
    }
    saveEditedTemplate({ ...editingTemplate.value }, true);
    }
};

const handleSetDefaultTemplate = async (template,เป็นDefault) => {
    if (updatingDefaultStatus[template.id]) return;
    updatingDefaultStatus[template.id] = true;

    try {
        if (เป็นDefault) {
            for (const t of templates.value) {
                if (t.id !== template.id && (t.is_default === 'true' || t.is_default === true)) {
                     const minimalPayload = { 
                        name: t.name, 
                        description: t.description, 
                        extraction_fields: t.extraction_fields,
                        custom_prompt: t.custom_prompt,
                        is_default: 'false'
                    };
                    await pdfApi.updateTemplate(t.id, minimalPayload);
                }
            }
        }
         const minimalPayloadCurrent = { 
            name: template.name, 
            description: template.description, 
            extraction_fields: template.extraction_fields,
            custom_prompt: template.custom_prompt,
            is_default: เป็นDefault ? 'true' : 'false'
        };
        await pdfApi.updateTemplate(template.id, minimalPayloadCurrent);
        ElMessage.success(`模板 "${template.name}" 已${เป็นDefault ? '设为' : '取消'}默认`);
        await loadTemplates(); 
        await loadCurrentDefaultConfig(); 
    } catch (error) {
        ElMessage.error('设置默认模板失败: ' + (error.response?.data?.detail || error.message || '未知错误'));
        const tInList = templates.value.find(t => t.id === template.id);
        if (tInList) tInList.is_default_bool = !เป็นDefault; 
    } finally {
       updatingDefaultStatus[template.id] = false;
    }
};

const deleteTemplate = async (template) => {
  ElMessageBox.confirm(
    `确定要删除模板 "${template.name}" 吗？此操作不可撤销。`,
    '确认删除',
    {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(async () => {
    try {
      if (editingTemplate.value && editingTemplate.value.id === template.id) {
        if (debouncedSaveTimeout.value) clearTimeout(debouncedSaveTimeout.value);
        editingTemplate.value = null;
        originalDescriptionBeforeEdit.value = '';
      }
      await pdfApi.deleteTemplate(template.id);
      ElMessage.success('模板删除成功');
      loadTemplates();
      if(template.is_default === 'true' || template.is_default === true) {
          loadCurrentDefaultConfig();
      }
    } catch (error) {
      ElMessage.error('删除模板失败: ' + (error.response?.data?.detail || error.message || '未知错误'));
    }
  }).catch(() => {});
};

const formatDate = (dateString) => dateString ? new Date(dateString).toLocaleString('zh-CN') : '-';

const goBack = () => {
  router.push('/');
};

onMounted(() => {
  loadCurrentDefaultConfig();
  loadTemplates();
});

</script>

<style scoped>
.field-configuration-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.config-container-card .el-card__body {
    padding-top: 0px; 
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

.config-section {
  padding: 15px;
}

.section-description {
  font-size: 14px;
  color: #606266;
  margin-bottom: 15px;
  line-height: 1.6;
}

.actions-bar {
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid #e4e7ed;
    text-align: right;
}

.template-management {
    margin-top: 10px;
}
.template-actions {
    display: flex;
    align-items: center;
    margin-bottom: 15px;
}

:deep(.el-tabs__content) {
}

:deep(.el-table__row) {
  cursor: pointer;
}

</style> 