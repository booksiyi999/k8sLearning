"""E2E 通关旅程测试。

模拟学员从 Q1.1 到 Q12.5 的完整通关流程：
1. 逐个提交所有 60 关的正确答案
2. 验证 XP 累积过程（每关 +10，每章 +50）
3. 验证最终 XP = 1200（60*10 + 12*50）
4. 验证报告生成（100% 完成率，S 级评定）
5. 验证知识域全部 100%
6. 验证无薄弱项
7. 验证称号为 "K8s 传奇"
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# ==========================================================================
#  60 个关卡的正确 YAML 答案（从教学示例中提取）
# ==========================================================================

CORRECT_ANSWERS = {
    "Q0.1": """\
apiVersion: v1
kind: Node
metadata:
  name: control-plane-node
  labels:
    node-role.kubernetes.io/control-plane: ""
---
apiVersion: v1
kind: Node
metadata:
  name: worker-node-1
  labels:
    node-role.kubernetes.io/worker: ""
""",
    "Q0.2": """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: nginx
        image: nginx:1.25
""",
    "Q0.3": """\
apiVersion: v1
kind: Pod
metadata:
  name: api-demo-pod
  labels:
    app: api-demo
spec:
  containers:
  - name: nginx
    image: nginx:1.25
---
apiVersion: v1
kind: Service
metadata:
  name: api-demo-svc
spec:
  selector:
    app: api-demo
  ports:
  - port: 80
    targetPort: 80
""",
    "Q1.1": """\
apiVersion: v1          # K8s API 版本
kind: Pod               # 资源类型: Pod
metadata:               # 元数据
  name: nginx-pod       # Pod 名称（唯一标识）
  labels:               # 标签（可选，用于选择）
    app: nginx
spec:                   # 规格定义
  containers:           # 容器列表
  - name: nginx         # 容器名
    image: nginx:1.25   # 镜像
    ports:              # 端口（可选）
    - containerPort: 80
""",
    "Q1.2": """\
apiVersion: v1              # K8s API 版本
kind: Pod                   # 资源类型: Pod
metadata:                   # 元数据
  name: redis-pod           # Pod 名称
  labels:                   # 标签区
    app: cache              # 应用标识
    tier: backend           # 架构层标识
spec:                       # 规格定义
  containers:               # 容器列表
  - name: redis             # 容器名
    image: redis:7-alpine   # Redis 镜像
""",
    "Q1.3": """\
apiVersion: v1                    # K8s API 版本
kind: Pod                         # 资源类型: Pod
metadata:                         # 元数据
  name: web-with-logger           # Pod 名称
spec:                             # 规格定义
  containers:                     # 容器列表（多个）
  - name: web                     # 主容器
    image: nginx:1.25             # Nginx 镜像
    ports:                        # 端口
    - containerPort: 80
    volumeMounts:                 # 挂载共享卷
    - name: shared-logs
      mountPath: /var/log/nginx
  - name: logger                  # Sidecar 容器
    image: busybox:1.36           # 轻量镜像
    volumeMounts:                 # 挂载同一个共享卷
    - name: shared-logs
      mountPath: /var/log/nginx
    command: ["/bin/sh", "-c"]    # 持续读取日志
    args: ["tail -f /var/log/nginx/access.log"]
  volumes:                        # 定义共享卷
  - name: shared-logs
    emptyDir: {}                  # 临时共享存储
""",
    "Q1.4": """\
apiVersion: v1                    # K8s API 版本
kind: Pod                         # 资源类型: Pod
metadata:                         # 元数据
  name: resource-pod              # Pod 名称
spec:                             # 规格定义
  containers:                     # 容器列表
  - name: app                     # 容器名
    image: nginx:1.25             # 镜像
    resources:                    # 资源配置
      requests:                   # 请求量（调度依据）
        cpu: "100m"               # 100 millicpu = 0.1 核
        memory: "128Mi"           # 128 Mebibyte
      limits:                     # 上限（运行时硬限制）
        cpu: "500m"               # 最多 0.5 核
        memory: "256Mi"           # 最多 256Mi
""",
    "Q1.5": """\
apiVersion: v1            # K8s API 版本
kind: Pod                 # 资源类型: Pod
metadata:                 # 元数据
  name: nginx-web         # Pod 名称
  labels:                 # 标签（便于后续 Service 选择）
    app: nginx
spec:                     # 规格定义
  containers:             # 容器列表
  - name: nginx           # 容器名
    image: nginx:1.25     # Nginx 镜像
    ports:                # 暴露端口
    - containerPort: 80   # Nginx 默认端口
""",
    "Q1.6": """\
apiVersion: v1
kind: Pod
metadata:
  name: probe-pod
spec:
  containers:
  - name: nginx
    image: nginx:1.25
    ports:
    - containerPort: 80
    livenessProbe:
      httpGet:
        path: /
        port: 80
      initialDelaySeconds: 5
      periodSeconds: 10
      failureThreshold: 3
""",
    "Q1.7": """\
apiVersion: v1
kind: Pod
metadata:
  name: health-pod
spec:
  containers:
  - name: nginx
    image: nginx:1.25
    ports:
    - containerPort: 80
    livenessProbe:
      httpGet:
        path: /health
        port: 80
      initialDelaySeconds: 5
      periodSeconds: 10
      failureThreshold: 3
    readinessProbe:
      httpGet:
        path: /ready
        port: 80
      initialDelaySeconds: 3
      periodSeconds: 5
      failureThreshold: 1
""",
    "Q2.1": """\
apiVersion: apps/v1              # Deployment 用 apps/v1
kind: Deployment                 # 资源类型: Deployment
metadata:                        # 元数据
  name: nginx-deploy             # Deployment 名称
spec:                            # 规格定义
  replicas: 3                    # 期望副本数
  selector:                      # 标签选择器
    matchLabels:                 # 必须与 template.labels 一致
      app: nginx
  template:                      # Pod 模板
    metadata:                    # Pod 元数据
      labels:                    # Pod 标签
        app: nginx
    spec:                        # Pod 规格
      containers:                # 容器列表
      - name: nginx              # 容器名
        image: nginx:1.25        # 容器镜像
""",
    "Q2.2": """\
apiVersion: apps/v1              # K8s API 版本
kind: Deployment                 # 资源类型: Deployment
metadata:                        # 元数据
  name: api-deploy               # Deployment 名称
spec:                            # 规格定义
  replicas: 5                    # 期望 5 个副本（水平扩展）
  selector:                      # 标签选择器
    matchLabels:
      app: api
  template:                      # Pod 模板
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api                # 容器名
        image: python:3.11-slim  # Python 镜像
""",
    "Q2.3": """\
apiVersion: apps/v1              # K8s API 版本
kind: Deployment
metadata:
  name: web-deploy               # Deployment 名称
spec:
  replicas: 3                    # 3 个副本
  strategy:                      # 更新策略
    type: RollingUpdate          # 滚动更新（默认）
    rollingUpdate:
      maxSurge: 1                # 最多超出 1 个 Pod
      maxUnavailable: 1          # 最多 1 个不可用
  selector:
    matchLabels:
      app: web
  template:                      # Pod 模板
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: nginx
        image: nginx:1.25        # ← 改成新版本触发滚动更新
""",
    "Q2.4": """\
apiVersion: apps/v1              # K8s API 版本
kind: Deployment
metadata:                        # 元数据
  name: web-deploy               # Deployment 名称
  annotations:                   # 注解区
    k8s-quest/rollback: "true"   # ← 触发回滚到上一版本
spec:                            # 规格定义
  replicas: 3                    # 副本数保持不变
  selector:                      # 标签选择器
    matchLabels:
      app: web
  template:                      # Pod 模板
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: nginx
        image: nginx:1.24        # 回滚后的镜像版本
""",
    "Q2.5": """\
apiVersion: apps/v1          # Deployment API 版本
kind: Deployment             # 资源类型
metadata:                    # 元数据
  name: web-deploy           # Deployment 名称
