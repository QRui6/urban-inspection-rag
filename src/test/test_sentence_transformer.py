from sentence_transformers import SentenceTransformer
from PIL import Image

# Load CLIP model
image_model = SentenceTransformer("clip-ViT-B-32")

# Encode an image:
img_emb = image_model.encode(Image.open(r"E:\program\AI\RAG\uploads\two_dogs_in_snow.jpg"))
print(img_emb.shape)  # (512,)

text_model = SentenceTransformer("shibing624/text2vec-base-chinese")
# Encode text descriptions
text_emb = text_model.encode(
    ["Two dogs in the snow", "A cat on a table", "A picture of London at night"]
)
print(text_emb.shape)  # (3, 768)
# # Compute similarities
# similarity_scores = model.similarity(img_emb, text_emb)
# print(similarity_scores)

# 1. 加载一个统一的、支持中文的多模态模型
# 第一次运行会自动下载
print("正在加载中文多模态模型...")
# 这个模型能处理图像和中文文本
model = SentenceTransformer('OFA-Sys/chinese-clip-vit-base-patch16')
print("模型加载成功！")

# 2. 准备图像和中文文本
image_path = r"E:\program\AI\RAG\uploads\two_dogs_in_snow.jpg" # 请确保路径正确
image = Image.open(image_path)
texts = [
    "雪地里的两只狗",      # 语义相关
    "桌子上的一只猫",      # 语义无关
    "伦敦的夜景照片"       # 语义无关
]

# 3. 使用同一个模型进行编码
print("\n开始编码图像...")
img_emb = model.encode(image)
print("图像编码完成！")

print("\n开始编码文本...")
text_embs = model.encode(texts)
print("文本编码完成！")

# 4. 检查维度
print(f"\n图像嵌入的维度: {img_emb.shape}")      
print(f"文本嵌入的维度: {text_embs.shape}")    
