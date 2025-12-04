# Urban Inspection RAG

🏙️ **多模态城市体检RAG系统** - 基于《城市体检工作手册》的智能检查助手

基于城市体检工作手册构建的多模态RAG系统，专门用于城市安全隐患识别与分析。该系统结合文本和图像双路检索技术，能够智能分析住房安全、小区功能、社区环境等城市问题，通过Chinese-CLIP、通义千问VL等先进AI模型提供专业的视觉分析和法规依据查询服务。系统采用FastAPI框架和ChromaDB向量数据库，支持实时图片上传分析、知识库检索匹配以及标准化体检报告生成，为城市管理部门和专业检查人员提供高效准确的智能辅助工具。

## 📋 目录

- [✨ 核心特性](#-核心特性)
- [🏗️ 系统架构](#️-系统架构)
- [🛠️ 技术栈](#️-技术栈)
- [📦 安装部署](#-安装部署)
- [🚀 快速开始](#-快速开始)
- [📡 API接口](#-api接口)
- [🎯 应用场景](#-应用场景)
- [📁 项目结构](#-项目结构)
- [⚙️ 配置说明](#️-配置说明)
- [🔧 开发指南](#-开发指南)
- [🤝 贡献指南](#-贡献指南)

## ✨ 核心特性

### 🔍 多模态分析
- **视觉理解**：支持图片上传和URL输入，智能识别城市安全隐患
- **文本分析**：深度理解用户查询意图，精准匹配相关法规条文
- **双路检索**：文本向量检索 + 图像向量检索，全方位信息获取

### 📚 专业知识库
- **权威依据**：基于《城市体检工作手册》构建专业知识库
- **全面覆盖**：涵盖住房安全、小区功能、社区环境三大维度
- **智能分块**：优化的文档分块策略，保持语义完整性

### 🎯 精准识别
- **14项指标**：支持结构安全、燃气安全、楼道安全等14个细分指标识别
- **案例匹配**：提供相似案例图片和处理建议
- **标准化报告**：生成符合规范的体检报告

### ⚡ 高性能架构
- **向量存储**：ChromaDB高效向量检索，毫秒级响应
- **缓存机制**：多层缓存优化，避免重复处理
- **API框架**：支持FastAPI和Flask双框架部署

## 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端界面       │    │   API网关       │    │   RAG核心       │
│  (Web/Mobile)   │◄──►│ FastAPI/Flask   │◄──►│    引擎         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                         │
                              ▼                         ▼
┌─────────────────────────────────────┐    ┌─────────────────┐
│          文件存储系统                │    │   向量数据库    │
│  ┌─────────┐  ┌─────────┐           │    │   ChromaDB      │
│  │ PDF转换 │  │ 图片存储│           │    └─────────────────┘
│  └─────────┘  └─────────┘           │              │
└─────────────────────────────────────┘              ▼
                                            ┌─────────────────┐
┌─────────────────────────────────────┐    │   AI模型服务    │
│          多模态处理层                │    │ ┌─────────────┐ │
│  ┌─────────┐  ┌─────────┐           │    │ │Chinese-CLIP │ │
│  │文本嵌入 │  │图像嵌入 │           │    │ │通义千问VL   │ │
│  └─────────┘  └─────────┘           │    │ │Google Gemini│ │
└─────────────────────────────────────┘    │ └─────────────┘ │
                                            └─────────────────┘
```

## 🛠️ 技术栈

### 后端框架
- **FastAPI** - 高性能异步API框架
- **Uvicorn** - ASGI服务器
- **Pydantic** - 数据验证和序列化

### AI & 机器学习
- **Chinese-CLIP** - 中文多模态预训练模型
- **Sentence Transformers** - 文本嵌入模型
- **CrossEncoder** - 重排序模型
- **Transformers** - HuggingFace模型库

### 向量数据库
- **ChromaDB** - 开源向量数据库
- **Elasticsearch** - 混合检索（可选）

### 多模态AI服务
- **通义千问VL** - 阿里云视觉语言模型
- **Google Gemini** - Google多模态模型
- **DashScope** - 阿里云多模态嵌入

### 数据处理
- **Pandas** - 数据分析
- **NumPy** - 数值计算
- **Pillow** - 图像处理
- **OpenCV** - 计算机视觉

## 📦 安装部署

### 环境要求
- Python 3.8+
- CUDA 11.0+ (可选，GPU加速)
- 4GB+ RAM
- 10GB+ 磁盘空间

### 1. 克隆项目
```bash
git clone https://github.com/your-username/urban-inspection-rag.git
cd urban-inspection-rag
```

### 2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 配置API密钥
在 `config/config.py` 文件中配置相关API密钥：

```python
# 火山引擎API配置
ARK_API_KEY = os.environ.get("ARK_API_KEY", "your_volcengine_api_key")

# Google Gemini API配置  
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "your_google_api_key")

# 通义千问API配置
QWEN_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "your_qwen_api_key")
```

**方式一：直接修改config.py**
直接将API密钥替换为你的实际密钥值。

**方式二：设置环境变量**
```bash
export ARK_API_KEY=your_volcengine_api_key
export GEMINI_API_KEY=your_google_api_key  
export DASHSCOPE_API_KEY=your_qwen_api_key
```

在 `ACTIVE_MODELS` 中配置使用的模型：
```python
ACTIVE_MODELS = {
    "vision": "gemini",        # 视觉分析模型
    "language": "gemini",      # 语言生成模型
    "embedding": "chinese-clip" # 向量嵌入模型
}
```

### 5. 准备数据
将PDF/Word文档放入 `data/raw/` 目录：
```bash
mkdir -p data/raw
# 复制城市体检工作手册等文档到此目录
```

### 6. 构建知识库
```bash
python main.py
```

## 🚀 快速开始

### 启动服务

```bash
python run.py --reload
```

服务启动后访问：
- API文档：http://localhost:5000/docs
- 健康检查：http://localhost:5000/api/health
- 交互式API文档：http://localhost:5000/redoc

### 基本使用

#### 1. 图片分析
```bash
curl -X POST "http://localhost:5000/api/analyze-image" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "这张图片有什么安全隐患？",
    "image_url": "https://example.com/image.jpg"
  }'
```

#### 2. 完整问答
```bash
curl -X POST "http://localhost:5000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "分析这个建筑的安全问题",
    "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJ..."
  }'
```

#### 3. 文件上传
```bash
curl -X POST "http://localhost:5000/api/upload" \
  -F "file=@/path/to/image.jpg"
```

## 📡 API接口

### 🔍 图片分析
**POST** `/api/analyze-image`

快速图片分析，返回视觉识别结果和会话ID。

```json
{
  "query": "描述图片中的安全隐患",
  "image_url": "https://example.com/image.jpg",
  "image_base64": "data:image/jpeg;base64,..."
}
```

### 💬 完成回答
**POST** `/api/complete-answer`

基于图片分析结果生成完整的体检报告。

```json
{
  "session_id": "1703123456.789"
}
```

### 🤖 综合问答
**POST** `/api/query`

一站式问答接口，支持纯文本或多模态查询。

```json
{
  "query": "这个小区有什么问题？",
  "image_url": "https://example.com/image.jpg"
}
```

### 📤 文件上传
**POST** `/api/upload`

上传图片文件，返回URL和base64编码。

### 💗 健康检查
**GET** `/api/health`

服务状态检查接口。

## 🎯 应用场景

### 🏠 住房安全检查
- **结构安全**：识别承重结构裂缝、变形、钢筋外露
- **燃气安全**：检测管道锈蚀、私拉乱接问题
- **围护安全**：发现外墙脱落、屋面渗漏、窗户破损

### 🏘️ 小区环境评估
- **停车管理**：识别违规停车、占用消防通道
- **充电安全**：检测飞线充电、设施缺失
- **公共设施**：评估活动场地、无障碍通道

### 🛣️ 街区道路巡检
- **道路状况**：发现路面破损、积水问题
- **违规停车**：识别占用人行道、盲道行为
- **共享单车**：检测乱停乱放现象

### 📊 智能报告生成
- **标准化格式**：符合城市体检工作规范
- **法规依据**：自动匹配相关政策条文
- **整改建议**：提供专业处理意见

## 📁 项目结构

```
urban-inspection-rag/
├── 📁 config/                 # 配置文件
│   └── config.py              # 主配置文件
├── 📁 data/                   # 数据目录
│   └── raw/                   # 原始文档
├── 📁 src/                    # 核心源码
│   ├── 📁 document_loader/    # 文档加载器
│   ├── 📁 embedding/          # 嵌入模型
│   ├── 📁 storage/            # 存储引擎
│   ├── 📁 retrieval/          # 检索模块
│   ├── 📁 reranker/           # 重排序器
│   ├── 📁 generator/          # 回答生成器
│   ├── 📁 utils/              # 工具函数
│   └── 📁 test/               # 测试用例
├── 📁 output/                 # 输出目录
│   ├── embedded_chunks.json   # 向量化缓存
│   └── chunks.json            # 分块缓存
├── 📁 logs/                   # 日志目录
├── 📁 uploads/                # 上传文件
├── main.py                    # 主程序入口
├── api.py                     # FastAPI服务
├── run.py                     # 启动脚本
├── requirements.txt           # 项目依赖
└── README.md                  # 项目文档
```

## ⚙️ 配置说明

### 模型配置
在 `config/config.py` 中配置各种AI模型：

```python
# 激活的模型
ACTIVE_MODELS = {
    "embedding": "text2vec-base-chinese",
    "vision": "qwen-vl", 
    "language": "volcengine"
}

# 嵌入模型配置
EMBEDDING_MODELS = {
    "text2vec-base-chinese": {
        "type": "local",
        "model_path": "shibing624/text2vec-base-chinese",
        "description": "中文文本嵌入模型"
    },
    "chinese-clip": {
        "type": "local", 
        "model_path": "OFA-Sys/chinese-clip-vit-base-patch16",
        "description": "中文多模态模型"
    }
}
```

### 提示词配置
```python
PROMPT_CONFIG = {
    "vision_analysis": {
        "city_inspection": "你是一名专业的城市体检员..."
    },
    "system": {
        "city_inspection_report": "根据视觉分析结果和知识库检索..."
    }
}
```

## 🔧 开发指南

### 添加新的嵌入模型
1. 在 `config/config.py` 中添加模型配置
2. 在 `src/embedding/embedder.py` 中实现模型加载逻辑
3. 更新 `ACTIVE_MODELS` 配置

### 自定义提示词
修改 `config/config.py` 中的 `PROMPT_CONFIG` 配置：
```python
PROMPT_CONFIG["vision_analysis"]["custom"] = "你的自定义提示词..."
```

### 扩展检索策略
在 `src/retrieval/retriever.py` 中实现新的检索算法：
```python
def custom_search(self, query: str, top_k: int = 5):
    # 自定义检索逻辑
    pass
```

### 测试指南
```bash
# 运行单元测试
python -m pytest src/test/

# 测试特定模块
python src/test/test_chinese_clip.py
python src/test/test_google_gemini.py
```

### UV开发工作流
```bash
# 安装开发依赖
uv sync --dev

# 运行测试
uv run pytest

# 代码格式化
uv run black .
uv run isort .

# 类型检查
uv run mypy src/

# 启动开发服务器
uv run python run.py --reload
```

## 🤝 贡献指南

欢迎提交Issue和Pull Request来帮助改进项目！

### 提交Issue
- 🐛 Bug报告：详细描述问题和复现步骤
- 💡 功能建议：说明需求背景和期望效果
- 📚 文档改进：指出文档不清晰或错误的地方

### 提交代码
1. Fork项目到你的GitHub账号
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add some amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 提交Pull Request

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

## 🙏 致谢

开源项目的支持：
- [ChromaDB](https://github.com/chroma-core/chroma) - 向量数据库
- [Chinese-CLIP](https://github.com/OFA-Sys/Chinese-CLIP) - 中文多模态模型
- [Sentence Transformers](https://github.com/UKPLab/sentence-transformers) - 文本嵌入
- [FastAPI](https://github.com/tiangolo/fastapi) - 现代Web框架

---

⭐ 如果这个项目对你有帮助，请给个Star支持一下！ 


