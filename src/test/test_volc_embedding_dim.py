import os
from volcenginesdkarkruntime import Ark

# 初始化Ark客户端
client = Ark(api_key="a510e12d-c2b0-4382-b73a-e525cbe60e55")

# 测试文本embedding
text_resp = client.multimodal_embeddings.create(
    model="doubao-embedding-vision-241215",
    # input=["花椰菜又称菜花、花菜，是一种常见的蔬菜。"],
    # encoding_format="float",
     input=[{"text":"天很蓝","type":"text"}]
)
print(text_resp)
text_embed = text_resp.data["embedding"]
print("文本embedding维度:", len(text_embed))

# 测试图片embedding（用一张本地图片base64）
import base64
img_path = r"E:\program\AI\RAG\server_chroma\output\images\980bc1d9dcbc6514da85e61056fe7e1ed4e537540386d04eb47c070012451e23.jpg"  # 请替换为实际存在的图片路径
if os.path.exists(img_path):
    with open(img_path, "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode()
    img_base64_str = f"data:image/jpeg;base64,{img_base64}"
    img_resp = client.multimodal_embeddings.create(
        model="doubao-embedding-vision-241215",
        encoding_format="float",
        input=[{"image_url": {"url": img_base64_str}, "type": "image_url"}]
    )
    img_embed = img_resp.data["embedding"]
    print("图片embedding维度:", len(img_embed))
else:
    print("未找到测试图片 test.jpg，请放置一张图片在当前目录下测试图片embedding维度。") 