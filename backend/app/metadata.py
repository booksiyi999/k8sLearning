"""K8s Quest 元数据：知识点映射、章节信息、XP 配置。

用于前端游戏化系统和结业报告生成。
"""

# ==================== 章节元数据 ====================

CHAPTERS_META = {
    "ch01": {
        "title": "Pod 基础",
        "icon": "🌱",
        "color": "#4caf50",
        "description": "K8s 最小调度单元，从这里开始你的旅程",
        "difficulty": 1,
    },
    "ch02": {
        "title": "Deployment",
        "icon": "🚀",
        "color": "#2196f3",
        "description": "管理 Pod 的期望状态，实现弹性伸缩与滚动更新",
        "difficulty": 2,
    },
    "ch03": {
        "title": "Service 网络",
        "icon": "🔗",
        "color": "#ff9800",
        "description": "服务发现与负载均衡，让 Pod 之间能互相通信",
        "difficulty": 2,
    },
    "ch04": {
        "title": "配置管理",
        "icon": "⚙️",
        "color": "#9c27b0",
        "description": "ConfigMap 与 Secret，将配置与镜像解耦",
        "difficulty": 3,
    },
    "ch05": {
        "title": "存储",
        "icon": "💾",
        "color": "#00bcd4",
        "description": "PV/PVC 体系，让数据比 Pod 活得更久",
        "difficulty": 3,
    },
    "ch06": {
        "title": "调度",
        "icon": "🎯",
        "color": "#f44336",
        "description": "控制 Pod 跑在哪个节点上，高级调度策略",
        "difficulty": 4,
    },
    "ch07": {
        "title": "Job/CronJob",
        "icon": "📋",
        "color": "#795548",
        "description": "批量任务与定时任务，运行完成即退出",
        "difficulty": 3,
    },
    "ch08": {
        "title": "StatefulSet",
        "icon": "🗄️",
        "color": "#607d8b",
        "description": "有状态应用管理，稳定 Pod 身份与持久化",
        "difficulty": 4,
    },
    "ch09": {
        "title": "RBAC",
        "icon": "🔐",
        "color": "#ff5722",
        "description": "基于角色的访问控制，权限管理",
        "difficulty": 4,
    },
    "ch10": {
        "title": "HPA",
        "icon": "📈",
        "color": "#4caf50",
        "description": "水平 Pod 自动伸缩，根据负载动态扩缩容",
        "difficulty": 3,
    },
    "ch11": {
        "title": "Ingress",
        "icon": "🌐",
        "color": "#2196f3",
        "description": "七层负载均衡，域名与路径路由",
        "difficulty": 3,
    },
    "ch12": {
        "title": "NetworkPolicy",
        "icon": "🛡️",
        "color": "#9c27b0",
        "description": "网络策略，Pod 间流量控制与安全隔离",
        "difficulty": 5,
    },
}

# ==================== 知识点映射 ====================
# 每个关卡关联的 K8s 知识点，用于结业报告的知识掌握度分析

