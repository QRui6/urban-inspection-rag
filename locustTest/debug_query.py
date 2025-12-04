#!/usr/bin/env python3
"""
调试query方法的返回值
"""
import sys
sys.path.insert(0, '..')

from main import RAGSystem

# 初始化RAG系统
rag = RAGSystem()

# 读取图片base64
with open('test_image_base64.txt', 'r') as f:
    image_base64 = f.read().strip()

print("调用rag.query()...")
print(f"图片base64长度: {len(image_base64)}")

# 调用query
result = rag.query("这张图片中有什么内容？", image_base64)

print(f"\n返回值类型: {type(result)}")
print(f"返回值: {result}")

if isinstance(result, dict):
    print("\n✅ 返回值是字典")
    print(f"Keys: {result.keys()}")
else:
    print(f"\n❌ 返回值不是字典，是 {type(result)}")
