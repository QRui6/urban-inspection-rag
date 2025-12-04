"""
API密钥管理器
支持多密钥轮询、负载均衡、失败重试
"""
import time
import threading
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class APIKeyStatus:
    """API密钥状态"""
    key: str
    name: str
    active_requests: int = 0  # 当前活跃请求数
    total_requests: int = 0   # 总请求数
    failed_requests: int = 0  # 失败请求数
    last_used: Optional[datetime] = None
    last_error: Optional[str] = None
    is_available: bool = True  # 是否可用
    cooldown_until: Optional[datetime] = None  # 冷却时间


class APIKeyManager:
    """
    API密钥管理器
    支持多密钥轮询、负载均衡、失败重试
    """
    
    def __init__(self, api_keys: List[Dict[str, str]], max_concurrent_per_key: int = 3):
        """
        初始化API密钥管理器
        
        Args:
            api_keys: API密钥列表，格式: [{"name": "key1", "key": "xxx"}, ...]
            max_concurrent_per_key: 每个密钥的最大并发数
        """
        self.api_keys = {
            key_info["name"]: APIKeyStatus(
                key=key_info["key"],
                name=key_info["name"]
            )
            for key_info in api_keys
        }
        self.max_concurrent_per_key = max_concurrent_per_key
        self.lock = threading.Lock()
        self.current_index = 0
        
        print(f"✓ API密钥管理器初始化完成，共 {len(self.api_keys)} 个密钥")
    
    def get_available_key(self, strategy: str = "round_robin") -> Optional[Tuple[str, str]]:
        """
        获取可用的API密钥
        
        Args:
            strategy: 选择策略
                - "round_robin": 轮询（默认）
                - "least_loaded": 最少负载
                - "random": 随机
        
        Returns:
            (key_name, api_key) 或 None
        """
        with self.lock:
            # 过滤可用的密钥
            available_keys = [
                (name, status) 
                for name, status in self.api_keys.items()
                if self._is_key_available(status)
            ]
            
            if not available_keys:
                print("⚠ 所有API密钥都不可用或已达到并发限制")
                return None
            
            # 根据策略选择密钥
            if strategy == "least_loaded":
                # 选择负载最少的密钥
                name, status = min(available_keys, key=lambda x: x[1].active_requests)
            elif strategy == "random":
                # 随机选择
                import random
                name, status = random.choice(available_keys)
            else:  # round_robin
                # 轮询选择
                self.current_index = (self.current_index + 1) % len(available_keys)
                name, status = available_keys[self.current_index]
            
            # 更新状态
            status.active_requests += 1
            status.total_requests += 1
            status.last_used = datetime.now()
            
            print(f"✓ 选择API密钥: {name} (活跃请求: {status.active_requests}/{self.max_concurrent_per_key})")
            return name, status.key
    
    def release_key(self, key_name: str, success: bool = True, error: Optional[str] = None):
        """
        释放API密钥
        
        Args:
            key_name: 密钥名称
            success: 是否成功
            error: 错误信息
        """
        with self.lock:
            if key_name not in self.api_keys:
                return
            
            status = self.api_keys[key_name]
            status.active_requests = max(0, status.active_requests - 1)
            
            if not success:
                status.failed_requests += 1
                status.last_error = error
                
                # 如果失败率过高，暂时禁用该密钥
                if status.total_requests > 10:
                    failure_rate = status.failed_requests / status.total_requests
                    if failure_rate > 0.5:  # 失败率超过50%
                        status.is_available = False
                        status.cooldown_until = datetime.now() + timedelta(minutes=5)
                        print(f"⚠ API密钥 {key_name} 失败率过高，暂时禁用5分钟")
            
            print(f"✓ 释放API密钥: {key_name} (活跃请求: {status.active_requests})")
    
    def _is_key_available(self, status: APIKeyStatus) -> bool:
        """检查密钥是否可用"""
        # 检查是否在冷却期
        if status.cooldown_until and datetime.now() < status.cooldown_until:
            return False
        
        # 检查是否被标记为不可用
        if not status.is_available:
            # 冷却期结束，重新启用
            if status.cooldown_until and datetime.now() >= status.cooldown_until:
                status.is_available = True
                status.cooldown_until = None
                status.failed_requests = 0  # 重置失败计数
                print(f"✓ API密钥 {status.name} 冷却期结束，重新启用")
            else:
                return False
        
        # 检查并发数
        return status.active_requests < self.max_concurrent_per_key
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        with self.lock:
            stats = {}
            for name, status in self.api_keys.items():
                stats[name] = {
                    "active_requests": status.active_requests,
                    "total_requests": status.total_requests,
                    "failed_requests": status.failed_requests,
                    "success_rate": (
                        (status.total_requests - status.failed_requests) / status.total_requests * 100
                        if status.total_requests > 0 else 100
                    ),
                    "is_available": status.is_available,
                    "last_used": status.last_used.isoformat() if status.last_used else None,
                    "last_error": status.last_error
                }
            return stats
    
    def reset_key(self, key_name: str):
        """重置密钥状态"""
        with self.lock:
            if key_name in self.api_keys:
                status = self.api_keys[key_name]
                status.is_available = True
                status.cooldown_until = None
                status.failed_requests = 0
                status.last_error = None
                print(f"✓ 重置API密钥: {key_name}")


class APIKeyPool:
    """
    API密钥池（简化版）
    用于快速集成到现有代码
    """
    
    def __init__(self, api_keys: List[str], max_concurrent_per_key: int = 3):
        """
        初始化API密钥池
        
        Args:
            api_keys: API密钥列表
            max_concurrent_per_key: 每个密钥的最大并发数
        """
        key_configs = [
            {"name": f"key_{i+1}", "key": key}
            for i, key in enumerate(api_keys)
        ]
        self.manager = APIKeyManager(key_configs, max_concurrent_per_key)
    
    def acquire(self) -> Optional[str]:
        """获取一个可用的API密钥"""
        result = self.manager.get_available_key()
        if result:
            return result[1]  # 返回密钥
        return None
    
    def release(self, key: str, success: bool = True, error: Optional[str] = None):
        """释放API密钥"""
        # 找到对应的key_name
        for name, status in self.manager.api_keys.items():
            if status.key == key:
                self.manager.release_key(name, success, error)
                break
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.manager.get_statistics()


# 使用示例
if __name__ == "__main__":
    # 示例1: 使用APIKeyManager
    api_keys = [
        {"name": "火山引擎-主账号", "key": "key_1"},
        {"name": "火山引擎-子账号1", "key": "key_2"},
        {"name": "火山引擎-子账号2", "key": "key_3"},
    ]
    
    manager = APIKeyManager(api_keys, max_concurrent_per_key=2)
    
    # 获取密钥
    key_name, api_key = manager.get_available_key()
    print(f"获取到密钥: {key_name}")
    
    # 使用密钥...
    
    # 释放密钥
    manager.release_key(key_name, success=True)
    
    # 查看统计
    print(manager.get_statistics())
    
    # 示例2: 使用APIKeyPool（简化版）
    pool = APIKeyPool(["key_1", "key_2", "key_3"])
    
    key = pool.acquire()
    # 使用key...
    pool.release(key, success=True)
