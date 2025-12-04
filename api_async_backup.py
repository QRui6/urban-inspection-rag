"""
RAG系统异步API服务
使用Redis + RQ实现异步任务处理
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

# 导入任务和队列配置
from src.tasks.queue_config import (
    redis_conn, 
    get_queue, 
    check_redis_connection,
    image_analysis_queue,
    answer_generation_queue,
    full_query_queue
)
from src.tasks.image_tasks import (
    analyze_image_task,
    complete_answer_task,
    full_query_task
)
from src.utils.image_tools import image_to_base64
from config.config import PROMPT_CONFIG

# 创建FastAPI应用
app = FastAPI(
    title="RAG系统异步API",
    description="城市体检RAG系统的异步REST API接口（基于Redis + RQ）",
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

# 会话存储（用于保存视觉分析结果）
session_store: Dict[str, Dict[str, Any]] = {}


# ==================== Pydantic模型定义 ====================

class HealthResponse(BaseModel):
    status: str
    timestamp: float
    redis_connected: bool


class TaskSubmitResponse(BaseModel):
    task_id: str
    status: str
    message: str
    estimated_time: Optional[int] = None  # 预计完成时间（秒）


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # queued, started, finished, failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: Optional[int] = None  # 进度百分比
    elapsed_time: Optional[float] = None


class AnalyzeImageRequest(BaseModel):
    query: str
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    use_structured_output: Optional[bool] = True


class CompleteAnswerRequest(BaseModel):
    session_id: str


class QueryRequest(BaseModel):
    query: str
    image_url: Optional[str] = None
    image_base64: Optional[str] = None


class UploadResponse(BaseModel):
    file_url: Optional[str] = None
    base64: Optional[str] = None
    filename: str
    success: bool
    error: Optional[str] = None


# ==================== 辅助函数 ====================

def allowed_file(filename: str) -> bool:
    """检查文件类型是否允许上传"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_job_status(job: Job) -> TaskStatusResponse:
    """获取任务状态"""
    if job.is_finished:
        return TaskStatusResponse(
            task_id=job.id,
            status="finished",
            result=job.result,
            elapsed_time=job.ended_at.timestamp() - job.started_at.timestamp() if job.ended_at and job.started_at else None
        )
    elif job.is_failed:
        return TaskStatusResponse(
            task_id=job.id,
            status="failed",
            error=str(job.exc_info) if job.exc_info else "Unknown error"
        )
    elif job.is_started:
        return TaskStatusResponse(
            task_id=job.id,
            status="started",
            progress=50  # 可以根据实际情况调整
        )
    else:  # queued
        return TaskStatusResponse(
            task_id=job.id,
            status="queued",
            progress=0
        )


# ==================== API端点 ====================

@app.on_event("startup")
async def startup_event():
    """启动时检查Redis连接"""
    if not check_redis_connection():
        print("警告: Redis连接失败，异步任务功能将不可用")


@app.get('/api/health', response_model=HealthResponse)
async def health_check():
    """健康检查接口"""
    redis_ok = check_redis_connection()
    return HealthResponse(
        status="ok" if redis_ok else "degraded",
        timestamp=time.time(),
        redis_connected=redis_ok
    )


