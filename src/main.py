"""
Flink 集群负载分析主程序
生成完整的分析报告和 Web 页面
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from analyzer.load_generator import LoadDataGenerator, LoadAnalyzer
from visualizer.charts import LoadVisualizer
from visualizer.web_report import WebReportGenerator


def main():
    print("=" * 60)
    print("Flink 集群负载效果评估系统")
    print("=" * 60)

    # 1. 生成模拟数据
    print("\n[1/4] 正在生成负载数据...")
    generator = LoadDataGenerator(num_machines=5, days=7)
    machine_df, cluster_df = generator.generate_all_data()

    # 合并数据
    full_df = pd.concat([machine_df, cluster_df], ignore_index=True)

    # 保存原始数据
    os.makedirs('data/processed', exist_ok=True)
    full_df.to_csv('data/processed/load_data.csv', index=False)
    print(f"  ✓ 生成了 {len(full_df)} 条记录（{len(full_df[full_df['machine']=='cluster'])} 条集群聚合数据）")

    # 2. 负载分析
    print("\n[2/4] 正在进行负载分析...")
    analyzer = LoadAnalyzer()
    analysis_results = analyzer.analyze_all(full_df)

    # 打印分析摘要
    cluster_result = next((r for r in analysis_results if r['machine'] == 'cluster'), None)
    if cluster_result:
        print(f"  ✓ 集群 CPU 画像准确率: {cluster_result['cpu_stats']['profile_accuracy']:.1f}%")
        print(f"  ✓ 集群内存画像准确率: {cluster_result['memory_stats']['profile_accuracy']:.1f}%")

    # 3. 生成图表
    print("\n[3/4] 正在生成可视化图表...")
    visualizer = LoadVisualizer(output_dir='output/charts')
    charts = visualizer.generate_all_charts(full_df, analysis_results)
    for name, path in charts.items():
        print(f"  ✓ 生成: {path}")

    # 4. 生成 Web 报告
    print("\n[4/4] 正在生成 Web 报告...")
    report_gen = WebReportGenerator(output_dir='output')
    report_path = report_gen.generate_html(analysis_results)
    print(f"  ✓ 生成: {report_path}")

    # 完成
    print("\n" + "=" * 60)
    print("分析完成！")
    print("=" * 60)
    print(f"\n📊 查看报告: file://{os.path.abspath(report_path)}")
    print(f"📁 图表目录: {os.path.abspath('output/charts')}")
    print(f"💾 数据文件: {os.path.abspath('data/processed/load_data.csv')}")
    print("\n你可以直接打开 report.html 在浏览器中查看完整报告。")

    return report_path


if __name__ == '__main__':
    main()
