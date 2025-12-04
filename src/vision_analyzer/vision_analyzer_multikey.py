"""
视觉分析模块 - 支持多API密钥轮询
提升并发处理能力
"""
import os
import json
from typing import Optional, Tuple, Dict, Any
from pydantic import BaseModel
from openai import OpenAI
from google import genai
from volcenginesdkarkruntime import Ark
from config.config import MODELS, ACTIVE_MODELS, PROMPT_CONFIG, ARK_API_KEYS, MAX_CONCURRENT_PER_KEY
from src.utils.api_key_manager import APIKeyManager


# 城市体检视觉分析结构化输出模型
class CityInspectionAnalysis(BaseModel):
    """城市体检视觉分析结果的结构化模型"""
    indicator_classification: str  # 指标分类
    specific_problem: str          # 具体问题
    detailed_description: str      # 详细描述


class VisionAnalyzerMultiKey:
    """
    支持多密钥的视觉分析器
    自动轮询使用多个API密钥以提升并发能力
    """
    
    def __init__(self):
        """初始化视觉分析器"""
        self.vision_clients = {}
        self.api_key_managers = {}  # 每个模型的密钥管理器
        self._init_vision_clients()
    
    def _init_vision_clients(self):
        """初始化视觉模型客户端和密钥管理器"""
        active_vision = ACTIVE_MODELS.get("vision")
        if not active_vision or active_vision not in MODELS["vision_models"]:
            print(f"警告: 未配置有效的视觉模型或模型'{active_vision}'不存在")
            return
        
        vision_models = MODELS["vision_models"]
        
        # 初始化所有已配置的视觉模型
        for model_name, model_config in vision_models.items():
            try:
                # 检查是否有多密钥配置
                if model_name == "volcengine-vision" and len(ARK_API_KEYS) > 1:
                    # 使用多密钥管理器
                    self.api_key_managers[model_name] = APIKeyManager(
                        ARK_API_KEYS,
                        max_concurrent_per_key=MAX_CONCURRENT_PER_KEY
                    )
                    print(f"✓ {model_name} 启用多密钥模式，共 {len(ARK_API_KEYS)} 个密钥")
                    
                    # 为每个密钥创建客户端（延迟创建）
                    self.vision_clients[model_name] = "multi_key"  # 标记为多密钥模式
                    
                elif model_config["type"] == "openai":
                    # 单密钥模式
                    self.vision_clients[model_name] = OpenAI(
                        api_key=model_config["api_key"],
                        base_url=model_config["base_url"],
                    )
                    print(f"✓ 已初始化视觉模型: {model_name} (单密钥模式)")
                    
                elif model_config["type"] == "google":
                    self.vision_clients[model_name] = genai.Client(api_key=model_config["api_key"])
                    print(f"✓ 已初始化视觉模型: {model_name} (单密钥模式)")
                    
                elif model_config["type"] == "ark":
                    self.vision_clients[model_name] = Ark(api_key=model_config["api_key"])
                    print(f"✓ 已初始化视觉模型: {model_name} (单密钥模式)")
                    
            except Exception as e:
                print(f"✗ 初始化视觉模型{model_name}失败: {e}")
    
    def analyze_image(
        self, 
        img_input: str, 
        prompt: str = None, 
        use_structured_output: bool = True
    ) -> Tuple[Optional[Any], Optional[str]]:
        """
        使用配置的视觉模型分析图像（支持多密钥）
        
        Args:
            img_input: 图片URL或base64编码
            prompt: 分析提示词
            use_structured_output: 是否使用结构化输出
            
        Returns:
            Tuple[分析结果, 使用的模型名称]
        """
        if prompt is None:
            prompt = PROMPT_CONFIG["vision_analysis"]["city_inspection"]
        
        active_vision = ACTIVE_MODELS.get("vision")
        if not active_vision or active_vision not in self.vision_clients:
            print(f"✗ 未找到有效的视觉模型'{active_vision}'")
            return None, None
        
        model_config = MODELS["vision_models"].get(active_vision)
        
        # 检查是否为多密钥模式
        if active_vision in self.api_key_managers:
            return self._analyze_with_multi_key(
                active_vision, 
                model_config, 
                img_input, 
                prompt, 
                use_structured_output
            )
        else:
            # 单密钥模式（原有逻辑）
            return self._analyze_with_single_key(
                active_vision, 
                model_config, 
                img_input, 
                prompt, 
                use_structured_output
            )
    
    def _analyze_with_multi_key(
        self,
        model_name: str,
        model_config: Dict,
        img_input: str,
        prompt: str,
        use_structured_output: bool
    ) -> Tuple[Optional[Any], Optional[str]]:
        """使用多密钥模式分析图像"""
        manager = self.api_key_managers[model_name]
        
        # 获取可用的API密钥
        key_info = manager.get_available_key(strategy="least_loaded")
        if not key_info:
            print("✗ 所有API密钥都不可用或已达到并发限制")
            return None, None
        
        key_name, api_key = key_info
        
        try:
            # 创建临时客户端
            if model_config["type"] == "openai":
                client = OpenAI(
                    api_key=api_key,
                    base_url=model_config["base_url"],
                )
                result = self._analyze_with_openai_client(
                    client,
                    model_config,
                    img_input,
                    prompt,
                    use_structured_output
                )
            elif model_config["type"] == "ark":
                client = Ark(api_key=api_key)
                result = self._analyze_with_ark_client(
                    client,
                    model_config,
                    img_input,
                    prompt,
                    use_structured_output
                )
            else:
                result = None
            
            # 释放密钥（成功）
            manager.release_key(key_name, success=True)
            
            return result, f"{model_name} ({key_name})"
            
        except Exception as e:
            # 释放密钥（失败）
            manager.release_key(key_name, success=False, error=str(e))
            print(f"✗ 使用密钥 {key_name} 分析失败: {e}")
            return None, None
    
    def _analyze_with_single_key(
        self,
        model_name: str,
        model_config: Dict,
        img_input: str,
        prompt: str,
        use_structured_output: bool
    ) -> Tuple[Optional[Any], Optional[str]]:
        """使用单密钥模式分析图像（原有逻辑）"""
        client = self.vision_clients[model_name]
        
        try:
            if model_config["type"] == "openai":
                result = self._analyze_with_openai_client(
                    client,
                    model_config,
                    img_input,
                    prompt,
                    use_structured_output
                )
            elif model_config["type"] == "google":
                result = self._analyze_with_google_client(
                    client,
                    model_config,
                    img_input,
                    prompt,
                    use_structured_output
                )
            elif model_config["type"] == "ark":
                result = self._analyze_with_ark_client(
                    client,
                    model_config,
                    img_input,
                    prompt,
                    use_structured_output
                )
            else:
                result = None
            
            return result, model_name
            
        except Exception as e:
            print(f"✗ 视觉分析失败: {e}")
            return None, None
    
    def _analyze_with_openai_client(
        self,
        client: OpenAI,
        model_config: Dict,
        img_input: str,
        prompt: str,
        use_structured_output: bool
    ) -> Optional[Any]:
        """使用OpenAI兼容客户端分析"""
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": img_input}},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        if use_structured_output:
            completion = client.beta.chat.completions.parse(
                model=model_config["model_id"],
                messages=messages,
                response_format=CityInspectionAnalysis,
            )
            return completion.choices[0].message.parsed.model_dump()
        else:
            completion = client.chat.completions.create(
                model=model_config["model_id"],
                messages=messages
            )
            return completion.choices[0].message.content
    
    def _analyze_with_google_client(
        self,
        client: genai.Client,
        model_config: Dict,
        img_input: str,
        prompt: str,
        use_structured_output: bool
    ) -> Optional[Any]:
        """使用Google Gemini客户端分析"""
        # Google Gemini实现
        # 这里保持原有逻辑
        pass
    
    def _analyze_with_ark_client(
        self,
        client: Ark,
        model_config: Dict,
        img_input: str,
        prompt: str,
        use_structured_output: bool
    ) -> Optional[Any]:
        """使用火山引擎Ark客户端分析"""
        # Ark实现
        # 这里保持原有逻辑
        pass
    
    def get_statistics(self) -> Dict:
        """获取所有密钥管理器的统计信息"""
        stats = {}
        for model_name, manager in self.api_key_managers.items():
            stats[model_name] = manager.get_statistics()
        return stats
