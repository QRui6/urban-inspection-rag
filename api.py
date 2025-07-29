"""
RAG系统API服务
提供REST API接口，包装RAG系统功能
"""
import os
import time
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from main import RAGSystem, image_to_base64
from src.storage.chroma_store import ChromaStore
from config.config import PROMPT_CONFIG

# 初始化Flask应用
app = Flask(__name__)
CORS(app)  # 启用跨域支持

# 初始化RAG系统
rag = RAGSystem(dual_retrieval=True)  # 默认启用双路检索

# 上传文件配置
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 创建会话存储，用于在不同请求之间保存视觉分析结果
# 格式: {session_id: {"visual_analysis": "...", "timestamp": 1234567890, "img_input": "..."}}
session_store = {}

# 初始化RAG系统前，加载知识库快照到Chroma
SNAPSHOT_PATH = os.path.join("output", "embedded_chunks.json")
if os.path.exists(SNAPSHOT_PATH):
    print(f"检测到知识库快照文件: {SNAPSHOT_PATH}，正在加载到Chroma...")
    try:
        with open(SNAPSHOT_PATH, "r", encoding="utf-8") as f:
            embedded_chunks = json.load(f)
        chroma_store = ChromaStore()
        # chroma_store.delete_index()  # 清空collection，防止重复
        success = chroma_store.add_documents(embedded_chunks)
        if success:
            print("知识库快照已成功加载到Chroma数据库！")
        else:
            print("加载知识库快照到Chroma时发生错误，请检查日志。")
    except Exception as e:
        print(f"加载知识库快照失败: {e}")
else:
    print(f"未检测到知识库快照文件: {SNAPSHOT_PATH}，请先运行主流程构建知识库。")

