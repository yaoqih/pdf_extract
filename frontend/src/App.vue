<template>
  <div id="app">
    <el-container class="layout-container">
      <el-header class="header">
        <div class="header-content">
          <h1 class="title">
            <el-icon><Document /></el-icon>
            PDF信息提取系统
          </h1>
          <div class="header-actions">
            <el-button type="primary" @click="$router.push('/')">
              <el-icon><OfficeBuilding /></el-icon>
              主工作台
            </el-button>
            <el-button type="default" @click="$router.push('/config')">
              <el-icon><Tools /></el-icon>
              字段配置
            </el-button>
          </div>
        </div>
      </el-header>
      
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <keep-alive>
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </el-main>
      
      <el-footer class="footer">
        <p>&copy; {{ new Date().getFullYear() }} PDF信息提取系统 - 杨律案件材料处理助手</p>
      </el-footer>
    </el-container>
  </div>
</template>

<script setup>
import { Document, OfficeBuilding, Tools } from '@element-plus/icons-vue'
</script>

<style scoped>
.layout-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 0;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  flex-shrink: 0;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 60px;
  padding: 0 20px;
  max-width: 100%;
  margin: 0 auto;
}

.title {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.header-actions .el-button .el-icon {
  margin-right: 5px;
}

.main-content {
  background-color: #f0f2f5;
  flex-grow: 1;
  padding: 0;
}

.footer {
  background-color: #34495e;
  color: #ecf0f1;
  text-align: center;
  padding: 15px 20px;
  flex-shrink: 0;
}

.footer p {
  margin: 0;
  font-size: 13px;
}
</style>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  height: 100%;
}

body {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  background-color: #f0f2f5;
}

#app {
  width: 100%;
  min-height: 100%;
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
</style> 