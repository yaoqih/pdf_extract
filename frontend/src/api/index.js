import axios from 'axios'

// 创建axios实例
const api = axios.create({
  baseURL: 'http://localhost:8000/api',
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
    return response.data
  },
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// API方法
export const pdfApi = {
  // 上传PDF文件
  uploadPDF(file) {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  // 上传PDF文件并使用自定义配置
  uploadPDFWithConfig(file, config) {
    const formData = new FormData()
    formData.append('file', file)
    if (config) {
      formData.append('config', JSON.stringify(config))
    }
    return api.post('/upload-with-config', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
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
    return api.get('/default-config')
  }
}

export default api
