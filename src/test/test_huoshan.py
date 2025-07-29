import requests
import json
from config.config import MODELS, ACTIVE_MODELS

def call_volcengine_api(prompt: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
    """调用火山引擎API生成文本
    
    Args:
        prompt: 提示词
        temperature: 温度参数，控制生成的随机性
        max_tokens: 最大生成token数
        
    Returns:
        生成的文本回答
    """
    # 获取火山引擎模型配置
    volcengine_config = MODELS["language_models"]["volcengine"]
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {volcengine_config['api_key']}"
    }
    
    # 根据火山引擎ARK模型API的格式构建请求
    payload = {
        "model": volcengine_config["model_id"],
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    try:
        # 使用config.py中配置的URL
        response = requests.post(f"{volcengine_config['base_url']}/chat/completions", headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # 抛出HTTP错误
        result = response.json()
        
        # 处理火山引擎API的响应格式
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            raise Exception(f"API返回格式异常: {result}")
            
    except Exception as e:
        print(f"火山引擎API调用失败: {str(e)}")
        raise