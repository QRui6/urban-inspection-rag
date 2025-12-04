"""
将图片转换为base64格式，用于Locust测试
"""
import base64
import sys

def image_to_base64(image_path):
    """将图片文件转换为base64字符串"""
    try:
        with open(image_path, 'rb') as image_file:
            encoded = base64.b64encode(image_file.read()).decode('utf-8')
            # 添加data URI前缀
            if image_path.lower().endswith('.png'):
                prefix = 'data:image/png;base64,'
            elif image_path.lower().endswith(('.jpg', '.jpeg')):
                prefix = 'data:image/jpeg;base64,'
            else:
                prefix = 'data:image/jpeg;base64,'  # 默认使用jpeg
            
            return prefix + encoded
    except Exception as e:
        print(f"转换失败: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python convert_image_to_base64.py <图片路径>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    base64_str = image_to_base64(image_path)
    
    if base64_str:
        # 保存到文件
        with open('test_image_base64.txt', 'w') as f:
            f.write(base64_str)
        
        print(f"✓ 转换成功！")
        print(f"Base64字符串长度: {len(base64_str)}")
        print(f"已保存到: test_image_base64.txt")
        print(f"\n前100个字符预览:")
        print(base64_str[:100] + "...")
    else:
        print("✗ 转换失败")
