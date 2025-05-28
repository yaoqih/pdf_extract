#!/usr/bin/env python3
"""
PDF信息提取系统后端启动脚本
"""

import os
import sys
import uvicorn
from pathlib import Path
from dotenv import load_dotenv
import os

# 加载 .env 文件
load_dotenv()
def main():
    """启动FastAPI应用"""
    
    # 获取项目根目录
    project_root = Path(__file__).parent.absolute()
    backend_dir = project_root / "backend"
    
    # 检查必要的目录
    os.makedirs(project_root / backend_dir / "uploads", exist_ok=True)
    os.makedirs(project_root / backend_dir / "static", exist_ok=True)
    
    # 检查环境变量文件
    env_file = project_root / ".env"
    if not env_file.exists():
        print("警告: 未找到.env文件，请复制env.example为.env并配置相关API密钥")
        print("系统将使用默认配置运行，但AI功能可能无法正常工作")
    
    print("正在启动PDF信息提取系统后端...")
    print("访问地址: http://localhost:8000")
    print("API文档: http://localhost:8000/docs")
    print("按 Ctrl+C 停止服务")
    
    # 切换到backend目录并添加到Python路径
    os.chdir(backend_dir)
    sys.path.insert(0, str(backend_dir))
    
    # 启动服务
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(backend_dir)],
        log_level="info"
    )

if __name__ == "__main__":
    main() 