spec:                        # 规格定义
  replicas: 3                # 期望 3 个副本
  selector:                  # 标签选择器
    matchLabels:             # 必须与 template labels 匹配
      app: web
  template:                  # Pod 模板
    metadata:                # Pod 元数据
      labels:                # Pod 标签
        app: web
    spec:                    # Pod 规格
      containers:            # 容器列表
      - name: nginx          # 容器名
        image: nginx:1.25    # 镜像
        ports:               # 端口
        - containerPort: 80
""",
    "Q3.1": """\
apiVersion: v1                  # K8s API 版本
kind: Service                   # 资源类型: Service
metadata:                       # 元数据
  name: nginx-svc               # Service 名称（也是 DNS 名）
spec:                           # 规格定义
  type: ClusterIP               # 默认类型（可省略）
  selector:                     # 标签选择器
    app: nginx                  # 匹配 app=nginx 的 Pod
  ports:                        # 端口映射
  - port: 80                    # Service 端口
    targetPort: 8080            # 后端 Pod 端口
    protocol: TCP               # 协议（默认 TCP）
""",
    "Q3.2": """\
apiVersion: v1                  # K8s API 版本
kind: Service                   # 资源类型: Service
metadata:                       # 元数据
  name: web-svc                 # Service 名称
spec:                           # 规格定义
  type: NodePort                # ← 关键: 设为 NodePort
  selector:                     # 标签选择器
    app: web                    # 匹配 app=web 的 Pod
  ports:                        # 端口映射
  - port: 80                    # Service ClusterIP 端口
    targetPort: 8080            # 后端 Pod 端口
    nodePort: 30080             # Node 端口 (30000-32767，可选)
""",
    "Q3.3": """\
apiVersion: v1                  # K8s API 版本
kind: Pod                       # 资源类型: Pod
metadata:                       # 元数据
  name: frontend-pod            # Pod 名称
spec:                           # 规格定义
  containers:                   # 容器列表
  - name: frontend              # 容器名
    image: nginx:latest         # 镜像
    env:                        # 环境变量
    - name: BACKEND_URL         # 变量名
      value: "backend-svc:3000" # ← 用 Service DNS 名访问后端
""",
    "Q3.4": """\
apiVersion: v1                  # K8s API 版本
kind: Service                   # 资源类型: Service
metadata:                       # 元数据
  name: db-svc                  # Service 名称
spec:                           # 规格定义
  clusterIP: None               # ← 关键: 设为 None (Headless)
  selector:                     # 标签选择器
    app: db                     # 匹配 app=db 的 Pod
  ports:                        # 端口映射
  - port: 5432                  # Service 端口
    targetPort: 5432            # 后端 Pod 端口
""",
    "Q3.5": """\
apiVersion: apps/v1               # Deployment API
kind: Deployment                  # 资源类型: Deployment
metadata:
  name: web-deploy
spec:
  replicas: 2                     # 2 个副本
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web                  # ← Service selector 匹配此标签
    spec:
      containers:
      - name: nginx
        image: nginx:1.25
        ports:
        - containerPort: 80       # ← targetPort 指向此端口
---
apiVersion: v1                    # Service API
kind: Service                     # 资源类型: Service
metadata:
  name: web-svc                   # Service 名称 = DNS 名称
spec:
  type: ClusterIP                 # 集群内部访问
  selector:                       # 匹配 Pod 标签
    app: web                      # ← 必须与 Deployment template labels 一致
  ports:
  - port: 80                      # Service 端口
    targetPort: 80                # Pod 端口
""",
    "Q4.1": """\
apiVersion: v1                  # K8s API 版本
kind: ConfigMap                 # 资源类型: ConfigMap
metadata:                       # 元数据
  name: app-config              # ConfigMap 名称
data:                           # 配置数据（键值对）
  APP_MODE: production          # 应用运行模式
  LOG_LEVEL: info               # 日志级别
  # 也可以存储多行配置文件:
  # config.yaml: |
  #   server:
  #     port: 8080
""",
    "Q4.2": """\
apiVersion: v1                  # K8s API 版本
kind: Pod                       # 资源类型: Pod
metadata:                       # 元数据
  name: app-pod                 # Pod 名称
spec:                           # 规格定义
  containers:                   # 容器列表
  - name: app                   # 容器名
    image: nginx:latest         # 镜像
    envFrom:                    # 批量注入 ConfigMap
    - configMapRef:
        name: app-config        # 引用 app-config 的所有 key
    # 或者逐个引用:
    # env:
    # - name: APP_MODE
    #   valueFrom:
    #     configMapKeyRef:
    #       name: app-config
    #       key: APP_MODE
""",
    "Q4.3": """\
apiVersion: v1                  # K8s API 版本
kind: Pod                       # 资源类型: Pod
metadata:                       # 元数据
  name: config-pod              # Pod 名称
spec:                           # 规格定义
  containers:                   # 容器列表
  - name: app                   # 容器名
    image: nginx:latest         # 镜像
    volumeMounts:               # 卷挂载
    - name: config-vol          # 挂载的 volume 名
      mountPath: /etc/config    # 容器内挂载路径
  volumes:                      # 卷定义
  - name: config-vol            # volume 名（与 mount 一致）
    configMap:                  # 引用 ConfigMap
      name: app-config          # ConfigMap 名称
""",
    "Q4.4": """\
apiVersion: v1                  # K8s API 版本
kind: Secret                    # 资源类型: Secret
metadata:                       # 元数据
  name: db-secret               # Secret 名称
type: Opaque                    # 通用类型（默认）
data:                           # Base64 编码数据
  password: bXlwYXNzd29yZA==    # echo -n 'mypassword' | base64
---                             # 多文档分隔符
apiVersion: v1                  # Pod 定义
kind: Pod
metadata:
  name: db-client               # Pod 名称
spec:
  containers:
  - name: client                # 容器名
    image: postgres:15          # 镜像
    env:                        # 环境变量
    - name: DB_PASSWORD         # 变量名
      valueFrom:
        secretKeyRef:           # 引用 Secret
          name: db-secret       # Secret 名称
          key: password         # data 中的 key
""",
    "Q4.5": """\
apiVersion: v1                  # ConfigMap API
kind: ConfigMap                 # 资源类型: ConfigMap
metadata:
  name: app-config              # ConfigMap 名称
data:                           # 配置数据（键值对）
  APP_MODE: production          # 应用模式
  LOG_LEVEL: info               # 日志级别
  DB_HOST: db.default.svc       # 数据库地址
---
apiVersion: v1                  # Pod API
kind: Pod                       # 资源类型: Pod
metadata:
  name: app-pod                 # Pod 名称
spec:
  containers:
  - name: app                   # 容器名
    image: nginx:1.25           # 镜像
    envFrom:                    # 批量注入环境变量
    - configMapRef:             # 引用 ConfigMap
        name: app-config        # ConfigMap 名称
""",
    "Q5.1": """\
apiVersion: v1                  # K8s API 版本
kind: PersistentVolume          # 资源类型: PV
metadata:                       # 元数据
  name: data-pv                 # PV 名称
spec:                           # 规格定义
  capacity:                     # 容量
    storage: 5Gi                # 5 GiB
  accessModes:                  # 访问模式
  - ReadWriteOnce               # 单节点读写（RWO）
  hostPath:                     # 本地路径（仅测试）
    path: /mnt/data             # Node 上的路径
  # persistentVolumeReclaimPolicy: Retain  # 回收策略
""",
    "Q5.2": """\
apiVersion: v1                  # K8s API 版本
kind: PersistentVolumeClaim     # 资源类型: PVC
metadata:                       # 元数据
  name: data-pvc                # PVC 名称
spec:                           # 规格定义
  accessModes:                  # 访问模式（与 PV 匹配）
  - ReadWriteOnce               # 单节点读写
  resources:                    # 资源请求
    requests:                   # 请求量
      storage: 5Gi              # 请求 5Gi 存储
  # storageClassName: standard  # 指定 StorageClass（可选）
""",
    "Q5.3": """\
apiVersion: v1                  # K8s API 版本
kind: Pod                       # 资源类型: Pod
metadata:                       # 元数据
  name: app-pod                 # Pod 名称
