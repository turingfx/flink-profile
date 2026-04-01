# Flink 集群画像负载效果评估

## 项目目标

分析 Flink 集群模式下每台机器/集群 的负载情况，评估画像负载的效果。

## 核心概念

### 负载指标类型

| 类型 | 说明 | 特点 |
|------|------|------|
| **实际负载** | 机器真实的运行时负载 | 波动大，反映瞬时状态 |
| **逻辑负载** | 最终表现机器负载的指标 | 等于实际负载乘以floating ratio，或资源负载，两者之间的最小值。 |
| **画像负载** | 基于模型估算的合理负载水位 | 相对稳定，代表预期负载 |

### 分析目标

1. **画像负载差值评估**: 计算画像负载与实际负载的偏差程度，观察画像负载比实际负载高或低百分之多少。
2. **逻辑负载计算**: 观察有哪些是根据实际负载算出来的，那些是通过资源负载算出来的。

## 项目结构

```
flink-profile/
├── CLAUDE.md                 # 项目说明文档
├── data/                     # 数据目录
│   ├── raw/                  # 原始负载数据
│   └── processed/            # 处理后的数据
├── src/                      # 源代码
│   ├── collector/            # 数据采集模块
│   ├── analyzer/             # 负载分析模块
│   └── visualizer/           # 可视化模块
├── scripts/                  # 脚本工具
└── output/                   # 分析结果输出
└── web/                      # 存储真实作业网页的har包和cookie，你需要访问web拿到实时数据
```

## 负载指标

### 机器维度指标

- CPU 使用率 (cpu_usage)
- 内存使用率 (memory_usage)

每个均有实际/逻辑/画像三种资源。然后集群维度和每台workmanager都有这些指标，你可以分析每台机器和集群维度的差值，以及如果单机差值过大，需要标注一下。


## 评估方法

### 1. 偏差分析

```python
# 计算负载偏差
deviation = |actual_load - calculated_load| / actual_load
```

<!-- ### 2. 波动性分析 -->
<!---->
<!-- ```python -->
<!-- # 标准差比较 -->
<!-- actual_std = std(actual_load_series) -->
<!-- calculated_std = std(calculated_load_series) -->
<!-- stability_ratio = calculated_std / actual_std  # 越小越稳定 -->
<!-- ``` -->

### 3. 预测准确率

```python
# 计算负载是否在实际负载的合理区间内
within_range = actual_load * 0.8 <= calculated_load <= actual_load * 1.2
accuracy = count(within_range) / total_samples
```

## 开发规范

### 代码风格

- 使用 Python 3.10+
- 遵循 PEP 8 规范
- 类型注解必须完整

### 数据处理

- 原始数据不可修改，处理后的数据存入 `data/processed/`
- 数据文件使用 Parquet 格式存储
- 时间戳统一使用 UTC 格式

### 分析输出

- 图表使用 matplotlib/seaborn
- 报告生成使用 Markdown 格式
- 关键指标需输出统计摘要

## 常用命令

```bash
# 数据采集
python -m src.collector --cluster <cluster_name> --output data/raw/

# 负载分析
python -m src.analyzer --input data/processed/ --output output/

# 生成报告
python -m src.visualizer --data output/ --report output/report.md
```

## 注意事项

1. 不要尝试修改任何页面数据，只做数据采集。
