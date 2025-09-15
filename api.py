"""
RAG系统FastAPI服务
提供REST API接口，包装RAG系统功能
"""
import os
import time
import json
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from werkzeug.utils import secure_filename
from main import RAGSystem
from src.vision_analyzer import VisionAnalyzer
from src.utils.image_tools import image_to_base64
from src.storage.chroma_store import ChromaStore
from config.config import PROMPT_CONFIG

# 创建FastAPI应用
app = FastAPI(
    title="RAG系统API",
    description="城市体检RAG系统的REST API接口",
    version="1.0.0"
)

# 启用CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化RAG系统
rag = RAGSystem(dual_retrieval=True)  # 默认启用双路检索

# 上传文件配置
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 挂载静态文件服务
app.mount("/uploads", StaticFiles(directory=UPLOAD_FOLDER), name="uploads")

# 创建会话存储，用于在不同请求之间保存视觉分析结果
# 格式: {session_id: {"visual_analysis": "...", "timestamp": 1234567890, "img_input": "..."}}
session_store: Dict[str, Dict[str, Any]] = {}

# 初始化RAG系统前，加载知识库快照到Chroma
SNAPSHOT_PATH = os.path.join("output", "embedded_chunks.json")
if os.path.exists(SNAPSHOT_PATH):
    print(f"检测到知识库快照文件: {SNAPSHOT_PATH}，正在加载到Chroma...")
    try:
        with open(SNAPSHOT_PATH, "r", encoding="utf-8") as f:
            embedded_chunks = json.load(f)
        chroma_store = ChromaStore()
        # chroma_store.delete_index()  # 清空collection，防止重复
        success = chroma_store.add_documents(embedded_chunks)
        if success:
            print("知识库快照已成功加载到Chroma数据库！")
        else:
            print("加载知识库快照到Chroma时发生错误，请检查日志。")
    except Exception as e:
        print(f"加载知识库快照失败: {e}")
else:
    print(f"未检测到知识库快照文件: {SNAPSHOT_PATH}，请先运行主流程构建知识库。")


# Pydantic模型定义
class HealthResponse(BaseModel):
    status: str
    timestamp: float


class AnalyzeImageRequest(BaseModel):
    query: str
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    use_structured_output: Optional[bool] = True  # 新增：是否使用结构化输出


class AnalyzeImageResponse(BaseModel):
    session_id: str
    status: str
    visual_analysis: str
    models_used: Dict[str, Optional[str]]
    timestamp: float
    is_structured: bool = False  # 新增：标识是否为结构化输出


class CompleteAnswerRequest(BaseModel):
    session_id: str


class CompleteAnswerResponse(BaseModel):
    status: str
    answer: str
    models_used: Dict[str, Optional[str]]
    timestamp: float


class QueryRequest(BaseModel):
    query: str
    image_url: Optional[str] = None
    image_base64: Optional[str] = None


class QueryResponse(BaseModel):
    status: str
    timestamp: float
    visual_analysis: Optional[str] = None
    models_used: Optional[Dict[str, Optional[str]]] = None
    answer: Optional[str] = None


class UploadResponse(BaseModel):
    file_url: Optional[str] = None
    base64: Optional[str] = None
    filename: str
    success: bool
    error: Optional[str] = None


