#!/usr/bin/env python
"""
RQ Worker启动脚本
用于启动后台任务处理进程
"""
import sys
from rq import Worker
from src.tasks.queue_config import (
    redis_conn,
    image_analysis_queue,
    answer_generation_queue,
    full_query_queue,
    check_redis_connection
)


def main():
    """启动Worker"""
    # 检查Redis连接
    if not check_redis_connection():
        print("错误: 无法连接到Redis，请确保Redis服务已启动")
        print("启动Redis: redis-server")
        sys.exit(1)
    
    print("=" * 60)
    print("RQ Worker 启动中...")
    print("=" * 60)
    print(f"监听队列:")
    print(f"  - image_analysis (图片分析)")
    print(f"  - answer_generation (答案生成)")
    print(f"  - full_query (完整查询)")
    print("=" * 60)
    
    # 🚀 预加载RAG系统模型（避免第一次任务时加载）
    print("\n🔄 预加载RAG系统模型...")
    print("  这可能需要几秒钟，请稍候...")
    try:
        import time
        start_time = time.time()
        
        from src.tasks.image_tasks import get_rag_system
        rag = get_rag_system()
        
        elapsed = time.time() - start_time
        print(f"✓ RAG系统预加载完成！耗时: {elapsed:.2f}秒")
        print("  - 所有模型已加载到内存")
        print("  - 后续任务将直接使用已加载的模型")
        print("  - 第一个请求不再需要等待模型加载")
    except Exception as e:
        print(f"⚠ RAG系统预加载失败: {e}")
        print("  Worker将在第一次任务时加载模型")
        import traceback
        traceback.print_exc()
    
    print("=" * 60)
    print("✓ Worker已就绪，等待任务...")
    print("按 Ctrl+C 停止Worker")
    print("=" * 60)
    
    # 创建Worker，监听多个队列
    # 队列优先级：image_analysis > answer_generation > full_query
    worker = Worker(
        queues=[image_analysis_queue, answer_generation_queue, full_query_queue],
        connection=redis_conn,
        name='rag-worker-1'
    )
    
    # 启动Worker
    worker.work(with_scheduler=True)


if __name__ == '__main__':
    main()
