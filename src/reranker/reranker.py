"""
重排序模块
"""
from typing import List, Dict, Any
import torch
import re
from sentence_transformers import CrossEncoder
from config.config import RERANKER_CONFIG

class Reranker:
    """重排序类"""
    
    def __init__(self):
        self.model = CrossEncoder(RERANKER_CONFIG["model_name"])
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.top_k = RERANKER_CONFIG["top_k"]
        
        if self.device == "cuda":
            self.model = self.model.to(self.device)
    
    def extract_problem_name(self, query: str) -> str:
        """
        从查询文本中提取问题名称
        
        Args:
            query: 包含问题描述的查询文本
            
        Returns:
            提取出的问题名称，如果无法提取则返回原始查询的前50个字符
            
        Examples:
            输入: '**二、 小区与公共空间**\n**公共区域无障碍与步行道问题**\n\n图片显示...'
            输出: '公共区域无障碍与步行道问题'
        """
        try:
            # 方法1: 使用正则表达式匹配第二个**标记对之间的内容
            pattern = r'\*\*([^*]+)\*\*.*?\*\*([^*]+)\*\*'
            match = re.search(pattern, query)
            
            if match:
                # 返回第二个匹配组（问题名）
                problem_name = match.group(2).strip()
                if problem_name:
                    return problem_name
            
            # 方法2: 如果正则表达式失败，尝试手动解析
            parts = query.split('**')
            if len(parts) >= 5:  # 至少需要5部分: '', '类别', '', '问题名', '内容...'
                problem_name = parts[3].strip()
                if problem_name:
                    return problem_name
            
            # 方法3: 查找包含"问题"、"隐患"等关键词的行
            lines = query.split('\n')
            for line in lines:
                line = line.strip().replace('*', '')
                if any(keyword in line for keyword in ['问题', '隐患', '改造', '数量']):
                    if len(line) > 0 and len(line) < 50:  # 合理的问题名长度
                        return line
            
            # 方法4: 如果都失败，返回查询的前50个字符作为备选
            clean_query = re.sub(r'\*+', '', query).strip()
            clean_query = clean_query.replace('\n', ' ')
            return clean_query[:50] + ('...' if len(clean_query) > 50 else '')
            
        except Exception as e:
            print(f"提取问题名时出错: {e}")
            # 出错时返回原始查询的前50个字符
            clean_query = re.sub(r'[*\n]', ' ', query).strip()
            return clean_query[:50] + ('...' if len(clean_query) > 50 else '')
    
    def rerank(self, query: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """对检索结果进行重排序"""
        if not documents:
            return []
        
        # 提取问题名用于重排序
        problem_name = self.extract_problem_name(query)
        print(f"提取的问题名: {problem_name}")
            
        # 准备输入对 - 使用提取的问题名与文档的indicator_title进行匹配
        pairs = [(problem_name, doc["metadata"]["indicator_title"]) for doc in documents]
        
        # 计算相关性分数
        scores = self.model.predict(
            pairs,
            show_progress_bar=True
        )
        
        # 将分数添加到文档中
        for doc, score in zip(documents, scores):
            doc["rerank_score"] = float(score)
        
        # 按分数排序
        reranked_docs = sorted(
            documents,
            key=lambda x: x["rerank_score"],
            reverse=True
        )
        
        # 返回top_k个结果
        return reranked_docs[:self.top_k] 