@app.post('/api/async/analyze-image', response_model=TaskSubmitResponse)
async def analyze_image(request: AnalyzeImageRequest):
    """
    纯异步图片分析接口
    立即返回task_id，客户端需要轮询获取结果
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
        
        # 提交任务到队列
        job = image_analysis_queue.enqueue(
            analyze_image_task,
            session_id=session_id,
            query=request.query,
            img_input=img_input,
            use_structured_output=request.use_structured_output,
            job_timeout='10m',
            result_ttl=3600  # 结果保留1小时
        )
        
        # 保存会话信息（用于后续complete_answer）
        session_store[session_id] = {
            "query": request.query,
            "img_input": img_input,
            "task_id": job.id,
            "timestamp": time.time()
        }
        
        return TaskSubmitResponse(
            task_id=job.id,
            status="queued",
            message="图片分析任务已提交，请使用task_id查询结果",
            estimated_time=15  # 预计15秒
        )
        
    except Exception as e:
        print(f"提交图片分析任务失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"提交任务失败: {str(e)}"
        )


@app.post('/api/async/complete-answer', response_model=TaskSubmitResponse)
async def complete_answer(request: CompleteAnswerRequest):
    """
    纯异步完成答案生成接口
    基于之前的视觉分析结果生成最终回答
    """
    try:
        # 检查会话是否存在
        if request.session_id not in session_store:
            raise HTTPException(
                status_code=404,
                detail="会话已过期或不存在"
            )
        
        session_data = session_store[request.session_id]
        
        # 检查视觉分析任务是否完成
        analyze_task_id = session_data.get("task_id")
        if analyze_task_id:
            try:
                analyze_job = Job.fetch(analyze_task_id, connection=redis_conn)
                if not analyze_job.is_finished:
                    raise HTTPException(
                        status_code=400,
                        detail="图片分析任务尚未完成，请稍后再试"
                    )
                
                # 获取视觉分析结果
                analyze_result = analyze_job.result
                if analyze_result.get("status") != "success":
                    raise HTTPException(
                        status_code=500,
                        detail="图片分析失败，无法生成答案"
                    )
                
                visual_analysis = analyze_result.get("visual_analysis")
                
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"获取视觉分析结果失败: {str(e)}"
                )
        else:
            raise HTTPException(
                status_code=400,
                detail="未找到对应的图片分析任务"
            )
        
        # 提交答案生成任务
        job = answer_generation_queue.enqueue(
            complete_answer_task,
            session_id=request.session_id,
            query=session_data["query"],
            img_input=session_data["img_input"],
            visual_analysis=visual_analysis,
            job_timeout='10m',
            result_ttl=3600
        )
        
        return TaskSubmitResponse(
            task_id=job.id,
            status="queued",
            message="答案生成任务已提交，请使用task_id查询结果",
            estimated_time=10
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"提交答案生成任务失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"提交任务失败: {str(e)}"
        )


@app.post('/api/query', response_model=TaskSubmitResponse)
async def query(request: QueryRequest):
    """
    异步完整查询接口
    一次性提交包含图片分析和答案生成的完整任务
    """
    try:
        # 生成任务ID
        task_id = f"query_{int(time.time() * 1000)}"
        
        # 处理图片输入
        img_input = None
        if request.image_base64:
            img_input = request.image_base64
        elif request.image_url:
            img_input = request.image_url
        
        # 提交完整查询任务
        job = full_query_queue.enqueue(
            full_query_task,
            task_id=task_id,
            query=request.query,
            img_input=img_input,
            job_timeout='15m',
            result_ttl=3600
        )
        
        estimated_time = 25 if img_input else 5
        
        return TaskSubmitResponse(
            task_id=job.id,
            status="queued",
            message="查询任务已提交，请使用task_id查询结果",
            estimated_time=estimated_time
        )
        
    except Exception as e:
        print(f"提交查询任务失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"提交任务失败: {str(e)}"
        )


@app.get('/api/task/{task_id}', response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    查询任务状态接口
    客户端应该每2-3秒轮询一次
    """
    try:
        job = Job.fetch(task_id, connection=redis_conn)
        return get_job_status(job)
        
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"任务不存在或已过期: {str(e)}"
        )


@app.delete('/api/task/{task_id}')
async def cancel_task(task_id: str):
    """取消任务"""
    try:
        job = Job.fetch(task_id, connection=redis_conn)
        job.cancel()
        return {"message": "任务已取消", "task_id": task_id}
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"任务不存在: {str(e)}"
        )


