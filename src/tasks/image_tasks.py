"""
异步图片分析任务
使用RQ (Redis Queue) 实现后台任务处理
"""
import os
import json
import time
from typing import Dict, Any, Optional
from main import RAGSystem
from config.config import PROMPT_CONFIG


def analyze_image_task(
    session_id: str,
    query: str,
    img_input: str,
    use_structured_output: bool = True
) -> Dict[str, Any]:
    """
    后台异步执行图片分析任务
    
    Args:
        session_id: 会话ID
        query: 用户问题
        img_input: 图片输入（URL或base64）
        use_structured_output: 是否使用结构化输出
        
    Returns:
        分析结果字典
    """
    try:
        print(f"[Task {session_id}] 开始处理图片分析任务...")
        start_time = time.time()
        
        # 初始化RAG系统
        rag = RAGSystem()
        
        # 执行视觉分析
        vl_prompt = PROMPT_CONFIG["vision_analysis"]["city_inspection"]
        vl_text, model_used = rag.analyze_image(img_input, vl_prompt, use_structured_output)
        
        # 处理分析结果
        if isinstance(vl_text, dict):
            visual_analysis = json.dumps(vl_text, ensure_ascii=False)
            visual_analysis = visual_analysis.replace("indicator_classification", "指标分类")
            visual_analysis = visual_analysis.replace("specific_problem", "具体问题")
            visual_analysis = visual_analysis.replace("detailed_description", "详细描述")
        else:
            visual_analysis = vl_text
        
        elapsed_time = time.time() - start_time
        print(f"[Task {session_id}] 图片分析完成，耗时: {elapsed_time:.2f}秒")
        
        return {
            "status": "success",
            "session_id": session_id,
            "visual_analysis": visual_analysis,
            "models_used": {
                "vision": model_used,
                "language": None
            },
            "is_structured": use_structured_output,
            "elapsed_time": elapsed_time
        }
        
    except Exception as e:
        print(f"[Task {session_id}] 图片分析失败: {str(e)}")
        return {
            "status": "error",
            "session_id": session_id,
            "error": str(e),
            "visual_analysis": None
        }


def complete_answer_task(
    session_id: str,
    query: str,
    img_input: str,
    visual_analysis: str
) -> Dict[str, Any]:
    """
    后台异步执行完整答案生成任务
    
    Args:
        session_id: 会话ID
        query: 用户问题
        img_input: 图片输入
        visual_analysis: 视觉分析结果
        
    Returns:
        完整答案字典
    """
    try:
        print(f"[Task {session_id}] 开始生成完整答案...")
        start_time = time.time()
        
        # 初始化RAG系统
        rag = RAGSystem()
        
        # 生成完整答案
        response = rag.complete_answer(query, img_input, visual_analysis)
        
        elapsed_time = time.time() - start_time
        print(f"[Task {session_id}] 答案生成完成，耗时: {elapsed_time:.2f}秒")
        
        response["elapsed_time"] = elapsed_time
        return response
        
    except Exception as e:
        print(f"[Task {session_id}] 答案生成失败: {str(e)}")
        return {
            "status": "error",
            "session_id": session_id,
            "error": str(e),
            "answer": None
        }


def full_query_task(
    task_id: str,
    query: str,
    img_input: Optional[str] = None
) -> Dict[str, Any]:
    """
    后台异步执行完整查询任务（包含图片分析和答案生成）
    
    Args:
        task_id: 任务ID
        query: 用户问题
        img_input: 可选的图片输入
        
    Returns:
        完整查询结果
    """
    try:
        print(f"[Task {task_id}] 开始处理完整查询任务...")
        start_time = time.time()
        
        # 初始化RAG系统
        rag = RAGSystem()
        
        # 执行查询
        response = rag.query(query, img_input)
        
        elapsed_time = time.time() - start_time
        print(f"[Task {task_id}] 查询完成，耗时: {elapsed_time:.2f}秒")
        
        response["elapsed_time"] = elapsed_time
        response["task_id"] = task_id
        return response
        
    except Exception as e:
        print(f"[Task {task_id}] 查询失败: {str(e)}")
        return {
            "status": "error",
            "task_id": task_id,
            "error": str(e),
            "answer": None
        }
