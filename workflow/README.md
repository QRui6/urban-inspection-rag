# 城市体检RAG系统工作流程图

## 文件说明

本目录包含城市体检RAG（检索增强生成）系统的完整技术流程图：

- `RAG_System_Workflow.drawio` - 系统工作流程图（业务流程视角）
- `RAG_Technical_Architecture.drawio` - 技术架构图（技术组件视角）
- `RAG_Workflow.drawio` - 原有流程图（保留）

## 如何查看

1. 在线查看：
   - 访问 [draw.io](https://app.diagrams.net/)
   - 点击"打开已有图表"
   - 选择上传本地文件，选择对应的`.drawio`文件

2. 桌面应用查看：
   - 下载并安装[draw.io Desktop](https://github.com/jgraph/drawio-desktop/releases)
   - 使用应用打开对应的`.drawio`文件

## 流程图详细说明

### RAG_System_Workflow.drawio - 系统工作流程图

展示了城市体检RAG系统的完整业务流程，包含两个主要阶段：

#### 阶段1：知识库构建
- **原始文档** → **PDF转Markdown** → **文档分块**
- **文本块** → **向量化** → **向量存储**
- **图像块** → **VLM图像描述** → **向量化** → **向量存储**

#### 阶段2：查询处理
- **用户输入**（文本/图像）
- **视觉模型分析**（针对图像输入）
- **双路检索**：
  - 路径1：文本向量检索（使用视觉分析文本）
  - 路径2：图像向量检索（直接使用图像向量）
- **检索结果融合** → **重排序** → **回答生成** → **最终输出**

#### API接口层
- `/api/analyze-image`：图像分析接口
- `/api/complete-answer`：完成回答接口
- `/api/query`：完整查询接口
- `/api/upload`：文件上传接口

### RAG_Technical_Architecture.drawio - 技术架构图

从技术组件角度展示系统架构，包含以下层次：

#### 用户界面层
- Web前端界面、移动端应用、API客户端

#### API服务层 (Flask)
- 图像分析、完成回答、完整查询、文件上传等接口

#### 核心业务层 (RAGSystem)
- **文档处理模块**：DocumentLoader、PDF2MD、MarkdownChunkLoader、VLM Batch
- **向量化模块**：Embedder、文本向量化、图像向量化
- **检索模块**：Retriever、双路检索、Reranker、结果融合器
- **生成模块**：Generator、提示词引擎
- **视觉理解模块**：多视觉模型、图像安全分析

#### 存储层
- ChromaStore（向量数据库）、文件存储、日志存储、快照存储

#### 外部服务层
- 通义千问API、Gemini API、火山引擎API、HuggingFace

#### 配置管理模块
- 模型配置、提示词配置、激活模型配置

#### 工具模块
- 图像工具等辅助功能

## 系统特色功能

### 1. 多模态支持
- 支持纯文本查询
- 支持文本+图像混合查询
- 图像安全隐患自动识别

### 2. 双路检索机制
- **文本路径**：使用视觉分析结果进行文本向量检索
- **图像路径**：直接使用图像向量进行相似图像检索
- **智能融合**：将两路检索结果进行融合和重排序

### 3. 城市体检专用
- 专门针对城市体检场景设计
- 支持9种安全隐患类型识别
- 提供专业的体检依据和整改建议

### 4. 灵活的模型配置
- 支持多种视觉模型（通义千问VL、Gemini）
- 支持多种语言模型（火山引擎、Gemini）
- 支持多种向量化模型（Sentence-Transformers、CLIP）

### 5. 完善的API设计
- RESTful接口设计
- 支持分步处理（先分析图像，再生成完整回答）
- 支持文件上传和base64图像处理

## 技术栈

- **后端框架**：Python + Flask
- **向量数据库**：ChromaDB
- **向量化技术**：Sentence-Transformers + CLIP
- **视觉模型**：通义千问VL + Gemini
- **语言模型**：火山引擎 + Gemini
- **文档处理**：PDF转Markdown + 智能分块
- **重排序**：Cross-encoder模型