@echo off
REM 城市体检RAG系统Windows一键部署脚本
REM 作者: AI Assistant
REM 版本: 1.0

setlocal enabledelayedexpansion

echo.
echo 🏙️ 城市体检RAG系统自动部署脚本 (Windows)
echo ==================================
echo.

REM 检查Docker是否安装
echo [INFO] 检查Docker安装状态...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker未安装，请先安装Docker Desktop
    echo 下载地址: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM 检查docker-compose是否安装
echo [INFO] 检查docker-compose安装状态...
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] docker-compose未安装，请先安装docker-compose
    pause
    exit /b 1
)

echo [SUCCESS] Docker环境检查完成

REM 配置环境变量
echo [INFO] 配置环境变量...
if not exist ".env" (
    if exist "env.example" (
        copy env.example .env >nul
        echo [WARNING] 请编辑 .env 文件配置您的API密钥
        echo [WARNING] 配置完成后重新运行此脚本
        echo.
        echo 需要配置的API密钥：
        echo - ARK_API_KEY: 火山引擎豆包API密钥
        echo - GEMINI_API_KEY: Google Gemini API密钥
        echo - DASHSCOPE_API_KEY: 阿里通义千问API密钥
        pause
        exit /b 1
    ) else (
        echo [ERROR] 找不到 env.example 文件
        pause
        exit /b 1
    )
)

REM 检查API密钥配置
findstr /C:"your_volcengine_api_key_here" .env >nul
if not errorlevel 1 (
    echo [WARNING] 检测到默认API密钥，请配置真实的API密钥
    echo [WARNING] 编辑 .env 文件后重新运行此脚本
    pause
    exit /b 1
)

echo [SUCCESS] 环境变量配置完成

REM 准备数据目录
echo [INFO] 准备数据目录...
if not exist "data\raw" mkdir data\raw
if not exist "data\processed" mkdir data\processed
if not exist "output" mkdir output
if not exist "uploads" mkdir uploads
if not exist "logs" mkdir logs
if not exist "nginx" mkdir nginx

echo [SUCCESS] 数据目录准备完成

REM 检查知识库数据
echo [INFO] 检查知识库数据...
if not exist "output\embedded_chunks.json" (
    if not exist "data\raw\20250526城市体检工作手册.pdf" (
        echo [WARNING] 未找到知识库数据文件
        echo [WARNING] 请将《城市体检工作手册》PDF文件放入 data\raw\ 目录
        echo [WARNING] 或者确保 output\embedded_chunks.json 文件存在
        echo.
        echo 文件放置完成后，系统将在首次启动时自动构建知识库
    )
) else (
    echo [SUCCESS] 发现已构建的知识库文件
)

REM 构建并启动服务
echo [INFO] 构建Docker镜像...
docker-compose build --no-cache
if errorlevel 1 (
    echo [ERROR] Docker镜像构建失败
    pause
    exit /b 1
)

echo [INFO] 启动服务...
docker-compose up -d
if errorlevel 1 (
    echo [ERROR] 服务启动失败
    pause
    exit /b 1
)

echo [INFO] 等待服务启动...
timeout /t 30 /nobreak >nul

REM 检查服务状态
echo [INFO] 检查服务状态...
set /a attempt=1
set /a max_attempts=10

:check_loop
echo [INFO] 尝试连接API服务 (第 !attempt! 次)...

REM 使用PowerShell检查HTTP状态
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:5000/api/health' -TimeoutSec 5; exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 (
    echo [SUCCESS] API服务启动成功！
    goto deployment_success
)

if !attempt! geq !max_attempts! (
    echo [ERROR] API服务启动失败，请检查日志：
    docker-compose logs rag-system --tail=50
    pause
    exit /b 1
)

timeout /t 5 /nobreak >nul
set /a attempt+=1
goto check_loop

:deployment_success
echo.
echo [SUCCESS] 🎉 城市体检RAG系统部署成功！
echo.
echo 📡 服务访问地址：
echo    - 主服务: http://localhost:5000
echo    - API文档: http://localhost:5000/docs
echo    - 健康检查: http://localhost:5000/api/health
echo    - ChromaDB: http://localhost:8000
echo.
echo 🔧 管理命令：
echo    - 查看日志: docker-compose logs -f
echo    - 停止服务: docker-compose down
echo    - 重启服务: docker-compose restart
echo    - 更新服务: docker-compose pull ^&^& docker-compose up -d
echo.
echo 📁 重要目录：
echo    - 上传文件: .\uploads\
echo    - 日志文件: .\logs\
echo    - 知识库: .\output\
echo    - 配置文件: .\config\
echo.
echo [WARNING] 注意: 首次启动可能需要下载模型文件，请耐心等待
echo.

REM 询问是否打开浏览器
set /p open_browser="是否现在打开浏览器访问系统？(Y/N): "
if /i "%open_browser%"=="Y" (
    start http://localhost:5000
)

pause
