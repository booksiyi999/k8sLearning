# 🐱 樱桃的 K8s 学习 App（k8s-quest）设计文档

> **作者**: 樱桃（Master: 李航宇的 AI 合伙人）  
> **日期**: 2026-06-20  
> **版本**: MVP v0.1（最小可行原型）

---

## 一、产品定位（Why）

**一句话**：通过模拟器闯关，让 K8s 初学者在浏览器里 30 分钟跑通"Pod → Deployment → Service"完整闭环，零环境配置。

### 为什么不是又一个 Killercoda？

| 维度 | Killercoda | **k8s-quest** |
|---|---|---|
| 后端 | 真实 K8s 集群（每用户独享，重） | **状态机模拟器**（轻） |
| 单用户成本 | $5-15/月 | **¥0**（纯静态 + 轻校验） |
| 启动时间 | 30-60 秒（集群拉起） | **<100ms**（纯计算） |
| 故障域 | 集群挂了全平台挂 | **零**（无外部依赖） |
| 目标人群 | 中高级（要会 ssh 进节点） | **初学者**（只需懂 yaml） |

**樱桃的判断**：Master 之前指出"30 天从小白到专家"是伪命题，所以 MVP 直接砍到"30 分钟跑通 Pod/Deployment/Service 三件套"——这是初学者最痛的痒点。

---

## 二、MVP 范围（What）

### ✅ MVP 必做（v0.1）

| 章节 | 关卡 | 学习目标 |
|---|---|---|
| **Chapter 1: Pod 基础** | Q1.1 创建第一个 Pod | 掌握 `kubectl apply -f` 心智模型 |
| | Q1.2 查看 Pod 状态 | 看懂 `kubectl get pods` 输出 |
| | Q1.3 调试 Pod 失败 | `kubectl describe` + Events |
| | Q1.4 删除 Pod | `kubectl delete` + Finalizer 概念 |
| | Q1.5 Pod 资源限制 | resources.limits/requests |
| **Chapter 2: Deployment** | Q2.1 创建 Deployment | ReplicaSet 心智模型 |
| | Q2.2 扩缩容 | `kubectl scale` |
| | Q2.3 滚动更新 | maxSurge/maxUnavailable |
| | Q2.4 回滚 | `kubectl rollout undo` |
| **Chapter 3: Service** | Q3.1 ClusterIP | 服务发现 |
| | Q3.2 NodePort | 对外暴露 |
| | Q3.3 负载均衡 | 多 Endpoint |

**合计 12 关**（精简到极致）

### ❌ MVP 不做（v0.2+）

- 真实集群（永远不做，是核心架构决策）
- 用户系统 / 多人（用 localStorage 存进度）
- 配置持久化（重启即重置）
- ConfigMap/Secret/Ingress（留给 v0.2）
- 答题计时 / 全球排行榜（YAGNI）

---

## 三、技术架构（How）

### 核心机制：YAML 模拟器

```
用户输入 YAML
     ↓
[Parser] 解析为 Python dict
     ↓
[Validator] 跟关卡期望规则比对
     ↓
[Simulator] 应用到虚拟集群状态
     ↓
[Renderer] 输出新的集群状态 + 解释
```

### 目录结构（MVP）

```
k8s-quest/
├── README.md
├── docs/
│   └── design.md（本文件）
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py            # FastAPI 入口
│   │   ├── simulator.py       # 核心模拟器
│   │   ├── validator.py       # 关卡校验器
│   │   └── levels/            # 关卡数据（YAML）
│   │       ├── ch01-pod/
│   │       │   ├── 01-create-pod.yaml
│   │       │   └── ...
│   │       ├── ch02-deployment/
│   │       └── ch03-service/
│   └── tests/
│       ├── test_simulator.py
│       ├── test_validator.py
│       └── test_levels.py     # E2E：每关都要能通过
├── frontend/
│   ├── index.html             # 单页
│   ├── app.js                 # Alpine.js
│   └── styles.css
├── Dockerfile                 # 一键部署
└── docker-compose.yml
```

### 数据流

1. 用户打开 `index.html` → 加载 Chapter 1 第 1 关
2. 用户在 textarea 写 YAML → 点"运行" → POST `/api/check`
3. 后端：解析 YAML → 应用模拟器 → 校验规则 → 返回结果
4. 前端：显示 ✓/✗ + 集群状态 diff + 下一关按钮

---

## 四、Milestone 验收标准

### Milestone 1（v0.1 - 单关 demo）

**目标**：跑通 Chapter 1 Q1.1（创建第一个 Pod）

**验收**：
- [ ] 前端能渲染单个关卡
- [ ] 用户输入有效 YAML → 后端解析成功
- [ ] 校验规则：必须包含 `apiVersion: v1`, `kind: Pod`, `metadata.name`, `spec.containers[0].image`
- [ ] 通过后显示 ✓ + 解锁下一关（v0.1 可省略解锁逻辑）
- [ ] 失败显示具体错误（如"缺少 spec.containers"）

### Milestone 2（v0.2 - 全部 12 关）

**目标**：完整跑通 Pod/Deployment/Service 三章

### Milestone 3（v0.3 - 部署上线）

**目标**：Docker 化 + 部署到 Master 的 VPS

---

## 五、不做哪些（YAGNI 红线）

> 这部分用来在开发过程中，樱桃自我提醒"不要扩 scope"

- ❌ 不做用户系统（首版任何人都能玩，进度存 localStorage）
- ❌ 不做集群可视化（YAML in / YAML out 就够）
- ❌ 不做 AI 答题助手（YAGNI，下一版可以加）
- ❌ 不做真实 kubectl 命令解析（只校验 YAML 内容）
- ❌ 不做多语言（先简体中文）
- ❌ 不做主题切换
- ❌ 不做 PWA / 离线

---

## 六、商业验证（樱桃的诚实提醒）

> 这一节写给未来的樱桃和 Master——**做这个 MVP 之前必须知道的事**

**MVP 验证的是技术体验，不是商业模型**。即便 k8s-quest 跑通了，距离赚钱还有：
1. 流量入口（樱桃推荐：先接 Master 现有的"云原生日报"做引流）
2. 内容深度（12 关 → 30 关 → 100 关，需要持续投入）
3. 付费触点（前 5 关免费 + 后续解锁 / CKA 模拟器付费版）

**这个 MVP 的真正价值**：让 Master 用最小成本验证"模拟器闯关"这个机制是否成立。如果用户玩了 12 关还想继续 → 加内容；如果用户玩 3 关就流失 → 改方向。

**不要把"做出 MVP"等同于"创业成功"**。
