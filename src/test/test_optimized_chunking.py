#!/usr/bin/env python3
"""
测试优化后的文档切块方案
"""
import json
import os
from datetime import datetime
from src.document_loader.md_loader_optimized import MarkdownChunkLoader

def test_optimized_chunking():
    """测试优化后的切块方案"""
    
    # 输入文件路径
    md_file = "output/20250526城市体检工作手册.md"
    
    if not os.path.exists(md_file):
        print(f"文件不存在: {md_file}")
        return
    
    print("开始使用优化后的切块方案...")
    
    # 创建优化后的加载器
    loader = MarkdownChunkLoader(
        md_path=md_file,
        max_chunk_size=4000  # 增大chunk大小，保持完整性
    )
    
    # 执行切块
    chunks = loader.chunk()
    
    # 统计信息
    total_chunks = len(chunks)
    text_chunks = len([c for c in chunks if c["type"] == "text"])
    image_chunks = len([c for c in chunks if c["type"] == "image"])
    indicator_chunks = len([c for c in chunks if c.get("metadata", {}).get("chunk_type") == "indicator_complete"])
    
    print(f"\n=== 优化后切块统计 ===")
    print(f"总chunk数: {total_chunks}")
    print(f"文本chunks: {text_chunks}")
    print(f"图片chunks: {image_chunks}")
    print(f"完整指标chunks: {indicator_chunks}")
    
    # 分析指标chunks的质量
    print(f"\n=== 指标chunks质量分析 ===")
    indicator_chunks_list = [c for c in chunks if c.get("metadata", {}).get("chunk_type") == "indicator_complete"]
    
    for i, chunk in enumerate(indicator_chunks_list[:3]):  # 只显示前3个
        metadata = chunk["metadata"]
        print(f"\n指标 {i+1}:")
        print(f"  标题: {metadata['indicator_title']}")
        print(f"  包含体检依据: {metadata['has_inspection_basis']}")
        print(f"  关键词: {metadata.get('keywords', [])}")
        print(f"  内容长度: {len(chunk['content'])}")
        if metadata.get('basis_content'):
            print(f"  体检依据摘要: {metadata['basis_content'][:100]}...")
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"logs/chunk_log_optimized_{timestamp}.json"
    
    # 确保logs目录存在
    os.makedirs("logs", exist_ok=True)
    
    # 准备输出数据
    output_data = {
        "timestamp": timestamp,
        "source_type": "markdown",
        "chunk_method": "OptimizedLogicalUnitSplitter",
        "total_chunks": total_chunks,
        "statistics": {
            "text_chunks": text_chunks,
            "image_chunks": image_chunks,
            "indicator_chunks": indicator_chunks
        },
        "chunks": chunks
    }
    
    # 保存到文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到: {output_file}")
    
    # 对比原方案
    print(f"\n=== 与原方案对比 ===")
    print(f"原方案chunks数: 1753")
    print(f"优化方案chunks数: {total_chunks}")
    print(f"减少比例: {((1753 - total_chunks) / 1753 * 100):.1f}%")
    
    # 测试特定查询的匹配效果
    print(f"\n=== 测试查询匹配效果 ===")
    test_query = "关于切实加强住房和城乡建设领域安全生产隐患排查整治的紧急通知"
    
    # 查找包含该查询内容的chunks
    matching_chunks = []
    for chunk in chunks:
        if chunk["type"] == "text" and test_query in chunk["content"]:
            matching_chunks.append(chunk)
    
    print(f"查询: {test_query}")
    print(f"匹配的chunks数量: {len(matching_chunks)}")
    
    for i, chunk in enumerate(matching_chunks):
        metadata = chunk["metadata"]
        print(f"\n匹配chunk {i+1}:")
        print(f"  类型: {metadata.get('chunk_type', 'unknown')}")
        print(f"  标题: {metadata.get('indicator_title', 'N/A')}")
        print(f"  是否完整指标: {metadata.get('is_complete_indicator', False)}")
        print(f"  关键词: {metadata.get('keywords', [])}")
    
    return chunks

if __name__ == "__main__":
    test_optimized_chunking()