def allowed_file(filename: str) -> bool:
    """检查文件类型是否允许上传"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.get('/api/health', response_model=HealthResponse)
async def health_check():
    """健康检查接口"""
    return HealthResponse(
        status="ok",
        timestamp=time.time()
    )


@app.post('/api/analyze-image', response_model=AnalyzeImageResponse)
async def analyze_image(request: AnalyzeImageRequest):
    """图片分析接口
    接收问题和图片URL或base64数据，只执行视觉模型分析，立即返回结果
    """
    try:
        if not request.image_url and not request.image_base64:
            raise HTTPException(
                status_code=400, 
                detail="image_url或image_base64至少提供一项"
            )
        
        # 生成会话ID
        session_id = str(time.time())
        
        # 选择图片输入源
        img_input = request.image_base64 if request.image_base64 else request.image_url
        
        # 调用RAG系统执行视觉分析（支持结构化输出）
        vl_prompt = PROMPT_CONFIG["vision_analysis"]["city_inspection"]
        use_structured = True
        vl_text, model_used = rag.analyze_image(img_input, vl_prompt, use_structured)
        
        # 添加失败重试机制（与query函数保持一致）
        if not vl_text and os.path.exists(img_input):
            print("尝试使用base64方式调用视觉模型...")
            try:
                base64_image = image_to_base64(img_input)
                if base64_image:
                    vl_text, model_used = rag.analyze_image(base64_image, vl_prompt, use_structured)
                    model_used = f"{model_used} (本地文件转base64)"
            except Exception as e:
                print(f"本地文件转base64调用失败: {e}")
        
        if not vl_text:
            raise HTTPException(
                status_code=500,
                detail="无法识别图片内容"
            )
        
        # 保存分析结果到会话存储，便于后续请求使用
        session_store[session_id] = {
            "visual_analysis": vl_text,
            "query": request.query,
            "img_input": img_input,
            "timestamp": time.time()
        }
        if isinstance(vl_text, dict):
            visual_analysis=json.dumps(vl_text, ensure_ascii=False)
            visual_analysis = visual_analysis.replace("indicator_classification", "指标分类")
            visual_analysis = visual_analysis.replace("specific_problem", "具体问题")
            visual_analysis = visual_analysis.replace("detailed_description", "详细描述")
        else:
            visual_analysis=vl_text
        # 构建并返回响应
        return AnalyzeImageResponse(
            session_id=session_id,
            status="success",
            visual_analysis=visual_analysis,
            models_used={
                "vision": model_used,
                "language": None
            },
            timestamp=time.time(),
            is_structured=use_structured
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"处理图片分析请求时出错: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"处理图片分析请求时出错: {str(e)}"
        )


@app.post('/api/complete-answer', response_model=CompleteAnswerResponse)
async def complete_answer(request: CompleteAnswerRequest):
    """完成回答接口
    接收会话ID，基于之前的视觉分析结果生成最终回答
    """
    try:
        # 检查会话是否存在
        if request.session_id not in session_store:
            raise HTTPException(
                status_code=404,
                detail="会话已过期或不存在"
            )
        
        # 获取会话数据
        session_data = session_store[request.session_id]
        visual_analysis = session_data["visual_analysis"]
        query_text = session_data["query"]
        img_input = session_data["img_input"]
        
        # 基于视觉分析结果，完成最终答案生成
        response = rag.complete_answer(query_text, img_input, visual_analysis)
        
        # 清理会话存储
        if request.session_id in session_store:
            del session_store[request.session_id]
        
        return CompleteAnswerResponse(
            status=response.get("status", "success"),
            answer=response.get("answer", ""),
            models_used=response.get("models_used", {}),
            timestamp=time.time()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"生成最终回答时出错: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"生成最终回答时出错: {str(e)}"
        )


@app.post('/api/query', response_model=QueryResponse)
async def query(request: QueryRequest):
    """问答接口(原始完整流程，保留以兼容旧版)
    接收JSON格式的请求，包含问题和可选的图片URL或base64数据
    返回AI回答，如果有图片输入，则同时返回视觉分析结果
    """
    try:
        # 处理图片输入 - 优先使用base64方式
        if request.image_base64 and request.image_base64.startswith('data:image'):
            # 使用base64数据调用RAG系统
            print("使用base64图片数据进行问答")
            response = rag.query(request.query, request.image_base64)
        elif request.image_url:
            # 使用URL方式调用RAG系统 - 用于终端测试
            print(f"使用图片URL进行问答: {request.image_url}")
            response = rag.query(request.query, request.image_url)
        else:
            # 纯文本问答
            print("执行纯文本问答")
            response = rag.query(request.query)
        
        # 构建API响应，包含状态、视觉分析结果和最终答案
        return QueryResponse(
            status=response.get("status", "success"),
            timestamp=time.time(),
            visual_analysis=response.get("visual_analysis"),
            models_used=response.get("models_used"),
            answer=response.get("answer")
        )
        
    except Exception as e:
        print(f"处理请求时出错: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"处理请求时出错: {str(e)}"
        )


@app.post('/api/upload', response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """文件上传接口
    接收图片文件，保存到服务器，并返回图片URL和base64数据
    """
    try:
        # 检查文件是否为空
        if not file.filename:
            raise HTTPException(status_code=400, detail="未选择文件")
        
        if not allowed_file(file.filename):
            raise HTTPException(status_code=400, detail="不支持的文件类型")
        
        # 安全地获取文件名并保存
        filename = secure_filename(file.filename)
        timestamp = int(time.time())
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        # 保存文件
        content = await file.read()
        with open(filepath, "wb") as f:
            f.write(content)
        
        # 生成文件的URL路径
        file_url = f"/uploads/{unique_filename}"
        
        # 转换为base64以便直接在前端显示和发送到模型
        try:
            base64_data = image_to_base64(filepath)
            if base64_data:
                print(f"成功生成图片base64数据: {filepath}, 文件URL: {file_url}")
                return UploadResponse(
                    file_url=file_url,
                    base64=base64_data,
                    filename=filename,
                    success=True
                )
        except Exception as e:
            print(f"转换base64出错: {e}")
            # 如果base64转换失败，仅返回URL
            return UploadResponse(
                file_url=file_url,
                filename=filename,
                error=f"Base64转换失败: {str(e)}",
                success=False
            )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"文件上传处理出错: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"文件上传处理出错: {str(e)}"
        )


@app.get('/uploads/{filename}')
async def get_uploaded_file(filename: str):
    """提供上传文件的访问接口"""
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(file_path)


# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器，记录错误并返回适当的响应"""
    import traceback
    error_details = traceback.format_exc()
    print(f"发生未捕获的异常: {str(exc)}\n{error_details}")
    
    return HTTPException(
        status_code=500,
        detail=f"服务器内部错误: {str(exc)}"
    )


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=5000) 