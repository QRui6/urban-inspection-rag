"""
RAG系统主程序入口
"""
import os
import base64
import requests
import json
from typing import List, Dict, Any, Optional, Tuple
from src.document_loader.loader import DocumentLoader
from src.embedding.embedder import Embedder
from src.storage.chroma_store import ChromaStore
from src.retrieval.retriever import Retriever
from src.reranker.reranker import Reranker
from src.generator.generator import Generator
from config.config import RAW_DATA_DIR, GENERATOR_CONFIG, MODELS, ACTIVE_MODELS, PROMPT_CONFIG
from src.document_loader.pdf2md import batch_pdf_to_markdown
from src.document_loader.md_loader_optimized import MarkdownChunkLoader
from src.document_loader.vlm_batch import batch_vlm_describe
from openai import OpenAI
from google import genai
from google.genai import types
from src.utils.image_tools import upload_image, image_to_base64, extract_image_url
from volcenginesdkarkruntime import Ark
import datetime


class RAGSystem:
    """RAG系统主类"""
    
    def __init__(self, dual_retrieval: bool = True):
        self.document_loader = DocumentLoader()
        self.embedder = Embedder()
        self.es_store = ChromaStore()
        self.reranker = Reranker()
        self.generator = Generator()
        
        # 是否启用双路检索
        self.dual_retrieval = dual_retrieval
        
        # 初始化模型客户端
        self.vision_clients = {}
        self.language_clients = {}
        
        # 初始化视觉模型客户端
        self._init_vision_clients()
        
        # 初始化语言模型客户端
        self._init_language_clients()
        
    def _init_vision_clients(self):
        """初始化视觉模型客户端"""
        # 获取当前激活的视觉模型
        active_vision = ACTIVE_MODELS.get("vision")
        if not active_vision or active_vision not in MODELS["vision_models"]:
            print(f"警告: 未配置有效的视觉模型或模型'{active_vision}'不存在")
            return
            
        # 获取视觉模型配置
        vision_models = MODELS["vision_models"]
        
        # 初始化所有已配置的视觉模型
        for model_name, model_config in vision_models.items():
            try:
                if model_config["type"] == "openai":
                    # 初始化OpenAI兼容的视觉模型（如通义千问）
                    self.vision_clients[model_name] = OpenAI(
                        api_key=model_config["api_key"],
                        base_url=model_config["base_url"],
                    )
                    print(f"已初始化视觉模型: {model_name} ({model_config['description']})")
                    
                elif model_config["type"] == "google":
                    # 初始化Google Gemini视觉模型
                    try:
                        self.vision_clients[model_name] = genai.Client(api_key=model_config["api_key"])
                        print(f"已初始化视觉模型: {model_name} ({model_config['description']})")
                    except Exception as e:
                        print(f"初始化Google视觉模型{model_name}失败: {e}")
                elif model_config["type"] == "google":
                    print(f"警告: Google API库不可用，无法初始化{model_name}视觉模型")
                        
            except Exception as e:
                print(f"初始化视觉模型{model_name}失败: {e}")
    
    def _init_language_clients(self):
        """初始化语言模型客户端"""
        # 获取当前激活的语言模型
        active_language = ACTIVE_MODELS.get("language")
        if not active_language or active_language not in MODELS["language_models"]:
            print(f"警告: 未配置有效的语言模型或模型'{active_language}'不存在")
            return
            
        # 获取语言模型配置
        language_models = MODELS["language_models"]
        
        # 初始化所有已配置的语言模型
        for model_name, model_config in language_models.items():
            try:
                if model_config["type"] == "openai":
                    # 初始化OpenAI兼容的语言模型（如火山引擎）
                    self.language_clients[model_name] = OpenAI(
                        api_key=model_config["api_key"],
                        base_url=model_config["base_url"],
                    )
                    print(f"已初始化语言模型: {model_name} ({model_config['description']})")
                    
                elif model_config["type"] == "google":
                    # 初始化Google Gemini语言模型
                    try:
                        self.language_clients[model_name] = genai.Client(api_key=model_config["api_key"])
                        print(f"已初始化语言模型: {model_name} ({model_config['description']})")
                    except Exception as e:
                        print(f"初始化Google语言模型{model_name}失败: {e}")
                elif model_config["type"] == "google":
                    print(f"警告: Google API库不可用，无法初始化{model_name}语言模型")
                        
            except Exception as e:
                print(f"初始化语言模型{model_name}失败: {e}")
    
    def analyze_image(self, img_input: str, prompt: str) -> Tuple[Optional[str], Optional[str]]:
        """使用配置的视觉模型分析图像
        
        Args:
            img_input: 图片URL或base64编码
            prompt: 分析提示词
            
        Returns:
            Tuple[str, str]: (分析结果文本, 使用的模型名称)
        """
        # 获取当前激活的视觉模型
        active_vision = ACTIVE_MODELS.get("vision")
        if not active_vision or active_vision not in self.vision_clients:
            print(f"错误: 未找到有效的视觉模型'{active_vision}'")
            return None, None
            
        # 尝试使用主视觉模型
        model_config = MODELS["vision_models"].get(active_vision)
        analysis_text = None
        model_used = None
        # 尝试主视觉模型
        try:
            if model_config["type"] == "openai":
                analysis_text = self._analyze_with_openai(active_vision, img_input, prompt, model_config)
                model_used = active_vision
            elif model_config["type"] == "google":
                analysis_text = self._analyze_with_google(active_vision, img_input, prompt, model_config)
                model_used = active_vision
        except Exception as e:
            print(f"主视觉模型 {active_vision} 分析失败: {e}")
        
        # 如果主模型失败，尝试其他可用模型
        if not analysis_text:
            for model_name, config in MODELS["vision_models"].items():
                if model_name == active_vision:  # 跳过已尝试的主模型
                    continue
                    
                if model_name in self.vision_clients:
                    try:
                        print(f"尝试使用备用视觉模型: {model_name}")
                        if config["type"] == "openai":
                            analysis_text = self._analyze_with_openai(model_name, img_input, prompt, config)
                        elif config["type"] == "google":
                            analysis_text = self._analyze_with_google(model_name, img_input, prompt, config)
                            
                        if analysis_text:
                            model_used = f"{model_name} (备用)"
                            break
                    except Exception as e:
                        print(f"备用视觉模型 {model_name} 分析失败: {e}")
        
        return analysis_text, model_used
        
    def _analyze_with_openai(self, model_name: str, img_input: str, prompt: str, config: Dict) -> Optional[str]:
        """使用OpenAI兼容的API分析图像"""
        client = self.vision_clients[model_name]
        
        # 判断输入是URL还是base64
        is_base64 = img_input.startswith('data:image')
        
        # 使用OpenAI兼容API调用视觉模型
        completion = client.chat.completions.create(
            model=config["model_id"],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": img_input}},
                        {"type": "text", "text": prompt}
                    ]
                }
            ],
            timeout=30
        )
        return completion.choices[0].message.content
    
    def _analyze_with_google(self, model_name: str, img_input: str, prompt: str, config: Dict) -> Optional[str]:
        """使用Google API分析图像"""
        print(f"使用Google API分析图像: {config['model_id']}")
        genai_client = self.vision_clients[model_name]
        
        try:
            # 判断输入是URL还是base64
            if img_input.startswith('data:image'):
                # 从base64字符串中提取实际的base64编码部分
                base64_data = img_input.split(',', 1)[1]
                # 解码base64为二进制数据
                image_bytes = base64.b64decode(base64_data)
                
                # 确定MIME类型
                mime_type = 'image/jpeg'  # 默认
                if img_input.startswith('data:image/png'):
                    mime_type = 'image/png'
                elif img_input.startswith('data:image/webp'):
                    mime_type = 'image/webp'
                elif img_input.startswith('data:image/gif'):
                    mime_type = 'image/gif'
                
                # 使用types.Part.from_bytes创建图像部分
                image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                contents = [image_part, prompt]
            else:
                # 处理URL图片 - 下载图片数据
                response = requests.get(img_input)
                response.raise_for_status()
                image_bytes = response.content
                
                # 根据URL推断MIME类型
                mime_type = 'image/jpeg'  # 默认
                if img_input.lower().endswith('.png'):
                    mime_type = 'image/png'
                elif img_input.lower().endswith('.webp'):
                    mime_type = 'image/webp'
                elif img_input.lower().endswith('.gif'):
                    mime_type = 'image/gif'
                
                # 使用types.Part.from_bytes创建图像部分
                image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                contents = [prompt, image_part]
            # 生成内容
            response = genai_client.models.generate_content(
                model = config["model_id"],
                contents = contents
            )
            # print(response.text)
            # 提取分析结果
            if hasattr(response, 'text'):
                return response.text
            else:
                return str(response)
                
        except Exception as e:
            print(f"Google API分析图片失败: {e}")
            return None
    
    def process_documents(self, directory: str = None) -> bool:
        """处理文档目录"""
        if directory is None:
            directory = RAW_DATA_DIR
            
        print("开始加载文档...")
        # 在处理文档前先删除索引
        self.es_store.delete_index()  # 删除现有索引
        documents = self.document_loader.load_directory(directory)
        if not documents:
            print("没有找到可处理的文档")
            return False
            
        print(f"加载了 {len(documents)} 个文档块")
        
        print("开始生成向量...")
        documents = self.embedder.embed_documents(documents)
        
        print("开始存储到Chroma...")
        success = self.es_store.add_documents(documents)
        if not success:
            print("存储文档时出错")
            return False
            
        print(f"成功存储 {len(documents)} 个文档块")
        return True
    
    def query(self, query: str, img_input: str = None) -> dict:
        """处理查询，支持纯文本或文本+图片（URL或base64），并结合向量库检索结果
        
        返回格式:
        {
            "visual_analysis": "视觉分析结果", # 如果有图片输入
            "answer": "最终生成的完整回答",
            "status": "success/processing/error",
            "models_used": {
                "vision": "使用的视觉模型名称",
                "language": "使用的语言模型名称"
            }
        }
        """
        result = {
            "visual_analysis": None,
            "answer": None,
            "status": "processing",
            "models_used": {
                "vision": None,
                "language": ACTIVE_MODELS.get("language")
            }
        }
        
        # 如果包含图片，先用视觉模型处理，然后结合向量检索结果
        if img_input:
            # 定义视觉模型提示词
            # vl_prompt = "你是一位建筑安全专家，分析以下施工现场图片并识别潜在的安全隐患以及隐患位置。注意不要讲你没有看到的信息。"
            # vl_prompt = """你是一位城市体检专家，分析以下城市建筑图片并列出图片属于哪种安全隐患（请从下列指标中，选择一项最符合当前情况的类型：
            #                 存在结构安全隐患的住宅
            #                 存在燃气安全隐患的住宅
            #                 存在楼道安全隐患的住宅
            #                 存在围护安全隐患的住宅
            #                 非成套住宅
            #                 存在管线管道破损的住宅
            #                 需要进行适老化改造的住宅
            #                 需要进行节能改造的住宅
            #                 需要进行数字化改造的住宅）
            #                 并分析体检依据，注意不要讲你没有看到的信息。"""
            vl_prompt = PROMPT_CONFIG["vision_analysis"]["city_inspection"]
            # 调用视觉分析方法
            vl_text, model_used = self.analyze_image(img_input, vl_prompt)
            result["models_used"]["vision"] = model_used
            
            # 如果视觉分析失败，尝试使用本地文件方式
            if not vl_text and os.path.exists(img_input):
                    print("尝试使用base64方式调用视觉模型...")
                    try:
                        base64_image = image_to_base64(img_input)
                        if base64_image:
                            vl_text, model_used = self.analyze_image(base64_image, vl_prompt)
                            result["models_used"]["vision"] = f"{model_used} (本地文件转base64)"
                    except Exception as e:
                        print(f"本地文件转base64调用失败: {e}")
            
            # 如果所有视觉分析方法都失败
            if not vl_text:
                result["status"] = "error"
                result["answer"] = "图片分析失败，无法提供安全隐患评估。"
                return result
            
            # 设置视觉分析结果到返回对象中
            result["visual_analysis"] = vl_text
            
            # 使用视觉模型输出作为查询，检索相关文档
            if self.dual_retrieval:
                # ===== 双路检索开始 =====
                print("开始双路检索...")
                
                # 路径1：使用视觉分析文本进行检索
                print("路径1：使用视觉分析文本进行检索...")
                vl_vector = self.embedder.embed_text(vl_text)
                text_documents = self.es_store.search(vl_text, vl_vector)
                # 保存文本检索结果
                self.save_search_results(vl_text, text_documents, img_input, prefix="text_vector_search_result", search_type="text")
                
                # 路径2：使用图像直接进行检索
                print("路径2：使用图像向量直接检索...")
                try:
                    # 获取图像向量
                    image_vector = self.embedder.embed_image(img_input)
                    # 使用图像向量检索
                    image_documents = self.es_store.search("", image_vector)
                    print(f"图像检索结果: {len(image_documents)} 条")
                    # 保存图像检索结果
                    self.save_search_results("图像查询", image_documents, img_input, prefix="image_vector_search_result", search_type="image")
                except Exception as e:
                    print(f"图像向量检索失败: {e}")
                    image_documents = []
                
                # 融合两路检索结果
                if text_documents or image_documents:
                    print("融合两路检索结果...")
                    merged_documents = self._merge_search_results(text_documents, image_documents)
                    print(f"融合后的结果数量: {len(merged_documents)} 条")
                    # 保存融合结果
                    self.save_search_results(f"融合查询(文本+图像)", merged_documents, img_input, prefix="merged_search_result", search_type="merged")
                    
                    # 重排序
                    reranked_docs = self.reranker.rerank(vl_text, merged_documents)
                    print(f"重排序后的结果数量: {len(reranked_docs)} 条")
                    
                    # 保存最终检索结果到日志目录
                    self.save_search_results(vl_text, reranked_docs, img_input, prefix="final_search_result", search_type="final")
                else:
                    print("两路检索均未找到相关内容")
                    result["status"] = "success"
                    result["answer"] = f"分析结果：\n\n{vl_text}\n\n未在知识库中找到相关的法规依据。请咨询专业人士进行进一步评估。"
                    return result
                # ===== 双路检索结束 =====
            else:
                # 传统单路检索
                print("使用传统单路检索...")
                vl_vector = self.embedder.embed_text(vl_text)
                documents = self.es_store.search(vl_text, vl_vector)
                
                if not documents:
                    print("未找到相关的知识库内容")
                    result["status"] = "success"
                    result["answer"] = f"分析结果：\n\n{vl_text}\n\n未在知识库中找到相关的法规依据。请咨询专业人士进行进一步评估。"
                    return result
                
                # 重排序
                reranked_docs = self.reranker.rerank(vl_text, documents)
                print(f"找到相关知识库内容: {len(reranked_docs)} 条")
                
                # 保存检索结果到日志目录
                self.save_search_results(vl_text, reranked_docs, img_input, prefix="visual_search_result")
            
            # 创建包含视觉分析结果的自定义文档对象
            img_source = "视觉模型分析图片"
            if not img_input.startswith('data:image'):
                img_source = img_input
                
            # 这将作为第一个参考文档出现在引用中
            vl_document = {
                "content": f"视觉模型分析结果：{vl_text}",
                "metadata": {
                    "source": "视觉分析",
                    "img_path": img_source
                }
            }
            
            # 将视觉分析结果添加到文档列表的开头
            final_docs = [vl_document] + reranked_docs
            
            # 构建结合视觉分析的系统提示词
            system_prompt = PROMPT_CONFIG["system"]["city_inspection_report"]
            # 构建用户提示词，包含原始问题
            user_query = PROMPT_CONFIG["user"]["query_template"].format(query=query)
            
            # 调用Generator生成最终回答
            print("正在使用Generator生成最终回答...")
            
            # 使用Generator生成回答，这将自动处理引用信息
            # 我们为Generator临时添加系统提示词
            original_system_prompt = self.generator._system_prompt if hasattr(self.generator, '_system_prompt') else None
            
            # 保存原始的创建提示词方法
            original_create_prompt = self.generator._create_prompt
            
            try:
                # 临时修改Generator的提示词创建方法，加入系统提示
                def custom_create_prompt(generator_self, q, docs):
                    # 提取文档内容
                    text_contents = []
                    image_contents = []
                    
                    # 用户照片（第一个文档是视觉分析结果，包含用户照片路径）
                    user_photo = ""
                    if docs and "metadata" in docs[0] and "img_path" in docs[0]["metadata"]:
                        user_photo = docs[0]["metadata"]["img_path"]
                    
                    # 处理文档内容，区分文本和图片
                    for i, doc in enumerate(docs):
                        content = doc["content"]
                        metadata = doc.get("metadata", {})
                        
                        # 第一个文档是视觉分析结果
                        if i == 0:
                            text_contents.append(f"[视觉分析结果]: \"{content}\"")
                            continue
                            
                        # 检查是否为图片文档
                        is_image = False
                        if "type" in metadata and metadata["type"] == "image":
                            is_image = True
                        elif "img_path" in metadata and metadata["img_path"]:
                            is_image = True
                        
                        if is_image:
                            # 这是一个图片文档
                            img_path = metadata.get("img_path", "")
                            if img_path:
                                image_contents.append(f"[案例图片 {len(image_contents)+1}]: {img_path}")
                        else:
                            # 这是一个文本文档
                            source = metadata.get("source", "")
                            source_name = os.path.basename(source) if source else f"检索到的文本块 {len(text_contents)}"
                            text_contents.append(f"[{source_name}]: \"{content}\"")
                    
                    # 构建知识库文本依据部分
                    text_context = "\n".join(text_contents)
                    
                    # 获取系统提示词并替换占位符
                    modified_system_prompt = system_prompt
                    
                    # 替换用户照片占位符
                    modified_system_prompt = modified_system_prompt.replace("<user_photo_placeholder>", user_photo)
                    
                    # 提取文档内容用于替换retrieved_chunk占位符
                    text_docs = []
                    for i, doc in enumerate(docs):
                        if i == 0:  # 跳过第一个文档（视觉分析结果）
                            continue
                        
                        metadata = doc.get("metadata", {})
                        
                        # 判断是否为图片文档：通过metadata中的img_path或chunk_type字段
                        is_image_doc = (
                            metadata.get("img_path") or 
                            metadata.get("chunk_type") == "indicator_image"
                        )
                        
                        if is_image_doc and metadata.get("context"):
                            # 图片文档，使用context作为内容
                            text_doc = {
                                "content": metadata["context"],
                                "metadata": metadata.copy()
                            }
                            text_docs.append(text_doc)
                        elif not is_image_doc and doc.get("content"):
                            # 文本文档，直接使用content
                            text_docs.append(doc)
                    
                    # 替换retrieved_chunk占位符
                    if len(text_docs) >= 1:
                        chunk_1_content = text_docs[0]["content"]
                        chunk_1_source = text_docs[0].get("metadata", {}).get("source", "未知来源")
                        modified_system_prompt = modified_system_prompt.replace("{retrieved_chunk_1_content}", chunk_1_content)
                        modified_system_prompt = modified_system_prompt.replace("{retrieved_chunk_1_metadata}", os.path.basename(chunk_1_source) if chunk_1_source != "未知来源" else chunk_1_source)
                    else:
                        modified_system_prompt = modified_system_prompt.replace("{retrieved_chunk_1_content}", "未找到相关文本内容")
                        modified_system_prompt = modified_system_prompt.replace("{retrieved_chunk_1_metadata}", "无")
                    
                    if len(text_docs) >= 2:
                        chunk_2_content = text_docs[1]["content"]
                        chunk_2_source = text_docs[1].get("metadata", {}).get("source", "未知来源")
                        modified_system_prompt = modified_system_prompt.replace("{retrieved_chunk_2_content}", chunk_2_content)
                        modified_system_prompt = modified_system_prompt.replace("{retrieved_chunk_2_metadata}", os.path.basename(chunk_2_source) if chunk_2_source != "未知来源" else chunk_2_source)
                    else:
                        modified_system_prompt = modified_system_prompt.replace("{retrieved_chunk_2_content}", "")
                        modified_system_prompt = modified_system_prompt.replace("{retrieved_chunk_2_metadata}", "")
                    
                    # 构建知识库参考案例图片部分
                    case_photos = []
                    # 直接从image_documents中提取图片路径
                    for doc in image_documents[:2]:  # 只取前两张最相似的图片
                        metadata = doc.get("metadata", {})
                        img_path = metadata.get("img_path", "")
                        if img_path:
                            case_photos.append(img_path)

                    # 如果有案例图片，替换占位符
                    if len(case_photos) >= 1:
                        modified_system_prompt = modified_system_prompt.replace("<retrieved_case_photo_1_placeholder>", case_photos[0])
                    else:
                        modified_system_prompt = modified_system_prompt.replace("<retrieved_case_photo_1_placeholder>", "无相关案例图片")
                        
                    if len(case_photos) >= 2:
                        modified_system_prompt = modified_system_prompt.replace("<retrieved_case_photo_2_placeholder>", case_photos[1])
                    else:
                        modified_system_prompt = modified_system_prompt.replace("<retrieved_case_photo_2_placeholder>", "无相关案例图片")
                    
                    # 自定义提示词，结合视觉分析和知识库内容
                    prompt = f"{user_query}\n\n参考资料：\n{text_context}"
                    
                    # 保存修改后的系统提示词，供外部使用
                    generator_self._modified_system_prompt = modified_system_prompt
                    
                    return prompt
                
                # 临时设置系统提示词创建方法
                self.generator._create_prompt = custom_create_prompt.__get__(self.generator, type(self.generator))
                
                # 先调用一次create_prompt来获取修改后的系统提示词
                self.generator._create_prompt(query, final_docs)
                
                # 设置修改后的系统提示词
                self.generator._system_prompt = getattr(self.generator, "_modified_system_prompt", system_prompt)
                
                # 调用generator生成回答
                answer = self.generator.generate(query, final_docs)
                
            finally:
                # 恢复原始设置
                if original_system_prompt is not None:
                    self.generator._system_prompt = original_system_prompt
                self.generator._create_prompt = original_create_prompt
            
            result["answer"] = answer
            result["status"] = "success"
            return result
            
        # 没有图片的情况，走传统RAG流程
        else:
            # 生成查询向量
            query_vector = self.embedder.embed_text(query)
            # 检索相关文档
            documents = self.es_store.search(query, query_vector)
            if not documents:
                result["status"] = "success"
                result["answer"] = "抱歉，没有找到相关的参考信息。"
                return result
            # 重排序
            reranked_docs = self.reranker.rerank(query, documents)
            # 保存检索结果到日志目录
            self.save_search_results(query, reranked_docs, prefix="text_search_result")
            # 生成回答
            answer = self.generator.generate(query, reranked_docs)
            result["status"] = "success"
            result["answer"] = answer
            return result

    def complete_answer(self, query: str, img_input: str, visual_analysis: str) -> dict:
        """基于已有的视觉分析结果，生成最终答案
        
        Args:
            query: 用户原始问题
            img_input: 图片输入（URL或base64）
            visual_analysis: 已经生成好的视觉分析结果
            
        Returns:
            {
                "visual_analysis": "视觉分析结果",
                "answer": "最终生成的完整回答",
                "status": "success/error",
                "models_used": {
                    "vision": "使用的视觉模型名称",
                    "language": "使用的语言模型名称"
                }
            }
        """
        result = {
            "visual_analysis": visual_analysis,  # 添加视觉分析结果
            "answer": None,
            "status": "processing",
            "models_used": {
                "vision": None,
                "language": ACTIVE_MODELS.get("language")
            }
        }
        
        try:
            # 使用视觉分析结果作为查询，检索相关文档
            if self.dual_retrieval:
                # ===== 双路检索开始 =====
                print("开始双路检索...")
                
                # 路径1：使用视觉分析文本进行检索
                print("路径1：使用视觉分析文本进行检索...")
                vl_vector = self.embedder.embed_text(visual_analysis)
                text_documents = self.es_store.search(visual_analysis, vl_vector)
                print(f"文本检索结果: {len(text_documents)} 条")
                # 保存文本检索结果 - 统一前缀名称
                self.save_search_results(visual_analysis, text_documents, img_input, prefix="text_vector_search_result", search_type="text")
                
                # 路径2：使用图像直接进行检索
                print("路径2：使用图像向量直接检索...")
                try:
                    # 获取图像向量
                    image_vector = self.embedder.embed_image(img_input)
                    # 使用图像向量检索
                    image_documents = self.es_store.search("", image_vector)
                    print(f"图像检索结果: {len(image_documents)} 条")
                    # 保存图像检索结果 - 统一前缀名称
                    self.save_search_results("图像查询", image_documents, img_input, prefix="image_vector_search_result", search_type="image")
                except Exception as e:
                    print(f"图像向量检索失败: {e}")
                    image_documents = []
                
                # 融合两路检索结果
                if text_documents or image_documents:
                    print("融合两路检索结果...")
                    merged_documents = self._merge_search_results(text_documents, image_documents)
                    print(f"融合后的结果数量: {len(merged_documents)} 条")
                    # 保存融合结果 - 统一前缀名称
                    self.save_search_results(f"融合查询(文本+图像)", merged_documents, img_input, prefix="merged_search_result", search_type="merged")
                    
                    # 重排序
                    # reranked_docs = self.reranker.rerank(visual_analysis, merged_documents)
                    reranked_docs = merged_documents[:3]
                    print(f"重排序后的结果数量: {len(reranked_docs)} 条")
                    
                    # 保存最终检索结果到日志目录 - 统一前缀名称
                    self.save_search_results(visual_analysis, reranked_docs, img_input, prefix="final_search_result", search_type="final")
                else:
                    print("两路检索均未找到相关内容")
                    result["status"] = "success"
                    result["answer"] = f"分析结果：\n\n{visual_analysis}\n\n未在知识库中找到相关的法规依据。请咨询专业人士进行进一步评估。"
                    return result
                # ===== 双路检索结束 =====
            else:
                # 传统单路检索
                print("使用传统单路检索...")
                vl_vector = self.embedder.embed_text(visual_analysis)
                documents = self.es_store.search(visual_analysis, vl_vector)
                
                if not documents:
                    print("未找到相关的知识库内容")
                    result["status"] = "success"
                    result["answer"] = f"分析结果：\n\n{visual_analysis}\n\n未在知识库中找到相关的法规依据。请咨询专业人士进行进一步评估。"
                    return result
                
                # 重排序
                # reranked_docs = self.reranker.rerank(visual_analysis, documents)
                reranked_docs = documents[:3]
                print(f"找到相关知识库内容: {len(reranked_docs)} 条")
                # 保存检索结果到日志目录 - 统一前缀名称
                self.save_search_results(visual_analysis, reranked_docs, img_input, prefix="visual_search_result")
                
                # 对于单路检索，image_documents为空列表
                image_documents = []
            
            # 创建包含视觉分析结果的自定义文档对象
            img_source = "视觉模型分析图片"
            if not img_input.startswith('data:image'):
                img_source = img_input
                
            # 这将作为第一个参考文档出现在引用中
            vl_document = {
                "content": f"视觉模型分析结果：{visual_analysis}",
                "metadata": {
                    "source": "视觉分析",
                    "img_path": img_source
                }
            }
            
            # 将视觉分析结果添加到文档列表的开头
            final_docs = [vl_document] + reranked_docs
            
            # 构建结合视觉分析的系统提示词 - 使用与query函数相同的提示词
            system_prompt = PROMPT_CONFIG["system"]["city_inspection_report"]
            # 构建用户提示词，包含原始问题
            user_query = PROMPT_CONFIG["user"]["query_template"].format(query=query)
            
            # 调用Generator生成最终回答
            print("正在使用Generator生成最终回答...")
            
            # 使用Generator生成回答，这将自动处理引用信息
            # 我们为Generator临时添加系统提示词
            original_system_prompt = self.generator._system_prompt if hasattr(self.generator, '_system_prompt') else None
            
            # 保存原始的创建提示词方法
            original_create_prompt = self.generator._create_prompt
            
            try:
                # 临时修改Generator的提示词创建方法，加入系统提示 - 使用与query函数相同的逻辑
                def custom_create_prompt(generator_self, q, docs, img_docs=None):
                    # 如果没有传入img_docs参数，使用外层作用域的image_documents
                    if img_docs is None:
                        img_docs = image_documents
                    
                    # 提取文档内容
                    text_contents = []
                    image_contents = []
                    
                    # 用户照片（第一个文档是视觉分析结果，包含用户照片路径）
                    user_photo = ""
                    if docs and "metadata" in docs[0] and "img_path" in docs[0]["metadata"]:
                        user_photo = docs[0]["metadata"]["img_path"]
                    
                    # 处理文档内容，区分文本和图片
                    for i, doc in enumerate(docs):
                        content = doc["content"]
                        metadata = doc.get("metadata", {})
                        
                        # 第一个文档是视觉分析结果
                        if i == 0:
                            text_contents.append(f"[视觉分析结果]: \"{content}\"")
                            continue
                            
                        # 检查是否为图片文档
                        is_image = False
                        if "type" in metadata and metadata["type"] == "image":
                            is_image = True
                        elif "img_path" in metadata and metadata["img_path"]:
                            is_image = True
                        
                        if is_image:
                            # 这是一个图片文档
                            img_path = metadata.get("img_path", "")
                            if img_path:
                                image_contents.append(f"[案例图片 {len(image_contents)+1}]: {img_path}")
                        else:
                            # 这是一个文本文档
                            source = metadata.get("source", "")
                            source_name = os.path.basename(source) if source else f"检索到的文本块 {len(text_contents)}"
                            text_contents.append(f"[{source_name}]: \"{content}\"")
                    
                    # 构建知识库文本依据部分
                    text_context = "\n".join(text_contents)
                    
                    # 获取系统提示词并替换占位符
                    modified_system_prompt = system_prompt
                    
                    # 替换用户照片占位符
                    modified_system_prompt = modified_system_prompt.replace("<user_photo_placeholder>", user_photo)
                    
                    # 提取文档内容用于替换retrieved_chunk占位符
                    text_docs = []
                    for i, doc in enumerate(docs):
                        if i == 0:  # 跳过第一个文档（视觉分析结果）
                            continue
                        
                        metadata = doc.get("metadata", {})
                        
                        # 判断是否为图片文档：通过metadata中的img_path或chunk_type字段
                        is_image_doc = (
                            metadata.get("img_path") or 
                            metadata.get("chunk_type") == "indicator_image"
                        )
                        
                        if is_image_doc and metadata.get("context"):
                            # 图片文档，使用context作为内容
                            text_doc = {
                                "content": metadata["context"],
                                "metadata": metadata.copy()
                            }
                            text_docs.append(text_doc)
                        elif not is_image_doc and doc.get("content"):
                            # 文本文档，直接使用content
                            text_docs.append(doc)
                    
                    # 替换retrieved_chunk占位符
                    if len(text_docs) >= 1:
                        chunk_1_content = text_docs[0]["content"]
                        chunk_1_source = text_docs[0].get("metadata", {}).get("source", "未知来源")
                        modified_system_prompt = modified_system_prompt.replace("{retrieved_chunk_1_content}", chunk_1_content)
                        modified_system_prompt = modified_system_prompt.replace("{retrieved_chunk_1_metadata}", os.path.basename(chunk_1_source) if chunk_1_source != "未知来源" else chunk_1_source)
                    else:
                        modified_system_prompt = modified_system_prompt.replace("{retrieved_chunk_1_content}", "未找到相关文本内容")
                        modified_system_prompt = modified_system_prompt.replace("{retrieved_chunk_1_metadata}", "无")
                    
                    if len(text_docs) >= 2:
                        chunk_2_content = text_docs[1]["content"]
                        chunk_2_source = text_docs[1].get("metadata", {}).get("source", "未知来源")
                        modified_system_prompt = modified_system_prompt.replace("{retrieved_chunk_2_content}", chunk_2_content)
                        modified_system_prompt = modified_system_prompt.replace("{retrieved_chunk_2_metadata}", os.path.basename(chunk_2_source) if chunk_2_source != "未知来源" else chunk_2_source)
                    else:
                        modified_system_prompt = modified_system_prompt.replace("{retrieved_chunk_2_content}", "")
                        modified_system_prompt = modified_system_prompt.replace("{retrieved_chunk_2_metadata}", "")
                    
                    # 构建知识库参考案例图片部分
                    case_photos = []
                    # 从传入的img_docs中提取图片路径
                    for doc in img_docs[:2]:  # 只取前两张最相似的图片
                        metadata = doc.get("metadata", {})
                        img_path = metadata.get("img_path", "")
                        if img_path:
                            case_photos.append(img_path)

                    # 如果有案例图片，替换占位符
                    if len(case_photos) >= 1:
                        modified_system_prompt = modified_system_prompt.replace("<retrieved_case_photo_1_placeholder>", case_photos[0])
                    else:
                        modified_system_prompt = modified_system_prompt.replace("<retrieved_case_photo_1_placeholder>", "无相关案例图片")
                        
                    if len(case_photos) >= 2:
                        modified_system_prompt = modified_system_prompt.replace("<retrieved_case_photo_2_placeholder>", case_photos[1])
                    else:
                        modified_system_prompt = modified_system_prompt.replace("<retrieved_case_photo_2_placeholder>", "无相关案例图片")
                    
                    # 自定义提示词，结合视觉分析和知识库内容
                    prompt = f"{user_query}\n\n参考资料：\n{text_context}"
                    
                    # 保存修改后的系统提示词，供外部使用
                    generator_self._modified_system_prompt = modified_system_prompt
                    
                    return prompt
                
                # 临时设置系统提示词创建方法，并传入image_documents参数
                def bound_custom_create_prompt(q, docs):
                    return custom_create_prompt(self.generator, q, docs, image_documents)
                
                self.generator._create_prompt = bound_custom_create_prompt
                
                # 先调用一次create_prompt来获取修改后的系统提示词
                self.generator._create_prompt(query, final_docs)
                
                # 设置修改后的系统提示词
                self.generator._system_prompt = getattr(self.generator, "_modified_system_prompt", system_prompt)
                
                # 调用generator生成回答
                answer = self.generator.generate(query, final_docs)
                
            finally:
                # 恢复原始设置
                if original_system_prompt is not None:
                    self.generator._system_prompt = original_system_prompt
                self.generator._create_prompt = original_create_prompt
            
            result["answer"] = answer
            result["status"] = "success"
            return result
            
        except Exception as e:
            print(f"生成最终答案时出错: {str(e)}")
            result["status"] = "error"
            result["answer"] = f"生成最终答案时出错: {str(e)}"
            return result

    def _merge_search_results(self, text_docs: List[Dict], image_docs: List[Dict], text_weight: float = 0.6, image_weight: float = 0.4, top_k: int = 5) -> List[Dict]:
        """融合基于文本和基于图像的检索结果
        
        Args:
            text_docs: 基于文本检索的文档列表
            image_docs: 基于图像检索的文档列表
            text_weight: 文本检索结果的权重
            image_weight: 图像检索结果的权重
            top_k: 返回的最大文档数量
            
        Returns:
            融合后的文档列表
        """
        # 如果任一列表为空，直接返回另一个列表
        if not text_docs:
            return image_docs[:top_k] if image_docs else []
        if not image_docs:
            return text_docs[:top_k] if text_docs else []
            
        # 创建文档ID到文档的映射
        all_docs = {}
        
        # 处理文本检索结果
        for i, doc in enumerate(text_docs):
            doc_id = doc.get("id") or str(i)
            # 确保每个文档有距离分数，如果没有则使用排名作为替代
            distance = doc.get("distance", 1.0 - 1.0 / (i + 1))
            # 归一化距离分数（越小越好）
            normalized_score = 1.0 - distance if distance <= 1.0 else 0.0
            
            # 确保文档有content字段
            if "content" not in doc or doc["content"] is None:
                # 尝试从metadata中获取信息
                metadata = doc.get("metadata", {})
                source = metadata.get("source", "未知来源")
                doc["content"] = f"来自{source}的文本文档"
            
            all_docs[doc_id] = {
                "doc": doc,
                "text_score": normalized_score,
                "image_score": 0.0,
                "final_score": normalized_score * text_weight
            }
            
        # 处理图像检索结果
        for i, doc in enumerate(image_docs):
            doc_id = doc.get("id") or f"img_{i}"
            # 确保每个文档有距离分数，如果没有则使用排名作为替代
            distance = doc.get("distance", 1.0 - 1.0 / (i + 1))
            # 归一化距离分数（越小越好）
            normalized_score = 1.0 - distance if distance <= 1.0 else 0.0
            
            # 确保文档有content字段
            if "content" not in doc or doc["content"] is None:
                # 尝试从metadata中获取信息构造内容
                metadata = doc.get("metadata", {})
                img_path = metadata.get("img_path", "")
                context = metadata.get("context", "")
                
                if context:
                    # 如果有上下文描述，使用它
                    doc["content"] = f"图片文档: {context}"
                elif img_path:
                    # 否则使用图片路径
                    doc["content"] = f"图片文档: {os.path.basename(img_path)}"
                else:
                    # 如果没有任何信息，使用默认描述
                    doc["content"] = f"图片文档 #{i+1}"
            
            if doc_id in all_docs:
                # 文档已存在，更新分数
                all_docs[doc_id]["image_score"] = normalized_score
                all_docs[doc_id]["final_score"] += normalized_score * image_weight
            else:
                # 新文档
                all_docs[doc_id] = {
                    "doc": doc,
                    "text_score": 0.0,
                    "image_score": normalized_score,
                    "final_score": normalized_score * image_weight
                }
                
        # 按最终分数排序
        sorted_results = sorted(all_docs.values(), key=lambda x: x["final_score"], reverse=True)
        
        # 返回前top_k个文档
        merged_docs = [item["doc"] for item in sorted_results[:top_k]]
        
        return merged_docs
    
    def save_search_results(self, query_text: str, documents: List[Dict], img_input: str = None, prefix: str = "search_result", search_type: str = "text"):
        """保存检索结果到日志目录
        
        Args:
            query_text: 查询文本
            documents: 检索到的文档列表
            img_input: 可选的图片输入路径或URL
            prefix: 文件名前缀
            search_type: 检索类型，如"text"或"image"
        """
        # 创建日志目录
        log_dir = r"E:\program\AI\RAG\server_chroma\logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # 生成时间戳
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 构建结果数据
        result_data = {
            "timestamp": timestamp,
            "query": query_text,
            "img_input": img_input,
            "documents": documents,
            "search_type": search_type
        }
        
        # 构建文件名
        filename = f"{prefix}_{timestamp}.json"
        filepath = os.path.join(log_dir, filename)
        
        # 保存为JSON文件
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            print(f"已保存检索结果到: {filepath}")
        except Exception as e:
            print(f"保存检索结果失败: {e}")

