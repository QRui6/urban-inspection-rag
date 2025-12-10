"""
RAG系统异步API服务
完全兼容api.py的接口，但内部使用Redis + RQ实现异步任务处理
"""
import os
import time
import json
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from werkzeug.utils import secure_filename
from rq.job import Job
import asyncio

# 导入任务和队列配置
from src.tasks.queue_config import (
    redis_conn,
    check_redis_connection,
    image_analysis_queue,
    answer_generation_queue,
    full_query_queue,
)
from src.tasks.image_tasks import (
    analyze_image_task,
    complete_answer_task,
    full_query_task,
)
from src.utils.image_tools import image_to_base64

# 创建FastAPI应用
app = FastAPI(
    title="RAG系统API",
    description="城市体检RAG系统的REST API接口（异步实现）",
    version="2.0.0"
)

# 启用CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 上传文件配置
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 挂载静态文件服务
app.mount("/uploads", StaticFiles(directory=UPLOAD_FOLDER), name="uploads")

# 会话存储（与api.py保持一致）
session_store: Dict[str, Dict[str, Any]] = {}


# ==================== Pydantic模型定义（与api.py完全一致）====================

class HealthResponse(BaseModel):
    status: str
    timestamp: float


class AnalyzeImageRequest(BaseModel):
    query: str
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    use_structured_output: Optional[bool] = True


class AnalyzeImageResponse(BaseModel):
    session_id: str
    status: str
    visual_analysis: str
    models_used: Dict[str, Optional[str]]
    timestamp: float
    is_structured: bool = False


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


# ==================== API端点（与api.py接口完全一致）====================

@app.on_event("startup")
async def startup_event():
    """启动时检查Redis连接"""
    if not check_redis_connection():
        print("警告: Redis连接失败，异步任务功能将不可用")


@app.get('/api/health', response_model=HealthResponse)
async def health_check():
    """健康检查接口"""
    return HealthResponse(
        status="ok",
        timestamp=time.time()
    )


