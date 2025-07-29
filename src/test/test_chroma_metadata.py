#!/usr/bin/env python3
"""
测试Chroma metadata处理
"""
from src.storage.chroma_store import ChromaStore

def test_chroma_metadata():
    """测试Chroma对metadata的处理"""
    
    # 创建测试数据
    test_documents = [
        {
            "content": "测试文档1",
            "embedding": [0.1] * 768,  # 假设768维向量
            "metadata": {
                "source": "test.md",
                "chunk_id": 1,
                "keywords": ["关键词1", "关键词2", "关键词3"],  # 列表类型
                "is_complete_indicator": True,  # 布尔类型
                "chunk_type": "indicator_complete",  # 字符串类型
                "distance": 1.5,  # 浮点类型
                "complex_data": {"nested": "value"}  # 字典类型
            }
        },
        {
            "content": "测试文档2",
            "embedding": [0.2] * 768,
            "metadata": {
                "source": "test2.md",
                "chunk_id": 2,
                "keywords": ["安全隐患", "结构安全"],
                "is_complete_indicator": False,
                "chunk_type": "general"
            }
        }
    ]
    
    print("=== 测试Chroma metadata处理 ===")
    
    # 创建ChromaStore实例
    store = ChromaStore(collection_name="test_metadata")
    
    # 删除现有集合（如果存在）
    store.delete_index()
    store = ChromaStore(collection_name="test_metadata")
    
    print("1. 测试添加包含列表类型metadata的文档...")
    
    try:
        success = store.add_documents(test_documents)
        if success:
            print("✓ 文档添加成功")
        else:
            print("✗ 文档添加失败")
            return
    except Exception as e:
        print(f"✗ 文档添加异常: {e}")
        return
    
    print("2. 测试检索和metadata恢复...")
    
    try:
        # 使用第一个文档的向量进行检索
        query_vector = [0.1] * 768
        results = store.search("测试查询", query_vector, top_k=2)
        
        print(f"检索到 {len(results)} 个结果")
        
        for i, result in enumerate(results):
            print(f"\n结果 {i+1}:")
            print(f"  内容: {result['content']}")
            print(f"  距离: {result['distance']}")
            print(f"  metadata:")
            
            metadata = result['metadata']
            for key, value in metadata.items():
                print(f"    {key}: {value} (类型: {type(value).__name__})")
            
            # 特别检查keywords是否正确恢复为列表
            if 'keywords' in metadata:
                keywords = metadata['keywords']
                if isinstance(keywords, list):
                    print(f"    ✓ keywords正确恢复为列表: {keywords}")
                else:
                    print(f"    ✗ keywords未正确恢复，当前类型: {type(keywords)}")
    
    except Exception as e:
        print(f"✗ 检索异常: {e}")
        return
    
    print("\n3. 清理测试数据...")
    store.delete_index()
    print("✓ 测试完成")

if __name__ == "__main__":
    test_chroma_metadata()