def allowed_file(filename):
    """检查文件类型是否允许上传"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        "status": "ok",
        "timestamp": time.time()
    })

@app.route('/api/analyze-image', methods=['POST'])
def analyze_image():
    """图片分析接口
    接收问题和图片URL或base64数据，只执行视觉模型分析，立即返回结果
    """
    try:
        data = request.json
        if not data or 'query' not in data:
            return jsonify({"error": "缺少必要参数", "message": "query参数为必填项"}), 400
        
        # 生成会话ID
        session_id = str(time.time())
        
        query_text = data['query']
        img_url = data.get('image_url', None)  # 可选参数：图片URL
        img_base64 = data.get('image_base64', None)  # 可选参数：图片base64
        
        if not img_url and not img_base64:
            return jsonify({"error": "缺少图片数据", "message": "image_url或image_base64至少提供一项"}), 400
        
        # 选择图片输入源
        img_input = img_base64 if img_base64 else img_url
        
        # 调用RAG系统执行视觉分析
        vl_prompt = PROMPT_CONFIG["vision_analysis"]["city_inspection"]
        vl_text, model_used = rag.analyze_image(img_input, vl_prompt)
        
        # 添加失败重试机制（与query函数保持一致）
        if not vl_text and os.path.exists(img_input):
            print("尝试使用base64方式调用视觉模型...")
            try:
                from main import image_to_base64  # 确保导入函数
                base64_image = image_to_base64(img_input)
                if base64_image:
                    vl_text, model_used = rag.analyze_image(base64_image, vl_prompt)
                    model_used = f"{model_used} (本地文件转base64)"
            except Exception as e:
                print(f"本地文件转base64调用失败: {e}")
        
        if not vl_text:
            return jsonify({
                "error": "图片分析失败", 
                "message": "无法识别图片内容",
                "status": "error",
                "timestamp": time.time()
            }), 500
        
        # 保存分析结果到会话存储，便于后续请求使用
        session_store[session_id] = {
            "visual_analysis": vl_text,
            "query": query_text,
            "img_input": img_input,
            "timestamp": time.time()
        }
        
        # 构建并返回响应
        result = {
            "session_id": session_id,
            "status": "success",
            "visual_analysis": vl_text,
            "models_used": {
                "vision": model_used,
                "language": None
            },
            "timestamp": time.time()
        }
        
        return jsonify(result)
    except Exception as e:
        print(f"处理图片分析请求时出错: {str(e)}")
        return jsonify({
            "error": "处理图片分析请求时出错", 
            "message": str(e),
            "status": "error",
            "timestamp": time.time()
        }), 500

@app.route('/api/complete-answer', methods=['POST'])
def complete_answer():
    """完成回答接口
    接收会话ID，基于之前的视觉分析结果生成最终回答
    """
    try:
        data = request.json
        if not data or 'session_id' not in data:
            return jsonify({"error": "缺少必要参数", "message": "session_id参数为必填项"}), 400
        
        session_id = data['session_id']
        
        # 检查会话是否存在
        if session_id not in session_store:
            return jsonify({
                "error": "无效的会话ID", 
                "message": "会话已过期或不存在",
                "status": "error",
                "timestamp": time.time()
            }), 404
        
        # 获取会话数据
        session_data = session_store[session_id]
        visual_analysis = session_data["visual_analysis"]
        query_text = session_data["query"]
        img_input = session_data["img_input"]
        
        # 基于视觉分析结果，完成最终答案生成
        response = rag.complete_answer(query_text, img_input, visual_analysis)
        
        # 构建API响应
        result = {
            "status": response.get("status", "success"),
            "answer": response.get("answer"),
            "models_used": response.get("models_used"),
            "timestamp": time.time()
        }
        
        # 清理会话存储
        # 注意：实际生产环境应该有更完善的会话过期清理机制
        if session_id in session_store:
            del session_store[session_id]
        
        return jsonify(result)
    except Exception as e:
        print(f"生成最终回答时出错: {str(e)}")
        return jsonify({
            "error": "生成最终回答时出错", 
            "message": str(e),
            "status": "error",
            "timestamp": time.time()
        }), 500

@app.route('/api/query', methods=['POST'])
def query():
    """问答接口(原始完整流程，保留以兼容旧版)
    接收JSON格式的请求，包含问题和可选的图片URL或base64数据
    返回AI回答，如果有图片输入，则同时返回视觉分析结果
    """
    try:
        data = request.json
        if not data or 'query' not in data:
            return jsonify({"error": "缺少必要参数", "message": "query参数为必填项"}), 400
        
        query_text = data['query']
        img_url = data.get('image_url', None)  # 可选参数：图片URL
        img_base64 = data.get('image_base64', None)  # 可选参数：图片base64
        
        # 处理图片输入 - 优先使用base64方式
        if img_base64 and img_base64.startswith('data:image'):
            # 使用base64数据调用RAG系统
            # 由于RAG系统已经支持base64输入，这里直接传递即可
            print("使用base64图片数据进行问答")
            response = rag.query(query_text, img_base64)
        elif img_url:
            # 使用URL方式调用RAG系统 - 用于终端测试
            print(f"使用图片URL进行问答: {img_url}")
            response = rag.query(query_text, img_url)
        else:
            # 纯文本问答
            print("执行纯文本问答")
            response = rag.query(query_text)
        
        # 构建API响应，包含状态、视觉分析结果和最终答案
        result = {
            "status": response.get("status", "success"),
            "timestamp": time.time()
        }
        
        # 添加视觉分析结果（如果有）
        if response.get("visual_analysis"):
            result["visual_analysis"] = response["visual_analysis"]
        
        # 添加使用的模型信息
        if response.get("models_used"):
            result["models_used"] = response["models_used"]
            
        # 添加最终答案（如果有）
        if response.get("answer"):
            result["answer"] = response["answer"]
        
        return jsonify(result)
    except Exception as e:
        print(f"处理请求时出错: {str(e)}")
        return jsonify({
            "error": "处理请求时出错", 
            "message": str(e),
            "status": "error"
        }), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """文件上传接口
    接收图片文件，保存到服务器，并返回图片URL和base64数据
    """
    # 检查是否有文件上传
    if 'file' not in request.files:
        return jsonify({"error": "未发现上传文件"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "未选择文件"}), 400
    
    if file and allowed_file(file.filename):
        # 安全地获取文件名并保存
        filename = secure_filename(file.filename)
        timestamp = int(time.time())
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # 生成文件的URL路径
        file_url = f"/uploads/{unique_filename}"
        full_url = request.host_url.rstrip('/') + file_url
        
        # 转换为base64以便直接在前端显示和发送到模型
        try:
            base64_data = image_to_base64(filepath)
            if base64_data:
                print(f"成功生成图片base64数据: {filepath}, 文件URL: {file_url}")
                return jsonify({
                    "file_url": file_url,
                    "base64": base64_data,
                    "filename": filename,
                    "success": True
                })
        except Exception as e:
            print(f"转换base64出错: {e}")
            # 如果base64转换失败，仅返回URL
            return jsonify({
                "file_url": file_url,
                "filename": filename,
                "error": f"Base64转换失败: {str(e)}",
                "success": False
            })
        
    return jsonify({"error": "不支持的文件类型"}), 400

@app.route('/uploads/<filename>', methods=['GET'])
def uploaded_file(filename):
    """提供上传文件的访问接口"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# 记录未捕获的异常
@app.errorhandler(Exception)
def handle_exception(e):
    """全局异常处理器，记录错误并返回适当的响应"""
    # 记录详细错误信息
    import traceback
    error_details = traceback.format_exc()
    print(f"发生未捕获的异常: {str(e)}\n{error_details}")
    
    # 返回给客户端的错误响应
    return jsonify({
        "error": "服务器内部错误",
        "message": str(e)
    }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 