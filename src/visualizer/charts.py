"""
Flink 集群负载可视化模块
基于 data-visualization skill 的最佳实践
"""
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import seaborn as sns
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
import os

# 设置中文字体和样式
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'

# 颜色方案
colors = {
    'actual': '#3b82f6',    # 蓝色 - 实际负载
    'logical': '#10b981',   # 绿色 - 逻辑负载
    'profile': '#f59e0b',   # 橙色 - 画像负载
    'warning': '#ef4444',   # 红色 - 警告/异常
    'grid': '#e2e8f0',      # 浅灰 - 网格线
}


class LoadVisualizer:
    """负载可视化器"""

    def __init__(self, output_dir: str = 'output/charts'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def _save_fig(self, name: str) -> str:
        """保存图表"""
        path = os.path.join(self.output_dir, f'{name}.png')
        plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        return path

    def plot_cluster_trend(self, df: pd.DataFrame) -> str:
        """绘制集群负载趋势图（线图）"""
        cluster_df = df[df['machine'] == 'cluster'].copy()
        cluster_df = cluster_df.sort_values('timestamp')

        fig, axes = plt.subplots(2, 1, figsize=(14, 10))

        # CPU 趋势
        ax1 = axes[0]
        ax1.plot(cluster_df['timestamp'], cluster_df['actual_cpu'],
                color=colors['actual'], linewidth=2, label='实际负载', marker='o', markersize=3)
        ax1.plot(cluster_df['timestamp'], cluster_df['logical_cpu'],
                color=colors['logical'], linewidth=2, label='逻辑负载', linestyle='--')
        ax1.plot(cluster_df['timestamp'], cluster_df['profile_cpu'],
                color=colors['profile'], linewidth=2.5, label='画像负载', marker='s', markersize=3)
        ax1.fill_between(cluster_df['timestamp'], cluster_df['profile_cpu'], cluster_df['actual_cpu'],
                        alpha=0.1, color=colors['actual'])

        ax1.set_ylabel('CPU 使用率 (%)', fontsize=12)
        ax1.set_title('Flink 集群 CPU 负载趋势分析', fontsize=16, fontweight='bold', pad=15)
        ax1.legend(fontsize=11, loc='upper right')
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.grid(axis='y', alpha=0.3)
        ax1.set_ylim(0, 100)

        # 标注关键数据点
        max_idx = cluster_df['actual_cpu'].idxmax()
        max_row = cluster_df.loc[max_idx]
        ax1.annotate(f'峰值: {max_row["actual_cpu"]:.1f}%',
                    xy=(max_row['timestamp'], max_row['actual_cpu']),
                    xytext=(10, 10), textcoords='offset points',
                    fontsize=10, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))

        # Memory 趋势
        ax2 = axes[1]
        ax2.plot(cluster_df['timestamp'], cluster_df['actual_memory'],
                color=colors['actual'], linewidth=2, label='实际负载', marker='o', markersize=3)
        ax2.plot(cluster_df['timestamp'], cluster_df['logical_memory'],
                color=colors['logical'], linewidth=2, label='逻辑负载', linestyle='--')
        ax2.plot(cluster_df['timestamp'], cluster_df['profile_memory'],
                color=colors['profile'], linewidth=2.5, label='画像负载', marker='s', markersize=3)

        ax2.set_ylabel('内存使用率 (%)', fontsize=12)
        ax2.set_title('Flink 集群内存负载趋势分析', fontsize=16, fontweight='bold', pad=15)
        ax2.legend(fontsize=11, loc='upper right')
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        ax2.grid(axis='y', alpha=0.3)
        ax2.set_ylim(0, 100)

        plt.tight_layout()
        return self._save_fig('cluster_trend')

    def plot_machine_comparison(self, df: pd.DataFrame) -> str:
        """绘制各机器负载对比（水平柱状图）"""
        # 计算各机器的平均负载
        machine_df = df[df['machine'] != 'cluster']
        avg_loads = machine_df.groupby('machine').agg({
            'actual_cpu': 'mean',
            'profile_cpu': 'mean',
            'actual_memory': 'mean',
            'profile_memory': 'mean',
        }).reset_index()

        # 按实际 CPU 负载排序
        avg_loads = avg_loads.sort_values('actual_cpu', ascending=True)

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # CPU 对比
        ax1 = axes[0]
        y_pos = np.arange(len(avg_loads))
        height = 0.35

        bars1 = ax1.barh(y_pos - height/2, avg_loads['actual_cpu'], height,
                          color=colors['actual'], label='实际负载')
        bars2 = ax1.barh(y_pos + height/2, avg_loads['profile_cpu'], height,
                          color=colors['profile'], label='画像负载')

        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(avg_loads['machine'])
        ax1.set_xlabel('CPU 使用率 (%)', fontsize=12)
        ax1.set_title('各机器 CPU 负载对比', fontsize=14, fontweight='bold')
        ax1.legend(fontsize=10)
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.set_xlim(0, 100)

        # 添加数值标签
        for i, (actual, profile) in enumerate(zip(avg_loads['actual_cpu'], avg_loads['profile_cpu'])):
            diff = abs(actual - profile)
            if diff > 10:  # 差值超过10%需要关注
                ax1.text(max(actual, profile) + 2, i, f'⚠ {diff:.1f}%', fontsize=9, color=colors['warning'])

        # Memory 对比
        ax2 = axes[1]
        avg_loads_mem = avg_loads.sort_values('actual_memory', ascending=True)
        y_pos = np.arange(len(avg_loads_mem))

        bars1 = ax2.barh(y_pos - height/2, avg_loads_mem['actual_memory'], height,
                          color=colors['actual'], label='实际负载')
        bars2 = ax2.barh(y_pos + height/2, avg_loads_mem['profile_memory'], height,
                          color=colors['profile'], label='画像负载')

        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(avg_loads_mem['machine'])
        ax2.set_xlabel('内存使用率 (%)', fontsize=12)
        ax2.set_title('各机器内存负载对比', fontsize=14, fontweight='bold')
        ax2.legend(fontsize=10)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        ax2.set_xlim(0, 100)

        plt.tight_layout()
        return self._save_fig('machine_comparison')

    def plot_deviation_heatmap(self, df: pd.DataFrame) -> str:
        """绘制负载偏差热力图"""
        machine_df = df[df['machine'] != 'cluster'].copy()

        # 计算每台机器每小时的偏差
        machine_df['hour'] = machine_df['timestamp'].dt.hour
        machine_df['cpu_deviation'] = abs(machine_df['actual_cpu'] - machine_df['profile_cpu'])

        # 创建透视表
        pivot = machine_df.groupby(['machine', 'hour'])['cpu_deviation'].mean().unstack(fill_value=0)

        fig, ax = plt.subplots(figsize=(14, 8))

        im = ax.imshow(pivot.values, cmap='Reds', aspect='auto', vmin=0, vmax=30)

        # 设置坐标轴
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels([f'{h}:00' for h in pivot.columns])
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels(pivot.index)

        # 添加数值标注
        for i in range(len(pivot.index)):
            for j in range(len(pivot.columns)):
                value = pivot.iloc[i, j]
                color = 'white' if value > 15 else 'black'
                ax.text(j, i, f'{value:.1f}', ha='center', va='center', fontsize=8, color=color)

        ax.set_title('各机器 CPU 负载偏差热力图（实际 vs 画像）', fontsize=16, fontweight='bold')
        ax.set_xlabel('时间 (小时)', fontsize=12)
        ax.set_ylabel('机器', fontsize=12)

        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('偏差 (%)', fontsize=11)

        plt.tight_layout()
        return self._save_fig('deviation_heatmap')

    def plot_accuracy_gauge(self, analysis_results: List[Dict]) -> str:
        """绘制准确率仪表盘"""
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))

        # 提取数据
        machines = [r['machine'] for r in analysis_results if r['machine'] != 'cluster']
        cpu_accuracy = [r['cpu_stats']['profile_accuracy'] for r in analysis_results if r['machine'] != 'cluster']
        mem_accuracy = [r['memory_stats']['profile_accuracy'] for r in analysis_results if r['machine'] != 'cluster']

        # CPU 准确率柱状图
        ax1 = axes[0, 0]
        colors_bar = [colors['logical'] if a >= 80 else colors['warning'] for a in cpu_accuracy]
        bars = ax1.bar(machines, cpu_accuracy, color=colors_bar)
        ax1.set_ylabel('准确率 (%)', fontsize=11)
        ax1.set_title('CPU 画像负载预测准确率', fontsize=13, fontweight='bold')
        ax1.set_ylim(0, 100)
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.axhline(y=80, color='red', linestyle='--', alpha=0.5, label='目标线 80%')
        ax1.legend()

        # 添加数值标签
        for bar, val in zip(bars, cpu_accuracy):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{val:.1f}%', ha='center', fontsize=9)

        # Memory 准确率柱状图
        ax2 = axes[0, 1]
        colors_bar = [colors['logical'] if a >= 80 else colors['warning'] for a in mem_accuracy]
        bars = ax2.bar(machines, mem_accuracy, color=colors_bar)
        ax2.set_ylabel('准确率 (%)', fontsize=11)
        ax2.set_title('内存画像负载预测准确率', fontsize=13, fontweight='bold')
        ax2.set_ylim(0, 100)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        ax2.axhline(y=80, color='red', linestyle='--', alpha=0.5, label='目标线 80%')
        ax2.legend()

        for bar, val in zip(bars, mem_accuracy):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{val:.1f}%', ha='center', fontsize=9)

        # 偏差分布
        ax3 = axes[1, 0]
        cpu_deviation = [r['cpu_stats']['profile_deviation_mean'] for r in analysis_results if r['machine'] != 'cluster']
        mem_deviation = [r['memory_stats']['profile_deviation_mean'] for r in analysis_results if r['machine'] != 'cluster']

        x = np.arange(len(machines))
        width = 0.35
        ax3.bar(x - width/2, cpu_deviation, width, label='CPU 偏差', color=colors['actual'])
        ax3.bar(x + width/2, mem_deviation, width, label='内存偏差', color=colors['profile'])
        ax3.set_ylabel('平均偏差 (%)', fontsize=11)
        ax3.set_title('画像负载平均偏差', fontsize=13, fontweight='bold')
        ax3.set_xticks(x)
        ax3.set_xticklabels(machines, rotation=45)
        ax3.legend()
        ax3.spines['top'].set_visible(False)
        ax3.spines['right'].set_visible(False)

        # 异常点统计
        ax4 = axes[1, 1]
        cpu_anomalies = [r['cpu_stats']['anomaly_count'] for r in analysis_results if r['machine'] != 'cluster']
        mem_anomalies = [r['memory_stats']['anomaly_count'] for r in analysis_results if r['machine'] != 'cluster']

        ax4.bar(x - width/2, cpu_anomalies, width, label='CPU 异常', color=colors['warning'])
        ax4.bar(x + width/2, mem_anomalies, width, label='内存异常', color=colors['logical'])
        ax4.set_ylabel('异常点数', fontsize=11)
        ax4.set_title('偏差超过 30% 的异常点统计', fontsize=13, fontweight='bold')
        ax4.set_xticks(x)
        ax4.set_xticklabels(machines, rotation=45)
        ax4.legend()
        ax4.spines['top'].set_visible(False)
        ax4.spines['right'].set_visible(False)

        plt.tight_layout()
        return self._save_fig('accuracy_analysis')

    def generate_all_charts(self, df: pd.DataFrame, analysis_results: List[Dict]) -> Dict[str, str]:
        """生成所有图表"""
        return {
            'cluster_trend': self.plot_cluster_trend(df),
            'machine_comparison': self.plot_machine_comparison(df),
            'deviation_heatmap': self.plot_deviation_heatmap(df),
            'accuracy_analysis': self.plot_accuracy_gauge(analysis_results),
        }