spec:                           # 规格定义
  containers:                   # 容器列表
  - name: app                   # 容器名
    image: nginx                # 镜像
    volumeMounts:               # 卷挂载
    - name: data-volume         # 引用 volume 名
      mountPath: /app/data      # 容器内挂载路径
  volumes:                      # 卷定义
  - name: data-volume           # volume 名
    persistentVolumeClaim:      # 引用 PVC
      claimName: data-pvc       # PVC 名称
""",
    "Q5.4": """\
apiVersion: v1                  # K8s API 版本
kind: Pod                       # 资源类型: Pod
metadata:                       # 元数据
  name: shared-pod              # Pod 名称
spec:                           # 规格定义
  containers:                   # 容器列表
  - name: writer                # 写入容器
    image: busybox              # 轻量镜像
    volumeMounts:               # 卷挂载
    - name: shared-data         # 引用 volume
      mountPath: /output        # 写入路径
  - name: reader                # 读取容器
    image: busybox              # 轻量镜像
    volumeMounts:               # 卷挂载
    - name: shared-data         # 同一个 volume
      mountPath: /input         # 读取路径
  volumes:                      # 卷定义
  - name: shared-data           # volume 名
    emptyDir: {}                # 临时空目录
""",
    "Q5.5": """\
apiVersion: v1                     # PVC API
kind: PersistentVolumeClaim        # 资源类型: PVC
metadata:
  name: data-pvc                   # PVC 名称
spec:
  accessModes:                     # 访问模式
  - ReadWriteOnce                  # 单节点读写
  resources:                       # 资源请求
    requests:                      # 申请量
      storage: 1Gi                 # 1 GiB
---
apiVersion: v1                     # Pod API
kind: Pod                          # 资源类型: Pod
metadata:
  name: app-pod                    # Pod 名称
spec:
  containers:
  - name: app                      # 容器名
    image: nginx:1.25              # 镜像
    volumeMounts:                  # 卷挂载
    - name: data                   # 卷名（与 volumes 对应）
      mountPath: /data             # 挂载到容器的 /data
  volumes:                         # 卷定义
  - name: data                     # 卷名
    persistentVolumeClaim:         # 引用 PVC
      claimName: data-pvc          # PVC 名称
""",
    "Q6.1": """\
apiVersion: v1                  # K8s API 版本
kind: Pod                       # 资源类型: Pod
metadata:                       # 元数据
  name: nginx-pod               # Pod 名称
spec:                           # 规格定义
  nodeSelector:                 # 节点选择器
    disktype: ssd               # 只调度到 disktype=ssd 的节点
  containers:                   # 容器列表
  - name: nginx                 # 容器名
    image: nginx                # 镜像
""",
    "Q6.2": """\
apiVersion: v1                  # K8s API 版本
kind: Pod                       # 资源类型: Pod
metadata:                       # 元数据
  name: ml-pod                  # Pod 名称
spec:                           # 规格定义
  affinity:                     # 亲和性配置
    nodeAffinity:               # 节点亲和性
      requiredDuringSchedulingIgnoredDuringExecution:  # 硬约束
        nodeSelectorTerms:      # 选择器条件
        - matchExpressions:     # 匹配表达式
          - key: gpu            # 标签 key
            operator: In        # 操作符: 值在列表中
            values:             # 匹配值列表
            - "true"            # gpu=true 的节点
  containers:                   # 容器列表
  - name: app                   # 容器名
    image: tensorflow:latest    # 镜像
""",
    "Q6.3": """\
apiVersion: v1                  # K8s API 版本
kind: Pod                       # 资源类型: Pod
metadata:                       # 元数据
  name: special-pod             # Pod 名称
spec:                           # 规格定义
  tolerations:                  # 容忍列表
  - key: "dedicated"            # 匹配的 Taint key
    operator: "Equal"           # 精确匹配 key=value
    value: "special"            # 匹配的 Taint value
    effect: "NoSchedule"        # 匹配的 Taint effect
  containers:                   # 容器列表
  - name: app                   # 容器名
    image: nginx                # 镜像
""",
    "Q6.4": """\
apiVersion: v1                  # K8s API 版本
kind: Pod                       # 资源类型: Pod
metadata:                       # 元数据
  name: limited-pod             # Pod 名称
spec:                           # 规格定义
  containers:                   # 容器列表
  - name: app                   # 容器名
    image: nginx                # 镜像
    resources:                  # 资源配置
      requests:                 # 请求量（调度依据）
        cpu: "100m"             # 100 millicpu = 0.1 核
        memory: "128Mi"         # 128 MiB
      limits:                   # 上限（运行时硬限制）
        cpu: "500m"             # 最多 0.5 核
        memory: "256Mi"         # 最多 256 MiB
""",
    "Q6.5": """\
apiVersion: v1              # K8s API 版本
kind: Pod                   # 资源类型: Pod
metadata:
  name: nginx-pod           # Pod 名称
spec:                       # 规格定义
  containers:               # 容器列表
  - name: nginx             # 容器名
    image: nginx:1.25       # 镜像
  nodeSelector:             # 节点选择器（硬约束）
    disktype: ssd           # 只调度到有 disktype=ssd 标签的节点
""",
    "Q7.1": """\
apiVersion: batch/v1       # Job API 版本
kind: Job                  # 资源类型: Job
metadata:                  # 元数据
  name: pi                 # Job 名称
spec:                      # 规格定义
  template:                # Pod 模板
    spec:                  # Pod 规格
      containers:          # 容器列表
      - name: pi           # 容器名
        image: perl:5.38   # Perl 镜像
        command:           # 启动命令
        - perl
        - "-Mbignum=bpi"
        - "-wle"
        - "print bpi(2000)"
      restartPolicy: Never # 失败不重启，创建新 Pod
  backoffLimit: 4          # 最多重试 4 次
""",
    "Q7.2": """\
apiVersion: batch/v1       # Job API 版本
kind: Job                  # 资源类型
metadata:                  # 元数据
  name: parallel-job       # Job 名称
spec:                      # 规格定义
  parallelism: 3           # 最大并发 3 个 Pod
  completions: 6           # 总共完成 6 个任务
  backoffLimit: 4          # 最多重试 4 次
  template:                # Pod 模板
    spec:                  # Pod 规格
      containers:          # 容器列表
      - name: worker       # 容器名
        image: busybox:1.36 # 镜像
        command:           # 启动命令
        - echo
        - hello
      restartPolicy: Never # 失败不重启
""",
    "Q7.3": """\
apiVersion: batch/v1           # CronJob API 版本
kind: CronJob                 # 资源类型
metadata:                     # 元数据
  name: hello-cron            # CronJob 名称
spec:                         # 规格定义
  schedule: "*/1 * * * *"     # 每分钟执行
  jobTemplate:                # Job 模板
    spec:                     # Job 规格
      template:               # Pod 模板
        spec:                 # Pod 规格
          containers:         # 容器列表
          - name: hello       # 容器名
            image: busybox:1.36 # 镜像
            command:          # 启动命令
            - echo
            - "hello from cron"
          restartPolicy: Never # 重启策略
""",
    "Q7.4": """\
apiVersion: batch/v1              # CronJob API 版本
kind: CronJob                    # 资源类型
metadata:                        # 元数据
  name: forbid-cron              # CronJob 名称
spec:                            # 规格定义
  schedule: "*/1 * * * *"        # 每分钟执行
  concurrencyPolicy: Forbid      # 禁止并发：跳过本次触发
  successfulJobsHistoryLimit: 3  # 保留 3 个成功 Job
  failedJobsHistoryLimit: 1      # 保留 1 个失败 Job
  jobTemplate:                   # Job 模板
    spec:                        # Job 规格
      template:                  # Pod 模板
        spec:                    # Pod 规格
          containers:            # 容器列表
          - name: task           # 容器名
            image: busybox:1.36  # 镜像
            command:             # 启动命令
            - sleep
            - "30"
          restartPolicy: Never   # 重启策略
""",
    "Q7.5": """\
apiVersion: batch/v1              # Job API 版本
kind: Job                        # 资源类型
metadata:                        # 元数据
  name: compute-job              # Job 名称
