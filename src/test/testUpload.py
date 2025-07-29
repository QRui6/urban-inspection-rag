import requests

# 定义文件路径
# 正确方式：为多个文件使用列表形式
files = [
    ('file', open('E:/program/AI/RAG/output/images/25c75e4fa2655fe47da94d68b4436459fbd4b9258cfb0b96e1009fe29aebcdf4.jpg', 'rb')),
    ('file', open('E:/program/AI/RAG/output/images/25c75e4fa2655fe47da94d68b4436459fbd4b9258cfb0b96e1009fe29aebcdf4.jpg', 'rb'))
]

# 自定义 Headers - 移除content-type，让requests自动处理
headers = {
    "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY0OWJiNzlkLWIxNDgtNDhmNS05NjA1LWY0YmIwY2Y3OTkzYSIsInVzZXJuYW1lIjoiaml1bnVhbiIsImlhdCI6MTc0Nzc0ODAyMCwiZXhwIjoxNzQ4MzUyODIwfQ==.9ka2DvVP-V51bSqbZNxvhXSNxgE5jTnECphWe9igafk",
    "Cookie": "cf_clearance=EXmmZeLgQHPYhCw8S9DKn4LL8u3fKaj6dEzcbOAk9Co-1747747751-1.2.1.1-XiSDECl0iAnc85x4I4tK.9y.5zO6JyzjfuBxyIExQaOj1R.UdDMPKufM5Lj0nMoM5T9FQvFMC3Z5NSLp4RFUz7MB.A89M5rN3UacQtrRgutH3PplTSL9LOIoP4scNKW.i0NuYenezWJMwa0f2uh42Inr_FP5rsumYA3HZeqm48Rd6ohAYAFDZ8.ZIcydtc7VwCzSZrbCoNFM0aqcDUE37VFF6OYjC1iUKa4ysZw4pnrATj_p3ptARdlUuUSPw7rIbJzh6K0lXXIDhMg2kNGX6CwzhjgC_HcZkkZkYWJjpNOKtMWhl49hXcG7apEBxD1RqlmX3Jlu7xF4hmpQuEhUIDWkEMJf1.ibN9J0SGewB7s"
}

# 目标 URL
url = 'https://bed.djxs.xyz/upload'

try:
    # 发送 POST 请求
    response = requests.post(url, files=files, headers=headers)
    
    # 检查响应
    print(f"状态码: {response.status_code}")
    print(f"响应内容: {response.text}")
    
    # 如果成功，解析并打印图片URL
    if response.status_code == 200:
        result = response.json()
        if isinstance(result, list):
            for i, item in enumerate(result):
                if "src" in item:
                    image_url = "https://bed.djxs.xyz" + item["src"]
                    print(f"图片 {i+1} 上传成功: {image_url}")
except Exception as e:
    print(f"上传失败: {str(e)}")
finally:
    # 关闭文件
    for _, file in files:
        file.close()