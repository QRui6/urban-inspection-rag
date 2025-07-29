import os
import re
import datetime
import json
from typing import List, Dict, Any
from pathlib import Path

class OptimizedMarkdownChunkLoader:
    """
    优化的Markdown分块器，专门针对城市体检工作手册优化
    主要改进：
    1. 保持指标完整性 - 每个指标作为一个完整的chunk
    2. 智能关键词提取 - 提升检索效果
    3. 增强语义关联 - 体检依据与指标保持关联
    4. 图片上下文保持 - 图片与相关文本关联
    """
    
    def __init__(self, md_path: str, image_root: str = None, max_chunk_size: int = 4000):
        self.md_path = md_path
        self.image_root = image_root or os.path.dirname(md_path)
        self.max_chunk_size = max_chunk_size
        self.log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "output")
        os.makedirs(self.log_dir, exist_ok=True)
        self.chunks_file = os.path.join(self.log_dir, "chunks.json")

    def chunk(self) -> List[Dict[str, Any]]:
        with open(self.md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        all_chunks = []
        chunk_id_counter = 0

        # 步骤1：按指标分割，保持每个指标的完整性
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
        
        # 保存所有chunk到JSON文件
        self._save_chunks_to_file(all_chunks)
        return all_chunks

    def _process_indicator_section(self, section: str, indicator_title: str, start_id: int) -> List[Dict[str, Any]]:
        """处理指标部分，保持完整性并提取关键信息"""
        chunks = []
        
        # 提取体检依据部分
        basis_pattern = r'# 【体检依据】\s*(.*?)(?=# 【|$)'
        basis_match = re.search(basis_pattern, section, re.DOTALL)
        basis_content = basis_match.group(1).strip() if basis_match else ""
        
        # 提取体检内容部分
        content_pattern = r'# 【体检内容】\s*(.*?)(?=# 【|$)'
        content_match = re.search(content_pattern, section, re.DOTALL)
        inspection_content = content_match.group(1).strip() if content_match else ""
        
        # 提取指标解释部分
        explanation_pattern = r'# 【指标解释】\s*(.*?)(?=# 【|$)'
        explanation_match = re.search(explanation_pattern, section, re.DOTALL)
        explanation_content = explanation_match.group(1).strip() if explanation_match else ""
        
        # 提取关键词用于检索优化
        keywords = self._extract_keywords(section, indicator_title)
        
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
                    "inspection_content": inspection_content,
                    "explanation_content": explanation_content,
                    "keywords": keywords,  # 添加关键词
                    "chunk_type": "indicator_complete"
                }
            })
        
        # 为图片创建独立的chunk，但保持与指标的关联
        for i, img_path in enumerate(image_matches):
            abs_img_path = os.path.abspath(os.path.join(self.image_root, img_path))
            
            # 尝试获取图片周围的上下文
            img_context = self._get_image_context(section, img_path)
            
            chunks.append({
                "type": "image",
                "content": None,  # 待VLM处理
                "metadata": {
                    "source": self.md_path,
                    "chunk_id": start_id + 1 + i,
                    "indicator_title": indicator_title,
                    "img_path": abs_img_path,
                    "context": img_context,  # 图片上下文
                    "related_basis": basis_content,  # 关联的体检依据
                    "keywords": keywords,  # 继承指标关键词
                    "chunk_type": "indicator_image"
                }
            })
        
        return chunks

    def _process_general_section(self, section: str, start_id: int) -> List[Dict[str, Any]]:
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

    def _create_text_chunk(self, content: str, chunk_id: int, title: str, chunk_type: str) -> Dict[str, Any]:
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
        
        # 提取关键词
        keywords = self._extract_keywords(content, title)
        
        return {
            "type": "text",
            "content": content,
            "metadata": {
                "source": self.md_path,
                "chunk_id": chunk_id,
                "indicator_title": title,
                "is_inspection_basis": has_basis,
                "basis_content": basis_content,
                "keywords": keywords,
                "chunk_type": chunk_type
            }
        }

    def _extract_keywords(self, content: str, title: str) -> List[str]:
        """提取关键词用于检索优化"""
        keywords = []
        
        # 从标题中提取关键词
        if title:
            # 移除标点符号和数字
            title_clean = re.sub(r'[^\u4e00-\u9fff\w\s]', ' ', title)
            title_words = [word.strip() for word in title_clean.split() if len(word.strip()) > 1]
            keywords.extend(title_words)
        
        # 提取重要的专业术语
        professional_terms = [
            "安全隐患", "结构安全", "燃气安全", "楼道安全", "围护安全", 
            "非成套住宅", "管线管道", "适老化改造", "节能改造", "数字化改造",
            "体检依据", "体检内容", "指标解释", "体检方法",
            "住宅项目规范", "住宅性能评定标准", "建筑节能", "绿色建筑",
            "城市体检", "住房城乡建设部", "安全生产", "隐患排查"
        ]
        
        for term in professional_terms:
            if term in content:
                keywords.append(term)
        
        # 提取规范标准编号
        standard_pattern = r'(GB[/T]*\s*\d+[-\d]*)'
        standards = re.findall(standard_pattern, content)
        keywords.extend(standards)
        
        # 去重、过滤空值并限制数量（避免过多关键词）
        keywords = list(set([k for k in keywords if k and k.strip()]))
        
        # 限制关键词数量，避免metadata过大
        return keywords[:20]  # 最多保留20个关键词

    def _get_image_context(self, section: str, img_path: str) -> str:
        """获取图片周围的上下文信息"""
        # 查找图片引用的位置
        img_pattern = rf'!\[.*?\]\({re.escape(img_path)}\)'
        match = re.search(img_pattern, section)
        
        if not match:
            return ""
        
        # 获取图片前后的文本作为上下文
        start_pos = max(0, match.start() - 200)
        end_pos = min(len(section), match.end() + 200)
        
        context = section[start_pos:end_pos]
        # 清理上下文，移除其他图片引用
        context = re.sub(r'!\[.*?\]\(.*?\)', '', context)
        context = re.sub(r'\n+', ' ', context).strip()
        
        return context
    
    def _save_chunks_to_file(self, chunks: List[Dict[str, Any]]) -> None:
        """将所有chunk保存到JSON文件"""
        # 准备保存的数据
        save_data = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_file": self.md_path,
            "max_chunk_size": self.max_chunk_size,
            "total_chunks": len(chunks),
            "text_chunks": len([c for c in chunks if c["type"] == "text"]),
            "image_chunks": len([c for c in chunks if c["type"] == "image"]),
            "chunks": chunks
        }
        
        # 保存到文件
        with open(self.chunks_file, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
            
        print(f"已保存 {len(chunks)} 个chunks到文件: {self.chunks_file}")

# 保持向后兼容性
class MarkdownChunkLoader(OptimizedMarkdownChunkLoader):
    """向后兼容的类名"""
    pass