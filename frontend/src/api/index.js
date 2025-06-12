import axios from 'axios'
import { ElMessage } from 'element-plus'
import { getApiBaseURL } from '../config/index.js'

// 创建axios实例
const api = axios.create({
  baseURL: getApiBaseURL(),
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    // If the request was for a blob (like a file download),
    // return the full response object so headers can be accessed.
    if (response.config && response.config.responseType === 'blob') {
      return response; // Return the full response object
    }
    return response.data; // Otherwise, return only the data
  },
  error => {
    console.error('API Error:', error)
    // 更友好的用户提示
    let message = '请求失败，请稍后重试。'
    if (error.response) {
      // 请求已发出，但服务器响应状态码不在 2xx 范围内
      message = `请求错误 ${error.response.status}: ${error.response.data.detail || error.response.statusText || '服务器内部错误'}`
    } else if (error.request) {
      // 请求已发出，但没有收到响应
      message = '网络请求超时或服务器无响应，请检查网络连接。'
    } else {
      // 在设置请求时触发了一个错误
      message = `请求设置错误: ${error.message}`
    }
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

// API方法
export const pdfApi = {
  // 上传PDF文件
  uploadPDF(file, onUploadProgressCallback) {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        if (onUploadProgressCallback && typeof onUploadProgressCallback === 'function') {
          onUploadProgressCallback(progressEvent);
        }
      }
    })
  },

  // 上传PDF文件并使用自定义配置
  uploadPDFWithConfig(file, config, onUploadProgressCallback) {
    const formData = new FormData()
    formData.append('file', file)
    if (config) {
      formData.append('config', JSON.stringify(config))
    }
    return api.post('/upload-with-config', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        if (onUploadProgressCallback && typeof onUploadProgressCallback === 'function') {
          onUploadProgressCallback(progressEvent);
        }
      }
    })
  },

  // 获取所有案例
  getCases() {
    return api.get('/cases')
  },

  // 获取特定案例
  getCase(caseId) {
    return api.get(`/cases/${caseId}`)
  },

  // 更新案例信息
  updateCase(caseId, data) {
    return api.put(`/cases/${caseId}`, data)
  },

  // 重新处理案例
  reprocessCase(caseId, config) {
    return api.post(`/cases/${caseId}/reprocess`, config)
  },

  // 删除案例
  deleteCase(caseId) {
    return api.delete(`/cases/${caseId}`)
  },

  // 导出案例
  exportCase(caseId) {
    return api.get(`/cases/${caseId}/export`)
  },

  // 模板管理API
  // 获取所有模板
  getTemplates() {
    return api.get('/templates')
  },

  // 创建模板
  createTemplate(templateData) {
    return api.post('/templates', templateData)
  },

  // 获取特定模板
  getTemplate(templateId) {
    return api.get(`/templates/${templateId}`)
  },

  // 更新模板
  updateTemplate(templateId, templateData) {
    return api.put(`/templates/${templateId}`, templateData)
  },

  // 删除模板
  deleteTemplate(templateId) {
    return api.delete(`/templates/${templateId}`)
  },

  // 获取默认配置
  getDefaultConfig() {
    return api.get('/default-config', {
      params: {
        _: new Date().getTime() // 添加时间戳以防止缓存
      }
    });
  },

  // 新增：导出所有案例到Excel
  exportAllCasesExcel() {
    return api.post('/export-all-cases-excel', {}, {
      responseType: 'blob', // 重要：确保响应类型为blob以下载文件
    });
  },

  // 新增：清空所有案例
  clearAllCases() {
    return api.delete('/clear-all-cases');
  }
}

export default api
