"""
单接口测试 - 只测试 /api/query
"""
import json
import time
import random
from locust import HttpUser, task, between


class QueryOnlyUser(HttpUser):
    """只测试 /api/query 接口"""
    
    wait_time = between(1, 3)
    
    test_queries = [
        "城市体检的主要内容是什么？",
        "如何评估城市安全隐患？",
        "城市基础设施检查包括哪些方面？",
    ]
    
    # 从文件读取图片base64
    test_image_base64 = None
    
    def on_start(self):
        """启动时读取图片"""
        try:
            with open('test_image_base64.txt', 'r') as f:
                self.test_image_base64 = f.read().strip()
        except:
            print("警告: 无法读取 test_image_base64.txt")
    
    @task(1)
    def test_query(self):
        """测试 /api/query"""
        if not self.test_image_base64:
            return
        
        query = random.choice(self.test_queries)
        
        with self.client.post(
            "/api/query",
            json={
                "query": query,
                "image_base64": self.test_image_base64
            },
            catch_response=True,
            name="/api/query"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    response.success()
                else:
                    response.failure("返回状态异常")
            else:
                response.failure(f"状态码: {response.status_code}")