# 可选：docx转md（需安装pandoc）
def docx_to_markdown(docx_path: str, output_dir: str = "output") -> str:
    name = os.path.splitext(os.path.basename(docx_path))[0]
    md_path = os.path.join(output_dir, f"{name}.md")
    os.makedirs(output_dir, exist_ok=True)
    os.system(f"pandoc '{docx_path}' -f docx -t markdown -o '{md_path}'")
    return md_path

def batch_docx_to_markdown(docx_dir: str, output_dir: str = "output") -> list:
    md_files = []
    for file in os.listdir(docx_dir):
        if file.lower().endswith('.docx'):
            docx_path = os.path.join(docx_dir, file)
            md_file = docx_to_markdown(docx_path, output_dir)
            md_files.append(md_file)
    return md_files

# VLM图片理解API（Qwen-VL）- 使用图片URL
def vlm_api_func(img_path, context):
    # 上传本地图片到图床服务，获取公网URL
    try:
        img_url = upload_image(img_path)
    except Exception as e:
        print(f"图片上传失败: {img_path}, 错误: {e}")
        return "None"
    
    prompt = PROMPT_CONFIG["vision_analysis"]["simple_description"]
    # 获取通义千问视觉模型配置
    qwen_config = MODELS["vision_models"]["qwen-vl"]
    client = OpenAI(
        api_key=qwen_config["api_key"],
        base_url=qwen_config["base_url"],
    )
    try:
        completion = client.chat.completions.create(
            model=qwen_config["model_id"],
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": img_url}}
                ]
            }],
            timeout=30
        )
        desc = completion.choices[0].message.content
        return desc
    except Exception as e:
        print(f"VLM API调用失败: {img_path}, 错误: {e}")
        # 尝试使用base64方式调用
        return vlm_api_base64(img_path, context)

