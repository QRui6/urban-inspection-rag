#!/bin/bash
# 启动异步RAG系统的所有组件

echo "=========================================="
echo "启动异步RAG系统"
echo "=========================================="

# 检查Redis是否运行
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis未运行，正在启动Redis..."
    redis-server --daemonize yes
    sleep 2
    
    if redis-cli ping > /dev/null 2>&1; then
        echo "✓ Redis启动成功"
    else
        echo "✗ Redis启动失败，请手动启动: redis-server"
        exit 1
    fi
else
    echo "✓ Redis已运行"
fi

# 激活虚拟环境
if [ -d ".venv" ]; then
    echo "✓ 激活虚拟环境..."
    source .venv/bin/activate
else
    echo "⚠ 未找到虚拟环境，使用系统Python"
fi

# 启动RQ Worker（后台运行）
echo "✓ 启动RQ Worker..."
nohup python start_worker.py > logs/worker.log 2>&1 &
WORKER_PID=$!
echo "  Worker PID: $WORKER_PID"

# 等待Worker启动
sleep 2

# 启动异步API服务
echo "✓ 启动异步API服务 (端口5001)..."
python api_async.py &
API_PID=$!
echo "  API PID: $API_PID"

echo ""
echo "=========================================="
echo "✓ 系统启动完成！"
echo "=========================================="
echo "异步API地址: http://localhost:5001"
echo "API文档: http://localhost:5001/docs"
echo "队列统计: http://localhost:5001/api/queue/stats"
echo ""
echo "查看Worker日志: tail -f logs/worker.log"
echo ""
echo "停止系统:"
echo "  kill $WORKER_PID  # 停止Worker"
echo "  kill $API_PID     # 停止API"
echo "或运行: ./stop_async_system.sh"
echo "=========================================="

# 保存PID到文件
echo $WORKER_PID > .worker.pid
echo $API_PID > .api.pid
