#!/usr/bin/env python
"""
异步API测试脚本
演示如何使用异步接口
"""
import requests
import time
import json


BASE_URL = "http://localhost:5001"


def test_health():
    """测试健康检查"""
    print("\n" + "="*60)
    print("1. 测试健康检查")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/api/health")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.json()["redis_connected"]


def test_async_analyze_image():
    """测试异步图片分析"""
    print("\n" + "="*60)
    print("2. 测试异步图片分析")
    print("="*60)
    
    # 准备测试数据
    test_data = {
        "query": "这张图片有什么安全隐患？",
        "image_url": "test_image.jpg",  # 替换为实际图片路径
        "use_structured_output": True
    }
    
    # 提交任务
    print("提交任务...")
    response = requests.post(
        f"{BASE_URL}/api/async/analyze-image",
        json=test_data
    )
    
    if response.status_code != 200:
        print(f"❌ 提交失败: {response.text}")
        return None
    
    result = response.json()
    task_id = result["task_id"]
    print(f"✓ 任务已提交")
    print(f"  Task ID: {task_id}")
    print(f"  预计时间: {result['estimated_time']}秒")
    
    # 轮询任务状态
    print("\n轮询任务状态...")
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        time.sleep(2)  # 每2秒查询一次
        
        status_response = requests.get(f"{BASE_URL}/api/async/task/{task_id}")
        status = status_response.json()
        
        print(f"  [{attempt}] 状态: {status['status']}", end="")
        
        if status["status"] == "finished":
            print(" ✓")
            print("\n任务完成！")
            print(json.dumps(status["result"], indent=2, ensure_ascii=False))
            return status["result"]
        elif status["status"] == "failed":
            print(" ✗")
            print(f"任务失败: {status.get('error')}")
            return None
        else:
            print(f" (进度: {status.get('progress', 0)}%)")
    
    print("\n⚠ 超时：任务未在预期时间内完成")
    return None


def test_queue_stats():
    """测试队列统计"""
    print("\n" + "="*60)
    print("3. 查看队列统计")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/api/queue/stats")
    stats = response.json()
    
    print(json.dumps(stats, indent=2, ensure_ascii=False))


def test_concurrent_requests():
    """测试并发请求"""
    print("\n" + "="*60)
    print("4. 测试并发请求（5个并发）")
    print("="*60)
    
    import concurrent.futures
    
    def submit_task(i):
        """提交单个任务"""
        data = {
            "query": f"测试查询 {i}",
            "image_url": "test_image.jpg"
        }
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/async/analyze-image",
            json=data
        )
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            task_id = response.json()["task_id"]
            print(f"  任务 {i}: 提交成功 (耗时: {elapsed:.3f}秒) - Task ID: {task_id}")
            return task_id
        else:
            print(f"  任务 {i}: 提交失败")
            return None
    
    # 并发提交5个任务
    print("并发提交5个任务...")
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        task_ids = list(executor.map(submit_task, range(1, 6)))
    
    total_time = time.time() - start_time
    print(f"\n✓ 5个任务提交完成，总耗时: {total_time:.3f}秒")
    print(f"  平均每个任务: {total_time/5:.3f}秒")
    
    # 查看队列状态
    time.sleep(1)
    test_queue_stats()


def main():
    """主测试流程"""
    print("\n" + "="*60)
    print("异步API测试")
    print("="*60)
    
    # 1. 健康检查
    redis_ok = test_health()
    if not redis_ok:
        print("\n❌ Redis未连接，请先启动Redis和Worker")
        print("   启动命令: ./start_async_system.sh")
        return
    
    # 2. 测试异步图片分析
    # test_async_analyze_image()
    
    # 3. 测试队列统计
    test_queue_stats()
    
    # 4. 测试并发
    test_concurrent_requests()
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)


if __name__ == "__main__":
    main()
