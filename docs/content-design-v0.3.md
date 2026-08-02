# 🎮 K8s Quest 内容设计文档 v0.3

> 🍒 24 关课程设计 — 从 K8s 小白到能独立排错  
> 目标：30-60 分钟通关，覆盖 K8s 60% 核心操作（CKA 考点）

---

## 📚 课程总览

| 章节 | 图标 | 关卡数 | 时长 | 学习目标 | 难度 |
|------|------|--------|------|----------|------|
| 🌱 Ch1: Pod 基础 | 绿 | 4 关 | 10 min | 创建/标签/多容器/资源限制 | ★☆☆ |
| 🚀 Ch2: Deployment | 蓝 | 4 关 | 15 min | 副本/扩缩容/滚动更新/回滚 | ★★☆ |
| 🔗 Ch3: Service 网络 | 橙 | 4 关 | 15 min | ClusterIP/NodePort/DNS/Headless | ★★☆ |
| ⚙️ Ch4: 配置管理 | 紫 | 4 关 | 15 min | ConfigMap/环境变量/Volume/Secret | ★★★ |
| 💾 Ch5: 存储 | 青 | 4 关 | 15 min | PV/PVC/Pod挂载/emptyDir | ★★★ |
| 🎯 Ch6: 调度 | 红 | 4 关 | 15 min | nodeSelector/Affinity/Taints/资源 | ★★★★ |

**合计 24 关** | 预计通关时间 60-90 分钟 | 满分 XP: 540

---

## 🌱 Chapter 1: Pod 基础（4 关）

### Q1.1 创建第一个 Pod

**学习目标**：理解 Pod 是什么，掌握最小 YAML 结构  
**通过条件**：创建 `nginx-pod`，镜像 `nginx:1.25`  
**知识点**：Pod 概念、YAML 结构 (apiVersion/kind/metadata/spec)、containers 定义

### Q1.2 带标签的 Pod

**学习目标**：理解 labels 的作用（后续 Service 会用）  
**通过条件**：Pod `redis-pod`，镜像 `redis:7-alpine`，labels: `app=cache, tier=backend`  
**知识点**：Labels 标签、标签选择器、key-value 键值对

### Q1.3 多容器 Pod（sidecar）

**学习目标**：理解 Pod 可以包含多个容器（sidecar 模式）  
**通过条件**：Pod `web-with-logger`，主容器 nginx + sidecar busybox  
**知识点**：多容器 Pod、Sidecar 模式、Pod 内容器共享网络/存储

### Q1.4 带 resource requests/limits 的 Pod

**学习目标**：理解资源管理对调度的影响  
**通过条件**：Pod 带 resources.requests 和 resources.limits  
**知识点**：资源管理、resources.requests、resources.limits

---

## 🚀 Chapter 2: Deployment（4 关）

### Q2.1 创建第一个 Deployment

**学习目标**：理解 Deployment vs Pod 的区别  
**通过条件**：Deployment `nginx-deploy`，3 副本，nginx:1.25  
**知识点**：Deployment 概念、ReplicaSet、spec.template 模板

### Q2.2 扩缩容

**学习目标**：理解 `replicas` 字段  
**通过条件**：Deployment `api-deploy`，5 副本，python:3.11-slim  
**知识点**：水平扩展、replicas 字段、弹性伸缩

### Q2.3 滚动更新

**学习目标**：理解 image 升级如何安全进行  
**通过条件**：已有 Deployment 升级 image 版本  
**知识点**：滚动更新、maxSurge/maxUnavailable、镜像升级策略

### Q2.4 回滚

**学习目标**：理解版本历史 + rollback  
**通过条件**：通过 rollback 回到上一版本  
**知识点**：版本回滚、rollout history、revision 回滚

---

## 🔗 Chapter 3: Service 网络（4 关）

### Q3.1 创建 ClusterIP Service

**学习目标**：理解 Service 怎么暴露 Pod  
**通过条件**：Service `backend-svc`，selector + ClusterIP  
**知识点**：ClusterIP、服务发现、selector + label 匹配

### Q3.2 NodePort 对外暴露

**学习目标**：理解如何让外部访问  
**通过条件**：Service `frontend-svc`，NodePort 30080  
**知识点**：NodePort、对外暴露服务、nodePort 端口范围

### Q3.3 Service 发现 DNS

**学习目标**：理解 CoreDNS 如何解析服务名  
**通过条件**：通过服务名访问后端服务  
**知识点**：DNS 解析、CoreDNS、服务名到 IP 映射

### Q3.4 Headless Service

**学习目标**：理解 Headless Service 的特殊场景  
**通过条件**：创建 Headless Service (clusterIP: None)  
**知识点**：Headless Service、StatefulSet 场景、Pod 直连

