# Flink 集群画像负载效果评估项目

## 项目概述

本项目是一个用于分析 Flink 集群模式下每台机器/集群负载情况的工具，主要用于评估画像负载的效果。通过采集和分析集群的实际负载、逻辑负载和画像负载数据，帮助识别负载不均衡问题，优化资源调度策略。

### 核心概念

| 指标类型 | 说明 | 特点 |
|---------|------|------|
| **实际负载** | 机器真实的运行时负载 | 波动大，反映瞬时状态 |
| **逻辑负载** | 最终表现机器负载的指标 | 等于实际负载 × floating ratio，或资源负载，两者取最小值 |
| **画像负载** | 基于模型估算的合理负载水位 | 相对稳定，代表预期负载 |

### 分析目标

1. **画像负载差值评估**: 计算画像负载与实际负载的偏差程度
2. **负载均衡分析**: 识别集群内各 WorkManager 的负载分布不均情况
3. **资源饱和度评估**: 评估 CPU 和内存资源的使用率和超分情况

## 项目结构

```
flink-profile/
├── CLAUDE.md                 # 项目详细说明文档
├── AGENTS.md                 # 本文件，AI 助手上下文文档
├── data/                     # 数据目录
│   ├── raw/                  # 原始负载数据（采集自 Flink 管理界面）
│   └── processed/            # 处理后的数据（Parquet 格式）
├── src/                      # 源代码
│   ├── collector/            # 数据采集模块
│   ├── analyzer/             # 负载分析模块
│   └── visualizer/           # 可视化模块
├── scripts/                  # 脚本工具
├── output/                   # 分析结果输出（Markdown 和 HTML 格式）
└── web/                      # 认证信息存储
    ├── cookie.txt            # 访问 Flink 管理界面的 Cookie
    └── *.har                 # HAR 格式的网络请求文件
```

## 技术栈

- **语言**: Python 3.10+
- **数据格式**: Parquet（处理后数据）、JSON（原始数据）、HAR（网络请求）
- **可视化**: matplotlib、seaborn
- **报告格式**: Markdown、HTML
- **代码规范**: PEP 8

## 负载指标

### 机器维度指标

每个 WorkManager 都有以下三种资源的负载指标：

1. **CPU 使用率** (cpu_usage)
2. **内存使用率** (memory_usage)

每种资源都有三种负载类型：
- 实际负载（actual）
- 逻辑负载（logical）
- 画像负载（profile）

### 集群维度指标

- 集群总资源使用率
- WorkManager 负载分布
- Floating Ratio 配置（CPU 和内存浮动比例）
- 运行作业数量

## 生成报告（最常用）

### 一键生成报告

```bash
# 更新 web/cookie.txt 后直接运行，自动采集数据并生成 HTML 报告
python3 scripts/collect_and_report.py
```

报告输出到 `output/cluster_load_report.html`，macOS 下会自动用浏览器打开。

### 脚本说明

| 脚本 | 功能 |
|------|------|
| `scripts/collect_and_report.py` | 采集 + 报告一体化入口，日常使用这个 |
| `scripts/gen_report.py` | 仅从 `/tmp/wm_*.json` 重新渲染报告（不重新采集） |

### Cookie 过期时的处理流程

Cookie 有效期约 12 小时，过期后 API 会返回 302 跳转到登录页。

**更新步骤（由用户操作）：**
1. 浏览器登录 `mybkcosmos.mybank.cn`
2. 打开开发者工具 → Network → 随便点一个请求 → 复制 Cookie 请求头
3. 粘贴到 `web/cookie.txt`（替换全部内容，只保留一行 cookie 字符串）

**或者通过 CDP 方式采集（当 cookie.txt 失效时）：**

当 `collect_and_report.py` 报 HTTP 错误时，改用 CDP 浏览器方式：

1. 确保 web-access skill 的 CDP Proxy 已运行（`node ~/.qoder/skills/web-access/scripts/check-deps.mjs`）
2. 打开目标页面并注入 Cookie：
   ```
   目标 URL：https://mybkcosmos.mybank.cn/proxy/cosmos/flink/cluster/eg168-cluster-pre/
             eg168-cluster-pre-service.blink-operator.svc.eg168.mybank.cn:8081/#/overview
   ```