KNOWLEDGE_POINTS = {
    "Q1.1": ["Pod 概念", "YAML 结构 (apiVersion/kind/metadata/spec)", "containers 定义"],
    "Q1.2": ["Labels 标签", "标签选择器", "key-value 键值对"],
    "Q1.3": ["多容器 Pod", "Sidecar 模式", "Pod 内容器共享网络/存储"],
    "Q1.4": ["资源管理", "resources.requests", "resources.limits"],
    "Q2.1": ["Deployment 概念", "ReplicaSet", "spec.template 模板"],
    "Q2.2": ["水平扩展", "replicas 字段", "弹性伸缩"],
    "Q2.3": ["滚动更新", "maxSurge/maxUnavailable", "镜像升级策略"],
    "Q2.4": ["版本回滚", "rollout history", "revision 回滚"],
    "Q3.1": ["ClusterIP", "服务发现", "selector + label 匹配"],
    "Q3.2": ["NodePort", "对外暴露服务", "nodePort 端口范围"],
    "Q3.3": ["DNS 解析", "CoreDNS", "服务名到 IP 映射"],
    "Q3.4": ["Headless Service", "StatefulSet 场景", "Pod 直连"],
    "Q4.1": ["ConfigMap", "配置分离", "data 字段"],
    "Q4.2": ["环境变量注入", "envFrom", "configMapKeyRef"],
    "Q4.3": ["Volume 挂载配置", "configMap volume", "配置文件注入"],
    "Q4.4": ["Secret", "敏感信息管理", "base64 编码"],
    "Q5.1": ["PersistentVolume", "集群级存储资源", "容量与访问模式"],
    "Q5.2": ["PersistentVolumeClaim", "存储申请", "PVC 绑定 PV"],
    "Q5.3": ["Pod 使用 PVC", "volumeMounts", "持久化存储挂载"],
    "Q5.4": ["emptyDir", "临时存储", "Pod 生命周期绑定"],
    "Q6.1": ["nodeSelector", "节点选择", "标签调度"],
    "Q6.2": ["nodeAffinity", "亲和性调度", "required/preferred"],
    "Q6.3": ["Taints & Tolerations", "污点与容忍", "驱逐策略"],
    "Q6.4": ["资源限制调度", "调度器决策", "资源碎片化"],
    # ---- 集群实战关卡 ----
    "Q1.5": ["Pod 真实部署", "kubectl 实操", "Pod 生命周期与调试"],
    "Q2.5": ["Deployment 扩缩容", "kubectl scale", "控制器协调循环"],
    "Q3.5": ["Service 间通信", "Endpoints", "集群内 DNS 访问"],
    "Q4.5": ["ConfigMap 环境变量注入", "envFrom", "配置分离实践"],
    "Q5.5": ["PVC 持久化存储", "volumeMounts", "存储持久化验证"],
    "Q6.5": ["nodeSelector 真实调度", "节点标签管理", "kubectl label"],
    # Ch7: Job/CronJob
    "Q7.1": ["Job 概念", "spec.template", "一次性任务"],
    "Q7.2": ["parallelism", "并行执行", "completions"],
    "Q7.3": ["CronJob", "schedule", "定时任务"],
    "Q7.4": ["concurrencyPolicy", "Forbid/Allow/Replace", "任务并发控制"],
    "Q7.5": ["Job 真实部署", "kubectl 计算任务", "任务状态查看"],
    # Ch8: StatefulSet
    "Q8.1": ["StatefulSet 概念", "有序 Pod", "spec.serviceName"],
    "Q8.2": ["StatefulSet 扩缩容", "有序扩容", "replicas"],
    "Q8.3": ["Headless Service", "StatefulSet DNS", "Pod 身份"],
    "Q8.4": ["volumeClaimTemplates", "持久化模板", "PVC 自动创建"],
    "Q8.5": ["StatefulSet 真实部署", "MySQL 有状态应用", "数据持久化"],
    # Ch9: RBAC
    "Q9.1": ["Role", "rules", "命名空间级权限"],
    "Q9.2": ["RoleBinding", "roleRef", "subjects"],
    "Q9.3": ["ClusterRole", "集群级权限", "rules"],
    "Q9.4": ["ClusterRoleBinding", "roleRef", "集群级绑定"],
    "Q9.5": ["RBAC 实战", "ServiceAccount", "权限组合"],
    # Ch10: HPA
    "Q10.1": ["HorizontalPodAutoscaler", "CPU 阈值", "maxReplicas"],
    "Q10.2": ["HPA 扩缩容", "minReplicas", "maxReplicas"],
    "Q10.3": ["HPA 多指标", "metrics", "Memory/Custom"],
    "Q10.4": ["HPA behavior", "scaleDown", "stabilizationWindowSeconds"],
    "Q10.5": ["HPA 实战", "Deployment 自动伸缩", "metrics-server"],
    # Ch11: Ingress
    "Q11.1": ["Ingress 概念", "rules", "host/backend"],
    "Q11.2": ["Ingress 多域名", "多 host 路由", "虚拟主机"],
    "Q11.3": ["Ingress 路径路由", "paths", "URL 路由"],
    "Q11.4": ["Ingress TLS", "tls", "secretName", "HTTPS"],
    "Q11.5": ["Ingress 实战", "Nginx Ingress Controller", "端到端路由"],
    # Ch12: NetworkPolicy
    "Q12.1": ["NetworkPolicy", "默认拒绝", "policyTypes"],
    "Q12.2": ["namespaceSelector", "跨命名空间", "入站控制"],
    "Q12.3": ["podSelector", "Pod 白名单", "入站控制"],
    "Q12.4": ["ingress/egress", "双向控制", "出入站规则"],
    "Q12.5": ["NetworkPolicy 实战", "数据库隔离", "最小权限原则"],
}

