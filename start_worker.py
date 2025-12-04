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
