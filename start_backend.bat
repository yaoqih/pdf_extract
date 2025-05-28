@echo off
echo 正在启动PDF信息提取系统后端...
echo.
echo 请确保已安装Python 3.8+
echo.

echo 检查虚拟环境...
if not exist venv (
    echo 创建虚拟环境...
    python -m venv venv
)

echo 激活虚拟环境...
call venv\Scripts\activate

echo 安装依赖...
pip install -r requirements.txt

echo.
echo 启动后端服务...
echo 访问地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo 按 Ctrl+C 停止服务
echo.

python start_backend.py

pause 