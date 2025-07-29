"""
RAG系统启动脚本
"""
import os
import sys
import argparse
from api import app, UPLOAD_FOLDER

def main():
    """启动服务"""
    parser = argparse.ArgumentParser(description='启动RAG系统API服务')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='监听主机地址')
    parser.add_argument('--port', type=int, default=5000, help='监听端口')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    args = parser.parse_args()
    
    # 确保上传目录存在
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    print(f"上传目录已就绪: {UPLOAD_FOLDER}")
    
    print(f"RAG系统API服务启动中，监听地址: {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main() 