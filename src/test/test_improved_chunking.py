#!/usr/bin/env python3
"""
测试改进的文档切块方案
"""
import json
import os
import re
from datetime import datetime

class ImprovedMarkdownChunkLoader:
    """
    改进的Markdown分块器，专门针对城市体检工作手册优化
    """
    def __init__(self, md_path: str, image_root: str = None, max_chunk_size: int = 3000):
        self.md_path = md_path
        self.image_root = image_root or os.path.dirname(md_path)
        self.max_chunk_size = max_chunk_size

    def chunk(self):
        with open(self.md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        all_chunks = []
        chunk_id_counter = 0

        # 步骤1：按指标分割，但保持每个指标的完整性
        indicator_pattern = r'(?=# 指标\d{1,2}：)'
        sections = re.split(indicator_pattern, content)
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
                
            # 检查是否是指标部分
            indicator_match = re.match(r'# (指标\d{1,2}：.*?)(?=\n|$)', section)
            
            if indicator_match:
                # 这是一个完整的指标，作为一个大chunk处理
                indicator_title = indicator_match.group(1)
                chunk_data = self._process_indicator_section(section, indicator_title, chunk_id_counter)
                all_chunks.extend(chunk_data)
                chunk_id_counter += len(chunk_data)
            else:
                # 非指标部分，按章节处理
                chapter_chunks = self._process_general_section(section, chunk_id_counter)
                all_chunks.extend(chapter_chunks)
                chunk_id_counter += len(chapter_chunks)
        
        return all_chunks

    def _process_indicator_section(self, section: str, indicator_title: str, start_id: int):
        """处理指标部分，保持完整性"""
        chunks = []
        
        # 提取体检依据部分
        basis_pattern = r'# 【体检依据】\s*(.*?)(?=# 【|$)'
        basis_match = re.search(basis_pattern, section, re.DOTALL)
        basis_content = basis_match.group(1).strip() if basis_match else ""
        
        # 分离图片和文本
        image_matches = re.findall(r'!\[.*?\]\((.*?)\)', section)
        text_content = re.sub(r'!\[.*?\]\(.*?\)', '', section).strip()
        
        # 创建主要的指标文本chunk（包含完整的指标信息）
        if text_content:
            chunks.append({
                "type": "text",
                "content": text_content,
                "metadata": {
                    "source": self.md_path,
                    "chunk_id": start_id,
                    "indicator_title": indicator_title,
                    "is_complete_indicator": True,  # 标记为完整指标
                    "has_inspection_basis": bool(basis_content),
                    "basis_content": basis_content,
                    "chunk_type": "indicator_complete"
                }
            })
        
        # 为图片创建独立的chunk，但保持与指标的关联
        for i, img_path in enumerate(image_matches):
            abs_img_path = os.path.abspath(os.path.join(self.image_root, img_path))
            chunks.append({
                "type": "image",
                "content": None,
                "metadata": {
                    "source": self.md_path,
                    "chunk_id": start_id + 1 + i,
                    "indicator_title": indicator_title,
                    "img_path": abs_img_path,
                    "related_basis": basis_content,  # 关联的体检依据
                    "chunk_type": "indicator_image"
                }
            })
        
        return chunks

    def _process_general_section(self, section: str, start_id: int):
        """处理非指标的一般章节"""
        chunks = []
        
        # 按较大的段落分割，避免过度细分
        paragraphs = re.split(r'\n\n+', section)
        current_chunk = ""
        current_title = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            # 检查是否是标题
            title_match = re.match(r'^#+\s+(.+)', paragraph)
            if title_match:
                # 如果当前chunk不为空，先保存
                if current_chunk:
                    chunks.append(self._create_text_chunk(
                        current_chunk, start_id + len(chunks), current_title, "general"
                    ))
                    current_chunk = ""
                current_title = title_match.group(1)
                current_chunk = paragraph
            else:
                # 累积内容
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
                    
                # 如果chunk太大，分割保存
                if len(current_chunk) > self.max_chunk_size:
                    chunks.append(self._create_text_chunk(
                        current_chunk, start_id + len(chunks), current_title, "general"
                    ))
                    current_chunk = ""
        
        # 保存最后的chunk
        if current_chunk:
            chunks.append(self._create_text_chunk(
                current_chunk, start_id + len(chunks), current_title, "general"
            ))
        
        return chunks

    def _create_text_chunk(self, content: str, chunk_id: int, title: str, chunk_type: str):
        """创建文本chunk"""
        # 检查是否包含体检依据相关内容
        has_basis = "体检依据" in content or "规范" in content or "标准" in content
        basis_keywords = ["GB", "规范", "标准", "条例", "意见", "通知", "规定"]
        basis_content = ""
        
        if has_basis:
            # 提取可能的依据内容
            for keyword in basis_keywords:
                if keyword in content:
                    # 简单提取包含关键词的句子
                    sentences = re.split(r'[。！？\n]', content)
                    basis_sentences = [s for s in sentences if keyword in s]
                    basis_content += "; ".join(basis_sentences[:3])  # 最多取3个相关句子
                    break
        
        return {
            "type": "text",
            "content": content,
            "metadata": {
                "source": self.md_path,
                "chunk_id": chunk_id,
                "indicator_title": title,
                "is_inspection_basis": has_basis,
                "basis_content": basis_content,
                "chunk_type": chunk_type
            }
        }

def test_improved_chunking():
    """测试改进的切块方案"""
    
    # 输入文件路径
    md_file = "output/20250526城市体检工作手册.md"
    
    if not os.path.exists(md_file):
        print(f"文件不存在: {md_file}")
        return
    
    print("开始使用改进的切块方案...")
    
    # 创建改进的加载器
    loader = ImprovedMarkdownChunkLoader(
        md_path=md_file,
        max_chunk_size=3000  # 增大chunk大小，减少切块数量
    )
    
    # 执行切块
    chunks = loader.chunk()
    
    # 统计信息
    total_chunks = len(chunks)
    text_chunks = len([c for c in chunks if c["type"] == "text"])
    image_chunks = len([c for c in chunks if c["type"] == "image"])
    indicator_chunks = len([c for c in chunks if c.get("metadata", {}).get("chunk_type") == "indicator_complete"])
    
    print(f"\n=== 切块统计 ===")
    print(f"总chunk数: {total_chunks}")
    print(f"文本chunks: {text_chunks}")
    print(f"图片chunks: {image_chunks}")
    print(f"完整指标chunks: {indicator_chunks}")
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"logs/chunk_log_improved_{timestamp}.json"
    
    # 确保logs目录存在
    os.makedirs("logs", exist_ok=True)
    
    # 准备输出数据
    output_data = {
        "timestamp": timestamp,
        "source_type": "markdown",
        "chunk_method": "ImprovedLogicalUnitSplitter",
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
    
    print(f"结果已保存到: {output_file}")
    
    # 显示一些示例chunks
    print(f"\n=== 示例chunks ===")
    
    # 显示第一个指标chunk
    indicator_chunks_list = [c for c in chunks if c.get("metadata", {}).get("chunk_type") == "indicator_complete"]
    if indicator_chunks_list:
        first_indicator = indicator_chunks_list[0]
        print(f"\n第一个完整指标chunk:")
        print(f"标题: {first_indicator['metadata']['indicator_title']}")
        print(f"内容长度: {len(first_indicator['content'])}")
        print(f"包含体检依据: {first_indicator['metadata']['has_inspection_basis']}")
        if first_indicator['metadata']['basis_content']:
            print(f"体检依据摘要: {first_indicator['metadata']['basis_content'][:200]}...")
    
    # 对比原方案
    print(f"\n=== 与原方案对比 ===")
    print(f"原方案chunks数: 1753")
    print(f"改进方案chunks数: {total_chunks}")
    print(f"减少比例: {((1753 - total_chunks) / 1753 * 100):.1f}%")
    
    return chunks

if __name__ == "__main__":
    test_improved_chunking()