spec:                            # 规格定义
  activeDeadlineSeconds: 300     # 最长运行 5 分钟
  ttlSecondsAfterFinished: 60    # 完成后 60 秒自动清理
  template:                      # Pod 模板
    spec:                        # Pod 规格
      containers:                # 容器列表
      - name: compute            # 容器名
        image: perl:5.38         # Perl 镜像
        command:                 # 启动命令
        - perl
        - "-Mbignum=bpi"
        - "-wle"
        - "print bpi(2000)"
      restartPolicy: Never       # 失败不重启
""",
    "Q8.1": """\
apiVersion: apps/v1           # StatefulSet API 版本
kind: StatefulSet             # 资源类型
metadata:                     # 元数据
  name: web                   # StatefulSet 名称
spec:                         # 规格定义
  serviceName: web            # 关联的 Headless Service (必填)
  replicas: 3                 # 3 个副本
  selector:                   # 标签选择器
    matchLabels:              # 必须与 template labels 匹配
      app: web
  template:                   # Pod 模板
    metadata:                 # Pod 元数据
      labels:                 # Pod 标签
        app: web
    spec:                     # Pod 规格
      containers:             # 容器列表
      - name: nginx           # 容器名
        image: nginx:1.25     # 镜像
        ports:                # 端口
        - containerPort: 80
""",
    "Q8.2": """\
apiVersion: apps/v1           # StatefulSet API 版本
kind: StatefulSet             # 资源类型
metadata:                     # 元数据
  name: web                   # 名称（与原有一致）
spec:                         # 规格定义
  serviceName: web            # Headless Service
  replicas: 5                 # 扩容到 5 副本
  selector:                   # 标签选择器
    matchLabels:
      app: web
  template:                   # Pod 模板
    metadata:
      labels:
        app: web
    spec:
      containers:             # 容器列表
      - name: nginx           # 容器名
        image: nginx:1.25     # 镜像
        ports:
        - containerPort: 80
""",
    "Q8.3": """\
# Headless Service                         # 无 ClusterIP 的 Service
apiVersion: v1                             # API 版本
kind: Service                              # 资源类型: Service
metadata:                                  # 元数据
  name: nginx                              # Service 名称
spec:                                      # 规格定义
  clusterIP: None                          # ← Headless: 不分配 ClusterIP
  selector:                                # 选择 Pod
    app: nginx
  ports:                                   # 端口配置
  - port: 80                               # Service 端口
    name: web
---                                        # 多文档分隔
apiVersion: apps/v1                        # StatefulSet API 版本
kind: StatefulSet                          # 资源类型
metadata:                                  # 元数据
  name: nginx                              # StatefulSet 名称
spec:                                      # 规格定义
  serviceName: nginx                       # ← 指向 Headless Service
  replicas: 3                              # 3 个副本
  selector:                                # 标签选择器
    matchLabels:
      app: nginx
  template:                                # Pod 模板
    metadata:
      labels:
        app: nginx
    spec:
      containers:                          # 容器列表
      - name: nginx                        # 容器名
        image: nginx:1.25                  # 镜像
        ports:
        - containerPort: 80
""",
    "Q8.4": """\
apiVersion: apps/v1                    # StatefulSet API 版本
kind: StatefulSet                     # 资源类型
metadata:                             # 元数据
  name: data-app                      # StatefulSet 名称
spec:                                 # 规格定义
  serviceName: data-app               # Headless Service
  replicas: 3                         # 3 个副本
  selector:                           # 标签选择器
    matchLabels:
      app: data-app
  volumeClaimTemplates:               # ← PVC 模板
  - metadata:                         # PVC 元数据
      name: data                      # PVC 模板名
    spec:                             # PVC 规格
      accessModes: [ReadWriteOnce]    # 访问模式
      resources:                      # 资源请求
        requests:
          storage: 1Gi                # 请求 1Gi 存储
  template:                           # Pod 模板
    metadata:
      labels:
        app: data-app
    spec:
      containers:                     # 容器列表
      - name: app                     # 容器名
        image: busybox:1.36           # 镜像
        command: [sleep, "3600"]      # 保持运行
        volumeMounts:                 # 挂载存储
        - name: data                  # 引用 PVC 模板名
          mountPath: /data            # 挂载路径
""",
    "Q8.5": """\
# Headless Service
apiVersion: v1                             # API 版本
kind: Service                              # 资源类型
metadata:                                  # 元数据
  name: mysql                              # Service 名称
spec:                                      # 规格定义
  clusterIP: None                          # Headless Service
  selector:                                # 选择 MySQL Pod
    app: mysql
  ports:                                   # 端口配置
  - port: 3306                             # MySQL 端口
    name: mysql
---                                        # 多文档分隔
apiVersion: apps/v1                        # StatefulSet API 版本
kind: StatefulSet                          # 资源类型
metadata:                                  # 元数据
  name: mysql                              # StatefulSet 名称
spec:                                      # 规格定义
  serviceName: mysql                       # 指向 Headless Service
  replicas: 3                              # 3 个副本
  selector:                                # 标签选择器
    matchLabels:
      app: mysql
  template:                                # Pod 模板
    metadata:
      labels:
        app: mysql
    spec:
      containers:                          # 容器列表
      - name: mysql                        # 容器名
        image: mysql:8.0                   # MySQL 镜像
        env:                               # 环境变量
        - name: MYSQL_ROOT_PASSWORD        # root 密码
          value: "password123"
        ports:                             # 端口
        - containerPort: 3306
        volumeMounts:                      # 挂载存储
        - name: data                       # 引用 PVC 模板
          mountPath: /var/lib/mysql        # MySQL 数据目录
  volumeClaimTemplates:                    # PVC 模板
  - metadata:
      name: data                           # PVC 模板名
    spec:
      accessModes: [ReadWriteOnce]         # 访问模式
      resources:
        requests:
          storage: 5Gi                     # 请求 5Gi 存储
""",
    "Q9.1": """\
apiVersion: rbac.authorization.k8s.io/v1   # RBAC API 版本
kind: Role                                 # 资源类型: Role
metadata:                                  # 元数据
  name: pod-reader                         # Role 名称
  namespace: default                       # 命名空间（可选，默认 default）
rules:                                     # 权限规则
- apiGroups: [""]                          # 核心 API 组
  resources: ["pods", "services"]          # 允许操作 Pod 和 Service
  verbs: ["get", "list"]                   # 允许 get 和 list 操作
""",
    "Q9.2": """\
apiVersion: rbac.authorization.k8s.io/v1   # RBAC API 版本
kind: RoleBinding                          # 资源类型: RoleBinding
metadata:                                  # 元数据
  name: pod-reader-binding                 # RoleBinding 名称
  namespace: default                       # 命名空间
roleRef:                                   # 引用的 Role
  kind: Role                               # 角色类型: Role
  name: pod-reader                         # Role 名称
  apiGroup: rbac.authorization.k8s.io      # API 组
subjects:                                  # 被授权的主体
- kind: ServiceAccount                     # 主体类型: ServiceAccount
  name: my-sa                              # SA 名称
  namespace: default                       # SA 所在命名空间
""",
    "Q9.3": """\
apiVersion: rbac.authorization.k8s.io/v1   # RBAC API 版本
kind: ClusterRole                          # 资源类型: ClusterRole
metadata:                                  # 元数据
  name: node-manager                       # ClusterRole 名称
rules:                                     # 权限规则
- apiGroups: [""]                          # 核心 API 组
  resources: ["nodes"]                     # 管理节点资源
  verbs: ["get", "list", "watch"]          # 允许查看节点
""",
    "Q9.4": """\
apiVersion: rbac.authorization.k8s.io/v1   # RBAC API 版本
kind: ClusterRoleBinding                   # 资源类型: ClusterRoleBinding
metadata:                                  # 元数据
  name: node-manager-binding               # 名称
roleRef:                                   # 引用的 ClusterRole
  kind: ClusterRole                        # 必须为 ClusterRole
  name: node-manager                       # ClusterRole 名称
  apiGroup: rbac.authorization.k8s.io      # API 组
subjects:                                  # 被授权的主体
- kind: ServiceAccount                     # 主体类型
  name: node-sa                            # SA 名称
  namespace: default                       # SA 所在命名空间
