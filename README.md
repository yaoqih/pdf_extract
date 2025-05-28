# PDF证据材料信息提取系统

一个基于AI的PDF证据材料信息提取和整理系统，专为律师事务所设计，支持自定义提取字段和提示词配置。

## 功能特点

### 🔍 智能信息提取
- **多层次文本识别**：结合百度OCR、Gemini VLM和LLM技术
- **证据材料专用**：专门针对法律证据材料优化
- **高精度提取**：支持中英文混合文档识别

### ⚙️ 灵活配置系统
- **自定义提取字段**：可配置需要提取的信息项
- **自定义提示词**：支持个性化的AI提示词模板
- **模板管理**：保存和复用提取配置模板
- **动态字段类型**：支持文本、多行文本、日期、数字等多种字段类型

### 📋 默认提取字段
系统预设了常用的证据材料信息字段：
- 姓名
- 性别  
- 民族
- 身份证号
- 家庭住址
- 合同签订时间
- 转账人
- 转账人银行账号
- 渠道
- 转账时间
- 收款人
- 收款人银行账号

### 🎯 智能处理流程
1. **PDF上传**：支持拖拽上传，最大50MB
2. **OCR识别**：使用百度OCR进行文字识别
3. **VLM分析**：Gemini Vision模型辅助理解
4. **LLM提取**：智能提取结构化信息
5. **结果编辑**：支持手动编辑和完善
6. **重新处理**：可使用新配置重新处理

## 技术架构

### 后端技术栈
- **框架**：FastAPI (Python)
- **OCR服务**：百度OCR API
- **VLM模型**：Google Gemini 2.0 Flash Exp
- **LLM模型**：Gemini / OpenAI兼容API
- **数据库**：SQLite
- **文件处理**：PyMuPDF, Pillow

### 前端技术栈
- **框架**：Vue 3 + Vite
- **UI组件**：Element Plus
- **状态管理**：Pinia
- **路由**：Vue Router
- **HTTP客户端**：Axios

## 快速开始

### 环境要求
- Python 3.8+
- Node.js 16+
- npm 或 pnpm

### 安装依赖

#### 后端依赖
```bash
pip install -r requirements.txt
```

#### 前端依赖
```bash
cd frontend
pnpm install
# 或者
npm install
```

### 环境配置

复制环境变量模板：
```bash
cp env.example .env
```

配置API密钥：
```env
# 百度OCR配置
BAIDU_API_KEY=your_baidu_api_key_here
BAIDU_SECRET_KEY=your_baidu_secret_key_here

# Gemini配置
GOOGLE_API_KEY=your_google_api_key_here
GEMINI_BASE_URL=https://generativelanguage.googleapis.com

# OpenAI兼容API配置（可选）
OPENAI_API_KEY=your_gemini_compatible_api_key_here
OPENAI_API_BASE=your_gemini_compatible_base_url_here
```

### 启动服务

#### 启动后端
```bash
python start_backend.py
```
后端服务将在 http://localhost:8000 启动

#### 启动前端
```bash
cd frontend
pnpm run dev
# 或者使用批处理脚本
.\start_dev.bat
```
前端服务将在 http://localhost:3000 启动

## 使用指南

### 基础使用
1. 打开浏览器访问 http://localhost:3000
2. 拖拽或点击上传PDF文件
3. 等待系统自动处理
4. 查看和编辑提取结果

### 高级配置
1. 点击"显示高级配置"
2. 配置自定义提取字段：
   - 设置字段键名和标签
   - 选择字段类型（文本/日期/数字等）
   - 标记必填字段
3. 编写自定义提示词（可选）
4. 保存为模板供后续使用

### 模板管理
- **创建模板**：在配置界面点击"保存为模板"
- **使用模板**：从下拉列表选择已保存的模板
- **管理模板**：通过API接口管理模板（未来将添加UI界面）

### 重新处理
对于已处理的文件，可以：
1. 在详情页面点击"重新处理"
2. 修改提取配置
3. 重新运行提取流程

## API文档

### 核心接口
- `POST /api/upload` - 上传PDF文件（使用默认配置）
- `POST /api/upload-with-config` - 上传PDF文件（使用自定义配置）
- `GET /api/cases` - 获取所有案例列表
- `GET /api/cases/{id}` - 获取案例详情
- `PUT /api/cases/{id}` - 更新案例信息
- `POST /api/cases/{id}/reprocess` - 重新处理案例

### 配置接口
- `GET /api/default-config` - 获取默认配置
- `GET /api/templates` - 获取所有模板
- `POST /api/templates` - 创建新模板
- `PUT /api/templates/{id}` - 更新模板
- `DELETE /api/templates/{id}` - 删除模板

## 常见问题

### 前端依赖安装问题
如果遇到 `npm install` 失败，建议：
1. 使用 `pnpm install` 替代
2. 清理 node_modules 目录后重试
3. 使用提供的启动脚本：`.\start_dev.bat`

### NumPy版本兼容性警告
系统可能显示NumPy版本兼容性警告，但不影响核心功能。如需解决：
```bash
pip install "numpy<2"
```

### API配置问题
请确保正确配置了API密钥：
- 百度OCR：需要在百度智能云申请
- Gemini：需要Google AI Studio API密钥
- 详细配置说明请参考 `API_CONFIG.md`

## 开发说明

### 项目结构
```
pdf_extract/
├── backend/                 # 后端代码
│   ├── services/           # 核心服务
│   │   ├── pdf_processor.py    # PDF处理器
│   │   └── ai_extractor.py     # AI信息提取器
│   ├── models.py           # 数据模型
│   ├── schemas.py          # API模式
│   └── main.py            # 主应用
├── frontend/               # 前端代码
│   ├── src/
│   │   ├── components/     # Vue组件
│   │   ├── views/         # 页面视图
│   │   ├── api/           # API接口
│   │   └── router/        # 路由配置
│   └── package.json
├── uploads/               # 上传文件目录
├── static/               # 静态文件目录
└── requirements.txt      # Python依赖
```

### 扩展开发
- **添加新字段类型**：在 `ExtractionConfig.vue` 中扩展字段类型
- **自定义处理器**：继承 `PDFProcessor` 类
- **新的AI模型**：在 `AIExtractor` 中添加新的API调用方法

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 更新日志

### v1.1.0 (当前版本)
- ✨ 新增自定义提取字段配置
- ✨ 新增自定义提示词支持
- ✨ 新增模板管理功能
- ✨ 新增重新处理功能
- 🔄 改进为证据材料专用系统
- 🎨 优化用户界面和交互体验

### v1.0.0
- 🎉 初始版本发布
- 📄 基础PDF文本提取功能
- 🤖 AI信息提取功能