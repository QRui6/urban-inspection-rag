"""
Elasticsearch存储模块
"""
from typing import List, Dict, Any, Optional
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from config.config import ES_CONFIG

class ElasticsearchStore:
    """Elasticsearch存储类"""
    
    def __init__(self):
        self.es = Elasticsearch(hosts=ES_CONFIG["hosts"], basic_auth=("elastic", "elastic"), verify_certs=False)
        self.index_name = ES_CONFIG["index_name"]
        self.vector_dim = ES_CONFIG["vector_dim"]
        print(self.vector_dim)
        self._create_index_if_not_exists()
    
    def _create_index_if_not_exists(self):
        """创建索引（如果不存在）"""
        if not self.es.indices.exists(index=self.index_name):
            mappings = {
                "mappings": {
                    "properties": {
                        "content": {"type": "text"},
                        "embedding": {
                            "type": "dense_vector",
                            "dims": self.vector_dim,
                            "index": True,
                            "similarity": "cosine"
                        },
                        "metadata": {
                            "properties": {
                                "source": {"type": "keyword"},
                                "chunk_id": {"type": "integer"},
                            }
                        }
                    }
                },
                "settings": {
                    "index": {
                        "number_of_shards": 1,
                        "number_of_replicas": 1
                    }
                }
            }
            self.es.indices.create(index=self.index_name, body=mappings)
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """批量添加文档，支持图片描述chunk与文本chunk统一存储"""
        actions = []
        for doc in documents:
            action = {
                "_index": self.index_name,
                "_source": {
                    "content": doc["content"],
                    "embedding": doc["embedding"],
                    "metadata": doc["metadata"]  # 其中可能包含img_path等
                }
            }
            actions.append(action)
        try:
            success, failed = bulk(self.es, actions)
            return len(failed) == 0
        except Exception as e:
            print(f"批量添加文档时出错: {str(e)}\n详细信息: {e.__class__.__name__}")
            if hasattr(e, 'errors') and e.errors:
                for err in e.errors:
                    print(f"文档错误: {err}")
            return False
    
    def search(self, query: str, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """混合搜索（BM25 + 向量检索）"""
        search_query = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "match": {
                                "content": {
                                    "query": query,
                                    "boost": 0.3  # BM25权重
                                }
                            }
                        },
                        {
                            "script_score": {
                                "query": {"match_all": {}},
                                "script": {
                                    "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                                    "params": {"query_vector": query_vector}
                                },
                                "boost": 0.7  # 向量检索权重
                            }
                        }
                    ]
                }
            },
            "size": top_k
        }
        
        try:
            response = self.es.search(index=self.index_name, body=search_query)
            hits = response["hits"]["hits"]
            return [hit["_source"] for hit in hits]
        except Exception as e:
            print(f"搜索时出错: {str(e)}")
            return []
    
    def delete_index(self):
        """删除索引"""
        if self.es.indices.exists(index=self.index_name):
            self.es.indices.delete(index=self.index_name)
    
    def get_document_count(self) -> int:
        """获取文档数量"""
        try:
            response = self.es.count(index=self.index_name)
            return response["count"]
        except Exception as e:
            print(f"获取文档数量时出错: {str(e)}")
            return 0 