"""
测试新的 Embedder 类的文本和图像编码功能
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.embedding.embedder import Embedder
from PIL import Image
import numpy as np

def test_text_embedding():
    """测试文本编码"""
    print("测试文本编码...")
    
    embedder = Embedder()
    
    # 测试单个文本
    text = "这是一个测试文本"
    embedding = embedder.embed_text(text)
    print(f"文本编码维度: {len(embedding)}")
    
    # 测试批量文本
    texts = ["这是第一个文本", "这是第二个文本", "这是第三个文本"]
    embeddings = embedder.embed_batch(texts)
    print(f"批量文本编码数量: {len(embeddings)}, 维度: {len(embeddings[0])}")
    
    return True

def test_image_embedding():
    """测试图像编码"""
    print("\n测试图像编码...")
    
    # 检查是否存在测试图片
    test_image = r"E:\program\AI\RAG\uploads\two_dogs_in_snow.jpg"  # 替换为你的测试图片路径
    if not os.path.exists(test_image):
        print(f"测试图片不存在: {test_image}")
        return False
    
    embedder = Embedder()
    
    # 测试单个图像
    try:
        embedding = embedder.embed_image(test_image)
        print(f"图像编码维度: {len(embedding)}")
    except Exception as e:
        print(f"图像编码失败: {str(e)}")
        return False
    
    # 测试批量图像
    try:
        embeddings = embedder.embed_image_batch([test_image])
        print(f"批量图像编码数量: {len(embeddings)}, 维度: {len(embeddings[0])}")
    except Exception as e:
        print(f"批量图像编码失败: {str(e)}")
        return False
    
    return True

def test_mixed_documents():
    """测试混合文档编码"""
    print("\n测试混合文档编码...")
    
    # 检查是否存在测试图片
    test_image = r"E:\program\AI\RAG\uploads\two_dogs_in_snow.jpg"  # 替换为你的测试图片路径
    if not os.path.exists(test_image):
        print(f"测试图片不存在: {test_image}")
        return False
    
    embedder = Embedder()
    
    # 创建混合文档
    documents = [
        {
            "type": "text",
            "content": "这是一个文本文档"
        },
        {
            "type": "image",
            "content": test_image
        },
        {
            "type": "text",
            "content": "这是另一个文本文档"
        }
    ]
    
    # 测试文档编码
    try:
        embedded_docs = embedder.embed_documents(documents)
        
        # 检查是否所有文档都有嵌入向量
        all_have_embeddings = all("embedding" in doc for doc in embedded_docs)
        
        # 检查嵌入向量维度是否一致
        if all_have_embeddings:
            dims = [len(doc["embedding"]) for doc in embedded_docs]
            same_dims = all(d == dims[0] for d in dims)
            print(f"所有文档都有嵌入向量: {all_have_embeddings}")
            print(f"嵌入向量维度一致: {same_dims}, 维度: {dims[0]}")
            
            # 计算文本和图像向量之间的相似度
            text_vec1 = np.array(embedded_docs[0]["embedding"])
            img_vec = np.array(embedded_docs[1]["embedding"])
            text_vec2 = np.array(embedded_docs[2]["embedding"])
            
            sim1 = np.dot(text_vec1, img_vec) / (np.linalg.norm(text_vec1) * np.linalg.norm(img_vec))
            sim2 = np.dot(text_vec1, text_vec2) / (np.linalg.norm(text_vec1) * np.linalg.norm(text_vec2))
            
            print(f"文本1和图像的余弦相似度: {sim1:.4f}")
            print(f"文本1和文本2的余弦相似度: {sim2:.4f}")
            
            return all_have_embeddings and same_dims
        else:
            print("不是所有文档都有嵌入向量")
            return False
    except Exception as e:
        print(f"混合文档编码失败: {str(e)}")
        return False

def test_volc_embedding():
    """测试火山引擎编码"""
    print("\n测试火山引擎编码...")
    
    # 修改配置以使用火山引擎
    from config.config import ACTIVE_MODELS
    original_embedding = ACTIVE_MODELS["embedding"]
    ACTIVE_MODELS["embedding"] = "volcengine"
    
    try:
        # 测试文本编码
        embedder = Embedder()
        text = "这是一个测试文本"
        embedding = embedder.embed_text(text)
        print(f"火山引擎文本编码维度: {len(embedding)}")
        
        # 测试图像编码
        test_image = r"E:\program\AI\RAG\uploads\two_dogs_in_snow.jpg"  # 替换为你的测试图片路径
        if os.path.exists(test_image):
            embedding = embedder.embed_image(test_image)
            print(f"火山引擎图像编码维度: {len(embedding)}")
            
            # 检查文本和图像编码维度是否一致
            text_embedding = embedder.embed_text(text)
            image_embedding = embedder.embed_image(test_image)
            print(f"文本编码维度: {len(text_embedding)}, 图像编码维度: {len(image_embedding)}")
            print(f"维度一致: {len(text_embedding) == len(image_embedding)}")
            
            return len(text_embedding) == len(image_embedding)
        else:
            print(f"测试图片不存在: {test_image}")
            return False
    finally:
        # 恢复原始配置
        ACTIVE_MODELS["embedding"] = original_embedding

if __name__ == "__main__":
    print("开始测试 Embedder 类...")
    
    # 测试文本编码
    text_result = test_text_embedding()
    
    # 测试图像编码
    image_result = test_image_embedding()
    
    # 测试混合文档编码
    mixed_result = test_mixed_documents()
    
    # 测试火山引擎编码
    volc_result = test_volc_embedding()
    
    # 输出总结果
    print("\n测试结果汇总:")
    print(f"文本编码测试: {'通过' if text_result else '失败'}")
    print(f"图像编码测试: {'通过' if image_result else '失败'}")
    print(f"混合文档编码测试: {'通过' if mixed_result else '失败'}")
    print(f"火山引擎编码测试: {'通过' if volc_result else '失败'}") 