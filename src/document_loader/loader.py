"""
文档加载和分块模块
"""
import os
from typing import List, Dict, Any
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
)
from config.config import DOCUMENT_CONFIG, RAW_DATA_DIR

class DocumentLoader:
    """文档加载和分块类"""
    
    def __init__(self):
        self.supported_formats = DOCUMENT_CONFIG["supported_formats"]
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=DOCUMENT_CONFIG["chunk_size"],
            chunk_overlap=DOCUMENT_CONFIG["chunk_overlap"],
        )
        
    def _get_loader(self, file_path: str):
        """根据文件类型获取对应的加载器"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return PyPDFLoader(file_path)
        elif ext == ".docx":
            return Docx2txtLoader(file_path)
        elif ext == ".txt":
            return TextLoader(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")
    
    def load_document(self, file_path: str) -> List[Dict[str, Any]]:
        """加载单个文档并分块"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
            
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.supported_formats:
            raise ValueError(f"不支持的文件格式: {ext}")
            
        loader = self._get_loader(file_path)
        documents = loader.load()
        chunks = self.text_splitter.split_documents(documents)
        
        # 转换为字典格式
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            meta = dict(chunk.metadata)
            # 修正PDF页码为1起始
            if "page" in meta and isinstance(meta["page"], int):
                meta["page"] = meta["page"] + 1
            processed_chunks.append({
                "content": chunk.page_content,
                "metadata": {
                    "source": file_path,
                    "chunk_id": i,
                    **meta
                }
            })
        # 打印前几个chunk的metadata，便于调试
        for c in processed_chunks[:3]:
            print("分块元数据示例：", c["metadata"])
        return processed_chunks
    
    def load_directory(self, directory: str = None) -> List[Dict[str, Any]]:
        """加载目录下的所有支持格式的文档"""
        if directory is None:
            directory = RAW_DATA_DIR
            
        all_chunks = []
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in self.supported_formats):
                    file_path = os.path.join(root, file)
                    try:
                        chunks = self.load_document(file_path)
                        all_chunks.extend(chunks)
                    except Exception as e:
                        print(f"处理文件 {file_path} 时出错: {str(e)}")
                        
        return all_chunks 