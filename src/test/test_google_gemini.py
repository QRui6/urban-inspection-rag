"""
测试Google Gemini API
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from google import genai
from google.genai import types
from config.config import MODELS

def test_google_gemini_text():
    """测试Google Gemini文本生成"""
    print("=== 测试Google Gemini文本生成 ===")
    
    try:
        # 获取Gemini配置
        gemini_config = MODELS["language_models"]["gemini"]
        
        # 创建客户端
        client = genai.Client(api_key=gemini_config["api_key"])
        
        # 测试提示词
        prompt = "Explain the concept of Occam's Razor and provide a simple, everyday example."
        
        print(f"使用模型: {gemini_config['model_id']}")
        print(f"提示词: {prompt}")
        print("\n正在调用API...")
        
        # 调用API
        response = client.models.generate_content(
            model=gemini_config["model_id"],
            contents=prompt
        )
        
        print(f"\n回答:\n{response.text}")
        print("\n测试成功！")
        
    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

def test_google_gemini_chinese():
    """测试Google Gemini中文对话"""
    print("\n=== 测试Google Gemini中文对话 ===")
    
    try:
        # 获取Gemini配置
        gemini_config = MODELS["language_models"]["gemini"]
        
        # 创建客户端
        client = genai.Client(api_key=gemini_config["api_key"])
        
        # 中文测试提示词
        prompt = "前50个质数的和是多少？"
        
        print(f"使用模型: {gemini_config['model_id']}")
        print(f"中文提示词: {prompt}")
        print("\n正在调用API...")
        
        # 调用API
        response = client.models.generate_content(
            model=gemini_config["model_id"],
            contents=prompt
        )
        for part in response.candidates[0].content.parts:
            if not part.text:
                continue
            if part.thought:
                print("Thought summary:")
                print(part.text)
                print()
            else:
                print("Answer:")
                print(part.text)
                print()
        
    except Exception as e:
        print(f"中文测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

def test_google_gemini_with_config():
    """测试带配置参数的Google Gemini调用"""
    print("\n=== 测试带配置参数的Google Gemini ===")
    
    try:
        # 获取Gemini配置
        gemini_config = MODELS["language_models"]["gemini"]
        
        # 创建客户端
        client = genai.Client(api_key=gemini_config["api_key"])
        
        prompt = "写一首关于AI助手的短诗"
        
        print(f"使用模型: {gemini_config['model_id']}")
        print(f"提示词: {prompt}")
        print("配置: temperature=0.8, max_output_tokens=200")
        print("\n正在调用API...")
        
        # 导入types模块
        from google.genai import types
        
        # 调用API（带配置参数）
        response = client.models.generate_content(
            model=gemini_config["model_id"],
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.8,
                max_output_tokens=200
            )
        )
        
        print(f"\n诗歌:\n{response.text}")
        print("\n配置参数测试成功！")
        
    except Exception as e:
        print(f"配置参数测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("开始测试Google Gemini API...")
    
    # 检查API密钥
    gemini_config = MODELS["language_models"]["gemini"]
    if not gemini_config["api_key"] or gemini_config["api_key"] == "your_api_key_here":
        print("错误: 请在config/config.py中设置正确的GEMINI_API_KEY")
        sys.exit(1)
    
    # 运行所有测试
    # test_google_gemini_text()
    test_google_gemini_chinese()
    # test_google_gemini_with_config()
    
    # print("\n所有测试完成！") 