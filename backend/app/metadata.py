"""K8s Quest 元数据：知识点映射、章节信息、XP 配置。

用于前端游戏化系统和结业报告生成。
"""

# ==================== 章节元数据 ====================

CHAPTERS_META = {
    "ch00": {
        "title": "K8s 架构总览",
        "icon": "🏗️",
        "color": "#6366f1",
        "description": "零基础起步：控制面/数据面架构、声明式模型、kubectl 全链路",
        "difficulty": "入门",
    },
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
    "ch13": {
        "title": "DaemonSet",
        "icon": "🛡️",
        "color": "#009688",
        "description": "守护进程集，确保每个节点运行一个 Pod 副本",
        "difficulty": 3,
    },
    "ch14": {
        "title": "Namespace & Quota",
        "icon": "📦",
        "color": "#e91e63",
        "description": "命名空间与资源配额，多团队资源隔离",
        "difficulty": 4,
    },
    "ch15": {
        "title": "PodDisruptionBudget",
        "icon": "🛡️",
        "color": "#00bcd4",
        "description": "中断预算，保护应用在自愿中断时的高可用",
        "difficulty": 3,
    },
    "ch16": {
        "title": "PriorityClass",
        "icon": "⭐",
        "color": "#ff9800",
        "description": "优先级与抢占，确保关键工作负载优先调度",
        "difficulty": 4,
    },
    "ch17": {
        "title": "CRD & Operator",
        "icon": "🔧",
        "color": "#673ab7",
        "description": "自定义资源定义与 Operator 模式，扩展 K8s 能力",
        "difficulty": 5,
    },
    "ch18": {
        "title": "SA & 安全上下文",
        "icon": "🛡️",
        "color": "#3f51b5",
        "description": "ServiceAccount 身份与 Pod 安全标准",
        "difficulty": 4,
    },
    "ch19": {
        "title": "Helm 包管理",
        "icon": "📦",
        "color": "#0d47a1",
        "description": "Helm Chart 打包、模板渲染与依赖管理",
        "difficulty": 4,
    },
    "ch20": {
        "title": "存储进阶",
        "icon": "💽",
        "color": "#00695c",
        "description": "StorageClass、CSI 驱动与 VolumeSnapshot",
        "difficulty": 5,
    },
    "ch21": {
        "title": "集群维护",
        "icon": "🔧",
        "color": "#455a64",
        "description": "etcd 备份恢复、集群升级与节点维护",
        "difficulty": 4,
    },
    "ch22": {
        "title": "故障排查",
        "icon": "🔍",
        "color": "#bf360c",
        "description": "Pod/Service/Node/控制平面故障诊断与修复",
        "difficulty": 5,
    },
    "ch23": {
        "title": "监控与日志",
        "icon": "📊",
        "color": "#e91e63",
        "description": "Prometheus、Grafana、Fluent Bit，构建可观测性体系",
        "difficulty": 4,
    },
    "ch24": {
        "title": "安全策略进阶",
        "icon": "🔒",
        "color": "#b71c1c",
        "description": "Admission Webhook、OPA Gatekeeper、审计日志",
        "difficulty": 5,
    },
    "ch25": {
        "title": "多容器模式",
        "icon": "📦",
        "color": "#00acc1",
        "description": "Init/Sidecar/Ambassador/Adapter，多容器设计模式",
        "difficulty": 4,
    },
    "ch26": {
        "title": "高级调度",
        "icon": "🎯",
        "color": "#ab47bc",
        "description": "Topology Spread、Descheduler、调度器配置",
        "difficulty": 5,
    },
    "ch27": {
        "title": "Service Mesh",
        "icon": "🌐",
        "color": "#5c6bc0",
        "description": "Istio 架构、VirtualService、DestinationRule、Gateway",
        "difficulty": 5,
    },
    "ch28": {
        "title": "CKA 模拟考试",
        "icon": "🎓",
        "color": "#d84315",
        "description": "综合考核：部署、网络、存储、故障排查、RBAC",
        "difficulty": 5,
    },
}

# ==================== 知识点映射 ====================
# 每个关卡关联的 K8s 知识点，用于结业报告的知识掌握度分析

