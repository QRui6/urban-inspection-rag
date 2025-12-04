#!/usr/bin/env python3
"""
手动测试API接口
"""
import requests
import json
import time

def test_health():
    """测试健康检查接口"""
    print("=" * 60)
    print("测试 1: 健康检查接口")
    print("=" * 60)
    try:
        response = requests.get("http://localhost:5000/api/health", timeout=5)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def test_query():
    """测试query接口"""
    print("\n" + "=" * 60)
    print("测试 2: Query接口（带图片）")
    print("=" * 60)
    
    # 读取图片base64
    try:
        with open('test_image_base64.txt', 'r') as f:
            image_base64 = f.read().strip()
        print(f"✓ 图片base64已加载，长度: {len(image_base64)}")
    except Exception as e:
        print(f"❌ 无法读取图片: {e}")
        return False
    
    # 准备请求
    payload = {
        "query": "这张图片中有什么内容？请详细描述。",
        "image_base64": image_base64
    }
    
    print(f"查询内容: {payload['query']}")
    print("发送请求...")
    
    start_time = time.time()
    
    try:
        response = requests.post(
            "http://localhost:5000/api/query",
            json=payload,
            timeout=120  # 2分钟超时
        )
        
        elapsed = time.time() - start_time
        
        print(f"\n状态码: {response.status_code}")
        print(f"响应时间: {elapsed:.2f}秒")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n响应数据:")
            print(json.dumps(data, ensure_ascii=False, indent=2))
            
            if data.get("status") == "success":
                print("\n✅ 测试成功！")
                return True
            else:
                print(f"\n⚠️  状态异常: {data.get('status')}")
                return False
        else:
            print(f"\n❌ 请求失败")
            print(f"响应内容: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"\n❌ 请求超时（>120秒）")
        return False
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        return False

def main():
    print("\n" + "🚀 " * 20)
    print("API接口测试")
    print("🚀 " * 20 + "\n")
    
    # 测试1: 健康检查
    health_ok = test_health()
    if not health_ok:
        print("\n❌ API服务未运行或无法访问")
        print("请先启动API: python api.py")
        return
    
    print("\n✓ API服务正常运行")
    
    # 测试2: Query接口
    query_ok = test_query()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"健康检查: {'✅ 通过' if health_ok else '❌ 失败'}")
    print(f"Query接口: {'✅ 通过' if query_ok else '❌ 失败'}")
    
    if health_ok and query_ok:
        print("\n🎉 所有测试通过！可以开始性能测试了。")
    else:
        print("\n⚠️  部分测试失败，请检查问题后再进行性能测试。")

if __name__ == "__main__":
    main()
