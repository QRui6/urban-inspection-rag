import torch

# 检查 CUDA 是否可用
is_cuda_available = torch.cuda.is_available()
print(f"Is CUDA available? {is_cuda_available}")

if is_cuda_available:
    # 如果可用，打印出 CUDA 版本和设备信息
    print(f"PyTorch CUDA version: {torch.version.cuda}")
    print(f"Number of GPUs: {torch.cuda.device_count()}")
    print(f"GPU Name: {torch.cuda.get_device_name(0)}")
else:
    # 如果不可用，打印出错误原因
    print("CUDA is not available. You are running on the CPU-only version of PyTorch.")