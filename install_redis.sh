#!/bin/bash
# Redis安装脚本

echo "=========================================="
echo "Redis 安装脚本"
echo "=========================================="

# 检测操作系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "无法检测操作系统"
    exit 1
fi

echo "检测到操作系统: $OS"

# 根据操作系统安装Redis
case $OS in
    ubuntu|debian)
        echo "使用apt安装Redis..."
        sudo apt-get update
        sudo apt-get install -y redis-server
        ;;
    centos|rhel|fedora)
        echo "使用yum安装Redis..."
        sudo yum install -y redis
        ;;
    *)
        echo "不支持的操作系统: $OS"
        echo "请手动安装Redis或使用Docker:"
        echo "  docker run -d --name redis -p 6379:6379 redis:latest"
        exit 1
        ;;
esac

# 启动Redis
echo ""
echo "启动Redis服务..."
sudo systemctl start redis
sudo systemctl enable redis

# 验证安装
echo ""
echo "验证Redis安装..."
if redis-cli ping > /dev/null 2>&1; then
    echo "✓ Redis安装成功！"
    redis-cli --version
else
    echo "⚠ Redis安装完成，但服务未启动"
    echo "请手动启动: sudo systemctl start redis"
fi

echo ""
echo "=========================================="
echo "安装完成！"
echo "=========================================="