KNOWLEDGE_POINTS = {
    "Q0.1": ["K8s 架构总览", "控制面组件", "数据面组件", "Node 角色", "多文档 YAML"],
    "Q0.2": ["声明式模型", "期望状态", "kubectl apply vs create", "Deployment 自愈"],
    "Q0.3": ["kubectl 全链路", "API Server 认证/授权/准入", "etcd 持久化", "Service selector 匹配"],
    "Q1.1": ["Pod 概念", "YAML 结构 (apiVersion/kind/metadata/spec)", "containers 定义"],
    "Q1.2": ["Labels 标签", "标签选择器", "key-value 键值对"],
    "Q1.3": ["多容器 Pod", "Sidecar 模式", "Pod 内容器共享网络/存储"],
    "Q1.4": ["资源管理", "resources.requests", "resources.limits"],
    "Q1.6": ["livenessProbe", "存活探针", "httpGet/tcpSocket/exec", "initialDelaySeconds/periodSeconds/failureThreshold"],
    "Q1.7": ["readinessProbe", "就绪探针", "liveness+readiness 双探针", "Pod Ready 状态"],
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
    # Ch13: DaemonSet
    "Q13.1": ["DaemonSet 概念", "每节点一个 Pod", "spec.template"],
    "Q13.2": ["nodeSelector", "节点选择", "标签过滤"],
    "Q13.3": ["RollingUpdate", "滚动更新", "maxUnavailable"],
    "Q13.4": ["DaemonSet vs Deployment", "工作负载选择", "节点级服务"],
    "Q13.5": ["DaemonSet 实战", "Fluent Bit 日志采集", "hostPath 挂载"],
    # Ch14: Namespace & ResourceQuota
    "Q14.1": ["Namespace 概念", "资源隔离", "逻辑分区"],
    "Q14.2": ["Namespace 作用域", "metadata.namespace", "多文档 YAML"],
    "Q14.3": ["ResourceQuota", "资源配额", "spec.hard"],
    "Q14.4": ["LimitRange", "资源限制范围", "default/defaultRequest"],
    "Q14.5": ["多团队隔离实战", "Namespace+Quota+LimitRange", "资源隔离方案"],
    # Ch15: PodDisruptionBudget
    "Q15.1": ["PodDisruptionBudget", "minAvailable", "自愿中断保护"],
    "Q15.2": ["minAvailable 百分比", "动态保护策略", "HPA 配合"],
    "Q15.3": ["maxUnavailable", "中断预算策略", "minAvailable vs maxUnavailable"],
    "Q15.4": ["PDB selector", "自愿中断 vs 非自愿中断", "驱逐保护"],
    "Q15.5": ["Deployment+PDB 实战", "生产保护方案", "多文档 YAML"],
    # Ch16: PriorityClass
    "Q16.1": ["PriorityClass", "value", "优先级基础"],
    "Q16.2": ["抢占机制", "preemptionPolicy", "PreemptLowerPriority"],
    "Q16.3": ["globalDefault", "默认优先级", "全局配置"],
    "Q16.4": ["优先级分层设计", "系统级 vs 用户级", "多 PriorityClass"],
    "Q16.5": ["多优先级工作负载", "priorityClassName", "Pod 优先级调度"],
    # Ch17: CRD & Operator
    "Q17.1": ["CRD 概念", "metadata.name 格式校验", "spec.group", "spec.names", "spec.versions"],
    "Q17.2": ["CRD Schema 验证", "openAPIV3Schema", "properties", "类型校验"],
    "Q17.3": ["Operator RBAC", "Role.rules", "RoleBinding.subjects", "ServiceAccount"],
    "Q17.4": ["Status 子资源", "subresources.status", "WATCH_NAMESPACE", "spec/status 隔离"],
    "Q17.5": ["Operator 实战", "CRD + SA + Deployment", "多文档 YAML", "完整部署栈"],
    "Q17.6": ["Reconcile 循环", "水平触发", "watch-compare-act", "requeue", "优雅退出"],
    "Q17.7": ["OwnerReference", "级联删除", "垃圾回收", "uid", "controller"],
    "Q17.8": ["Finalizer", "优雅删除", "deletionTimestamp", "清理机制"],
    "Q17.9": ["Conditions", "status.conditions", "type/status/lastTransitionTime", "状态管理"],
    "Q17.10": ["Operator 最佳实践", "幂等性", "requeue", "finalizer", "ownerReference"],
    # Ch18: ServiceAccount & 安全上下文
    "Q18.1": ["ServiceAccount", "身份认证", "metadata.name"],
    "Q18.2": ["Pod 绑定 SA", "serviceAccountName", "身份传递"],
    "Q18.3": ["SecurityContext", "runAsNonRoot", "readOnlyRootFilesystem"],
    "Q18.4": ["Pod Security Standards", "restricted", "baseline", "privileged"],
    "Q18.5": ["最小权限实战", "SA + 安全 Pod", "多文档 YAML"],
    # Ch19: Helm 包管理
    "Q19.1": ["Helm Chart 概念", "Chart.yaml 结构", "apiVersion/name/version"],
    "Q19.2": ["values.yaml", "配置参数化", ".Values 引用"],
    "Q19.3": ["Helm 模板", "Go template", ".Release/.Values/.Chart"],
    "Q19.4": ["Helm 依赖", "dependencies", "子 chart 管理"],
    "Q19.5": ["Helm 实战", "helm install/upgrade", "Release 管理"],
    # Ch20: 存储进阶
    "Q20.1": ["StorageClass", "动态 Provisioning", "provisioner"],
    "Q20.2": ["CSI 驱动", "volumeBindingMode", "WaitForFirstConsumer"],
    "Q20.3": ["VolumeSnapshot", "卷快照", "PVC 快照"],
    "Q20.4": ["VolumeSnapshotContent", "快照内容管理", "snapshotHandle"],
    "Q20.5": ["动态存储全流程", "SC+PVC+Pod+Snapshot", "多文档 YAML"],
    # Ch21: 集群维护
    "Q21.1": ["etcd 备份", "etcdctl snapshot save", "TLS 证书"],
    "Q21.2": ["etcd 恢复", "etcdctl snapshot restore", "--data-dir"],
    "Q21.3": ["集群升级", "kubeadm upgrade plan/apply", "版本兼容性"],
    "Q21.4": ["节点维护", "kubectl drain/uncordon", "--ignore-daemonsets"],
    "Q21.5": ["完整节点维护", "drain+维护+uncordon", "生产环境流程"],
    # Ch22: 故障排查
    "Q22.1": ["CrashLoopBackOff", "kubectl logs --previous", "容器命令修复"],
    "Q22.2": ["Service 连通性", "selector/labels 匹配", "Endpoints 排查"],
    "Q22.3": ["Node NotReady", "kubectl describe node", "Conditions/Events"],
    "Q22.4": ["控制平面故障", "kube-system Pod", "componentstatuses"],
    "Q22.5": ["完整故障排查", "多问题修复", "系统性排查"],
    # Ch23: 监控与日志
    "Q23.1": ["ServiceMonitor", "Prometheus Operator", "selector/matchLabels", "endpoints"],
    "Q23.2": ["Grafana Dashboard", "ConfigMap", "grafana_dashboard 标签", "Sidecar 自动发现"],
    "Q23.3": ["Fluent Bit", "DaemonSet", "hostPath 挂载", "日志采集"],
    "Q23.4": ["PrometheusRule", "告警规则", "PromQL", "groups/rules"],
    "Q23.5": ["可观测性栈", "ServiceMonitor+ConfigMap+DaemonSet", "多文档 YAML"],
    # Ch24: 安全策略进阶
    "Q24.1": ["ValidatingAdmissionWebhook", "准入控制", "clientConfig", "rules"],
    "Q24.2": ["MutatingAdmissionWebhook", "变更准入", "JSON Patch", "reinvocationPolicy"],
    "Q24.3": ["OPA Gatekeeper", "Constraint", "策略即代码", "Rego"],
    "Q24.4": ["Audit Policy", "审计日志", "level", "rules"],
    "Q24.5": ["多层安全防护", "Webhook+OPA+NetworkPolicy", "纵深防御", "多文档 YAML"],
    # Ch25: 多容器模式
    "Q25.1": ["Init Container", "initContainers", "初始化容器", "emptyDir 共享"],
    "Q25.2": ["Sidecar 模式", "多容器 Pod", "共享卷", "边车容器"],
    "Q25.3": ["Ambassador 模式", "代理容器", "localhost 通信", "Envoy 代理"],
    "Q25.4": ["Adapter 模式", "适配器容器", "格式转换", "日志标准化"],
    "Q25.5": ["多容器综合实战", "Init+Sidecar+Service", "生产级多容器应用"],
    # Ch26: 高级调度
    "Q26.1": ["TopologySpreadConstraints", "maxSkew", "拓扑分布约束", "whenUnsatisfiable"],
    "Q26.2": ["PodAntiAffinity", "requiredDuringScheduling", "preferredDuringScheduling", "跨节点反亲和"],
    "Q26.3": ["Descheduler", "RemoveDuplicates", "LowNodeUtilization", "重新调度策略"],
    "Q26.4": ["KubeSchedulerConfiguration", "调度框架", "插件配置", "profiles"],
    "Q26.5": ["高可用调度", "Topology Spread+PDB", "多副本+跨节点分布"],
    # Ch27: Service Mesh
    "Q27.1": ["Istio 架构", "控制面/数据面", "istiod", "Envoy Sidecar"],
    "Q27.2": ["VirtualService", "流量路由", "HTTP 路由规则", "subset"],
    "Q27.3": ["DestinationRule", "版本子集", "trafficPolicy", "负载均衡策略"],
    "Q27.4": ["Istio Gateway", "入口网关", "servers", "selector"],
    "Q27.5": ["Service Mesh 综合", "Gateway+VS+DR", "完整流量管理配置"],
    # Ch28: CKA 模拟考试
    "Q28.1": ["CKA 综合", "Deployment+Service", "资源限制", "readinessProbe"],
    "Q28.2": ["CKA 网络", "Service+NetworkPolicy+Ingress", "网络隔离", "七层路由"],
    "Q28.3": ["CKA 存储", "PVC+ConfigMap+Secret", "存储与配置综合"],
    "Q28.4": ["CKA 故障排查", "selector/labels 匹配", "CrashLoopBackOff 修复"],
    "Q28.5": ["CKA RBAC", "ServiceAccount+Role+RoleBinding", "securityContext", "最小权限"],
}

