import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import os

class ChromaStore:
    """
    Chroma向量存储类
    用于将文本及其向量、元数据存储到Chroma数据库，并支持向量检索、删除集合、统计数量等操作。
    """
    def __init__(self, persist_directory: Optional[str] = None, collection_name: str = "rag_collection", vector_dim: int = 768):
        """
        初始化Chroma存储对象
        :param persist_directory: Chroma持久化目录，默认为当前工作目录下chroma_db
        :param collection_name: 集合名称，默认为rag_collection
        :param vector_dim: 向量维度，默认768
        """
        self.persist_directory = persist_directory or os.path.join(os.getcwd(), "chroma_db")
        self.collection_name = collection_name
        self.vector_dim = 3072
        self.client = chromadb.Client(Settings(persist_directory=self.persist_directory))
        self.collection = self._get_or_create_collection()

    def _get_or_create_collection(self):
        """
        获取或创建Chroma集合（collection）
        :return: 集合对象
        """
        if self.collection_name in [c.name for c in self.client.list_collections()]:
            return self.client.get_collection(self.collection_name)
        else:
            return self.client.create_collection(self.collection_name)

    def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """
        批量添加文档到Chroma集合
        :param documents: 文档列表，每个文档需包含content、embedding、metadata字段
        :return: 添加成功返回True，否则False
        """
        try:
            # 过滤无效文档
            valid_documents = [
                doc for doc in documents 
                if "embedding" in doc and doc.get("content") is not None
            ]
            
            if len(valid_documents) < len(documents):
                print(f"警告: 过滤掉 {len(documents) - len(valid_documents)} 个无效文档")
            
            if not valid_documents:
                print("警告: 没有有效的文档可以添加")
                return True

            ids = [str(i) for i in range(self.get_document_count(), self.get_document_count() + len(valid_documents))]
            embeddings = [doc["embedding"] for doc in valid_documents]
            
            # 处理metadata，确保所有值都是Chroma支持的类型
            metadatas = []
            for doc in valid_documents:
                cleaned_metadata = self._clean_metadata(doc["metadata"])
                metadatas.append(cleaned_metadata)
            
            documents_content = [doc["content"] for doc in valid_documents]
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents_content
            )
            return True
        except Exception as e:
            print(f"Chroma批量添加文档时出错: {str(e)}")
            return False
    
    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        清理metadata，确保所有值都是Chroma支持的类型（str, int, float, bool, None）
        :param metadata: 原始metadata
        :return: 清理后的metadata
        """
        cleaned = {}
        for key, value in metadata.items():
            if value is None:
                cleaned[key] = None
            elif isinstance(value, (str, int, float, bool)):
                cleaned[key] = value
            elif isinstance(value, list):
                # 将列表转换为逗号分隔的字符串
                cleaned[key] = ", ".join(str(item) for item in value if item is not None)
            elif isinstance(value, dict):
                # 将字典转换为JSON字符串
                import json
                cleaned[key] = json.dumps(value, ensure_ascii=False)
            else:
                # 其他类型转换为字符串
                cleaned[key] = str(value)
        return cleaned

    # def search(self, query: str, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
    #     """
    #     基于向量的相似度检索
    #     :param query: 查询文本（未用，仅为接口兼容）
    #     :param query_vector: 查询向量
    #     :param top_k: 返回最相似的文档数量
    #     :return: 检索到的文档列表，每个包含content、embedding、metadata
    #     """
    #     try:
    #         results = self.collection.query(
    #             query_embeddings=[query_vector],
    #             n_results=top_k,
    #             # include=["documents", "embeddings", "metadatas"]
    #         )
    #         docs = []
    #         indicator_docs = []  # 指标文档
    #         general_docs = []    # 通用文档
    #         for i in range(len(results["ids"][0])):
    #             # 恢复metadata中的列表类型数据
    #             metadata = self._restore_metadata(results["metadatas"][0][i])
    #             docs.append({
    #                 "content": results["documents"][0][i],
    #                 "metadata": metadata,
    #                 "distance": results["distances"][0][i],  # 可选：加上距离，便于后续排序或调试
    #                 "id": results["ids"][0][i]
    #             })
    #         return docs
    #     except Exception as e:
    #         print(f"Chroma搜索时出错: {str(e)}")
    #         return []

    def search(self, query: str, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        基于向量的相似度检索，优化指标内容检索
        :param query: 查询文本（未用，仅为接口兼容）
        :param query_vector: 查询向量
        :param top_k: 返回最相似的文档数量
        :return: 检索到的文档列表，每个包含content、embedding、metadata
        """
        try:
            # 大幅增加检索候选数量，确保能检索到指标内容
            candidate_count = max(top_k * 10, 200)  # 至少检索100个候选
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=candidate_count,
            )
            
            indicator_docs = []  # 指标文档
            general_docs = []    # 通用文档
            
            # 按chunk_type分类文档
            for i in range(len(results["ids"][0])):
                # 恢复metadata中的列表类型数据
                metadata = self._restore_metadata(results["metadatas"][0][i])
                doc = {
                    "content": results["documents"][0][i],
                    "metadata": metadata,
                    "distance": results["distances"][0][i],  # 可选：加上距离，便于后续排序或调试
                    "id": results["ids"][0][i]
                }
                
                # 根据chunk_type分类
                if metadata.get("chunk_type") == "indicator_complete":
                    indicator_docs.append(doc)
                else:
                    general_docs.append(doc)
            
            # 如果指标文档数量不足，降低筛选标准
            if len(indicator_docs) < top_k * 0.3:  # 如果指标文档少于30%
                # 尝试通过其他元数据识别指标内容
                for doc in general_docs[:]:
                    metadata = doc["metadata"]
                    # 通过标题或其他特征识别潜在的指标内容
                    indicator_title = metadata.get("indicator_title", "")
                    if ("指标" in indicator_title or 
                        "体检依据" in doc["content"] or 
                        "体检内容" in doc["content"] or
                        "指标解释" in doc["content"]):
                        # 将这些文档也视为指标文档
                        indicator_docs.append(doc)
                        general_docs.remove(doc)
            
            # 按距离排序（距离越小越相似）
            indicator_docs.sort(key=lambda x: x["distance"])
            general_docs.sort(key=lambda x: x["distance"])
            
            # 优先返回指标文档
            if len(indicator_docs) >= top_k:
                # 如果指标文档足够，优先返回指标文档
                final_docs = indicator_docs[:top_k]
            else:
                # 如果指标文档不足，全部返回并补充通用文档
                final_docs = indicator_docs[:]
                remaining_count = top_k - len(indicator_docs)
                final_docs.extend(general_docs[:remaining_count])
            
            return final_docs
        except Exception as e:
            print(f"Chroma搜索时出错: {str(e)}")
            return []

    
    def _restore_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        恢复metadata中的复合类型数据
        :param metadata: 从Chroma检索到的metadata
        :return: 恢复后的metadata
        """
        restored = {}
        for key, value in metadata.items():
            if key == "keywords" and isinstance(value, str) and value:
                # 将逗号分隔的字符串恢复为列表
                restored[key] = [item.strip() for item in value.split(",") if item.strip()]
            elif key.endswith("_json") and isinstance(value, str):
                # 恢复JSON字符串为字典
                try:
                    import json
                    restored[key.replace("_json", "")] = json.loads(value)
                except:
                    restored[key] = value
            else:
                restored[key] = value
        return restored

    def delete_index(self):
        """
        删除当前Chroma集合（collection）
        """
        try:
            self.client.delete_collection(self.collection_name)
        except Exception as e:
            print(f"Chroma删除集合时出错: {str(e)}")

    def get_document_count(self) -> int:
        """
        获取当前集合中的文档数量
        :return: 文档数量
        """
        try:
            return self.collection.count()
        except Exception as e:
            print(f"Chroma获取文档数量时出错: {str(e)}")
            return 0 