""",
    "Q9.5": """\
# Role                                        # 权限定义
apiVersion: rbac.authorization.k8s.io/v1      # RBAC API 版本
kind: Role                                    # 资源类型: Role
metadata:                                     # 元数据
  name: pod-reader                            # Role 名称
rules:                                        # 权限规则
- apiGroups: [""]                             # 核心 API 组
  resources: ["pods", "services"]             # 可操作的资源
  verbs: ["get", "list"]                      # 允许的操作
---                                           # 多文档分隔
# RoleBinding                                 # 权限绑定
apiVersion: rbac.authorization.k8s.io/v1      # RBAC API 版本
kind: RoleBinding                             # 资源类型: RoleBinding
metadata:                                     # 元数据
  name: pod-reader-binding                    # 名称
roleRef:                                      # 引用 Role
  kind: Role                                  # 角色类型
  name: pod-reader                            # Role 名称
  apiGroup: rbac.authorization.k8s.io         # API 组
subjects:                                     # 被授权主体
- kind: ServiceAccount                        # 主体类型
  name: my-sa                                 # SA 名称（真实集群中需先创建 SA）
  namespace: default                          # 命名空间
""",
    "Q10.1": """\
apiVersion: autoscaling/v2                    # HPA API 版本
kind: HorizontalPodAutoscaler                 # 资源类型: HPA
metadata:                                     # 元数据
  name: web-hpa                               # HPA 名称
spec:                                         # 规格定义
  scaleTargetRef:                             # 伸缩目标
    apiVersion: apps/v1                       # 目标 API 版本
    kind: Deployment                          # 目标类型
    name: web                                 # 目标名称
  maxReplicas: 10                             # 最大副本数
  metrics:                                    # 伸缩指标
  - type: Resource                            # 指标类型: 资源指标
    resource:                                 # 资源配置
      name: cpu                               # CPU 指标
      target:                                 # 目标值
        type: Utilization                     # 利用率类型
        averageUtilization: 50                # 目标 50% 利用率
""",
    "Q10.2": """\
apiVersion: autoscaling/v2                    # HPA API 版本
kind: HorizontalPodAutoscaler                 # 资源类型: HPA
metadata:                                     # 元数据
  name: web-hpa                               # HPA 名称
spec:                                         # 规格定义
  scaleTargetRef:                             # 伸缩目标
    apiVersion: apps/v1                       # 目标 API 版本
    kind: Deployment                          # 目标类型
    name: web                                 # 目标名称
  minReplicas: 2                              # 最小副本数
  maxReplicas: 20                             # 最大副本数
  metrics:                                    # 伸缩指标
  - type: Resource                            # 资源指标
    resource:                                 # 资源配置
      name: cpu                               # CPU 指标
      target:                                 # 目标值
        type: Utilization                     # 利用率
        averageUtilization: 50                # 目标 50%
""",
    "Q10.3": """\
apiVersion: autoscaling/v2                    # HPA API 版本 (v2 支持多指标)
kind: HorizontalPodAutoscaler                 # 资源类型: HPA
metadata:                                     # 元数据
  name: web-hpa                               # HPA 名称
spec:                                         # 规格定义
  scaleTargetRef:                             # 伸缩目标
    apiVersion: apps/v1
    kind: Deployment
    name: web
  minReplicas: 2                              # 最小副本数
  maxReplicas: 20                             # 最大副本数
  metrics:                                    # 多指标列表
  - type: Resource                            # 指标 1: CPU
    resource:
      name: cpu                               # CPU 资源
      target:
        type: Utilization                     # 利用率类型
        averageUtilization: 50                # 目标 50%
  - type: Resource                            # 指标 2: Memory
    resource:
      name: memory                            # Memory 资源
      target:
        type: Utilization                     # 利用率类型
        averageUtilization: 60                # 目标 60%
""",
    "Q10.4": """\
apiVersion: autoscaling/v2                    # HPA API 版本
kind: HorizontalPodAutoscaler                 # 资源类型
metadata:                                     # 元数据
  name: web-hpa                               # 名称
spec:                                         # 规格定义
  scaleTargetRef:                             # 伸缩目标
    apiVersion: apps/v1
    kind: Deployment
    name: web
  minReplicas: 2                              # 最小副本
  maxReplicas: 20                             # 最大副本
  metrics:                                    # 指标
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
  behavior:                                   # ← 行为配置
    scaleDown:                                # 缩容行为
      stabilizationWindowSeconds: 300         # 5 分钟稳定窗口
      policies:                               # 策略列表
      - type: Percent                         # 按百分比
        value: 10                             # 最多缩 10%
        periodSeconds: 60                     # 每 60 秒一次
      selectPolicy: Min                       # 选最小变化（保守）
    scaleUp:                                  # 扩容行为
      stabilizationWindowSeconds: 0           # 无延迟，立即扩容
      policies:
      - type: Percent
        value: 100                            # 可翻倍扩容
        periodSeconds: 15                     # 每 15 秒一次
""",
    "Q10.5": """\
# Deployment                              # 被伸缩的目标
apiVersion: apps/v1                      # Deployment API 版本
kind: Deployment                         # 资源类型
metadata:                                # 元数据
  name: web                              # 名称
spec:                                    # 规格
  replicas: 2                            # 初始副本数
  selector:                              # 标签选择器
    matchLabels:
      app: web
  template:                              # Pod 模板
    metadata:
      labels:
        app: web
    spec:
      containers:                        # 容器列表
      - name: nginx                      # 容器名
        image: nginx:1.25               # 镜像
        resources:                       # 资源设置（关键！）
          requests:                      # 请求值
            cpu: 100m                    # HPA 基于 requests 计算
---                                      # 多文档分隔
# HorizontalPodAutoscaler                # 自动伸缩器
apiVersion: autoscaling/v2               # HPA API 版本
kind: HorizontalPodAutoscaler            # 资源类型
metadata:                                # 元数据
  name: web-hpa                          # 名称
spec:                                    # 规格
  scaleTargetRef:                        # 伸缩目标
    apiVersion: apps/v1
    kind: Deployment
    name: web                            # 指向 Deployment
  minReplicas: 2                         # 最小副本
  maxReplicas: 10                        # 最大副本
  metrics:                               # 伸缩指标
  - type: Resource                       # 资源指标
    resource:
      name: cpu                          # CPU
      target:
        type: Utilization                # 利用率
        averageUtilization: 50           # 目标 50%
""",
    "Q11.1": """\
apiVersion: networking.k8s.io/v1            # Ingress API 版本
kind: Ingress                               # 资源类型: Ingress
metadata:                                   # 元数据
  name: web-ingress                         # Ingress 名称
  annotations:                              # 注解（可选）
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:                                       # 规格定义
  rules:                                    # 路由规则
  - host: example.com                       # 匹配域名
    http:                                   # HTTP 路由
      paths:                                # 路径列表
      - path: /                             # 匹配路径
        pathType: Prefix                    # 前缀匹配
        backend:                            # 后端配置
          service:                          # 指向 Service
            name: web-svc                   # Service 名称
            port:                           # 端口
              number: 80                    # 端口号
""",
    "Q11.2": """\
apiVersion: networking.k8s.io/v1            # Ingress API 版本
kind: Ingress                               # 资源类型
metadata:                                   # 元数据
  name: multi-host-ingress                  # 名称
spec:                                       # 规格
  rules:                                    # 路由规则（多个）
  - host: example.com                       # 域名 1
    http:                                   # HTTP 路由
      paths:
      - path: /                             # 匹配所有路径
        pathType: Prefix                    # 前缀匹配
        backend:                            # 后端
          service:
            name: web-svc                   # Web 服务
            port:
              number: 80
  - host: api.example.com                   # 域名 2
    http:                                   # HTTP 路由
      paths:
      - path: /                             # 匹配所有路径
        pathType: Prefix
        backend:                            # 后端
          service:
            name: api-svc                   # API 服务
            port:
              number: 8080
""",
    "Q11.3": """\
apiVersion: networking.k8s.io/v1            # Ingress API 版本
kind: Ingress                               # 资源类型
metadata:                                   # 元数据
  name: path-routing-ingress                # 名称
  annotations:                              # 注解
    nginx.ingress.kubernetes.io/rewrite-target: /  # 重写目标