@app.post('/api/analyze-image', response_model=AnalyzeImageResponse)
async def analyze_image(request: AnalyzeImageRequest):
    """
    图片分析接口（与api.py完全兼容）
    接收问题和图片URL或base64数据，只执行视觉模型分析，立即返回结果
    内部使用异步队列处理，但对前端表现为同步
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
        
        # 提交任务到异步队列
        use_structured = request.use_structured_output if request.use_structured_output is not None else True
        
        job = image_analysis_queue.enqueue(
            analyze_image_task,
            session_id=session_id,
            query=request.query,
            img_input=img_input,
            use_structured_output=use_structured,
            job_timeout='10m',
            result_ttl=3600
        )
        
        # 等待任务完成（最多等待5分钟）
        max_wait = 300
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            job.refresh()
            
            if job.is_finished:
                result = job.result
                
                if result.get("status") == "success":
                    vl_text = result.get("visual_analysis")
                    
                    # 处理visual_analysis格式（与api.py保持一致）
                    if isinstance(vl_text, dict):
                        visual_analysis = json.dumps(vl_text, ensure_ascii=False)
                        visual_analysis = visual_analysis.replace("indicator_classification", "指标分类")
                        visual_analysis = visual_analysis.replace("specific_problem", "具体问题")
                        visual_analysis = visual_analysis.replace("detailed_description", "详细描述")
                    else:
                        visual_analysis = vl_text
                    
                    # 保存分析结果到会话存储（与api.py保持一致）
                    session_store[session_id] = {
                        "visual_analysis": vl_text,  # 保存原始数据
                        "query": request.query,
                        "img_input": img_input,
                        "timestamp": time.time()
                    }
                    
                    # 返回与api.py完全一致的格式
                    return AnalyzeImageResponse(
                        session_id=session_id,
                        status="success",
                        visual_analysis=visual_analysis,
                        models_used=result.get("models_used", {"vision": None, "language": None}),
                        timestamp=time.time(),
                        is_structured=use_structured
                    )
                else:
                    raise HTTPException(
                        status_code=500,
                        detail="无法识别图片内容"
                    )
            
            elif job.is_failed:
                raise HTTPException(
                    status_code=500,
                    detail=f"任务处理失败: {str(job.exc_info) if job.exc_info else '未知错误'}"
                )
            
            await asyncio.sleep(1)
        
        raise HTTPException(
            status_code=504,
            detail="任务处理超时，请稍后重试"
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
    """
    完成回答接口（与api.py完全兼容）
    接收会话ID，基于之前的视觉分析结果生成最终回答
    内部使用异步队列处理，但对前端表现为同步
    """
    try:
        # 检查会话是否存在（与api.py保持一致）
        if request.session_id not in session_store:
            raise HTTPException(
                status_code=404,
                detail="会话已过期或不存在"
            )
        
        # 获取会话数据（与api.py保持一致）
        session_data = session_store[request.session_id]
        visual_analysis = session_data["visual_analysis"]
        query_text = session_data["query"]
        img_input = session_data["img_input"]
        
        # 提交任务到异步队列
        job = answer_generation_queue.enqueue(
            complete_answer_task,
            session_id=request.session_id,
            query=query_text,
            img_input=img_input,
            visual_analysis=visual_analysis,
            job_timeout='10m',
            result_ttl=3600
        )
        
        # 等待任务完成（最多等待5分钟）
        max_wait = 300
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            job.refresh()
            
            if job.is_finished:
                result = job.result
                
                # 清理会话存储（与api.py保持一致）
                if request.session_id in session_store:
                    del session_store[request.session_id]
                
                # 返回与api.py完全一致的格式
                return CompleteAnswerResponse(
                    status=result.get("status", "success"),
                    answer=result.get("answer", ""),
                    models_used=result.get("models_used", {}),
                    timestamp=time.time()
                )
            
            elif job.is_failed:
                raise HTTPException(
                    status_code=500,
                    detail=f"任务处理失败: {str(job.exc_info) if job.exc_info else '未知错误'}"
                )
            
            await asyncio.sleep(1)
        
        raise HTTPException(
            status_code=504,
            detail="任务处理超时，请稍后重试"
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
    """
    完整查询接口（与api.py完全兼容）
    接收问题和可选的图片，一次性完成分析和答案生成
    内部使用异步队列处理，但对前端表现为同步
    注意：此接口会等待较长时间（约25秒），推荐使用两步调用方式
    """
    try:
        # 生成任务ID
        task_id = str(time.time())
        
        # 选择图片输入源（与api.py保持一致）
        img_input = None
        if request.image_base64 and request.image_base64.startswith('data:image'):
            img_input = request.image_base64
            print("使用base64图片数据进行问答")
        elif request.image_url:
            img_input = request.image_url
            print(f"使用图片URL进行问答: {request.image_url}")
        else:
            print("执行纯文本问答")
        
        # 提交任务到异步队列
        job = full_query_queue.enqueue(
            full_query_task,
            task_id=task_id,
            query=request.query,
            img_input=img_input,
            job_timeout='15m',
            result_ttl=3600
        )
        
        # 等待任务完成（最多等待15分钟）
        max_wait = 900
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            job.refresh()
            
            if job.is_finished:
                result = job.result
                
                # 返回与api.py完全一致的格式
                return QueryResponse(
                    status=result.get("status", "success"),
                    timestamp=time.time(),
                    visual_analysis=result.get("visual_analysis"),
                    models_used=result.get("models_used"),
                    answer=result.get("answer")
                )
            
            elif job.is_failed:
                raise HTTPException(
                    status_code=500,
                    detail=f"任务处理失败: {str(job.exc_info) if job.exc_info else '未知错误'}"
                )
            
            await asyncio.sleep(1)
        
        raise HTTPException(
            status_code=504,
            detail="任务处理超时，请稍后重试"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"处理查询请求时出错: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"处理查询请求时出错: {str(e)}"
        )


@app.post('/api/upload', response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """文件上传接口（与api.py完全一致）"""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="未选择文件")
        
        if not allowed_file(file.filename):
            raise HTTPException(status_code=400, detail="不支持的文件类型")
        
        filename = secure_filename(file.filename)
        timestamp = int(time.time())
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        content = await file.read()
        with open(filepath, "wb") as f:
            f.write(content)
        
        file_url = f"/uploads/{unique_filename}"
        
        try:
            base64_data = image_to_base64(filepath)
            if base64_data:
                return UploadResponse(
                    file_url=file_url,
                    base64=base64_data,
                    filename=filename,
                    success=True
                )
        except Exception as e:
            print(f"转换base64出错: {e}")
            return UploadResponse(
                file_url=file_url,
                filename=filename,
                error=f"Base64转换失败: {str(e)}",
                success=False
            )
        
    except HTTPException:
        raise
    except Exception as e:
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


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=5000)
