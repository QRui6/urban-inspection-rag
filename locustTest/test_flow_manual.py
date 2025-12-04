#!/usr/bin/env python3
"""手动测试两阶段流程"""
import requests
import json
import time

# 读取图片
with open('test_image_base64.txt', 'r') as f:
    image_base64 = f.read().strip()

print("=" * 60)
print("测试两阶段流程")
print("=" * 60)

# 第一步: 分析图片
print("\n[1/2] 调用 /api/analyze-image...")
start = time.time()
response1 = requests.post(
    "http://localhost:5000/api/analyze-image",
    json={
        "query": "这张图片中有什么安全隐患？",
        "image_base64": image_base64
    },
    timeout=120
)
elapsed1 = time.time() - start

print(f"状态码: {response1.status_code}")
print(f"耗时: {elapsed1:.2f}秒")

if response1.status_code == 200:
    data1 = response1.json()
    print(f"Session ID: {data1.get('session_id')}")
    print(f"视觉分析: {data1.get('visual_analysis')[:100]}...")
    
    session_id = data1.get('session_id')
    
    # 第二步: 完成回答
    print(f"\n[2/2] 调用 /api/complete-answer...")
    start = time.time()
    response2 = requests.post(
        "http://localhost:5000/api/complete-answer",
        json={
            "session_id": session_id
        },
        timeout=120
    )
    elapsed2 = time.time() - start
    
    print(f"状态码: {response2.status_code}")
    print(f"耗时: {elapsed2:.2f}秒")
    
    if response2.status_code == 200:
        data2 = response2.json()
        print(f"\n最终答案:\n{data2.get('answer')[:200]}...")
        print(f"\n✅ 流程测试成功！")
        print(f"总耗时: {elapsed1 + elapsed2:.2f}秒")
    else:
        print(f"❌ 第二步失败: {response2.text}")
else:
    print(f"❌ 第一步失败: {response1.text}")