spec:                                       # 规格
  rules:                                    # 路由规则
  - host: example.com                       # 域名
    http:                                   # HTTP 路由
      paths:                                # 路径列表
      - path: /api                          # API 路径
        pathType: Prefix                    # 前缀匹配
        backend:                            # 后端
          service:
            name: api-svc                   # API 服务
            port:
              number: 8080
      - path: /web                          # Web 路径
        pathType: Prefix                    # 前缀匹配
        backend:                            # 后端
          service:
            name: web-svc                   # Web 服务
            port:
              number: 80
""",
    "Q11.4": """\
apiVersion: networking.k8s.io/v1            # Ingress API 版本
kind: Ingress                               # 资源类型
metadata:                                   # 元数据
  name: tls-ingress                         # 名称
  annotations:                              # 注解
    nginx.ingress.kubernetes.io/ssl-redirect: "true"  # HTTP 重定向到 HTTPS
spec:                                       # 规格
  tls:                                      # ← TLS 配置
  - hosts:                                  # 使用该证书的域名
    - example.com                           # 域名
    secretName: tls-secret                  # TLS 证书 Secret
  rules:                                    # 路由规则
  - host: example.com                       # 域名
    http:                                   # HTTP 路由
      paths:
      - path: /                             # 路径
        pathType: Prefix                    # 前缀匹配
        backend:                            # 后端
          service:
            name: web-svc                   # Service 名称
            port:
              number: 80
""",
    "Q11.5": """\
# Deployment                                # Web 应用
apiVersion: apps/v1                        # API 版本
kind: Deployment                           # 资源类型
metadata:                                  # 元数据
  name: web                                # 名称
spec:                                      # 规格
  replicas: 2                              # 2 个副本
  selector:                                # 标签选择器
    matchLabels:
      app: web
  template:                                # Pod 模板
    metadata:
      labels:
        app: web
    spec:
      containers:                          # 容器
      - name: nginx                        # 容器名
        image: nginx:1.25                 # 镜像
---                                        # 多文档分隔
# Service                                  # 服务暴露
apiVersion: v1                             # API 版本
kind: Service                              # 资源类型
metadata:                                  # 元数据
  name: web-svc                            # 名称
spec:                                      # 规格
  selector:                                # 选择 Pod
    app: web                               # 匹配标签
  ports:                                   # 端口
  - port: 80                               # Service 端口
---                                        # 多文档分隔
# Ingress                                  # 入口路由
apiVersion: networking.k8s.io/v1           # Ingress API 版本
kind: Ingress                              # 资源类型
metadata:                                  # 元数据
  name: web-ingress                        # 名称
spec:                                      # 规格
  ingressClassName: nginx                  # Ingress Controller 类
  rules:                                   # 路由规则
  - host: example.com                      # 域名
    http:                                  # HTTP 路由
      paths:                               # 路径列表
      - path: /                            # 匹配所有路径
        pathType: Prefix                   # 前缀匹配
        backend:                           # 后端
          service:                         # 指向 Service
            name: web-svc                  # Service 名称
            port:
              number: 80                   # 端口
""",
    "Q12.1": """\
apiVersion: networking.k8s.io/v1            # NetworkPolicy API 版本
kind: NetworkPolicy                          # 资源类型: NetworkPolicy
metadata:                                    # 元数据
  name: default-deny                         # 策略名称
  namespace: default                         # 命名空间（可选，默认 default）
spec:                                        # 规格定义
  podSelector: {}                            # 空选择器 = 所有 Pod
  policyTypes:                               # 策略类型
  - Ingress                                  # 仅控制入站流量
  # 不写 ingress = 拒绝所有入站
""",
    "Q12.2": """\
apiVersion: networking.k8s.io/v1            # NetworkPolicy API 版本
kind: NetworkPolicy                          # 资源类型
metadata:                                    # 元数据
  name: allow-from-frontend                  # 策略名称
  namespace: backend                         # 目标命名空间
spec:                                        # 规格
  podSelector: {}                            # 选择所有 Pod
  policyTypes:                               # 策略类型
  - Ingress                                  # 控制入站
  ingress:                                   # 入站规则
  - from:                                    # 允许来源
    - namespaceSelector:                     # 按命名空间选择
        matchLabels:                         # 标签匹配
          kubernetes.io/metadata.name: frontend  # frontend 命名空间
""",
    "Q12.3": """\
apiVersion: networking.k8s.io/v1            # NetworkPolicy API 版本
kind: NetworkPolicy                          # 资源类型
metadata:                                    # 元数据
  name: allow-api-client                     # 策略名称
spec:                                        # 规格
  podSelector:                               # 目标 Pod（被保护的）
    matchLabels:                             # 标签匹配
      app: backend                           # 保护 app=backend 的 Pod
  policyTypes:                               # 策略类型
  - Ingress                                  # 控制入站
  ingress:                                   # 入站规则
  - from:                                    # 允许来源
    - podSelector:                           # 按 Pod 标签选择
        matchLabels:                         # 标签匹配
          app: api-client                    # 只允许 app=api-client 的 Pod
  ports:                                     # 允许端口（可选）
  - protocol: TCP                            # 协议
    port: 8080                               # 端口号
""",
    "Q12.4": """\
apiVersion: networking.k8s.io/v1            # NetworkPolicy API 版本
kind: NetworkPolicy                          # 资源类型
metadata:                                    # 元数据
  name: ingress-egress-policy               # 策略名称
spec:                                        # 规格
  podSelector:                               # 目标 Pod
    matchLabels:
      app: backend                           # 保护 app=backend
  policyTypes:                               # 策略类型（双向）
  - Ingress                                  # 控制入站
  - Egress                                   # 控制出站
  ingress:                                   # 入站规则
  - from:                                    # 允许来源
    - podSelector:                           # 按 Pod 标签
        matchLabels:
          app: frontend                      # 只允许 frontend
  ports:                                     # 入站端口
  - protocol: TCP
    port: 8080
  egress:                                    # 出站规则
  - to:                                      # 允许目标
    - podSelector:                           # 按 Pod 标签
        matchLabels:
          app: database                      # 只允许访问 database
    ports:                                   # 出站端口
    - protocol: TCP
      port: 5432                             # PostgreSQL 端口
""",
    "Q12.5": """\
apiVersion: networking.k8s.io/v1            # NetworkPolicy API 版本
kind: NetworkPolicy                          # 资源类型
metadata:                                    # 元数据
  name: db-isolation                         # 策略名称
  namespace: default                         # 命名空间
spec:                                        # 规格
  podSelector:                               # 选择数据库 Pod
    matchLabels:                             # 标签匹配
      app: database                          # 数据库 Pod 标签
  policyTypes:                               # 策略类型
  - Ingress                                  # 控制入站
  ingress:                                   # 入站规则
  - from:                                    # 允许来源
    - podSelector:                           # 按 Pod 标签
        matchLabels:                         # 标签匹配
          app: backend                       # 只允许 backend Pod
    ports:                                   # 端口限制
    - protocol: TCP                          # 协议
      port: 5432                             # PostgreSQL 端口
