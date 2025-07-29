"""
配置文件
"""
import os
from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent

# 数据目录
DATA_DIR = ROOT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Elasticsearch配置
ES_CONFIG = {
    "hosts": ["http://localhost:9200"],
    "index_name": "rag_documents",
    "vector_dim": 3072,  # sentence-transformers默认维度
}

# 文档处理配置
DOCUMENT_CONFIG = {
    "chunk_size": 2000,  # 文本分块大小
    "chunk_overlap": 50,  # 分块重叠大小
    "supported_formats": [".pdf", ".docx", ".txt"],  # 支持的文档格式
}

# 检索配置
RETRIEVAL_CONFIG = {
    "top_k": 5,  # 检索返回的文档数量
    "bm25_weight": 0.3,  # BM25权重
    "vector_weight": 0.7,  # 向量检索权重
}

# 重排序配置
RERANKER_CONFIG = {
    "model_name": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "top_k": 3,  # 重排序后保留的文档数量
}

# 火山引擎API配置
ARK_API_KEY = os.environ.get("ARK_API_KEY", "a510e12d-c2b0-4382-b73a-e525cbe60e55")
ARK_BASE_URL = os.environ.get("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
ARK_MODEL_ID = os.environ.get("ARK_MODEL_ID", "ep-20250208172048-c9n4x")

# Google Gemini API配置
# GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyA_te7PSxGls4YmslspG2aRE0GgeOOFs2c")
# GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyB4pdPnfk89KSf9kB8Yb6FKcE7s27eZAbY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyAbP1BoeQ3M82KkEo5jiIPUPEiU0-wd-6M")
GEMINI_BASE_URL = os.environ.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1/")
# GEMINI_MODEL_ID = os.environ.get("GEMINI_MODEL_ID", "gemini-2.5-flash-preview-05-20")
GEMINI_MODEL_ID = os.environ.get("GEMINI_MODEL_ID", "gemini-2.5-flash")

# 通义千问API配置
QWEN_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "sk-60d76b6077414033a1b9eb7285c39e73")
QWEN_BASE_URL = os.environ.get("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
QWEN_MODEL_ID = os.environ.get("QWEN_MODEL_ID", "qwen-vl-plus")

# 模型配置系统 - 所有可用模型的配置信息
MODELS = {
    # 视觉模型配置
    "vision_models": {
        "qwen-vl": {
            "type": "openai",
            "api_key": QWEN_API_KEY,
            "base_url": QWEN_BASE_URL,
            "model_id": QWEN_MODEL_ID,
            "description": "通义千问视觉语言模型"
        },
        "gemini": {
            "type": "google",
            "api_key": GEMINI_API_KEY,
            "base_url": GEMINI_BASE_URL,
            "model_id": GEMINI_MODEL_ID,
            "description": "Google Gemini视觉语言模型"
        }
    },
    
    # 语言模型配置
    "language_models": {
        "volcengine": {
            "type": "openai",  # 火山引擎API兼容OpenAI格式
            "api_key": ARK_API_KEY,
            "base_url": ARK_BASE_URL,
            "model_id": ARK_MODEL_ID,
            "description": "火山引擎大语言模型"
        },
        "gemini": {
            "type": "google",
            "api_key": GEMINI_API_KEY,
            "base_url": GEMINI_BASE_URL,
            "model_id": GEMINI_MODEL_ID,
            "description": "Google Gemini大语言模型"
        }
    },
    
    # 嵌入模型配置
    "embedding_models": {
        "sentence-transformer": {
            "type": "local",
            "model_name": "sentence-transformers/all-MiniLM-L6-v2",
            "device": "cpu",
            "batch_size": 32,
            "description": "Sentence Transformer本地嵌入模型（英文优化）"
        },
        "chinese-text": {
            "type": "local",
            "model_name": "shibing624/text2vec-base-chinese",
            "device": "cpu",
            "batch_size": 32,
            "description": "中文文本向量化模型（专门优化中文语义理解）"
        },
        "chinese-clip": {
            "type": "local",
            "model_name": "OFA-Sys/chinese-clip-vit-base-patch16",
            "device": "cpu",
            "batch_size": 16,
            "description": "Chinese CLIP多模态模型（中文优化的图文匹配模型）"
        },
        "multilingual": {
            "type": "local",
            "model_name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            "device": "cpu",
            "batch_size": 32,
            "description": "多语言文本嵌入模型（支持中英文）"
        },
        "clip-vit": {
            "type": "local",
            "model_name": "clip-ViT-B-32",
            "device": "cpu",
            "batch_size": 32,
            "description": "CLIP ViT-B-32 多模态嵌入模型（支持图像和文本，但文本检索效果一般）"
        },
        "volcengine": {
            "type": "api",
            "api_key": ARK_API_KEY,
            "model_id": "doubao-embedding-vision-241215",
            "encoding_format": "float",
            "description": "火山引擎多模态嵌入模型（支持图像和文本）"
        },
        "dashscope": {
            "type": "api",
            "api_key": QWEN_API_KEY,
            "model_id": "multimodal-embedding-v1",
            "description": "阿里DashScope多模态嵌入模型（支持图像和文本）"
        }
    }
}

# 当前激活的模型配置
ACTIVE_MODELS = {
    "vision": "gemini",     # 视觉分析模型
    "language": "gemini", # 语言生成模型
    "embedding": "chinese-clip" # 向量嵌入模型 - 支持图像和文本的多模态模型
}

# 保持向后兼容的生成器配置
GENERATOR_CONFIG = {
    "model_name": "gpt-3.5-turbo",  # 兼容OpenAI旧参数
    "temperature": 0.7,
    "max_tokens": 2000,
    # 火山引擎参数
    "ark_api_key": ARK_API_KEY,
    "ark_base_url": ARK_BASE_URL,
    "ark_model_id": ARK_MODEL_ID,
    # Google Gemini参数
    "use_gemini": False,  # 已弃用，请使用ACTIVE_MODELS["language"]
    "gemini_api_key": GEMINI_API_KEY,
    "gemini_base_url": GEMINI_BASE_URL,
    "gemini_model_id": GEMINI_MODEL_ID,
}

# 创建必要的目录
for dir_path in [RAW_DATA_DIR, PROCESSED_DATA_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True) 

# 提示词配置
PROMPT_CONFIG = {
    # 视觉分析提示词
    "vision_analysis": {
        # 城市体检视觉分析提示词
        "city_inspection": """你是一名专业的城市体检员，请严格依据《城市体检工作手册》的视角，对下图进行专业、客观、详细的描述。请专注于图中可以被直接观察到的、与住房安全、小区功能、社区环境和居民生活品质相关的物理细节。
你的描述应从以下三大类、共14个细分指标中，选择一个最相关的指标进行分类，然后生成一段精准的文本描述。
一、 住房（针对住宅楼栋或户内）
存在结构安全隐患的住宅: 描述承重结构（如梁、板、柱、墙体）的明显病害，如裂缝、变形、破损、钢筋外露等。
存在燃气安全隐患的住宅: 描述燃气管道、阀门、仪表的锈蚀、破损、私拉乱接等问题。
存在楼道安全隐患的住宅: 描述楼道、楼梯、公共走廊的问题，如楼梯破损、照明缺失、消防设施（消防栓、灭火器）缺失或损坏、杂物堆积堵塞通道、电动车违规停放或"飞线"充电。
存在围护安全隐患的住宅: 描述建筑外墙、屋顶、门窗等非承重部分的问题，如外墙饰面脱落、屋面渗漏、窗户破损、阳台/外挂空调机摇摇欲坠。
存在管线管道破损的住宅: 描述暴露在外的给水、排水、采暖、电力、通信等管线的破损、老化、滴漏、杂乱、裸露等情况。
需要进行适老化改造的住宅: 描述缺少方便老年人出行的设施，如无电梯（针对多层住宅）、缺少无障碍坡道、楼梯无扶手等。
需要进行节能改造的住宅: 描述外墙无保温层、窗户非节能窗等明显不符合节能要求的特征。
二、 小区与公共空间（针对小区内部的公共区域）
停车管理问题: 描述机动车或非机动车的停放乱象，如停车位不足、车辆占用消防通道、占用绿地、停车混乱无序。
电动自行车充电与安全问题: 描述电动自行车充电相关的问题，如未配建集中充电设施、充电桩数量不足、存在"飞线"充电现象、充电区域缺少必要的消防安全设施（如灭火器、喷淋）。
公共活动场地与设施问题: 描述小区内的公共活动场地，如儿童娱乐、老年活动、体育健身场地的设施不充足、破损、地面不平整或破损。
小区智慧化与安防问题: 描述缺少智能化便民和安防设施，如无智能信包箱/快递柜、安防监控系统不完善、缺少高空抛物监控摄像头。
公共区域无障碍与步行道问题: 描述小区内步行道和公共设施的无障碍设计缺陷，如路面破损、宽度不足、夜间照明不足、被占用、缺少坡道或坡道不合规、无法连贯通行。
三、 街区与道路（针对小区外部的街道环境）
道路乱停车问题: 描述街道上的车辆停放问题，如机动车/非机动车无序停放、违规占用人行道、占用绿化带、占用盲道。
共享单车停放问题: 描述共享单车集中停放但无明确划线区域，或乱停乱放影响通行。
【输出要求】
先分类，再描述：首先明确指出图片内容符合上述列表中的哪个具体指标。
客观描述：只描述你看到的物理事实。例如，不说"这里很危险"，而说"楼道内可见一辆电动车正在通过从楼上窗口垂下的插线板进行充电，旁边堆放有纸箱等杂物"。
细节量化：尽可能量化细节。例如，不说"墙上有裂缝"，而说"二楼窗户下方的外墙墙面有一条长约1米的水平裂缝"。
精准用词：使用手册中的专业术语，如"飞线充电"、"占用消防通道"、"围护结构"等。
最终目的：你生成的文本描述将用于在《城市体检工作手册》知识库中检索相关条款和案例，因此必须精准、具体。
请开始分析图片。
""",
        # 简单图片描述提示词
        "simple_description": "请描述这张图片的内容"
    },
    
    # 系统提示词
    "system": {
        # 默认系统提示词
        "default": "你是一个专业的助手，请基于给定的参考信息回答问题。",
        
        # 城市体检报告生成提示词
        "city_inspection_report": """你是一位极其严谨和专业的城市体检专家，专门负责住房和社区维度的体检工作。请根据用户上传的现场照片，并结合从《城市体检工作手册》知识库中检索到的文本依据和相似案例图片，生成一份专业的分析报告。
                            **[输入信息]**
                            
                            1.  **用户现场照片**: 
                                <user_photo_placeholder>
                            
                            2.  **[知识库-文本依据]**: (以下内容均从《城市体检工作手册》中检索)
                                ---
                                [文本块1 - 指标定义与解释]: "{retrieved_chunk_1_content}" 
                                *来源: {retrieved_chunk_1_metadata}*
                            
                                [文本块2 - 具体规范]: "{retrieved_chunk_2_content}"
                                *来源: {retrieved_chunk_2_metadata}*
                                ---
                            
                            3.  **知识库参考案例图片**:
                                [案例图片 1]: <retrieved_case_photo_1_placeholder>
                                [案例图片 2]: <retrieved_case_photo_2_placeholder>
                            
                            **[你的任务]**
                            
                            请严格按照以下格式，结合所有输入信息，生成分析报告：
                            
                            - **隐患类型**: 根据用户现场照片和知识库内容，准确判断并列出最符合的安全隐患类型。
                            
                            - **隐患描述**: 详细描述在【用户现场照片】中观察到的具体问题，并解释为什么它构成隐患。
                            
                            - **体检依据**: **直接、完整地引用**在 **[知识库-文本依据]** 中找到的 **【体检依据】** 部分。必须明确列出所引用的法规、政策文件名（如《住宅项目规范》（GB55038-2025））。如果文本中包含多个依据，请都列出来。
                            
                            - **整改建议**: 基于发现的隐患类型和体检依据，提供整改措施和建议，用一段话来描述，不要分点。
                            
                            请确保你的回答专业、严谨，并充分利用了提供的所有图文材料。
                            """,
        # 原案例佐证已替换为整改建议
        # - **【案例佐证】**: 展示在 **[知识库-案例图片]** 中找到的最相似的图片，并附上说明："知识库中的类似案例如下所示，可作为直观参考："。
        # 城市体检分析提示词（简化版）
        "city_inspection_analysis": """你是一位城市体检专家。请分析视觉模型识别的安全隐患，结合知识库中的相关指标提供详细说明与体检依据。
                            请按以下格式输出:
                            - 隐患类型：列出图片属于哪种安全隐患
                            - 隐患描述：列出图片中存在的安全隐患详细描述
                            - 体检依据：根据知识库内容提供体检依据
                            """
    },
    
    # 用户提示词模板
    "user": {
        # 查询模板
        "query_template": "以下是用户的问题:\n{query}\n\n请根据知识库内容和视觉分析结果，提供专业的安全评估和整改建议。"
    }
} 