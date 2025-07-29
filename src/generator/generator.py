"""
生成模块
"""
import os
import re
from typing import List, Dict, Any, Optional
from openai import OpenAI
from google import genai
from google.genai import types
from config.config import GENERATOR_CONFIG, MODELS, ACTIVE_MODELS, PROMPT_CONFIG

class Generator:
    """生成类"""
    
    def __init__(self):
        # 初始化客户端字典
        self.clients = {}
        
        # 初始化配置参数
        self.temperature = GENERATOR_CONFIG.get("temperature", 0.7)
        self.max_tokens = GENERATOR_CONFIG.get("max_tokens", 2000)
        
        # 设置默认系统提示词
        self._system_prompt = PROMPT_CONFIG["system"]["default"]
        
        # 设置当前激活的模型
        self.active_model = ACTIVE_MODELS.get("language")
        
        # 初始化语言模型客户端
        self._init_language_clients()

    def _init_language_clients(self):
        """初始化语言模型客户端"""
        # 获取语言模型配置
        language_models = MODELS.get("language_models", {})
        
        # 初始化所有已配置的语言模型
        for model_name, model_config in language_models.items():
            try:
                if model_config["type"] == "openai":
                    # 初始化OpenAI兼容的语言模型（如火山引擎）
                    self.clients[model_name] = {
                        "client": OpenAI(
                            api_key=model_config["api_key"],
                            base_url=model_config["base_url"],
                        ),
                        "config": model_config,
                        "type": "openai"
                    }
                    print(f"Generator: 已初始化语言模型: {model_name} ({model_config['description']})")
                    
                elif model_config["type"] == "google":
                    # 初始化Google Gemini语言模型
                    try:
                        genai_client = genai.Client(api_key=model_config["api_key"])
                        self.clients[model_name] = {
                            "client": genai_client,
                            "config": model_config,
                            "type": "google"
                        }
                        print(f"Generator: 已初始化语言模型: {model_name} ({model_config['description']})")
                    except Exception as e:
                        print(f"初始化Google语言模型{model_name}失败: {e}")
                        
            except Exception as e:
                print(f"初始化语言模型{model_name}失败: {e}")
        
        # 如果当前激活的模型未成功初始化，尝试使用任何可用的模型
        if self.active_model not in self.clients and self.clients:
            self.active_model = next(iter(self.clients.keys()))
            print(f"警告: 激活的模型{ACTIVE_MODELS.get('language')}不可用，使用{self.active_model}作为替代")

    def _create_prompt(self, query: str, documents: List[Dict[str, Any]]) -> str:
        """创建提示词"""
        context = "\n\n".join([doc["content"] for doc in documents])
        prompt = f"""基于以下参考信息回答问题。如果参考信息中没有相关内容，请说明无法回答。\n\n参考信息：\n{context}\n\n问题：{query}\n\n回答："""
        return prompt
    
    def generate(self, query: str, documents: List[Dict[str, Any]], model_name: str = None) -> str:
        """生成回答
        
        Args:
            query: 用户查询
            documents: 相关文档列表
            model_name: 可选，指定使用的模型名称，默认使用active_model
            
        Returns:
            生成的回答文本
        """
        prompt = self._create_prompt(query, documents)
        model_to_use = model_name or self.active_model
        
        # 如果指定的模型不可用，使用默认模型
        if model_to_use not in self.clients:
            print(f"警告: 指定的模型{model_to_use}不可用，尝试使用默认模型{self.active_model}")
            model_to_use = self.active_model
            
            # 如果默认模型也不可用，但有其他可用模型，则使用第一个可用的模型
            if model_to_use not in self.clients and self.clients:
                model_to_use = next(iter(self.clients.keys()))
                print(f"警告: 默认模型也不可用，使用{model_to_use}作为替代")
        
        # 如果没有任何可用模型
        if not self.clients:
            return "错误: 没有可用的语言模型。请检查配置。"
            
        # 生成回答
        try:
            client_info = self.clients[model_to_use]
            client_type = client_info["type"]
            
            if client_type == "openai":
                answer = self._generate_with_openai(prompt, client_info)
            elif client_type == "google":
                answer = self._generate_with_google(prompt, client_info)
            else:
                answer = f"错误: 不支持的客户端类型 {client_type}"
        except Exception as e:
            print(f"使用{model_to_use}模型生成回答时出错: {e}")
            answer = f"抱歉，生成回答时出现错误: {str(e)}"
            
        # 构建引用信息
        references = []
        for idx, doc in enumerate(documents, 1):
            meta = doc.get("metadata", {})
            source = meta.get("source", "未知文件")
            page = meta.get("page", None)
            chunk_id = meta.get("chunk_id", None)
            img_path = meta.get("img_path", None)
            ref = f"[{idx}] 文件: {source}"
            if page is not None:
                ref += f", 页码: {page}"
            if chunk_id is not None:
                ref += f", chunk_id: {chunk_id}"
            if img_path:
                ref += f", 图片: {img_path}"
            references.append(ref)
        if references:
            answer += "\n\n参考资料：\n" + "\n".join(references)
        # 若涉及图片chunk，自动在答案中用Markdown格式引用图片
        for doc in documents:
            meta = doc.get("metadata", {})
            img_path = meta.get("img_path", None)
            if img_path and isinstance(img_path, str) and not img_path.startswith("data:"):
                # 只添加实际图片路径，不添加base64图片
                answer += f"\n\n![]({img_path})"
        return answer
    
    def _generate_with_openai(self, prompt: str, client_info: Dict) -> str:
        """使用OpenAI API生成回答"""
        try:
            # 构建消息数组，包含系统消息和用户消息
            messages = [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            client = client_info["client"]
            config = client_info["config"]
            
            completion = client.chat.completions.create(
                model=config["model_id"],
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            answer = completion.choices[0].message.content
            return answer
        except Exception as e:
            print(f"使用OpenAI兼容API生成回答时出错: {str(e)}")
            raise
    def clean_prompt_for_api(self, text):
        # 1. 将所有换行符替换为单个空格
        cleaned_text = text.replace('\n', ' ')
        # 2. 移除Markdown加粗标记 (双星号)
        cleaned_text = cleaned_text.replace('**', '')
        # 3. 移除Markdown列表项标记 (星号加空格)
        # 使用正则表达式，因为可能会有多个空格或tab，或者星号后面直接跟文字
        cleaned_text = re.sub(r'\*\s*', '', cleaned_text)
        # 4. 将多个连续的空格替换为单个空格
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        # 5. 移除首尾空格
        cleaned_text = cleaned_text.strip()
        return cleaned_text
    def _generate_with_google(self, prompt: str, client_info: Dict) -> str:
        """使用Google Gemini API生成回答"""
        try:
            client = client_info["client"]
            prompt = self.clean_prompt_for_api(prompt)
            # 为请求配置参数
            generation_config = types.GenerateContentConfig(
                system_instruction=self._system_prompt,
                temperature=self.temperature,
                # max_output_tokens=self.max_tokens,
            )
            # print(prompt)
            # 构建请求
            response = client.models.generate_content(
                model=client_info["config"]["model_id"],
                contents=[prompt],
                config=generation_config,
            )
            # print(response.text)
            # 提取回答
            if hasattr(response, 'text'):
                return response.text
            else:
                return str(response)
                
        except Exception as e:
            print(f"使用Google Gemini生成回答时出错: {str(e)}")
            raise 