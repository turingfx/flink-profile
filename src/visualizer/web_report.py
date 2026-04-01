"""
Flink 集群负载分析 Web 报告生成器
生成静态 HTML 报告
"""
import json
from datetime import datetime
from typing import List, Dict
import os


class WebReportGenerator:
    """Web 报告生成器"""

    def __init__(self, output_dir: str = 'output'):
        self.output_dir = output_dir
        self.charts_dir = os.path.join(output_dir, 'charts')

    def _generate_summary(self, analysis_results: List[Dict]) -> Dict:
        """生成汇总统计"""
        cluster_result = next((r for r in analysis_results if r['machine'] == 'cluster'), None)
        machine_results = [r for r in analysis_results if r['machine'] != 'cluster']

        # 找出显著偏差的机器
        high_deviation_machines = []
        for r in machine_results:
            cpu_dev = r['cpu_stats']['profile_deviation_mean']
            mem_dev = r['memory_stats']['profile_deviation_mean']
            if cpu_dev > 20 or mem_dev > 20:
                high_deviation_machines.append({
                    'machine': r['machine'],
                    'cpu_deviation': cpu_dev,
                    'memory_deviation': mem_dev,
                })

        return {
            'total_machines': len(machine_results),
            'cluster_cpu_accuracy': cluster_result['cpu_stats']['profile_accuracy'] if cluster_result else 0,
            'cluster_memory_accuracy': cluster_result['memory_stats']['profile_accuracy'] if cluster_result else 0,
            'avg_cpu_accuracy': sum(r['cpu_stats']['profile_accuracy'] for r in machine_results) / len(machine_results),
            'avg_memory_accuracy': sum(r['memory_stats']['profile_accuracy'] for r in machine_results) / len(machine_results),
            'high_deviation_machines': high_deviation_machines,
            'total_anomalies': sum(r['cpu_stats']['anomaly_count'] + r['memory_stats']['anomaly_count']
                                  for r in machine_results),
        }

    def generate_html(self, analysis_results: List[Dict]) -> str:
        """生成 HTML 报告"""
        summary = self._generate_summary(analysis_results)

        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flink 集群负载效果评估报告</title>
    <style>
        :root {{
            --primary: #3b82f6;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --dark: #1e293b;
            --light: #f8fafc;
            --border: #e2e8f0;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: var(--light);
            color: var(--dark);
            line-height: 1.6;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}

        header {{
            background: linear-gradient(135deg, var(--primary), #1d4ed8);
            color: white;
            padding: 40px 20px;
            text-align: center;
            border-radius: 12px;
            margin-bottom: 30px;
        }}

        header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
        }}

        header p {{
            opacity: 0.9;
            font-size: 1.1rem;
        }}

        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .card {{
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}

        .card-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 16px;
        }}

        .card-icon {{
            width: 48px;
            height: 48px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
        }}

        .icon-primary {{ background: #dbeafe; }}
        .icon-success {{ background: #d1fae5; }}
        .icon-warning {{ background: #fef3c7; }}
        .icon-danger {{ background: #fee2e2; }}

        .card-title {{
            font-size: 0.875rem;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .card-value {{
            font-size: 2rem;
            font-weight: 700;
            margin-top: 4px;
        }}

        .section {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}

        .section h2 {{
            font-size: 1.5rem;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 2px solid var(--border);
        }}

        .chart-container {{
            text-align: center;
            margin: 20px 0;
        }}

        .chart-container img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}

        .alert {{
            padding: 16px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            align-items: flex-start;
            gap: 12px;
        }}

        .alert-warning {{
            background: #fef3c7;
            border-left: 4px solid var(--warning);
        }}

        .alert-danger {{
            background: #fee2e2;
            border-left: 4px solid var(--danger);
        }}

        .alert-success {{
            background: #d1fae5;
            border-left: 4px solid var(--success);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}

        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}

        th {{
            background: var(--light);
            font-weight: 600;
            color: #64748b;
            font-size: 0.875rem;
            text-transform: uppercase;
        }}

        tr:hover {{
            background: var(--light);
        }}

        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.875rem;
            font-weight: 500;
        }}

        .badge-success {{ background: #d1fae5; color: #065f46; }}
        .badge-warning {{ background: #fef3c7; color: #92400e; }}
        .badge-danger {{ background: #fee2e2; color: #991b1b; }}

        .grid-2 {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
        }}

        .legend {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin: 20px 0;
            flex-wrap: wrap;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
        }}

        .text-muted {{
            color: #64748b;
        }}

        footer {{
            text-align: center;
            padding: 40px;
            color: #64748b;
        }}

        @media (max-width: 768px) {{
            header h1 {{ font-size: 1.75rem; }}
            .grid-2 {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Flink 集群负载效果评估报告</h1>
            <p>画像负载与实际负载偏差分析 | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>

        <!-- 汇总卡片 -->
        <div class="summary-cards">
            <div class="card">
                <div class="card-header">
                    <div class="card-icon icon-primary">🖥️</div>
                    <div>
                        <div class="card-title">分析机器数</div>
                        <div class="card-value">{summary['total_machines']}</div>
                    </div>
                </div>
            </div>
            <div class="card">
                <div class="card-header">
                    <div class="card-icon icon-success">✅</div>
                    <div>
                        <div class="card-title">CPU 预测准确率</div>
                        <div class="card-value">{summary['cluster_cpu_accuracy']:.1f}%</div>
                    </div>
                </div>
            </div>
            <div class="card">
                <div class="card-header">
                    <div class="card-icon icon-success">📊</div>
                    <div>
                        <div class="card-title">内存预测准确率</div>
                        <div class="card-value">{summary['cluster_memory_accuracy']:.1f}%</div>
                    </div>
                </div>
            </div>
            <div class="card">
                <div class="card-header">
                    <div class="card-icon {'icon-danger' if summary['total_anomalies'] > 10 else 'icon-warning'}">⚠️</div>
                    <div>
                        <div class="card-title">异常点总数</div>
                        <div class="card-value">{summary['total_anomalies']}</div>
                    </div>
                </div>
            </div>
        </div>
'''

        # 添加警告区域
        if summary['high_deviation_machines']:
            html += '''
        <div class="alert alert-warning">
            <span>⚠️</span>
            <div>
                <strong>偏差警告</strong><br>
                以下机器的画像负载与实际负载偏差超过 20%，需要关注：
                <ul style="margin-top: 8px; margin-left: 20px;">
'''
            for m in summary['high_deviation_machines']:
                html += f"                    <li>{m['machine']}: CPU偏差 {m['cpu_deviation']:.1f}%, 内存偏差 {m['memory_deviation']:.1f}%</li>\n"
            html += '''                </ul>
            </div>
        </div>
'''

        # 集群趋势分析
        html += '''
        <div class="section">
            <h2>📈 集群负载趋势分析</h2>
            <div class="legend">
                <div class="legend-item"><div class="legend-color" style="background: #3b82f6;"></div>实际负载</div>
                <div class="legend-item"><div class="legend-color" style="background: #10b981;"></div>逻辑负载</div>
                <div class="legend-item"><div class="legend-color" style="background: #f59e0b;"></div>画像负载</div>
            </div>
            <div class="chart-container">
                <img src="charts/cluster_trend.png" alt="集群负载趋势">
            </div>
            <p class="text-muted">
                上图展示了集群整体的 CPU 和内存负载趋势。蓝色线表示实际负载，绿色虚线表示逻辑负载，橙色线表示画像负载。
                阴影区域表示画像负载与实际负载之间的偏差范围。
            </p>
        </div>

        <div class="grid-2">
            <div class="section">
                <h2>🖥️ 机器负载对比</h2>
                <div class="chart-container">
                    <img src="charts/machine_comparison.png" alt="机器负载对比">
                </div>
                <p class="text-muted">
                    对比各机器的平均负载，标注了画像负载与实际负载偏差较大的机器。
                </p>
            </div>

            <div class="section">
                <h2>📊 准确率与偏差分析</h2>
                <div class="chart-container">
                    <img src="charts/accuracy_analysis.png" alt="准确率分析">
                </div>
                <p class="text-muted">
                    展示了各机器的画像负载预测准确率、平均偏差和异常点统计。准确率目标线为 80%。
                </p>
            </div>
        </div>

        <div class="section">
            <h2>🔥 负载偏差热力图</h2>
            <div class="chart-container">
                <img src="charts/deviation_heatmap.png" alt="偏差热力图">
            </div>
            <p class="text-muted">
                热力图展示了不同时段各机器的负载偏差情况。颜色越深表示偏差越大。
                可用于识别负载异常的时间规律和机器。
            </p>
        </div>

        <div class="section">
            <h2>📋 详细分析数据</h2>
            <table>
                <thead>
                    <tr>
                        <th>机器</th>
                        <th>CPU 实际均值</th>
                        <th>CPU 画像均值</th>
                        <th>CPU 准确率</th>
                        <th>内存实际均值</th>
                        <th>内存画像均值</th>
                        <th>内存准确率</th>
                        <th>异常点</th>
                    </tr>
                </thead>
                <tbody>
'''

        for r in analysis_results:
            cpu_acc = r['cpu_stats']['profile_accuracy']
            mem_acc = r['memory_stats']['profile_accuracy']
            anomalies = r['cpu_stats']['anomaly_count'] + r['memory_stats']['anomaly_count']

            html += f'''                    <tr>
                        <td><strong>{r['machine']}</strong></td>
                        <td>{r['cpu_stats']['actual_mean']:.1f}%</td>
                        <td>{r['cpu_stats']['profile_mean']:.1f}%</td>
                        <td><span class="badge {'badge-success' if cpu_acc >= 80 else 'badge-warning'}">{cpu_acc:.1f}%</span></td>
                        <td>{r['memory_stats']['actual_mean']:.1f}%</td>
                        <td>{r['memory_stats']['profile_mean']:.1f}%</td>
                        <td><span class="badge {'badge-success' if mem_acc >= 80 else 'badge-warning'}">{mem_acc:.1f}%</span></td>
                        <td>{anomalies}</td>
                    </tr>
'''

        html += '''                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>📝 分析结论与建议</h2>
'''

        # 生成结论
        avg_acc = (summary['cluster_cpu_accuracy'] + summary['cluster_memory_accuracy']) / 2
        if avg_acc >= 85:
            html += '''            <div class="alert alert-success">
                <span>✅</span>
                <div>
                    <strong>总体评估：优秀</strong><br>
                    画像负载预测准确率超过 85%，预测模型表现良好，能够有效反映集群负载情况。
                </div>
            </div>
'''
        elif avg_acc >= 70:
            html += '''            <div class="alert alert-warning">
                <span>⚠️</span>
                <div>
                    <strong>总体评估：良好</strong><br>
                    画像负载预测准确率在 70%-85% 之间，模型基本可用，但仍有优化空间。
                </div>
            </div>
'''
        else:
            html += '''            <div class="alert alert-danger">
                <span>❌</span>
                <div>
                    <strong>总体评估：需改进</strong><br>
                    画像负载预测准确率低于 70%，模型需要重新调优或更换算法。
                </div>
            </div>
'''

        html += '''            <h3 style="margin-top: 20px;">优化建议：</h3>
            <ol style="margin-left: 20px; line-height: 2;">
                <li><strong>偏差较大机器优化：</strong>对于画像负载偏差超过 20% 的机器，建议检查资源采集逻辑和画像模型参数。</li>
                <li><strong>时间规律分析：</strong>根据热力图识别负载异常高发时段，优化调度策略。</li>
                <li><strong>异常点排查：</strong>针对偏差超过 30% 的异常点进行深入分析，可能是业务突发或系统故障导致。</li>
                <li><strong>模型迭代：</strong>持续收集数据，定期重新训练画像模型，提高预测准确性。</li>
            </ol>
        </div>

        <footer>
            <p>Flink 集群负载效果评估系统 | 报告生成时间: ''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '''</p>
            <p class="text-muted">本报告基于 data-visualization 最佳实践生成</p>
        </footer>
    </div>
</body>
</html>'''

        # 保存文件
        output_path = os.path.join(self.output_dir, 'report.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        return output_path
