"""
视觉分析模块 - 独立的图像分析功能
支持结构化输出
"""
import os
import json
import base64
import requests
from typing import Optional, Tuple, Dict, Any
from pydantic import BaseModel
from openai import OpenAI
from google import genai
from google.genai import types
from volcenginesdkarkruntime import Ark
from config.config import MODELS, ACTIVE_MODELS, PROMPT_CONFIG

# 城市体检视觉分析结构化输出模型
class CityInspectionAnalysis(BaseModel):
    """城市体检视觉分析结果的结构化模型"""
    indicator_classification: str  # 指标分类：维度名称 - 二级指标序号 二级指标名称
    specific_problem: str          # 具体问题：三级问题序号 - 具体问题描述
    detailed_description: str      # 详细描述：客观、量化的专业描述

class VisionAnalyzer:
    """视觉分析器类"""
    
    def __init__(self):
        """初始化视觉分析器"""
        self.vision_clients = {}
        self._init_vision_clients()
    
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
                    # 初始化OpenAI兼容的视觉模型（如通义千问、火山引擎）
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
                elif model_config["type"] == "ark":
                    # 初始化火山引擎 豆包视觉模型
                    try:
                        self.vision_clients[model_name] = Ark(api_key=model_config["api_key"])
                        print(f"已初始化视觉模型: {model_name} ({model_config['description']})")
                    except Exception as e:
                        print(f"初始化Google视觉模型{model_name}失败: {e}")
                        
            except Exception as e:
                print(f"初始化视觉模型{model_name}失败: {e}")
    
    def analyze_image(self, img_input: str, prompt: str = None, use_structured_output: bool = True) -> Tuple[Optional[str], Optional[str]]:
        """使用配置的视觉模型分析图像
        
        Args:
            img_input: 图片URL或base64编码
            prompt: 分析提示词，如果为None则使用默认的城市体检提示词
            use_structured_output: 是否使用结构化输出
            
        Returns:
            Tuple[str, str]: (分析结果文本, 使用的模型名称)
        """
        if prompt is None:
            prompt = PROMPT_CONFIG["vision_analysis"]["city_inspection"]
            
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
                analysis_text = self._analyze_with_openai(
                    active_vision, img_input, prompt, model_config, use_structured_output
                )
                model_used = active_vision
            elif model_config["type"] == "google":
                analysis_text = self._analyze_with_google(
                    active_vision, img_input, prompt, model_config, use_structured_output
                )
                model_used = active_vision
            elif model_config["type"] == "ark":
                analysis_text = self._analyze_with_ark(
                    active_vision, img_input, prompt, model_config, use_structured_output
                )
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
                            analysis_text = self._analyze_with_openai(
                                model_name, img_input, prompt, config, use_structured_output
                            )
                        elif config["type"] == "google":
                            analysis_text = self._analyze_with_google(
                                model_name, img_input, prompt, config, use_structured_output
                            )
                        elif config["type"] == "ark":
                            analysis_text = self._analyze_with_ark(
                                model_name, img_input, prompt, config, use_structured_output
                            )
                            
                        if analysis_text:
                            model_used = f"{model_name} (备用)"
                            break
                    except Exception as e:
                        print(f"备用视觉模型 {model_name} 分析失败: {e}")
        
        return analysis_text, model_used
    
    def _analyze_with_openai(self, model_name: str, img_input: str, prompt: str, config: Dict, use_structured_output: bool = True) -> Optional[str]:
        """使用OpenAI兼容的API分析图像（支持阿里千问）"""
        client = self.vision_clients[model_name]
        try:
            # 判断输入是URL还是base64
            is_base64 = img_input.startswith('data:image')

            example1_response = json.dumps(
                {
                  "indicator_classification": "小区维度 - 18 不达标的步行道长度",
                  "specific_problem": "18.1 - 小区及周边道路的主要人行道路存在路面破损问题",
                  "detailed_description": "图中所示为一处通往建筑内部的地面区域，其混凝土铺装存在严重破损。路面多处出现大面积开裂、板块缺失以及表面剥落现象，导致地面凹凸不平，形成明显的通行障碍和安全隐患。破损的缝隙和边缘处有大量杂草丛生，显示出该区域长期缺乏维护管理。整体路面状况劣化严重 ，不符合步行道的使用标准。"
                },
                ensure_ascii=False
            )
            example2_response = json.dumps(
                {
                  "indicator_classification": "小区维度 - 16 未配建电动自行车充电设施的小区数量",
                  "specific_problem": "16.2 - 小区电动自行车乱拉飞线充电、安全防护设施配备和消防安全管理不到位",
                  "detailed_description": "图中显示一辆电动自行车停放在一栋建筑物外墙边，其充电器放置在车辆座椅上并连接电源线，正在进行充电。此充电行为发生于非专用充电区域的公共空间，存在电动自行车私拉乱接、违规充电的安全隐患。这反映出该小区可能未配备充足的电动自行车集中充电设施，且对电动 自行车的充电安全管理不到位，增加了火灾等安全风险。"
                },
                ensure_ascii=False
            )

            # 构建消息内容
            if use_structured_output:
                # 使用结构化输出时，将示例加入prompt中
                enhanced_prompt = f"""{prompt}

                    请严格按照以下JSON格式返回结果：
                    示例1: {example1_response}
                    示例2: {example2_response}
                    
                    请基于图像内容，按照上述JSON格式返回分析结果。"""
                
                request_params = {
                    "model": config["model_id"],
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": {"url": img_input}},
                                {"type": "text", "text": enhanced_prompt}
                            ]
                        }
                    ],
                    "response_format": {"type": "json_object"},
                    "timeout": 30
                }
            else:
                # 普通输出模式
                request_params = {
                    "model": config["model_id"],
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": {"url": img_input}},
                                {"type": "text", "text": prompt}
                            ]
                        }
                    ],
                    "timeout": 30
                }

            # 调用API
            completion = client.chat.completions.create(**request_params)
            response = completion.choices[0].message.content

            if use_structured_output:
                try:
                    # 解析JSON结构化输出
                    result_data = json.loads(response)
                    print(result_data)
                    return result_data
                except Exception as e:
                    print(f"{model_name}结构化输出解析失败: {e}，返回原始内容")
                    return response
            else:
                # 普通输出
                return response
        except Exception as e:
            print(f"视觉模型{model_name}分析图片失败: {e}")
            return None
    
    def _analyze_with_google(self, model_name: str, img_input: str, prompt: str, config: Dict, use_structured_output: bool = True) -> Optional[str]:
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
            
            # 构建生成配置
            generation_config = types.GenerateContentConfig()
            
            # 如果启用结构化输出，配置响应格式
            if use_structured_output:
                generation_config.response_mime_type = "application/json"
                generation_config.response_schema = CityInspectionAnalysis
            
            # 生成内容
            response = genai_client.models.generate_content(
                model=config["model_id"],
                contents=contents,
                config=generation_config
            )
            print(response.text)
            # 处理返回结果
            if use_structured_output:
                try:
                    # 解析JSON结构化输出
                    result_data = json.loads(response.text)
                    print(result_data)
                    return result_data
                except Exception as e:
                    print(f"Google结构化输出解析失败: {e}，返回原始内容")
                    return response.text if hasattr(response, 'text') else str(response)
            else:
                # 普通输出
                return response.text if hasattr(response, 'text') else str(response)
                
        except Exception as e:
            print(f"Google API分析图片失败: {e}")
            return None
    
    def _analyze_with_ark(self, model_name: str, img_input: str, prompt: str, config: Dict, use_structured_output: bool = True) -> Optional[str]:
        """使用火山引擎 API分析图像"""
        print(f"使用火山引擎 API分析图像: {config['model_id']}")
        client = self.vision_clients[model_name]
        
        # 判断输入是URL还是base64
        is_base64 = img_input.startswith('data:image')
        
        # 如果是火山引擎模型且启用结构化输出
        if use_structured_output:
            try:
                completion = client.beta.chat.completions.parse(
                    model=config["model_id"],  # 具体模型需替换为实际可用模型
                    messages=[
                        {"role": "system", "content": prompt},
                        {
                            "role": "user", "content": [
                                {
                                    "type": "image_url", 
                                    "image_url": {
                                        "url": img_input
                                    }
                                }
                            ]
                        }
                    ],
                    temperature=0.6,
                    response_format=CityInspectionAnalysis,  # 指定响应解析模型
                )
                resp = completion.choices[0].message.parsed
                result_data = json.loads(resp.model_dump_json(indent=2))
                print(result_data)
                return result_data
            except Exception as e:
                print(f"火山引擎结构化视觉分析输出失败: {e}")
                return None
        else:
            try:
                completion = client.chat.completions.create(
                    model=config["model_id"],  # 具体模型需替换为实际可用模型
                    messages=[
                        {"role": "system", "content": prompt},
                        {
                            "role": "user", "content": [
                                {
                                    "type": "image_url", 
                                    "image_url": {
                                        "url": img_input
                                    }
                                }
                            ]
                        }
                    ],
                )
                print(completion.choices[0].message.content)
                return completion.choices[0].message.content
            except Exception as e:
                print(f"火山引擎视觉分析输出失败: {e}")
                return None

    def analyze_city_inspection(self, img_input: str, use_structured_output: bool = True) -> Tuple[Optional[str], Optional[str]]:
        """城市体检专用图像分析方法
        
        Args:
            img_input: 图片URL或base64编码
            use_structured_output: 是否使用结构化输出
            
        Returns:
            Tuple[str, str]: (分析结果文本, 使用的模型名称)
        """
        prompt = PROMPT_CONFIG["vision_analysis"]["city_inspection"]
        return self.analyze_image(img_input, prompt, use_structured_output)