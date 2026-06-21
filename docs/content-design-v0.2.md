# 🎮 K8s Quest 内容设计文档 v0.2

> 🍒 12 关课程设计——从 K8s 小白到能独立排错  
> 目标：30-45 分钟通关，覆盖 K8s 80% 日常操作

---

## 📚 课程总览

| 章节 | 关卡数 | 时长 | 学习目标 |
|------|--------|------|----------|
| 🌱 Chapter 1: Pod 基础 | 4 关 | 10 min | 创建、查看、调试、删除 Pod |
| 🚀 Chapter 2: Deployment | 4 关 | 15 min | 副本管理、滚动更新、回滚、扩缩容 |
| 🔗 Chapter 3: Service 网络 | 4 关 | 15 min | ClusterIP、NodePort、负载均衡、外部访问 |

---

## 🌱 Chapter 1: Pod 基础（4 关）

### Q1.1 ✅ 创建第一个 Pod（已实现）

**学习目标**：理解 Pod 是什么，掌握最小 YAML 结构  
**通过条件**：创建 `nginx-pod`，镜像 `nginx:1.25`  
**教学点**：apiVersion / kind / metadata / spec / containers

---

### Q1.2 🏷️ 带标签的 Pod

**学习目标**：理解 labels 的作用（后续 Service 会用）  
**通过条件**：
- Pod 名字 `redis-pod`
- 镜像 `redis:7-alpine`
- labels: `app=cache, tier=backend`

**教学点**：labels 是 K8s 的"分类标签"，Service/Deployment 都靠它选 Pod

**starter_yaml**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: redis-pod
  # 在这里加 labels
spec:
  containers:
    - name: redis
      image: redis:7-alpine
```

---

### Q1.3 🔍 查看 Pod 状态（多容器 Pod）

**学习目标**：理解 Pod 可以包含多个容器（sidecar 模式）  
**通过条件**：
- Pod 名字 `web-with-logger`
- 主容器：`nginx:1.25`，名字 `web`
- sidecar 容器：`busybox:1.36`，名字 `logger`
- 两个容器都启动

**教学点**：Pod 是"原子调度单位"，多容器共享网络/存储

---

### Q1.4 🧹 删除 Pod（资源清理）

**学习目标**：学会删除资源，理解 YAML 如何精确控制  
**通过条件**：
- 创建 Pod `temp-pod`（image: `alpine:3.18`）
- 然后从集群中"删除"它（提示：本关用特殊机制）

**特殊机制**：本关 checker 检查"集群中没有 temp-pod"——玩家需要先创建，验证 simulator 支持删除操作（这部分要给 simulator 加功能）

**教学点**：K8s 是声明式的，删除也是"声明"

---

## 🚀 Chapter 2: Deployment（4 关）

### Q2.1 🚀 创建第一个 Deployment

**学习目标**：理解 Deployment vs Pod 的区别  
**通过条件**：
- Deployment 名字 `nginx-deploy`
- 3 个副本
- 镜像 `nginx:1.25`

**教学点**：Deployment 管 Pod 的"期望状态"，自动维持副本数

---

### Q2.2 📈 扩缩容

**学习目标**：理解 `replicas` 字段  
**通过条件**：
- Deployment 名字 `api-deploy`
- 5 个副本
- 镜像 `python:3.11-slim`

**教学点**：水平扩展 = 改 replicas 字段

---

### Q2.3 🔄 滚动更新

**学习目标**：理解 image 升级如何安全进行  
**通过条件**：
- 已有 Deployment `web-deploy`（v1，3 副本，image: `nginx:1.24`）
- 玩家提交新 YAML，把 image 改成 `nginx:1.25`
- 检查所有 Pod 都升级到新版本

**教学点**：声明式升级，K8s 自动滚动

---

### Q2.4 🔙 回滚

**学习目标**：理解版本历史 + rollback  
**通过条件**：
- 模拟一次失败升级（image 写错）
- 玩家通过 rollback 回到上一版本
- （需要给 simulator 加 rollout history）

**教学点**：Deployment 自带"撤销"

---

## 🔗 Chapter 3: Service（4 关）

### Q3.1 🌐 ClusterIP 服务发现

**学习目标**：理解 Service 怎么暴露 Pod  
**通过条件**：
- 创建 Service `backend-svc`
- selector: `app=backend`
- port: 80 → targetPort: 8080
- type: ClusterIP
- 集群里已有带 `app=backend` 标签的 Pod（前置状态）

**教学点**：Service 通过 selector + label 选 Pod，提供稳定 IP

---

### Q3.2 🚪 NodePort 对外暴露

**学习目标**：理解如何让外部访问  
**通过条件**：
- Service `frontend-svc`
- selector: `app=frontend`
- type: NodePort
- nodePort: 30080

**教学点**：NodePort 在所有节点开一个端口

---

### Q3.3 ⚖️ Service 负载均衡

**学习目标**：理解 Service 自动分发流量  
**通过条件**：
- 创建 3 个带 `app=api` 标签的 Pod
- 创建 Service `api-svc`（selector: `app=api`）
- 模拟请求分发，检查流量到多个 Pod

**教学点**：Service 默认轮询，kube-proxy 做 DNAT

---

### Q3.4 🔗 完整 3 层架构（实战）

**学习目标**：把 Pod + Deployment + Service 串起来  
**通过条件**：
- Deployment `web-deploy`（3 副本，nginx，labels: `app=web`）
- Service `web-svc`（ClusterIP，selector: `app=web`）
- 整套架构正确建立

**教学点**：典型 K8s 应用 = Deployment + Service

---

## 🎯 设计原则

1. **由浅入深**：每关只引入 1 个新概念
2. **真实场景**：用真 K8s YAML，不简化语法
3. **即时反馈**：错误时给具体提示（指向哪个字段错了）
4. **教学优先**：每关结尾给"樱桃的学习笔记"（深度洞察）
5. **可重试**：失败不扣分，鼓励试错

---

## 🛠️ Simulator 需要的扩展

| 功能 | 当前 | 需要 | 用于 |
|------|------|------|------|
| Pod CRUD | ✅ 创建 | 加 删除 | Q1.4 |
| Deployment | ✅ 副本 | 加 rollout history | Q2.4 |
| Service | ✅ 创建 | 加 selector 匹配 + 流量模拟 | Q3.1-Q3.4 |
| 前置状态 | ❌ | 加 "preset" 机制 | Q2.3, Q3.1, Q3.3 |

**preset 机制**：关卡可以定义"集群已有的初始状态"，玩家在此基础上答题。

---

## 📊 通关奖励

- 每关 +10 经验
- 章节通关：徽章（🌱 Pod 新手 / 🚀 Deployment 大师 / 🔗 Service 老司机）
- 全部通关：可分享的证书（"我已掌握 K8s 基础"）

---

*由 🍒 樱桃 PM 设计 | v0.2*
