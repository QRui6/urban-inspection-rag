"""
Redis队列配置
"""
import os
from redis import Redis
from rq import Queue

# Redis连接配置
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB = int(os.environ.get("REDIS_DB", 0))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", None)

# 创建Redis连接
redis_conn = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=False  # RQ需要bytes模式
)

# 创建任务队列
# 可以创建多个队列，设置不同优先级
image_analysis_queue = Queue('image_analysis', connection=redis_conn, default_timeout='10m')
answer_generation_queue = Queue('answer_generation', connection=redis_conn, default_timeout='10m')
full_query_queue = Queue('full_query', connection=redis_conn, default_timeout='15m')

# 队列配置
QUEUE_CONFIG = {
    "image_analysis": {
        "queue": image_analysis_queue,
        "timeout": 600,  # 10分钟
        "description": "图片分析队列"
    },
    "answer_generation": {
        "queue": answer_generation_queue,
        "timeout": 600,
        "description": "答案生成队列"
    },
    "full_query": {
        "queue": full_query_queue,
        "timeout": 900,  # 15分钟
        "description": "完整查询队列"
    }
}


def get_queue(queue_name: str = "image_analysis") -> Queue:
    """获取指定队列"""
    config = QUEUE_CONFIG.get(queue_name)
    if not config:
        raise ValueError(f"未知的队列名称: {queue_name}")
    return config["queue"]


def check_redis_connection() -> bool:
    """检查Redis连接是否正常"""
    try:
        redis_conn.ping()
        print("✓ Redis连接正常")
        return True
    except Exception as e:
        print(f"✗ Redis连接失败: {e}")
        return False
