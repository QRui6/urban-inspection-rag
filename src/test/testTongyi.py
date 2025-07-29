from openai import OpenAI
from config.config import MODELS, ACTIVE_MODELS

def vlm_api_func(img_path, context):
    # 获取通义千问视觉模型配置
    qwen_config = MODELS["vision_models"]["qwen-vl"]
    
    # 上传本地图片到图床服务，获取公网URL
    try:
        img_url = "https://bed.djxs.xyz/file/BQACAgUAAyEGAASVl6k_AAICi2gskF4L-EaeSVkx9UQJskIDykeBAAJqFQACTDppVcHqds3TfzUJNgQ.jpg"
    except Exception as e:
        print(f"图片上传失败: {img_path}, 错误: {e}")
        return "None"
    
    prompt = "请描述这张图片的内容"
    client = OpenAI(
        api_key=qwen_config["api_key"],
        base_url=qwen_config["base_url"],
    )
    try:
        completion = client.chat.completions.create(
            model=qwen_config["model_id"],
            messages=[
                # {
                #     "role": "system",
                #     "content": [{"type": "text", "text": "你是一个专业的视觉语言助手。请基于图片内容回答问题。"}]
                # },
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": img_url}},
                        {"type": "text", "text": prompt}
                    ]
                }
            ],
            timeout=30
        )
        desc = completion.choices[0].message.content
        print(desc)
        return desc
    except Exception as e:
        print(f"VLM API调用失败: {img_path}, 错误: {e}")

if __name__ == "__main__":
    img_path = "test.jpg"
    context = "这是一张图片"
    desc = vlm_api_func(img_path, context)
    print(desc)