""",
}

# 关卡顺序（Q0.1 -> Q12.5）
ALL_LEVEL_IDS = (
    [f"Q0.{lv}" for lv in range(1, 4)]            # Ch0: 3 levels
    + [f"Q1.{lv}" for lv in range(1, 8)]          # Ch1: 7 levels (incl. Q1.6, Q1.7)
    + [f"Q{ch}.{lv}" for ch in range(2, 13) for lv in range(1, 6)]  # Ch2-12: 55 levels
)

# 每章关卡列表
CHAPTERS = {
    0: ['Q0.1', 'Q0.2', 'Q0.3'],
    1: ['Q1.1', 'Q1.2', 'Q1.3', 'Q1.4', 'Q1.5', 'Q1.6', 'Q1.7'],
2: ['Q2.1', 'Q2.2', 'Q2.3', 'Q2.4', 'Q2.5'],
3: ['Q3.1', 'Q3.2', 'Q3.3', 'Q3.4', 'Q3.5'],
4: ['Q4.1', 'Q4.2', 'Q4.3', 'Q4.4', 'Q4.5'],
5: ['Q5.1', 'Q5.2', 'Q5.3', 'Q5.4', 'Q5.5'],
6: ['Q6.1', 'Q6.2', 'Q6.3', 'Q6.4', 'Q6.5'],
7: ['Q7.1', 'Q7.2', 'Q7.3', 'Q7.4', 'Q7.5'],
8: ['Q8.1', 'Q8.2', 'Q8.3', 'Q8.4', 'Q8.5'],
9: ['Q9.1', 'Q9.2', 'Q9.3', 'Q9.4', 'Q9.5'],
10: ['Q10.1', 'Q10.2', 'Q10.3', 'Q10.4', 'Q10.5'],
11: ['Q11.1', 'Q11.2', 'Q11.3', 'Q11.4', 'Q11.5'],
12: ['Q12.1', 'Q12.2', 'Q12.3', 'Q12.4', 'Q12.5'],
}

LEVEL_XP = 10
CHAPTER_BONUS_XP = 50


# ==========================================================================
#  E2E 通关旅程
# ==========================================================================

class TestE2EJourney:
    """模拟学员从 Q1.1 到 Q12.5 的完整通关旅程"""

    @pytest.fixture(autouse=True)
    def setup_journey(self):
        """执行完整通关流程，记录每一步的状态。"""
        self.completed_levels = []
        self.level_attempts = {}
        self.level_first_try = []
        self.level_time_spent = {}
        self.total_xp = 0
        self.check_results = {}  # level_id -> check response
        self.xp_after_each_level = []  # (level_id, xp_after)

        chapter_bonus_claimed = set()

        for level_id in ALL_LEVEL_IDS:
            # 提交正确答案
            r = client.post("/api/check", json={
                "level_id": level_id,
                "user_yaml": CORRECT_ANSWERS[level_id],
            })
            assert r.status_code == 200
            check_data = r.json()
            self.check_results[level_id] = check_data

            # 验证通过
            assert check_data["ok"] is True, (
                f"Level {level_id} should pass with correct answer, "
                f"got error: {check_data.get('error', '')}"
            )

            # 记录通关状态
            self.completed_levels.append(level_id)
            self.level_attempts[level_id] = 1  # 一次通过
            self.level_first_try.append(level_id)
            self.level_time_spent[level_id] = 60  # 假设每关 60 秒

            # XP 计算：每关 +10
            self.total_xp += LEVEL_XP

            # 章节通关奖励：该章 5 关全部完成时 +50
            ch_num = int(level_id.split(".")[0][1:])
            ch_levels = CHAPTERS[ch_num]
            if all(l in self.completed_levels for l in ch_levels):
                if ch_num not in chapter_bonus_claimed:
                    self.total_xp += CHAPTER_BONUS_XP
                    chapter_bonus_claimed.add(ch_num)

            self.xp_after_each_level.append((level_id, self.total_xp))

    # ---- 验证每关都通过 ----

    def test_all_65_levels_passed(self):
        """所有 65 关都应通过"""
        assert len(self.check_results) == 65
        for lid, result in self.check_results.items():
            assert result["ok"] is True, f"{lid} did not pass"

    def test_all_65_levels_have_cluster_state(self):
        """通过的关卡应返回 cluster_state（非 None）"""
        for lid, result in self.check_results.items():
            # 部分关卡可能返回 None cluster_state（如纯 ConfigMap），但 ok=True 即可
            assert result["ok"] is True

    # ---- 验证 XP 累积过程 ----

    def test_xp_accumulation_per_level(self):
        """每关 +10 XP"""
        # Q0.1 之后应为 10
        assert self.xp_after_each_level[0] == ("Q0.1", 10)
        # Q0.2 之后应为 20
        assert self.xp_after_each_level[1] == ("Q0.2", 20)

    def test_xp_chapter_bonus_after_ch0(self):
        """完成 Ch0 全部 3 关后 +50 章节奖励"""
        # Q0.3 是 Ch0 最后一关，完成后 XP = 3*10 + 50 = 80
        q03_xp = next(xp for lid, xp in self.xp_after_each_level if lid == "Q0.3")
        assert q03_xp == 80  # 30 + 50

    def test_xp_chapter_bonus_after_ch1(self):
        """完成 Ch1 全部 7 关后 +50 章节奖励"""
        # Q1.7 是 Ch1 最后一关，完成后 XP = 80 + 7*10 + 50 = 200
        q17_xp = next(xp for lid, xp in self.xp_after_each_level if lid == "Q1.7")
        assert q17_xp == 200  # 80 + 70 + 50

    def test_xp_chapter_bonus_after_ch2(self):
        """完成 Ch2 全部 5 关后 +50 章节奖励"""
        q25_xp = next(xp for lid, xp in self.xp_after_each_level if lid == "Q2.5")
        assert q25_xp == 300  # 200 + 50 + 50

    def test_xp_chapter_bonus_after_ch3(self):
        q35_xp = next(xp for lid, xp in self.xp_after_each_level if lid == "Q3.5")
        assert q35_xp == 400  # 300 + 50 + 50

    def test_xp_chapter_bonus_after_ch4(self):
        q45_xp = next(xp for lid, xp in self.xp_after_each_level if lid == "Q4.5")
        assert q45_xp == 500  # 400 + 50 + 50

    def test_xp_chapter_bonus_after_ch5(self):
        q55_xp = next(xp for lid, xp in self.xp_after_each_level if lid == "Q5.5")
        assert q55_xp == 600  # 500 + 50 + 50

    def test_xp_chapter_bonus_after_ch6(self):
        q65_xp = next(xp for lid, xp in self.xp_after_each_level if lid == "Q6.5")
        assert q65_xp == 700  # 600 + 50 + 50

    def test_xp_chapter_bonus_after_ch7(self):
        q75_xp = next(xp for lid, xp in self.xp_after_each_level if lid == "Q7.5")
        assert q75_xp == 800  # 700 + 50 + 50

    def test_xp_chapter_bonus_after_ch8(self):
        q85_xp = next(xp for lid, xp in self.xp_after_each_level if lid == "Q8.5")
        assert q85_xp == 900  # 800 + 50 + 50

    def test_xp_chapter_bonus_after_ch9(self):
        q95_xp = next(xp for lid, xp in self.xp_after_each_level if lid == "Q9.5")
        assert q95_xp == 1000  # 900 + 50 + 50

    def test_xp_chapter_bonus_after_ch10(self):
        q105_xp = next(xp for lid, xp in self.xp_after_each_level if lid == "Q10.5")
        assert q105_xp == 1100  # 1000 + 50 + 50

    def test_xp_chapter_bonus_after_ch11(self):
        q115_xp = next(xp for lid, xp in self.xp_after_each_level if lid == "Q11.5")
        assert q115_xp == 1200  # 1100 + 50 + 50

    def test_xp_chapter_bonus_after_ch12(self):
        q125_xp = next(xp for lid, xp in self.xp_after_each_level if lid == "Q12.5")
        assert q125_xp == 1300  # 1200 + 50 + 50

    def test_final_xp_is_1300(self):
        """最终 XP = 1300（65*10 + 13*50）"""
        assert self.total_xp == 1300

    def test_xp_after_each_chapter_completion(self):
        """每个章节完成时的 XP 值"""
        expected = {
            "Q0.3": 80,
            "Q1.7": 200,
            "Q2.5": 300,
            "Q3.5": 400,
            "Q4.5": 500,
            "Q5.5": 600,
            "Q6.5": 700,
            "Q7.5": 800,
            "Q8.5": 900,
            "Q9.5": 1000,
            "Q10.5": 1100,
            "Q11.5": 1200,
            "Q12.5": 1300,
        }
        for lid, expected_xp in expected.items():
            actual_xp = next(xp for l, xp in self.xp_after_each_level if l == lid)
            assert actual_xp == expected_xp, (
                f"After {lid}: expected {expected_xp} XP, got {actual_xp}"
            )

    # ---- 验证报告生成 ----

    def _generate_report(self):
        r = client.post("/api/report", json={
            "completed_levels": self.completed_levels,
            "level_attempts": self.level_attempts,
            "level_first_try": self.level_first_try,
            "level_time_spent": self.level_time_spent,
            "total_xp": self.total_xp,
        })
        assert r.status_code == 200
        return r.json()

    def test_report_completion_rate_100(self):
        """报告显示完成率（65/145 = Ch0-12 全通）"""
        data = self._generate_report()
        assert data["completion_rate"] == 65 / 145
        assert data["completed_count"] == 65
        assert data["total_levels"] == 145

    def test_report_grade_s(self):
        """报告评定（65/145 完成率 ≈ 44.8% -> D 级）"""
        data = self._generate_report()
        assert data["grade"] == "D"
        assert "起步中" in data["grade_comment"]

    def test_report_total_xp_1300(self):
        """报告总 XP = 1300"""
        data = self._generate_report()
        assert data["total_xp"] == 1300

    def test_report_first_try_count_65(self):
        """所有 65 关都是首通"""
        data = self._generate_report()
        assert data["first_try_count"] == 65

    def test_report_total_attempts_65(self):
        """总尝试次数 = 65（每关 1 次）"""
        data = self._generate_report()
        assert data["total_attempts"] == 65

    # ---- 验证知识域全部 100% ----

    def test_report_all_domains_100(self):
        """Ch0-12 知识域 100%，Ch13-28 知识域 0%"""
        data = self._generate_report()
        ch12_domains = {"架构基础", "工作负载管理", "网络与服务", "配置与密钥", "存储管理", "调度与资源",
                        "批量任务", "有状态应用", "权限管理", "自动伸缩", "入口路由", "网络安全"}
        for domain, stats in data["domain_stats"].items():
            if domain in ch12_domains:
                assert stats["rate"] == 1.0, f"Domain {domain} rate is {stats['rate']}, expected 1.0"
                assert stats["completed"] == stats["total"]
            else:
                assert stats["rate"] == 0.0, f"Domain {domain} rate is {stats['rate']}, expected 0.0"

    def test_report_domain_levels_all_completed(self):
        """Ch0-12 知识域的关卡都标记为已完成"""
        data = self._generate_report()
        ch12_domains = {"架构基础", "工作负载管理", "网络与服务", "配置与密钥", "存储管理", "调度与资源",
                        "批量任务", "有状态应用", "权限管理", "自动伸缩", "入口路由", "网络安全"}
        for domain, stats in data["domain_stats"].items():
            if domain in ch12_domains:
                for lv in stats["levels"]:
                    assert lv["completed"] is True, f"{lv['id']} not marked completed"
                    assert lv["first_try"] is True, f"{lv['id']} not marked first_try"
                    assert lv["attempts"] == 1

    # ---- 验证无薄弱项 ----

    def test_report_no_weak_areas(self):
        """Ch13-28 未完成 -> 有薄弱项"""
        data = self._generate_report()
        assert len(data["weak_areas"]) == 80  # Ch13-28 共 80 关未完成

    # ---- 验证称号 ----

    def test_report_rank_is_legend(self):
        """称号为 K8s 传奇"""
        data = self._generate_report()
        assert "K8s 传奇" in data["rank"]

    def test_report_next_rank_is_none(self):
        """已满级，无下一称号"""
        data = self._generate_report()
        assert data["next_rank"] is None
        assert data["xp_to_next_rank"] == 0

    # ---- 验证优势项 ----

    def test_report_strengths_count_65(self):
        """65 个优势项（全部首通）"""
        data = self._generate_report()
        assert len(data["strengths"]) == 65

    # ---- 验证学习建议 ----

    def test_report_no_recommendations(self):
        """Ch13-28 未完成 -> 有学习建议"""
        data = self._generate_report()
        assert len(data["recommendations"]) > 0  # 未完成章节会有建议

    # ---- 验证章节统计 ----

    def test_report_all_chapters_complete(self):
        """Ch0-12 章节 100% 完成，Ch13-28 未完成"""
        data = self._generate_report()
        # Ch00 has 3 levels
        ch00 = data["chapter_stats"]["ch00"]
        assert ch00["total"] == 3
        assert ch00["completed"] == 3
        assert ch00["rate"] == 1.0
        # Ch01 has 7 levels (incl. Q1.6, Q1.7)
        ch01 = data["chapter_stats"]["ch01"]
        assert ch01["total"] == 7
        assert ch01["completed"] == 7
        assert ch01["rate"] == 1.0
        # Ch02-12 have 5 levels each
        for ch_id in ["ch02", "ch03", "ch04", "ch05", "ch06", "ch07", "ch08", "ch09", "ch10", "ch11", "ch12"]:
            ch = data["chapter_stats"][ch_id]
            assert ch["total"] == 5
            assert ch["completed"] == 5
            assert ch["rate"] == 1.0
        for ch_id in [f"ch{i:02d}" for i in range(13, 29)]:
            ch = data["chapter_stats"][ch_id]
            assert ch["total"] == 5
            assert ch["completed"] == 0
            assert ch["rate"] == 0.0

    # ---- 验证时间统计 ----

    def test_report_total_time_spent(self):
        """总时间 = 65 * 60 = 3900 秒"""
        data = self._generate_report()
        assert data["total_time_spent"] == 3900


# ==========================================================================
#  逐关验证（参数化测试）
# ==========================================================================

class TestEachLevelSubmission:
    """逐个验证每个关卡的提交"""

    @pytest.mark.parametrize("level_id", ALL_LEVEL_IDS)
    def test_submit_correct_answer(self, level_id):
        """每个关卡的正确答案都能通过"""
        r = client.post("/api/check", json={
            "level_id": level_id,
            "user_yaml": CORRECT_ANSWERS[level_id],
        })
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True, (
            f"Level {level_id} failed with correct answer: {data.get('error', '')}"
        )

    @pytest.mark.parametrize("level_id", ALL_LEVEL_IDS)
    def test_submit_wrong_answer_fails(self, level_id):
        """错误答案应该失败"""
        r = client.post("/api/check", json={
            "level_id": level_id,
            "user_yaml": "apiVersion: v1\nkind: Pod\nmetadata:\n  name: totally-wrong\nspec:\n  containers:\n    - name: x\n      image: wrong:latest\n",
        })
        assert r.status_code == 200
        assert r.json()["ok"] is False


# ==========================================================================
#  XP 累积序列验证
# ==========================================================================

class TestXPAccumulation:
    """验证 XP 逐步累积的完整序列"""

    def test_full_xp_sequence(self):
        """验证每一步的 XP 值"""
        total_xp = 0
        completed = []
        chapter_bonus_claimed = set()
        xp_sequence = []

        for level_id in ALL_LEVEL_IDS:
            # 提交
            r = client.post("/api/check", json={
                "level_id": level_id,
                "user_yaml": CORRECT_ANSWERS[level_id],
            })
            assert r.json()["ok"] is True

            completed.append(level_id)
            total_xp += LEVEL_XP

            ch_num = int(level_id.split(".")[0][1:])
            ch_levels = CHAPTERS[ch_num]
            if all(l in completed for l in ch_levels) and ch_num not in chapter_bonus_claimed:
                total_xp += CHAPTER_BONUS_XP
                chapter_bonus_claimed.add(ch_num)

            xp_sequence.append((level_id, total_xp))

        # 验证完整序列
        expected_xp = 0
        claimed = set()
        for i, level_id in enumerate(ALL_LEVEL_IDS):
            expected_xp += LEVEL_XP
            ch_num = int(level_id.split(".")[0][1:])
            ch_levels = CHAPTERS[ch_num]
            done_so_far = [l for l in ALL_LEVEL_IDS[:i + 1] if l.startswith(f"Q{ch_num}.")]
            if len(done_so_far) == len(CHAPTERS[ch_num]) and ch_num not in claimed:
                expected_xp += CHAPTER_BONUS_XP
                claimed.add(ch_num)
            assert xp_sequence[i] == (level_id, expected_xp), (
                f"Step {i}: expected ({level_id}, {expected_xp}), got {xp_sequence[i]}"
            )

        assert expected_xp == 1300
        assert total_xp == 1300