3. 通过浏览器内 fetch 调用以下 API 获取数据（带登录态）：
   - `GET /overview` → 集群总览（floating ratio、总资源）
   - `GET /workermanagers` → 4 台机器列表（CPU占用、内存占用、画像值）
   - `GET /workermanagers/{ip}` → 单机详情，返回每个 worker 的三种负载：
     - `physicalResource` = 实际负载
     - `logicalResource` = 逻辑负载
     - `profiledResource` = 画像负载
   - 4 台机器 IP：`33.190.84.129` / `33.190.85.106` / `33.190.85.70` / `33.190.85.103`
4. 将响应保存到 `/tmp/wm_{ip}.json`，再运行 `python3 scripts/gen_report.py`

### 环境准备

```bash
python3 -m venv venv
source venv/bin/activate
pip install pandas pyarrow matplotlib seaborn requests beautifulsoup4
```

## 开发规范

### 代码风格

- 使用 Python 3.10+
- 遵循 PEP 8 规范
- 类型注解必须完整（使用 `typing` 模块）
- 函数和类需要有清晰的文档字符串

### 数据处理规范

- **不可变原则**: 原始数据（`data/raw/`）不可修改
- **数据存储**: 处理后的数据使用 Parquet 格式存储在 `data/processed/`
- **时间格式**: 时间戳统一使用 UTC 格式
- **错误处理**: 数据采集和处理过程中需要完善的错误处理和日志记录

### 分析输出规范

- **可视化**: 使用 matplotlib/seaborn 生成图表
- **报告格式**: 优先使用 Markdown 格式，可同时生成 HTML
- **关键指标**: 报告必须包含统计摘要和关键发现
- **风险标注**: 对负载异常（差值过大）的机器进行明确标注

### 模块职责

#### collector 模块
- 从 Flink 管理界面采集负载数据
- 使用 HAR 文件和 Cookie 进行认证
- 支持多集群数据采集
- 数据清洗和初步验证

#### analyzer 模块
- 计算实际负载、逻辑负载和画像负载
- 计算负载偏差和预测准确率
- 识别负载不均衡和资源超分情况
- 生成分析结果数据

#### visualizer 模块
- 生成负载分析报告（Markdown/HTML）
- 创建可视化图表（负载趋势、分布等）
- 高亮显示关键发现和风险提示

## 数据采集注意事项

1. **只读操作**: 不要尝试修改任何页面数据，只做数据采集
2. **认证信息**: `web/cookie.txt` 包含敏感的认证信息，需妥善保管
3. **数据源**: 主要从 Flink 管理界面（如 mybkcosmos.mybank.cn）采集数据
4. **频率控制**: 避免过于频繁的数据采集，防止对生产系统造成压力

## 评估方法

### 1. 偏差分析

```python
# 计算负载偏差
deviation = |actual_load - profile_load| / actual_load
```

### 2. 预测准确率

```python
# 计算负载是否在实际负载的合理区间内
within_range = actual_load * 0.8 <= profile_load <= actual_load * 1.2
accuracy = count(within_range) / total_samples
```

### 3. 风险识别

- **高负载风险**: 逻辑负载 > 100%
- **超分风险**: 物理负载远超 100%（如 > 200%）
- **不均衡风险**: 单机负载偏差显著高于集群平均水平

## 项目状态

- **框架**: 已搭建完成（目录结构、模块划分）
- **源代码**: 各模块待实现（collector、analyzer、visualizer）
- **示例输出**: 已有 cluster_load_report.md 作为报告模板参考
- **数据源**: 已配置 cookie.txt 和 HAR 文件

## 下一步开发建议

1. **实现 collector 模块**: 完成从 Flink 管理界面采集数据的功能
2. **实现 analyzer 模块**: 实现负载计算和分析逻辑
3. **实现 visualizer 模块**: 生成报告和可视化图表
4. **添加单元测试**: 确保数据分析和计算的准确性
5. **完善日志系统**: 便于调试和问题排查

## 联系方式

如有问题或需要帮助，请参考 CLAUDE.md 获取更详细的项目说明。