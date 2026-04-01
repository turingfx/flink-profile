# Flink 集群监控接口文档

## 概述

本文档描述 Flink 集群监控页面的 API 接口。

**基础信息：**
- 集群名称：`eg168-cluster-pre`
- 基础 URL：`https://mybkcosmos.mybank.cn/proxy/cosmos/flink/cluster/eg168-cluster-pre/eg168-cluster-pre-service.blink-operator.svc.eg168.mybank.cn:8081`

---

## 接口列表

| 接口 | 方法 | 说明 |
|------|------|------|
| `/overview` | GET | 集群概览 |
| `/workermanagers` | GET | WorkManager 列表 |
| `/applications` | GET | 应用程序列表 |

---

## 接口详情

### 1. 集群概览 `/overview`

**请求：**
```
GET /overview
```

**响应示例：**
```json
{
  "resourceInfo": {
    "totalResources": {
      "cpuCores": 96.0,
      "memInMB": 196608
    },
    "availableResources": {
      "cpuCores": -1.5323721879005419,
      "memInMB": 4279
    },
    "physicalResources": {
      "cpuCores": 38.336984453722835,
      "memInMB": 43177
    }
  },
  "workerManagerNum": 4,
  "runningApplication": 7,
  "completedApplication": 0,
  "configurationMap": {
    "physical.resource.floating.ratio.cpu": "1.1",
    "physical.resource.floating.ratio.memory": "1.1",
    "workermanager.cpu.cores": "32",
    "workermanager.memory.mb": "65536",
    ...
  }
}
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `resourceInfo.totalResources.cpuCores` | double | 总CPU核心数 |
| `resourceInfo.totalResources.memInMB` | double | 总内存(MB) |
| `resourceInfo.availableResources.cpuCores` | double | 可用CPU核心数 |
| `resourceInfo.availableResources.memInMB` | double | 可用内存(MB) |
| `resourceInfo.physicalResources.cpuCores` | double | 物理CPU核心数 |
| `resourceInfo.physicalResources.memInMB` | double | 物理内存(MB) |
| `workerManagerNum` | int | WorkManager 数量 |
| `runningApplication` | int | 运行中的作业数 |
| `configurationMap` | object | 配置项 |

**关键配置项：**
- `physical.resource.floating.ratio.cpu`: CPU 浮动比例 (1.1 = 允许超分 10%)
- `physical.resource.floating.ratio.memory`: 内存浮动比例 (1.1 = 允许超分 10%)
- `workermanager.cpu.cores`: 每个 WorkManager CPU 核心数 (32)
- `workermanager.memory.mb`: 每个 WorkManager 内存 (65536 MB = 64GB)

---

### 2. WorkManager 列表 `/workermanagers`

**请求：**
```
GET /workermanagers
```

**响应示例：**
```json
{
  "workermanagers": [
    {
      "id": "33.190.84.129",
      "path": "akka.tcp://flink@33.190.84.129:50010/user/rpc/workermanager_0",
      "dataPort": 0,
      "version": "UNKNOWN",
      "timeSinceLastHeartbeat": 1774523577730,
      "totalResources": {
        "usedCpu": 25.876693355751037,
        "leftCpu": -1.876693355751037,
        "usedMem": 42137,
        "leftMem": 7015
      },
      "physicalResources": {
        "cpuCores": 8.04655733332038,
        "memInMB": 20802
      },
      "workerTotalUsage": {
        "cpuCores": 15.95344266667962,
        "memInMB": 28350
      },
      "status": "AVAILABLE",
      "failedRunningWorkers": 0,
      "failedScheduling": 0,
      "threadNum": 2272
    }
  ]
}
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `workermanagers[].id` | string | WorkManager IP |
| `workermanagers[].status` | string | 状态 (AVAILABLE/UNAVAILABLE) |
| `workermanagers[].totalResources.usedCpu` | double | 已使用 CPU (逻辑) |
| `workermanagers[].totalResources.leftCpu` | double | 剩余 CPU (逻辑) |
| `workermanagers[].totalResources.usedMem` | double | 已使用内存(MB) (逻辑) |
| `workermanagers[].totalResources.leftMem` | double | 剩余内存(MB) (逻辑) |
| `workermanagers[].physicalResources.cpuCores` | double | 物理 CPU 核心数 |
| `workermanagers[].physicalResources.memInMB` | double | 物理内存(MB) |
| `workermanagers[].workerTotalUsage.cpuCores` | double | 作业实际使用 CPU |
| `workermanagers[].workerTotalUsage.memInMB` | double | 作业实际使用内存(MB) |
| `workermanagers[].threadNum` | int | 线程数 |

