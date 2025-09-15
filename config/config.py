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
# ARK_MODEL_ID = os.environ.get("ARK_MODEL_ID", "ep-20250208172048-c9n4x")
ARK_MODEL_ID = os.environ.get("ARK_MODEL_ID", "doubao-1-5-thinking-vision-pro-250428")

# Google Gemini API配置
# "AIzaSyAUMGFjOEx4gHp5BLbeb6pqDQEjydnWlFk",  # 主密钥
# "AIzaSyA_te7PSxGls4YmslspG2aRE0GgeOOFs2c",  # 武书钊
# "AIzaSyDTcc8nvff00_2Eui44yyv7j8jV23fm4MM",  # 崔
# "AIzaSyCe42q75c56_xzATol1Snz6YGIav6v9nO8",  # 许高然
# "AIzaSyAbP1BoeQ3M82KkEo5jiIPUPEiU0-wd-6M",  # 邱文瑞
# "AIzaSyCcIWLpIAPGfTv_8txG7TP-eVmzJpuU79A",  # 姚圣
# "AIzaSyB42nKpbipdL8MiALT7jpdoFmUAtdmN-kc",  # 常宝瑞
# "AIzaSyDYgWaE8wWG50m5OYz_3JLzrRRRXMWL-DM",  # 张璐爽
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyDYgWaE8wWG50m5OYz_3JLzrRRRXMWL-DM")
GEMINI_BASE_URL = os.environ.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1/")
# GEMINI_MODEL_ID = os.environ.get("GEMINI_MODEL_ID", "gemini-2.5-flash-preview-05-20")
GEMINI_MODEL_ID = os.environ.get("GEMINI_MODEL_ID", "gemini-2.5-pro")

# 通义千问API配置
QWEN_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "sk-60d76b6077414033a1b9eb7285c39e73")
QWEN_BASE_URL = os.environ.get("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
QWEN_MODEL_ID = os.environ.get("QWEN_MODEL_ID", "qwen-vl-max")

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
        },
        "volcengine-vision": {
            "type": "ark",
            "api_key": ARK_API_KEY,
            "base_url": ARK_BASE_URL,
            "model_id": ARK_MODEL_ID,
            "description": "火山引擎豆包视觉语言模型"
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
    # "vision": "gemini",
    # "vision": "qwen-vl",     # 视觉分析模型：可选 "qwen-vl", "gemini", "volcengine-vision"
    "vision": "volcengine-vision", 
    "language": "gemini", # 语言生成模型
    "embedding": "chinese-clip" # 向量嵌入模型 - 支持图像和文本的多模态模型
}

