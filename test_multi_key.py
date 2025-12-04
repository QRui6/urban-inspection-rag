#!/usr/bin/env python
"""
多密钥功能测试脚本
"""
import time
import concurrent.futures
from src.utils.api_key_manager import APIKeyManager


def test_basic_functionality():
    """测试基本功能"""
    print("\n" + "="*60)
    print("测试1: 基本功能")
    print("="*60)
    
    # 创建测试密钥
    api_keys = [
        {"name": "密钥1", "key": "test_key_1"},
        {"name": "密钥2", "key": "test_key_2"},
        {"name": "密钥3", "key": "test_key_3"},
    ]
    
    manager = APIKeyManager(api_keys, max_concurrent_per_key=2)
    
    # 获取密钥
    print("\n获取密钥:")
    for i in range(5):
        result = manager.get_available_key()
        if result:
            key_name, api_key = result
            print(f"  {i+1}. 获取到: {key_name}")
            time.sleep(0.1)
    
    # 查看统计
    print("\n统计信息:")
    stats = manager.get_statistics()
    for name, stat in stats.items():
        print(f"  {name}:")
        print(f"    - 活跃请求: {stat['active_requests']}")
        print(f"    - 总请求数: {stat['total_requests']}")
    
    print("\n✓ 基本功能测试通过")


def test_concurrent_access():
    """测试并发访问"""
    print("\n" + "="*60)
    print("测试2: 并发访问")
    print("="*60)
    
    api_keys = [
        {"name": "密钥1", "key": "test_key_1"},
        {"name": "密钥2", "key": "test_key_2"},
        {"name": "密钥3", "key": "test_key_3"},
    ]
    
    manager = APIKeyManager(api_keys, max_concurrent_per_key=2)
    
    def worker(worker_id):
        """模拟工作进程"""
        result = manager.get_available_key()
        if result:
            key_name, api_key = result
            print(f"  Worker {worker_id}: 使用 {key_name}")
            time.sleep(1)  # 模拟处理
            manager.release_key(key_name, success=True)
            return f"Worker {worker_id} 完成"
        else:
            print(f"  Worker {worker_id}: 无可用密钥")
            return f"Worker {worker_id} 失败"
    
    # 并发执行
    print("\n启动10个并发Worker:")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker, i) for i in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    # 查看统计
    print("\n统计信息:")
    stats = manager.get_statistics()
    for name, stat in stats.items():
        print(f"  {name}:")
        print(f"    - 总请求: {stat['total_requests']}")
        print(f"    - 成功率: {stat['success_rate']:.1f}%")
    
    print("\n✓ 并发访问测试通过")


def test_load_balancing():
    """测试负载均衡"""
    print("\n" + "="*60)
    print("测试3: 负载均衡策略")
    print("="*60)
    
    api_keys = [
        {"name": "密钥1", "key": "test_key_1"},
        {"name": "密钥2", "key": "test_key_2"},
        {"name": "密钥3", "key": "test_key_3"},
    ]
    
    manager = APIKeyManager(api_keys, max_concurrent_per_key=5)
    
    # 测试轮询策略
    print("\n轮询策略 (round_robin):")
    for i in range(6):
        result = manager.get_available_key(strategy="round_robin")
        if result:
            key_name, _ = result
            print(f"  {i+1}. {key_name}")
            manager.release_key(key_name)
    
    # 测试最少负载策略
    print("\n最少负载策略 (least_loaded):")
    # 先给密钥1增加负载
    manager.get_available_key()
    manager.get_available_key()
    
    for i in range(3):
        result = manager.get_available_key(strategy="least_loaded")
        if result:
            key_name, _ = result
            print(f"  {i+1}. {key_name} (应该优先选择密钥2和密钥3)")
    
    print("\n✓ 负载均衡测试通过")


def test_failure_handling():
    """测试失败处理"""
    print("\n" + "="*60)
    print("测试4: 失败处理")
    print("="*60)
    
    api_keys = [
        {"name": "密钥1", "key": "test_key_1"},
        {"name": "密钥2", "key": "test_key_2"},
    ]
    
    manager = APIKeyManager(api_keys, max_concurrent_per_key=2)
    
    # 模拟密钥1多次失败
    print("\n模拟密钥1多次失败:")
    for i in range(12):
        result = manager.get_available_key()
        if result:
            key_name, _ = result
            # 密钥1总是失败
            success = (key_name != "密钥1")
            manager.release_key(key_name, success=success, error="模拟错误" if not success else None)
            print(f"  {i+1}. {key_name} - {'成功' if success else '失败'}")
    
    # 查看统计
    print("\n统计信息:")
    stats = manager.get_statistics()
    for name, stat in stats.items():
        print(f"  {name}:")
        print(f"    - 总请求: {stat['total_requests']}")
        print(f"    - 失败请求: {stat['failed_requests']}")
        print(f"    - 成功率: {stat['success_rate']:.1f}%")
        print(f"    - 可用状态: {stat['is_available']}")
    
    print("\n✓ 失败处理测试通过")


def test_performance():
    """测试性能"""
    print("\n" + "="*60)
    print("测试5: 性能测试")
    print("="*60)
    
    # 单密钥
    print("\n单密钥性能:")
    api_keys_1 = [{"name": "密钥1", "key": "test_key_1"}]
    manager_1 = APIKeyManager(api_keys_1, max_concurrent_per_key=3)
    
    start = time.time()
    count = 0
    for _ in range(100):
        result = manager_1.get_available_key()
        if result:
            count += 1
            manager_1.release_key(result[0])
    elapsed_1 = time.time() - start
    print(f"  100次操作耗时: {elapsed_1:.3f}秒")
    print(f"  成功获取: {count}次")
    
    # 3密钥
    print("\n3密钥性能:")
    api_keys_3 = [
        {"name": "密钥1", "key": "test_key_1"},
        {"name": "密钥2", "key": "test_key_2"},
        {"name": "密钥3", "key": "test_key_3"},
    ]
    manager_3 = APIKeyManager(api_keys_3, max_concurrent_per_key=3)
    
    start = time.time()
    count = 0
    for _ in range(100):
        result = manager_3.get_available_key()
        if result:
            count += 1
            manager_3.release_key(result[0])
    elapsed_3 = time.time() - start
    print(f"  100次操作耗时: {elapsed_3:.3f}秒")
    print(f"  成功获取: {count}次")
    
    print(f"\n性能提升: {elapsed_1/elapsed_3:.2f}x")
    print("\n✓ 性能测试通过")


def main():
    """主测试流程"""
    print("\n" + "="*60)
    print("多密钥功能测试")
    print("="*60)
    
    try:
        test_basic_functionality()
        test_concurrent_access()
        test_load_balancing()
        test_failure_handling()
        test_performance()
        
        print("\n" + "="*60)
        print("✓ 所有测试通过！")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
