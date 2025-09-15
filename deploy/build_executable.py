#!/usr/bin/env python3
"""
RAG系统可执行文件构建脚本
使用PyInstaller将Python应用打包成可执行文件
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def install_pyinstaller():
    """安装PyInstaller"""
    try:
        import PyInstaller
        print("✅ PyInstaller已安装")
        return True
    except ImportError:
        print("📦 正在安装PyInstaller...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
            print("✅ PyInstaller安装成功")
            return True
        except subprocess.CalledProcessError:
            print("❌ PyInstaller安装失败")
            return False

def create_spec_file():
    """创建PyInstaller规格文件"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 收集数据文件
datas = []
datas += collect_data_files('sentence_transformers')
datas += collect_data_files('transformers')
datas += collect_data_files('chromadb')
datas += [('config', 'config')]
datas += [('src', 'src')]

# 收集隐式导入
hiddenimports = []
hiddenimports += collect_submodules('sentence_transformers')
hiddenimports += collect_submodules('transformers')
hiddenimports += collect_submodules('chromadb')
hiddenimports += collect_submodules('uvicorn')
hiddenimports += collect_submodules('fastapi')
hiddenimports += [
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets.websockets_impl',
    'uvicorn.protocols.http.httptools_impl',
    'uvicorn.protocols.http.h11_impl',
]

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='RAG城市体检系统',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''
    
    with open('app.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    print("✅ 创建PyInstaller规格文件: app.spec")

def prepare_build_environment():
    """准备构建环境"""
    print("🔧 准备构建环境...")
    
    # 创建构建目录
    build_dir = Path('build_exe')
    build_dir.mkdir(exist_ok=True)
    
    # 清理之前的构建文件
    dist_dir = Path('dist')
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
        print("🗑️  清理旧的构建文件")
    
    return build_dir

def build_executable():
    """构建可执行文件"""
    print("🔨 开始构建可执行文件...")
    
    try:
        # 使用spec文件构建
        cmd = [sys.executable, '-m', 'PyInstaller', '--clean', 'app.spec']
        subprocess.check_call(cmd)
        print("✅ 可执行文件构建成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 构建失败: {e}")
        return False

def prepare_distribution():
    """准备分发包"""
    print("📦 准备分发包...")
    
    dist_dir = Path('dist')
    if not dist_dir.exists():
        print("❌ 找不到构建输出目录")
        return False
    
    # 创建必要的目录
    directories = ['data/raw', 'data/processed', 'output', 'uploads', 'logs']
    for directory in directories:
        (dist_dir / directory).mkdir(parents=True, exist_ok=True)
    
    # 复制配置文件
    if Path('config').exists():
        shutil.copytree('config', dist_dir / 'config', dirs_exist_ok=True)
    
    # 复制示例环境变量文件
    if Path('env.example').exists():
        shutil.copy2('env.example', dist_dir / 'env.example')
    
    # 创建启动脚本
    create_startup_scripts(dist_dir)
    
    # 创建README
    create_distribution_readme(dist_dir)
    
    print("✅ 分发包准备完成")
    return True

def create_startup_scripts(dist_dir):
    """创建启动脚本"""
    
    # Windows启动脚本
    windows_script = '''@echo off
echo 启动城市体检RAG系统...

REM 检查环境变量文件
if not exist ".env" (
    if exist "env.example" (
        copy env.example .env
        echo 请编辑 .env 文件配置您的API密钥
        echo 配置完成后重新运行此脚本
        pause
        exit /b 1
    )
)

REM 启动系统
echo 正在启动服务...
start "RAG系统" "RAG城市体检系统.exe" --host 0.0.0.0 --port 5000

REM 等待服务启动
timeout /t 10 /nobreak > nul

REM 打开浏览器
echo 正在打开浏览器...
start http://localhost:5000

echo RAG系统已启动！
echo 访问地址: http://localhost:5000
echo 按任意键退出...
pause > nul
'''
    
    with open(dist_dir / 'start.bat', 'w', encoding='gbk') as f:
        f.write(windows_script)
    
    # Linux启动脚本
    linux_script = '''#!/bin/bash

echo "启动城市体检RAG系统..."

# 检查环境变量文件
if [ ! -f ".env" ]; then
    if [ -f "env.example" ]; then
        cp env.example .env
        echo "请编辑 .env 文件配置您的API密钥"
        echo "配置完成后重新运行此脚本"
        exit 1
    fi
fi

# 启动系统
echo "正在启动服务..."
./RAG城市体检系统 --host 0.0.0.0 --port 5000 &

# 等待服务启动
sleep 10

# 打开浏览器
if command -v xdg-open > /dev/null; then
    xdg-open http://localhost:5000
elif command -v open > /dev/null; then
    open http://localhost:5000
fi

echo "RAG系统已启动！"
echo "访问地址: http://localhost:5000"
'''
    
    with open(dist_dir / 'start.sh', 'w', encoding='utf-8') as f:
        f.write(linux_script)
    
    # 给Linux脚本添加执行权限
    try:
        os.chmod(dist_dir / 'start.sh', 0o755)
    except:
        pass
    
    print("✅ 创建启动脚本")

def create_distribution_readme(dist_dir):
    """创建分发包说明文档"""
    readme_content = '''# 城市体检RAG系统 - 可执行文件版本

## 快速开始

### Windows系统
1. 双击运行 `start.bat` 启动系统
2. 首次运行会提示配置API密钥，编辑 `.env` 文件
3. 配置完成后重新运行 `start.bat`
4. 浏览器会自动打开 http://localhost:5000

### Linux/Mac系统
1. 在终端中运行 `./start.sh`
2. 首次运行会提示配置API密钥，编辑 `.env` 文件
3. 配置完成后重新运行 `./start.sh`
4. 浏览器会自动打开 http://localhost:5000

## API密钥配置

编辑 `.env` 文件，配置以下API密钥：

```
# 火山引擎豆包API密钥
ARK_API_KEY=your_volcengine_api_key_here

# Google Gemini API密钥
GEMINI_API_KEY=your_google_api_key_here

# 阿里通义千问API密钥
DASHSCOPE_API_KEY=your_qwen_api_key_here
```

## 系统要求

- 内存: 至少4GB可用内存
- 存储: 至少2GB可用空间
- 网络: 稳定的互联网连接（用于调用AI服务API）
- 操作系统: Windows 10+, Linux, macOS

## 目录说明

- `data/raw/`: 放置原始文档文件（如PDF）
- `output/`: 系统生成的知识库文件
- `uploads/`: 用户上传的图片文件
- `logs/`: 系统运行日志
- `config/`: 系统配置文件

## 访问地址

启动后可通过以下地址访问：
- 主页: http://localhost:5000
- API文档: http://localhost:5000/docs
- 健康检查: http://localhost:5000/api/health

## 故障排除

1. **端口被占用**: 修改启动脚本中的端口号
2. **API调用失败**: 检查网络连接和API密钥配置
3. **内存不足**: 关闭其他程序释放内存
4. **启动失败**: 查看终端输出的错误信息

## 技术支持

如遇问题，请检查：
1. 系统日志文件
2. 网络连接状态
3. API密钥有效性
4. 系统资源使用情况
'''
    
    with open(dist_dir / 'README.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print("✅ 创建分发包说明文档")

def main():
    """主函数"""
    print("🏙️ 城市体检RAG系统可执行文件构建工具")
    print("=" * 50)
    
    # 检查当前目录
    if not Path('run.py').exists():
        print("❌ 请在项目根目录运行此脚本")
        sys.exit(1)
    
    # 安装PyInstaller
    if not install_pyinstaller():
        sys.exit(1)
    
    # 准备构建环境
    build_dir = prepare_build_environment()
    
    # 创建spec文件
    create_spec_file()
    
    # 构建可执行文件
    if not build_executable():
        sys.exit(1)
    
    # 准备分发包
    if not prepare_distribution():
        sys.exit(1)
    
    print("\n🎉 构建完成！")
    print(f"📁 可执行文件位置: {Path('dist').absolute()}")
    print("📋 使用说明:")
    print("   1. 将整个 dist 目录复制到目标机器")
    print("   2. 运行 start.bat (Windows) 或 start.sh (Linux/Mac)")
    print("   3. 配置API密钥并重新启动")
    print("   4. 访问 http://localhost:5000")

if __name__ == "__main__":
    main()