**当前 WorkManager 列表：**

| IP | 状态 | 逻辑CPU使用 | 逻辑内存使用 | 物理CPU | 物理内存 |
|----|------|-------------|--------------|---------|----------|
| 33.190.84.129 | AVAILABLE | 25.9 | 42137 MB | 8.0 | 20802 MB |
| 33.190.85.106 | AVAILABLE | 25.6 | 46079 MB | 12.6 | 11149 MB |
| 33.190.85.70 | AVAILABLE | 10.3 | 48724 MB | 18.8 | 7451 MB |
| 33.190.85.103 | AVAILABLE | 32.4 | 55348 MB | -0.04 | 3904 MB |

---

### 3. 应用程序列表 `/applications`

**请求：**
```
GET /applications
```

**响应示例：**
```json
{
  "applications": [
    {
      "applicationInfo": {
        "name": "antc4flink3903000144-mybkc1cn",
        "id": "6d88bf4a6284cd2664496ae2779c0ff5",
        "status": "RUNNING",
        "submit-time": 1774519183524,
        "master-url": "http://33.190.84.129:34847"
      },
      "runningFailures": 0,
      "schedulingFailures": 0,
      "resourceOveruseInfo": {
        "maxCpuOveruseRatio": 0.008666351437568665,
        "maxMemOveruseRatio": 0.19205729166666666,
        "requestedCpu": 1.5,
        "requestedMem": 3072,
        "physicalCpu": 0.012999527156352997,
        "physicalMem": 590
      }
    }
  ]
}
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `applications[].applicationInfo.name` | string | 作业名称 |
| `applications[].applicationInfo.id` | string | 作业 ID |
| `applications[].applicationInfo.status` | string | 状态 (RUNNING/FINISHED/FAILED) |
| `applications[].applicationInfo.submit-time` | long | 提交时间戳 |
| `applications[].applicationInfo.master-url` | string | Master URL |
| `applications[].resourceOveruseInfo.requestedCpu` | double | 请求 CPU |
| `applications[].resourceOveruseInfo.requestedMem` | double | 请求内存(MB) |
| `applications[].resourceOveruseInfo.physicalCpu` | double | 物理 CPU |
| `applications[].resourceOveruseInfo.physicalMem` | double | 物理内存(MB) |
| `applications[].resourceOveruseInfo.maxCpuOveruseRatio` | double | 最大 CPU 超分比例 |
| `applications[].resourceOveruseInfo.maxMemOveruseRatio` | double | 最大内存超分比例 |

**当前运行作业：**

| 作业名称 | ID | 状态 | 请求CPU | 请求内存 | 物理CPU | 物理内存 |
|----------|-----|------|---------|----------|---------|----------|
| antc4flink3903000144-mybkc1cn | 6d88bf... | RUNNING | 1.5 | 3072 | 0.01 | 590 |
| antc4flink3799000341-mybkc1cn | fabd66... | RUNNING | 27.0 | 66150 | 1.07 | 10442 |
| antc4flink3799000264-mybkc1cn | fc6dd1... | RUNNING | 23.1 | 54912 | 33.27 | 43473 |
| antc4flink3903000142-mybkc1cn | 5d131a... | RUNNING | 12.5 | 30868 | 6.34 | 10811 |
| antc4flink3799000390-mybkc1cn | 12469a... | RUNNING | 17.5 | 42144 | 3.11 | 25689 |
| antc4flink3799000366-mybkc1cn | 8b8331... | RUNNING | 27.5 | 55595 | 4.64 | 21905 |
| antc4flink3907000236-mybkc1cn | 599cd4... | RUNNING | 27.1 | 62400 | 8.14 | 40392 |

---

## 负载计算说明

### 1. 逻辑负载 vs 物理负载

- **逻辑负载** = 作业请求的资源 (requested)
- **物理负载** = 作业实际使用的资源 (physical)

### 2. 浮动比例 (Floating Ratio)

配置文件中：
- `physical.resource.floating.ratio.cpu = 1.1` (允许 CPU 超分 10%)
- `physical.resource.floating.ratio.memory = 1.1` (允许内存超分 10%)

### 3. 资源计算公式

```
逻辑资源 = 请求资源 × 浮动比例
实际物理资源 = 作业真实使用量
```

---

## 认证

接口需要通过 `mybkcosmos.mybank.cn` 的认证，使用 Cookie 认证。

Cookie 文件位置：`web/cookie.txt`