# ==================== XP 配置 ====================

LEVEL_XP = {f"Q{i}.{j}": 10 for i in range(2, 29) for j in range(1, 6)}
LEVEL_XP.update({"Q0.1": 10, "Q0.2": 10, "Q0.3": 10})
LEVEL_XP.update({f"Q1.{j}": 10 for j in range(1, 8)})
# Ch17 扩展为 10 关
LEVEL_XP.update({f"Q17.{j}": 10 for j in range(6, 11)})

# 章节通关奖励
CHAPTER_BONUS_XP = {f"ch{i:02d}": 50 for i in range(0, 29)}

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
    "架构基础": ["Q0.1", "Q0.2", "Q0.3"],
    "工作负载管理": ["Q1.1", "Q1.2", "Q1.3", "Q1.4", "Q1.5", "Q1.6", "Q1.7", "Q2.1", "Q2.2", "Q2.3", "Q2.4", "Q2.5"],
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
    "守护进程": ["Q13.1", "Q13.2", "Q13.3", "Q13.4", "Q13.5"],
    "资源管理": ["Q14.1", "Q14.2", "Q14.3", "Q14.4", "Q14.5"],
    "中断保护": ["Q15.1", "Q15.2", "Q15.3", "Q15.4", "Q15.5"],
    "优先级调度": ["Q16.1", "Q16.2", "Q16.3", "Q16.4", "Q16.5"],
    "自定义资源": ["Q17.1", "Q17.2", "Q17.3", "Q17.4", "Q17.5", "Q17.6", "Q17.7", "Q17.8", "Q17.9", "Q17.10"],
    "安全与身份": ["Q18.1", "Q18.2", "Q18.3", "Q18.4", "Q18.5"],
    "包管理": ["Q19.1", "Q19.2", "Q19.3", "Q19.4", "Q19.5"],
    "存储进阶": ["Q20.1", "Q20.2", "Q20.3", "Q20.4", "Q20.5"],
    "集群维护": ["Q21.1", "Q21.2", "Q21.3", "Q21.4", "Q21.5"],
    "故障排查": ["Q22.1", "Q22.2", "Q22.3", "Q22.4", "Q22.5"],
    "监控与日志": ["Q23.1", "Q23.2", "Q23.3", "Q23.4", "Q23.5"],
    "安全策略进阶": ["Q24.1", "Q24.2", "Q24.3", "Q24.4", "Q24.5"],
    "多容器模式": ["Q25.1", "Q25.2", "Q25.3", "Q25.4", "Q25.5"],
    "高级调度": ["Q26.1", "Q26.2", "Q26.3", "Q26.4", "Q26.5"],
    "Service Mesh": ["Q27.1", "Q27.2", "Q27.3", "Q27.4", "Q27.5"],
    "CKA 综合考核": ["Q28.1", "Q28.2", "Q28.3", "Q28.4", "Q28.5"],
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