# VLM图片理解API（Qwen-VL）- 使用Base64
def vlm_api_base64(img_path, context):
    """使用Base64编码的图片调用视觉模型API"""
    try:
        # 获取通义千问视觉模型配置
        qwen_config = MODELS["vision_models"]["qwen-vl"]
        
        # 转换图片为base64
        base64_image = image_to_base64(img_path)
        if not base64_image:
            return "None"
        
        prompt = PROMPT_CONFIG["vision_analysis"]["simple_description"]
        client = OpenAI(
            api_key=qwen_config["api_key"],
            base_url=qwen_config["base_url"],
        )
        
        # 调用API，使用base64编码的图片
        completion = client.chat.completions.create(
            model=qwen_config["model_id"],
            messages=[
                {
                    "role": "system",
                    "content": [{"type": "text", "text": "你是一个专业的视觉语言助手。请详细描述图片内容。"}]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": base64_image}
                        },
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
        )
        
        desc = completion.choices[0].message.content
        return desc
    except Exception as e:
        print(f"Base64 VLM API调用失败: {img_path}, 错误: {e}")
        return "None"

def vlm_api_func1(img_path, context):
      # TODO: 替换为实际VLM API调用
      return "示例图片描述：包含有意义的信息。"

# 定义一个通用的API调用函数，支持不同的模型类型
def call_language_model_api(prompt: str, model_name: str = None, temperature: float = 0.7, max_tokens: int = 2000) -> str:
    """调用语言模型API生成文本，支持多种模型类型
    
    Args:
        prompt: 提示词
        model_name: 指定要使用的语言模型名称，默认使用active_model
        temperature: 温度参数，控制生成的随机性
        max_tokens: 最大生成token数
        
    Returns:
        生成的文本回答
    """
    # 获取当前激活的语言模型
    active_model = model_name or ACTIVE_MODELS.get("language")
    
    # 获取模型配置
    if active_model not in MODELS["language_models"]:
        raise ValueError(f"未找到指定的语言模型配置: {active_model}")
    
    model_config = MODELS["language_models"][active_model]
    
    # 根据模型类型调用不同的API
    if model_config["type"] == "openai":
        # 对于兼容OpenAI接口的模型（如火山引擎模型）
        try:
            # 创建OpenAI客户端
            client = OpenAI(
                api_key=model_config["api_key"],
                base_url=model_config["base_url"],
            )
            
            # 使用客户端调用API
            response = client.chat.completions.create(
                model=model_config["model_id"],
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # 返回生成的文本
            return response.choices[0].message.content
                
        except Exception as e:
            print(f"{active_model} API调用失败: {str(e)}")
            raise
    
    elif model_config["type"] == "google":
        # 对于Google Gemini模型
        try:
            # 创建Client对象
            client = genai.Client(api_key=model_config["api_key"])
            
            # 生成内容
            response = client.models.generate_content(
                model=model_config["model_id"],
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature
                )
            )
            
            # 返回文本
            if hasattr(response, 'text'):
                return response.text
            else:
                return str(response)
                
        except Exception as e:
            print(f"{active_model} API调用失败: {str(e)}")
            raise
    
    else:
        raise ValueError(f"不支持的模型类型: {model_config['type']}")

# 保留旧函数名以向后兼容
def call_volcengine_api(prompt: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
    """向后兼容的函数，调用火山引擎API生成文本，内部使用call_language_model_api
    
    Args:
        prompt: 提示词
        temperature: 温度参数，控制生成的随机性
        max_tokens: 最大生成token数
        
    Returns:
        生成的文本回答
    """
    # 直接使用volcengine模型
    return call_language_model_api(prompt, "volcengine", temperature, max_tokens)

def get_image_embedding_by_volc(image_base64: str) -> list:
    """
    调用火山API将base64图片转为embedding向量
    :param image_base64: base64图片字符串（data:image/...;base64,...）
    :return: embedding向量（list[float]），失败返回None
    """
    # api_key = os.environ.get("ARK_API_KEY")
    # if not api_key:
    #     print("未检测到ARK_API_KEY环境变量，无法调用火山图片embedding API")
    #     return None
    client = Ark(api_key='a510e12d-c2b0-4382-b73a-e525cbe60e55')
    # 提取base64纯数据部分
    # if image_base64.startswith("data:image"):
    #     base64_data = image_base64.split(",", 1)[1]
    # else:
    base64_data = image_base64
    try:
        resp = client.multimodal_embeddings.create(
            model="doubao-embedding-vision-241215",
            encoding_format="float",
            input=[{"image_url": {"url": base64_data}, "type": "image_url"}]
        )
        embedding = resp.data["embedding"]
        return embedding
    except Exception as e:
        print(f"火山图片embedding API调用失败: {e}")
        return None

def get_text_embedding_by_volc(text: str) -> list:
    """
    调用火山API将文本转为embedding向量
    :param text: 文本字符串
    :return: embedding向量（list[float]），失败返回None
    """
    client = Ark(api_key='a510e12d-c2b0-4382-b73a-e525cbe60e55')
    try:
        resp = client.multimodal_embeddings.create(
            model="doubao-embedding-vision-241215",
            encoding_format="float",
            input=[{"text": text, "type": "text"}]
        )
        embedding = resp.data["embedding"] if isinstance(resp.data, dict) else resp.data[0].embedding
        return embedding
    except Exception as e:
        print(f"火山文本embedding API调用失败: {e}")
        return None

def main(rebuild_index=False):
    raw_dir = "./data/raw"
    output_dir = "./output"
    snapshot_path = os.path.join(output_dir, "embedded_chunks.json")
    log_dir = "./logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # 检查是否存在已生成的知识库快照，且不需要重建索引
    if not rebuild_index and os.path.exists(snapshot_path):
        print(f"[1/2] 从现有快照加载知识库: {snapshot_path}")
        try:
            with open(snapshot_path, "r", encoding="utf-8") as f:
                embedded_chunks = json.load(f)
            print(f"已加载 {len(embedded_chunks)} 个向量化chunk")
            
            print("[2/2] 存储到Chroma...")
            es_store = ChromaStore()
            success = es_store.add_documents(embedded_chunks)
            if success:
                print("全部chunk已存入Chroma数据库！")
            else:
                print("存储到Chroma时发生错误，请检查日志。")
            return
        except Exception as e:
            print(f"加载知识库快照失败: {e}")
            print("将重新生成知识库...")

    # 如果需要重建索引或者没有现有快照，执行完整的处理流程
    print("[1/6] 批量将PDF/Docx转为Markdown...")
    
    # 检查特定的城市体检工作手册Markdown文件是否已存在
    target_md_file = os.path.join(output_dir, "20250526城市体检工作手册.md")
    
    if os.path.exists(target_md_file):
        print(f"发现已存在的文件: {target_md_file}")
        md_files = [target_md_file]
        print("跳过PDF/Docx转换步骤")
    else:
        print("未找到城市体检工作手册Markdown文件，开始转换...")
        md_files_pdf = batch_pdf_to_markdown(raw_dir, output_dir)
        md_files_docx = batch_docx_to_markdown(raw_dir, output_dir)
        md_files = md_files_pdf + md_files_docx
        print(f"共生成Markdown文件: {md_files}")
    
    if not md_files:
        print("未发现可用的PDF或Docx文件，流程终止。")
        return

    print("[2/6] 分块与图片识别...")
    
    # 检查是否已存在chunks.json文件
    chunks_file = os.path.join(output_dir, "chunks.json")
    
    if os.path.exists(chunks_file):
        print(f"发现已存在的chunks文件: {chunks_file}")
        print("跳过分块步骤，直接加载已有chunks...")
        try:
            with open(chunks_file, "r", encoding="utf-8") as f:
                chunks_data = json.load(f)
            all_chunks = chunks_data.get("chunks", [])
            print(f"已加载chunks总数: {len(all_chunks)}")
        except Exception as e:
            print(f"加载chunks文件失败: {e}")
            print("将重新执行分块...")
            all_chunks = []
    else:
        print("未找到chunks文件，开始分块处理...")
        all_chunks = []
    
    # 如果没有成功加载chunks，则执行分块处理
    if not all_chunks:
        chunk_files = []
        
        for md_file in md_files:
            print(f"处理文件: {md_file}")
            loader = MarkdownChunkLoader(md_file)
            chunks = loader.chunk()
            all_chunks.extend(chunks)
            chunk_files.append(loader.chunks_file)
        
        print(f"分块总数: {len(all_chunks)}")
    
    if not all_chunks:
        print("未分出任何chunk，流程终止。")
        return

    print("[3/6] 并发VLM图片理解...")
    text_chunks = [c for c in all_chunks if c["type"] == "text"]
    image_chunks = [c for c in all_chunks if c["type"] == "image"]
    print(f"待处理图片chunk数: {len(image_chunks)}，文本chunk数: {len(text_chunks)}")
    
    print("[5/6] 向量化...")
    
    # 检查是否已存在embedded_chunks.json文件
    if os.path.exists(snapshot_path):
        print(f"发现已存在的向量化文件: {snapshot_path}")
        print("跳过向量化步骤，直接加载已有向量...")
        try:
            with open(snapshot_path, "r", encoding="utf-8") as f:
                embedded_chunks = json.load(f)
            print(f"已加载向量化chunks数: {len(embedded_chunks)}")
        except Exception as e:
            print(f"加载向量化文件失败: {e}")
            print("将重新执行向量化...")
            embedded_chunks = []
    else:
        print("未找到向量化文件，开始向量化处理...")
        embedded_chunks = []
    
    # 如果没有成功加载向量化chunks，则执行向量化处理
    if not embedded_chunks:
        # 使用Embedder类处理向量化
        embedder = Embedder()
        print(f"使用编码模型: {embedder.active_embedding} ({embedder.embedding_config['description']})")
        
        # 处理所有chunks（同时处理文本和图像）
        embedded_chunks = embedder.embed_documents(all_chunks)
        print(f"已向量化chunk数: {len(embedded_chunks)}")

        # 保存embedded_chunks到JSON文件
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(snapshot_path), exist_ok=True)
            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(embedded_chunks, f, ensure_ascii=False)
            print(f"已保存知识库快照到: {snapshot_path}")
            
            # 同时保存一份到logs目录，便于查看
            # embedded_chunks_log = os.path.join(log_dir, f"embedded_chunks_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            # with open(embedded_chunks_log, "w", encoding="utf-8") as f:
            #     json.dump(embedded_chunks, f, ensure_ascii=False)
        except Exception as e:
            print(f"保存知识库快照失败: {e}")

    print("[6/6] 存储到Chroma...")
    es_store = ChromaStore()
    success = es_store.add_documents(embedded_chunks)
    
    if success:
        print("全部chunk已存入Chroma数据库！")
    else:
        print("存储到Chroma时发生错误，请检查日志。")

if __name__ == "__main__":
    # 直接设置变量，不使用命令行参数
    rebuild_index = True  # 是否重建知识库索引
    query_only = False     # 是否仅查询模式，不构建知识库
    dual_retrieval = True  # 是否启用双路检索（默认开启）
    
    # 如果不是仅查询模式，则先构建知识库
    if not query_only:
        main(rebuild_index=rebuild_index)
    
    # 问答交互环节
    rag = RAGSystem(dual_retrieval=dual_retrieval)
    print("\n知识库已构建完毕，可以开始问答。输入'quit'退出。")
    print("提示：你可以在问题中直接输入图片URL，系统会自动识别并处理。")
    if dual_retrieval:
        print("双路检索功能已启用，将同时使用文本和图像向量进行检索。")
    while True:
        user_input = input("\n请输入你的问题：").strip()
        if user_input.lower() == "quit":
            break
        
        # 从用户输入中提取可能的图片URL
        query, img_input = extract_image_url(user_input)
        if img_input:
            print(f"检测到图片URL: {img_input}")
            print("问题内容:", query)
        
        # 调用问答
        response = rag.query(query, img_input)
        
        # 处理新的返回格式
        if img_input and response.get("visual_analysis"):
            print("\n[视觉分析结果]")
            print(response["visual_analysis"])
            print("\n[正在生成完整回答...]")
            
        if response.get("answer"):
            print(f"\n[完整回答]")
            print(response["answer"])
        else:
            print(f"\n处理状态: {response.get('status', '未知')}")
            if response.get("status") == "error":
                print("处理过程中出现错误，请重试。") 