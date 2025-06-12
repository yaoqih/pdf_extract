// 环境配置文件
const config = {
  development: {
    apiBaseURL: 'http://localhost:8000/api',
    frontendPort: 3000,
    backendPort: 8000
  },
  production: {
    // 生产环境动态获取IP
    apiBaseURL: `http://${window.location.hostname}:8000/api`,
    frontendPort: 3000,
    backendPort: 8000
  }
}

// 获取当前环境
const getEnvironment = () => {
  if (import.meta.env.MODE === 'development') {
    return 'development'
  }
  return 'production'
}

// 获取当前环境配置
const getCurrentConfig = () => {
  const env = getEnvironment()
  return config[env]
}

// 动态获取API基础URL
export const getApiBaseURL = () => {
  const hostname = window.location.hostname
  
  // 本地开发环境
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return config.development.apiBaseURL
  }
  
  // 生产环境或其他IP
  return `http://${hostname}:${config.production.backendPort}/api`
}

// 导出配置
export default getCurrentConfig()
export { config, getEnvironment } 