#!/usr/bin/env python
"""
测试异步版本的 /api/query 接口
"""
import requests
import json
import time


def test_query_with_image():
    """测试带图片的完整查询"""
    print("=" * 60)
    print("测试 /api/query 接口（带图片）")
    print("=" * 60)
    
    # 准备测试数据
    url = "http://localhost:5000/api/query"
    
    # 使用一个测试图片URL或base64
    payload = {
        "query": "这张图片有什么问题？",
        "image_url": "test.jpg"  # 替换为实际的图片路径
    }
    
    print(f"\n发送请求到: {url}")
    print(f"查询内容: {payload['query']}")
    
    start_time = time.time()
    
    try:
        response = requests.post(url, json=payload, timeout=300)
        elapsed = time.time() - start_time
        
        print(f"\n✓ 请求完成，耗时: {elapsed:.2f}秒")
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n响应内容:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            print("\n✓ 测试成功！")
            print(f"  - 状态: {result.get('status')}")
            print(f"  - 视觉分析: {result.get('visual_analysis', '无')[:100]}...")
            print(f"  - 答案: {result.get('answer', '无')[:100]}...")
        else:
            print(f"\n✗ 请求失败: {response.text}")
            
    except requests.exceptions.Timeout:
        print("\n✗ 请求超时（超过5分钟）")
    except Exception as e:
        print(f"\n✗ 请求出错: {e}")


def test_query_text_only():
    """测试纯文本查询"""
    print("\n" + "=" * 60)
    print("测试 /api/query 接口（纯文本）")
    print("=" * 60)
    
    url = "http://localhost:5000/api/query"
    
    payload = {
        "query": "什么是城市体检？"
    }
    
    print(f"\n发送请求到: {url}")
    print(f"查询内容: {payload['query']}")
    
    start_time = time.time()
    
    try:
        response = requests.post(url, json=payload, timeout=300)
        elapsed = time.time() - start_time
        
        print(f"\n✓ 请求完成，耗时: {elapsed:.2f}秒")
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n响应内容:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            print("\n✓ 测试成功！")
            print(f"  - 状态: {result.get('status')}")
            print(f"  - 答案: {result.get('answer', '无')[:200]}...")
        else:
            print(f"\n✗ 请求失败: {response.text}")
            
    except requests.exceptions.Timeout:
        print("\n✗ 请求超时（超过5分钟）")
    except Exception as e:
        print(f"\n✗ 请求出错: {e}")


def test_health():
    """测试健康检查"""
    print("\n" + "=" * 60)
    print("测试健康检查")
    print("=" * 60)
    
    url = "http://localhost:5000/api/health"
    
    try:
        response = requests.get(url, timeout=5)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ API运行正常")
            print(f"  响应: {result}")
        else:
            print(f"✗ API异常: {response.text}")
            
    except Exception as e:
        print(f"✗ 无法连接到API: {e}")
        print("请确保API服务已启动: python api_async.py")
        return False
    
    return True


if __name__ == "__main__":
    print("\n🚀 开始测试异步 /api/query 接口\n")
    
    # 1. 先测试健康检查
    if not test_health():
        print("\n❌ API未运行，请先启动API服务")
        exit(1)
    
    # 2. 测试纯文本查询
    test_query_text_only()
    
    # 3. 测试带图片的查询（可选）
    # test_query_with_image()
    
    print("\n" + "=" * 60)
    print("✓ 所有测试完成")
    print("=" * 60)
