import os
import re
from typing import List, Dict, Any
from pathlib import Path

class MarkdownChunkLoader:
    """Markdown分块与图片识别"""
    # def __init__(self, md_path: str, image_root: str = None):
    #     self.md_path = md_path
    #     self.image_root = image_root or os.path.dirname(md_path)
    def __init__(self, md_path: str, image_root: str = None):
        self.md_path = md_path
        # 如果没有提供image_root，则根据Markdown文件位置自动推断图片根目录
        if image_root is None:
            # 假设图片在与Markdown文件同目录的images子目录中
            md_dir = os.path.dirname(os.path.abspath(md_path))
            potential_image_dir = os.path.join(md_dir, "images")
            if os.path.exists(potential_image_dir):
                self.image_root = potential_image_dir
            else:
                self.image_root = md_dir
        else:
            self.image_root = image_root

    def chunk(self) -> List[Dict[str, Any]]:
        with open(self.md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # 分块：按段落或标题分割
        blocks = re.split(r'(\n#+ .+\n|\n{2,})', content)
        chunks = []
        chunk_id = 0
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            # 检查是否为图片引用
            img_matches = re.findall(r'!\[.*?\]\((.*?)\)', block)
            if img_matches:
                for img_path in img_matches:
                    abs_img_path = os.path.abspath(os.path.join(self.image_root, img_path))
                    # 记录图片chunk待处理信息
                    chunks.append({
                        "type": "image",
                        "content": None,  # 待VLM处理
                        "metadata": {
                            "source": self.md_path,
                            "chunk_id": chunk_id,
                            "img_path": abs_img_path,
                            "context": block  # 可选：前后文本
                        }
                    })
                    chunk_id += 1
            # 普通文本块
            text = re.sub(r'!\[.*?\]\(.*?\)', '', block).strip()
            if text:
                chunks.append({
                    "type": "text",
                    "content": text,
                    "metadata": {
                        "source": self.md_path,
                        "chunk_id": chunk_id
                    }
                })
                chunk_id += 1
        return chunks 