#!/bin/bash
# 重启异步RAG系统

echo "=========================================="
echo "重启异步RAG系统"
echo "=========================================="

# 停止所有服务
echo "✓ 停止现有服务..."
pkill -f start_worker
pkill -f api_async
sleep 2

# 检查是否停止成功
if ps aux | grep -E "start_worker|api_async" | grep -v grep > /dev/null; then
    echo "⚠ 部分进程未停止，强制终止..."
    pkill -9 -f start_worker
    pkill -9 -f api_async
    sleep 1
fi

echo "✓ 所有服务已停止"

# 激活虚拟环境
if [ -d ".venv" ]; then
    echo "✓ 激活虚拟环境..."
    source .venv/bin/activate
else
    echo "⚠ 未找到虚拟环境"
fi

# 创建日志目录
mkdir -p logs

# 启动Worker
echo "✓ 启动Worker..."
nohup python start_worker.py > logs/worker.log 2>&1 &
WORKER_PID=$!
echo "  Worker PID: $WORKER_PID"
echo $WORKER_PID > .worker.pid

# 等待Worker初始化（重要：等待模型加载完成）
echo "⏳ 等待Worker初始化（加载模型）..."
sleep 5

# 检查Worker是否正常运行
if ps -p $WORKER_PID > /dev/null; then
    echo "✓ Worker运行正常"
else
    echo "✗ Worker启动失败，查看日志: tail -f logs/worker.log"
    exit 1
fi

# 启动API
echo "✓ 启动API服务..."
python api_async.py &
API_PID=$!
echo "  API PID: $API_PID"
echo $API_PID > .api.pid

echo ""
echo "=========================================="
echo "✓ 系统重启完成！"
echo "=========================================="
echo "API地址: http://localhost:5000"
echo "API文档: http://localhost:5000/docs"
echo ""
echo "查看日志:"
echo "  Worker: tail -f logs/worker.log"
echo "  API: 查看当前终端输出"
echo ""
echo "停止系统: ./stop_async_system.sh"
echo "=========================================="
