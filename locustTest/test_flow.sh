#!/bin/bash
# 测试两阶段流程的并发性能

# 激活虚拟环境
if [ -f "../.venv/bin/activate" ]; then
    source ../.venv/bin/activate
    echo "✓ 虚拟环境已激活"
else
    echo "❌ 找不到虚拟环境"
    exit 1
fi

echo "=========================================="
echo "  两阶段流程并发测试"
echo "  analyze-image -> complete-answer"
echo "=========================================="
echo ""

# 检查图片文件
if [ ! -f "test_image_base64.txt" ]; then
    echo "❌ test_image_base64.txt 不存在"
    exit 1
fi

# 检查API
if ! curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
    echo "❌ API服务未运行"
    exit 1
fi

echo "✓ 环境检查通过"
echo ""

RESULT_DIR="flow_test_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULT_DIR"


# 测试1: 3用户并发
echo "测试1: 小并发 (3用户, 5分钟)"
locust -f locustfile_flow.py \
    --host=http://localhost:5000 \
    --users=3 \
    --spawn-rate=1 \
    --run-time=2m \
    --headless \
    --html="$RESULT_DIR/test2_3users.html" \
    --csv="$RESULT_DIR/test2_3users"

echo ""
echo "⏳ 等待30秒..."
sleep 30

# 测试3: 5用户并发
echo "测试2: 中等并发 (5用户, 5分钟)"
locust -f locustfile_flow.py \
    --host=http://localhost:5000 \
    --users=5 \
    --spawn-rate=1 \
    --run-time=2m \
    --headless \
    --html="$RESULT_DIR/test3_5users.html" \
    --csv="$RESULT_DIR/test3_5users"

echo ""
echo "⏳ 等待30秒..."
sleep 30

# 测试4: 10用户高并发
echo "测试3: 高并发 (10用户, 5分钟)"
locust -f locustfile_flow.py \
    --host=http://localhost:5000 \
    --users=10 \
    --spawn-rate=2 \
    --run-time=3m \
    --headless \
    --html="$RESULT_DIR/test4_10users.html" \
    --csv="$RESULT_DIR/test4_10users"

echo ""
echo "=========================================="
echo "✅ 测试完成！"
echo "结果目录: $RESULT_DIR/"
echo "=========================================="
