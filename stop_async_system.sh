#!/bin/bash
# 停止异步RAG系统

echo "=========================================="
echo "停止异步RAG系统"
echo "=========================================="

# 停止Worker
if [ -f ".worker.pid" ]; then
    WORKER_PID=$(cat .worker.pid)
    if kill -0 $WORKER_PID 2>/dev/null; then
        echo "✓ 停止Worker (PID: $WORKER_PID)..."
        kill $WORKER_PID
        rm .worker.pid
    else
        echo "⚠ Worker已停止"
        rm .worker.pid
    fi
else
    echo "⚠ 未找到Worker PID文件"
fi

# 停止API
if [ -f ".api.pid" ]; then
    API_PID=$(cat .api.pid)
    if kill -0 $API_PID 2>/dev/null; then
        echo "✓ 停止API (PID: $API_PID)..."
        kill $API_PID
        rm .api.pid
    else
        echo "⚠ API已停止"
        rm .api.pid
    fi
else
    echo "⚠ 未找到API PID文件"
fi

echo "=========================================="
echo "✓ 系统已停止"
echo "=========================================="
