@echo off
echo 正在启动PDF信息提取系统前端...
echo.
echo 请确保已安装Node.js和npm
echo.

cd frontend

echo 检查依赖...
if not exist node_modules (
    echo 正在安装依赖...
    npm install
)

echo.
echo 启动开发服务器...
echo 访问地址: http://localhost:3000
echo 按 Ctrl+C 停止服务
echo.

npm run dev

pause 