# ==================== XP 配置 ====================

LEVEL_XP = {f"Q{i}.{j}": 10 for i in range(1, 13) for j in range(1, 6)}

# 章节通关奖励
CHAPTER_BONUS_XP = {f"ch{i:02d}": 50 for i in range(1, 13)}

# 等级称号 (总XP -> 称号)
RANKS = [
    (0, "🎓 K8s 萌新"),
    (40, "🌱 Pod 学徒"),
    (100, "🚀 Deployment 行者"),
    (180, "🔗 Service 武者"),
    (260, "⚙️ 配置大师"),
    (340, "💾 存储宗师"),
    (420, "🎯 调度贤者"),
    (500, "👑 K8s 传奇"),
]


def get_rank(total_xp: int) -> str:
    """根据总 XP 返回当前称号。"""
    rank = RANKS[0][1]
    for threshold, name in RANKS:
        if total_xp >= threshold:
            rank = name
    return rank


def get_next_rank(total_xp: int) -> tuple[str | None, int]:
    """返回下一个称号和所需 XP，已满级返回 (None, 0)。"""
    for threshold, name in RANKS:
        if total_xp < threshold:
            return name, threshold - total_xp
    return None, 0


# ==================== 知识域分组（结业报告用） ====================

KNOWLEDGE_DOMAINS = {
    "工作负载管理": ["Q1.1", "Q1.2", "Q1.3", "Q1.4", "Q1.5", "Q2.1", "Q2.2", "Q2.3", "Q2.4", "Q2.5"],
    "网络与服务": ["Q3.1", "Q3.2", "Q3.3", "Q3.4", "Q3.5"],
    "配置与密钥": ["Q4.1", "Q4.2", "Q4.3", "Q4.4", "Q4.5"],
    "存储管理": ["Q5.1", "Q5.2", "Q5.3", "Q5.4", "Q5.5"],
    "调度与资源": ["Q6.1", "Q6.2", "Q6.3", "Q6.4", "Q6.5"],
    "批量任务": ["Q7.1", "Q7.2", "Q7.3", "Q7.4", "Q7.5"],
    "有状态应用": ["Q8.1", "Q8.2", "Q8.3", "Q8.4", "Q8.5"],
    "权限管理": ["Q9.1", "Q9.2", "Q9.3", "Q9.4", "Q9.5"],
    "自动伸缩": ["Q10.1", "Q10.2", "Q10.3", "Q10.4", "Q10.5"],
    "入口路由": ["Q11.1", "Q11.2", "Q11.3", "Q11.4", "Q11.5"],
    "网络安全": ["Q12.1", "Q12.2", "Q12.3", "Q12.4", "Q12.5"],
}


def get_all_meta() -> dict:
    """返回完整元数据，供 /api/meta 端点使用。"""
    return {
        "chapters": CHAPTERS_META,
        "knowledge_points": KNOWLEDGE_POINTS,
        "level_xp": LEVEL_XP,
        "chapter_bonus_xp": CHAPTER_BONUS_XP,
        "ranks": RANKS,
        "knowledge_domains": KNOWLEDGE_DOMAINS,
    }