# 保持向后兼容的生成器配置
GENERATOR_CONFIG = {
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
        "city_inspection": """你是一名专业的城市体检员，请严格依据《城市体检工作手册》的视角，对下图进行专业、客观、详细的描述。

**【分析要求】**
请按照以下三级层次化分类体系进行精确识别：

**一级体检维度（维度类别）→ 二级指标名称（指标名称）→ 三级指标（具体问题）**

**【完整指标体系】**
一、住房维度
**2.1 存在结构安全隐患的住宅数量**
    2.1.1 - 混凝土结构件裂缝：如承重墙体、楼板、结构梁开裂，裂缝肉眼清晰可见，裂缝较深。墙体、楼板裂缝多为贯通状；梁裂缝多集中于梁的底部，呈现多条裂缝
    2.1.2 - 违规拆除结构承重构件：如户内承重墙体拆墙打洞，底商或者地库结构柱拆除，砖混结构拆除阳台承重墙垛
    2.1.3 - 砖混结构主体出现砖体缺棱掉角、表面存在裂缝，砂浆饱满度差，呈粉末状，砖与砂浆之间存在较大裂缝
    2.1.4 - 违规拆除外窗窗下墙体加建阳台，违规加建悬挑飘窗

**2.2 存在燃气安全隐患的住宅数量**
    2.2.1 - 住宅燃气立管、引入管、水平干管运行满20年，且存在锈蚀严重、破损
    
**2.3 存在楼道安全隐患的住宅数量**
    2.3.1 - 楼梯间内楼梯踏步缺损、楼梯扶手松动或缺失、照明损坏缺失、安全护栏松动损坏或缺失
    2.3.2 - 通风井道、排风烟道等堵塞，造成通风不畅、异味串味
    2.3.3 - 住宅消防门缺失、损坏、无法关闭
    2.3.4 - 消火栓缺失或无水、无日常维护、老化损坏
    2.3.5 - 住宅灭火器缺失、未设置灭火器保护设施。注意消防规范明确要求，灭火器应设置在灭火器箱或挂钩上，不能随意放置在地面，以免影响疏散或被损坏。
    2.3.6 - 住宅消防安全出口指示灯损坏或者缺失
    2.3.7 - 违规占用消防楼梯、楼道、管道井等公共空间，用于堆放杂物
    2.3.8 - 公共楼道停放自行车、电动自行车以及违规充电

**2.4 存在围护安全隐患的住宅数量**
    2.4.1 - 外墙装饰材料和保温材料开裂、损坏、脱落
    2.4.2 - 外墙悬挂设施不规范（如过大、过高）或损坏松脱的情况
    2.4.3 - 门窗玻璃存在破损、脱落等情况
    2.4.4 - 屋面排水不畅、漏水
    2.4.5 - 外墙内侧或地下室渗水漏水

**2.6 存在管线管道破损的住宅数量**
    2.6.1 - 存在给水管线跑冒滴漏的问题
    2.6.2 - 存在排水管线老化破损、渗漏堵塞的问题
    2.6.3 - 存在采暖季温度不达标问题
    2.6.4 - 存在电力管线老化破损及裸露、私搭乱接的问题

**2.7 需要进行适老化改造的住宅数量**
    2.7.2 - 住宅单元出入口和通道未进行无障碍改造、地面防滑处理。注意：重点检查出入口是否存在台阶但未配建规范的无障碍坡道或扶手的情况。
    2.7.3 - 楼梯间未沿墙加装扶手

**2.9 需要进行数字化改造的住宅数量**
    2.9.2 - 住宅公共空间未安装楼宇入侵报警、视频监控等安防检测设备
    2.9.3 - 高层住宅的楼梯间、走道、候梯厅、门厅等公共部位未安装烟感报警器

二、小区维度
**14. 停车泊位缺口数**
  14.3 存在占用消防通道问题。注意：消防通道通常是楼梯口、过道、消防车通道等区域。

**16. 未配建电动自行车充电设施的小区数量**
  16.1 未配建电动自行车集中充电设施
  16.2 小区电动自行车乱拉飞线充电、安全防护设施配备和消防安全管理不到位

**17. 未达标配建的公共活动场地的小区数量**  注意：公共活动场地侧重活动功能，指供儿童娱乐、老年活动、体育健身等的专属场地空间（其地面铺装、设施均属于场地配套范畴）
  17.1 小区（社区）公共活动场地及公共绿地存在儿童娱乐、老年活动、体育健身设施不充足或破损的问题。注意：重点检查儿童游乐区、健身区的彩色塑胶地面、缓冲地垫等安全设施的破损情况。

**18. 不达标的步行道长度**  注意：步行道侧重通行功能，指小区及周边 “主要人行道路”（如连接出入口、单元门的通行道路），铺装形式为混凝土、沥青或砖石等
  18.1 小区及周边道路的主要人行道路存在路面破损问题。
  18.2 小区及周边道路的主要人行道路存在宽度不足问题
  18.3 小区及周边道路的主要人行道路存在雨后积水问题。注意：重点检查路面是否存在水洼、水渍。
  18.4 小区及周边道路的主要人行道路存在夜间照明不足问题

**21. 需要进行智慧化改造的小区数量**
  21.1 智能安防设施、智能安防系统不完善

**【输出格式要求】**
请严格按照以下格式输出：

**指标分类**: 将匹配到的一级和二级指标组合，格式为：维度名称 - 指标序号 指标名称
**具体问题**: [将匹配到的三级具体问题的序号与文本组合，格式为：问题序号 - 具体问题。在组合三级指标文本时，如果文本中包含“注意”、“例如”等起解释说明作用的词语，则只输出这些词语之前的问题描述本身。]
**详细描述**: [对图片中观察到的具体情况进行客观、量化的专业描述，输出一段话，不要分点，不要太短]

**示例**：
**指标分类**: 小区维度 - 18 不达标的步行道长度
**具体问题**: 18.1 - 小区及周边道路的主要人行道路存在路面破损问题
**详细描述**: 图中所示为文体路周边的人行道路区域，步行道石材铺装存在多处破碎、松动、缺失情况，部分石材脱离原铺设位置，形成明显的路面破损状况。

**【描述要求】**
1. 先分类，再描述：首先明确指出图片内容符合上述列表中的具体指标。如果图中存在多个问题，选择并描述其中两个最明显的问题，尽量选择问题区域占比较大的。
2. 客观描述：只描述看到的物理事实，避免主观判断。请严格区分正常的老化/磨损与构成安全隐患的“破损/缺失”。 只有当状态明确符合指标描述时才可上报，不能仅因为物体外观陈旧或不整洁而判定为问题。
3. 专业用词：使用专业术语（如"飞线充电"、"围护结构"等）
4. 精准定位：明确指出问题的具体位置和特征


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
                                [文本块1 - 具体规范]: "{retrieved_chunk_1_content}" 
                                *来源: {retrieved_chunk_1_metadata}*
                            
                                [文本块2 - 具体规范]: "{retrieved_chunk_2_content}"
                                *来源: {retrieved_chunk_2_metadata}*
                                ---
                            
                            3.  **知识库参考案例图片**:
                                [案例图片 1]: <retrieved_case_photo_1_placeholder>
                                [案例图片 2]: <retrieved_case_photo_2_placeholder>
                            
                            **[你的任务]**
                            
                            请严格按照以下格式，结合所有输入信息，生成分析报告：
                            
                            - **指标分类**: [此处填写“视觉分析结果”中的“指标分类”字段]

                            - **具体问题**: [此处填写“视觉-分析结果”中的“具体问题”字段]
                            
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