@app.post('/api/upload', response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """文件上传接口（与同步版本相同）"""
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


@app.get('/api/queue/stats')
async def get_queue_stats():
    """获取队列统计信息"""
    try:
        return {
            "image_analysis": {
                "queued": len(image_analysis_queue),
                "started": image_analysis_queue.started_job_registry.count,
                "finished": image_analysis_queue.finished_job_registry.count,
                "failed": image_analysis_queue.failed_job_registry.count
            },
            "answer_generation": {
                "queued": len(answer_generation_queue),
                "started": answer_generation_queue.started_job_registry.count,
                "finished": answer_generation_queue.finished_job_registry.count,
                "failed": answer_generation_queue.failed_job_registry.count
            },
            "full_query": {
                "queued": len(full_query_queue),
                "started": full_query_queue.started_job_registry.count,
                "finished": full_query_queue.finished_job_registry.count,
                "failed": full_query_queue.failed_job_registry.count
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取队列统计失败: {str(e)}"
        )


@app.post('/api/analyze-image')
async def analyze_image(request: AnalyzeImageRequest):
    """
    兼容旧前端的同步风格接口
    内部使用异步处理，但会等待结果返回
    """
    import asyncio
    
    try:
        if not request.image_url and not request.image_base64:
            raise HTTPException(
                status_code=400,
                detail="image_url或image_base64至少提供一项"
            )
        
        # 生成会话ID
        session_id = str(time.time())
        img_input = request.image_base64 if request.image_base64 else request.image_url
        
        # 提交任务到队列
        job = image_analysis_queue.enqueue(
            analyze_image_task,
            session_id=session_id,
            query=request.query,
            img_input=img_input,
            use_structured_output=request.use_structured_output,
            job_timeout='10m',
            result_ttl=3600
        )
        
        # 等待任务完成（最多等待5分钟）
        max_wait = 300  # 5分钟
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            job.refresh()
            
            if job.is_finished:
                result = job.result
                if result.get("status") == "success":
                    # 返回兼容旧前端的格式
                    return {
                        "session_id": result.get("session_id"),
                        "status": "success",
                        "visual_analysis": result.get("visual_analysis"),
                        "models_used": result.get("models_used"),
                        "timestamp": time.time(),
                        "is_structured": result.get("is_structured", False)
                    }
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"图片分析失败: {result.get('error', '未知错误')}"
                    )
            
            elif job.is_failed:
                raise HTTPException(
                    status_code=500,
                    detail=f"任务处理失败: {str(job.exc_info) if job.exc_info else '未知错误'}"
                )
            
            # 等待1秒后重试
            await asyncio.sleep(1)
        
        # 超时
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
            detail=f"处理请求时出错: {str(e)}"
        )


@app.post('/api/complete-answer')
async def complete_answer(request: CompleteAnswerRequest):
    """
    兼容旧前端的完成答案接口
    内部使用异步处理，但会等待结果返回
    """
    import asyncio
    
    try:
        # 检查会话是否存在
        if request.session_id not in session_store:
            raise HTTPException(
                status_code=404,
                detail="会话已过期或不存在"
            )
        
        session_data = session_store[request.session_id]
        
        # 检查视觉分析任务是否完成
        analyze_task_id = session_data.get("task_id")
        if not analyze_task_id:
            raise HTTPException(
                status_code=400,
                detail="未找到对应的图片分析任务"
            )
        
        try:
            analyze_job = Job.fetch(analyze_task_id, connection=redis_conn)
            if not analyze_job.is_finished:
                raise HTTPException(
                    status_code=400,
                    detail="图片分析任务尚未完成，请稍后再试"
                )
            
            # 获取视觉分析结果
            analyze_result = analyze_job.result
            if analyze_result.get("status") != "success":
                raise HTTPException(
                    status_code=500,
                    detail="图片分析失败，无法生成答案"
                )
            
            visual_analysis = analyze_result.get("visual_analysis")
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"获取视觉分析结果失败: {str(e)}"
            )
        
        # 提交答案生成任务
        job = answer_generation_queue.enqueue(
            complete_answer_task,
            session_id=request.session_id,
            query=session_data["query"],
            img_input=session_data["img_input"],
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
                
                # 清理会话存储
                if request.session_id in session_store:
                    del session_store[request.session_id]
                
                # 返回兼容旧前端的格式
                return {
                    "status": result.get("status", "success"),
                    "answer": result.get("answer", ""),
                    "models_used": result.get("models_used", {}),
                    "timestamp": time.time()
                }
            
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


@app.post('/api/query')
async def query(request: QueryRequest):
    """
    兼容旧前端的完整查询接口
    内部使用异步处理，但会等待结果返回
    """
    import asyncio
    
    try:
        task_id = f"query_{int(time.time() * 1000)}"
        img_input = None
        if request.image_base64:
            img_input = request.image_base64
        elif request.image_url:
            img_input = request.image_url
        
        # 提交完整查询任务
        job = full_query_queue.enqueue(
            full_query_task,
            task_id=task_id,
            query=request.query,
            img_input=img_input,
            job_timeout='15m',
            result_ttl=3600
        )
        
        # 等待任务完成（最多等待10分钟）
        max_wait = 600
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            job.refresh()
            
            if job.is_finished:
                result = job.result
                return {
                    "status": result.get("status", "success"),
                    "timestamp": time.time(),
                    "visual_analysis": result.get("visual_analysis"),
                    "models_used": result.get("models_used"),
                    "answer": result.get("answer")
                }
            
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
            detail=f"处理请求时出错: {str(e)}"
        )


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=5000)  # 异步API使用5000端口
