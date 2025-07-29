import concurrent.futures
from typing import List, Dict, Any, Callable

def vlm_image_describe(img_path: str, context: str, vlm_api_func: Callable) -> str:
    """
    调用VLM模型API，输入图片路径和上下文，返回图片描述。
    vlm_api_func(img_path, context) -> str
    """
    return vlm_api_func(img_path, context)


def batch_vlm_describe(image_chunks: List[Dict[str, Any]], vlm_api_func: Callable, max_workers: int = 8) -> List[Dict[str, Any]]:
    """
    并发处理图片chunk，返回有意义的图片描述chunk列表
    """
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_chunk = {
            executor.submit(vlm_image_describe, chunk["metadata"]["img_path"], chunk["metadata"].get("context", ""), vlm_api_func): chunk
            for chunk in image_chunks
        }
        for future in concurrent.futures.as_completed(future_to_chunk):
            chunk = future_to_chunk[future]
            try:
                desc = future.result()
                # 过滤无意义图片
                if desc and desc.strip().lower() != "none" and len(desc.strip()) >= 10:
                    chunk["type"] = "image_desc"
                    chunk["content"] = desc.strip()
                    results.append(chunk)
            except Exception as e:
                print(f"VLM处理图片失败: {chunk['metadata']['img_path']}，错误: {e}")
    return results 