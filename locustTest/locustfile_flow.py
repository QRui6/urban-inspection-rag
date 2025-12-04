"""
测试两阶段流程: analyze-image -> complete-answer
"""
import json
import random
from locust import HttpUser, task, between, SequentialTaskSet


class TwoStageFlow(SequentialTaskSet):
    """两阶段流程任务"""
    
    session_id = None
    
    @task
    def step1_analyze_image(self):
        """第一步: 分析图片"""
        if not self.user.test_image_base64:
            self.interrupt()
            return
        
        query = random.choice(self.user.test_queries)
        
        with self.client.post(
            "/api/analyze-image",
            json={
                "query": query,
                "image_base64": self.user.test_image_base64
            },
            catch_response=True,
            name="1-analyze-image"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    self.session_id = data.get("session_id")
                    response.success()
                else:
                    response.failure("分析失败")
                    self.interrupt()
            else:
                response.failure(f"状态码: {response.status_code}")
                self.interrupt()
    
    @task
    def step2_complete_answer(self):
        """第二步: 完成回答"""
        if not self.session_id:
            self.interrupt()
            return
        
        with self.client.post(
            "/api/complete-answer",
            json={
                "session_id": self.session_id
            },
            catch_response=True,
            name="2-complete-answer"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    response.success()
                else:
                    response.failure("生成回答失败")
            else:
                response.failure(f"状态码: {response.status_code}")


class FlowUser(HttpUser):
    """流程测试用户"""
    
    wait_time = between(2, 5)
    tasks = [TwoStageFlow]
    
    test_queries = [
        "这张图片中有什么安全隐患？",
        "请分析图片中的城市体检问题",
        "图片中的设施是否符合规范？",
    ]
    
    test_image_base64 = None
    
    def on_start(self):
        """启动时读取图片"""
        try:
            with open('test_image_base64.txt', 'r') as f:
                self.test_image_base64 = f.read().strip()
        except:
            print("警告: 无法读取 test_image_base64.txt")