---

## ⚙️ Chapter 4: 配置管理（4 关）

### Q4.1 创建 ConfigMap

**学习目标**：理解 ConfigMap 的作用  
**通过条件**：创建包含配置数据的 ConfigMap  
**知识点**：ConfigMap、配置分离、data 字段

### Q4.2 ConfigMap 环境变量注入

**学习目标**：理解如何将 ConfigMap 注入为环境变量  
**通过条件**：Pod 使用 envFrom 或 configMapKeyRef 引用 ConfigMap  
**知识点**：环境变量注入、envFrom、configMapKeyRef

### Q4.3 ConfigMap Volume 挂载

**学习目标**：理解如何将 ConfigMap 挂载为配置文件  
**通过条件**：Pod 通过 volume 挂载 ConfigMap  
**知识点**：Volume 挂载配置、configMap volume、配置文件注入

### Q4.4 创建 Secret 并使用

**学习目标**：理解 Secret 与 ConfigMap 的区别  
**通过条件**：创建 Secret 并在 Pod 中引用  
**知识点**：Secret、敏感信息管理、base64 编码

---

## 💾 Chapter 5: 存储（4 关）

### Q5.1 创建 PersistentVolume

**学习目标**：理解 PV 是集群级存储资源  
**通过条件**：创建 PV，指定容量和访问模式  
**知识点**：PersistentVolume、集群级存储资源、容量与访问模式

### Q5.2 创建 PersistentVolumeClaim

**学习目标**：理解 PVC 如何申请存储  
**通过条件**：创建 PVC 并绑定到 PV  
**知识点**：PersistentVolumeClaim、存储申请、PVC 绑定 PV

### Q5.3 Pod 使用 PVC

**学习目标**：理解 Pod 如何使用持久化存储  
**通过条件**：Pod 通过 volumeMounts 挂载 PVC  
**知识点**：Pod 使用 PVC、volumeMounts、持久化存储挂载

### Q5.4 emptyDir 临时存储

**学习目标**：理解 emptyDir 的临时性  
**通过条件**：Pod 使用 emptyDir 作为共享存储  
**知识点**：emptyDir、临时存储、Pod 生命周期绑定

---

## 🎯 Chapter 6: 调度（4 关）

### Q6.1 nodeSelector 节点选择

**学习目标**：理解最简单的调度约束  
**通过条件**：Pod 通过 nodeSelector 指定节点  
**知识点**：nodeSelector、节点选择、标签调度

### Q6.2 nodeAffinity 节点亲和性

**学习目标**：理解更灵活的调度约束  
**通过条件**：Pod 使用 nodeAffinity（required 或 preferred）  
**知识点**：nodeAffinity、亲和性调度、required/preferred

### Q6.3 Taints & Tolerations

**学习目标**：理解污点与容忍机制  
**通过条件**：Pod 通过 tolerations 容忍节点污点  
**知识点**：Taints & Tolerations、污点与容忍、驱逐策略

### Q6.4 资源限制与调度

**学习目标**：理解调度器如何根据资源调度  
**通过条件**：Pod 带资源限制，理解调度器决策  
**知识点**：资源限制调度、调度器决策、资源碎片化

---

## 🎯 设计原则

1. **由浅入深**：每关只引入 1 个新概念
2. **真实场景**：用真 K8s YAML，不简化语法
3. **即时反馈**：错误时给具体提示（指向哪个字段错了）
4. **教学优先**：每关结尾给"樱桃的学习笔记"（深度洞察）
5. **可重试**：失败不扣分，鼓励试错
6. **游戏化正反馈**：XP/连击/徽章让学员"上头"

---

## 📊 通关奖励

- 每关 +10 XP
- 章节通关：+50 XP + 徽章
- 全部通关：👑 K8s 传奇称号 + 可导出结业报告

---

## 🛠️ 模拟器支持的资源类型

| 资源 | 支持 | 模拟行为 |
|------|------|----------|
| Pod | ✅ 创建/删除 | 存入集群状态 |
| Deployment | ✅ 创建/更新 | 自动实例化 Pod |
| Service | ✅ 创建 | selector 匹配 Pod |
| ConfigMap | ✅ 创建 | 存入集群状态 |
| Secret | ✅ 创建 | 存入集群状态 |
| PersistentVolume | ✅ 创建 | 存入集群状态 |
| PersistentVolumeClaim | ✅ 创建 | 绑定 PV |
| 多文档 YAML | ✅ | yaml.safe_load_all() |

---

*由 🍒 樱桃 PM 设计 | v0.3 | 2026-08-03*
