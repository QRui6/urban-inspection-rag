"""
RAG系统FastAPI启动脚本
"""
import os
import sys
import argparse
import uvicorn
from api import app, UPLOAD_FOLDER

def main():
    """启动FastAPI服务"""
    parser = argparse.ArgumentParser(description='启动RAG系统FastAPI服务')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='监听主机地址')
    parser.add_argument('--port', type=int, default=5000, help='监听端口')
    parser.add_argument('--reload', action='store_true', help='启用自动重载（开发模式）')
    parser.add_argument('--workers', type=int, default=1, help='工作进程数量')
    
    args = parser.parse_args()
    
    # 确保上传目录存在
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    print(f"上传目录已就绪: {UPLOAD_FOLDER}")
    
    print(f"RAG系统FastAPI服务启动中，监听地址: {args.host}:{args.port}")
    
    # 启动uvicorn服务器
    uvicorn.run(
        "api:app",  # 应用模块和变量
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,  # reload模式下只能有1个worker
        log_level="info"
    )

if __name__ == "__main__":
    main() 