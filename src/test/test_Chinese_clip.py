from PIL import Image
import requests
from transformers import ChineseCLIPProcessor, ChineseCLIPModel

print("正在加载Chinese CLIP模型...")
model = ChineseCLIPModel.from_pretrained("OFA-Sys/chinese-clip-vit-base-patch16")
processor = ChineseCLIPProcessor.from_pretrained("OFA-Sys/chinese-clip-vit-base-patch16")

print("正在下载测试图片...")
url = "https://clip-cn-beijing.oss-cn-beijing.aliyuncs.com/pokemon.jpeg"
image = Image.open(requests.get(url, stream=True).raw)

# 测试文本
texts = ["杰尼龟", "妙蛙种子", "小火龙", "皮卡丘"]

print("计算图像特征向量...")
# compute image feature
inputs = processor(images=image, return_tensors="pt")
image_features = model.get_image_features(**inputs)
image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)  # normalize

print("计算文本特征向量...")
# compute text features
inputs = processor(text=texts, padding=True, truncation=True, max_length=512, return_tensors="pt")
text_features = model.get_text_features(**inputs)
text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)  # normalize

# 输出维度信息
print(f"\n=== Chinese CLIP 模型维度测试结果 ===")
print(f"图像特征向量维度: {image_features.shape}")
print(f"文本特征向量维度: {text_features.shape}")
print(f"单个图像向量维度: {image_features.shape[-1]}")
print(f"单个文本向量维度: {text_features.shape[-1]}")

# 计算相似度矩阵
logits_per_image = (image_features @ text_features.T) * 100
logits_per_text = logits_per_image.T

print(f"\n=== 相似度测试 ===")
print(f"图像与文本的相似度分数:")
for i, text in enumerate(texts):
    score = logits_per_image[0][i].item()
    print(f"  {text}: {score:.2f}")

print(f"\n模型测试完成！")


