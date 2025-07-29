"""
检索模块
"""
from typing import List, Dict, Any
from src.embedding.embedder import Embedder
from src.storage.chroma_store import ChromaStore
from config.config import RETRIEVAL_CONFIG

class Retriever:
    """检索类"""
    
    def __init__(self):
        self.embedder = Embedder()
        self.es_store = ChromaStore()
        self.top_k = RETRIEVAL_CONFIG["top_k"]
        self.bm25_weight = RETRIEVAL_CONFIG["bm25_weight"]
        self.vector_weight = RETRIEVAL_CONFIG["vector_weight"]
    
    def retrieve(self, query: str) -> List[Dict[str, Any]]:
        """检索相关文档"""
        # 生成查询向量
        query_vector = self.embedder.embed_text(query)
        
        # 从Elasticsearch检索文档
        documents = self.es_store.search(
            query=query,
            query_vector=query_vector,
            top_k=self.top_k
        )
        
        return documents 