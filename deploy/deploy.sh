#!/bin/bash

# 城市体检RAG系统一键部署脚本
# 作者: AI Assistant
# 版本: 1.0

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 未安装，请先安装 $1"
        return 1
    fi
    return 0
}

# 检查系统要求
check_requirements() {
    print_status "检查系统要求..."
    
    # 检查Docker
    if ! check_command docker; then
        print_error "请先安装Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # 检查docker-compose
    if ! check_command docker-compose; then
        print_error "请先安装docker-compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    # 检查可用内存
    available_mem=$(free -m | awk 'NR==2{printf "%.1f", $7/1024}')
    required_mem=4.0
    if (( $(echo "$available_mem < $required_mem" | bc -l) )); then
        print_warning "可用内存 ${available_mem}GB 可能不足，建议至少 ${required_mem}GB"
    fi
    
    # 检查磁盘空间
    available_disk=$(df -BG . | awk 'NR==2{print $4}' | sed 's/G//')
    required_disk=10
    if [ "$available_disk" -lt "$required_disk" ]; then
        print_warning "可用磁盘空间 ${available_disk}GB 可能不足，建议至少 ${required_disk}GB"
    fi
    
    print_success "系统要求检查完成"
}

# 配置环境变量
setup_environment() {
    print_status "配置环境变量..."
    
    if [ ! -f ".env" ]; then
        if [ -f "env.example" ]; then
            cp env.example .env
            print_warning "请编辑 .env 文件配置您的API密钥"
            print_warning "配置完成后重新运行此脚本"
            echo ""
            echo "需要配置的API密钥："
            echo "- ARK_API_KEY: 火山引擎豆包API密钥"
            echo "- GEMINI_API_KEY: Google Gemini API密钥"
            echo "- DASHSCOPE_API_KEY: 阿里通义千问API密钥"
            exit 1
        else
            print_error "找不到 env.example 文件"
            exit 1
        fi
    fi
    
    # 检查API密钥是否配置
    source .env
    if [[ "$ARK_API_KEY" == "your_volcengine_api_key_here" ]] || 
       [[ "$GEMINI_API_KEY" == "your_google_api_key_here" ]] || 
       [[ "$DASHSCOPE_API_KEY" == "your_qwen_api_key_here" ]]; then
        print_warning "检测到默认API密钥，请配置真实的API密钥"
        print_warning "编辑 .env 文件后重新运行此脚本"
        exit 1
    fi
    
    print_success "环境变量配置完成"
}

# 准备数据目录
prepare_directories() {
    print_status "准备数据目录..."
    
    # 创建必要的目录
    mkdir -p data/raw
    mkdir -p data/processed
    mkdir -p output
    mkdir -p uploads
    mkdir -p logs
    mkdir -p nginx
    
    # 设置目录权限
    chmod 755 data uploads logs output
    
    print_success "数据目录准备完成"
}

# 检查知识库数据
check_knowledge_base() {
    print_status "检查知识库数据..."
    
    if [ ! -f "output/embedded_chunks.json" ]; then
        if [ ! -f "data/raw/20250526城市体检工作手册.pdf" ]; then
            print_warning "未找到知识库数据文件"
            print_warning "请将《城市体检工作手册》PDF文件放入 data/raw/ 目录"
            print_warning "或者确保 output/embedded_chunks.json 文件存在"
            echo ""
            echo "文件放置完成后，系统将在首次启动时自动构建知识库"
        fi
    else
        print_success "发现已构建的知识库文件"
    fi
}

# 构建并启动服务
deploy_services() {
    print_status "构建Docker镜像..."
    docker-compose build --no-cache
    
    print_status "启动服务..."
    docker-compose up -d
    
    print_status "等待服务启动..."
    sleep 30
}

# 检查服务状态
check_services() {
    print_status "检查服务状态..."
    
    # 检查容器状态
    if ! docker-compose ps | grep -q "Up"; then
        print_error "服务启动失败，检查日志："
        docker-compose logs --tail=50
        exit 1
    fi
    
    # 检查API健康状态
    max_attempts=10
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        print_status "尝试连接API服务 (第 $attempt 次)..."
        
        if curl -f -s http://localhost:5000/api/health > /dev/null 2>&1; then
            print_success "API服务启动成功！"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            print_error "API服务启动失败，请检查日志："
            docker-compose logs rag-system --tail=50
            exit 1
        fi
        
        sleep 5
        attempt=$((attempt + 1))
    done
}

# 显示部署信息
show_deployment_info() {
    print_success "🎉 城市体检RAG系统部署成功！"
    echo ""
    echo "📡 服务访问地址："
    echo "   - 主服务: http://localhost:5000"
    echo "   - API文档: http://localhost:5000/docs"
    echo "   - 健康检查: http://localhost:5000/api/health"
    echo "   - ChromaDB: http://localhost:8000"
    echo ""
    echo "🔧 管理命令："
    echo "   - 查看日志: docker-compose logs -f"
    echo "   - 停止服务: docker-compose down"
    echo "   - 重启服务: docker-compose restart"
    echo "   - 更新服务: docker-compose pull && docker-compose up -d"
    echo ""
    echo "📁 重要目录："
    echo "   - 上传文件: ./uploads/"
    echo "   - 日志文件: ./logs/"
    echo "   - 知识库: ./output/"
    echo "   - 配置文件: ./config/"
    echo ""
    print_warning "注意: 首次启动可能需要下载模型文件，请耐心等待"
}

# 主函数
main() {
    echo ""
    echo "🏙️ 城市体检RAG系统自动部署脚本"
    echo "=================================="
    echo ""
    
    check_requirements
    setup_environment
    prepare_directories
    check_knowledge_base
    deploy_services
    check_services
    show_deployment_info
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
