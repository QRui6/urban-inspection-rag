import os
import base64
import requests
import re

def upload_image(image_path):
    """
    上传图片到指定图床服务
    
    Args:
        image_path: 本地图片路径
        
    Returns:
        图片URL
    """
    url = "https://bed.djxs.xyz/upload"
    
    # 设置请求头 - 移除content-type，让requests自动处理
    headers = {
        "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY0OWJiNzlkLWIxNDgtNDhmNS05NjA1LWY0YmIwY2Y3OTkzYSIsInVzZXJuYW1lIjoiaml1bnVhbiIsImlhdCI6MTc0Nzc0ODAyMCwiZXhwIjoxNzQ4MzUyODIwfQ==.9ka2DvVP-V51bSqbZNxvhXSNxgE5jTnECphWe9igafk",
        "Cookie": "cf_clearance=EXmmZeLgQHPYhCw8S9DKn4LL8u3fKaj6dEzcbOAk9Co-1747747751-1.2.1.1-XiSDECl0iAnc85x4I4tK.9y.5zO6JyzjfuBxyIExQaOj1R.UdDMPKufM5Lj0nMoM5T9FQvFMC3Z5NSLp4RFUz7MB.A89M5rN3UacQtrRgutH3PplTSL9LOIoP4scNKW.i0NuYenezWJMwa0f2uh42Inr_FP5rsumYA3HZeqm48Rd6ohAYAFDZ8.ZIcydtc7VwCzSZrbCoNFM0aqcDUE37VFF6OYjC1iUKa4ysZw4pnrATj_p3ptARdlUuUSPw7rIbJzh6K0lXXIDhMg2kNGX6CwzhjgC_HcZkkZkYWJjpNOKtMWhl49hXcG7apEBxD1RqlmX3Jlu7xF4hmpQuEhUIDWkEMJf1.ibN9J0SGewB7s"
    }
    
    try:
        # 准备文件数据
        files = {'file': open(image_path, 'rb')}
        
        # 发送POST请求
        response = requests.post(url, headers=headers, files=files)
        
        # 检查响应状态
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0 and "src" in result[0]:
                # 拼接完整URL
                image_url = "https://bed.djxs.xyz" + result[0]["src"]
                print(f"图片上传成功: {image_url}")
                return image_url
            else:
                raise Exception(f"上传响应格式异常: {result}")
        else:
            raise Exception(f"上传失败，状态码: {response.status_code}，响应: {response.text}")
            
    except Exception as e:
        print(f"图片上传失败: {str(e)}")
        raise
    finally:
        # 确保文件被关闭
        if 'files' in locals() and hasattr(files['file'], 'close'):
            files['file'].close()

def image_to_base64(image_path):
    """
    将图片转换为base64编码
    
    Args:
        image_path: 本地图片路径
        
    Returns:
        base64编码的图片字符串
    """
    try:
        with open(image_path, "rb") as image_file:
            # 读取图片文件内容
            image_data = image_file.read()
            # 转换为base64编码
            base64_encoded = base64.b64encode(image_data).decode('utf-8')
            
            # 获取图片格式
            img_format = os.path.splitext(image_path)[1].lower()
            if img_format == '.jpg' or img_format == '.jpeg':
                mime_type = 'image/jpeg'
            elif img_format == '.png':
                mime_type = 'image/png'
            elif img_format == '.webp':
                mime_type = 'image/webp'
            elif img_format == '.gif':
                mime_type = 'image/gif'
            else:
                # 默认使用jpeg
                mime_type = 'image/jpeg'
                
            # 返回base64 URL格式
            return f"data:{mime_type};base64,{base64_encoded}"
    except Exception as e:
        print(f"图片转base64失败: {str(e)}")
        return None

def extract_image_url(text):
    """
    从用户输入中提取图片URL
    """
    # 匹配以http(s)://开头，以jpg/jpeg/png/gif等常见图片格式结尾的URL
    pattern = r'(https?://\S+\.(jpg|jpeg|png|gif|bmp|webp))'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        img_url = match.group(0)
        # 移除URL，只保留文本部分
        clean_text = text.replace(img_url, '').strip()
        return clean_text, img_url
    return text, None 