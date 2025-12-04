"""
单接口测试 - 只测试完整流程 (analyze-image + complete-answer)
"""
import json
import time
import random
from locust import HttpUser, task, between


class FlowOnlyUser(HttpUser):
    """只测试完整流程"""
    
    wait_time = between(1, 3)
    
    test_queries = [
        "城市体检的主要内容是什么？",
        "如何评估城市安全隐患？",
        "城市基础设施检查包括哪些方面？",
    ]
    
    test_image_base64 = None
    
    def on_start(self):
        """启动时读取图片"""
        try:
            with open('test_image_base64.txt', 'r') as f:
                self.test_image_base64 = f.read().strip()
        except:
            print("警告: 无法读取 test_image_base64.txt")
    
    @task(1)
    def test_complete_flow(self):
        """测试完整流程：analyze-image + complete-answer"""
        if not self.test_image_base64:
            return
        
        query = random.choice(self.test_queries)
        
        # 步骤1: 图片分析
        response1 = self.client.post(
            "/api/analyze-image",
            json={
                "query": query,
                "image_base64": self.test_image_base64,
            },
            name="步骤1: analyze-image"
        )
        
        if response1.status_code != 200:
            return
        
        session_id = response1.json().get("session_id")
        if not session_id:
            return
        
        time.sleep(0.5)  # 模拟用户查看结果
        
        # 步骤2: 生成完整答案
        with self.client.post(
            "/api/complete-answer",
            json={"session_id": session_id},
            catch_response=True,
            name="步骤2: complete-answer"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    response.success()
                else:
                    response.failure("返回状态异常")
            else:
                response.failure(f"状态码: {response.status_code}")
