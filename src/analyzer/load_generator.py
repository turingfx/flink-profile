"""
Flink 集群负载数据生成器
生成模拟的实际负载、逻辑负载和画像负载数据
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import random


class LoadDataGenerator:
    """生成 Flink 集群的负载数据"""

    def __init__(self, num_machines: int = 5, days: int = 7):
        self.num_machines = num_machines
        self.days = days
        self.machines = [f"worker-{i:02d}" for i in range(1, num_machines + 1)]

    def _generate_base_pattern(self, hours: int) -> np.ndarray:
        """生成基础负载模式（模拟昼夜规律）"""
        x = np.linspace(0, 2 * np.pi * hours / 24, hours)
        # 白天高、晚上低的模式
        base = 0.3 + 0.4 * (np.sin(x - np.pi/2) + 1) / 2
        return base

    def _add_noise(self, data: float, noise_level: float = 0.1) -> float:
        """添加随机波动"""
        noise = np.random.normal(0, noise_level)
        return float(np.clip(data + noise, 0, 1))

    def generate_machine_loads(self) -> pd.DataFrame:
        """生成每台机器的负载数据"""
        hours = self.days * 24
        timestamps = [datetime.now() - timedelta(hours=hours-i) for i in range(hours)]

        records = []
        for machine in self.machines:
            # 基础模式
            base_cpu = self._generate_base_pattern(hours)
            base_memory = self._generate_base_pattern(hours) * 0.8

            # 为不同机器添加特性
            machine_factor = random.uniform(0.7, 1.3)

            for i, ts in enumerate(timestamps):
                # 实际负载（带噪声的真实负载）
                actual_cpu = self._add_noise(base_cpu[i] * machine_factor)
                actual_memory = self._add_noise(base_memory[i] * machine_factor)

                # 逻辑负载 = 实际负载 * floating ratio (0.8-1.2)
                floating_ratio = random.uniform(0.8, 1.2)
                logical_cpu = min(actual_cpu * floating_ratio, 1.0)
                logical_memory = min(actual_memory * floating_ratio, 1.0)

                # 画像负载（模型估算的稳定负载）
                profile_cpu = base_cpu[i] * machine_factor * 0.95
                profile_memory = base_memory[i] * machine_factor * 0.95

                records.append({
                    'timestamp': ts,
                    'machine': machine,
                    'actual_cpu': round(actual_cpu * 100, 2),
                    'logical_cpu': round(logical_cpu * 100, 2),
                    'profile_cpu': round(profile_cpu * 100, 2),
                    'actual_memory': round(actual_memory * 100, 2),
                    'logical_memory': round(logical_memory * 100, 2),
                    'profile_memory': round(profile_memory * 100, 2),
                })

        return pd.DataFrame(records)

    def generate_cluster_aggregated(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成集群聚合数据"""
        cluster_df = df.groupby('timestamp').agg({
            'actual_cpu': 'mean',
            'logical_cpu': 'mean',
            'profile_cpu': 'mean',
            'actual_memory': 'mean',
            'logical_memory': 'mean',
            'profile_memory': 'mean',
        }).reset_index()
        cluster_df['machine'] = 'cluster'
        return cluster_df

    def generate_all_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """生成所有数据"""
        machine_df = self.generate_machine_loads()
        cluster_df = self.generate_cluster_aggregated(machine_df)
        return machine_df, cluster_df


class LoadAnalyzer:
    """负载分析器"""

    @staticmethod
    def calculate_deviation(actual: float, calculated: float) -> float:
        """计算负载偏差百分比"""
        if actual == 0:
            return 0
        return abs(actual - calculated) / actual * 100

    @staticmethod
    def is_within_range(actual: float, calculated: float, tolerance: float = 0.2) -> bool:
        """判断计算值是否在实际值的合理区间内"""
        return actual * (1 - tolerance) <= calculated <= actual * (1 + tolerance)

    @staticmethod
    def analyze_machine(df: pd.DataFrame, machine: str) -> Dict:
        """分析单个机器的负载情况"""
        machine_data = df[df['machine'] == machine]

        results = {
            'machine': machine,
            'samples': len(machine_data),
        }

        # CPU 分析
        for metric_type in ['cpu', 'memory']:
            actual_col = f'actual_{metric_type}'
            logical_col = f'logical_{metric_type}'
            profile_col = f'profile_{metric_type}'

            actual = machine_data[actual_col]
            logical = machine_data[logical_col]
            profile = machine_data[profile_col]

            # 偏差分析
            logical_deviation = (abs(actual - logical) / actual * 100).replace([np.inf, -np.inf], 0).fillna(0)
            profile_deviation = (abs(actual - profile) / actual * 100).replace([np.inf, -np.inf], 0).fillna(0)

            # 准确率（在20%误差范围内）
            logical_accuracy = (abs(logical - actual) / actual <= 0.2).mean() * 100
            profile_accuracy = (abs(profile - actual) / actual <= 0.2).mean() * 100

            # 画像差值评估 - 高/低百分比
            profile_diff_pct = ((profile - actual) / actual * 100).mean()

            results[f'{metric_type}_stats'] = {
                'actual_mean': round(actual.mean(), 2),
                'actual_max': round(actual.max(), 2),
                'logical_mean': round(logical.mean(), 2),
                'profile_mean': round(profile.mean(), 2),
                'logical_deviation_mean': round(logical_deviation.mean(), 2),
                'profile_deviation_mean': round(profile_deviation.mean(), 2),
                'logical_accuracy': round(logical_accuracy, 2),
                'profile_accuracy': round(profile_accuracy, 2),
                'profile_diff_pct': round(profile_diff_pct, 2),  # 正数表示画像高于实际
                'anomaly_count': int((profile_deviation > 30).sum()),  # 偏差超过30%的异常点
            }

        return results

    @staticmethod
    def analyze_all(df: pd.DataFrame) -> List[Dict]:
        """分析所有机器"""
        machines = df['machine'].unique()
        return [LoadAnalyzer.analyze_machine(df, m) for m in machines]
