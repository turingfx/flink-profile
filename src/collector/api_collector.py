"""
Flink 集群数据采集器
从 Flink 监控 API 获取集群和机器负载数据
"""
import requests
import json
import os
from datetime import datetime
from typing import Dict, List, Any


class FlinkCollector:
    """Flink 集群数据采集器"""

    def __init__(self, cluster_name: str = "eg168-cluster-pre"):
        self.cluster_name = cluster_name
        # 基础 URL
        self.base_url = "https://mybkcosmos.mybank.cn/proxy/cosmos/flink/cluster"
        self.cluster_url = f"{self.cluster_name}/{self.cluster_name}-service.blink-operator.svc.eg168.mybank.cn:8081"

        # Cookie 文件路径
        cookie_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                  "web/cookie.txt")
        self.cookies = self._load_cookies(cookie_path)

    def _load_cookies(self, cookie_path: str) -> Dict[str, str]:
        """加载 Cookie"""
        cookies = {}
        if os.path.exists(cookie_path):
            with open(cookie_path, 'r') as f:
                cookie_str = f.read().strip()
                for item in cookie_str.split(';'):
                    if '=' in item:
                        key, value = item.strip().split('=', 1)
                        cookies[key] = value
        return cookies

    def _get(self, path: str) -> Dict:
        """发送 GET 请求"""
        url = f"{self.base_url}/{self.cluster_url}{path}"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, cookies=self.cookies, verify=False)
        response.raise_for_status()
        return response.json()

    def get_overview(self) -> Dict:
        """获取集群概览"""
        return self._get("/overview")

    def get_workermanagers(self) -> Dict:
        """获取 WorkManager 列表"""
        return self._get("/workermanagers")

    def get_applications(self) -> Dict:
        """获取应用程序列表"""
        return self._get("/applications")

    def collect_all(self) -> Dict:
        """采集所有数据"""
        overview = self.get_overview()
        workermanagers = self.get_workermanagers()
        applications = self.get_applications()

        return {
            "timestamp": datetime.now().isoformat(),
            "overview": overview,
            "workermanagers": workermanagers,
            "applications": applications
        }


def main():
    """测试采集"""
    collector = FlinkCollector()

    print("=" * 80)
    print("Flink 集群数据采集")
    print("=" * 80)

    # 采集数据
    data = collector.collect_all()

    # 解析 overview
    overview = data['overview']
    print("\n【集群概览】")
    print(f"  WorkManager 数量: {overview.get('workerManagerNum')}")
    print(f"  运行作业数: {overview.get('runningApplication')}")

    total_res = overview.get('resourceInfo', {}).get('totalResources', {})
    phys_res = overview.get('resourceInfo', {}).get('physicalResources', {})

    print(f"\n  总资源:")
    print(f"    CPU: {total_res.get('cpuCores')} 核")
    print(f"    内存: {total_res.get('memInMB')} MB")

    print(f"\n  物理资源:")
    print(f"    CPU: {phys_res.get('cpuCores'):.1f} 核")
    print(f"    内存: {phys_res.get('memInMB')} MB")

    # 获取配置
    config = overview.get('configurationMap', {})
    cpu_float = config.get('physical.resource.floating.ratio.cpu', '1.1')
    mem_float = config.get('physical.resource.floating.ratio.memory', '1.1')
    print(f"\n  浮动比例:")
    print(f"    CPU: {cpu_float}")
    print(f"    内存: {mem_float}")

    # 解析 WorkManager
    wms = data['workermanagers'].get('workermanagers', [])
    print("\n" + "=" * 80)
    print("【WorkManager 负载详情】")
    print("=" * 80)

    print(f"\n{'IP':<20} {'逻辑CPU':>12} {'逻辑内存':>12} {'物理CPU':>12} {'物理内存':>12} {'状态':<12}")
    print("-" * 80)

    for wm in wms:
        ip = wm.get('id')
        total_res = wm.get('totalResources', {})
        phys_res = wm.get('physicalResources', {})
        status = wm.get('status')

        used_cpu = total_res.get('usedCpu', 0)
        used_mem = total_res.get('usedMem', 0)
        phys_cpu = phys_res.get('cpuCores', 0)
        phys_mem = phys_res.get('memInMB', 0)

        print(f"{ip:<20} {used_cpu:>11.1f} {used_mem:>11.0f} {phys_cpu:>11.1f} {phys_mem:>11.0f} {status:<12}")

    # 集群汇总
    print("\n" + "=" * 80)
    print("【集群汇总】")
    print("=" * 80)

    # 计算逻辑资源总和
    total_logical_cpu = sum(wm.get('totalResources', {}).get('usedCpu', 0) for wm in wms)
    total_logical_mem = sum(wm.get('totalResources', {}).get('usedMem', 0) for wm in wms)
    total_physical_cpu = sum(wm.get('physicalResources', {}).get('cpuCores', 0) for wm in wms)
    total_physical_mem = sum(wm.get('physicalResources', {}).get('memInMB', 0) for wm in wms)

    print(f"\n逻辑资源（作业请求 × 浮动比例）:")
    print(f"  CPU: {total_logical_cpu:.1f} 核")
    print(f"  内存: {total_logical_mem:.0f} MB")

    print(f"\n物理资源（实际使用）:")
    print(f"  CPU: {total_physical_cpu:.1f} 核")
    print(f"  内存: {total_physical_mem:.0f} MB")

    # 计算画像负载（基于配置）
    # 画像负载 = 物理资源 / 浮动比例
    float_cpu = float(cpu_float)
    float_mem = float(mem_float)

    profile_cpu = total_physical_cpu / float_cpu if float_cpu > 0 else total_physical_cpu
    profile_mem = total_physical_mem / float_mem if float_mem > 0 else total_physical_mem

    print(f"\n画像负载（物理资源 / 浮动比例）:")
    print(f"  CPU: {profile_cpu:.1f} 核")
    print(f"  内存: {profile_mem:.0f} MB")

    return data


if __name__ == "__main__":
    main()