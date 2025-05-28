@echo off
echo 启动前端开发服务器...
cd /d "%~dp0"
"C:\Program Files\nodejs\node.exe" ".\node_modules\vite\bin\vite.js"
pause 