"""
向量化模块，支持文本和图像编码
"""
from typing import List, Dict, Any, Union, Optional
import os
import base64
import torch
from PIL import Image
import requests
import io
from sentence_transformers import SentenceTransformer
from volcenginesdkarkruntime import Ark
from config.config import MODELS, ACTIVE_MODELS
from transformers import ChineseCLIPProcessor, ChineseCLIPModel

# 导入阿里DashScope
import dashscope
from http import HTTPStatus


class Embedder:
    """文本和图像向量化类"""
    
    def __init__(self):
        # 获取当前激活的嵌入模型
        self.active_embedding = ACTIVE_MODELS.get("embedding", "sentence-transformer")
        
        # 获取模型配置
        if self.active_embedding not in MODELS["embedding_models"]:
            raise ValueError(f"未找到嵌入模型配置: {self.active_embedding}")
            
        self.embedding_config = MODELS["embedding_models"][self.active_embedding]
        self.model_type = self.embedding_config.get("type", "local")
        
        # 初始化本地模型
        if self.model_type == "local":
            # 根据模型名称选择合适的模型
            model_name = self.embedding_config.get("model_name", "clip-ViT-B-32")
            print(f"正在加载本地模型: {model_name}")
            
            if model_name == "clip-ViT-B-32":
                # 多模态模型，支持图像和文本
                self.model = SentenceTransformer("clip-ViT-B-32")
                self.is_multimodal = True
            elif model_name == "OFA-Sys/chinese-clip-vit-base-patch16":
                # Chinese CLIP模型，需要特殊处理
                self._init_chinese_clip()
                self.is_multimodal = True
                self.is_chinese_clip = True
            else:
                # 纯文本模型，更适合文本检索
                self.model = SentenceTransformer(model_name)
                self.is_multimodal = False
                
            self.device = self.embedding_config["device"]
            self.batch_size = self.embedding_config["batch_size"]
            
            if self.device == "cuda" and torch.cuda.is_available():
                self.model = self.model.to("cuda")
        
        # 初始化API客户端
        elif self.model_type == "api":
            self.api_key = self.embedding_config.get("api_key")
            self.model_id = self.embedding_config.get("model_id")
            self.encoding_format = self.embedding_config.get("encoding_format", "float")
            
            if not self.api_key:
                raise ValueError(f"未提供API密钥，无法初始化{self.active_embedding}模型")
                
            # 初始化火山引擎客户端
            if self.active_embedding == "volcengine":
                self.client = Ark(api_key=self.api_key)
            
            # 初始化阿里DashScope
            elif self.active_embedding == "dashscope":
                # 设置DashScope API密钥
                dashscope.api_key = self.api_key
                print(f"阿里DashScope多模态模型初始化成功: {self.model_id}")
    
    def _init_chinese_clip(self):
        """初始化Chinese CLIP模型"""   
        model_name = self.embedding_config.get("model_name")
        print(f"正在加载Chinese CLIP模型: {model_name}")
        
        try:
            self.chinese_clip_model = ChineseCLIPModel.from_pretrained(model_name)
            self.chinese_clip_processor = ChineseCLIPProcessor.from_pretrained(model_name)
            
            # 如果有GPU可用，将模型移到GPU
            if self.embedding_config.get("device") == "cuda" and torch.cuda.is_available():
                self.chinese_clip_model = self.chinese_clip_model.to("cuda")
                
            print(f"Chinese CLIP模型加载成功")
        except Exception as e:
            raise ValueError(f"加载Chinese CLIP模型失败: {e}")
    
    def embed_text(self, text: str) -> List[float]:
        """将单个文本转换为向量"""
        if self.model_type == "local":
            # 检查是否是Chinese CLIP模型
            if hasattr(self, 'is_chinese_clip') and self.is_chinese_clip:
                return self._embed_text_chinese_clip(text)
            else:
                embedding = self.model.encode(
                    text,
                    convert_to_tensor=True,
                    device=self.device
                )
                return embedding.cpu().numpy().tolist()
        elif self.model_type == "api":
            if self.active_embedding == "volcengine":
                return self._embed_text_by_volc(text)
            elif self.active_embedding == "dashscope":
                return self._embed_text_by_dashscope(text)
            else:
                raise ValueError(f"不支持的API模型: {self.active_embedding}")
        else:
            raise ValueError(f"不支持的模型类型: {self.model_type}")
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量将文本转换为向量"""
        if not texts:
            return []
            
        if self.model_type == "local":
            # 检查是否是Chinese CLIP模型
            if hasattr(self, 'is_chinese_clip') and self.is_chinese_clip:
                # Chinese CLIP需要特殊处理批量编码
                results = []
                for text in texts:
                    results.append(self._embed_text_chinese_clip(text))
                return results
            else:
                embeddings = self.model.encode(
                    texts,
                    batch_size=self.batch_size,
                    convert_to_tensor=True,
                    device=self.device,
                    show_progress_bar=True
                )
                return embeddings.cpu().numpy().tolist()
        elif self.model_type == "api":
            if self.active_embedding == "volcengine":
                # 对于API模型，可能需要分批处理
                results = []
                for text in texts:
                    results.append(self._embed_text_by_volc(text))
                return results
            elif self.active_embedding == "dashscope":
                # 对于DashScope，可能需要分批处理
                results = []
                for text in texts:
                    results.append(self._embed_text_by_dashscope(text))
                return results
            else:
                raise ValueError(f"不支持的API模型: {self.active_embedding}")
        else:
            raise ValueError(f"不支持的模型类型: {self.model_type}")
    
    def embed_image(self, image_path_or_url_or_base64: str) -> List[float]:
        """将单个图像转换为向量
        
        Args:
            image_path_or_url_or_base64: 图像路径、URL或base64字符串
            
        Returns:
            图像的嵌入向量
        """
        if self.model_type == "local":
            # 检查当前模型是否支持多模态
            if not hasattr(self, 'is_multimodal') or not self.is_multimodal:
                # 如果是纯文本模型，无法直接处理图像，返回零向量或抛出异常
                print(f"警告: 当前模型 {self.active_embedding} 不支持图像编码，返回零向量")
                # 获取模型的向量维度
                sample_text_embedding = self.embed_text("sample")
                return [0.0] * len(sample_text_embedding)
            
            # 检查是否是Chinese CLIP模型
            if hasattr(self, 'is_chinese_clip') and self.is_chinese_clip:
                return self._embed_image_chinese_clip(image_path_or_url_or_base64)
            else:
                # 处理不同类型的图像输入
                image = self._process_image_input(image_path_or_url_or_base64)
                if image is None:
                    raise ValueError(f"无法处理图像输入: {image_path_or_url_or_base64}")
                    
                embedding = self.model.encode(
                    image,
                    convert_to_tensor=True,
                    device=self.device
                )
                return embedding.cpu().numpy().tolist()
        elif self.model_type == "api":
            if self.active_embedding == "volcengine":
                return self._embed_image_by_volc(image_path_or_url_or_base64)
            elif self.active_embedding == "dashscope":
                return self._embed_image_by_dashscope(image_path_or_url_or_base64)
            else:
                raise ValueError(f"不支持的API模型: {self.active_embedding}")
        else:
            raise ValueError(f"不支持的模型类型: {self.model_type}")
    
    def embed_image_batch(self, image_paths_or_urls_or_base64s: List[str]) -> List[List[float]]:
        """批量将图像转换为向量
        
        Args:
            image_paths_or_urls_or_base64s: 图像路径、URL或base64字符串列表
            
        Returns:
            图像的嵌入向量列表
        """
        if not image_paths_or_urls_or_base64s:
            return []
            
        if self.model_type == "local":
            # 检查当前模型是否支持多模态
            if not hasattr(self, 'is_multimodal') or not self.is_multimodal:
                # 如果是纯文本模型，无法直接处理图像，返回零向量列表
                print(f"警告: 当前模型 {self.active_embedding} 不支持图像编码，返回零向量列表")
                # 获取模型的向量维度
                sample_text_embedding = self.embed_text("sample")
                zero_vector = [0.0] * len(sample_text_embedding)
                return [zero_vector] * len(image_paths_or_urls_or_base64s)
            
            # 检查是否是Chinese CLIP模型
            if hasattr(self, 'is_chinese_clip') and self.is_chinese_clip:
                # Chinese CLIP需要特殊处理批量图像编码
                results = []
                for img_input in image_paths_or_urls_or_base64s:
                    results.append(self._embed_image_chinese_clip(img_input))
                return results
            else:
                images = []
                for img_input in image_paths_or_urls_or_base64s:
                    image = self._process_image_input(img_input)
                    if image is not None:
                        images.append(image)
                
                if not images:
                    return []
                    
                embeddings = self.model.encode(
                    images,
                    batch_size=self.batch_size,
                    convert_to_tensor=True,
                    device=self.device,
                    show_progress_bar=True
                )
                return embeddings.cpu().numpy().tolist()
        elif self.model_type == "api":
            if self.active_embedding == "volcengine":
                # 对于API模型，可能需要分批处理
                results = []
                for img_input in image_paths_or_urls_or_base64s:
                    results.append(self._embed_image_by_volc(img_input))
                return results
            elif self.active_embedding == "dashscope":
                # 对于DashScope，可能需要分批处理
                results = []
                for img_input in image_paths_or_urls_or_base64s:
                    results.append(self._embed_image_by_dashscope(img_input))
                return results
            else:
                raise ValueError(f"不支持的API模型: {self.active_embedding}")
        else:
            raise ValueError(f"不支持的模型类型: {self.model_type}")
    
    def embed_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理文档列表，添加向量字段，支持文本和图片chunk
        
        Args:
            documents: 文档列表，每个文档是一个字典，包含"content"和"type"字段
                       type可以是"text"或"image"
                       对于image类型，content应该是图像路径、URL或base64字符串
                       
        Returns:
            添加了embedding字段的文档列表
        """
        # 分离文本和图像文档
        text_docs = []
        image_docs = []
        text_indices = []
        image_indices = []
        
        for i, doc in enumerate(documents):
            doc_type = doc.get("type", "text")
            if doc_type == "text":
                text_docs.append(doc)
                text_indices.append(i)
            elif doc_type == "image":
                image_docs.append(doc)
                image_indices.append(i)
        
        # 处理文本文档
        if text_docs:
            texts = [doc["content"] for doc in text_docs]
            
            # 保存文本内容到文件
            import json
            output_dir = "logs"
            os.makedirs(output_dir, exist_ok=True)
            
            # 保存texts列表到JSON文件
            texts_file = os.path.join(output_dir, f"texts_content.json")
            try:
                with open(texts_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "total_texts": len(texts),
                        "texts": texts
                    }, f, ensure_ascii=False, indent=2)
                print(f"已保存 {len(texts)} 个文本内容到: {texts_file}")
            except Exception as e:
                print(f"保存文本内容失败: {e}")
            
            text_embeddings = self.embed_batch(texts)
            for doc, embedding in zip(text_docs, text_embeddings):
                doc["embedding"] = embedding
        
        # 处理图像文档
        if image_docs:
            image_paths = []
            for doc in image_docs:
                img_path = doc.get("content")
                if not img_path and "metadata" in doc:
                    # 如果content为空但metadata中有img_path，使用img_path
                    img_path = doc["metadata"].get("img_path")
                image_paths.append(img_path)
            
            image_embeddings = self.embed_image_batch(image_paths)
            for doc, embedding in zip(image_docs, image_embeddings):
                doc["embedding"] = embedding
        
        # 合并结果
        result = documents.copy()
        for i, doc in zip(text_indices, text_docs):
            result[i] = doc
        for i, doc in zip(image_indices, image_docs):
            result[i] = doc
        
        return result
    
    def _process_image_input(self, image_input: str) -> Optional[Image.Image]:
        """处理不同类型的图像输入，返回PIL Image对象
        
        Args:
            image_input: 图像路径、URL或base64字符串
            
        Returns:
            PIL Image对象，如果处理失败则返回None
        """
        try:
            # 检查是否是本地文件路径
            if os.path.exists(image_input):
                return Image.open(image_input)
            
            # 检查是否是base64编码
            if image_input.startswith('data:image'):
                # 从base64字符串中提取实际的base64编码部分
                base64_data = image_input.split(',', 1)[1]
                # 解码base64为二进制数据
                image_bytes = base64.b64decode(base64_data)
                return Image.open(io.BytesIO(image_bytes))
            
            # 检查是否是URL
            if image_input.startswith(('http://', 'https://')):
                response = requests.get(image_input)
                response.raise_for_status()
                return Image.open(io.BytesIO(response.content))
            
            # 尝试作为纯base64处理
            try:
                image_bytes = base64.b64decode(image_input)
                return Image.open(io.BytesIO(image_bytes))
            except:
                pass
            
            return None
        except Exception as e:
            print(f"处理图像输入失败: {str(e)}")
            return None
    
    def _embed_text_by_volc(self, text: str) -> List[float]:
        """调用火山API将文本转为embedding向量
        
        Args:
            text: 文本字符串
            
        Returns:
            embedding向量（list[float]），失败返回空列表
        """
        try:
            resp = self.client.multimodal_embeddings.create(
                model=self.model_id,
                encoding_format=self.encoding_format,
                input=[{"text": text, "type": "text"}]
            )
            embedding = resp.data["embedding"] if isinstance(resp.data, dict) else resp.data[0].embedding
            return embedding
        except Exception as e:
            print(f"火山文本embedding API调用失败: {e}")
            return []
    
    def _embed_image_by_volc(self, image_input: str) -> List[float]:
        """调用火山API将图像转为embedding向量
        
        Args:
            image_input: 图像路径、URL或base64字符串
            
        Returns:
            embedding向量（list[float]），失败返回空列表
        """
        try:
            # 处理不同类型的图像输入
            if os.path.exists(image_input):
                # 本地文件路径
                with open(image_input, "rb") as f:
                    img_base64 = base64.b64encode(f.read()).decode()
                base64_data = f"data:image/jpeg;base64,{img_base64}"
            elif image_input.startswith('data:image'):
                # 已经是base64格式
                base64_data = image_input
            elif image_input.startswith(('http://', 'https://')):
                # URL
                response = requests.get(image_input)
                response.raise_for_status()
                img_base64 = base64.b64encode(response.content).decode()
                base64_data = f"data:image/jpeg;base64,{img_base64}"
            else:
                # 尝试作为纯base64处理
                try:
                    base64.b64decode(image_input)
                    base64_data = image_input
                except:
                    print(f"无法处理图像输入: {image_input}")
                    return []
            
            # 调用API
            resp = self.client.multimodal_embeddings.create(
                model=self.model_id,
                encoding_format=self.encoding_format,
                input=[{"image_url": {"url": base64_data}, "type": "image_url"}]
            )
            embedding = resp.data["embedding"] if isinstance(resp.data, dict) else resp.data[0].embedding
            return embedding
        except Exception as e:
            print(f"火山图片embedding API调用失败: {e}")
            return []
    
    def _embed_text_chinese_clip(self, text: str) -> List[float]:
        """使用Chinese CLIP模型将文本转为embedding向量
        
        Args:
            text: 文本字符串
            
        Returns:
            embedding向量（list[float]）
        """
        try:
            # 使用Chinese CLIP processor处理文本
            inputs = self.chinese_clip_processor(text=text, return_tensors="pt", padding=True, truncation=True, max_length=512)
            
            # 如果模型在GPU上，将输入也移到GPU
            if self.device == "cuda" and torch.cuda.is_available():
                inputs = {k: v.to("cuda") for k, v in inputs.items()}
            
            # 获取文本特征
            with torch.no_grad():
                text_features = self.chinese_clip_model.get_text_features(**inputs)
                # 归一化
                text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)
            
            return text_features.cpu().numpy().tolist()[0]
        except Exception as e:
            print(f"Chinese CLIP文本编码失败: {e}")
            return []
    
    def _embed_image_chinese_clip(self, image_input: str) -> List[float]:
        """使用Chinese CLIP模型将图像转为embedding向量
        
        Args:
            image_input: 图像路径、URL或base64字符串
            
        Returns:
            embedding向量（list[float]）
        """
        try:
            # 处理图像输入
            image = self._process_image_input(image_input)
            if image is None:
                raise ValueError(f"无法处理图像输入: {image_input}")
            
            # 使用Chinese CLIP processor处理图像
            inputs = self.chinese_clip_processor(images=image, return_tensors="pt")
            
            # 如果模型在GPU上，将输入也移到GPU
            if self.device == "cuda" and torch.cuda.is_available():
                inputs = {k: v.to("cuda") for k, v in inputs.items()}
            
            # 获取图像特征
            with torch.no_grad():
                image_features = self.chinese_clip_model.get_image_features(**inputs)
                # 归一化
                image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
            
            return image_features.cpu().numpy().tolist()[0]
        except Exception as e:
            print(f"Chinese CLIP图像编码失败: {e}")
            return [] 
    
    def _embed_text_by_dashscope(self, text: str) -> List[float]:
        """使用阿里DashScope将文本转为embedding向量
        
        Args:
            text: 文本字符串
            
        Returns:
            embedding向量（list[float]），失败返回空列表
        """
        try:
            # 构建输入
            input_data = [{'text': text}]
            
            # 调用模型接口
            resp = dashscope.MultiModalEmbedding.call(
                model=self.model_id,
                input=input_data
            )
            
            # 检查响应状态
            if resp.status_code == HTTPStatus.OK:
                # 提取embedding
                embedding = resp.output['embeddings'][0]['embedding']
                return embedding
            else:
                print(f"DashScope API调用失败: {resp.code}, {resp.message}")
                return []
        except Exception as e:
            print(f"DashScope文本embedding API调用失败: {e}")
            return []
    
    def _embed_image_by_dashscope(self, image_input: str) -> List[float]:
        """使用阿里DashScope将图像转为embedding向量
        
        Args:
            image_input: 图像路径、URL或base64字符串
            
        Returns:
            embedding向量（list[float]），失败返回空列表
        """
        try:
            # 处理不同类型的图像输入
            if os.path.exists(image_input):
                # 本地文件路径，需要上传或转为URL
                # DashScope目前只支持URL，所以这里需要先将本地图片上传到某个可访问的URL
                # 这里简化处理，假设有上传函数
                from src.utils.image_tools import upload_image
                image_url = upload_image(image_input)
                if not image_url:
                    print(f"无法上传本地图片: {image_input}")
                    return []
            elif image_input.startswith('data:image'):
                # base64格式不直接支持，需要转换
                print(f"DashScope不直接支持base64格式图片，请提供URL")
                return []
            elif image_input.startswith(('http://', 'https://')):
                # URL格式，直接使用
                image_url = image_input
            else:
                print(f"无法处理图像输入: {image_input}")
                return []
            
            # 构建输入
            input_data = [{'image': image_url}]
            
            # 调用模型接口
            resp = dashscope.MultiModalEmbedding.call(
                model=self.model_id,
                input=input_data
            )
            
            # 检查响应状态
            if resp.status_code == HTTPStatus.OK:
                # 提取embedding
                embedding = resp.output['embeddings'][0]['embedding']
                return embedding
            else:
                print(f"DashScope API调用失败: {resp.code}, {resp.message}")
                return []
        except Exception as e:
            print(f"DashScope图片embedding API调用失败: {e}")
            return [] 